"""Tests for the ``set_project_context`` AI tool.

The tool mutates the shared ``ToolContext`` in place after an RBAC access
check (``get_accessible_projects``) and a project fetch
(``project_service.get_as_of``). We patch the module-level RBAC helpers in
``context_tools`` plus the ``ToolContext.project_service`` property so every
test is fully DB-free, mirroring the mock style of ``test_add_document_tool.py``.
"""

from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.ai.tools import context_tools
from app.ai.tools.context_tools import set_project_context
from app.ai.tools.types import ToolContext

# ``@ai_tool`` replaces the module name ``set_project_context`` with a
# LangChain ``StructuredTool``. ``.coroutine`` is the decorator's
# session-managing wrapper, and ``__wrapped__`` is the original async function
# with no session side effects -- what we want for a pure unit test.
_set_project_context_raw = set_project_context.coroutine.__wrapped__  # type: ignore[attr-defined]

_USER_ID = "00000000-0000-0000-0000-000000000001"
_PROJECT_ID = "00000000-0000-0000-0000-0000000000aa"
_OTHER_PROJECT_ID = "00000000-0000-0000-0000-0000000000bb"


class _StubProject:
    """Minimal stand-in for a Project ORM row (only read attrs are set)."""

    def __init__(self, *, name: str = "Automation Line 1", code: str = "AL1") -> None:
        self.name = name
        self.code = code


def _make_context(
    project_id: str | None = None,
    branch_name: str | None = None,
    branch_mode: str | None = None,
) -> ToolContext:
    return ToolContext(
        session=MagicMock(),
        user_id=_USER_ID,
        project_id=project_id,
        branch_name=branch_name,
        branch_mode=branch_mode,  # type: ignore[arg-type]
    )


def _patch_rbac(
    monkeypatch: pytest.MonkeyPatch,
    *,
    accessible: list[uuid.UUID],
) -> MagicMock:
    """Patch the module-level RBAC helpers used by ``set_project_context``.

    Returns the mock unified service instance so tests can assert on calls.
    """
    unified_service = MagicMock()
    unified_service.get_accessible_projects = AsyncMock(return_value=accessible)

    monkeypatch.setattr(
        context_tools, "get_unified_rbac_service", lambda: unified_service
    )
    monkeypatch.setattr(
        context_tools, "set_unified_rbac_session", lambda _session: None
    )
    return unified_service


def _patch_project_service(
    monkeypatch: pytest.MonkeyPatch,
    *,
    return_value: Any = None,
) -> MagicMock:
    """Patch ``ToolContext.project_service`` to return a controlled mock.

    Returns the mock service instance.
    """
    service = MagicMock()
    service.get_as_of = AsyncMock(return_value=return_value)
    # Replace the class-level property with a plain attribute returning the
    # mock service (shadows the property for instances created in this test).
    monkeypatch.setattr(ToolContext, "project_service", service, raising=False)
    return service


@pytest.mark.asyncio
async def test_valid_accessible_project_sets_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Accessible project -> success, context mutated, name/code returned."""
    project_uuid = uuid.UUID(_PROJECT_ID)
    _patch_rbac(monkeypatch, accessible=[project_uuid])
    _patch_project_service(monkeypatch, return_value=_StubProject())

    ctx = _make_context(project_id=None, branch_name=None, branch_mode=None)

    result = await _set_project_context_raw(project_id=_PROJECT_ID, context=ctx)

    assert "error" not in result, f"unexpected error: {result.get('error')}"
    assert result["success"] is True
    assert result["project_id"] == _PROJECT_ID
    assert result["project_name"] == "Automation Line 1"
    assert result["project_code"] == "AL1"
    assert result["changes"]["project_id"] == {"from": None, "to": _PROJECT_ID}
    # Context mutated in place
    assert ctx.project_id == _PROJECT_ID
    assert ctx.branch_name == "main"
    assert ctx.branch_mode == "merged"


@pytest.mark.asyncio
async def test_access_denied_leaves_context_unchanged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Project not in get_accessible_projects -> error, context unchanged."""
    # User can access a DIFFERENT project only
    _patch_rbac(monkeypatch, accessible=[uuid.UUID(_OTHER_PROJECT_ID)])
    service = _patch_project_service(monkeypatch, return_value=_StubProject())

    ctx = _make_context(project_id=_OTHER_PROJECT_ID, branch_name="BR-1")

    result = await _set_project_context_raw(project_id=_PROJECT_ID, context=ctx)

    assert result == {"error": "Access denied to this project"}
    # Context must be untouched (no fetch should have run either)
    assert ctx.project_id == _OTHER_PROJECT_ID
    assert ctx.branch_name == "BR-1"
    service.get_as_of.assert_not_awaited()


