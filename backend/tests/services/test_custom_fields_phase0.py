"""Phase 0 verification battery for admin-defined custom fields.

Exercises the JSONB persistence paths and validation chokepoint introduced in
the custom-fields initiative (see memory note 44 + the functional analysis at
docs/03-project-plan/iterations/2026-06-24-custom-fields-analysis/). The
battery is deliberately deterministic and self-contained:

1. RAW-INSERT path A -- ``custom_fields`` survives ``UpdateCommand`` (branching).
2. ORM-FLUSH path B -- ``custom_fields`` survives CreateBranch + Merge.
3. M12 -- Versionable dict JSONB (``field_definitions``) round-trips through the
   versioning CreateVersion/UpdateVersion commands on ``CustomEntityTemplate``.
4. C1 enforcement -- the unique partial index rejects a second open-ended
   current version per (root, branch).
5. Validation unit -- ``CustomFieldService.validate_field_values`` rejects
   unknown keys, missing-required, bad select, and bool-as-number.
6. CO plumbing -- the rename ``custom_field_values`` -> ``custom_fields`` works
   end-to-end through the change-order service (storage + validation integration).
7. CO approval smoke -- regression guard for the rename in the approval flow
   (deferred to a documented skip stub; covered by #6).

SELF-CLEANUP: the ``db`` fixture COMMITS at teardown (conftest.py line 100-101)
so every persistent row created here MUST be removed via an
``async_session_maker()`` session in a ``finally`` block, or dev-DB junk
accumulates (memory note 35).
"""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.branching.commands import (
    CreateBranchCommand,
    MergeBranchCommand,
    UpdateCommand,
)
from app.core.branching.service import BranchableService
from app.core.versioning.commands import (
    CreateVersionCommand,
    UpdateVersionCommand,
)
from app.db.session import async_session_maker
from app.models.domain.change_order import ChangeOrder
from app.models.domain.custom_entity_template import CustomEntityTemplate
from app.models.domain.project import Project
from app.services.custom_field_service import CustomFieldService
from tests.factories import create_test_project

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


# ===========================================================================
# (1) RAW-INSERT PATH A -- UpdateCommand custom_fields round-trip
# ===========================================================================


class TestRawInsertPathCustomFields:
    """Path A: custom_fields dict survives the branching UpdateCommand raw-INSERT."""

    @pytest.mark.asyncio
    async def test_update_command_persists_custom_fields(
        self, db: AsyncSession, actor_id: UUID
    ) -> None:
        """A custom_fields dict round-trips through UpdateCommand on Project.

        UpdateCommand (branching) builds a raw INSERT (commands.py ~line 341).
        JSONB columns whose value ``isinstance(values[col], dict)`` are
        serialized via json.dumps (line 352); this asserts the dict is restored
        on readback.
        """
        project = await create_test_project(
            db, actor_id, name="CF-A", custom_fields={"seismic_area": "2"}
        )
        await db.commit()
        root_id = project.project_id

        try:
            update_cmd = UpdateCommand(
                entity_class=Project,
                root_id=root_id,
                actor_id=actor_id,
                updates={"custom_fields": {"seismic_area": "3", "priority": "high"}},
                branch="main",
            )
            await update_cmd.execute(db)
            await db.commit()

            # Re-fetch the current version via the service (raw-INSERT bypasses
            # the ORM identity map, so refresh on the stale object is unreliable).
            service = BranchableService(Project, db)
            current = await service.get_as_of(root_id)
            assert current is not None
            assert current.custom_fields == {"seismic_area": "3", "priority": "high"}
        finally:
            await _cleanup("projects", "project_id", root_id)


# ===========================================================================
# (2) ORM-FLUSH PATH B -- CreateBranch + Merge custom_fields round-trip
# ===========================================================================


