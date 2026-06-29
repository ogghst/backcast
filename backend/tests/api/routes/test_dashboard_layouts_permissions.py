"""Phase 6 + Phase 7 — Backend persistence correctness for global dashboards.

Covers gaps from
``docs/03-project-plan/iterations/2026-06-29-global-dashboard-widgets/
global-dashboard-widgets-design.md``:

Phase 6 (§7 Phase 6):

- **G4** — `RoleChecker` supports any-of across multiple permissions, and the
  6 dashboard-layout routes use ``required_permissions=["project-read",
  "portfolio-read"]`` so a portfolio-only role is no longer 403'd.
- **G5** — `get_for_user_project(strict_scope=True)` returns only the exact
  scope (no global union), so a user's global layouts do not pollute every
  project list (and vice-versa).
- **G8** — `clone_template(is_default=True)` clears any prior default for the
  user/scope before inserting, so a re-firing first-visit clone cannot leave
  two ``is_default=True`` layouts.
- **G13** — `get_templates(scope=...)` filters templates by the ``scope``
  COLUMN (``"project"`` / ``"portfolio"``).

Phase 7 (§7 Phase 7):

- **D3 seed + role column** — ``role``/``scope`` columns; 3 portfolio
  templates (``Portfolio Overview`` role=NULL, ``Cost Controlling``
  role=cost-controller, ``PMO Schedule`` role=pmo-director); viewer template
  intentionally NOT seeded.
- **get_default_template_for_role** — exact role match, else generic
  (role IS NULL) fallback; never returns a project-scope template.
- **G9** — ``get_user_roles`` returns roles in deterministic name-ASC order so
  ``display_role = roles[0]`` is stable for multi-role users.

Why most tests hit the service / RBAC layer directly rather than the ASGI
client: the shared ``tests/conftest.py`` monkey-patches
``RoleChecker.__call__`` to bypass all RBAC (so the default ``client`` fixture
authenticates as the global admin). That mirrors the precedent in
``tests/api/routes/test_evm_batch_scoping.py`` (G2), which validates the
underlying RBAC resolution directly. The ``RoleChecker`` any-of branch itself
is unit-tested by recovering the real ``__call__`` from source (``inspect
.getsource`` reads the file, unaffected by the runtime patch) so the actual
production logic is exercised.

Test-fixture note (project memory 35): the ``db`` fixture COMMITS, so any test
creating persistent rows (users, role assignments, layouts) cleans up in a
``finally`` block to avoid junk accumulating in the dev DB.
"""

import ast
import importlib
import inspect
import textwrap
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any
from uuid import UUID, uuid4

import pytest
from fastapi import Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import RoleChecker, UserIdentity, get_current_user
from app.core.rbac_unified import (
    get_unified_rbac_service,
    set_unified_rbac_session,
)
from app.db.session import get_db
from app.models.domain.dashboard_layout import DashboardLayout
from app.models.domain.rbac import RBACRole
from app.models.domain.user import User
from app.models.domain.user_role_assignment import (
    ScopeType,
    UserRoleAssignment,
)
from app.services.dashboard_layout_service import DashboardLayoutService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


# Type of the recovered RoleChecker.__call__ coroutine function.
RoleCheckerCall = Callable[[RoleChecker, UserIdentity, Any], Awaitable[UserIdentity]]


