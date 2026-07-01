"""Phase 1C verification battery for the custom_fields entity-service chokepoint.

Exercises the shared CREATE/UPDATE chokepoint wired into ProjectService /
WBSElementService / WorkPackageService (and the unified ChangeOrderService
path) introduced in Phase 1C. The chokepoint resolves the bound
CustomEntityTemplate, validates the supplied ``custom_fields`` against the
template's ``field_definitions``, and captures the IMMUTABLE snapshot onto the
entity row at create; update-time validation reuses that snapshot (D11).

Coverage (one assertion per design directive):
    (a) create WITH a template + valid custom_fields → snapshot captured +
        values stored (re-fetch + assert both).
    (b) create with custom_fields but NO template → rejected (400-path
        ValueError).
    (c) create with a template but INVALID custom_fields (bad select value)
        → rejected.
    (d) update custom_fields → validates against the captured snapshot:
        rejects a bad value, accepts a good one.
    (e) update with custom_fields ABSENT → unchanged (D11: absent = skip).
    (f) ReferenceField: create with a reference pointing at a non-existent
        user → rejected; pointing at a real user → accepted.

SELF-CLEANUP: the ``db`` fixture COMMITS at teardown (conftest.py) so every
persistent row created here is removed via an ``async_session_maker()``
session in a ``finally`` block (memory note 35).
"""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_maker
from app.models.domain.custom_entity_template import CustomEntityTemplate
from app.models.domain.user import User
from app.models.schemas.project import ProjectCreate, ProjectUpdate
from app.services.custom_field_service import (
    CustomFieldService,
    CustomFieldValidationError,
)
from app.services.project import ProjectService

# ---------------------------------------------------------------------------
# Self-cleanup helpers (memory note 35: db fixture COMMITS at teardown).
# ---------------------------------------------------------------------------


async def _cleanup(table: str, root_col: str, root_id: UUID) -> None:
    """Delete every version row for *root_id* from *table* in its own session."""
    async with async_session_maker() as s:
        await s.execute(
            text(f"DELETE FROM {table} WHERE {root_col} = :rid"), {"rid": root_id}
        )
        await s.commit()


async def _cleanup_by_ids(table: str, ids_col: str, ids: set[UUID]) -> None:
    """Delete every row in *table* whose *ids_col* is in *ids*."""
    if not ids:
        return
    async with async_session_maker() as s:
        await s.execute(
            text(f"DELETE FROM {table} WHERE {ids_col} = ANY(:ids)"),
            {"ids": list(ids)},
        )
        await s.commit()


async def _seed_project_template(
    db: AsyncSession,
    actor_id: UUID,
    *,
    field_definitions: dict[str, Any],
) -> UUID:
    """Seed a PROJECT CustomEntityTemplate and return its root id.

    Uses a UNIQUE code per call so concurrent tests do not collide on the
    code index. The caller is responsible for cleanup.
    """
    root_id = uuid4()
    db.add(
        CustomEntityTemplate(
            custom_entity_template_id=root_id,
            organizational_unit_id=uuid4(),
            target_entity_type="PROJECT",
            code=f"proj-tpl-{root_id.hex[:8]}",
            name=f"Project Template {root_id.hex[:8]}",
            field_definitions=field_definitions,
            created_by=actor_id,
        )
    )
    await db.commit()
    return root_id


# ===========================================================================
# (a) CREATE WITH TEMPLATE + VALID CUSTOM_FIELDS → snapshot + values stored
# (c) CREATE WITH TEMPLATE + INVALID SELECT → rejected
# (b) CREATE WITH CUSTOM_FIELDS BUT NO TEMPLATE → rejected
# (f) REFERENCE FIELD existence check
# ===========================================================================


