"""Tests for the transport-agnostic ExecutionLifecycle coordinator.

Covers the protocol-agnostic execution lifecycle extracted from the
WebSocket-coupled flow in ``agent_service``.  The lifecycle owns the bounded
``execution_id -> _ExecutionContext`` registry (non-destructive eviction),
opaque-token presence attach/detach + the disconnect-grace-stop bridge, and
the single terminal cleanup (ask-cancel + bus-remove + registry-drop).

Model B: event delivery stays bus-subscription based (the lifecycle does NOT
fan events out through the tokens); the tokens only represent "a transport
is present" for grace/cleanup decisions.  ``publish``/``on_event`` were
removed, so this module no longer tests them.

Settings are monkeypatched to tiny values (grace window, registry cap) so the
tests run fast and exercise eviction without polluting global config.
"""

from __future__ import annotations

import asyncio

import pytest

from app.ai.execution.agent_event_bus import AgentEventBus
from app.ai.execution.lifecycle import ExecutionLifecycle
from app.ai.tools import ask_user

# =====================================================================
# Fixtures / helpers
# =====================================================================


def _make_bus(execution_id: str = "exec-test") -> AgentEventBus:
    return AgentEventBus(execution_id=execution_id)


def _token() -> object:
    """A fresh opaque, hashable presence token (one per simulated transport)."""
    return object()


@pytest.fixture
def small_grace(monkeypatch: pytest.MonkeyPatch) -> float:
    """Patch the disconnect grace window to a tiny value and return it."""
    from app.core.config import settings

    grace = 0.05
    monkeypatch.setattr(settings, "AI_DISCONNECT_GRACE_SECONDS", grace)
    return grace


@pytest.fixture
def fresh_lifecycle() -> ExecutionLifecycle:
    """A fresh ExecutionLifecycle with an empty registry for each test."""
    return ExecutionLifecycle()


def _register_pending_ask(ask_id: str, execution_id: str) -> None:
    """Register a non-done Future in ask_user._pending_asks for a test."""
    loop = asyncio.get_running_loop()
    fut: asyncio.Future[str] = loop.create_future()
    ask_user._pending_asks[ask_id] = (fut, execution_id)


# =====================================================================
# 1. Non-destructive eviction
# =====================================================================


