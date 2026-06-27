"""Tests for surfacing custom_fields to the AI assistant (Phase 1E, D8).

Covers:
  (a) the ``filter_ai_visible_custom_fields`` / ``ai_visible_field_manifest``
      helpers (D8 gate — only ai_visible fields; empty when no snapshot);
  (b) ``get_project`` includes ai_visible custom_fields and EXCLUDES a
      non-ai_visible field;
  (c) ``list_projects`` omits custom_fields when include_custom_fields=False;
  (d) ``create_project`` passes custom_fields + custom_entity_template_root_id
      through to the service payload (validation is the service's job — mocked).
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.ai.tools.custom_fields_helpers import (
    ai_visible_field_manifest,
    filter_ai_visible_custom_fields,
)
from app.ai.tools.project_tools import get_project, list_projects
from app.ai.tools.templates.project_template import create_project
from app.ai.tools.types import ToolContext

# ``@ai_tool`` replaces the module names with LangChain ``StructuredTool``
# instances whose ``.coroutine`` is the decorator's session-managing wrapper.
# ``__wrapped__`` is the original async function with no session side effects.
_get_project_raw = get_project.coroutine.__wrapped__  # type: ignore[attr-defined]
_list_projects_raw = list_projects.coroutine.__wrapped__  # type: ignore[attr-defined]
_create_project_raw = create_project.coroutine.__wrapped__  # type: ignore[attr-defined]


# =============================================================================
# (a) ai_visible filter helper (the D8 chokepoint)
# =============================================================================


def test_filter_surfaces_only_ai_visible_fields() -> None:
    """Only codes whose snapshot spec has ai_visible===True are surfaced."""
    custom_fields = {"public_code": "ABC", "secret": "shhh", "also_public": 42}
    snapshot = {
        "public_code": {"type": "text", "label": "Public", "ai_visible": True},
        "secret": {"type": "text", "label": "Secret", "ai_visible": False},
        "also_public": {"type": "integer", "label": "Also Public", "ai_visible": True},
    }

    surfaced = filter_ai_visible_custom_fields(custom_fields, snapshot)

    assert surfaced == {"public_code": "ABC", "also_public": 42}
    # The non-ai_visible value must NEVER reach the LLM.
    assert "secret" not in surfaced


def test_filter_empty_when_no_snapshot() -> None:
    """Conservative: no snapshot -> nothing surfaced (D8)."""
    assert filter_ai_visible_custom_fields({"x": 1}, None) == {}
    assert filter_ai_visible_custom_fields({"x": 1}, {}) == {}


def test_filter_empty_when_no_values() -> None:
    assert filter_ai_visible_custom_fields(None, {"x": {"ai_visible": True}}) == {}
    assert filter_ai_visible_custom_fields({}, {"x": {"ai_visible": True}}) == {}


def test_filter_orphan_value_without_spec_is_hidden() -> None:
    """A value whose code is absent from the snapshot is not surfaced."""
    snapshot = {"known": {"ai_visible": True}}
    surfaced = filter_ai_visible_custom_fields({"known": "v", "orphan": "v"}, snapshot)
    assert surfaced == {"known": "v"}


def test_filter_missing_ai_visible_key_treated_as_false() -> None:
    """A spec without an explicit ai_visible key defaults hidden (default OFF)."""
    snapshot = {"no_flag": {"type": "text", "label": "No Flag"}}
    surfaced = filter_ai_visible_custom_fields({"no_flag": "v"}, snapshot)
    assert surfaced == {}


def test_manifest_lists_only_ai_visible_labels_sorted() -> None:
    """The discovery manifest hides non-ai_visible labels AND sorts by code."""
    snapshot = {
        "z_field": {"type": "text", "label": "Z", "ai_visible": True, "required": True},
        "hidden": {"type": "text", "label": "Hidden", "ai_visible": False},
        "a_field": {"type": "integer", "label": "A", "ai_visible": True},
    }

    manifest = ai_visible_field_manifest(snapshot)

    assert [f["code"] for f in manifest] == ["a_field", "z_field"]
    assert manifest[0] == {
        "code": "a_field",
        "label": "A",
        "type": "integer",
        "required": False,
    }
    assert manifest[1]["required"] is True
    # Non-ai_visible label must never appear.
    assert "Hidden" not in {f["label"] for f in manifest}


def test_manifest_empty_when_no_snapshot() -> None:
    assert ai_visible_field_manifest(None) == []
    assert ai_visible_field_manifest({}) == []


# =============================================================================
# (b)+(c) get_project / list_projects integration of the helper
# =============================================================================


class _StubProject:
    """Minimal stand-in for a Project ORM row including custom-field columns."""

    def __init__(
        self,
        *,
        project_id: uuid.UUID,
        custom_fields: dict[str, Any] | None,
        snapshot: dict[str, Any] | None,
    ) -> None:
        self.project_id = project_id
        self.code = "AL1"
        self.name = "Automation Line 1"
        self.description = "desc"
        self.status = "ACT"
        self.budget = Decimal("1000000.00")
        self.contract_value = None
        self.currency = "EUR"
        self.start_date = None
        self.end_date = None
        self.branch = "main"
        self.custom_fields = custom_fields
        self.custom_field_definitions_snapshot = snapshot


def _make_context_with_project(stub_project: _StubProject | None) -> ToolContext:
    """ToolContext whose project_service is stubbed to return ``stub_project``."""

    mock_service = MagicMock()
    mock_service.get_as_of = AsyncMock(return_value=stub_project)
    mock_service.get_projects = AsyncMock(
        return_value=([stub_project], 1) if stub_project is not None else ([], 0)
    )

    class _TestContext(ToolContext):
        @property
        def project_service(self) -> Any:  # type: ignore[override]
            return mock_service

    return _TestContext(
        session=MagicMock(),
        user_id="00000000-0000-0000-0000-000000000001",
    )


_SNAPSHOT_WITH_MIXED_VISIBILITY = {
    "public_code": {"type": "text", "label": "Public", "ai_visible": True},
    "secret": {"type": "text", "label": "Secret", "ai_visible": False},
}


@pytest.mark.asyncio
async def test_get_project_includes_ai_visible_and_excludes_hidden() -> None:
    """get_project must surface ai_visible values and hide non-ai_visible ones."""
    pid = uuid.UUID("00000000-0000-0000-0000-0000000000aa")
    stub = _StubProject(
        project_id=pid,
        custom_fields={"public_code": "ABC", "secret": "shhh"},
        snapshot=_SNAPSHOT_WITH_MIXED_VISIBILITY,
    )
    ctx = _make_context_with_project(stub)

    result = await _get_project_raw(project_id=str(pid), context=ctx)

    assert isinstance(result, dict)
    assert "error" not in result, f"unexpected error: {result.get('error')}"
    assert result["custom_fields"] == {"public_code": "ABC"}
    # The hidden field's value must not leak.
    assert "secret" not in result["custom_fields"]


@pytest.mark.asyncio
async def test_get_project_custom_fields_empty_when_no_snapshot() -> None:
    """An entity with no captured snapshot surfaces no custom fields."""
    pid = uuid.UUID("00000000-0000-0000-0000-0000000000bb")
    stub = _StubProject(
        project_id=pid,
        custom_fields={"orphan": "v"},
        snapshot=None,
    )
    ctx = _make_context_with_project(stub)

    result = await _get_project_raw(project_id=str(pid), context=ctx)

    assert "error" not in result
    assert result["custom_fields"] == {}


@pytest.mark.asyncio
async def test_list_projects_omits_custom_fields_when_flag_false() -> None:
    """Default (include_custom_fields=False) keeps custom_fields out of rows."""
    pid = uuid.UUID("00000000-0000-0000-0000-0000000000cc")
    stub = _StubProject(
        project_id=pid,
        custom_fields={"public_code": "ABC"},
        snapshot=_SNAPSHOT_WITH_MIXED_VISIBILITY,
    )
    ctx = _make_context_with_project(stub)

    # list_projects consults RBAC via the unified service + session; patch the
    # two import points so the test stays DB-free and returns the stub project.
    import app.core.rbac_unified as rbac

    unified_mock = MagicMock()
    unified_mock.get_accessible_projects = AsyncMock(return_value=[pid])

    original_get = rbac.get_unified_rbac_service
    original_set = rbac.set_unified_rbac_session
    rbac.get_unified_rbac_service = MagicMock(return_value=unified_mock)  # type: ignore[assignment]
    rbac.set_unified_rbac_session = MagicMock()  # type: ignore[assignment]
    try:
        result = await _list_projects_raw(
            search=None,
            status=None,
            page=1,
            limit=10,
            include_custom_fields=False,
            context=ctx,
        )
    finally:
        rbac.get_unified_rbac_service = original_get  # type: ignore[assignment]
        rbac.set_unified_rbac_session = original_set  # type: ignore[assignment]

    assert isinstance(result, dict)
    assert "error" not in result, f"unexpected error: {result.get('error')}"
    projects = result.get("projects", [])
    assert len(projects) == 1
    # Token-bloat control: custom_fields absent when the flag is False.
    assert "custom_fields" not in projects[0]


@pytest.mark.asyncio
async def test_list_projects_includes_custom_fields_when_flag_true() -> None:
    """include_custom_fields=True surfaces ai_visible fields per row."""
    pid = uuid.UUID("00000000-0000-0000-0000-0000000000dd")
    stub = _StubProject(
        project_id=pid,
        custom_fields={"public_code": "ABC", "secret": "shhh"},
        snapshot=_SNAPSHOT_WITH_MIXED_VISIBILITY,
    )
    ctx = _make_context_with_project(stub)

    import app.core.rbac_unified as rbac

    unified_mock = MagicMock()
    unified_mock.get_accessible_projects = AsyncMock(return_value=[pid])

    original_get = rbac.get_unified_rbac_service
    original_set = rbac.set_unified_rbac_session
    rbac.get_unified_rbac_service = MagicMock(return_value=unified_mock)  # type: ignore[assignment]
    rbac.set_unified_rbac_session = MagicMock()  # type: ignore[assignment]
    try:
        result = await _list_projects_raw(
            search=None,
            status=None,
            page=1,
            limit=10,
            include_custom_fields=True,
            context=ctx,
        )
    finally:
        rbac.get_unified_rbac_service = original_get  # type: ignore[assignment]
        rbac.set_unified_rbac_session = original_set  # type: ignore[assignment]

    assert "error" not in result
    projects = result.get("projects", [])
    assert len(projects) == 1
    assert projects[0]["custom_fields"] == {"public_code": "ABC"}
    assert "secret" not in projects[0]["custom_fields"]


# =============================================================================
# (d) create_project passes custom_fields through to the service payload
# =============================================================================


@pytest.mark.asyncio
async def test_create_project_passes_custom_fields_to_service() -> None:
    """create_project forwards custom_fields + template root id to ProjectCreate.

    Validation/snapshot capture is the service's job (Phase 1C); here we assert
    the AI tool hands the values through unchanged. The service is mocked so no
    DB or template is required.
    """
    captured: dict[str, Any] = {}

    template_root_id = uuid.UUID("00000000-0000-0000-0000-0000000000ee")

    class _CapturingService:
        async def get_by_code(self, code: str) -> None:
            return None  # no duplicate

        async def create_project(self, project_data: Any, actor_id: Any) -> Any:
            captured["custom_fields"] = project_data.custom_fields
            captured["template_root_id"] = project_data.custom_entity_template_root_id

            class _Created:
                project_id = uuid.UUID("00000000-0000-0000-0000-0000000000ff")
                name = project_data.name
                code = project_data.code
                description = project_data.description
                status = "PLN"
                budget = None  # computed at read time; not on ProjectCreate
                custom_fields = project_data.custom_fields
                custom_field_definitions_snapshot = None

            return _Created()

    class _TestContext(ToolContext):
        @property
        def project_service(self) -> Any:  # type: ignore[override]
            return _CapturingService()

    ctx = _TestContext(
        session=MagicMock(),
        user_id="00000000-0000-0000-0000-000000000001",
    )

    # ``_apply_session_project_switch`` is invoked after create; patch it so the
    # test stays focused on the payload-forwarding contract.
    import app.ai.tools.templates.project_template as pt

    original_switch = pt._apply_session_project_switch
    pt._apply_session_project_switch = AsyncMock()  # type: ignore[assignment]
    try:
        result = await _create_project_raw(
            name="Automation Line 1",
            code="AL-001",
            custom_fields={"public_code": "ABC"},
            custom_entity_template_root_id=str(template_root_id),
            context=ctx,
        )
    finally:
        pt._apply_session_project_switch = original_switch  # type: ignore[assignment]

    assert "error" not in result, f"unexpected error: {result.get('error')}"
    # The tool forwarded the custom_fields and template root id verbatim.
    assert captured["custom_fields"] == {"public_code": "ABC"}
    assert captured["template_root_id"] == template_root_id
    # And the created-entity response surfaces ai_visible fields (snapshot None
    # -> empty, conservative).
    assert result["custom_fields"] == {}
