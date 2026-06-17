"""Integration tests for the F1 premature-completion guard.

Tests the guard NODE (``_premature_completion_guard_node``) and the router's
``No handoff → END`` branch end-to-end at the component level, mirroring the
``test_supervisor_redispatch_cap.py`` instantiation pattern.

Scenarios:
1. Premature guard fires → supervisor re-attempts → handoff for the pending
   step → clean termination (the guard does not loop forever; supervisor
   iteration cap is the primary termination guarantee).
2. Premature guard hits the global reprompt cap → END (clean intentional
   message).
3. Re-dispatch cap interplay: a step already dispatched that the supervisor
   tries to confabulate-complete routes through the guard then the
   specialist node's re-dispatch cap nudges replan → terminates.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import END

from app.ai.plan import PlanDocument, PlanStep
from app.ai.supervisor_orchestrator import (
    AI_MAX_PREMATURE_COMPLETION_REPROMPTS,
    SupervisorOrchestrator,
    _decide_premature_completion,
)
from app.ai.tools.types import ToolContext

# ---------------------------------------------------------------------------
# Fixtures
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


def _text_only_done_answer() -> AIMessage:
    """A supervisor AIMessage that claims completion with NO tool call."""
    return AIMessage(content="All done. I have completed every step.")


def _plan_with_pending_step(
    *,
    completed_steps: tuple[int, ...] = (0,),
    pending_step_index: int = 1,
    specialist: str = "evm_analyst",
) -> PlanDocument:
    steps: list[PlanStep] = []
    for i in completed_steps:
        steps.append(
            PlanStep(
                step_index=i,
                specialist="general_purpose",
                task_description=f"task {i}",
                status="completed",
                result_summary="done",
            )
        )
    steps.append(
        PlanStep(
            step_index=pending_step_index,
            specialist=specialist,
            task_description="Calculate CPI/SPI for the project",
            status="pending",
        )
    )
    return PlanDocument(
        original_request="multi-step",
        steps=steps,
        requires_planning=True,
    )


def _state(
    plan: PlanDocument,
    *,
    last_msg: Any = None,
    supervisor_iterations: int = 1,
    premature_reprompts: int = 0,
    max_iterations: int = 5,
) -> dict[str, Any]:
    return {
        "messages": [HumanMessage(content="go"), last_msg or _text_only_done_answer()],
        "active_agent": "supervisor",
        "tool_call_count": 0,
        "max_tool_iterations": 25,
        "briefing_data": {
            "original_request": "multi-step",
            "sections": [],
            "supervisor_analysis": "",
            "task_history": [],
        },
        "supervisor_iterations": supervisor_iterations,
        "max_supervisor_iterations": max_iterations,
        "completed_specialists": set(),
        "plan_data": plan.model_dump(),
        "completed_steps": set(plan.completed_step_indices()),
        "current_step_index": 0,
        "replan_count": 0,
        "max_replan_count": 2,
        "replan_context": "",
        "specialist_dispatch_counts": {},
        "specialist_failure_counts": {},
        "premature_reprompts": premature_reprompts,
    }


# ===========================================================================
# Guard node: applies Command with message + supervisor_iterations +1
# ===========================================================================


@pytest.mark.asyncio
async def test_guard_node_injects_correction_and_returns_to_supervisor() -> None:
    """The guard node recomputes the decision and applies a Command that
    injects the contrastive-refutation SystemMessage, bumps
    supervisor_iterations (+1, the primary termination guarantee) and
    premature_reprompts (+1), and returns to 'supervisor'."""
    ctx = _make_tool_context()
    orchestrator = SupervisorOrchestrator(model=MagicMock(), context=ctx)
    plan = _plan_with_pending_step()

    state = _state(plan, supervisor_iterations=1, premature_reprompts=0)
    result = orchestrator._premature_completion_guard_node(state)

    assert result.goto == "supervisor"
    msgs = result.update.get("messages")
    assert msgs and isinstance(msgs[0], SystemMessage)
    assert "FALSE" in msgs[0].content
    assert "handoff_to_evm_analyst" in msgs[0].content
    # PRIMARY termination guarantee: supervisor_iterations MUST increment.
    assert result.update.get("supervisor_iterations") == 1
    # Secondary bound: premature_reprompts increments.
    assert result.update.get("premature_reprompts") == 1


@pytest.mark.asyncio
async def test_guard_node_routes_to_end_at_cap() -> None:
    """When the global reprompt cap is reached the guard node terminates END
    with a clean intentional message (no supervisor loop)."""
    ctx = _make_tool_context()
    orchestrator = SupervisorOrchestrator(model=MagicMock(), context=ctx)
    plan = _plan_with_pending_step()

    state = _state(
        plan,
        supervisor_iterations=4,
        premature_reprompts=AI_MAX_PREMATURE_COMPLETION_REPROMPTS,
    )
    result = orchestrator._premature_completion_guard_node(state)

    assert result.goto == END
    msgs = result.update.get("messages")
    assert msgs and isinstance(msgs[0], SystemMessage)
    assert "NOT executed" in msgs[0].content


# ===========================================================================
# Router consults the helper before END (the No-handoff branch)
# ===========================================================================


@pytest.mark.asyncio
async def test_router_routes_to_guard_on_premature_completion() -> None:
    """The router's 'No handoff → END' branch consults the helper and routes
    to the guard node when a dispatchable step is still pending."""
    ctx = _make_tool_context()
    orchestrator = SupervisorOrchestrator(model=MagicMock(), context=ctx)
    plan = _plan_with_pending_step()

    router = orchestrator._make_supervisor_router(["evm_analyst"])
    state = _state(plan, supervisor_iterations=1, premature_reprompts=0)
    assert router(state) == "premature_completion_guard"


@pytest.mark.asyncio
async def test_router_falls_through_to_end_when_no_dispatchable_step() -> None:
    """When the plan is fully complete (no dispatchable step), the router
    returns END and does NOT invoke the guard."""
    ctx = _make_tool_context()
    orchestrator = SupervisorOrchestrator(model=MagicMock(), context=ctx)
    plan = PlanDocument(
        original_request="x",
        steps=[
            PlanStep(
                step_index=0,
                specialist="a",
                task_description="t",
                status="completed",
                result_summary="done",
            )
        ],
        requires_planning=True,
    )
    router = orchestrator._make_supervisor_router(["a"])
    state = _state(plan, supervisor_iterations=1, premature_reprompts=0)
    assert router(state) == END


@pytest.mark.asyncio
async def test_router_does_not_fire_guard_after_correct_handoff() -> None:
    """Regression: a correct handoff returns
    ``Command(goto=agent, update={"messages": [ai_message, tool_message]})`` so
    the supervisor's ``messages[-1]`` is a ``ToolMessage`` (mid-flow, NOT a
    final answer). The router must NOT route to ``premature_completion_guard``
    after a correct handoff — previously the predicate treated any non-AIMessage
    (incl. ToolMessage) as a "text-only final answer" and false-fired on every
    delegation, derailing the run.
    """
    from langchain_core.messages import ToolMessage

    ctx = _make_tool_context()
    orchestrator = SupervisorOrchestrator(model=MagicMock(), context=ctx)
    plan = _plan_with_pending_step()

    # Post-handoff shape: the handoff tool returns
    # Command(goto=agent, update={"messages": [ai_message, tool_message]}), so
    # the supervisor's messages[-1] becomes the ToolMessage result below.
    tool_msg = ToolMessage(
        content="transferring to evm_analyst",
        tool_call_id="call_1",
        name="handoff_to_evm_analyst",
    )
    state = _state(
        plan,
        last_msg=tool_msg,
        supervisor_iterations=1,
        premature_reprompts=0,
    )
    # The last message is the ToolMessage (mid-flow), NOT an AIMessage.
    assert state["messages"][-1] is tool_msg

    router = orchestrator._make_supervisor_router(["evm_analyst"])
    result = router(state)
    assert result != "premature_completion_guard"
    assert result == END


# ===========================================================================
# Termination: guard → supervisor → handoff → terminate cleanly
# ===========================================================================


def test_termination_simulation_guard_then_handoff_then_end() -> None:
    """Simulate the cycle the guard is meant to enable:
    1. Supervisor confabulates (text-only done) → guard fires (reprompts 0→1).
    2. Supervisor emits handoff for the pending step → routed to specialist
       (not the guard — last_msg has tool_calls).
    3. After the specialist completes, plan is fully complete → END (no guard).
    Verifies the helper's decision at each step.
    """
    plan = _plan_with_pending_step()

    # Step 1: confabulation. Helper fires.
    d1 = _decide_premature_completion(
        plan=plan,
        last_msg_is_text_only=True,
        supervisor_iterations=1,
        max_iterations=5,
        premature_reprompts=0,
        max_reprompts=AI_MAX_PREMATURE_COMPLETION_REPROMPTS,
    )
    assert d1.goto == "premature_completion_guard"

    # Step 2: after the correction the supervisor emits a handoff tool call.
    # Helper must NOT fire (last message has tool_calls).
    d2 = _decide_premature_completion(
        plan=plan,
        last_msg_is_text_only=False,
        supervisor_iterations=2,
        max_iterations=5,
        premature_reprompts=1,
        max_reprompts=AI_MAX_PREMATURE_COMPLETION_REPROMPTS,
    )
    assert d2.goto == "END"  # no guard; router handles the handoff normally

    # Step 3: specialist completes the pending step → plan fully done.
    completed_plan = _plan_with_pending_step()
    completed_plan.mark_step_completed(1, "CPI=0.9, SPI=1.0")
    d3 = _decide_premature_completion(
        plan=completed_plan,
        last_msg_is_text_only=True,
        supervisor_iterations=3,
        max_iterations=5,
        premature_reprompts=1,
        max_reprompts=AI_MAX_PREMATURE_COMPLETION_REPROMPTS,
    )
    # No dispatchable step remains → no guard, clean END.
    assert d3.goto == "END"


def test_termination_simulation_repeated_confabulation_hits_cap() -> None:
    """The supervisor confabulates repeatedly. The global reprompt cap (2)
    terminates the cycle cleanly with END, NOT an unbounded guard loop."""
    plan = _plan_with_pending_step()
    # 1st confabulation:
    d1 = _decide_premature_completion(
        plan=plan,
        last_msg_is_text_only=True,
        supervisor_iterations=1,
        max_iterations=8,
        premature_reprompts=0,
        max_reprompts=AI_MAX_PREMATURE_COMPLETION_REPROMPTS,
    )
    assert d1.goto == "premature_completion_guard"
    # 2nd confabulation (after the 1st correction, model still confabulates):
    d2 = _decide_premature_completion(
        plan=plan,
        last_msg_is_text_only=True,
        supervisor_iterations=2,
        max_iterations=8,
        premature_reprompts=1,
        max_reprompts=AI_MAX_PREMATURE_COMPLETION_REPROMPTS,
    )
    assert d2.goto == "premature_completion_guard"
    # 3rd confabulation hits the GLOBAL cap → END (clean termination).
    d3 = _decide_premature_completion(
        plan=plan,
        last_msg_is_text_only=True,
        supervisor_iterations=3,
        max_iterations=8,
        premature_reprompts=2,
        max_reprompts=AI_MAX_PREMATURE_COMPLETION_REPROMPTS,
    )
    assert d3.goto == "END"
