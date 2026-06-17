"""Tests for Fix D: hard per-execution ask_user cap.

A model that re-asks can drive dozens of user-facing ask_user prompts per
execution (39 observed).  This adds a hard per-execution cap enforced INSIDE
the ask_user tool BEFORE it publishes an event or marks the execution
awaiting-user.  When the cap is hit the tool returns a synthetic
``{"answer": ..., "capped": True}`` (its own return value, like the existing
timeout ``{"error": ...}``) so the model proceeds with gathered information
instead of blocking on a question.

These tests use a fake event bus whose ``publish`` records calls, and the
``execution_id`` attribute the tool reads.  They reset the module-level
``_ask_counts`` registry between tests.
"""

from __future__ import annotations

from typing import Any

import pytest

from app.ai.tools import ask_user as ask_user_module
from app.ai.tools.ask_user import _ask_counts, ask_user
from app.ai.tools.types import ToolContext

# ``@ai_tool`` wraps the function into a LangChain StructuredTool, so to test
# the cap logic directly (bypassing BaseTool arg-schema validation) we invoke
# the underlying coroutine.  ``context`` is passed explicitly as a kwarg.
_ask_user_fn = ask_user.coroutine

CAP = 3  # override the default for fast, deterministic tests


class _FakeEventBus:
    """Minimal stand-in for AgentEventBus that ask_user needs.

    Records every ``publish`` call so tests can assert the capped call did NOT
    publish.  ``execution_id`` is what ask_user reads to key the cap.
    """

    def __init__(self, execution_id: str) -> None:
        self.execution_id = execution_id
        self.published: list[Any] = []

    def publish(self, event: Any) -> None:
        self.published.append(event)


@pytest.fixture
def reset_counts() -> Any:
    """Clear the module-level _ask_counts registry before and after each test."""
    _ask_counts.clear()
    yield
    _ask_counts.clear()


@pytest.fixture(autouse=True)
def _small_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    """Lower the cap to CAP for fast tests."""
    monkeypatch.setattr(ask_user_module, "AI_MAX_ASK_USER_PER_EXECUTION", CAP)


def _make_context(bus: _FakeEventBus) -> ToolContext:
    """Build a ToolContext carrying the fake event bus."""
    ctx = ToolContext.__new__(ToolContext)
    ctx._event_bus = bus  # type: ignore[attr-defined]
    return ctx


# ===========================================================================
# After CAP successful resolves, the next call is capped (no publish)
# ===========================================================================


@pytest.mark.asyncio
async def test_call_is_capped_after_limit(reset_counts: Any) -> None:
    """After CAP publishes, the (CAP+1)th call returns capped and does NOT publish."""

    bus = _FakeEventBus("exec-1")
    ctx = _make_context(bus)

    # Simulate CAP prior successful publishes by inflating the count directly.
    _ask_counts["exec-1"] = CAP

    coro = _ask_user_fn("Another question?", context=ctx)
    result = await coro

    assert result.get("capped") is True
    assert "answer" in result
    # The capped call must NOT have published an ask_user event.
    assert bus.published == []
    # The count is not incremented for a capped call.
    assert _ask_counts.get("exec-1") == CAP
    # And the execution must NOT be marked awaiting-user (no blocking future).
    from app.ai.tools.ask_user import is_awaiting_user

    assert is_awaiting_user("exec-1") is False


@pytest.mark.asyncio
async def test_successful_call_publishes_and_increments(reset_counts: Any) -> None:
    """A call under the cap publishes and increments the per-execution count."""
    bus = _FakeEventBus("exec-2")
    ctx = _make_context(bus)

    # Resolve the future immediately so ask_user returns promptly.
    import asyncio

    from app.ai.tools.ask_user import _pending_asks

    # Schedule the resolution before awaiting.
    async def _resolve_after_publish() -> None:
        # Wait a tick for ask_user to register its future.
        await asyncio.sleep(0)
        for _ask_id, (fut, _eid) in list(_pending_asks.items()):
            if _eid == "exec-2" and not fut.done():
                fut.set_result("user said yes")
                break

    asyncio.create_task(_resolve_after_publish())

    result = await _ask_user_fn("First question?", context=ctx)

    assert result.get("answer") == "user said yes"
    assert bus.published, "an ask_user event must have been published"
    assert _ask_counts.get("exec-2") == 1


# ===========================================================================
# cancel_asks_for_execution clears the count
# ===========================================================================


def test_cancel_asks_clears_count(reset_counts: Any) -> None:
    """cancel_asks_for_execution pops the per-execution count (stop/disconnect)."""
    from app.ai.tools.ask_user import cancel_asks_for_execution

    _ask_counts["exec-3"] = CAP
    cancel_asks_for_execution("exec-3")
    assert "exec-3" not in _ask_counts


def test_cancel_asks_clears_count_independent_of_others(reset_counts: Any) -> None:
    """Clearing one execution's count does not affect another's."""
    from app.ai.tools.ask_user import cancel_asks_for_execution

    _ask_counts["exec-a"] = 2
    _ask_counts["exec-b"] = 3
    cancel_asks_for_execution("exec-a")
    assert "exec-a" not in _ask_counts
    assert _ask_counts.get("exec-b") == 3


# ===========================================================================
# Per-execution isolation: different execution_ids have independent caps
# ===========================================================================


@pytest.mark.asyncio
async def test_cap_is_per_execution(reset_counts: Any) -> None:
    """exec-1 hitting its cap does not cap exec-2."""
    bus1 = _FakeEventBus("exec-1")
    ctx1 = _make_context(bus1)
    _ask_counts["exec-1"] = CAP

    bus2 = _FakeEventBus("exec-2")
    ctx2 = _make_context(bus2)

    r1 = await _ask_user_fn("capped?", context=ctx1)
    assert r1.get("capped") is True

    # exec-2 is at 0 -> NOT capped (it would publish). We can't easily resolve
    # the future, so assert the cap guard did not trip by checking publish.
    import asyncio

    from app.ai.tools.ask_user import _pending_asks

    async def _resolve() -> None:
        await asyncio.sleep(0)
        for _ask_id, (fut, _eid) in list(_pending_asks.items()):
            if _eid == "exec-2" and not fut.done():
                fut.set_result("ok")
                break

    asyncio.create_task(_resolve())
    r2 = await _ask_user_fn("fresh?", context=ctx2)
    assert r2.get("answer") == "ok"
    assert "capped" not in r2
    assert bus2.published


# ===========================================================================
# Default cap value sanity (the re-exported setting)
# ===========================================================================


def test_default_cap_is_eight() -> None:
    """The shipped default is 8 (generous legit round, far below the 39 seen)."""
    # Undo the autouse small-cap monkeypatch by reading the source Settings.
    from app.core.config import settings

    assert settings.AI_MAX_ASK_USER_PER_EXECUTION == 8
