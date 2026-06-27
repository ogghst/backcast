"""Phase 3 battery: merge fidelity + per-field lifecycle write/AI gate.

Exercises the two Phase-3 concerns of the custom-fields initiative
(memory note 44, Phase 3):

1. **3B write gate (M2 — status authority).** ``CustomFieldService.validate_field_values``
   honours a ``live_statuses`` override so a field an admin DEPRECATES or
   RETIRES today rejects writes on EXISTING entities whose captured snapshot
   still says ``active``. The snapshot column is NEVER mutated; the gate reads
   the LIVE template status. ``prepare_for_update`` resolves the live template
   and threads the status map through; ``prepare_for_create`` does not (the
   snapshot captured at create already reflects the live template).
2. **AI gate.** ``filter_ai_visible_custom_fields`` and
   ``ai_visible_field_manifest`` exclude RETIRED fields entirely and surface
   DEPRECATED ones with ``status="deprecated"`` (readable data + a hint the LLM
   must not set them).

The 3A JSONB merge diff is covered in ``tests/core/test_branching_core.py``
(it needs the full branching service + a real divergence point).

SELF-CLEANUP: the ``db`` fixture COMMITS at teardown (conftest.py line 100-101)
so every persistent row created here MUST be removed via an
``async_session_maker()`` session in a ``finally`` block (memory note 35).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.tools.custom_fields_helpers import (
    ai_visible_field_manifest,
    filter_ai_visible_custom_fields,
)
from app.db.session import async_session_maker
from app.models.domain.custom_entity_template import CustomEntityTemplate
from app.services.custom_field_service import (
    CustomFieldService,
    CustomFieldValidationError,
)

# ---------------------------------------------------------------------------
# Self-cleanup helpers (memory note 35: db fixture COMMITS at teardown).
# ---------------------------------------------------------------------------


async def _cleanup_templates(root_ids: set[UUID]) -> None:
    if not root_ids:
        return
    async with async_session_maker() as s:
        await s.execute(
            text(
                "DELETE FROM custom_entity_templates "
                "WHERE custom_entity_template_id = ANY(:ids)"
            ),
            {"ids": list(root_ids)},
        )
        await s.commit()


async def _seed_template(
    db: AsyncSession,
    *,
    field_definitions: dict[str, Any],
    actor_id: UUID,
) -> UUID:
    """Insert a CURRENT CustomEntityTemplate row and return its root id.

    A single root id is reused for every version we want to simulate on it
    (the deprecation/retirement is a NEW current version of the SAME root).
    """
    root_id = uuid4()
    db.add(
        CustomEntityTemplate(
            custom_entity_template_id=root_id,
            organizational_unit_id=uuid4(),
            target_entity_type="PROJECT",
            code=f"TPL-{root_id.hex[:6].upper()}",
            name=f"Phase3 template {root_id.hex[:6]}",
            field_definitions=field_definitions,
            created_by=actor_id,
        )
    )
    await db.commit()
    return root_id


async def _supersede_template(
    db: AsyncSession,
    *,
    root_id: UUID,
    field_definitions: dict[str, Any],
    actor_id: UUID,
) -> None:
    """Close the existing current version and open a new one for ``root_id``.

    Simulates an admin editing the live template (e.g. deprecating a field):
    the previous current version gets its ``valid_time`` upper-bound set, and a
    new current version with the updated ``field_definitions`` is inserted.
    Both share the same ``custom_entity_template_id`` (root id).

    Raw SQL is used for the upper-bound because building the tstzrange
    expression through the ORM column property is fragile; the table name +
    predicate mirror the migration's C1 partial-index definition.
    """
    await db.execute(
        text(
            "UPDATE custom_entity_templates "
            "SET valid_time = tstzrange(lower(valid_time), now()) "
            "WHERE custom_entity_template_id = :rid "
            "AND upper(valid_time) IS NULL AND deleted_at IS NULL"
        ),
        {"rid": root_id},
    )
    db.add(
        CustomEntityTemplate(
            custom_entity_template_id=root_id,
            organizational_unit_id=uuid4(),
            target_entity_type="PROJECT",
            code=f"TPL-{root_id.hex[:6].upper()}",
            name=f"Phase3 template {root_id.hex[:6]}",
            field_definitions=field_definitions,
            created_by=actor_id,
        )
    )
    await db.commit()


# ===========================================================================
# 3B write gate (M2): live-status authority
# ===========================================================================


class TestLiveStatusWriteGate:
    """``validate_field_values`` + ``prepare_for_update`` live-status gate."""

    @pytest.mark.asyncio
    async def test_update_rejects_setting_deprecated_field(
        self, db: AsyncSession, actor_id: UUID
    ) -> None:
        """An update that SETS a now-deprecated field is rejected (M2).

        Scenario: entity created with an ``active`` field bound; admin then
        deprecates the field on the LIVE template; a subsequent update that
        SETS the field is rejected with "field '<code>' is deprecated".
        """
        tpl_root = await _seed_template(
            db,
            field_definitions={
                "risk": {"type": "text", "label": "Risk", "status": "active"}
            },
            actor_id=actor_id,
        )
        try:
            svc = CustomFieldService(db)
            # First-time binding UPDATE: snapshot captured from the live (active) template.
            upd = await svc.prepare_for_update(
                current_template_root_id=None,
                incoming_template_root_id=tpl_root,
                current_snapshot=None,
                custom_fields={"risk": "high"},
                actor_id=actor_id,
            )
            assert upd["custom_fields"] == {"risk": "high"}

            # Admin deprecates the field on the LIVE template.
            await _supersede_template(
                db,
                root_id=tpl_root,
                field_definitions={
                    "risk": {
                        "type": "text",
                        "label": "Risk",
                        "status": "deprecated",
                    }
                },
                actor_id=actor_id,
            )

            # A subsequent UPDATE that SETS the deprecated field is rejected.
            # The snapshot captured at bind time still says "active"; the LIVE
            # status (deprecated) governs the write gate.
            snapshot_at_bind = {
                "risk": {"type": "text", "label": "Risk", "status": "active"}
            }
            with pytest.raises(CustomFieldValidationError) as ei:
                await svc.prepare_for_update(
                    current_template_root_id=tpl_root,
                    incoming_template_root_id=tpl_root,
                    current_snapshot=snapshot_at_bind,
                    custom_fields={"risk": "medium"},
                    actor_id=actor_id,
                )
            assert "field 'risk' is deprecated" in str(ei.value)
        finally:
            await _cleanup_templates({tpl_root})

    @pytest.mark.asyncio
    async def test_update_allows_omitting_deprecated_field(
        self, db: AsyncSession, actor_id: UUID
    ) -> None:
        """An update that OMITS the deprecated field is allowed (M2).

        Deprecation forbids SETTING the field, not editing the entity. An
        update payload that does not include the deprecated code passes.
        """
        tpl_root = await _seed_template(
            db,
            field_definitions={
                "risk": {"type": "text", "label": "Risk", "status": "active"},
                "note": {"type": "text", "label": "Note", "status": "active"},
            },
            actor_id=actor_id,
        )
        try:
            svc = CustomFieldService(db)
            await svc.prepare_for_update(
                current_template_root_id=None,
                incoming_template_root_id=tpl_root,
                current_snapshot=None,
                custom_fields={"risk": "high", "note": "x"},
                actor_id=actor_id,
            )

            # Deprecate only ``risk``; ``note`` stays active.
            await _supersede_template(
                db,
                root_id=tpl_root,
                field_definitions={
                    "risk": {
                        "type": "text",
                        "label": "Risk",
                        "status": "deprecated",
                    },
                    "note": {"type": "text", "label": "Note", "status": "active"},
                },
                actor_id=actor_id,
            )

            snapshot_at_bind = {
                "risk": {"type": "text", "label": "Risk", "status": "active"},
                "note": {"type": "text", "label": "Note", "status": "active"},
            }
            # Omitting ``risk`` (only setting ``note``) is allowed.
            upd = await svc.prepare_for_update(
                current_template_root_id=tpl_root,
                incoming_template_root_id=tpl_root,
                current_snapshot=snapshot_at_bind,
                custom_fields={"note": "y"},
                actor_id=actor_id,
            )
            assert upd["custom_fields"] == {"note": "y"}
        finally:
            await _cleanup_templates({tpl_root})

    @pytest.mark.asyncio
    async def test_update_allows_unchanged_deprecated_field_echoed(
        self, db: AsyncSession, actor_id: UUID
    ) -> None:
        """An update that ECHOES the deprecated field unchanged is allowed.

        Regression guard for the D11 whole-map-replace echo bug: the frontend
        edit form submits the ENTIRE ``custom_fields`` dict, including locked
        deprecated/retired fields rendered read-only at their CURRENT stored
        value. A presence-based gate rejected any such edit; the change-based
        gate (``stored_custom_fields`` threaded through) permits the echo and
        only rejects a genuine change. Here an UNRELATED active field (``note``)
        is changed while the deprecated ``risk`` is echoed at its stored value
        → the update SUCCEEDS and ``note`` is updated.
        """
        tpl_root = await _seed_template(
            db,
            field_definitions={
                "risk": {"type": "text", "label": "Risk", "status": "active"},
                "note": {"type": "text", "label": "Note", "status": "active"},
            },
            actor_id=actor_id,
        )
        try:
            svc = CustomFieldService(db)
            # First-time binding: store both fields.
            await svc.prepare_for_update(
                current_template_root_id=None,
                incoming_template_root_id=tpl_root,
                current_snapshot=None,
                custom_fields={"risk": "high", "note": "x"},
                actor_id=actor_id,
            )

            # Admin deprecates ``risk`` on the LIVE template; ``note`` active.
            await _supersede_template(
                db,
                root_id=tpl_root,
                field_definitions={
                    "risk": {
                        "type": "text",
                        "label": "Risk",
                        "status": "deprecated",
                    },
                    "note": {"type": "text", "label": "Note", "status": "active"},
                },
                actor_id=actor_id,
            )

            snapshot_at_bind = {
                "risk": {"type": "text", "label": "Risk", "status": "active"},
                "note": {"type": "text", "label": "Note", "status": "active"},
            }
            # Echo ``risk`` UNCHANGED at its stored value ("high") while
            # CHANGING ``note``. The deprecated echo must NOT block the edit.
            stored = {"risk": "high", "note": "x"}
            upd = await svc.prepare_for_update(
                current_template_root_id=tpl_root,
                incoming_template_root_id=tpl_root,
                current_snapshot=snapshot_at_bind,
                custom_fields={"risk": "high", "note": "changed"},
                actor_id=actor_id,
                stored_custom_fields=stored,
            )
            assert upd["custom_fields"] == {"risk": "high", "note": "changed"}
        finally:
            await _cleanup_templates({tpl_root})

    @pytest.mark.asyncio
    async def test_update_rejects_changing_deprecated_field(
        self, db: AsyncSession, actor_id: UUID
    ) -> None:
        """An update that CHANGES the deprecated field is still rejected.

        Counterpart to the echo test: echoing unchanged is allowed, but
        CHANGING the deprecated field's value is rejected with "field '<code>'
        is deprecated". Confirms the gate is change-based, not absent.
        """
        tpl_root = await _seed_template(
            db,
            field_definitions={
                "risk": {"type": "text", "label": "Risk", "status": "active"},
                "note": {"type": "text", "label": "Note", "status": "active"},
            },
            actor_id=actor_id,
        )
        try:
            svc = CustomFieldService(db)
            await svc.prepare_for_update(
                current_template_root_id=None,
                incoming_template_root_id=tpl_root,
                current_snapshot=None,
                custom_fields={"risk": "high", "note": "x"},
                actor_id=actor_id,
            )

            await _supersede_template(
                db,
                root_id=tpl_root,
                field_definitions={
                    "risk": {
                        "type": "text",
                        "label": "Risk",
                        "status": "deprecated",
                    },
                    "note": {"type": "text", "label": "Note", "status": "active"},
                },
                actor_id=actor_id,
            )

            snapshot_at_bind = {
                "risk": {"type": "text", "label": "Risk", "status": "active"},
                "note": {"type": "text", "label": "Note", "status": "active"},
            }
            stored = {"risk": "high", "note": "x"}
            # CHANGING ``risk`` (high → critical) is rejected even though
            # ``stored_custom_fields`` is supplied (change-based gate fires).
            with pytest.raises(CustomFieldValidationError) as ei:
                await svc.prepare_for_update(
                    current_template_root_id=tpl_root,
                    incoming_template_root_id=tpl_root,
                    current_snapshot=snapshot_at_bind,
                    custom_fields={"risk": "critical", "note": "changed"},
                    actor_id=actor_id,
                    stored_custom_fields=stored,
                )
            assert "field 'risk' is deprecated" in str(ei.value)
        finally:
            await _cleanup_templates({tpl_root})

    @pytest.mark.asyncio
    async def test_update_rejects_setting_retired_field(
        self, db: AsyncSession, actor_id: UUID
    ) -> None:
        """A retired field set on update is rejected (M2)."""
        tpl_root = await _seed_template(
            db,
            field_definitions={
                "legacy": {"type": "text", "label": "Legacy", "status": "active"}
            },
            actor_id=actor_id,
        )
        try:
            svc = CustomFieldService(db)
            await svc.prepare_for_update(
                current_template_root_id=None,
                incoming_template_root_id=tpl_root,
                current_snapshot=None,
                custom_fields={"legacy": "v1"},
                actor_id=actor_id,
            )

            await _supersede_template(
                db,
                root_id=tpl_root,
                field_definitions={
                    "legacy": {
                        "type": "text",
                        "label": "Legacy",
                        "status": "retired",
                    }
                },
                actor_id=actor_id,
            )

            snapshot_at_bind = {
                "legacy": {"type": "text", "label": "Legacy", "status": "active"}
            }
            with pytest.raises(CustomFieldValidationError) as ei:
                await svc.prepare_for_update(
                    current_template_root_id=tpl_root,
                    incoming_template_root_id=tpl_root,
                    current_snapshot=snapshot_at_bind,
                    custom_fields={"legacy": "v2"},
                    actor_id=actor_id,
                )
            assert "field 'legacy' is retired" in str(ei.value)
        finally:
            await _cleanup_templates({tpl_root})

    @pytest.mark.asyncio
    async def test_update_allows_setting_active_field(
        self, db: AsyncSession, actor_id: UUID
    ) -> None:
        """An active field is set normally (no gate interference)."""
        tpl_root = await _seed_template(
            db,
            field_definitions={
                "region": {
                    "type": "select",
                    "label": "Region",
                    "options": ["EU", "US"],
                    "status": "active",
                }
            },
            actor_id=actor_id,
        )
        try:
            svc = CustomFieldService(db)
            snapshot = {
                "region": {
                    "type": "select",
                    "label": "Region",
                    "options": ["EU", "US"],
                    "status": "active",
                }
            }
            upd = await svc.prepare_for_update(
                current_template_root_id=tpl_root,
                incoming_template_root_id=tpl_root,
                current_snapshot=snapshot,
                custom_fields={"region": "EU"},
                actor_id=actor_id,
            )
            assert upd["custom_fields"] == {"region": "EU"}
        finally:
            await _cleanup_templates({tpl_root})

    @pytest.mark.asyncio
    async def test_create_rejects_setting_deprecated_field(
        self, db: AsyncSession, actor_id: UUID
    ) -> None:
        """Create against a live template with a deprecated field is rejected.

        On CREATE the snapshot is captured from the live template, so the spec
        itself already carries ``status="deprecated"``; the gate fires via the
        snapshot status (``live_statuses=None``).
        """
        tpl_root = await _seed_template(
            db,
            field_definitions={
                "old": {
                    "type": "text",
                    "label": "Old",
                    "status": "deprecated",
                }
            },
            actor_id=actor_id,
        )
        try:
            svc = CustomFieldService(db)
            with pytest.raises(CustomFieldValidationError) as ei:
                await svc.prepare_for_create(
                    template_root_id=tpl_root,
                    custom_fields={"old": "x"},
                    actor_id=actor_id,
                )
            assert "field 'old' is deprecated" in str(ei.value)
        finally:
            await _cleanup_templates({tpl_root})

    @pytest.mark.asyncio
    async def test_update_falls_back_when_live_template_missing(
        self, db: AsyncSession, actor_id: UUID
    ) -> None:
        """If the live template is unresolvable, the gate falls back to snapshot.

        The entity's binding points at a root id whose current version was
        deleted; ``prepare_for_update`` must NOT hard-fail — it falls back to
        ``live_statuses=None`` and uses the snapshot status verbatim.
        """
        # Seed then immediately soft-delete the only current version.
        tpl_root = await _seed_template(
            db,
            field_definitions={"k": {"type": "text", "label": "K", "status": "active"}},
            actor_id=actor_id,
        )
        try:
            await db.execute(
                update(CustomEntityTemplate)
                .where(
                    CustomEntityTemplate.custom_entity_template_id == tpl_root,
                )
                .values(deleted_at=datetime.now(UTC))
            )
            await db.commit()

            svc = CustomFieldService(db)
            snapshot = {"k": {"type": "text", "label": "K", "status": "active"}}
            # No hard failure; the active snapshot status governs (allowed).
            upd = await svc.prepare_for_update(
                current_template_root_id=tpl_root,
                incoming_template_root_id=tpl_root,
                current_snapshot=snapshot,
                custom_fields={"k": "v"},
                actor_id=actor_id,
            )
            assert upd["custom_fields"] == {"k": "v"}
        finally:
            await _cleanup_templates({tpl_root})


# ===========================================================================
# AI gate: filter_ai_visible_custom_fields + ai_visible_field_manifest
# ===========================================================================


class TestAIGateStatus:
    """The AI visibility helpers honour the per-field lifecycle status."""

    def test_filter_excludes_retired_keeps_deprecated(self) -> None:
        """Retired fields never reach the LLM; deprecated stay readable."""
        snapshot = {
            "live": {"type": "text", "label": "Live", "ai_visible": True},
            "dep": {
                "type": "text",
                "label": "Dep",
                "ai_visible": True,
                "status": "deprecated",
            },
            "dead": {
                "type": "text",
                "label": "Dead",
                "ai_visible": True,
                "status": "retired",
            },
            "hidden": {"type": "text", "label": "Hidden"},  # not ai_visible
        }
        values = {"live": "a", "dep": "b", "dead": "c", "hidden": "z"}
        surfaced = filter_ai_visible_custom_fields(values, snapshot)
        assert "live" in surfaced
        assert "dep" in surfaced  # deprecated stays readable
        assert "dead" not in surfaced  # retired never surfaced
        assert "hidden" not in surfaced  # not ai_visible

    def test_manifest_includes_status_and_excludes_retired(self) -> None:
        """Manifest carries ``status`` and omits retired entries entirely."""
        snapshot = {
            "live": {
                "type": "text",
                "label": "Live",
                "ai_visible": True,
                "required": True,
            },
            "dep": {
                "type": "select",
                "label": "Dep",
                "options": ["x", "y"],
                "ai_visible": True,
                "status": "deprecated",
            },
            "dead": {
                "type": "text",
                "label": "Dead",
                "ai_visible": True,
                "status": "retired",
            },
        }
        manifest = ai_visible_field_manifest(snapshot)
        codes = {entry["code"]: entry for entry in manifest}
        assert set(codes) == {"live", "dep"}  # retired excluded
        assert codes["live"]["status"] == "active"  # default applied
        assert codes["live"]["required"] is True
        assert codes["dep"]["status"] == "deprecated"
        assert codes["dep"]["type"] == "select"

    def test_manifest_empty_when_all_retired(self) -> None:
        """A snapshot of only retired ai_visible fields yields an empty manifest."""
        snapshot = {
            "dead": {
                "type": "text",
                "label": "Dead",
                "ai_visible": True,
                "status": "retired",
            }
        }
        assert ai_visible_field_manifest(snapshot) == []