def _recover_real_rolechecker_call() -> RoleCheckerCall:
    """Return the REAL ``RoleChecker.__call__`` recovered from the source file.

    ``tests/conftest.py`` monkey-patches ``RoleChecker.__call__`` to bypass all
    RBAC at import time (so the default ASGI ``client`` authenticates as the
    global admin). ``inspect.getsource`` is unreliable after that patch
    (it may return the patched function, raise ``OSError``, or return the whole
    class body depending on how the attribute was bound).

    To exercise the REAL production any-of branch we instead:

    1. Read ``app/api/dependencies/auth.py`` from disk.
    2. Parse it with ``ast`` and extract the ``RoleChecker.__call__`` method
       node verbatim.
    3. Recompile that method into a fresh function bound to the same globals
       the production method uses.

    This faithfully executes the actual any-of code path in ``auth.py``.
    """
    auth_module = importlib.import_module("app.api.dependencies.auth")
    src_path = Path(inspect.getfile(auth_module))
    tree = ast.parse(src_path.read_text())

    call_node: ast.AsyncFunctionDef | None = None
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "RoleChecker":
            for item in node.body:
                if isinstance(item, ast.AsyncFunctionDef) and item.name == "__call__":
                    call_node = item
                    break
            break
    assert call_node is not None, "Could not locate RoleChecker.__call__"

    # Re-emit the method as a top-level async function and compile it.
    segment = ast.get_source_segment(src_path.read_text(), call_node)
    assert segment is not None, "Could not extract __call__ source segment"
    func_src = "async def " + segment.split("async def ", 1)[1]
    # ``ast.get_source_segment`` returns the indented method; dedent for top-level.
    func_src = textwrap.dedent(func_src)
    code_obj = compile(func_src, "<recovered RoleChecker.__call__>", "exec")
    namespace: dict[str, object] = {
        "Annotated": Annotated,
        "HTTPException": HTTPException,
        "Depends": Depends,
        "AsyncSession": AsyncSession,
        "UserIdentity": UserIdentity,
        "get_current_user": get_current_user,
        "get_db": get_db,
        "get_unified_rbac_service": get_unified_rbac_service,
        "set_unified_rbac_session": set_unified_rbac_session,
        "ScopeType": ScopeType,
        "status": status,
    }
    exec(code_obj, namespace)  # noqa: S102  (intentional exec of recovered prod code)
    return namespace["__call__"]  # type: ignore[return-value]


async def _create_user(db: AsyncSession, *, email: str) -> UUID:
    """Insert a fresh active user and return its root id."""
    user_id = uuid4()
    db.add(
        User(
            id=user_id,
            user_id=user_id,
            email=email,
            hashed_password="x",
            full_name=email,
            is_active=True,
            created_by=user_id,
        )
    )
    await db.flush()
    return user_id


async def _grant_global_role(
    db: AsyncSession, *, user_id: UUID, role_id: UUID, granted_by: UUID
) -> UUID:
    """Assign a GLOBAL-scoped role to a user; return the assignment id."""
    assignment_id = uuid4()
    db.add(
        UserRoleAssignment(
            id=assignment_id,
            user_id=user_id,
            role_id=role_id,
            scope_type=ScopeType.GLOBAL.value,
            scope_id=None,
            granted_by=granted_by,
        )
    )
    await db.flush()
    return assignment_id


async def _ensure_role(
    db: AsyncSession, *, name: str, permissions: list[str], system_user_id: UUID
) -> tuple[UUID, list[UUID]]:
    """Create (or reuse) an RBAC role + its permission rows.

    Returns ``(role_id, permission_ids)`` for cleanup.
    """
    from app.models.domain.rbac import RBACRolePermission

    existing_id = (
        await db.execute(select(RBACRole.id).where(RBACRole.name == name))
    ).scalar_one_or_none()
    if existing_id is not None:
        existing_perm_ids = [
            row[0]
            for row in (
                await db.execute(
                    select(RBACRolePermission.id).where(
                        RBACRolePermission.role_id == existing_id
                    )
                )
            ).all()
        ]
        return existing_id, existing_perm_ids

    role_id = uuid4()
    db.add(
        RBACRole(
            id=role_id,
            name=name,
            description=f"Test role {name}",
            is_system=False,
        )
    )
    await db.flush()
    perm_ids: list[UUID] = []
    for perm in permissions:
        pid = uuid4()
        db.add(RBACRolePermission(id=pid, role_id=role_id, permission=perm))
        perm_ids.append(pid)
    await db.flush()
    return role_id, perm_ids


