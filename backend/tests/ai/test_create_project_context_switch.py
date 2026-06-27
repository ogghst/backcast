"""Tests for ``create_project`` auto-retargeting the session project context.

Regression coverage for the bug where ``create_project`` left the session's
effective project on the AMBIENT project, so every subsequent project-scoped
tool (``add_document``, ``batch_create_wbs_elements``, ``create_control_account``)
operated on the wrong project. After the fix, ``create_project`` retargets the
shared ``ToolContext`` in place AND persists the new ``project_id`` to the
``AIConversationSession`` row via ``_apply_session_project_switch``.

These tests are fully DB-free: they stub ``ToolContext.project_service`` and
patch ``async_session_maker`` (the separate session the helper uses for the
session-row update), mirroring the mock style of
``test_set_project_context_tool.py``.
"""

from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.ai.tools import context_tools
from app.ai.tools.templates.project_template import create_project
from app.ai.tools.types import ToolContext

# ``@ai_tool`` replaces the module name ``create_project`` with a LangChain
# ``StructuredTool``. ``.coroutine`` is the decorator's session-managing
# wrapper, and ``__wrapped__`` is the original async function with no session
# side effects -- what we want for a pure unit test.
_create_project_raw = create_project.coroutine.__wrapped__  # type: ignore[attr-defined]

_USER_ID = "00000000-0000-0000-0000-000000000001"
_AMBIENT_PROJECT_ID = "00000000-0000-0000-0000-0000000000aa"
_NEW_PROJECT_ID = "00000000-0000-0000-0000-0000000000bb"
_SESSION_ID = "00000000-0000-0000-0000-0000000000cc"


class _StubProject:
    """Minimal stand-in for a Project ORM row (only read attrs are set)."""

    def __init__(
        self, *, project_id: uuid.UUID, name: str = "ESP32-IRRIG", code: str = "ESP32"
    ) -> None:
        self.project_id = project_id
        self.name = name
        self.code = code
        self.description = "Drip irrigation controller"
        self.status = "ACT"
        self.budget = None


class _TestContext(ToolContext):
    """ToolContext subclass exposing a stubbed ``project_service``."""

    def __init__(self, service: MagicMock, **kwargs: Any) -> None:
        super().__init__(session=MagicMock(), user_id=_USER_ID, **kwargs)
        self._service = service

    @property
    def project_service(self) -> Any:  # type: ignore[override]
        return self._service


def _make_service(stub_project: _StubProject) -> MagicMock:
    """Build a mock project_service with create_project returning the stub.

    ``get_by_code`` returns None so the dedup check passes through.
    """
    service = MagicMock()
    service.get_by_code = AsyncMock(return_value=None)
    service.create_project = AsyncMock(return_value=stub_project)
    return service


