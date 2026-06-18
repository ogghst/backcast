"""Tests for mid-specialist stop granularity (FIX #2).

``stop_event`` is only checked at the specialist-completion checkpoint.
A specialist stuck in a tool/LLM loop ran until the 120s specialist
timeout or the 600s graph deadline.  Raising inside a tool would be
swallowed by LangChain's tool node (converted to a ToolMessage), so
the robust hook is the pausable deadline, which already cancels the
asyncio task per tick.

This file verifies:

1. ``await_with_pausable_deadline`` evaluates ``should_stop`` each tick
   BEFORE timeout-accrual, so a stop interrupts even mid-ask and within
   a single tick window (~0.5s).
2. ``invoke_with_retry`` propagates ``ExecutionStoppedError`` WITHOUT
   retrying it (it is not a TimeoutError or transient stream error).
3. ``specialist_node`` RE-RAISES ``ExecutionStoppedError`` from the
   specialist invocation instead of compiling it into a briefing error.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.ai.exceptions import ExecutionStoppedError
from app.ai.execution.llm_retry import await_with_pausable_deadline, invoke_with_retry
from app.ai.plan import PlanDocument, PlanStep
from app.ai.supervisor_orchestrator import SupervisorOrchestrator
from app.ai.tools.types import ToolContext

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_tool_context() -> ToolContext:
    """Build a minimal ToolContext with a mock event bus (no DB)."""
    mock_session = MagicMock()
    mock_event_bus = MagicMock()
    mock_event_bus.publish = MagicMock()
    mock_event_bus.execution_id = "test-exec-id"

    ctx = ToolContext(
        session=mock_session,
        user_id="test-user",
        _event_bus=mock_event_bus,
    )
    ctx._stop_event = MagicMock()
    ctx._stop_event.is_set.return_value = False
    return ctx


# ===========================================================================
# 1. await_with_pausable_deadline: should_stop=True immediately
# ===========================================================================


@pytest.mark.asyncio
async def test_await_should_stop_immediately_raises() -> None:
    """A coroutine that sleeps 5s with timeout=10 and should_stop=lambda: True
    must raise ExecutionStoppedError within ~1 tick.  The underlying task is
    cancelled before it produces a result (the inner sleep never completes),
    proven by the absence of a return value and the fast elapsed time."""
    completed = {"value": False}

    async def _sleeps_long() -> dict[str, Any]:
        await asyncio.sleep(5.0)
        completed["value"] = True  # pragma: no cover - should never reach
        return {"ok": True}

    start = time.monotonic()
    with pytest.raises(ExecutionStoppedError):
        await await_with_pausable_deadline(
            _sleeps_long(),
            timeout=10.0,
            should_stop=lambda: True,
            tick=0.05,
        )
    elapsed = time.monotonic() - start

    # Fires within ~1 tick (well under the 5s sleep or the 10s timeout).
    assert elapsed < 1.0, f"stop took too long: {elapsed:.2f}s"
    # The inner coroutine never completed — task was cancelled, not leaked.
    assert completed["value"] is False


# ===========================================================================
# 2. await_with_pausable_deadline: should_stop flips to True after 0.2s
# ===========================================================================


@pytest.mark.asyncio
async def test_await_should_stop_flips_after_delay() -> None:
    """should_stop returns False initially and flips to True after ~0.2s.
    ExecutionStoppedError must fire shortly after the flip, NOT after the
    full 5s inner sleep."""
    state = {"stopped": False}

    def _should_stop() -> bool:
        return state["stopped"]

    async def _sleeps_long() -> dict[str, Any]:
        await asyncio.sleep(5.0)  # pragma: no cover - should never reach
        return {"ok": True}

    async def _flip_after() -> None:
        await asyncio.sleep(0.2)
        state["stopped"] = True

    start = time.monotonic()
    asyncio.ensure_future(_flip_after())
    with pytest.raises(ExecutionStoppedError):
        await await_with_pausable_deadline(
            _sleeps_long(),
            timeout=10.0,
            should_stop=_should_stop,
            tick=0.05,
        )
    elapsed = time.monotonic() - start

    # Fires shortly after the 0.2s flip, not after 5s.
    assert elapsed < 1.0, f"stop took too long: {elapsed:.2f}s"


# ===========================================================================
# 3. invoke_with_retry: should_stop=True propagates ExecutionStoppedError
#    WITHOUT retrying (ExecutionStoppedError is not retryable)
# ===========================================================================


@pytest.mark.asyncio
async def test_invoke_with_retry_stop_not_retried(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A should_stop that is True immediately -> ExecutionStoppedError
    propagates from invoke_with_retry on the FIRST attempt, even though
    invoke_with_retry catches Exception broadly.  No retries."""
    sleeps: list[float] = []

    async def _recorder(delay: float) -> None:
        sleeps.append(delay)

    monkeypatch.setattr(asyncio, "sleep", _recorder)

    async def _invocation() -> dict[str, Any]:
        await asyncio.sleep(5.0)  # pragma: no cover - should never reach
        return {"ok": True}

    with pytest.raises(ExecutionStoppedError):
        await invoke_with_retry(
            _invocation,
            label="TestSpecialist",
            max_retries=3,
            timeout=10.0,
            should_stop=lambda: True,
        )

    # No backoff sleep occurred (ExecutionStoppedError is non-retryable).
    assert sleeps == []


