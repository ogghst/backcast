"""Tests for the ``send_notification`` AI tool.

The tool resolves recipients (self by default; others by UUID/email), enforces
an internal ``notifications-send`` RBAC check for cross-user sends, maps a
severity string, then delegates to :func:`user_emitter(...).emit`. We call the
raw async function (``send_notification.coroutine.__wrapped__`` -- the unwrapped
fn with no session commit/rollback) and patch the module-level ``user_emitter``
plus ``UserService`` so every test is fully DB-free, mirroring the mock style
of ``test_set_project_context_tool.py``.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.ai.tools import notification_tools
from app.ai.tools.notification_tools import send_notification
from app.ai.tools.types import ToolContext
from app.core.notifications import NotificationType, Severity
from app.core.notifications.registry import REGISTRY

# ``@ai_tool`` wraps the fn in a LangChain StructuredTool whose ``coroutine``
# is the session-managing wrapper; ``__wrapped__`` is the original async fn
# with no session side effects -- what we want for a pure unit test.
_send_notification_raw = send_notification.coroutine.__wrapped__  # type: ignore[attr-defined]

_USER_ID = "00000000-0000-0000-0000-000000000001"
_OTHER_USER_ID = "00000000-0000-0000-0000-000000000002"
_PROJECT_ID = "00000000-0000-0000-0000-0000000000aa"


class _StubUser:
    """Minimal stand-in for a User ORM row (only read attrs are set)."""

    def __init__(self, user_id: uuid.UUID) -> None:
        self.user_id = user_id
        self.email = f"{user_id}@example.com"


def _make_context(
    user_id: str = _USER_ID,
    project_id: str | None = None,
    check_permission_return: bool = False,
) -> tuple[ToolContext, AsyncMock]:
    """Build a minimal ToolContext with a mock ``check_permission``.

    Returns ``(context, check_permission_mock)`` so tests can assert on calls.
    """
    ctx = ToolContext(session=MagicMock(), user_id=user_id, project_id=project_id)
    check_perm = AsyncMock(return_value=check_permission_return)
    # Patch the bound method so the tool's ``context.check_permission`` resolves
    # to our mock regardless of the LRU cache.
    ctx.check_permission = check_perm  # type: ignore[method-assign]
    return ctx, check_perm


def _patch_user_service(
    monkeypatch: pytest.MonkeyPatch,
    *,
    by_uuid: dict[uuid.UUID, _StubUser] | None = None,
    by_email: dict[str, _StubUser] | None = None,
) -> MagicMock:
    """Patch ``UserService`` in the tool module to return canned users.

    Args:
        by_uuid: Map of UUID -> stub user returned by ``get_user``.
        by_email: Map of email -> stub user returned by ``get_by_email``.

    Returns the mock service instance tests can assert on.
    """
    by_uuid = by_uuid or {}
    by_email = by_email or {}

    service = MagicMock()
    service.get_user = AsyncMock(side_effect=lambda uid: by_uuid.get(uid))
    service.get_by_email = AsyncMock(side_effect=lambda email: by_email.get(email))
    mock_cls = MagicMock(return_value=service)
    monkeypatch.setattr(notification_tools, "UserService", mock_cls)
    return service


def _patch_emitter(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[MagicMock, MagicMock]:
    """Patch ``user_emitter`` to return a mock EventEmitter.

    Returns ``(emitter_mock, emit_mock)`` where ``emit_mock`` is an
    ``AsyncMock`` tests can assert was awaited with the expected args.
    """
    emit_mock = AsyncMock()
    emitter = MagicMock()
    emitter.emit = emit_mock
    maker = MagicMock(return_value=emitter)
    monkeypatch.setattr(notification_tools, "user_emitter", maker)
    return emitter, emit_mock


# ---------------------------------------------------------------------------
# Registry invariant: agent.notify registered + NotificationType mirrors it.
# ---------------------------------------------------------------------------


def test_registry_has_agent_notify() -> None:
    """agent.notify is in REGISTRY and NotificationType.AGENT_NOTIFY mirrors it."""
    assert "agent.notify" in REGISTRY
    assert NotificationType.AGENT_NOTIFY == "agent.notify"
    assert REGISTRY["agent.notify"].category.value == "agent"


# ---------------------------------------------------------------------------
# Self-notify (no permission required).
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_self_default_no_recipients(monkeypatch: pytest.MonkeyPatch) -> None:
    """No recipients -> emits to current user only, self_only True, no perm check."""
    _, emit_mock = _patch_emitter(monkeypatch)
    svc = _patch_user_service(monkeypatch)
    ctx, check_perm = _make_context()

    result = await _send_notification_raw(message="hi", context=ctx)

    assert "error" not in result, result
    assert result["sent"] is True
    assert result["self_only"] is True
    assert result["count"] == 1
    assert result["recipients"] == [{"user_id": _USER_ID}]
    emit_mock.assert_awaited_once()
    kwargs = emit_mock.await_args.kwargs
    assert kwargs["target_user_ids"] == [uuid.UUID(_USER_ID)]
    assert kwargs["title"] == "Notification"
    assert kwargs["message"] == "hi"
    # No user lookups happened for the self-default path.
    svc.get_user.assert_not_awaited()
    svc.get_by_email.assert_not_awaited()
    # No permission check for self-only sends.
    check_perm.assert_not_awaited()


@pytest.mark.asyncio
async def test_explicit_self_recipient(monkeypatch: pytest.MonkeyPatch) -> None:
    """recipients=[own_uuid] -> same as default; self_only True, no perm check."""
    _, emit_mock = _patch_emitter(monkeypatch)
    _patch_user_service(
        monkeypatch,
        by_uuid={uuid.UUID(_USER_ID): _StubUser(uuid.UUID(_USER_ID))},
    )
    ctx, check_perm = _make_context()

    result = await _send_notification_raw(
        message="hi", context=ctx, recipients=[_USER_ID]
    )

    assert result["sent"] is True
    assert result["self_only"] is True
    assert result["count"] == 1
    emit_mock.assert_awaited_once()
    check_perm.assert_not_awaited()


@pytest.mark.asyncio
async def test_self_only_without_permission_succeeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Role has no permission but recipients=None -> still succeeds (self-only)."""
    _, emit_mock = _patch_emitter(monkeypatch)
    _patch_user_service(monkeypatch)
    # check_permission defaults to False (no permission); must NOT block self.
    ctx, check_perm = _make_context(check_permission_return=False)

    result = await _send_notification_raw(message="hi", context=ctx)

    assert result["sent"] is True
    assert result["self_only"] is True
    emit_mock.assert_awaited_once()
    check_perm.assert_not_awaited()


