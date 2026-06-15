"""Tests surfacing contract_value and currency to AI tools (gap G1).

The AI-facing project serializers hand-build dicts instead of using the public
Pydantic schema, and previously omitted ``contract_value`` / ``currency``.  These
tests pin the fix for ``get_project`` and ``list_projects``.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.ai.tools.project_tools import get_project, list_projects
from app.ai.tools.types import ToolContext

# ``@ai_tool`` replaces the module names ``get_project`` / ``list_projects`` with
# LangChain ``StructuredTool`` instances whose ``.coroutine`` is the decorator's
# session-managing wrapper.  ``__wrapped__`` is the original async function with
# no session side effects -- what we want for a pure unit test.
_get_project_raw = get_project.coroutine.__wrapped__  # type: ignore[attr-defined]
_list_projects_raw = list_projects.coroutine.__wrapped__  # type: ignore[attr-defined]


class _StubProject:
    """Minimal stand-in for a Project ORM row.

    Only the attributes read by ``get_project`` / ``list_projects`` are set; the
    others (e.g. valid_time) are irrelevant to the serialization under test.
    """

    def __init__(
        self,
        *,
        project_id: uuid.UUID,
        contract_value: Decimal | None,
        currency: str,
        budget: Decimal | None,
    ) -> None:
        self.project_id = project_id
        self.code = "AL1"
        self.name = "Automation Line 1"
        self.description = "An end-of-line automation project"
        self.status = "ACT"
        self.budget = budget
        self.contract_value = contract_value
        self.currency = currency
        self.start_date = None
        self.end_date = None
        self.branch = "main"


def _make_context_with_project(stub_project: _StubProject | None) -> ToolContext:
    """Build a ToolContext whose ``project_service`` is fully stubbed.

    ``ToolContext.project_service`` is a property returning a real
    ``ProjectService``; we override it on a subclass to return a mock whose
    ``get_as_of`` / ``get_projects`` yield our stub data with no DB.
    """

    mock_service = MagicMock()
    mock_service.get_as_of = AsyncMock(return_value=stub_project)

    if stub_project is not None:
        mock_service.get_projects = AsyncMock(
            return_value=([stub_project], 1),
        )
    else:
        mock_service.get_projects = AsyncMock(return_value=([], 0))

    class _TestContext(ToolContext):
        @property
        def project_service(self) -> Any:  # type: ignore[override]
            return mock_service

    return _TestContext(
        session=MagicMock(),
        user_id="00000000-0000-0000-0000-000000000001",
    )


@pytest.mark.asyncio
async def test_get_project_surfaces_contract_value_and_currency() -> None:
    """get_project must include contract_value (float) and currency (str)."""
    pid = uuid.UUID("00000000-0000-0000-0000-0000000000aa")
    stub = _StubProject(
        project_id=pid,
        contract_value=Decimal("1234567.89"),
        currency="EUR",
        budget=Decimal("1000000.00"),
    )
    ctx = _make_context_with_project(stub)

    result = await _get_project_raw(project_id=str(pid), context=ctx)

    assert isinstance(result, dict)
    assert "error" not in result, f"unexpected error: {result.get('error')}"
    assert result["contract_value"] == 1234567.89
    assert result["currency"] == "EUR"
    # budget must still be present (unchanged behaviour)
    assert result["budget"] == 1000000.00


@pytest.mark.asyncio
async def test_get_project_contract_value_none_when_unset() -> None:
    """When contract_value is None it must serialize to None, not error."""
    pid = uuid.UUID("00000000-0000-0000-0000-0000000000bb")
    stub = _StubProject(
        project_id=pid,
        contract_value=None,
        currency="USD",
        budget=None,
    )
    ctx = _make_context_with_project(stub)

    result = await _get_project_raw(project_id=str(pid), context=ctx)

    assert isinstance(result, dict)
    assert "error" not in result
    assert result["contract_value"] is None
    assert result["currency"] == "USD"
    assert result["budget"] is None


@pytest.mark.asyncio
async def test_list_projects_surfaces_contract_value_and_currency() -> None:
    """Each item from list_projects must carry contract_value and currency."""
    pid = uuid.UUID("00000000-0000-0000-0000-0000000000cc")
    stub = _StubProject(
        project_id=pid,
        contract_value=Decimal("500000.00"),
        currency="EUR",
        budget=Decimal("500000.00"),
    )
    ctx = _make_context_with_project(stub)

    # list_projects consults RBAC via the unified service + session.  Patch the
    # two import points so the test stays DB-free and returns the stub project.
    import app.core.rbac_unified as rbac

    unified_mock = MagicMock()
    unified_mock.get_accessible_projects = AsyncMock(return_value=[pid])
    ctx_uuid = uuid.UUID(ctx.user_id)

    monkey_get_unified = MagicMock(return_value=unified_mock)
    monkey_set_unified = MagicMock()

    original_get = rbac.get_unified_rbac_service
    original_set = rbac.set_unified_rbac_session
    rbac.get_unified_rbac_service = monkey_get_unified  # type: ignore[assignment]
    rbac.set_unified_rbac_session = monkey_set_unified  # type: ignore[assignment]
    try:
        result = await _list_projects_raw(
            search=None, status=None, page=1, limit=10, context=ctx
        )
    finally:
        rbac.get_unified_rbac_service = original_get  # type: ignore[assignment]
        rbac.set_unified_rbac_session = original_set  # type: ignore[assignment]

    assert isinstance(result, dict)
    assert "error" not in result, f"unexpected error: {result.get('error')}"
    projects = result.get("projects", [])
    assert len(projects) == 1
    item = projects[0]
    assert item["contract_value"] == 500000.00
    assert item["currency"] == "EUR"
    assert item["budget"] == 500000.00

    # Guard: the ctx_uuid local above is intentionally exercised to keep the
    # import graph honest (RBAC plumbing reads the user id as a UUID).
    assert ctx_uuid == uuid.UUID(ctx.user_id)