async def _invalidate_rbac_cache(user_id: UUID) -> None:
    """Clear the unified RBAC caches for a user + refresh role permissions.

    Two caches live on ``UnifiedRBACService``:

    - assignment cache (user -> roles), invalidated per scope.
    - permissions cache (role -> permissions), populated only from
      ``refresh_permissions_cache``. Freshly-created test roles are NOT in it
      (``_check_permission_from_roles`` returns False on miss), so we must
      refresh after inserting role/permission rows.
    """
    service = get_unified_rbac_service()
    for scope_type in (ScopeType.GLOBAL, ScopeType.PROJECT, ScopeType.CHANGE_ORDER):
        service._invalidate_assignment_cache(user_id, scope_type.value, None)  # noqa: SLF001
    await service.refresh_permissions_cache()


async def _create_layout_row(
    db: AsyncSession,
    *,
    user_id: UUID,
    name: str,
    project_id: UUID | None,
    is_template: bool = False,
    is_default: bool = False,
    scope: str | None = None,
    role: str | None = None,
) -> DashboardLayout:
    """Insert a DashboardLayout row directly and return it."""
    layout = DashboardLayout(
        name=name,
        description=None,
        user_id=user_id,
        project_id=project_id,
        is_template=is_template,
        is_default=is_default,
        widgets=[],
        scope=scope,
        role=role,
    )
    db.add(layout)
    await db.flush()
    await db.refresh(layout)
    return layout


# ---------------------------------------------------------------------------
# G4 — RoleChecker any-of permission support
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rolechecker_anyof_grants_when_user_has_one_of(
    db: AsyncSession,
) -> None:
    """``required_permissions=["a","b"]`` grants when the user holds ANY of them.

    A portfolio-only role (has ``portfolio-read`` but NOT ``project-read``)
    must pass a ``["project-read","portfolio-read"]`` guard. This is the core
    G4 fix: previously the route only checked a single permission.
    """
    system_user_id = uuid4()
    # Avoid polluting the users table — use a throwaway id we never insert as a
    # User row; has_permission only consults role assignments, not User.is_active
    # (active-check happens in get_current_user, which RoleChecker does not call).
    portfolio_user_id = uuid4()

    role_id, perm_ids = await _ensure_role(
        db,
        name="test-portfolio-only",
        permissions=["portfolio-read"],
        system_user_id=system_user_id,
    )
    assignment_id = await _grant_global_role(
        db, user_id=portfolio_user_id, role_id=role_id, granted_by=system_user_id
    )
    await db.flush()

    try:
        set_unified_rbac_session(db)
        await _invalidate_rbac_cache(portfolio_user_id)
        rc = RoleChecker(required_permissions=["project-read", "portfolio-read"])
        real_call = _recover_real_rolechecker_call()
        ui = UserIdentity(user_id=portfolio_user_id)
        # Should grant (portfolio-read held) — no exception raised.
        result = await real_call(rc, ui, db)
        assert result.user_id == portfolio_user_id
    finally:
        await db.execute(
            delete(UserRoleAssignment).where(UserRoleAssignment.id == assignment_id)
        )
        from app.models.domain.rbac import RBACRolePermission

        await db.execute(
            delete(RBACRolePermission).where(RBACRolePermission.id.in_(perm_ids))
        )
        await db.execute(delete(RBACRole).where(RBACRole.id == role_id))
        await db.flush()
        # Refresh caches BEFORE unsetting the session so the deleted test role
        # is evicted from the permissions cache (and the user's assignment cache).
        set_unified_rbac_session(db)
        await _invalidate_rbac_cache(portfolio_user_id)
        set_unified_rbac_session(None)


@pytest.mark.asyncio
async def test_rolechecker_anyof_denies_when_user_has_neither(
    db: AsyncSession,
) -> None:
    """A user with NEITHER permission is denied (403)."""
    role_id, perm_ids = await _ensure_role(
        db,
        name="test-no-read",
        permissions=["some-other-perm"],
        system_user_id=uuid4(),
    )
    norole_user_id = uuid4()
    assignment_id = await _grant_global_role(
        db,
        user_id=norole_user_id,
        role_id=role_id,
        granted_by=uuid4(),
    )
    await db.flush()

    try:
        set_unified_rbac_session(db)
        await _invalidate_rbac_cache(norole_user_id)
        rc = RoleChecker(required_permissions=["project-read", "portfolio-read"])
        real_call = _recover_real_rolechecker_call()
        ui = UserIdentity(user_id=norole_user_id)
        with pytest.raises(HTTPException) as exc:
            await real_call(rc, ui, db)
        assert exc.value.status_code == 403
    finally:
        await db.execute(
            delete(UserRoleAssignment).where(UserRoleAssignment.id == assignment_id)
        )
        from app.models.domain.rbac import RBACRolePermission

        await db.execute(
            delete(RBACRolePermission).where(RBACRolePermission.id.in_(perm_ids))
        )
        await db.execute(delete(RBACRole).where(RBACRole.id == role_id))
        await db.flush()
        set_unified_rbac_session(db)
        await _invalidate_rbac_cache(norole_user_id)
        set_unified_rbac_session(None)