class TestProjectCreateChokepoint:
    """ProjectService.create_project funnels through the shared chokepoint."""

    @pytest.mark.asyncio
    async def test_create_with_template_captures_snapshot_and_stores_values(
        self, db: AsyncSession, actor_id: UUID
    ) -> None:
        """(a) valid custom_fields → snapshot captured + values stored."""
        template_root = await _seed_project_template(
            db,
            actor_id,
            field_definitions={
                "seismic_area": {
                    "type": "select",
                    "label": "Seismic",
                    "options": ["1", "2", "3", "4"],
                },
                "notes": {"type": "text", "label": "Notes"},
            },
        )

        project_root = uuid4()
        try:
            service = ProjectService(db)
            project = await service.create_project(
                ProjectCreate(
                    project_id=project_root,
                    name="CF-Create-OK",
                    code=f"P-CFOK-{project_root.hex[:6].upper()}",
                    status="active",
                    currency="EUR",
                    contract_value=1000000,
                    custom_entity_template_root_id=template_root,
                    custom_fields={"seismic_area": "2", "notes": "ok"},
                ),
                actor_id,
            )
            await db.commit()

            assert project.custom_fields == {"seismic_area": "2", "notes": "ok"}
            assert project.custom_entity_template_root_id == template_root
            assert project.custom_field_definitions_snapshot is not None
            assert "seismic_area" in project.custom_field_definitions_snapshot

            # Re-fetch the current version via the service to confirm the
            # snapshot + values survived the raw-INSERT flush.
            current = await service.get_as_of(project_root)
            assert current is not None
            assert current.custom_fields == {"seismic_area": "2", "notes": "ok"}
            assert current.custom_entity_template_root_id == template_root
            assert current.custom_field_definitions_snapshot is not None
        finally:
            await _cleanup("projects", "project_id", project_root)
            await _cleanup(
                "custom_entity_templates",
                "custom_entity_template_id",
                template_root,
            )

    @pytest.mark.asyncio
    async def test_create_with_custom_fields_but_no_template_rejected(
        self, db: AsyncSession, actor_id: UUID
    ) -> None:
        """(b) custom_fields without a template root id → ValueError."""
        project_root = uuid4()
        try:
            service = ProjectService(db)
            with pytest.raises(ValueError, match="custom_entity_template_root_id"):
                await service.create_project(
                    ProjectCreate(
                        project_id=project_root,
                        name="CF-NoTpl",
                        code=f"P-NT-{project_root.hex[:6].upper()}",
                        status="active",
                        currency="EUR",
                        contract_value=1000000,
                        custom_fields={"rogue": "x"},
                    ),
                    actor_id,
                )
        finally:
            # Nothing should have been persisted (validation runs before the
            # CreateVersionCommand), but clean defensively.
            await _cleanup("projects", "project_id", project_root)

    @pytest.mark.asyncio
    async def test_create_with_invalid_select_rejected(
        self, db: AsyncSession, actor_id: UUID
    ) -> None:
        """(c) a template-bound create with a bad select value → ValueError."""
        template_root = await _seed_project_template(
            db,
            actor_id,
            field_definitions={
                "seismic_area": {
                    "type": "select",
                    "label": "Seismic",
                    "options": ["1", "2", "3", "4"],
                },
            },
        )

        project_root = uuid4()
        try:
            service = ProjectService(db)
            with pytest.raises(ValueError, match="Seismic"):
                await service.create_project(
                    ProjectCreate(
                        project_id=project_root,
                        name="CF-BadSelect",
                        code=f"P-BS-{project_root.hex[:6].upper()}",
                        status="active",
                        currency="EUR",
                        contract_value=1000000,
                        custom_entity_template_root_id=template_root,
                        custom_fields={"seismic_area": "9"},
                    ),
                    actor_id,
                )
        finally:
            await _cleanup("projects", "project_id", project_root)
            await _cleanup(
                "custom_entity_templates",
                "custom_entity_template_id",
                template_root,
            )


# ===========================================================================
# (d) UPDATE custom_fields → validates against the captured snapshot
# (e) UPDATE with custom_fields ABSENT → unchanged (D11)
# ===========================================================================