class TestOrmFlushPathCustomFields:
    """Path B: custom_fields dict survives the branch clone() + merge flow."""

    @pytest.mark.asyncio
    async def test_branch_and_merge_preserve_custom_fields(
        self, db: AsyncSession, actor_id: UUID
    ) -> None:
        """custom_fields edited on a CO branch surface on main after merge.

        CreateBranchCommand.clone(), UpdateCommand.clone(), and
        MergeBranchCommand.clone() each copy the entity's attributes (incl.
        custom_fields) onto a new version. This asserts the NEW custom_fields
        value edited on the branch is what lands on main post-merge.
        """
        project = await create_test_project(
            db,
            actor_id,
            name="CF-B",
            custom_fields={"region": "EU"},
        )
        await db.commit()
        root_id = project.project_id

        try:
            # 1. Create the branch (clones the main version onto BR-CF).
            await CreateBranchCommand(
                entity_class=Project,
                root_id=root_id,
                actor_id=actor_id,
                new_branch="BR-CF",
            ).execute(db)
            await db.commit()

            # 2. Edit custom_fields on the branch.
            await UpdateCommand(
                entity_class=Project,
                root_id=root_id,
                actor_id=actor_id,
                updates={"custom_fields": {"region": "US", "tier": "gold"}},
                branch="BR-CF",
            ).execute(db)
            await db.commit()

            # 3. Merge back to main.
            await MergeBranchCommand(
                entity_class=Project,
                root_id=root_id,
                actor_id=actor_id,
                source_branch="BR-CF",
                target_branch="main",
            ).execute(db)
            await db.commit()

            service = BranchableService(Project, db)
            merged = await service.get_as_of(root_id)
            assert merged is not None
            assert merged.branch == "main"
            assert merged.custom_fields == {"region": "US", "tier": "gold"}
        finally:
            await _cleanup("projects", "project_id", root_id)


# ===========================================================================
# (3) M12 -- Versionable dict JSONB (field_definitions) round-trip
# ===========================================================================


class TestVersionableDictJsonb:
    """field_definitions (dict JSONB NOT NULL) round-trips on CustomEntityTemplate.

    CustomEntityTemplate is a Versionable (NOT Branchable) entity, so this
    exercises CreateVersionCommand + UpdateVersionCommand (the versioning core's
    own raw-INSERT path at commands.py ~line 353-357), not the branching
    commands. The dict-typed JSONB guard is the same, so this proves the
    versioning path serializes field_definitions correctly.
    """

    @pytest.mark.asyncio
    async def test_field_definitions_round_trip_through_versioning_commands(
        self, db: AsyncSession, actor_id: UUID
    ) -> None:
        root_id = uuid4()
        org_unit = uuid4()

        try:
            create_cmd = CreateVersionCommand(
                entity_class=CustomEntityTemplate,
                root_id=root_id,
                actor_id=actor_id,
                organizational_unit_id=org_unit,
                target_entity_type="PROJECT",
                code="T1",
                name="T",
                field_definitions={"a": {"type": "text", "label": "A"}},
            )
            created = await create_cmd.execute(db)
            await db.commit()
            assert created.field_definitions == {"a": {"type": "text", "label": "A"}}

            update_cmd = UpdateVersionCommand(
                entity_class=CustomEntityTemplate,
                root_id=root_id,
                actor_id=actor_id,
                field_definitions={
                    "a": {"type": "text", "label": "A", "required": True},
                    "b": {"type": "select", "label": "B", "options": ["x", "y"]},
                },
            )
            await update_cmd.execute(db)
            await db.commit()

            # Re-read the current version from the DB.
            stmt = (
                select(CustomEntityTemplate)
                .where(
                    CustomEntityTemplate.custom_entity_template_id == root_id,
                    text("upper(valid_time) IS NULL AND deleted_at IS NULL"),
                )
                .limit(1)
            )
            updated = (await db.execute(stmt)).scalar_one()
            assert updated.field_definitions == {
                "a": {"type": "text", "label": "A", "required": True},
                "b": {"type": "select", "label": "B", "options": ["x", "y"]},
            }
        finally:
            await _cleanup(
                "custom_entity_templates", "custom_entity_template_id", root_id
            )


# ===========================================================================
# (4) C1 ENFORCEMENT -- unique partial index (deterministic)
# ===========================================================================