def _patch_session_maker(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[MagicMock, MagicMock]:
    """Patch ``async_session_maker`` (used by the retarget helper) to a mock.

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
async def test_create_project_retargets_context_in_memory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """After create_project, context.project_id points at the NEW project.

    This is the core regression: previously the context stayed on the ambient
    project and every subsequent tool operated on it instead. We spy on the
    helper to confirm it was invoked with the new project's identity AND that
    it mutated the context in place.
    """
    new_pid = uuid.UUID(_NEW_PROJECT_ID)
    service = _make_service(_StubProject(project_id=new_pid))
    helper_calls: list[dict[str, Any]] = []
    real_helper = context_tools._apply_session_project_switch

    async def _spy(
        context: ToolContext,
        project_uuid: uuid.UUID,
        project_name: str,
        project_code: str,
    ) -> None:
        helper_calls.append(
            {
                "project_uuid": project_uuid,
                "project_name": project_name,
                "project_code": project_code,
            }
        )
        await real_helper(context, project_uuid, project_name, project_code)

    # Patch both the source module and the template's bound reference so the
    # spy is used regardless of which import the call site resolves through.
    monkeypatch.setattr(context_tools, "_apply_session_project_switch", _spy)
    import app.ai.tools.templates.project_template as pt

    monkeypatch.setattr(pt, "_apply_session_project_switch", _spy)

    ctx = _TestContext(service, project_id=_AMBIENT_PROJECT_ID)

    result = await _create_project_raw(name="ESP32-IRRIG", code="ESP32", context=ctx)

    assert "error" not in result, f"unexpected error: {result.get('error')}"
    # The helper was called with the newly created project's identity.
    assert helper_calls == [
        {
            "project_uuid": new_pid,
            "project_name": "ESP32-IRRIG",
            "project_code": "ESP32",
        }
    ]
    # In-memory context switched off the ambient project.
    assert ctx.project_id == _NEW_PROJECT_ID
    assert ctx.branch_name == "main"
    assert ctx.branch_mode == "merged"


@pytest.mark.asyncio
async def test_create_project_persists_project_id_to_session_row(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """create_project writes the new project_id to AIConversationSession."""
    new_pid = uuid.UUID(_NEW_PROJECT_ID)
    service = _make_service(_StubProject(project_id=new_pid))
    maker_mock, db_mock = _patch_session_maker(monkeypatch)

    ctx = _TestContext(
        service,
        project_id=_AMBIENT_PROJECT_ID,
        session_id=_SESSION_ID,
    )

    result = await _create_project_raw(name="ESP32-IRRIG", code="ESP32", context=ctx)

    assert result.get("context_switched_to") == _NEW_PROJECT_ID
    # The session-row UPDATE was issued via the separate session and committed.
    maker_mock.assert_called_once()
    db_mock.execute.assert_awaited_once()
    db_mock.commit.assert_awaited_once()

    executed_stmt = db_mock.execute.await_args.args[0]
    compiled = executed_stmt.compile()
    bound = compiled.construct_params()
    assert bound["project_id"] == _NEW_PROJECT_ID
    # The WHERE clause targets our session id.
    assert bound.get("id_1") == _SESSION_ID


@pytest.mark.asyncio
async def test_create_project_context_switch_reflected_in_return(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The returned dict advertises the switch via context_switched_to."""
    new_pid = uuid.UUID(_NEW_PROJECT_ID)
    service = _make_service(_StubProject(project_id=new_pid))
    _patch_session_maker(monkeypatch)

    ctx = _TestContext(service, project_id=_AMBIENT_PROJECT_ID, session_id=_SESSION_ID)

    result = await _create_project_raw(name="ESP32-IRRIG", code="ESP32", context=ctx)

    assert result["context_switched_to"] == str(new_pid)
    # Existing fields are preserved.
    assert result["id"] == str(new_pid)
    assert result["code"] == "ESP32"


@pytest.mark.asyncio
async def test_create_project_no_session_id_skips_db_write(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Without session_id, no DB write but in-memory context still switches."""
    new_pid = uuid.UUID(_NEW_PROJECT_ID)
    service = _make_service(_StubProject(project_id=new_pid))
    maker_mock, db_mock = _patch_session_maker(monkeypatch)

    ctx = _TestContext(service, project_id=_AMBIENT_PROJECT_ID, session_id=None)

    await _create_project_raw(name="ESP32-IRRIG", code="ESP32", context=ctx)

    assert ctx.project_id == _NEW_PROJECT_ID
    maker_mock.assert_not_called()
    db_mock.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_project_dup_error_does_not_switch_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If the project already exists (dedup), the session context is untouched."""
    existing_pid = uuid.UUID(_AMBIENT_PROJECT_ID)
    service = MagicMock()
    service.get_by_code = AsyncMock(
        return_value=_StubProject(project_id=existing_pid, name="OLD")
    )
    service.create_project = AsyncMock()
    _patch_session_maker(monkeypatch)

    ctx = _TestContext(service, project_id=_AMBIENT_PROJECT_ID, session_id=_SESSION_ID)

    result = await _create_project_raw(name="ESP32-IRRIG", code="ESP32", context=ctx)

    assert "error" in result
    service.create_project.assert_not_awaited()
    # Context unchanged.
    assert ctx.project_id == _AMBIENT_PROJECT_ID