class TestProjectUpdateChokepoint:
    """ProjectService.update_project validates against the captured snapshot."""

    @pytest.mark.asyncio
    async def test_update_accepts_good_value_and_rejects_bad(
        self, db: AsyncSession, actor_id: UUID
    ) -> None:
        """(d) update validates against the IMMUTABLE create-time snapshot."""
        template_root = await _seed_project_template(
            db,
            actor_id,
            field_definitions={
                "seismic_area": {
                    "type": "select",
                    "label": "Seismic",
                    "options": ["1", "2", "3", "4"],
                },
            },
        )

        project_root = uuid4()
        try:
            service = ProjectService(db)
            await service.create_project(
                ProjectCreate(
                    project_id=project_root,
                    name="CF-Upd",
                    code=f"P-UP-{project_root.hex[:6].upper()}",
                    status="active",
                    currency="EUR",
                    contract_value=1000000,
                    custom_entity_template_root_id=template_root,
                    custom_fields={"seismic_area": "2"},
                ),
                actor_id,
            )
            await db.commit()

            # Good value accepted.
            updated = await service.update_project(
                project_root,
                ProjectUpdate(custom_fields={"seismic_area": "3"}, branch="main"),
                actor_id,
            )
            await db.commit()
            assert updated.custom_fields == {"seismic_area": "3"}

            # Bad value rejected (validated against the captured snapshot).
            with pytest.raises(CustomFieldValidationError, match="Seismic"):
                await service.update_project(
                    project_root,
                    ProjectUpdate(custom_fields={"seismic_area": "99"}, branch="main"),
                    actor_id,
                )

            # Re-fetch to confirm the rejected update did not mutate the row.
            current = await service.get_as_of(project_root)
            assert current is not None
            assert current.custom_fields == {"seismic_area": "3"}
        finally:
            await _cleanup("projects", "project_id", project_root)
            await _cleanup(
                "custom_entity_templates",
                "custom_entity_template_id",
                template_root,
            )

    @pytest.mark.asyncio
    async def test_update_without_custom_fields_key_is_noop(
        self, db: AsyncSession, actor_id: UUID
    ) -> None:
        """(e) D11: update with custom_fields ABSENT → values unchanged."""
        template_root = await _seed_project_template(
            db,
            actor_id,
            field_definitions={
                "notes": {"type": "text", "label": "Notes"},
            },
        )

        project_root = uuid4()
        try:
            service = ProjectService(db)
            await service.create_project(
                ProjectCreate(
                    project_id=project_root,
                    name="CF-Skip",
                    code=f"P-SK-{project_root.hex[:6].upper()}",
                    status="active",
                    currency="EUR",
                    contract_value=1000000,
                    custom_entity_template_root_id=template_root,
                    custom_fields={"notes": "original"},
                ),
                actor_id,
            )
            await db.commit()

            # Update ONLY the name — custom_fields key absent.
            updated = await service.update_project(
                project_root,
                ProjectUpdate(name="CF-Skip-Renamed", branch="main"),
                actor_id,
            )
            await db.commit()
            assert updated.name == "CF-Skip-Renamed"
            # custom_fields untouched.
            assert updated.custom_fields == {"notes": "original"}
        finally:
            await _cleanup("projects", "project_id", project_root)
            await _cleanup(
                "custom_entity_templates",
                "custom_entity_template_id",
                template_root,
            )


# ===========================================================================
# (f) ReferenceField existence check (D6 MVP target = user)
# ===========================================================================


class TestReferenceFieldExistenceCheck:
    """ReferenceField.validate_async resolves the User by root id at write time."""

    @pytest.mark.asyncio
    async def test_reference_to_nonexistent_user_rejected(
        self, db: AsyncSession, actor_id: UUID
    ) -> None:
        """(f) a reference field pointing at a missing user → ValueError."""
        template_root = await _seed_project_template(
            db,
            actor_id,
            field_definitions={
                "owner": {
                    "type": "reference",
                    "label": "Owner",
                    "target_entity": "user",
                },
            },
        )

        project_root = uuid4()
        try:
            service = ProjectService(db)
            with pytest.raises(ValueError, match="unknown user"):
                await service.create_project(
                    ProjectCreate(
                        project_id=project_root,
                        name="CF-BadRef",
                        code=f"P-BR-{project_root.hex[:6].upper()}",
                        status="active",
                        currency="EUR",
                        contract_value=1000000,
                        custom_entity_template_root_id=template_root,
                        custom_fields={"owner": str(uuid4())},
                    ),
                    actor_id,
                )
        finally:
            await _cleanup("projects", "project_id", project_root)
            await _cleanup(
                "custom_entity_templates",
                "custom_entity_template_id",
                template_root,
            )

    @pytest.mark.asyncio
    async def test_reference_to_real_user_accepted(
        self, db: AsyncSession, actor_id: UUID
    ) -> None:
        """(f) a reference field pointing at an existing user → accepted."""
        template_root = await _seed_project_template(
            db,
            actor_id,
            field_definitions={
                "owner": {
                    "type": "reference",
                    "label": "Owner",
                    "target_entity": "user",
                },
            },
        )

        # Seed a throwaway user row and capture its root id.
        user_root = uuid4()
        project_root = uuid4()
        try:
            db.add(
                User(
                    user_id=user_root,
                    email=f"ref-{user_root.hex[:8]}@test.local",
                    hashed_password="x",
                    full_name="Ref User",
                    is_active=True,
                    created_by=actor_id,
                )
            )
            await db.commit()

            service = ProjectService(db)
            project = await service.create_project(
                ProjectCreate(
                    project_id=project_root,
                    name="CF-GoodRef",
                    code=f"P-GR-{project_root.hex[:6].upper()}",
                    status="active",
                    currency="EUR",
                    contract_value=1000000,
                    custom_entity_template_root_id=template_root,
                    custom_fields={"owner": str(user_root)},
                ),
                actor_id,
            )
            await db.commit()

            assert project.custom_fields == {"owner": str(user_root)}
        finally:
            await _cleanup("projects", "project_id", project_root)
            await _cleanup(
                "custom_entity_templates",
                "custom_entity_template_id",
                template_root,
            )
            await _cleanup("users", "user_id", user_root)