class TestC1UniquePartialIndex:
    """C1: the unique partial index rejects a 2nd open current version per (root, branch).

    A single project has one open-ended (current) version on 'main'. Inserting
    a SECOND row for the same (project_id, 'main') with an open valid_time MUST
    raise IntegrityError with sqlstate '23505' (unique_violation). This proves
    the index enforces one-current-version-per-(root,branch) -- the contract the
    analysis (memory note 44, v4 C1) substituted for the withdrawn v3 TOCTOU.
    """

    @pytest.mark.asyncio
    async def test_second_open_current_version_rejected(
        self, db: AsyncSession, actor_id: UUID
    ) -> None:
        project = await create_test_project(db, actor_id, name="CF-C1")
        await db.commit()
        root_id = project.project_id

        try:
            # Mirror the minimal NOT NULL columns the projects table requires.
            # id + project_id + branch + valid_time + transaction_time + created_by
            # are the load-bearing ones for the versioning row + the C1 index.
            dup_sql = text(
                """
                INSERT INTO projects
                    (id, project_id, branch, name, code, status, currency,
                     created_by, valid_time, transaction_time)
                VALUES
                    (:id, :rid, 'main', 'CF-C1-DUP', 'CF-C1-DUP', 'active', 'EUR',
                     :actor,
                     tstzrange(clock_timestamp(), NULL, '[]'),
                     tstzrange(clock_timestamp(), NULL, '[]'))
                """
            )
            with pytest.raises(IntegrityError) as exc_info:
                await db.execute(
                    dup_sql,
                    {"id": uuid4(), "rid": root_id, "actor": actor_id},
                )
                await db.commit()

            # The Postgres unique_violation sqlstate is 23505. asyncpg surfaces
            # it on the .orig wrapper as ``sqlstate``.
            orig = getattr(exc_info.value.orig, "sqlstate", None)
            assert orig == "23505", (
                f"Expected sqlstate 23505 (unique_violation) from the C1 index, "
                f"got {orig!r}: {exc_info.value.orig!r}"
            )

            # Roll back the failed statement so the db fixture's teardown commit
            # does not re-raise the aborted transaction.
            await db.rollback()
        finally:
            await _cleanup("projects", "project_id", root_id)


# ===========================================================================
# (5) CUSTOM FIELD VALIDATION -- pure unit on the service chokepoint
# ===========================================================================


class TestCustomFieldServiceValidation:
    """Pure unit tests for CustomFieldService.validate_field_values.

    These are deterministic: the service is the unified async chokepoint (M1).
    Unknown keys are rejected, required-null is rejected (D11 directive 3), and
    per-type shape checks delegate to the FieldDefinition hierarchy (NumberField
    rejects bool because Python ``True`` is an ``int``).
    """

    DEFINITIONS: dict[str, Any] = {
        "seismic_area": {
            "type": "select",
            "label": "Seismic",
            "options": ["1", "2", "3", "4"],
            "required": True,
        },
        "notes": {"type": "text", "label": "Notes"},
        "height": {"type": "number", "label": "H"},
    }

    @pytest.mark.asyncio
    async def test_valid_values_yield_no_errors(self) -> None:
        errors = await CustomFieldService().validate_field_values(
            self.DEFINITIONS,
            {"seismic_area": "2", "notes": "ok", "height": 10},
        )
        assert errors == []

    @pytest.mark.asyncio
    async def test_unknown_key_rejected(self) -> None:
        errors = await CustomFieldService().validate_field_values(
            self.DEFINITIONS,
            {"seismic_area": "2", "rogue": "x"},
        )
        assert any("rogue" in e for e in errors), errors

    @pytest.mark.asyncio
    async def test_missing_required_rejected(self) -> None:
        errors = await CustomFieldService().validate_field_values(
            self.DEFINITIONS, {"notes": "ok"}
        )
        assert any("Field 'seismic_area' is required" in e for e in errors), errors

    @pytest.mark.asyncio
    async def test_select_out_of_range_rejected(self) -> None:
        errors = await CustomFieldService().validate_field_values(
            self.DEFINITIONS, {"seismic_area": "9"}
        )
        assert any("Seismic" in e for e in errors), errors

    @pytest.mark.asyncio
    async def test_number_rejects_bool(self) -> None:
        """A bool must be rejected for a number field (bool is an int subclass)."""
        errors = await CustomFieldService().validate_field_values(
            self.DEFINITIONS, {"seismic_area": "2", "height": True}
        )
        assert any("H must be a number" in e for e in errors), errors

    @pytest.mark.asyncio
    async def test_malformed_spec_missing_type_is_validation_error(self) -> None:
        """A field spec missing 'type' surfaces as a validation error, not a 500.

        Hardening (Fix B): the registry's build_field uses guarded access and
        raises ValueError on a missing 'type', which the service chokepoint
        catches and turns into a returned error string. No KeyError leaks.
        """
        errors = await CustomFieldService().validate_field_values(
            {"bad": {"label": "X"}}, {}
        )
        assert isinstance(errors, list)
        assert any("type" in e for e in errors), errors

    @pytest.mark.asyncio
    async def test_select_without_options_is_validation_error(self) -> None:
        """A select field whose spec lacks 'options' surfaces as a validation error.

        Hardening (Fix B): SelectField.validate uses guarded access and returns a
        'no configured options' message instead of raising KeyError on
        self.config["options"]. No 500.
        """
        errors = await CustomFieldService().validate_field_values(
            {"priority": {"type": "select", "label": "P"}}, {"priority": "x"}
        )
        assert isinstance(errors, list)
        assert any("no configured options" in e for e in errors), errors