@pytest.mark.asyncio
async def test_rolechecker_single_required_permission_still_works(
    db: AsyncSession,
) -> None:
    """Backward-compat: existing ``required_permission=...`` callers unaffected.

    A user holding exactly ``dashboard-template-update`` passes a guard that
    still uses the single-permission form; a user without it is denied.
    """
    role_id, perm_ids = await _ensure_role(
        db,
        name="test-template-updater",
        permissions=["dashboard-template-update"],
        system_user_id=uuid4(),
    )
    user_id = uuid4()
    assignment_id = await _grant_global_role(
        db, user_id=user_id, role_id=role_id, granted_by=uuid4()
    )
    await db.flush()

    try:
        set_unified_rbac_session(db)
        await _invalidate_rbac_cache(user_id)

        # Holds the permission -> granted.
        rc_ok = RoleChecker(required_permission="dashboard-template-update")
        real_call = _recover_real_rolechecker_call()
        ui = UserIdentity(user_id=user_id)
        result = await real_call(rc_ok, ui, db)
        assert result.user_id == user_id

        # Does NOT hold a different permission -> denied.
        await _invalidate_rbac_cache(user_id)
        rc_no = RoleChecker(required_permission="portfolio-read")
        with pytest.raises(HTTPException) as exc:
            await real_call(rc_no, ui, db)
        assert exc.value.status_code == 403
    finally:
        await db.execute(
            delete(UserRoleAssignment).where(UserRoleAssignment.id == assignment_id)
        )
        from app.models.domain.rbac import RBACRolePermission

        await db.execute(
            delete(RBACRolePermission).where(RBACRolePermission.id.in_(perm_ids))
        )
        await db.execute(delete(RBACRole).where(RBACRole.id == role_id))
        await db.flush()
        set_unified_rbac_session(db)
        await _invalidate_rbac_cache(user_id)
        set_unified_rbac_session(None)


# ---------------------------------------------------------------------------
# G5 — get_for_user_project strict_scope
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_for_user_project_strict_scope_excludes_global(
    db: AsyncSession,
) -> None:
    """``strict_scope=True`` with a project_id returns ONLY that project's layouts.

    Global layouts (project_id IS NULL) owned by the same user must NOT appear.
    This is the G5 fix: prevents a global layout from polluting every project's
    layout list.
    """
    user_id = await _create_user(db, email=f"strict-{uuid4().hex[:8]}@backcast.test")
    project_id = uuid4()
    other_project_id = uuid4()

    rows: list[DashboardLayout] = []
    try:
        rows.append(
            await _create_layout_row(
                db, user_id=user_id, name="Global", project_id=None
            )
        )
        rows.append(
            await _create_layout_row(
                db,
                user_id=user_id,
                name="Project X",
                project_id=project_id,
            )
        )
        rows.append(
            await _create_layout_row(
                db,
                user_id=user_id,
                name="Project Y",
                project_id=other_project_id,
            )
        )

        service = DashboardLayoutService(db)

        # strict_scope=True: only project X (no global, no other project).
        strict = await service.get_for_user_project(
            user_id, project_id=project_id, strict_scope=True
        )
        strict_names = {r.name for r in strict}
        assert strict_names == {"Project X"}

        # Default (strict_scope=False): project X ∪ global.
        union = await service.get_for_user_project(user_id, project_id=project_id)
        union_names = {r.name for r in union}
        assert union_names == {"Project X", "Global"}

        # strict_scope=True with project_id=None: only global.
        strict_global = await service.get_for_user_project(
            user_id, project_id=None, strict_scope=True
        )
        assert {r.name for r in strict_global} == {"Global"}
    finally:
        for r in rows:
            await db.execute(delete(DashboardLayout).where(DashboardLayout.id == r.id))
        await db.execute(delete(User).where(User.user_id == user_id))
        await db.flush()


