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

from app.ai.agent_service import AgentService
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
_SESSION_ID = "00000000-0000-0000-0000-0000000000cc"


class _StubProject:
    """Minimal stand-in for a Project ORM row (only read attrs are set)."""

    def __init__(self, *, name: str = "Automation Line 1", code: str = "AL1") -> None:
        self.name = name
        self.code = code


def _make_context(
    project_id: str | None = None,
    branch_name: str | None = None,
    branch_mode: str | None = None,
    session_id: str | None = None,
) -> ToolContext:
    return ToolContext(
        session=MagicMock(),
        user_id=_USER_ID,
        project_id=project_id,
        branch_name=branch_name,
        branch_mode=branch_mode,  # type: ignore[arg-type]
        session_id=session_id,
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


# ---------------------------------------------------------------------------
# Cross-turn persistence: set_project_context writes the project_id back to the
# AIConversationSession row (best-effort) so the scope survives the next turn.
# ---------------------------------------------------------------------------


class _AsyncCM:
    """Minimal async context manager wrapping a mock session.

    ``set_project_context`` does ``async with async_session_maker() as db:``,
    so we patch the maker to return an object whose ``__aenter__`` yields the
    mock session and ``__aexit__`` is awaitable.
    """

    def __init__(self, session: MagicMock) -> None:
        self._session = session

    async def __aenter__(self) -> MagicMock:
        return self._session

    async def __aexit__(self, *exc: object) -> None:
        return None


def _patch_session_maker(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[MagicMock, MagicMock]:
    """Patch ``async_session_maker`` at its source to a mock factory.

    ``set_project_context`` imports the maker locally
    (``from app.db.session import async_session_maker``), so we patch the
    symbol on ``app.db.session`` itself.

    Returns ``(maker_mock, db_mock)`` where ``db_mock.execute`` /
    ``db_mock.commit`` are ``AsyncMock`` instances tests can assert on.
    """
    import app.db.session as db_session_mod

    db_mock = MagicMock()
    db_mock.execute = AsyncMock()
    db_mock.commit = AsyncMock()
    db_mock.__aenter__ = AsyncMock(return_value=db_mock)
    db_mock.__aexit__ = AsyncMock(return_value=None)

    maker_mock = MagicMock(return_value=db_mock)
    monkeypatch.setattr(db_session_mod, "async_session_maker", maker_mock)
    return maker_mock, db_mock


@pytest.mark.asyncio
async def test_persists_project_id_to_session_row(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With session_id set, the project_id is written to AIConversationSession.

    Patches async_session_maker so no DB is touched; asserts execute (UPDATE)
    was awaited with a statement carrying the project_id, and commit ran.
    The in-memory context is still mutated regardless.
    """
    project_uuid = uuid.UUID(_PROJECT_ID)
    _patch_rbac(monkeypatch, accessible=[project_uuid])
    _patch_project_service(monkeypatch, return_value=_StubProject())
    maker_mock, db_mock = _patch_session_maker(monkeypatch)

    ctx = _make_context(project_id=None, session_id=_SESSION_ID)

    result = await _set_project_context_raw(project_id=_PROJECT_ID, context=ctx)

    assert result.get("success") is True
    # In-memory mutation happened
    assert ctx.project_id == _PROJECT_ID
    # Persistence: maker was called, UPDATE executed, commit awaited
    maker_mock.assert_called_once()
    db_mock.execute.assert_awaited_once()
    db_mock.commit.assert_awaited_once()

    # The UPDATE statement must carry the project_id in its compiled params.
    executed_stmt = db_mock.execute.await_args.args[0]
    compiled = executed_stmt.compile()
    bound = compiled.construct_params()
    assert bound["project_id"] == _PROJECT_ID
    # The WHERE clause targets our session id
    assert bound.get("id_1") == _SESSION_ID


@pytest.mark.asyncio
async def test_no_session_id_skips_db_write(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Without session_id, no DB write occurs but context is still mutated."""
    project_uuid = uuid.UUID(_PROJECT_ID)
    _patch_rbac(monkeypatch, accessible=[project_uuid])
    _patch_project_service(monkeypatch, return_value=_StubProject())
    maker_mock, db_mock = _patch_session_maker(monkeypatch)

    ctx = _make_context(project_id=None, session_id=None)

    result = await _set_project_context_raw(project_id=_PROJECT_ID, context=ctx)

    assert result.get("success") is True
    # In-memory mutation happened even without persistence
    assert ctx.project_id == _PROJECT_ID
    # No DB interaction at all
    maker_mock.assert_not_called()
    db_mock.execute.assert_not_awaited()
    db_mock.commit.assert_not_awaited()


# ---------------------------------------------------------------------------
# Preflight return shape: _preflight_execution returns a 2-tuple.
# A heavyweight fixture (real session row) is not worth the brittleness here;
# the tuple shape is verified via the function's return annotation instead,
# which is the load-bearing contract for the start_execution destructuring.
# ---------------------------------------------------------------------------


def test_preflight_execution_returns_two_tuple_annotation() -> None:
    """_preflight_execution is annotated to return a (context, project_id) tuple."""
    from typing import get_type_hints

    hints = get_type_hints(AgentService._preflight_execution)
    # The return annotation must be a 2-tuple type (typing.Tuple or tuple[...]).
    ret = hints.get("return")
    assert ret is not None
    args = getattr(ret, "__args__", None)
    assert args is not None and len(args) == 2, f"expected 2-tuple return, got {ret!r}"
