"""Tests for CustomEntityTemplateService (Phase 1A).

Mirrors the CostElementTypeService test surface and adds the two
custom-fields-specific guards: field_definitions validation (via the OO
field registry) and target_entity_type immutability on update.

SELF-CLEANUP: the ``db`` fixture COMMITS at teardown (conftest.py), so
every persistent row created here is removed via its own
``async_session_maker()`` session in a ``finally`` block (memory note 35).
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_maker
from app.models.domain.custom_entity_template import CustomEntityTemplate
from app.models.schemas.custom_entity_template import (
    CustomEntityTemplateCreate,
    CustomEntityTemplateUpdate,
)
from app.services.custom_entity_template_service import CustomEntityTemplateService
from tests.factories import create_test_org_unit

# ---------------------------------------------------------------------------
# Self-cleanup helper (memory note 35).
# ---------------------------------------------------------------------------


async def _cleanup_template(root_id: UUID) -> None:
    """Delete every version row for *root_id* in its own committed session."""
    async with async_session_maker() as s:
        await s.execute(
            delete(CustomEntityTemplate).where(
                CustomEntityTemplate.custom_entity_template_id == root_id
            )
        )
        await s.commit()


# ---------------------------------------------------------------------------
# Fixtures.
# ---------------------------------------------------------------------------


def _valid_field_definitions() -> dict[str, dict[str, object]]:
    return {
        "priority": {"type": "select", "label": "Priority", "options": ["low", "high"]},
        "notes": {"type": "text", "label": "Notes", "max_length": 500},
    }


async def _make_template(
    db: AsyncSession,
    actor_id: UUID,
    org_unit_id: UUID,
    *,
    target_entity_type: str = "PROJECT",
    field_definitions: dict[str, dict[str, object]] | None = None,
    code: str | None = None,
) -> CustomEntityTemplate:
    create_in = CustomEntityTemplateCreate(
        code=code or f"CET-{uuid4().hex[:8]}",
        name="Test Template",
        description="desc",
        target_entity_type=target_entity_type,  # type: ignore[arg-type]
        field_definitions=field_definitions or _valid_field_definitions(),
        organizational_unit_id=org_unit_id,
    )
    service = CustomEntityTemplateService(db)
    return await service.create(type_in=create_in, actor_id=actor_id)


# ---------------------------------------------------------------------------
# Create + validation.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_template_valid(db: AsyncSession, actor_id: UUID) -> None:
    """A well-formed template persists and round-trips field_definitions."""
    org_unit = await create_test_org_unit(db, actor_id)
    await db.commit()

    tpl = await _make_template(db, actor_id, org_unit.organizational_unit_id)
    await db.commit()

    try:
        assert tpl.custom_entity_template_id is not None
        assert tpl.target_entity_type == "PROJECT"
        assert isinstance(tpl.field_definitions, dict)
        assert "priority" in tpl.field_definitions

        service = CustomEntityTemplateService(db)
        found = await service.get_by_id(tpl.custom_entity_template_id)
        assert found is not None
        assert found.code == tpl.code
        assert found.created_by_name is not None  # actor is a real user
    finally:
        await _cleanup_template(tpl.custom_entity_template_id)


@pytest.mark.asyncio
async def test_create_rejects_unknown_field_type(
    db: AsyncSession, actor_id: UUID
) -> None:
    """An unknown field type in field_definitions is rejected at create time."""
    org_unit = await create_test_org_unit(db, actor_id)
    await db.commit()

    try:
        bad_defs = {"x": {"type": "nonexistent_type", "label": "X"}}
        with pytest.raises(ValueError, match="Unknown custom field type"):
            await _make_template(
                db,
                actor_id,
                org_unit.organizational_unit_id,
                field_definitions=bad_defs,  # type: ignore[arg-type]
            )
    finally:
        pass  # nothing persisted (create rejected)


@pytest.mark.asyncio
async def test_create_rejects_missing_field_type(
    db: AsyncSession, actor_id: UUID
) -> None:
    """A field spec missing the 'type' key is rejected at create time."""
    org_unit = await create_test_org_unit(db, actor_id)
    await db.commit()

    try:
        bad_defs = {"x": {"label": "X"}}  # no 'type'
        with pytest.raises(ValueError, match="missing 'type'"):
            await _make_template(
                db,
                actor_id,
                org_unit.organizational_unit_id,
                field_definitions=bad_defs,  # type: ignore[arg-type]
            )
    finally:
        pass


@pytest.mark.asyncio
async def test_create_rejects_invalid_target_entity_type(
    db: AsyncSession, actor_id: UUID
) -> None:
    """An out-of-whitelist target_entity_type is rejected at create time.

    The Pydantic ``Literal`` annotation rejects it at schema construction
    (a ``ValidationError``, itself a ``ValueError`` subclass), before the
    service-level whitelist backstop runs. Both layers reject it.
    """
    org_unit = await create_test_org_unit(db, actor_id)
    await db.commit()

    try:
        with pytest.raises(ValueError, match="Input should be"):
            await _make_template(
                db,
                actor_id,
                org_unit.organizational_unit_id,
                target_entity_type="NOT_A_REAL_ENTITY",  # type: ignore[arg-type]
            )
    finally:
        pass


@pytest.mark.asyncio
async def test_create_rejects_unknown_org_unit(
    db: AsyncSession, actor_id: UUID
) -> None:
    """A non-existent organizational_unit_id is rejected."""
    try:
        with pytest.raises(ValueError, match="OrganizationalUnit .* not found"):
            await _make_template(db, actor_id, uuid4())
    finally:
        pass


@pytest.mark.asyncio
async def test_create_rejects_field_definitions_not_dict(
    db: AsyncSession, actor_id: UUID
) -> None:
    """field_definitions must be a dict (versioning JSONB guard).

    Pydantic's ``dict`` annotation rejects a list at schema construction
    (``ValidationError``), so the bad shape never reaches the service.
    """
    org_unit = await create_test_org_unit(db, actor_id)
    await db.commit()

    try:
        with pytest.raises(ValueError, match="Input should be a valid dictionary"):
            await _make_template(
                db,
                actor_id,
                org_unit.organizational_unit_id,
                field_definitions=[{"type": "text", "code": "x"}],  # type: ignore[arg-type]
            )
    finally:
        pass


# ---------------------------------------------------------------------------
# List filtering.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_filter_by_target_entity_type(
    db: AsyncSession, actor_id: UUID
) -> None:
    """get_custom_entity_templates filters server-side by target_entity_type."""
    org_unit = await create_test_org_unit(db, actor_id)
    await db.commit()

    tpl_p = await _make_template(
        db, actor_id, org_unit.organizational_unit_id, target_entity_type="PROJECT"
    )
    tpl_w = await _make_template(
        db, actor_id, org_unit.organizational_unit_id, target_entity_type="WBS_ELEMENT"
    )
    await db.commit()

    try:
        service = CustomEntityTemplateService(db)
        items, total = await service.get_custom_entity_templates(
            filters={"target_entity_type": "PROJECT"}
        )
        assert total >= 1
        assert all(i.target_entity_type == "PROJECT" for i in items)
        assert any(
            i.custom_entity_template_id == tpl_p.custom_entity_template_id
            for i in items
        )
        assert not any(
            i.custom_entity_template_id == tpl_w.custom_entity_template_id
            for i in items
        )
    finally:
        await _cleanup_template(tpl_p.custom_entity_template_id)
        await _cleanup_template(tpl_w.custom_entity_template_id)


# ---------------------------------------------------------------------------
# History.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_history_returns_versions(db: AsyncSession, actor_id: UUID) -> None:
    """After an update, get_history returns >=2 versions."""
    org_unit = await create_test_org_unit(db, actor_id)
    await db.commit()

    tpl = await _make_template(db, actor_id, org_unit.organizational_unit_id)
    await db.commit()

    try:
        service = CustomEntityTemplateService(db)
        update_in = CustomEntityTemplateUpdate(name="Renamed Template")
        await service.update(
            custom_entity_template_id=tpl.custom_entity_template_id,
            type_in=update_in,
            actor_id=actor_id,
        )
        await db.commit()

        history = await service.get_history(tpl.custom_entity_template_id)
        assert len(history) >= 2
    finally:
        await _cleanup_template(tpl.custom_entity_template_id)


# ---------------------------------------------------------------------------
# Update immutability.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_rejects_target_entity_type_change(
    db: AsyncSession, actor_id: UUID
) -> None:
    """Changing target_entity_type on update is rejected (immutable)."""
    org_unit = await create_test_org_unit(db, actor_id)
    await db.commit()

    tpl = await _make_template(db, actor_id, org_unit.organizational_unit_id)
    await db.commit()

    try:
        service = CustomEntityTemplateService(db)
        update_in = CustomEntityTemplateUpdate(target_entity_type="WBS_ELEMENT")  # type: ignore[arg-type]
        with pytest.raises(ValueError, match="target_entity_type is immutable"):
            await service.update(
                custom_entity_template_id=tpl.custom_entity_template_id,
                type_in=update_in,
                actor_id=actor_id,
            )
    finally:
        await _cleanup_template(tpl.custom_entity_template_id)


@pytest.mark.asyncio
async def test_update_same_target_entity_type_is_noop(
    db: AsyncSession, actor_id: UUID
) -> None:
    """Sending the same target_entity_type is allowed (no-op, not rejected)."""
    org_unit = await create_test_org_unit(db, actor_id)
    await db.commit()

    tpl = await _make_template(db, actor_id, org_unit.organizational_unit_id)
    await db.commit()

    try:
        service = CustomEntityTemplateService(db)
        update_in = CustomEntityTemplateUpdate(
            target_entity_type="PROJECT",
            name="Renamed",  # type: ignore[arg-type]
        )
        updated = await service.update(
            custom_entity_template_id=tpl.custom_entity_template_id,
            type_in=update_in,
            actor_id=actor_id,
        )
        await db.commit()
        assert updated.name == "Renamed"
        assert updated.target_entity_type == "PROJECT"
    finally:
        await _cleanup_template(tpl.custom_entity_template_id)


@pytest.mark.asyncio
async def test_update_validates_field_definitions(
    db: AsyncSession, actor_id: UUID
) -> None:
    """Update rejects malformed field_definitions like create does."""
    org_unit = await create_test_org_unit(db, actor_id)
    await db.commit()

    tpl = await _make_template(db, actor_id, org_unit.organizational_unit_id)
    await db.commit()

    try:
        service = CustomEntityTemplateService(db)
        update_in = CustomEntityTemplateUpdate(
            field_definitions={"x": {"type": "bogus"}}  # type: ignore[arg-type]
        )
        with pytest.raises(ValueError, match="Unknown custom field type"):
            await service.update(
                custom_entity_template_id=tpl.custom_entity_template_id,
                type_in=update_in,
                actor_id=actor_id,
            )
    finally:
        await _cleanup_template(tpl.custom_entity_template_id)


# ---------------------------------------------------------------------------
# Soft delete.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_soft_delete_hides_from_current(db: AsyncSession, actor_id: UUID) -> None:
    """soft_delete marks the template deleted; get_by_id returns None."""
    org_unit = await create_test_org_unit(db, actor_id)
    await db.commit()

    tpl = await _make_template(db, actor_id, org_unit.organizational_unit_id)
    await db.commit()

    try:
        service = CustomEntityTemplateService(db)
        await service.soft_delete(
            custom_entity_template_id=tpl.custom_entity_template_id,
            actor_id=actor_id,
        )
        await db.commit()

        assert await service.get_by_id(tpl.custom_entity_template_id) is None
    finally:
        await _cleanup_template(tpl.custom_entity_template_id)


# ---------------------------------------------------------------------------
# RBAC (RoleChecker) — unit-style, no app restart needed.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rbac_read_perm_string_is_seeded() -> None:
    """The 4 custom-entity-template permission strings exist in ROLE_PERMISSIONS.

    RBAC enforcement itself is exercised by RoleChecker against the DB-backed
    permission set, which requires a full app start to merge the seed (the
    startup seeder is idempotent). Here we assert the seed source-of-truth so
    the wiring is guarded without depending on a restart.
    """
    from app.db.seed_users_rbac import ROLE_PERMISSIONS

    perms: set[str] = set()
    for role_perms in ROLE_PERMISSIONS.values():
        perms.update(role_perms.get("permissions", []))

    for p in (
        "custom-entity-template-read",
        "custom-entity-template-create",
        "custom-entity-template-update",
        "custom-entity-template-delete",
    ):
        assert p in perms, f"missing permission in seed: {p}"

    # admin + ai-admin + ai-manager hold all 4; manager/viewer/ai-viewer hold read.
    for role in ("admin", "ai-admin", "ai-manager"):
        rp = set(ROLE_PERMISSIONS[role]["permissions"])
        assert rp.issuperset(
            {
                "custom-entity-template-read",
                "custom-entity-template-create",
                "custom-entity-template-update",
                "custom-entity-template-delete",
            }
        ), f"{role} missing full custom-entity-template perms"
    for role in ("manager", "viewer", "ai-viewer"):
        rp = set(ROLE_PERMISSIONS[role]["permissions"])
        assert "custom-entity-template-read" in rp
        assert "custom-entity-template-create" not in rp