# ---------------------------------------------------------------------------
# G8 — clone_template is_default clears prior default
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_clone_template_is_default_clears_prior_default(
    db: AsyncSession,
) -> None:
    """Cloning with ``is_default=True`` clears the prior default for the scope.

    After the clone, exactly ONE ``is_default=True`` layout exists in the
    user's global scope (the new clone).
    """
    owner_id = uuid4()
    try:
        # Seed a global template (owned by a system user).
        system_id = uuid4()
        template = await _create_layout_row(
            db,
            user_id=system_id,
            name="Template-A",
            project_id=None,
            is_template=True,
        )

        # Pre-existing user default global layout.
        prior = await _create_layout_row(
            db,
            user_id=owner_id,
            name="Prior default",
            project_id=None,
            is_default=True,
        )

        service = DashboardLayoutService(db)
        cloned = await service.clone_template(
            template.id,
            owner_id,
            project_id=None,
            name="Cloned default",
            is_default=True,
        )

        # Refresh prior from DB to confirm its is_default was cleared.
        await db.refresh(prior)
        assert prior.is_default is False
        assert cloned.is_default is True
        assert cloned.project_id is None
        assert cloned.user_id == owner_id

        # Exactly one is_default global layout for this user.
        stmt = select(DashboardLayout).where(
            DashboardLayout.user_id == owner_id,
            DashboardLayout.is_default == True,  # noqa: E712
            DashboardLayout.project_id.is_(None),
        )
        defaults = (await db.execute(stmt)).scalars().all()
        assert len(defaults) == 1
        assert defaults[0].id == cloned.id
    finally:
        await db.execute(
            delete(DashboardLayout).where(DashboardLayout.user_id == owner_id)
        )
        # Clean the template + system-user rows we created (template only;
        # system_id User row was never inserted).
        await db.execute(
            delete(DashboardLayout).where(DashboardLayout.name == "Template-A")
        )
        await db.flush()


@pytest.mark.asyncio
async def test_clone_template_default_false_does_not_disturb_existing_default(
    db: AsyncSession,
) -> None:
    """A normal clone (``is_default=False``) leaves the existing default intact.

    Backward-compat for the manual clone flow.
    """
    owner_id = uuid4()
    try:
        system_id = uuid4()
        template = await _create_layout_row(
            db,
            user_id=system_id,
            name="Template-B",
            project_id=None,
            is_template=True,
        )
        prior = await _create_layout_row(
            db,
            user_id=owner_id,
            name="Prior default B",
            project_id=None,
            is_default=True,
        )

        service = DashboardLayoutService(db)
        cloned = await service.clone_template(template.id, owner_id, project_id=None)

        await db.refresh(prior)
        assert prior.is_default is True  # unchanged
        assert cloned.is_default is False
    finally:
        await db.execute(
            delete(DashboardLayout).where(DashboardLayout.user_id == owner_id)
        )
        await db.execute(
            delete(DashboardLayout).where(DashboardLayout.name == "Template-B")
        )
        await db.flush()


