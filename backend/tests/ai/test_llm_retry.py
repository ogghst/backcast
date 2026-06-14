"""Unit tests for the shared LLM-retry primitives.

Covers :func:`iter_with_pausable_deadline` (the async-generator sibling
of :func:`await_with_pausable_deadline`) used to bound
``ctx.graph.astream_events``.

The specialist-scoped ``invoke_with_retry`` behaviour is already covered
by ``test_specialist_retry.py`` (which exercises the same code path via
the ``_invoke_specialist_with_retry`` re-export).
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

import pytest

from app.ai.execution.llm_retry import iter_with_pausable_deadline


async def _async_gen(items: list) -> AsyncIterator:
    """Yield *items* with no delay."""
    for item in items:
        yield item


async def _stalling_gen(after: float, *, tracker: dict | None = None) -> AsyncIterator:
    """Yield one item, then sleep *after* seconds before yielding the next.

    Used to force a stall past a short deadline.  When *tracker* is given,
    record whether the generator was closed (``aclose`` invoked) via the
    ``closed`` key."""
    try:
        yield "first"
        await asyncio.sleep(after)
        yield "should-not-reach"
    finally:
        if tracker is not None:
            tracker["closed"] = True


def _register_pending_ask(ask_id: str, execution_id: str = "exec-test") -> None:
    from app.ai.tools import ask_user

    loop = asyncio.get_running_loop()
    fut: asyncio.Future[str] = loop.create_future()
    ask_user._pending_asks[ask_id] = (fut, execution_id)


def _clear_pending_ask(ask_id: str) -> None:
    from app.ai.tools import ask_user

    ask_user._pending_asks.pop(ask_id, None)


# =====================================================================
# 1. Normal iteration: yields all items and returns when generator ends
# =====================================================================


@pytest.mark.asyncio
async def test_iter_yields_items_and_stops_at_end() -> None:
    """A well-behaved generator yields all items; iteration ends cleanly."""
    agen = _async_gen(["a", "b", "c"])
    out: list = []
    async for item in iter_with_pausable_deadline(agen, timeout=5.0, tick=0.1):
        out.append(item)

    assert out == ["a", "b", "c"]


# =====================================================================
# 2. Stalling generator: timeout fires, generator is closed, TimeoutError
# =====================================================================


@pytest.mark.asyncio
async def test_iter_stall_past_timeout_raises_and_closes_generator() -> None:
    """A generator that stalls past *timeout* raises TimeoutError.

    The deadline must trip on active (non-paused) time, the iteration
    must abort, and the underlying generator must be closed (its
    ``finally`` clause runs, recorded via *tracker*).
    """
    tracker: dict = {}
    agen = _stalling_gen(after=2.0, tracker=tracker)
    seen: list = []
    with pytest.raises((asyncio.TimeoutError, TimeoutError)):
        async for item in iter_with_pausable_deadline(agen, timeout=0.3, tick=0.1):
            seen.append(item)

    # First item was yielded before the stall.
    assert seen == ["first"]

    # The generator's finally clause ran -> aclose() was invoked by the
    # helper.  Give the close a tick to settle (the in-flight sleep is
    # cancelled by the helper before aclose).
    for _ in range(20):
        if tracker.get("closed"):
            break
        await asyncio.sleep(0.05)
    assert tracker.get("closed") is True, "generator was not closed after timeout"


# =====================================================================
# 3. Pausable deadline: ask_user pending -> clock does not accrue
# =====================================================================


@pytest.mark.asyncio
async def test_iter_pauses_while_ask_user_pending() -> None:
    """While an ask_user human-wait is pending, active time does NOT accrue.

    A long real sleep (well past the short timeout) completes successfully
    because the deadline is paused for the whole duration.
    """
    ask_id = "test-iter-ask-1"
    _register_pending_ask(ask_id)
    try:

        async def _slow_then_yield() -> AsyncIterator:
            # Real sleep longer than the timeout below (0.3s).  With an
            # ask pending the deadline never accrues past 0.3s.
            await asyncio.sleep(0.8)
            yield "done"

        agen = _slow_then_yield()
        out: list = []
        async for item in iter_with_pausable_deadline(
            agen,
            timeout=0.3,
            tick=0.1,
            execution_id="exec-test",  # matches _register_pending_ask
        ):
            out.append(item)

        assert out == ["done"]
    finally:
        _clear_pending_ask(ask_id)


# =====================================================================
# 4. No ask pending -> a real stall still trips the timeout (regression)
# =====================================================================


@pytest.mark.asyncio
async def test_iter_no_ask_pending_real_stall_times_out() -> None:
    """Regression guard: the pausable deadline must NOT disable stall
    protection when no ask_user is awaiting a human."""
    agen = _stalling_gen(after=2.0)
    with pytest.raises((asyncio.TimeoutError, TimeoutError)):
        async for _ in iter_with_pausable_deadline(agen, timeout=0.2, tick=0.1):
            pass