# ===========================================================================
# (6) CO PLUMBING -- rename custom_field_values -> custom_fields end-to-end
# ===========================================================================


async def _delete_co_templates_for_change_order() -> None:
    """Remove all CHANGE_ORDER templates so the validation integration case
    has a clean slate to seed its own. The startup seeder
    (seed_default_custom_templates) recreates the default on next start, so
    deleting here is safe for the dev DB."""
    async with async_session_maker() as s:
        await s.execute(
            text(
                "DELETE FROM custom_entity_templates "
                "WHERE target_entity_type = 'CHANGE_ORDER'"
            )
        )
        await s.commit()


async def _co_template_count() -> int:
    async with async_session_maker() as s:
        row = (
            await s.execute(
                text(
                    "SELECT count(*) FROM custom_entity_templates "
                    "WHERE target_entity_type = 'CHANGE_ORDER'"
                )
            )
        ).scalar_one()
        return int(row)


class TestChangeOrderCustomFieldsPlumbing:
    """Verify the rename custom_field_values -> custom_fields works CO-wide.

    Because ``_validate_custom_fields`` returns early when no CHANGE_ORDER
    template is found (change_order_service.py ~line 1996-1998), creating a CO
    with arbitrary custom_fields stores them as-is. This is the storage half of
    the rename regression. The validation-integration half seeds its own
    template and asserts a bad value raises.
    """

    @pytest.mark.asyncio
    async def test_co_stores_custom_fields_via_createversion(
        self, db: AsyncSession, actor_id: UUID
    ) -> None:
        """Direct CreateVersionCommand on ChangeOrder stores + reads custom_fields.

        Avoids the CO service's impact-analysis / matrix / branch-creation
        machinery (which is the subject of test 7's deferred e2e) and isolates
        the rename: the field is named ``custom_fields`` and round-trips.
        """
        project = await create_test_project(db, actor_id)
        await db.commit()

        co_id = uuid4()
        try:
            cmd = CreateVersionCommand(
                entity_class=ChangeOrder,
                root_id=co_id,
                actor_id=actor_id,
                branch="main",
                code=f"CO-CF-{co_id.hex[:6].upper()}",
                project_id=project.project_id,
                title="CF plumbing CO",
                status="draft",
                custom_fields={"reason": "x"},
            )
            co = await cmd.execute(db)
            await db.commit()

            assert co.custom_fields == {"reason": "x"}
            assert hasattr(co, "custom_fields")
            assert not hasattr(co, "custom_field_values")
        finally:
            await _cleanup("change_orders", "change_order_id", co_id)
            await _cleanup("projects", "project_id", project.project_id)

    @pytest.mark.asyncio
    async def test_co_validation_rejects_bad_custom_field(
        self, db: AsyncSession, actor_id: UUID
    ) -> None:
        """Seeding a CHANGE_ORDER template makes _validate_custom_fields reject
        an out-of-range select value via the service chokepoint.

        Uses the CO service create path so the validation hook fires (the direct
        CreateVersionCommand path above bypasses it on purpose).
        """
        from app.models.domain.custom_entity_template import CustomEntityTemplate
        from app.models.schemas.change_order import ChangeOrderCreate
        from app.services.change_order_service import ChangeOrderService

        # 1. Clean slate: remove any pre-existing CHANGE_ORDER templates.
        await _delete_co_templates_for_change_order()

        template_root = uuid4()
        project = await create_test_project(db, actor_id)
        await db.commit()
        co_id_holder: set[UUID] = set()

        try:
            # 2. Seed our own template with a single select field.
            db.add(
                CustomEntityTemplate(
                    custom_entity_template_id=template_root,
                    organizational_unit_id=uuid4(),
                    target_entity_type="CHANGE_ORDER",
                    code="test-co-tpl",
                    name="Test CO Template",
                    field_definitions={
                        "priority": {
                            "type": "select",
                            "label": "P",
                            "options": ["low", "high"],
                        }
                    },
                    created_by=actor_id,
                )
            )
            await db.commit()

            # 3. Create a CO with an INVALID select value -> must raise.
            service = ChangeOrderService(db)
            co_in = ChangeOrderCreate(
                code=f"CO-VAL-{uuid4().hex[:6].upper()}",
                project_id=project.project_id,
                title="CF validation CO",
                custom_fields={"priority": "INVALID"},
            )
            with pytest.raises(ValueError, match="Custom field validation failed"):
                co = await service.create_change_order(co_in, actor_id)
                # Capture any row that slipped through so cleanup runs.
                co_id_holder.add(co.change_order_id)

            # No CO should have been persisted (create_root runs after validate).
        finally:
            # Best-effort cleanup of any stray CO + the template + project.
            await _cleanup_by_ids("change_orders", "change_order_id", co_id_holder)
            await _cleanup(
                "custom_entity_templates",
                "custom_entity_template_id",
                template_root,
            )
            await _cleanup("projects", "project_id", project.project_id)