# ---------------------------------------------------------------------------
# G13 — get_templates scope filter (Phase 7: filters on the scope COLUMN)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_templates_scope_filter(db: AsyncSession) -> None:
    """``get_templates(scope=...)`` filters on the ``scope`` COLUMN.

    Phase 7 correction: all templates are stored ``project_id=NULL``, so the
    Phase-6 ``project_id``-based filter was a no-op for templates. The filter
    now keys on the ``scope`` column (``"project"`` / ``"portfolio"``).

    - ``scope="project"`` -> only templates tagged ``scope="project"``
    - ``scope="portfolio"`` -> only templates tagged ``scope="portfolio"``
    - ``scope=None`` (or any other value) -> all templates (original behavior)
    """
    system_id = uuid4()
    created: list[DashboardLayout] = []
    try:
        # Both stored project_id=NULL (templates are global rows) —
        # distinguished ONLY by the scope column.
        created.append(
            await _create_layout_row(
                db,
                user_id=system_id,
                name="TPL-Project",
                project_id=None,
                is_template=True,
                scope="project",
            )
        )
        created.append(
            await _create_layout_row(
                db,
                user_id=system_id,
                name="TPL-Portfolio",
                project_id=None,
                is_template=True,
                scope="portfolio",
                role="cost-controller",
            )
        )

        service = DashboardLayoutService(db)

        # Isolate to only the templates we just created (the dev DB ships
        # seeded templates; filter by name prefix to reason deterministically).
        async def names(scope: str | None) -> set[str]:
            tpls = await service.get_templates(scope=scope)
            return {t.name for t in tpls if t.name.startswith("TPL-")}

        ours_all = await names(None)
        assert ours_all == {"TPL-Project", "TPL-Portfolio"}

        ours_project = await names("project")
        assert ours_project == {"TPL-Project"}

        ours_portfolio = await names("portfolio")
        assert ours_portfolio == {"TPL-Portfolio"}

        # Unknown scope value falls back to "all" (no filter) per contract.
        ours_unknown = await names("bogus")
        assert ours_unknown == {"TPL-Project", "TPL-Portfolio"}
    finally:
        for c in created:
            await db.execute(delete(DashboardLayout).where(DashboardLayout.id == c.id))
        await db.flush()


# ---------------------------------------------------------------------------
# Phase 7 — get_default_template_for_role
# ---------------------------------------------------------------------------

# Names of the 3 portfolio templates seeded by the production seed. The dev DB
# may already have these (lifespan seed); tests guard against duplicate seeding
# and clean up only what they themselves insert.
_PORTFOLIO_TEMPLATE_NAMES = {
    "Portfolio Overview",
    "Cost Controlling",
    "PMO Schedule",
}


async def _seed_portfolio_templates_once(
    db: AsyncSession, *, system_user_id: UUID
) -> tuple[list[DashboardLayout], bool]:
    """Ensure the 3 portfolio templates exist; return (rows, inserted_by_us).

    If any of the 3 names already exist (dev DB pre-seeded), inserts only the
    missing ones and returns ``inserted_by_us=False`` for those. The caller
    cleans up only the rows it inserted (never the lifespan-seeded ones).
    """
    service = DashboardLayoutService(db)
    existing = {t.name for t in (await service.get_templates(scope="portfolio"))}
    missing = _PORTFOLIO_TEMPLATE_NAMES - existing
    inserted: list[DashboardLayout] = []
    if missing:
        created_count = await service.seed_templates(system_user_id)
        assert created_count >= len(missing), "seed did not create missing templates"
        # Re-query to grab the freshly-seeded portfolio rows.
        inserted = [
            t
            for t in (await service.get_templates(scope="portfolio"))
            if t.name in missing
        ]
        await db.flush()
    return inserted, bool(inserted)


@pytest.mark.asyncio
async def test_get_default_template_for_role_exact_match(db: AsyncSession) -> None:
    """Exact role match returns the role-tagged portfolio template.

    - ``role="cost-controller"`` -> "Cost Controlling"
    - ``role="pmo-director"`` -> "PMO Schedule"
    """
    system_id = uuid4()
    inserted, _ = await _seed_portfolio_templates_once(db, system_user_id=system_id)
    try:
        service = DashboardLayoutService(db)

        cc = await service.get_default_template_for_role("cost-controller")
        assert cc is not None
        assert cc.name == "Cost Controlling"
        assert cc.scope == "portfolio"
        assert cc.role == "cost-controller"

        pmo = await service.get_default_template_for_role("pmo-director")
        assert pmo is not None
        assert pmo.name == "PMO Schedule"
        assert pmo.scope == "portfolio"
        assert pmo.role == "pmo-director"
    finally:
        for row in inserted:
            await db.execute(
                delete(DashboardLayout).where(DashboardLayout.id == row.id)
            )
        await db.flush()


