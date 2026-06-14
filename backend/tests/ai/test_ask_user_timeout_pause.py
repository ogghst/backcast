"""Tests for the per-execution pausable deadline + awaiting-user registry.

Covers the timeout-pause fix for the known issue where the specialist step
timeout (``AI_SPECIALIST_STEP_TIMEOUT``, default 120s) wraps the WHOLE
specialist invoke via ``asyncio.wait_for`` -- shorter than ask_user's wait
window, so it killed specialists legitimately blocked on a human answer.

Two mechanisms are exercised:

1. ``mark_awaiting_user`` / ``clear_awaiting_user`` / ``is_awaiting_user``
   in ``app.ai.tools.ask_user`` -- the per-execution registry the
   specialist watchdog consults.
2. ``_invoke_specialist_with_retry`` passing ``execution_id`` through to
   ``_await_with_pausable_deadline`` so the deadline PAUSES while the
   specialist is awaiting a human (active work accrues only when NOT
   awaiting), but a real provider stall still trips the timeout.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from app.ai.supervisor_orchestrator import _invoke_specialist_with_retry
from app.ai.tools.ask_user import (
    _awaiting_user,
    clear_awaiting_user,
    is_awaiting_user,
    mark_awaiting_user,
)


def _reset_registry() -> None:
    """Clear the module-global awaiting-user set so tests do not leak state."""
    _awaiting_user.clear()


# =====================================================================
# Registry unit tests
# =====================================================================


def test_registry_mark_clear_is() -> None:
    """mark adds, is detects, clear removes; clear is idempotent."""
    _reset_registry()
    try:
        assert is_awaiting_user("exec-A") is False
        mark_awaiting_user("exec-A")
        assert is_awaiting_user("exec-A") is True
        # Different execution unaffected.
        assert is_awaiting_user("exec-B") is False
        clear_awaiting_user("exec-A")
        assert is_awaiting_user("exec-A") is False
        # clear on a non-marked execution is a no-op (no KeyError).
        clear_awaiting_user("never-marked")
    finally:
        _reset_registry()


def test_registry_clear_then_is_false() -> None:
    """After clear, is_awaiting_user returns False even mid-execution."""
    _reset_registry()
    try:
        mark_awaiting_user("exec-X")
        assert is_awaiting_user("exec-X") is True
        clear_awaiting_user("exec-X")
        assert is_awaiting_user("exec-X") is False
    finally:
        _reset_registry()


# =====================================================================
# _invoke_specialist_with_retry pausable-deadline fault injection
# =====================================================================


@pytest.mark.asyncio
async def test_awaiting_user_pauses_specialist_timeout() -> None:
    """invoke() marks awaiting-user, sleeps past timeout, clears, returns.

    The specialist step clock accrues ONLY active work; while awaiting a
    human it pauses. So a slow human does NOT get the specialist killed --
    the call completes successfully even though wall-clock exceeds the
    timeout.
    """
    _reset_registry()
    eid = "exec-pause-1"
    # Tiny timeout; invoke will block wall-clock well past it.
    timeout = 2.0

    async def _blocks_on_human() -> dict[str, Any]:
        mark_awaiting_user(eid)
        try:
            # Wall-clock sleep exceeds timeout (timeout + 3s per spec).
            await asyncio.sleep(timeout + 3.0)
            return {"messages": ["answered after slow human"]}
        finally:
            clear_awaiting_user(eid)

    try:
        result = await _invoke_specialist_with_retry(
            _blocks_on_human,
            specialist_name="WBSSpecialist",
            max_retries=0,
            timeout=timeout,
            execution_id=eid,
        )
        assert result == {"messages": ["answered after slow human"]}
    finally:
        _reset_registry()


@pytest.mark.asyncio
async def test_real_stall_without_awaiting_user_times_out() -> None:
    """invoke() does NOT mark awaiting and sleeps past timeout -> TimeoutError.

    Regression guard: the pausable deadline must still bound a real provider
    stall (no human in the loop).
    """
    _reset_registry()
    eid = "exec-stall-1"
    timeout = 2.0

    async def _real_stall() -> dict[str, Any]:
        # No mark_awaiting_user -- a genuine stall.
        await asyncio.sleep(timeout + 3.0)
        return {"messages": ["should not reach"]}

    try:
        with pytest.raises((asyncio.TimeoutError, TimeoutError)):
            await _invoke_specialist_with_retry(
                _real_stall,
                specialist_name="CostSpecialist",
                max_retries=0,
                timeout=timeout,
                execution_id=eid,
            )
    finally:
        _reset_registry()


@pytest.mark.asyncio
async def test_other_execution_awaiting_does_not_pause_this_one() -> None:
    """A different execution awaiting a human does NOT pause THIS specialist.

    Per-execution scoping matters: if exec-B is awaiting a human, exec-A's
    timeout must still fire on a real stall. This guards against regressing
    back to the coarse global predicate as the sole source of truth.
    """
    _reset_registry()
    other_eid = "exec-other"
    this_eid = "exec-this"
    timeout = 2.0

    mark_awaiting_user(other_eid)  # a DIFFERENT execution is awaiting
    try:

        async def _stall() -> dict[str, Any]:
            await asyncio.sleep(timeout + 3.0)
            return {"messages": ["should not reach"]}

        with pytest.raises((asyncio.TimeoutError, TimeoutError)):
            await _invoke_specialist_with_retry(
                _stall,
                specialist_name="RiskSpecialist",
                max_retries=0,
                timeout=timeout,
                execution_id=this_eid,
            )
    finally:
        _reset_registry()