@pytest.mark.asyncio
async def test_invalid_uuid_returns_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Non-UUID string -> error dict, context unchanged, no RBAC/fetch calls."""
    unified = _patch_rbac(monkeypatch, accessible=[])
    service = _patch_project_service(monkeypatch, return_value=_StubProject())

    ctx = _make_context(project_id=None)

    result = await _set_project_context_raw(project_id="not-a-uuid", context=ctx)

    assert result == {"error": "Invalid project ID: not-a-uuid"}
    assert ctx.project_id is None
    unified.get_accessible_projects.assert_not_awaited()
    service.get_as_of.assert_not_awaited()


@pytest.mark.asyncio
async def test_project_not_found_returns_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Accessible but get_as_of returns None -> error, context unchanged."""
    project_uuid = uuid.UUID(_PROJECT_ID)
    _patch_rbac(monkeypatch, accessible=[project_uuid])
    _patch_project_service(monkeypatch, return_value=None)

    ctx = _make_context(project_id=None)

    result = await _set_project_context_raw(project_id=_PROJECT_ID, context=ctx)

    assert result == {"error": f"Project {_PROJECT_ID} not found"}
    assert ctx.project_id is None


@pytest.mark.asyncio
async def test_project_scoped_guard_no_longer_trips_after_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """After a successful set_project_context, add_document's guard passes."""
    from app.ai.tools.document_tools import add_document

    _add_document_raw = add_document.coroutine.__wrapped__  # type: ignore[attr-defined]

    project_uuid = uuid.UUID(_PROJECT_ID)
    _patch_rbac(monkeypatch, accessible=[project_uuid])
    _patch_project_service(monkeypatch, return_value=_StubProject())

    # Patch DocumentService so add_document never touches the DB
    stub_doc = MagicMock()
    stub_doc.id = uuid.UUID("00000000-0000-0000-0000-0000000000b1")
    stub_doc.name = "report.md"
    stub_doc.extension = "md"
    stub_doc.folder_id = None
    stub_doc.size_bytes = 42
    stub_doc.description = None
    stub_doc.tags = []
    stub_doc.current_version.version_number = 1
    mock_doc_service_cls = MagicMock()
    mock_doc_service_cls.return_value.upload_document = AsyncMock(return_value=stub_doc)
    mock_doc_service_cls.return_value.update_metadata = AsyncMock(return_value=stub_doc)
    monkeypatch.setattr(
        "app.ai.tools.document_tools.DocumentService", mock_doc_service_cls
    )

    # Start in general (no-project) chat
    ctx = _make_context(project_id=None)

    # Before: add_document trips the guard
    pre = await _add_document_raw(filename="report.md", content="hi", context=ctx)
    assert "error" in pre
    assert "No project context" in pre["error"]

    # Scope to the project
    set_result = await _set_project_context_raw(project_id=_PROJECT_ID, context=ctx)
    assert set_result.get("success") is True

    # After: add_document proceeds (no "No project context" error)
    post = await _add_document_raw(filename="report.md", content="hi", context=ctx)
    assert "error" not in post, post
    assert post["id"] == str(stub_doc.id)