@pytest.mark.asyncio
async def test_title_override(monkeypatch: pytest.MonkeyPatch) -> None:
    """Explicit title is forwarded to emit instead of the default."""
    _, emit_mock = _patch_emitter(monkeypatch)
    _patch_user_service(monkeypatch)
    ctx, _ = _make_context()

    result = await _send_notification_raw(message="body", context=ctx, title="Heads up")

    assert result["sent"] is True
    assert emit_mock.await_args.kwargs["title"] == "Heads up"


# ---------------------------------------------------------------------------
# Cross-user resolution (email / UUID / mixed) + dedup.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_email_resolution(monkeypatch: pytest.MonkeyPatch) -> None:
    """An email recipient resolves via get_by_email -> emits to that user_id."""
    other = _StubUser(uuid.UUID(_OTHER_USER_ID))
    _, emit_mock = _patch_emitter(monkeypatch)
    _patch_user_service(monkeypatch, by_email={"other@example.com": other})
    ctx, check_perm = _make_context(check_permission_return=True)

    result = await _send_notification_raw(
        message="hi", context=ctx, recipients=["other@example.com"]
    )

    assert result["sent"] is True
    assert result["self_only"] is False
    assert result["count"] == 1
    assert result["recipients"] == [{"user_id": _OTHER_USER_ID}]
    check_perm.assert_awaited_once()
    emit_mock.assert_awaited_once()
    assert emit_mock.await_args.kwargs["target_user_ids"] == [other.user_id]