@pytest.mark.asyncio
async def test_eviction_is_non_destructive(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Overflow drops oldest + warns, but does NOT .set() the evicted event.

    Regression guard for the bug where the old AgentService._stop_events
    registry .set() the evicted event, spuriously stopping a live execution.
    """
    from app.core.config import settings

    monkeypatch.setattr(settings, "AI_EXECUTION_REGISTRY_MAX", 2)
    lc = ExecutionLifecycle()

    bus_a = _make_bus("exec-A")
    bus_b = _make_bus("exec-B")
    bus_c = _make_bus("exec-C")

    stop_a = asyncio.Event()
    stop_b = asyncio.Event()
    stop_c = asyncio.Event()

    lc.register("exec-A", stop_a, bus_a)
    lc.register("exec-B", stop_b, bus_b)
    # Registry now at capacity (2) — registering exec-C must drop exec-A.
    lc.register("exec-C", stop_c, bus_c)

    # exec-A was dropped from the registry...
    assert "exec-A" not in lc._contexts
    assert "exec-B" in lc._contexts
    assert "exec-C" in lc._contexts
    # ...but its stop_event was NEVER set (non-destructive eviction).
    assert stop_a.is_set() is False
    # The dropped execution is simply untracked; request_stop returns False.
    assert lc.request_stop("exec-A") is False


# =====================================================================
# 2. opaque-token attach / detach
# =====================================================================


@pytest.mark.asyncio
async def test_attach_detach_opaque_token(fresh_lifecycle: ExecutionLifecycle) -> None:
    """attach records the opaque token; detach removes it; both are no-ops for
    unknown executions or unattached tokens."""
    lc = fresh_lifecycle
    bus = _make_bus("exec-token")
    stop = asyncio.Event()
    lc.register("exec-token", stop, bus)

    tok = _token()
    assert lc.attach("exec-token", tok) is True
    ctx = lc._contexts["exec-token"]
    assert tok in ctx.observers

    # Attaching the same token again is idempotent (set semantics).
    assert lc.attach("exec-token", tok) is True
    assert len(ctx.observers) == 1

    # A second distinct token coexists.
    tok2 = _token()
    lc.attach("exec-token", tok2)
    assert {tok, tok2} == ctx.observers

    # Detaching one observer leaves the other; no grace task yet (still observed).
    lc.detach("exec-token", tok)
    assert tok not in ctx.observers
    assert tok2 in ctx.observers
    assert ctx.grace_task is None

    # Detaching an unknown execution / unattached token is a safe no-op.
    lc.detach("exec-token", tok)  # already detached
    lc.detach("exec-unknown", tok)


# =====================================================================
# 3. pending-token path: attach before register, register pulls it in
# =====================================================================


@pytest.mark.asyncio
async def test_pending_token_attach_before_register(
    fresh_lifecycle: ExecutionLifecycle,
) -> None:
    """attach before register holds the token in _pending; register pulls it
    into the new context so presence-tracking is robust regardless of the
    start/attach ordering."""
    lc = fresh_lifecycle
    tok = _token()

    # attach BEFORE register: returns True, token held in _pending.
    assert lc.attach("exec-pending", tok) is True
    assert "exec-pending" not in lc._contexts
    assert tok in lc._pending["exec-pending"]

    # Now register: the pending token must move into the context's observers.
    bus = _make_bus("exec-pending")
    stop = asyncio.Event()
    lc.register("exec-pending", stop, bus)

    assert "exec-pending" not in lc._pending  # drained
    ctx = lc._contexts["exec-pending"]
    assert tok in ctx.observers


@pytest.mark.asyncio
async def test_pending_token_detach_during_window(
    fresh_lifecycle: ExecutionLifecycle,
) -> None:
    """detach also discards from _pending (attach-before-register that was
    detached before register ever ran leaves nothing behind)."""
    lc = fresh_lifecycle
    tok = _token()

    lc.attach("exec-pending2", tok)
    assert tok in lc._pending["exec-pending2"]

    lc.detach("exec-pending2", tok)
    assert "exec-pending2" not in lc._pending  # empty set popped

    # Later register pulls nothing in.
    bus = _make_bus("exec-pending2")
    stop = asyncio.Event()
    lc.register("exec-pending2", stop, bus)
    assert lc._contexts["exec-pending2"].observers == set()


# =====================================================================
# 4. attach cancels a pending grace-stop
# =====================================================================


@pytest.mark.asyncio
async def test_attach_cancels_pending_grace_stop(
    fresh_lifecycle: ExecutionLifecycle, small_grace: float
) -> None:
    """A re-attach within the grace window cancels the pending grace-stop."""
    lc = fresh_lifecycle
    bus = _make_bus("exec-attach")
    stop = asyncio.Event()
    lc.register("exec-attach", stop, bus)

    tok1 = _token()
    tok2 = _token()

    assert lc.attach("exec-attach", tok1) is True
    # Detaching the last token schedules a grace-stop task.
    lc.detach("exec-attach", tok1)
    ctx = lc._contexts["exec-attach"]
    assert ctx.grace_task is not None

    # Re-attach before the grace window elapses.
    assert lc.attach("exec-attach", tok2) is True
    # The grace task must be cancelled/cleared by attach.
    assert ctx.grace_task is None

    # Let the original grace window pass — no stop should fire.
    await asyncio.sleep(small_grace + 0.05)
    assert stop.is_set() is False
    assert lc.is_stopping("exec-attach") is False


# =====================================================================
# 5. detach of the last observer schedules a grace-stop that fires
# =====================================================================


@pytest.mark.asyncio
async def test_detach_last_observer_schedules_grace_stop(
    fresh_lifecycle: ExecutionLifecycle, small_grace: float
) -> None:
    """Detaching the last token fires request_stop after the grace window."""
    lc = fresh_lifecycle
    bus = _make_bus("exec-detach")
    stop = asyncio.Event()
    lc.register("exec-detach", stop, bus)

    tok = _token()
    lc.attach("exec-detach", tok)
    lc.detach("exec-detach", tok)

    ctx = lc._contexts["exec-detach"]
    assert ctx.grace_task is not None

    # Before the grace window: not stopping.
    assert stop.is_set() is False

    # After the grace window: request_stop fired.
    await asyncio.sleep(small_grace + 0.1)
    assert stop.is_set() is True
    assert lc.is_stopping("exec-detach") is True
    # The grace task cleared itself after firing.
    assert ctx.grace_task is None


# =====================================================================
# 6. re-attach before grace expiry cancels the stop
# =====================================================================


@pytest.mark.asyncio
async def test_reattach_before_grace_expiry_no_stop(
    fresh_lifecycle: ExecutionLifecycle, small_grace: float
) -> None:
    """Detach then re-attach then wait -> no stop fires."""
    lc = fresh_lifecycle
    bus = _make_bus("exec-reattach")
    stop = asyncio.Event()
    lc.register("exec-reattach", stop, bus)

    tok1 = _token()
    lc.attach("exec-reattach", tok1)
    lc.detach("exec-reattach", tok1)
    # Re-attach halfway through the grace window.
    await asyncio.sleep(small_grace / 2)
    tok2 = _token()
    assert lc.attach("exec-reattach", tok2) is True

    # Wait well past the original grace window.
    await asyncio.sleep(small_grace + 0.1)
    assert stop.is_set() is False


# =====================================================================
# 7. terminate cancels asks + removes bus + drops registry + drops tokens
#    (idempotent)
# =====================================================================


@pytest.mark.asyncio
async def test_terminate_idempotent_and_cleans_up(
    fresh_lifecycle: ExecutionLifecycle, monkeypatch: pytest.MonkeyPatch
) -> None:
    """terminate cancels asks, removes the bus, drops the context; idempotent."""
    lc = fresh_lifecycle
    eid = "exec-term"

    # Register a bus in the runner_manager so terminate's remove_bus has work.
    from app.ai.execution.runner_manager import runner_manager

    # Clean any pre-existing entry from a prior test.
    runner_manager._buses.pop(eid, None)
    bus = runner_manager.create_bus(eid)
    stop = asyncio.Event()
    lc.register(eid, stop, bus)

    # Register a pending ask for this execution so cancel has something to do.
    ask_id = "ask-term-1"
    _register_pending_ask(ask_id, eid)
    assert ask_id in ask_user._pending_asks

    tok = _token()
    lc.attach(eid, tok)
    lc.detach(eid, tok)

    # First terminate: cancels grace task, marks terminal, cancels asks,
    # removes bus, drops context.
    lc.terminate(eid)
    assert eid not in lc._contexts
    assert ask_id not in ask_user._pending_asks
    assert runner_manager.get_bus(eid) is None

    # Second terminate: idempotent no-op (must not raise).
    lc.terminate(eid)
    assert eid not in lc._contexts

    # request_stop on a terminated/unknown execution returns False.
    assert lc.request_stop(eid) is False


@pytest.mark.asyncio
async def test_terminate_drops_pending_and_attached_tokens(
    fresh_lifecycle: ExecutionLifecycle,
) -> None:
    """terminate discards both pending tokens (attach-before-register) and
    tokens attached to a registered context."""
    lc = fresh_lifecycle
    eid = "exec-tok"

    # A pending token (attach before register).
    pending_tok = _token()
    lc.attach(eid, pending_tok)
    assert eid in lc._pending

    # Register + attach a live token.
    bus = _make_bus(eid)
    stop = asyncio.Event()
    lc.register(eid, stop, bus)
    live_tok = _token()
    lc.attach(eid, live_tok)

    lc.terminate(eid)
    # No token state leaks.
    assert eid not in lc._contexts
    assert eid not in lc._pending


# =====================================================================
# 8. is_stopping reflects the stop_event
# =====================================================================


def test_is_stopping_reflects_stop_event(
    fresh_lifecycle: ExecutionLifecycle,
) -> None:
    """is_stopping is True iff registered and stop_event.is_set()."""
    lc = fresh_lifecycle
    bus = _make_bus("exec-stopping")
    stop = asyncio.Event()
    lc.register("exec-stopping", stop, bus)

    assert lc.is_stopping("exec-stopping") is False
    assert lc.is_stopping("unknown") is False  # not registered

    stop.set()
    assert lc.is_stopping("exec-stopping") is True


# =====================================================================
# 9. Regression: subscribe (reconnect) then disconnect detaches the
#    observer promptly and schedules the grace-stop (not blocked)
# =====================================================================


@pytest.mark.asyncio
async def test_subscribe_then_disconnect_schedules_grace_promptly(
    fresh_lifecycle: ExecutionLifecycle, small_grace: float
) -> None:
    """Reconnect (attach) followed by disconnect (detach) must detach the
    observer token and schedule the grace-stop WITHOUT delay.

    Regression guard for the WS thin-transport bug in ``ai_chat.py``'s
    ``subscribe`` handler: the handler used to ``await
    forward_bus_events(...)`` inline, which blocked the message loop.
    On a reconnect-then-disconnect the inline await kept the loop stuck
    inside the forwarding task (which only broke when
    ``is_websocket_connected`` flipped, lagging for half-closed
    sockets), so the disconnect ``finally`` did not run promptly and the
    ``execution_lifecycle.detach(...)`` for the observer token was
    delayed by ~minutes -- the grace-stop fired ~5 minutes late instead
    of after ``AI_DISCONNECT_GRACE_SECONDS`` (30s).

    The fix runs the forwarding as a background task (the ``chat``
    handler's pattern) so the message loop returns to ``receive_json``,
    detects the disconnect promptly, and the ``finally`` detaches the
    token immediately.  This test asserts the lifecycle invariant the
    fix preserves: right after a simulated detach (no delay, no inline
    await), the token is gone and a grace-stop is scheduled.
    """
    lc = fresh_lifecycle
    eid = "exec-reconnect"
    bus = _make_bus(eid)
    stop = asyncio.Event()
    lc.register(eid, stop, bus)

    tok = _token()

    # Simulate the subscribe handler's attach (reconnect).
    assert lc.attach(eid, tok) is True
    ctx = lc._contexts[eid]
    assert tok in ctx.observers
    assert ctx.grace_task is None

    # Simulate the disconnect ``finally`` running PROMPTLY (the bug
    # delayed this): detach the observer token immediately.
    lc.detach(eid, tok)

    # The token is gone and a grace-stop task was scheduled -- no
    # lingering observer that would make ExecutionLifecycle think a
    # transport is still present.
    assert tok not in ctx.observers
    assert ctx.grace_task is not None
    assert not ctx.observers

    # Before the grace window elapses, stop has not fired yet -- but the
    # task exists, so it WILL fire on schedule (30s, not minutes late).
    assert stop.is_set() is False

    # After the grace window: request_stop fired on time.
    await asyncio.sleep(small_grace + 0.1)
    assert stop.is_set() is True
    assert lc.is_stopping(eid) is True


@pytest.mark.asyncio
async def test_subscribe_forwarding_does_not_block_message_loop() -> None:
    """The subscribe handler must NOT ``await forward_bus_events`` inline.

    Models the corrected control flow: attaching an observer + starting a
    forwarding background task must return control to the message loop
    immediately so a subsequent ``receive_json`` (or, here, a simulated
    disconnect) is observed without waiting for the bus to drain.  With
    the old inline-await bug, this loop would block until the bus
    completed (minutes for a half-closed socket).
    """
    lc = ExecutionLifecycle()
    eid = "exec-noblock"
    bus = _make_bus(eid)
    stop = asyncio.Event()
    lc.register(eid, stop, bus)
    tok = _token()

    # A background "forwarding" task that never completes on its own
    # (mirrors forward_bus_events blocked on a half-closed socket).
    started = asyncio.Event()
    release = asyncio.Event()

    async def stuck_forwarding() -> None:
        started.set()
        await release.wait()

    tasks: set[asyncio.Task[None]] = set()
    try:
        # The fixed subscribe handler: attach, then run forwarding as a
        # background task, then return to the loop (no inline await).
        lc.attach(eid, tok)
        fwd_task = asyncio.create_task(stuck_forwarding())
        tasks.add(fwd_task)
        fwd_task.add_done_callback(tasks.discard)
        assert not fwd_task.done()

        # Control returned to the "message loop" promptly: we reach here
        # even though forwarding is still running.
        await asyncio.wait_for(started.wait(), timeout=1.0)
        assert not fwd_task.done()  # forwarding still blocked

        # Simulated disconnect: the ``finally`` cancels forwarding and
        # detaches the observer immediately -- not gated on the
        # forwarding task finishing.
        fwd_task.cancel()
        lc.detach(eid, tok)

        ctx = lc._contexts[eid]
        assert tok not in ctx.observers
        assert not ctx.observers  # observer detached despite blocked forwarding
    finally:
        release.set()
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