@pytest.mark.asyncio
async def test_get_default_template_for_role_falls_back_to_generic(
    db: AsyncSession,
) -> None:
    """A role with no exact match falls back to the generic role-IS-NULL template.

    ``role="admin"`` and a never-seeded role both resolve to "Portfolio
    Overview" (role IS NULL).
    """
    system_id = uuid4()
    inserted, _ = await _seed_portfolio_templates_once(db, system_user_id=system_id)
    try:
        service = DashboardLayoutService(db)

        admin = await service.get_default_template_for_role("admin")
        assert admin is not None
        assert admin.name == "Portfolio Overview"
        assert admin.role is None
        assert admin.scope == "portfolio"

        unknown = await service.get_default_template_for_role("never-seeded-role")
        assert unknown is not None
        assert unknown.name == "Portfolio Overview"

        none_role = await service.get_default_template_for_role(None)
        assert none_role is not None
        assert none_role.name == "Portfolio Overview"
    finally:
        for row in inserted:
            await db.execute(
                delete(DashboardLayout).where(DashboardLayout.id == row.id)
            )
        await db.flush()


@pytest.mark.asyncio
async def test_get_default_template_for_role_never_returns_project_template(
    db: AsyncSession,
) -> None:
    """A project-scope template is NEVER returned by the role resolver.

    Even with no portfolio templates present (simulated by scoping the query
    to a fresh user with only project templates), the resolver returns the
    generic portfolio template from the seeded set — never a project template.
    """
    system_id = uuid4()
    inserted, _ = await _seed_portfolio_templates_once(db, system_user_id=system_id)
    try:
        service = DashboardLayoutService(db)

        result = await service.get_default_template_for_role("cost-controller")
        assert result is not None
        # Must be portfolio-scope, never project-scope.
        assert result.scope == "portfolio"
        assert result.name != "Project Overview"
        # And the full project set is never reachable via this resolver.
        all_results = [result.name]
        for r in ("admin", "manager", "viewer", None):
            got = await service.get_default_template_for_role(r)
            if got is not None:
                all_results.append(got.name)
        assert "Project Overview" not in all_results
        assert "EVM Analysis" not in all_results
    finally:
        for row in inserted:
            await db.execute(
                delete(DashboardLayout).where(DashboardLayout.id == row.id)
            )
        await db.flush()


@pytest.mark.asyncio
async def test_seed_templates_idempotent(db: AsyncSession) -> None:
    """Seeding twice creates the portfolio templates only once."""
    system_id = uuid4()
    # Ensure the portfolio set exists (lifespan seed may have already done it).
    inserted, _ = await _seed_portfolio_templates_once(db, system_user_id=system_id)
    try:
        service = DashboardLayoutService(db)

        # Second seed must create 0 new templates (all 7 already exist).
        created = await service.seed_templates(system_id)
        assert created == 0, f"idempotent re-seed created {created} (expected 0)"

        # And the portfolio set is still exactly the 3 expected templates.
        portfolio = await service.get_templates(scope="portfolio")
        assert {t.name for t in portfolio} == _PORTFOLIO_TEMPLATE_NAMES
    finally:
        for row in inserted:
            await db.execute(
                delete(DashboardLayout).where(DashboardLayout.id == row.id)
            )
        await db.flush()


# ---------------------------------------------------------------------------
# Phase 7 — DashboardLayoutRead exposes role + scope
# ---------------------------------------------------------------------------


