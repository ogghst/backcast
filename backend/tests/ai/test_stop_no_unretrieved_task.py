"""Regression: a user stop mid-specialist must not leak an unretrieved task.

Root cause: when ``ctx.stop_event`` is set, both pausable-deadline
checkpoints raise ``ExecutionStoppedError``.  The specialist-level one
(``await_with_pausable_deadline``) propagates up through langgraph/langchain's
streaming task tree; langchain's teardown only suppresses ``CancelledError``,
so ``ExecutionStoppedError`` (a foreign exception type) leaked from an
internal generator-close task as
``asyncio - ERROR - Task exception was never retrieved``.

Fix: the pausable-deadline helpers now ``await`` the cancelled underlying task
on every exit path (``_cancel_and_drain``) so its terminal exception is
retrieved AND langchain's ``finally`` teardown runs in the cancelling context.

These tests assert no unretrieved ``ExecutionStoppedError`` reaches the loop's
exception handler during a clean stop.  They install a capturing handler on
the test loop (strict-mode ``pytest-asyncio``) and pump it briefly so any
orphaned task gets a chance to surface.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from app.ai.exceptions import ExecutionStoppedError
from app.ai.execution.llm_retry import (
    _cancel_and_drain,
    await_with_pausable_deadline,
    iter_with_pausable_deadline,
)

# ---------------------------------------------------------------------------
# Loop exception-handler capture helper
# ---------------------------------------------------------------------------


def _install_capturing_handler(
    loop: asyncio.AbstractEventLoop,
) -> list[dict[str, Any]]:
    """Replace the loop's exception handler with one that records every call.

    Returns the list each ``call_exception_handler`` invocation appends a
    context dict to.  Restoring the default handler is the caller's job.
    """
    captured: list[dict[str, Any]] = []

    def handler(loop_: asyncio.AbstractEventLoop, context: dict[str, Any]) -> None:
        captured.append(context)

    loop.set_exception_handler(handler)
    return captured


def _unretrieved_stops(contexts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Filter captured contexts down to the bug signature."""
    return [
        c
        for c in contexts
        if c.get("message") == "Task exception was never retrieved"
        and isinstance(c.get("exception"), ExecutionStoppedError)
    ]


# ===========================================================================
# await_with_pausable_deadline: stop path must not orphan a task
# ===========================================================================


@pytest.mark.asyncio
async def test_await_stop_does_not_leak_unretrieved_task() -> None:
    """A user stop mid-await must surface ``ExecutionStoppedError`` WITHOUT
    leaking an unretrieved task exception.

    Drives a 5s ``asyncio.sleep`` under a 30s active deadline with a 0.1s tick,
    flipping ``should_stop`` True after ~0.2s of wall time.  We then pump the
    loop briefly so any orphaned task would be GC'd/retrieved, and assert the
    capturing handler saw no unretrieved ``ExecutionStoppedError``.
    """
    loop = asyncio.get_running_loop()
    captured = _install_capturing_handler(loop)
    try:
        started = loop.time()
        stop_at = started + 0.2

        def should_stop() -> bool:
            return loop.time() >= stop_at

        with pytest.raises(ExecutionStoppedError):
            await await_with_pausable_deadline(
                asyncio.sleep(5),
                timeout=30.0,
                tick=0.1,
                should_stop=should_stop,
            )

        # Give any orphaned internal task a window to be scheduled, run its
        # ``finally`` teardown, and be retrieved/GC'd.  Two yield points + a
        # short sleep is enough to surface the bug if it regressed.
        for _ in range(3):
            await asyncio.sleep(0)
        await asyncio.sleep(0.2)
    finally:
        loop.set_exception_handler(None)  # restore default

    leaked = _unretrieved_stops(captured)
    assert leaked == [], (
        f"expected no unretrieved ExecutionStoppedError, got: {leaked!r}"
    )


# ===========================================================================
# iter_with_pausable_deadline: stop path must not orphan the in-flight step
# ===========================================================================


@pytest.mark.asyncio
async def test_iter_stop_does_not_leak_unretrieved_task() -> None:
    """Sibling of the await case, for the async-generator shape used by the
    top-level ``astream_events`` loop.

    An async generator that blocks on ``asyncio.sleep`` between yields is
    iterated under a pausable deadline; ``should_stop`` flips True shortly
    after the first ``__anext__`` is in flight, forcing the ``finally`` to
    drain the still-running step task.
    """

    async def slow_agen() -> Any:
        # First __anext__ blocks long enough for the stop to trip mid-flight.
        await asyncio.sleep(5)
        yield "unreached"

    loop = asyncio.get_running_loop()
    captured = _install_capturing_handler(loop)
    try:
        started = loop.time()
        stop_at = started + 0.2

        def should_stop() -> bool:
            return loop.time() >= stop_at

        with pytest.raises(ExecutionStoppedError):
            async for _ in iter_with_pausable_deadline(
                slow_agen(),
                timeout=30.0,
                tick=0.1,
                should_stop=should_stop,
            ):
                pass

        for _ in range(3):
            await asyncio.sleep(0)
        await asyncio.sleep(0.2)
    finally:
        loop.set_exception_handler(None)

    leaked = _unretrieved_stops(captured)
    assert leaked == [], (
        f"expected no unretrieved ExecutionStoppedError, got: {leaked!r}"
    )


# ===========================================================================
# _cancel_and_drain: unit tests for the helper itself
# ===========================================================================


@pytest.mark.asyncio
class TestCancelAndDrain:
    async def test_drains_running_task_terminal_exception(self) -> None:
        """A task that raises on cancellation must not leak."""

        async def boom_on_cancel() -> None:
            try:
                await asyncio.sleep(10)
            except asyncio.CancelledError:
                # Simulate a langchain-style finally that re-raises a foreign
                # exception (the leak shape this fix targets).
                raise ExecutionStoppedError("paused-deadline") from None

        task = asyncio.ensure_future(boom_on_cancel())
        # Let the task actually enter the sleep before we drain it.
        await asyncio.sleep(0)
        # Must not raise -- the helper swallows the terminal exception.
        await _cancel_and_drain(task)
        assert task.done()

    async def test_idempotent_on_already_done_task(self) -> None:
        """Calling drain on a completed task is a safe no-op."""
        task = asyncio.ensure_future(asyncio.sleep(0))
        await asyncio.sleep(0.05)  # let it finish
        assert task.done()
        await _cancel_and_drain(task)  # must not raise
        assert task.done()

    async def test_retrieves_cancelled_error_without_warning(self) -> None:
        """Draining a plain cancelled task must not surface as unretrieved."""
        loop = asyncio.get_running_loop()
        captured = _install_capturing_handler(loop)
        try:
            task = asyncio.ensure_future(asyncio.sleep(10))
            await asyncio.sleep(0)
            await _cancel_and_drain(task)
            for _ in range(3):
                await asyncio.sleep(0)
            await asyncio.sleep(0.1)
        finally:
            loop.set_exception_handler(None)

        leaked = [
            c
            for c in captured
            if c.get("message") == "Task exception was never retrieved"
        ]
        assert leaked == []
