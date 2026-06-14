"""Unit tests for the ask_user tool: published payload + registry behavior.

Covers:
- The published event data contains ``expires_at`` and ``timeout_seconds``
  (needed by the frontend countdown), plus the typed shape via
  ``WSAskUserMessage``.
- The awaiting-user registry (``mark_awaiting_user`` /
  ``clear_awaiting_user`` / ``is_awaiting_user``) is toggled around the
  blocking wait so the specialist step-timeout PAUSES while a human is
  being asked.
- ``expires_at`` is ~ ``now + timeout_seconds``.

Mirrors the ToolContext + mock event-bus faking pattern already used in
``tests/ai/test_replan_integration.py``.

The ``@ai_tool`` decorator returns a LangChain ``StructuredTool``; the
underlying async function (with context injection + session lifecycle) is
accessible as ``ask_user.coroutine``. We call that directly and stub
``ToolSessionManager`` so commit/rollback are no-ops (ask_user never
touches the DB).
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.ai.tools import ask_user as ask_user_module
from app.ai.tools.ask_user import (
    _awaiting_user,
    ask_user,
    is_awaiting_user,
    resolve_ask_user_response,
)
from app.ai.tools.types import ToolContext


def _make_context(
    execution_id: str = "exec-payload-1",
) -> tuple[ToolContext, list[Any]]:
    """Build a minimal ToolContext with a recording mock event bus.

    Returns the context and a list capturing every published AgentEvent.
    """
    mock_session = MagicMock()
    mock_event_bus = MagicMock()
    published: list[Any] = []
    mock_event_bus.publish = MagicMock(side_effect=lambda evt: published.append(evt))
    mock_event_bus.execution_id = execution_id
    ctx = ToolContext(
        session=mock_session,
        user_id="test-user",
        _event_bus=mock_event_bus,
    )
    ctx._stop_event = MagicMock()
    ctx._stop_event.is_set.return_value = False
    return ctx, published


def _reset_global_state() -> None:
    """Clear module-global registries so tests do not leak state."""
    ask_user_module._pending_asks.clear()
    _awaiting_user.clear()


@pytest.fixture(autouse=True)
def _stub_session_manager(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make ToolSessionManager.commit/rollback no-ops for every test."""
    monkeypatch.setattr(
        "app.ai.tools.session_manager.ToolSessionManager.commit",
        AsyncMock(),
    )
    monkeypatch.setattr(
        "app.ai.tools.session_manager.ToolSessionManager.rollback",
        AsyncMock(),
    )


@pytest.mark.asyncio
async def test_published_payload_has_expires_at_and_timeout_seconds() -> None:
    """The ask_user event carries expires_at + timeout_seconds for countdown."""
    _reset_global_state()
    ctx, published = _make_context()
    timeout = 60

    # ask_user.coroutine is the wrapped async fn; context is passed via kwargs.
    task = asyncio.create_task(
        ask_user.coroutine(  # type: ignore[attr-defined]
            "Which cell?",
            why="Need the cell to scope the cost search",
            options=["Robot Cell A", "Assembly Station 1"],
            timeout_seconds=timeout,
            context=ctx,
        )
    )
    # Yield so ask_user publishes the event before we resolve.
    await asyncio.sleep(0.05)

    assert len(published) == 1
    data = published[0].data

    # Required typed fields.
    assert data["type"] == "ask_user"
    assert data["question"] == "Which cell?"
    assert isinstance(data["ask_id"], str) and data["ask_id"]
    assert data["context"] == "Need the cell to scope the cost search"
    assert data["options"] == ["Robot Cell A", "Assembly Station 1"]
    # New countdown fields.
    assert data["timeout_seconds"] == timeout
    assert "expires_at" in data
    expires_at = datetime.fromisoformat(data["expires_at"].replace("Z", "+00:00"))
    now = datetime.now(UTC)
    delta = (expires_at - now).total_seconds()
    # expires_at should be ~ now + timeout (allow scheduling slack).
    assert timeout - 10 <= delta <= timeout + 10

    # Resolve so the task completes cleanly.
    resolve_ask_user_response(data["ask_id"], "Robot Cell A")
    result = await asyncio.wait_for(task, timeout=5)
    assert result == {"answer": "Robot Cell A"}
    _reset_global_state()


@pytest.mark.asyncio
async def test_options_none_excluded_from_payload() -> None:
    """When options/why are None, they are excluded (exclude_none=True)."""
    _reset_global_state()
    ctx, published = _make_context()

    task = asyncio.create_task(
        ask_user.coroutine(  # type: ignore[attr-defined]
            "Open question?",
            timeout_seconds=30,
            context=ctx,
        )
    )
    await asyncio.sleep(0.05)

    data = published[0].data
    assert "options" not in data
    assert "context" not in data
    assert data["timeout_seconds"] == 30
    assert "expires_at" in data

    resolve_ask_user_response(data["ask_id"], "whatever")
    await asyncio.wait_for(task, timeout=5)
    _reset_global_state()


@pytest.mark.asyncio
async def test_awaiting_user_toggled_around_wait() -> None:
    """While ask_user is blocked, is_awaiting_user(execution_id) is True."""
    _reset_global_state()
    ctx, published = _make_context(execution_id="exec-await-1")

    task = asyncio.create_task(
        ask_user.coroutine(  # type: ignore[attr-defined]
            "Blocking?", timeout_seconds=30, context=ctx
        )
    )
    # Let it publish + enter the wait (mark_awaiting_user called).
    await asyncio.sleep(0.05)
    try:
        assert is_awaiting_user("exec-await-1") is True

        # Resolve -> wait returns, finally clears the flag.
        ask_id = published[0].data["ask_id"]
        resolve_ask_user_response(ask_id, "yes")
        await asyncio.wait_for(task, timeout=5)

        # After completion the flag must be cleared.
        assert is_awaiting_user("exec-await-1") is False
    finally:
        _reset_global_state()


@pytest.mark.asyncio
async def test_awaiting_user_cleared_on_timeout() -> None:
    """If ask_user times out, the awaiting flag is still cleared in finally."""
    _reset_global_state()
    ctx, _ = _make_context(execution_id="exec-timeout-1")

    # Tiny timeout; never resolve the future.
    result = await ask_user.coroutine(  # type: ignore[attr-defined]
        "Will you answer?", timeout_seconds=0.1, context=ctx
    )
    assert "error" in result
    assert is_awaiting_user("exec-timeout-1") is False
    # And the pending ask was cleaned up.
    assert ask_user_module._pending_asks == {}
    _reset_global_state()


@pytest.mark.asyncio
async def test_no_event_bus_returns_error_without_marking() -> None:
    """Missing event bus short-circuits BEFORE touching the registry."""
    _reset_global_state()
    ctx = ToolContext(
        session=MagicMock(),
        user_id="test-user",
        _event_bus=None,
    )
    result = await ask_user.coroutine(  # type: ignore[attr-defined]
        "Q?", timeout_seconds=10, context=ctx
    )
    assert result == {
        "error": "Cannot ask user: no event bus available in this context"
    }
    # Registry untouched.
    assert is_awaiting_user("anything") is False
    assert ask_user_module._pending_asks == {}
    _reset_global_state()