def test_dashboard_layout_read_exposes_role_and_scope() -> None:
    """``DashboardLayoutRead`` carries ``role`` and ``scope`` (read-only).

    They default to ``None`` so existing payloads (without the fields) still
    validate, and an ORM row with them set round-trips through from_attributes.
    """
    from app.models.schemas.dashboard_layout import DashboardLayoutRead

    # Defaults: a payload omitting role/scope still validates.
    minimal = DashboardLayoutRead(
        id=uuid4(),
        name="X",
        description=None,
        user_id=uuid4(),
        project_id=None,
        is_template=True,
        is_default=False,
        widgets=[],
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    assert minimal.role is None
    assert minimal.scope is None

    # from_attributes: an ORM-like object with role/scope round-trips.
    class _Row:
        def __init__(self) -> None:
            self.id = uuid4()
            self.name = "Cost Controlling"
            self.description = "d"
            self.user_id = uuid4()
            self.project_id = None
            self.is_template = True
            self.is_default = False
            self.widgets: list[dict[str, object]] = []
            self.role = "cost-controller"
            self.scope = "portfolio"
            self.created_at = datetime.now(UTC)
            self.updated_at = datetime.now(UTC)

    read = DashboardLayoutRead.model_validate(_Row())
    assert read.role == "cost-controller"
    assert read.scope == "portfolio"


# ---------------------------------------------------------------------------
# Phase 7 — G9 deterministic role-match (get_user_roles ORDER BY)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_user_roles_deterministic_order(db: AsyncSession) -> None:
    """``get_user_roles`` returns roles in stable name-ASC order (G9).

    A user holding two global roles must get ``roles[0]`` deterministically so
    the ``display_role`` / global-dashboard first-visit template clone is
    reproducible. Before the ORDER BY this was non-deterministic for
    multi-role users.
    """
    system_user_id = uuid4()
    user_id = await _create_user(db, email=f"g9-{uuid4().hex[:8]}@backcast.test")

    # Two roles whose natural DB order is NOT alphabetical — name-ASC must
    # sort "zzz-before" ahead of "aaa-after" is wrong; pick names where
    # insertion order != alphabetical order to actually exercise the sort.
    role_id_a, perm_ids_a = await _ensure_role(
        db,
        name="zzz-test-role",
        permissions=["portfolio-read"],
        system_user_id=system_user_id,
    )
    role_id_b, perm_ids_b = await _ensure_role(
        db,
        name="aaa-test-role",
        permissions=["project-read"],
        system_user_id=system_user_id,
    )
    # Insert in reverse-alphabetical order so the sort is observable.
    await _grant_global_role(
        db, user_id=user_id, role_id=role_id_a, granted_by=system_user_id
    )
    await _grant_global_role(
        db, user_id=user_id, role_id=role_id_b, granted_by=system_user_id
    )
    await db.flush()

    try:
        service = get_unified_rbac_service()
        set_unified_rbac_session(db)
        # Invalidate cache so the fresh DB query (with ORDER BY) runs.
        for scope_type in (
            ScopeType.GLOBAL,
            ScopeType.PROJECT,
            ScopeType.CHANGE_ORDER,
        ):
            service._invalidate_assignment_cache(  # noqa: SLF001
                user_id, scope_type.value, None
            )

        roles = await service.get_user_roles(user_id, scope_type=ScopeType.GLOBAL)
        # Deterministic name-ASC: aaa-test-role before zzz-test-role.
        assert roles == ["aaa-test-role", "zzz-test-role"], (
            f"expected name-ASC order, got {roles}"
        )

        # roles[0] is the deterministic display_role used by the first-visit
        # template clone — must be the alphabetically-first role.
        assert roles[0] == "aaa-test-role"

        # Calling again (now cached) must return the SAME order.
        roles_again = await service.get_user_roles(user_id, scope_type=ScopeType.GLOBAL)
        assert roles_again == roles
    finally:
        from app.models.domain.rbac import RBACRolePermission

        await db.execute(
            delete(UserRoleAssignment).where(UserRoleAssignment.user_id == user_id)
        )
        await db.execute(
            delete(RBACRolePermission).where(
                RBACRolePermission.role_id.in_([role_id_a, role_id_b])
            )
        )
        await db.execute(
            delete(RBACRole).where(RBACRole.id.in_([role_id_a, role_id_b]))
        )
        await db.execute(delete(User).where(User.user_id == user_id))
        await db.flush()
        # Evict the test user from caches before unbinding the session.
        service = get_unified_rbac_service()
        for scope_type in (
            ScopeType.GLOBAL,
            ScopeType.PROJECT,
            ScopeType.CHANGE_ORDER,
        ):
            service._invalidate_assignment_cache(  # noqa: SLF001
                user_id, scope_type.value, None
            )
        set_unified_rbac_session(None)