@pytest.mark.asyncio
async def test_uuid_resolution(monkeypatch: pytest.MonkeyPatch) -> None:
    """A UUID recipient resolves via get_user -> emits to that UUID."""
    other = _StubUser(uuid.UUID(_OTHER_USER_ID))
    _, emit_mock = _patch_emitter(monkeypatch)
    _patch_user_service(monkeypatch, by_uuid={uuid.UUID(_OTHER_USER_ID): other})
    ctx, _ = _make_context(check_permission_return=True)

    result = await _send_notification_raw(
        message="hi", context=ctx, recipients=[_OTHER_USER_ID]
    )

    assert result["sent"] is True
    assert result["count"] == 1
    assert result["recipients"] == [{"user_id": _OTHER_USER_ID}]
    emit_mock.assert_awaited_once()
    assert emit_mock.await_args.kwargs["target_user_ids"] == [other.user_id]


@pytest.mark.asyncio
async def test_mixed_recipients_deduped(monkeypatch: pytest.MonkeyPatch) -> None:
    """Email + UUID + self resolves to a deduped, order-preserving list."""
    self_uuid = uuid.UUID(_USER_ID)
    other_uuid = uuid.UUID(_OTHER_USER_ID)
    other = _StubUser(other_uuid)
    _, emit_mock = _patch_emitter(monkeypatch)
    _patch_user_service(
        monkeypatch,
        by_uuid={self_uuid: _StubUser(self_uuid), other_uuid: other},
        by_email={"other@example.com": other},  # same user via email
    )
    ctx, _ = _make_context(check_permission_return=True)

    result = await _send_notification_raw(
        message="hi",
        context=ctx,
        recipients=[
            _USER_ID,  # self (uuid)
            "other@example.com",  # other (email)
            _OTHER_USER_ID,  # other (uuid) -> dup
        ],
    )

    assert result["sent"] is True
    assert result["count"] == 2
    assert result["self_only"] is False
    assert result["recipients"] == [
        {"user_id": _USER_ID},
        {"user_id": _OTHER_USER_ID},
    ]
    emit_mock.assert_awaited_once()
    assert emit_mock.await_args.kwargs["target_user_ids"] == [self_uuid, other_uuid]


# ---------------------------------------------------------------------------
# Failure paths (must return error dicts and NOT emit).
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unknown_email_returns_error_no_emit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unknown email -> error dict, no emit, no permission check."""
    _, emit_mock = _patch_emitter(monkeypatch)
    _patch_user_service(monkeypatch, by_email={})  # nothing resolves
    ctx, check_perm = _make_context(check_permission_return=True)

    result = await _send_notification_raw(
        message="hi", context=ctx, recipients=["nobody@example.com"]
    )

    assert "error" in result
    assert "nobody@example.com" in result["error"]
    emit_mock.assert_not_awaited()
    check_perm.assert_not_awaited()


@pytest.mark.asyncio
async def test_unknown_uuid_returns_error_no_emit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Valid UUID shape but no user -> error dict, no emit."""
    _, emit_mock = _patch_emitter(monkeypatch)
    _patch_user_service(monkeypatch, by_uuid={})  # nothing resolves
    ctx, _ = _make_context(check_permission_return=True)

    ghost = "11111111-1111-1111-1111-111111111111"
    result = await _send_notification_raw(message="hi", context=ctx, recipients=[ghost])

    assert "error" in result
    assert ghost in result["error"]
    emit_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_cross_user_denied_returns_error_no_emit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cross-user send without permission -> error dict, no emit."""
    other = _StubUser(uuid.UUID(_OTHER_USER_ID))
    _, emit_mock = _patch_emitter(monkeypatch)
    _patch_user_service(monkeypatch, by_uuid={uuid.UUID(_OTHER_USER_ID): other})
    ctx, check_perm = _make_context(check_permission_return=False)

    result = await _send_notification_raw(
        message="hi", context=ctx, recipients=[_OTHER_USER_ID]
    )

    assert result["error"] == "Not authorized to send notifications to other users"
    check_perm.assert_awaited_once()
    emit_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_cross_user_allowed_emits(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cross-user send WITH permission -> emits to the other user."""
    other = _StubUser(uuid.UUID(_OTHER_USER_ID))
    _, emit_mock = _patch_emitter(monkeypatch)
    _patch_user_service(monkeypatch, by_uuid={uuid.UUID(_OTHER_USER_ID): other})
    ctx, _ = _make_context(check_permission_return=True)

    result = await _send_notification_raw(
        message="hi", context=ctx, recipients=[_OTHER_USER_ID]
    )

    assert result["sent"] is True
    assert result["self_only"] is False
    emit_mock.assert_awaited_once()
    assert emit_mock.await_args.kwargs["target_user_ids"] == [other.user_id]