# ===========================================================================
# 4. specialist_node: ExecutionStoppedError from ainvoke RE-RAISES
#    (does NOT compile into briefing; no error_update returned)
# ===========================================================================


@pytest.mark.asyncio
async def test_specialist_node_reraises_execution_stopped() -> None:
    """A specialist_graph.ainvoke that raises ExecutionStoppedError -> the
    node RE-RAISES it.  No Command(error_update) is returned, no
    BRIEFING_UPDATE is published.  The exception propagates up the graph."""
    plan = PlanDocument(
        original_request="x",
        steps=[
            PlanStep(
                step_index=0,
                specialist="evm_analyst",
                task_description="Calculate CPI",
                status="pending",
            ),
        ],
        requires_planning=True,
    )
    ctx = _make_tool_context()

    failing_graph = AsyncMock()

    async def _raises_stop(*_a: Any, **_kw: Any) -> dict[str, Any]:
        raise ExecutionStoppedError("paused-deadline")

    failing_graph.ainvoke.side_effect = _raises_stop

    orchestrator = SupervisorOrchestrator(model=MagicMock(), context=ctx)
    node = orchestrator._create_specialist_wrapper(
        specialist_name="evm_analyst",
        specialist_graph=failing_graph,
    )

    from langchain_core.messages import HumanMessage

    state: dict[str, Any] = {
        "messages": [HumanMessage(content="x")],
        "active_agent": "evm_analyst",
        "tool_call_count": 0,
        "max_tool_iterations": 25,
        "briefing_data": {
            "original_request": "x",
            "sections": [],
            "supervisor_analysis": "",
            "task_history": [],
        },
        "supervisor_iterations": 1,
        "completed_specialists": set(),
        "plan_data": plan.model_dump(),
        "completed_steps": set(),
        "current_invocation_id": "inv-stop-001",
    }

    with pytest.raises(ExecutionStoppedError):
        await node(state)

    # No BRIEFING_UPDATE / AGENT_COMPLETE published on the stop path.
    bus = ctx._event_bus
    publishes = [c.args[0] for c in bus.publish.call_args_list]
    types = [getattr(p, "event_type", None) for p in publishes]
    from app.ai.event_types import AgentEventType

    assert AgentEventType.BRIEFING_UPDATE not in types
    assert AgentEventType.AGENT_COMPLETE not in types


# ---------------------------------------------------------------------------
# Type aliases used by the parameterised tests above (kept for clarity).
# ---------------------------------------------------------------------------

# Re-exported so callers can mirror the invoke factory pattern.
_InvokeFactory = Callable[[], Awaitable[dict[str, Any]]]
