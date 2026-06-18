"""Fault-injection test: a hung supervisor-level graph stream must honor
``request_stop`` promptly (within ~1-2s), NOT after the 600s graph budget.

Reproduces the empirical e2e bug WITHOUT the live server:

- A fake "graph stream" async generator that HANGS mid-step (mirrors a hung
  supervisor LLM call inside ``ctx.graph.astream_events``).
- Wrapped in the REAL :func:`iter_with_pausable_deadline` with the REAL
  :func:`_make_stop_predicate`, exactly like the real call site in
  ``agent_service._run_graph_astream_events``.
- The stop_event is registered with the REAL :class:`ExecutionLifecycle`
  via ``AgentService._register_stop_event``, so ``request_stop`` is the
  exact path that sets the event the predicate reads.
- After consumption has started (the generator is hung mid-step),
  ``request_stop`` fires from a concurrent task.  We assert
  :class:`ExecutionStoppedError` is raised within ~2s, NOT after the 60s
  graph timeout.

If the deadline honors stop in isolation (this test passes) the production
bug is specific to the real ``ctx.graph.astream_events`` path -- NOT to
the deadline/predicate wiring itself -- and the live-server investigation
(via event-id diagnostic logging) is the next step.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator
from typing import Any

import pytest

from app.ai.agent_service import AgentService, _make_stop_predicate
from app.ai.exceptions import ExecutionStoppedError
from app.ai.execution.agent_event_bus import AgentEventBus
from app.ai.execution.lifecycle import execution_lifecycle
from app.ai.execution.llm_retry import iter_with_pausable_deadline


@pytest.fixture(autouse=True)
def _isolate_lifecycle_registry() -> Any:
    """Snapshot and fully restore the module-level execution_lifecycle.

    The lifecycle is a process singleton holding ``_contexts`` /
    ``_pending`` maps.  Tests that register executions must not leak into
    sibling tests.  We restore the exact prior state (or a clean slate if
    the registry was mutated by an earlier failing test).
    """
    saved_ctx = dict(execution_lifecycle._contexts)
    saved_pending = dict(execution_lifecycle._pending)
    try:
        # Start each test from a clean registry so leftover entries from
        # other tests cannot mask a stop (an unknown eid is a no-op).
        execution_lifecycle._contexts.clear()
        execution_lifecycle._pending.clear()
        yield
    finally:
        execution_lifecycle._contexts.clear()
        execution_lifecycle._pending.clear()
        execution_lifecycle._contexts.update(saved_ctx)
        execution_lifecycle._pending.update(saved_pending)


async def _hung_graph_stream() -> AsyncIterator[dict[str, Any]]:
    """Yield one event, then hang forever (mirrors a hung supervisor call).

    The first yield lets the consumer enter the ``async for`` body so the
    generator is genuinely "in flight mid-step" when the hang occurs.
    """
    yield {"event": "on_chain_start", "name": "supervisor"}
    # Hang forever -- this is the analog of a supervisor LLM call that
    # never returns inside ``astream_events``.
    await asyncio.Event().wait()
    yield {"event": "on_chain_end"}  # unreachable


async def _ask_user_blocked_stream(
    execution_id: str, ask_id: str
) -> AsyncIterator[dict[str, Any]]:
    """Yield one event, then block on a pending ask_user future.

    Mirrors the EXACT failing e2e scenario: the supervisor called ask_user
    (a human-wait).  The deadline's tick loop must STILL fire while the
    step is suspended on the ask_user future, and when ``request_stop``
    sets the stop_event, ``should_stop`` must return True (stop takes
    priority over the ask_user pause) within ~1 tick.

    Registers a pending ask via ``ask_user._pending_asks`` and
    ``mark_awaiting_user`` exactly like the real tool, so
    ``_awaiting_human`` returns True (the deadline PAUSE branch).  When the
    future is cancelled by ``request_stop`` (the fix), this generator
    mirrors the real ``ask_user`` tool's ``CancelledError`` handler: it
    yields a synthetic ``on_tool_end`` event instead of propagating the
    cancellation, so the surrounding deadline sees the step complete and
    the supervisor's stop check finalizes the run.
    """
    from app.ai.tools import ask_user

    yield {"event": "on_chain_start", "name": "supervisor"}
    # Mirror what the real ask_user tool does immediately before awaiting.
    loop = asyncio.get_running_loop()
    fut: asyncio.Future[str] = loop.create_future()
    ask_user._pending_asks[ask_id] = (fut, execution_id)
    ask_user.mark_awaiting_user(execution_id)
    cancelled = False
    try:
        # Block on the ask_user future -- this is where the graph's
        # astream_events __anext__ is suspended in production.
        await fut
    except asyncio.CancelledError:
        # Mirrors the real ask_user tool: request_stop cancelled the
        # future; return a synthetic value rather than propagating.
        cancelled = True
    finally:
        ask_user.clear_awaiting_user(execution_id)
        ask_user._pending_asks.pop(ask_id, None)
    if cancelled:
        yield {"event": "on_tool_end", "name": "ask_user", "cancelled": True}
    else:
        yield {"event": "on_chain_end"}


@pytest.mark.asyncio
async def test_hung_supervisor_stream_honors_request_stop_promptly() -> None:
    """A hung graph stream wrapped in the pausable deadline must surface
    ExecutionStoppedError within ~2s of ``request_stop`` firing -- NOT
    after the 60s graph timeout.

    This reproduces the e2e scenario where a supervisor-level LLM call
    inside ``astream_events`` hangs and ``request_stop`` is set externally.
    """
    eid = "exec-hung-supervisor-stop-test"
    bus = AgentEventBus(execution_id=eid)

    # Mirror the real wiring: one Event created by _register_stop_event,
    # registered with the lifecycle, AND returned so the SAME object flows
    # into GraphContext.stop_event -> _make_stop_predicate.
    stop_event = AgentService._register_stop_event(eid, bus)
    assert stop_event is execution_lifecycle._contexts[eid].stop_event, (
        "_register_stop_event must register the SAME object it returns "
        "(otherwise the predicate reads a different event than request_stop sets)"
    )

    should_stop = _make_stop_predicate(stop_event)
    assert should_stop is not None, "predicate must be built for a non-None event"

    deadline_timeout = 60.0  # mimics AI_GRAPH_EXECUTION_TIMEOUT (scaled down)
    started = time.monotonic()
    fired_at: list[float] = []
    raised_exc: BaseException | None = None

    async def consumer() -> None:
        nonlocal raised_exc
        try:
            async for _event in iter_with_pausable_deadline(
                _hung_graph_stream(),
                timeout=deadline_timeout,
                execution_id=eid,
                should_stop=should_stop,
            ):
                # First event yielded here -- the generator is now hung on
                # its NEXT __anext__.  Signal the stop in a sibling task.
                if not fired_at:
                    fired_at.append(time.monotonic())
        except ExecutionStoppedError:
            raised_exc = ExecutionStoppedError("paused-deadline")
        except BaseException as exc:  # noqa: BLE001 - record whatever fires
            raised_exc = exc

    consumer_task = asyncio.create_task(consumer())

    # Wait until the consumer has entered the loop body (the generator is
    # now hung mid-step), then fire request_stop exactly as the WS path does.
    while not fired_at:
        await asyncio.sleep(0.02)
        if time.monotonic() - started > 5.0:
            pytest.fail("consumer never yielded its first (pre-hang) event")

    # The generator is hung.  Fire the stop via the SAME path the WS uses.
    stop_set_ok = execution_lifecycle.request_stop(eid)
    assert stop_set_ok, "request_stop must find the registered execution"
    stop_fired_at = time.monotonic()

    # The deadline should honor stop within ~1-2s (a few tick windows).
    # It must NOT wait for the 60s timeout.
    try:
        await asyncio.wait_for(consumer_task, timeout=5.0)
    except TimeoutError:
        pytest.fail(
            "iter_with_pausable_deadline did NOT honor request_stop within 5s "
            "on a hung step (consumer still blocked)"
        )

    elapsed = time.monotonic() - stop_fired_at
    assert isinstance(raised_exc, ExecutionStoppedError), (
        f"expected ExecutionStoppedError, got {type(raised_exc).__name__}: {raised_exc}"
    )
    # Stop should land well under the deadline; allow generous headroom for CI.
    assert elapsed < 3.0, (
        f"stop fired but took {elapsed:.2f}s to propagate (expected < ~2s; "
        f"deadline was {deadline_timeout}s)"
    )


@pytest.mark.asyncio
async def test_ask_user_blocked_stream_honors_request_stop_promptly() -> None:
    """The EXACT failing e2e scenario: the supervisor called ask_user and is
    blocked on its human-response future (no human responding).  The deadline
    tick loop must STILL fire while the step is suspended on the future, and
    when ``request_stop`` sets the stop_event, ``should_stop`` must return
    True (stop takes priority over the ask_user pause) within ~1-2s -- NOT
    after the 60s graph budget and NOT stuck forever.

    This is the path the live server failed on (execution stayed ``running``
    past the graph timeout instead of finalizing ``stopped``).
    """
    eid = "exec-askuser-supervisor-stop-test"
    ask_id = "ask-supervisor-stop-test-1"
    bus = AgentEventBus(execution_id=eid)
    stop_event = AgentService._register_stop_event(eid, bus)
    should_stop = _make_stop_predicate(stop_event)
    assert should_stop is not None

    deadline_timeout = 60.0
    started = time.monotonic()
    entered_body_at: list[float] = []
    raised_exc: BaseException | None = None

    async def consumer() -> None:
        nonlocal raised_exc
        try:
            async for _event in iter_with_pausable_deadline(
                _ask_user_blocked_stream(eid, ask_id),
                timeout=deadline_timeout,
                execution_id=eid,
                should_stop=should_stop,
            ):
                if not entered_body_at:
                    entered_body_at.append(time.monotonic())
        except ExecutionStoppedError:
            raised_exc = ExecutionStoppedError("paused-deadline")
        except BaseException as exc:  # noqa: BLE001
            raised_exc = exc

    consumer_task = asyncio.create_task(consumer())

    # Wait until the consumer entered the loop body (the generator is now
    # blocked on the ask_user future).
    while not entered_body_at:
        await asyncio.sleep(0.02)
        if time.monotonic() - started > 5.0:
            pytest.fail("consumer never yielded its first (pre-ask) event")

    # Poll until the generator has actually registered the ask and marked
    # itself awaiting (this happens on the SECOND __anext__, after the
    # first yield).  The deadline's wait_for on that __anext__ is in flight.
    from app.ai.tools import ask_user

    deadline_setup = time.monotonic()
    while not ask_user.is_awaiting_user(eid):
        await asyncio.sleep(0.02)
        if time.monotonic() - deadline_setup > 5.0:
            pytest.fail(
                "test setup: generator never marked ask_user awaiting "
                "(is_awaiting_user stayed False)"
            )

    # Confirm the deadline is actually paused (ask_user is pending) so this
    # mirrors production: _awaiting_human(eid) is True.
    assert ask_user.is_awaiting_user(eid), (
        "test setup: ask_user must be marked awaiting for the pause branch"
    )

    # The generator is blocked on the ask_user future.  Fire the stop via
    # the SAME path the WS disconnect grace uses.
    stop_fired_at = time.monotonic()
    assert execution_lifecycle.request_stop(eid) is True

    try:
        await asyncio.wait_for(consumer_task, timeout=5.0)
    except TimeoutError:
        pytest.fail(
            "iter_with_pausable_deadline did NOT honor request_stop within 5s "
            "while blocked on a pending ask_user (consumer still blocked)"
        )

    elapsed = time.monotonic() - stop_fired_at
    assert isinstance(raised_exc, ExecutionStoppedError), (
        f"expected ExecutionStoppedError, got {type(raised_exc).__name__}: {raised_exc}"
    )
    assert elapsed < 3.0, (
        f"stop fired but took {elapsed:.2f}s to propagate while blocked on "
        f"ask_user (expected < ~2s; deadline was {deadline_timeout}s)"
    )
    # Sanity: the ask_user future was cleaned up by the generator's finally.
    assert ask_id not in ask_user._pending_asks