# ===========================================================================
# Pure-unit regression for the no-session fallback (Phase-0 compatibility)
# ===========================================================================


class TestNoSessionFallback:
    """CustomFieldService() with no session skips existence checks (Phase-0)."""

    @pytest.mark.asyncio
    async def test_reference_field_with_no_session_skips_existence(
        self,
    ) -> None:
        """A no-arg CustomFieldService cannot check existence → skips (returns [])."""
        definitions = {
            "owner": {
                "type": "reference",
                "label": "Owner",
                "target_entity": "user",
            }
        }
        errors = await CustomFieldService().validate_field_values(
            definitions, {"owner": str(uuid4())}
        )
        assert errors == []


# ===========================================================================
# API-level: UPDATE with an INVALID custom field value → HTTP 400 (not 404)
# Verifies the route-level CustomFieldValidationError → 400 handler.
# ===========================================================================


class TestProjectUpdateApiReturns400OnBadCustomField:
    """The Project UPDATE route maps CustomFieldValidationError to 400."""

    @pytest.mark.asyncio
    async def test_update_with_invalid_select_returns_400(
        self,
        db: AsyncSession,
        client: AsyncClient,
        actor_id: UUID,
    ) -> None:
        """(API) PUT /projects/{id} with an out-of-range select → 400, not 404."""
        template_root = await _seed_project_template(
            db,
            actor_id,
            field_definitions={
                "seismic_area": {
                    "type": "select",
                    "label": "Seismic",
                    "options": ["1", "2", "3", "4"],
                },
            },
        )

        project_root = uuid4()
        try:
            service = ProjectService(db)
            await service.create_project(
                ProjectCreate(
                    project_id=project_root,
                    name="CF-API-400",
                    code=f"P-A4-{project_root.hex[:6].upper()}",
                    status="active",
                    currency="EUR",
                    contract_value=1000000,
                    custom_entity_template_root_id=template_root,
                    custom_fields={"seismic_area": "2"},
                ),
                actor_id,
            )
            await db.commit()

            # Out-of-range select value: chokepoint raises
            # CustomFieldValidationError → route maps to 400 (not 404).
            response = await client.put(
                f"/projects/{project_root}",
                json={"custom_fields": {"seismic_area": "99"}},
            )
            assert response.status_code == 400
            assert "Seismic" in response.json()["detail"]
        finally:
            await _cleanup("projects", "project_id", project_root)
            await _cleanup(
                "custom_entity_templates",
                "custom_entity_template_id",
                template_root,
            )


# ===========================================================================
# First-time template binding on UPDATE (refines frozen decision D2):
# immutable once SET, but the first binding may happen on edit for a
# template-less existing entity.
# ===========================================================================


