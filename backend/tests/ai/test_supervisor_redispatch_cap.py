"""Tests for the code-enforced per-specialist re-dispatch cap (Phase 4).

The supervisor prompt states "each plan step may be delegated to its
specialist at most ONCE"; ``_MAX_DISPATCHES_PER_SPECIALIST`` enforces it in
the specialist dispatch node so a weak reasoning model cannot drive a
Swarm-style infinite re-dispatch loop
(supervisor -> specialist -> supervisor -> same specialist -> ...).

The cap is tracked at ``(specialist, step_index)`` granularity so a genuine
NEW step for the same specialist is unaffected.  When the cap is exceeded
the dispatch node routes back to the supervisor with a ``request_replan``
nudge instead of running the specialist again.

Test level: the real ``specialist_node`` closure (mirrors the
``test_plan_order_guidance.py`` instantiation pattern).
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import HumanMessage, SystemMessage

from app.ai.plan import PlanDocument, PlanStep
from app.ai.supervisor_orchestrator import (
    _MAX_DISPATCHES_PER_SPECIALIST,
    SupervisorOrchestrator,
)
from app.ai.tools.types import ToolContext

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_tool_context() -> ToolContext:
    mock_event_bus = MagicMock()
    mock_event_bus.publish = MagicMock()
    mock_event_bus.execution_id = "test-exec-id"
    ctx = ToolContext(
        session=MagicMock(),
        user_id="test-user",
        _event_bus=mock_event_bus,
    )
    ctx._stop_event = MagicMock()
    ctx._stop_event.is_set.return_value = False
    return ctx


def _make_failing_specialist_graph() -> Any:
    """A graph whose ainvoke raises if called -- proves the cap blocks the
    re-dispatch BEFORE the specialist runs."""
    graph = AsyncMock()

    async def _explode(*_a: Any, **_kw: Any) -> dict[str, Any]:
        pytest.fail("specialist_graph.ainvoke must NOT be called when the cap is hit")

    graph.ainvoke.side_effect = _explode
    return graph


def _plan_with_one_step() -> PlanDocument:
    return PlanDocument(
        original_request="calc metrics",
        steps=[
            PlanStep(
                step_index=0,
                specialist="evm_analyst",
                task_description="Calculate CPI/SPI",
                status="pending",
            ),
        ],
        requires_planning=True,
    )


def _state_with_dispatch_count(count: int) -> dict[str, Any]:
    plan = _plan_with_one_step()
    return {
        "messages": [HumanMessage(content="calc metrics")],
        "active_agent": "evm_analyst",
        "tool_call_count": 0,
        "max_tool_iterations": 25,
        "briefing_data": {
            "original_request": "calc metrics",
            "sections": [],
            "supervisor_analysis": "",
            "task_history": [],
        },
        "supervisor_iterations": 2,
        "completed_specialists": set(),
        "plan_data": plan.model_dump(),
        "completed_steps": set(),
        # evm_analyst has ALREADY been dispatched once for step 0 (the cap).
        "specialist_dispatch_counts": {"evm_analyst|0": count},
    }


# ===========================================================================
# Cap enforcement
# ===========================================================================


@pytest.mark.asyncio
async def test_redispatch_cap_blocks_repeat_dispatch_of_same_step() -> None:
    """A specialist already dispatched for a step at/above the cap is routed
    to the supervisor with a request_replan nudge; the specialist is NOT run."""
    assert _MAX_DISPATCHES_PER_SPECIALIST == 1  # contract: once per step

    ctx = _make_tool_context()
    fake_graph = _make_failing_specialist_graph()
    orchestrator = SupervisorOrchestrator(model=MagicMock(), context=ctx)
    node = orchestrator._create_specialist_wrapper(
        specialist_name="evm_analyst",
        specialist_graph=fake_graph,
    )

    state = _state_with_dispatch_count(count=_MAX_DISPATCHES_PER_SPECIALIST)
    result = await node(state)

    # Routes to supervisor, NOT END and NOT running the specialist.
    assert result.goto == "supervisor"
    msgs = result.update.get("messages")
    assert msgs and isinstance(msgs[0], SystemMessage)
    text = msgs[0].content
    assert "request_replan" in text
    assert "evm_analyst" in text

    # The specialist graph was NOT invoked.
    assert fake_graph.ainvoke.await_count == 0
    # Iteration counter advanced so the graph cannot spin forever.
    assert result.update.get("supervisor_iterations", 0) >= 2


@pytest.mark.asyncio
async def test_new_step_for_same_specialist_is_not_blocked() -> None:
    """The cap is per (specialist, step_index): a dispatch of the SAME
    specialist for a DIFFERENT step is allowed even if the specialist was
    already dispatched for another step."""
    plan = PlanDocument(
        original_request="multi",
        steps=[
            PlanStep(
                step_index=0,
                specialist="evm_analyst",
                task_description="step zero done",
                status="completed",
                result_summary="done",
            ),
            PlanStep(
                step_index=1,
                specialist="evm_analyst",
                task_description="step one new work",
                status="pending",
                dependencies=[0],
            ),
        ],
        requires_planning=True,
    )

    ctx = _make_tool_context()
    # A graph that SUCCEEDS so the dispatch proceeds past the cap check.
    success_graph = AsyncMock()

    async def _ok(*_a: Any, **_kw: Any) -> dict[str, Any]:
        return {
            "messages": [],
            "structured_response": MagicMock(
                summary="CPI=0.9",
                key_findings=["CPI=0.9"],
                open_questions=[],
                delegation_notes="",
            ),
            "tool_call_count": 2,
        }

    success_graph.ainvoke.side_effect = _ok
    orchestrator = SupervisorOrchestrator(model=MagicMock(), context=ctx)
    node = orchestrator._create_specialist_wrapper(
        specialist_name="evm_analyst",
        specialist_graph=success_graph,
    )

    state: dict[str, Any] = {
        "messages": [HumanMessage(content="multi")],
        "active_agent": "evm_analyst",
        "tool_call_count": 0,
        "max_tool_iterations": 25,
        "briefing_data": {
            "original_request": "multi",
            "sections": [],
            "supervisor_analysis": "",
            "task_history": [],
        },
        "supervisor_iterations": 3,
        "completed_specialists": {"evm_analyst"},
        "plan_data": plan.model_dump(),
        "completed_steps": {0},
        # Dispatched once for step 0; step 1 has NO count yet -> allowed.
        "specialist_dispatch_counts": {"evm_analyst|0": 1},
    }

    result = await node(state)

    # The specialist WAS invoked (cap did not block a new step).
    assert success_graph.ainvoke.await_count == 1
    # Step 1 completed; dispatch count for step 1 recorded.
    assert result.goto == "supervisor"
    counts = result.update.get("specialist_dispatch_counts", {})
    assert counts.get("evm_analyst|1") == 1


@pytest.mark.asyncio
async def test_first_dispatch_under_cap_is_allowed() -> None:
    """A specialist with a dispatch count below the cap runs normally."""
    ctx = _make_tool_context()
    success_graph = AsyncMock()

    async def _ok(*_a: Any, **_kw: Any) -> dict[str, Any]:
        return {
            "messages": [],
            "structured_response": MagicMock(
                summary="ok",
                key_findings=[],
                open_questions=[],
                delegation_notes="",
            ),
            "tool_call_count": 1,
        }

    success_graph.ainvoke.side_effect = _ok
    orchestrator = SupervisorOrchestrator(model=MagicMock(), context=ctx)
    node = orchestrator._create_specialist_wrapper(
        specialist_name="evm_analyst",
        specialist_graph=success_graph,
    )

    # Count is 0 (below the cap of 1) -> dispatch proceeds.
    state = _state_with_dispatch_count(count=0)
    result = await node(state)

    assert success_graph.ainvoke.await_count == 1
    assert result.goto == "supervisor"
    counts = result.update.get("specialist_dispatch_counts", {})
    assert counts.get("evm_analyst|0") == 1