# ===========================================================================
# (7) CO APPROVAL SMOKE -- deferred to a documented stub
# ===========================================================================


class TestChangeOrderApprovalSmoke:
    """Regression guard for the rename in the CO approval flow.

    ``submit_for_approval`` (change_order_service.py ~line 1093) is too coupled
    to set up deterministically in a Phase 0 battery: it requires an isolation
    branch (``branch_name``), a seeded impact matrix
    (``ChangeOrderWorkflowConfig`` + ``co_impact_level_config`` rows), a passing
    ``_run_impact_analysis`` (compares main vs branch), and
    ``ControlDateValidator.validate_control_date_sequence``. Stubbed here and
    tracked as a follow-up; the rename's storage half is already covered by the
    CO plumbing tests above (CreateVersionCommand + the validation integration
    case both read back ``custom_fields``).
    """

    @pytest.mark.skip(
        reason=(
            "submit_for_approval depends on branch isolation + impact matrix + "
            "ControlDateValidator sequence; too coupled for a deterministic "
            "Phase 0 battery. The custom_fields rename is verified end-to-end by "
            "TestChangeOrderCustomFieldsPlumbing (storage + validation paths). "
            "Follow-up: add an approval e2e once the matrix seeder is "
            "deterministic."
        )
    )
    @pytest.mark.asyncio
    async def test_submit_for_approval_status_transition(
        self, db: AsyncSession, actor_id: UUID
    ) -> None:
        # Intentionally empty: see the skip reason above.
        # A working e2e would: seed co_workflow_config + impact level rows,
        # create a CO (with custom_fields), create the BR-{code} branch,
        # run service.submit_for_approval, and assert co.status ==
        # SUBMITTED_FOR_APPROVAL.
        raise NotImplementedError("deferred -- see skip reason")