async def _create_templateless_project(
    db: AsyncSession,
    actor_id: UUID,
    project_root: UUID,
) -> None:
    """Create a Project with NO custom_entity_template (legacy/template-less row)."""
    service = ProjectService(db)
    await service.create_project(
        ProjectCreate(
            project_id=project_root,
            name="CF-Templateless",
            code=f"P-TL-{project_root.hex[:6].upper()}",
            status="active",
            currency="EUR",
            contract_value=1000000,
        ),
        actor_id,
    )
    await db.commit()


class TestFirstTimeTemplateBindingOnUpdate:
    """ProjectService.update_project binds a template on first edit (D2 refinement).

    (1) UPDATE a template-less entity with a template_root_id + custom_fields
        → binds + captures snapshot + stores values.
    (2) UPDATE an already-bound entity with a DIFFERENT template_root_id
        → CustomFieldValidationError ("immutable").
    (3) UPDATE an already-bound entity with custom_fields (no template change)
        → validates against the existing snapshot: accepts good / rejects bad.
    (4) UPDATE with custom_fields but no template (entity has none)
        → CustomFieldValidationError.
    (5) UPDATE with custom_fields ABSENT → unchanged (D11).
    """

    @pytest.mark.asyncio
    async def test_first_time_binding_captures_snapshot_and_stores_values(
        self, db: AsyncSession, actor_id: UUID
    ) -> None:
        """(1) UPDATE a template-less project, supplying a template + values."""
        template_root = await _seed_project_template(
            db,
            actor_id,
            field_definitions={
                "seismic_area": {
                    "type": "select",
                    "label": "Seismic",
                    "options": ["1", "2", "3", "4"],
                },
                "notes": {"type": "text", "label": "Notes"},
            },
        )

        project_root = uuid4()
        try:
            await _create_templateless_project(db, actor_id, project_root)

            service = ProjectService(db)
            updated = await service.update_project(
                project_root,
                ProjectUpdate(
                    custom_entity_template_root_id=template_root,
                    custom_fields={"seismic_area": "2", "notes": "bound on edit"},
                    branch="main",
                ),
                actor_id,
            )
            await db.commit()

            assert updated.custom_entity_template_root_id == template_root
            assert updated.custom_field_definitions_snapshot is not None
            assert "seismic_area" in updated.custom_field_definitions_snapshot
            assert updated.custom_fields == {
                "seismic_area": "2",
                "notes": "bound on edit",
            }

            # Re-fetch the current version to confirm persistence.
            current = await service.get_as_of(project_root)
            assert current is not None
            assert current.custom_entity_template_root_id == template_root
            assert current.custom_field_definitions_snapshot is not None
            assert (
                current.custom_field_definitions_snapshot
                == updated.custom_field_definitions_snapshot
            )
            assert current.custom_fields == {
                "seismic_area": "2",
                "notes": "bound on edit",
            }
        finally:
            await _cleanup("projects", "project_id", project_root)
            await _cleanup(
                "custom_entity_templates",
                "custom_entity_template_id",
                template_root,
            )

    @pytest.mark.asyncio
    async def test_switching_template_on_bound_entity_rejected(
        self, db: AsyncSession, actor_id: UUID
    ) -> None:
        """(2) UPDATE an already-bound entity with a different template → error."""
        template_a = await _seed_project_template(
            db,
            actor_id,
            field_definitions={"a": {"type": "text", "label": "A"}},
        )
        template_b = await _seed_project_template(
            db,
            actor_id,
            field_definitions={"b": {"type": "text", "label": "B"}},
        )

        project_root = uuid4()
        try:
            service = ProjectService(db)
            await service.create_project(
                ProjectCreate(
                    project_id=project_root,
                    name="CF-Bound",
                    code=f"P-BD-{project_root.hex[:6].upper()}",
                    status="active",
                    currency="EUR",
                    contract_value=1000000,
                    custom_entity_template_root_id=template_a,
                    custom_fields={"a": "x"},
                ),
                actor_id,
            )
            await db.commit()

            # Switch to a different template on update → immutable violation.
            with pytest.raises(CustomFieldValidationError, match="immutable once set"):
                await service.update_project(
                    project_root,
                    ProjectUpdate(
                        custom_entity_template_root_id=template_b,
                        branch="main",
                    ),
                    actor_id,
                )

            # Confirm the rejected update did not mutate the binding.
            current = await service.get_as_of(project_root)
            assert current is not None
            assert current.custom_entity_template_root_id == template_a
        finally:
            await _cleanup("projects", "project_id", project_root)
            await _cleanup_by_ids(
                "custom_entity_templates",
                "custom_entity_template_id",
                {template_a, template_b},
            )

    @pytest.mark.asyncio
    async def test_update_custom_fields_validates_against_existing_snapshot(
        self, db: AsyncSession, actor_id: UUID
    ) -> None:
        """(3) UPDATE an already-bound entity's custom_fields (no template change)."""
        template_root = await _seed_project_template(
            db,
            actor_id,
            field_definitions={
                "seismic_area": {
                    "type": "select",
                    "label": "Seismic",
                    "options": ["1", "2", "3", "4"],
                },
            },
        )

        project_root = uuid4()
        try:
            service = ProjectService(db)
            await service.create_project(
                ProjectCreate(
                    project_id=project_root,
                    name="CF-UpdBound",
                    code=f"P-UB-{project_root.hex[:6].upper()}",
                    status="active",
                    currency="EUR",
                    contract_value=1000000,
                    custom_entity_template_root_id=template_root,
                    custom_fields={"seismic_area": "2"},
                ),
                actor_id,
            )
            await db.commit()

            # Good value accepted (validated against the existing snapshot).
            updated = await service.update_project(
                project_root,
                ProjectUpdate(custom_fields={"seismic_area": "3"}, branch="main"),
                actor_id,
            )
            await db.commit()
            assert updated.custom_fields == {"seismic_area": "3"}

            # Bad value rejected.
            with pytest.raises(CustomFieldValidationError, match="Seismic"):
                await service.update_project(
                    project_root,
                    ProjectUpdate(custom_fields={"seismic_area": "99"}, branch="main"),
                    actor_id,
                )

            current = await service.get_as_of(project_root)
            assert current is not None
            assert current.custom_fields == {"seismic_area": "3"}
        finally:
            await _cleanup("projects", "project_id", project_root)
            await _cleanup(
                "custom_entity_templates",
                "custom_entity_template_id",
                template_root,
            )

    @pytest.mark.asyncio
    async def test_update_custom_fields_without_any_template_rejected(
        self, db: AsyncSession, actor_id: UUID
    ) -> None:
        """(4) UPDATE with custom_fields but no template (entity has none) → error."""
        project_root = uuid4()
        try:
            await _create_templateless_project(db, actor_id, project_root)

            service = ProjectService(db)
            with pytest.raises(
                CustomFieldValidationError,
                match="no custom-field template",
            ):
                await service.update_project(
                    project_root,
                    ProjectUpdate(custom_fields={"rogue": "x"}, branch="main"),
                    actor_id,
                )
        finally:
            await _cleanup("projects", "project_id", project_root)

    @pytest.mark.asyncio
    async def test_update_without_custom_fields_key_is_unchanged(
        self, db: AsyncSession, actor_id: UUID
    ) -> None:
        """(5) UPDATE with custom_fields ABSENT → unchanged (D11)."""
        template_root = await _seed_project_template(
            db,
            actor_id,
            field_definitions={"notes": {"type": "text", "label": "Notes"}},
        )

        project_root = uuid4()
        try:
            service = ProjectService(db)
            await service.create_project(
                ProjectCreate(
                    project_id=project_root,
                    name="CF-Absent",
                    code=f"P-AB-{project_root.hex[:6].upper()}",
                    status="active",
                    currency="EUR",
                    contract_value=1000000,
                    custom_entity_template_root_id=template_root,
                    custom_fields={"notes": "original"},
                ),
                actor_id,
            )
            await db.commit()

            # Update ONLY the name — custom_fields key absent.
            updated = await service.update_project(
                project_root,
                ProjectUpdate(name="CF-Absent-Renamed", branch="main"),
                actor_id,
            )
            await db.commit()
            assert updated.name == "CF-Absent-Renamed"
            assert updated.custom_fields == {"notes": "original"}
            assert updated.custom_entity_template_root_id == template_root
            assert updated.custom_field_definitions_snapshot is not None
        finally:
            await _cleanup("projects", "project_id", project_root)
            await _cleanup(
                "custom_entity_templates",
                "custom_entity_template_id",
                template_root,
            )