@pytest.mark.asyncio
async def test_too_many_recipients_returns_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """>20 distinct recipients -> error dict, no emit."""
    _, emit_mock = _patch_emitter(monkeypatch)
    # All resolve to distinct users.
    by_uuid = {uuid.UUID(int=i): _StubUser(uuid.UUID(int=i)) for i in range(1, 25)}
    _patch_user_service(monkeypatch, by_uuid=by_uuid)
    ctx, check_perm = _make_context(check_permission_return=True)

    recipients = [str(uuid.UUID(int=i)) for i in range(1, 25)]  # 24 distinct
    result = await _send_notification_raw(
        message="hi", context=ctx, recipients=recipients
    )

    assert "error" in result
    assert "max" in result["error"].lower()
    emit_mock.assert_not_awaited()
    check_perm.assert_not_awaited()


# ---------------------------------------------------------------------------
# Severity mapping.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_severity_warning(monkeypatch: pytest.MonkeyPatch) -> None:
    """severity='warning' -> Severity.WARNING forwarded."""
    _, emit_mock = _patch_emitter(monkeypatch)
    _patch_user_service(monkeypatch)
    ctx, _ = _make_context()

    await _send_notification_raw(message="hi", context=ctx, severity="warning")

    assert emit_mock.await_args.kwargs["severity"] == Severity.WARNING


@pytest.mark.asyncio
async def test_severity_bogus_falls_back_to_notice(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unknown severity -> falls back to Severity.NOTICE."""
    _, emit_mock = _patch_emitter(monkeypatch)
    _patch_user_service(monkeypatch)
    ctx, _ = _make_context()

    await _send_notification_raw(message="hi", context=ctx, severity="bogus")

    assert emit_mock.await_args.kwargs["severity"] == Severity.NOTICE


# ---------------------------------------------------------------------------
# Emit payload shape: event type, project scope, payload tag.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_emit_payload_shape_with_project_scope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """emit is awaited with AGENT_NOTIFY, project_id from context, via tag."""
    _, emit_mock = _patch_emitter(monkeypatch)
    _patch_user_service(monkeypatch)
    ctx, _ = _make_context(project_id=_PROJECT_ID)

    await _send_notification_raw(message="hi", context=ctx)

    args, kwargs = emit_mock.await_args
    assert args[0] == NotificationType.AGENT_NOTIFY
    assert kwargs["project_id"] == uuid.UUID(_PROJECT_ID)
    assert kwargs["payload"] == {"via": "ai_tool"}


@pytest.mark.asyncio
async def test_emit_no_project_scope_when_context_global(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Without project_id in context, project_id=None is forwarded."""
    _, emit_mock = _patch_emitter(monkeypatch)
    _patch_user_service(monkeypatch)
    ctx, _ = _make_context(project_id=None)

    await _send_notification_raw(message="hi", context=ctx)

    assert emit_mock.await_args.kwargs["project_id"] is None


# ---------------------------------------------------------------------------
# Unexpected exception -> error dict (tool never raises).
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unexpected_exception_returns_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If emit raises, the tool swallows it and returns an error dict."""
    emit_mock = AsyncMock(side_effect=RuntimeError("boom"))
    emitter = MagicMock()
    emitter.emit = emit_mock
    maker = MagicMock(return_value=emitter)
    monkeypatch.setattr(notification_tools, "user_emitter", maker)
    _patch_user_service(monkeypatch)
    ctx, _ = _make_context()

    result = await _send_notification_raw(message="hi", context=ctx)

    assert "error" in result
    assert "boom" in result["error"]
