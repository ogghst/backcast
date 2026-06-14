"""Unit tests for the specialist invocation retry/timeout helper.

The helper ``_invoke_specialist_with_retry`` was extracted from the inline
retry loop in ``SupervisorOrchestrator._invoke_specialist`` so that the
timeout + exponential-backoff-with-jitter behaviour can be tested in
isolation.

These tests monkeypatch ``asyncio.sleep`` so the real backoff delays never
slow the suite, except where the hang-test needs a real (short) sleep that
exceeds the timeout.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

import pytest

from app.ai.supervisor_orchestrator import (
    _SPECIALIST_RETRY_BASE_S,
    _SPECIALIST_RETRY_CAP_S,
    _SPECIALIST_RETRY_JITTER_S,
    _invoke_specialist_with_retry,
)

# Type alias for the invoke factory used in tests.
InvokeFactory = Callable[[], Awaitable[dict[str, Any]]]


def _make_invoke(
    behavior: Callable[[int], Awaitable[dict[str, Any]]],
) -> InvokeFactory:
    """Build a zero-arg async factory that awaits ``behavior(attempt)``.

    ``behavior`` is an async callable returning a ``dict`` (success) or
    raising.  ``attempt`` is a 0-based counter incremented on each
    invocation.
    """

    counter = {"n": 0}

    async def _invoke() -> dict[str, Any]:
        n = counter["n"]
        counter["n"] += 1
        return await behavior(n)

    return _invoke


def _patch_sleep_recorder(
    monkeypatch: pytest.MonkeyPatch,
) -> list[float]:
    """Replace ``asyncio.sleep`` with a no-op that records its delay.

    The recorded list is returned so tests can assert on backoff delays
    without paying the real sleep cost.
    """

    sleeps: list[float] = []

    async def _recorder(delay: float) -> None:
        sleeps.append(delay)

    monkeypatch.setattr(asyncio, "sleep", _recorder)
    return sleeps


# =====================================================================
# 1. Success on first try
# =====================================================================


@pytest.mark.asyncio
async def test_success_first_try(monkeypatch: pytest.MonkeyPatch) -> None:
    """Returns the result, invokes once, never sleeps."""
    sleeps = _patch_sleep_recorder(monkeypatch)
    calls = {"n": 0}

    async def _ok(_n: int) -> dict[str, Any]:
        calls["n"] += 1
        return {"messages": ["ok"]}

    result = await _invoke_specialist_with_retry(
        _make_invoke(_ok),
        specialist_name="WBSSpecialist",
        max_retries=3,
        timeout=5.0,
    )

    assert result == {"messages": ["ok"]}
    assert calls["n"] == 1
    assert sleeps == []


# =====================================================================
# 2. Transient error once, then success
# =====================================================================


@pytest.mark.asyncio
async def test_transient_then_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """ConnectionResetError on attempt 0, success on attempt 1."""
    sleeps = _patch_sleep_recorder(monkeypatch)
    real_counter = {"n": 0}

    async def _flaky() -> dict[str, Any]:
        n = real_counter["n"]
        real_counter["n"] += 1
        if n == 0:
            raise ConnectionResetError("reset")
        return {"messages": ["recovered"]}

    result = await _invoke_specialist_with_retry(
        _flaky,
        specialist_name="CostSpecialist",
        max_retries=3,
        timeout=5.0,
    )

    assert result == {"messages": ["recovered"]}
    assert real_counter["n"] == 2  # invoked twice
    assert len(sleeps) == 1  # backoff slept once


# =====================================================================
# 3. Non-retryable error propagates immediately
# =====================================================================


@pytest.mark.asyncio
async def test_non_retryable_error_propagates(monkeypatch: pytest.MonkeyPatch) -> None:
    """ValueError is not transient -> raise immediately, no sleep, one call."""
    sleeps = _patch_sleep_recorder(monkeypatch)
    calls = {"n": 0}

    async def _bad(_n: int) -> dict[str, Any]:
        calls["n"] += 1
        raise ValueError("not transient")

    with pytest.raises(ValueError, match="not transient"):
        await _invoke_specialist_with_retry(
            _make_invoke(_bad),
            specialist_name="RiskSpecialist",
            max_retries=3,
            timeout=5.0,
        )

    assert calls["n"] == 1
    assert sleeps == []


# =====================================================================
# 4. Exhausted retries on persistent transient error
# =====================================================================


@pytest.mark.asyncio
async def test_exhausted_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    """max_retries=2, persistent ConnectionResetError -> raises after 3 calls."""
    sleeps = _patch_sleep_recorder(monkeypatch)
    calls = {"n": 0}

    async def _always_transient(_n: int) -> dict[str, Any]:
        calls["n"] += 1
        raise ConnectionResetError("always reset")

    with pytest.raises(ConnectionResetError):
        await _invoke_specialist_with_retry(
            _make_invoke(_always_transient),
            specialist_name="CostSpecialist",
            max_retries=2,
            timeout=5.0,
        )

    # invoked max_retries + 1 times
    assert calls["n"] == 3
    # slept max_retries times (between attempts), with strictly increasing delays
    assert len(sleeps) == 2
    assert sleeps[0] < sleeps[1]
    # each delay within CAP + jitter
    for delay in sleeps:
        assert delay <= _SPECIALIST_RETRY_CAP_S + _SPECIALIST_RETRY_JITTER_S


@pytest.mark.asyncio
async def test_exponential_backoff_formula(monkeypatch: pytest.MonkeyPatch) -> None:
    """With jitter pinned to 0, delays are exactly min(base*2**attempt, cap)."""
    monkeypatch.setattr(
        "app.ai.supervisor_orchestrator.random.uniform", lambda a, b: 0.0
    )
    sleeps = _patch_sleep_recorder(monkeypatch)

    async def _always_transient(_n: int) -> dict[str, Any]:
        raise ConnectionResetError("reset")

    with pytest.raises(ConnectionResetError):
        await _invoke_specialist_with_retry(
            _make_invoke(_always_transient),
            specialist_name="CostSpecialist",
            max_retries=4,  # attempts 0..4, sleeps after 0,1,2,3
            timeout=5.0,
        )

    expected = [
        min(_SPECIALIST_RETRY_BASE_S * 2**a, _SPECIALIST_RETRY_CAP_S) for a in range(4)
    ]
    assert sleeps == expected
    # sanity: 1, 2, 4, 8 (cap 20 not hit at base=1)
    assert expected == [1.0, 2.0, 4.0, 8.0]


# =====================================================================
# 5. Hanging invocation times out and is retried
# =====================================================================


@pytest.mark.asyncio
async def test_hanging_invocation_times_out() -> None:
    """Factory sleeps longer than timeout -> TimeoutError raised after retries.

    Uses a real (short) inner sleep (0.2s) with timeout 0.05s so the test
    stays fast WITHOUT patching asyncio.sleep globally -- the inner hang
    sleep and the helper's backoff sleep both run for real, but they are
    tiny.
    """
    calls = {"n": 0}

    async def _hang() -> dict[str, Any]:
        calls["n"] += 1
        await asyncio.sleep(0.2)  # longer than timeout=0.05
        return {"messages": ["should not reach"]}

    with pytest.raises((asyncio.TimeoutError, TimeoutError)):
        await _invoke_specialist_with_retry(
            _hang,
            specialist_name="WBSSpecialist",
            max_retries=1,
            timeout=0.05,
        )

    # invoked max_retries + 1 times (initial + 1 retry)
    assert calls["n"] == 2


# =====================================================================
# 6. Pausable deadline -- ask_user pending pauses the specialist timeout
# =====================================================================
#
# FU-1: the step-timeout must PAUSE while a specialist is blocked on
# ``ask_user`` awaiting human input.  A provider stall (no ask pending)
# is still bounded by ``timeout``; a legitimate user-wait (ask pending)
# is NOT, because ask_user carries its own response timeout.
#


def _register_pending_ask(ask_id: str, execution_id: str = "exec-test") -> None:
    """Register a non-done Future in ``ask_user._pending_asks`` for a test."""
    from app.ai.tools import ask_user

    loop = asyncio.get_running_loop()
    fut: asyncio.Future[str] = loop.create_future()
    ask_user._pending_asks[ask_id] = (fut, execution_id)


def _clear_pending_ask(ask_id: str) -> None:
    """Remove a test-registered ask so global state does not leak."""
    from app.ai.tools import ask_user

    ask_user._pending_asks.pop(ask_id, None)


@pytest.mark.asyncio
async def test_ask_pending_does_not_fire_timeout() -> None:
    """ask_user pending -> wall-clock exceeds timeout but helper RETURNS.

    The deadline accumulates ONLY when no ask is pending; with a pending
    ask the clock pauses, so a slow human does not get the specialist
    killed mid-clarification.
    """
    ask_id = "test-ask-1"
    _register_pending_ask(ask_id)
    try:
        # Fake invoke blocks ~0.8s (well past timeout=0.3) but an ask is
        # pending the entire time, so the deadline never accrues past 0.3s.
        async def _blocks_on_user() -> dict[str, Any]:
            await asyncio.sleep(0.8)
            return {"messages": ["answered after slow human"]}

        result = await _invoke_specialist_with_retry(
            _blocks_on_user,
            specialist_name="WBSSpecialist",
            max_retries=0,
            timeout=0.3,
        )

        assert result == {"messages": ["answered after slow human"]}
    finally:
        _clear_pending_ask(ask_id)


@pytest.mark.asyncio
async def test_no_ask_pending_real_stall_times_out() -> None:
    """No ask pending -> real provider stall still trips the timeout.

    Regression guard for the #2 fix: the pausable-deadline helper must NOT
    disable the stall protection when no ask_user is awaiting a human.
    """

    async def _real_stall() -> dict[str, Any]:
        await asyncio.sleep(0.8)  # no ask registered; exceeds timeout=0.3
        return {"messages": ["should not reach"]}

    with pytest.raises((asyncio.TimeoutError, TimeoutError)):
        await _invoke_specialist_with_retry(
            _real_stall,
            specialist_name="WBSSpecialist",
            max_retries=0,
            timeout=0.3,
        )


@pytest.mark.asyncio
async def test_ask_resolves_mid_wait_deadline_resumes() -> None:
    """ask resolves mid-wait -> deadline resumes; completes before re-accruing.

    Boundary behavior: the fake sleeps with an ask pending past the
    timeout, the ask then resolves (clearing ``_pending_asks``), and the
    fake sleeps a bit more WITHOUT an ask.  Because the cleared-state
    elapsed budget resets to near-zero when the ask was pending for most
    of the wall-clock window, the remaining non-ask sleep does not push
    elapsed past the timeout -> success.
    """
    ask_id = "test-ask-2"
    _register_pending_ask(ask_id)
    try:

        async def _ask_then_finish() -> dict[str, Any]:
            # Phase 1: blocked on human (ask pending). Wall-clock passes
            # the timeout here, but the deadline is paused.
            await asyncio.sleep(0.5)
            # Human answers -- ask resolves mid-wait.
            _clear_pending_ask(ask_id)
            # Phase 2: brief compute with NO ask pending. Keep it well
            # inside the remaining tick window so the resumed deadline
            # does not re-accrue past timeout before completion.
            await asyncio.sleep(0.05)
            return {"messages": ["done after human answered"]}

        result = await _invoke_specialist_with_retry(
            _ask_then_finish,
            specialist_name="WBSSpecialist",
            max_retries=0,
            timeout=0.3,
        )

        assert result == {"messages": ["done after human answered"]}
    finally:
        _clear_pending_ask(ask_id)
