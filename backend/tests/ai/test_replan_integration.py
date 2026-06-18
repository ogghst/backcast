"""Integration tests: replan flow through planner, router, and specialist_node.

Three tests that together cover the full replan cycle without mocking the
entire LangGraph execution engine:

1. ``test_planner_replan_path`` -- planner_node with replan_context produces a
   revised plan preserving completed steps.
2. ``test_router_planner_integration`` -- router state transitions during a
   replan cycle (delegation -> replan request -> back to planner -> delegation).
3. ``test_specialist_node_with_revised_plan`` -- specialist_node resolves the
   correct pending step when the plan has non-contiguous completed indices.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import END

from app.ai.handoff_tools import create_replan_tool
from app.ai.plan import PlanDocument, PlannerOutput, PlannerStepOutput, PlanStep
from app.ai.planner import planner_node
from app.ai.supervisor_orchestrator import SupervisorOrchestrator
from app.ai.tools.types import ToolContext

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SPECIALIST_CATALOG: list[dict[str, str]] = [
    {"name": "evm_analyst", "description": "EVM metric analysis"},
    {"name": "visualization_specialist", "description": "Charts and dashboards"},
]


def _make_initial_plan() -> PlanDocument:
    """3-step plan where step 1 is redundant after step 0 completes."""
    return PlanDocument(
        original_request="Analyze EVM and build a dashboard",
        steps=[
            PlanStep(
                step_index=0,
                specialist="evm_analyst",
                task_description="Calculate CPI and SPI for the project",
                dependencies=[],
                expected_output="CPI and SPI values with trends",
            ),
            PlanStep(
                step_index=1,
                specialist="evm_analyst",
                task_description="Calculate EVM composite metrics",
                dependencies=[0],
                expected_output="Composite EVM indices",
            ),
            PlanStep(
                step_index=2,
                specialist="visualization_specialist",
                task_description="Build EVM performance dashboard",
                dependencies=[0, 1],
                expected_output="Interactive dashboard",
            ),
        ],
        estimated_complexity="moderate",
        requires_planning=True,
    )


def _make_completed_plan_after_step0() -> PlanDocument:
    """Plan where step 0 is completed (findings make step 1 redundant)."""
    plan = _make_initial_plan()
    plan.steps[0].status = "completed"
    plan.steps[
        0
    ].result_summary = "CPI=0.94, SPI=1.02. Composite indices derivable from these."
    return plan


def _make_llm_response(content: str) -> MagicMock:
    """Create a mock LLM response with string content."""
    msg = MagicMock()
    msg.content = content
    return msg


# ---------------------------------------------------------------------------
# Test 1: planner_node replan path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_planner_replan_path() -> None:
    """planner_node with replan_context revises the plan, preserving completed steps.

    Scenario:
    - Step 0 (evm_analyst) is completed and its findings make step 1 redundant.
    - The replan LLM returns a 1-step revised plan (visualization_specialist only).
    - planner_node should merge: completed step 0 + revised step at index 1.
    """
    existing_plan = _make_completed_plan_after_step0()

    # Mock the LLM to return a revised plan that drops the redundant step 1
    revised_output = PlannerOutput(
        original_request="Analyze EVM and build a dashboard",
        requires_planning=True,
        estimated_complexity="moderate",
        steps=[
            PlannerStepOutput(
                step_index=0,
                specialist="visualization_specialist",
                task_description="Build EVM performance dashboard from CPI/SPI data",
                dependencies=[],
                expected_output="Interactive EVM dashboard",
            ),
        ],
    )

    mock_llm = AsyncMock()
    mock_llm.ainvoke.return_value = _make_llm_response(revised_output.model_dump_json())

    state: dict[str, Any] = {
        "messages": [HumanMessage(content="Analyze EVM and build a dashboard")],
        "plan_data": existing_plan.model_dump(),
        "replan_context": "Step 0 found CPI=0.94, SPI=1.02 with composite indices derivable. Step 1 is redundant.",
        "briefing_data": None,
    }

    result = await planner_node(state, mock_llm, specialist_catalog=_SPECIALIST_CATALOG)

    # Verify state update structure
    assert "plan_data" in result
    assert result["replan_context"] == ""  # Must be cleared after processing

    plan = PlanDocument.from_state(result["plan_data"])

    # Completed step 0 preserved exactly
    assert len(plan.steps) == 2
    assert plan.steps[0].step_index == 0
    assert plan.steps[0].status == "completed"
    assert plan.steps[0].specialist == "evm_analyst"
    assert "CPI=0.94" in plan.steps[0].result_summary

    # Revised step gets index 1 (max_completed_idx=0, so 0+1=1)
    assert plan.steps[1].step_index == 1
    assert plan.steps[1].status == "pending"
    assert plan.steps[1].specialist == "visualization_specialist"
    assert "CPI/SPI data" in plan.steps[1].task_description

    # LLM was called exactly once
    mock_llm.ainvoke.assert_awaited_once()


# ---------------------------------------------------------------------------
# Test 2: router + planner integration (state transitions during replan)
# ---------------------------------------------------------------------------


def test_router_planner_integration() -> None:
    """Simulate router state transitions through a full replan cycle.

    Flow:
    1. Supervisor delegates step 0 (evm_analyst) -> router returns "evm_analyst"
    2. Supervisor calls request_replan -> router returns "planner"
    3. After replan, supervisor delegates revised step -> router returns "visualization_specialist"
    4. Supervisor wraps up (no tool call) -> router returns END
    """
    specialist_names = ["evm_analyst", "visualization_specialist"]
    router = SupervisorOrchestrator._make_supervisor_router(specialist_names)

    base_state: dict[str, Any] = {
        "replan_count": 0,
        "max_replan_count": 2,
        "supervisor_iterations": 0,
        "max_supervisor_iterations": 10,
        "completed_specialists": set(),
        "completed_steps": set(),
        "plan_data": _make_initial_plan().model_dump(),
    }

    # Transition 1: Supervisor delegates step 0 to evm_analyst
    state_delegation_1 = {
        **base_state,
        "messages": [
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "handoff_to_evm_analyst",
                        "args": {
                            "task_description": "Calculate CPI and SPI",
                            "step_index": 0,
                        },
                        "id": "tc_step0",
                        "type": "tool_call",
                    }
                ],
            )
        ],
    }
    assert router(state_delegation_1) == "evm_analyst"

    # Transition 2: After step 0 completes, supervisor requests replan
    state_replan = {
        **base_state,
        "replan_count": 0,  # Will be incremented by the tool, but router reads pre-tool state
        "completed_specialists": {"evm_analyst"},
        "completed_steps": {0},
        "messages": [
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "request_replan",
                        "args": {"reason": "Step 1 redundant after step 0 findings"},
                        "id": "tc_replan",
                        "type": "tool_call",
                    }
                ],
            )
        ],
    }
    assert router(state_replan) == "planner"

    # Transition 3: After replan, supervisor delegates revised step to visualization_specialist
    revised_plan = PlanDocument(
        original_request="Analyze EVM and build a dashboard",
        steps=[
            PlanStep(
                step_index=0,
                specialist="evm_analyst",
                task_description="Calculate CPI and SPI",
                status="completed",
                result_summary="CPI=0.94, SPI=1.02",
            ),
            PlanStep(
                step_index=1,
                specialist="visualization_specialist",
                task_description="Build dashboard from EVM data",
                status="pending",
            ),
        ],
        requires_planning=True,
    )
    state_delegation_2 = {
        **base_state,
        "replan_count": 1,
        "completed_specialists": {"evm_analyst"},
        "completed_steps": {0},
        "plan_data": revised_plan.model_dump(),
        "messages": [
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "handoff_to_visualization_specialist",
                        "args": {
                            "task_description": "Build dashboard from EVM data",
                            "step_index": 1,
                        },
                        "id": "tc_step1",
                        "type": "tool_call",
                    }
                ],
            )
        ],
    }
    # Plan-driven mode allows re-dispatch, so visualization_specialist is valid
    assert router(state_delegation_2) == "visualization_specialist"

    # Transition 4: Supervisor wraps up with no tool calls -> END.
    # In production, completing step 1 re-serializes plan_data with step 1's
    # status="completed" (via mark_step_completed); reflect that here so the
    # plan is genuinely complete and the F1 premature-completion guard does
    # not fire on a stale-pending step.
    completed_revised_plan = PlanDocument(
        original_request="Analyze EVM and build a dashboard",
        steps=[
            PlanStep(
                step_index=0,
                specialist="evm_analyst",
                task_description="Calculate CPI and SPI",
                status="completed",
                result_summary="CPI=0.94, SPI=1.02",
            ),
            PlanStep(
                step_index=1,
                specialist="visualization_specialist",
                task_description="Build dashboard from EVM data",
                status="completed",
                result_summary="Dashboard built.",
            ),
        ],
        requires_planning=True,
    )
    state_wrap_up = {
        **base_state,
        "replan_count": 1,
        "completed_specialists": {"evm_analyst", "visualization_specialist"},
        "completed_steps": {0, 1},
        "plan_data": completed_revised_plan.model_dump(),
        "messages": [AIMessage(content="All steps completed. Here is the briefing.")],
    }
    assert router(state_wrap_up) == END

    # Transition 5: Verify replan is blocked at max count. As of the
    # bounded-termination fix, the max-replan force-END path routes to the
    # ``bounded_terminate`` node (which emits a grounded notice and then END)
    # instead of bare END, so the user is always told when a run is bounded.
    state_max_replan = {
        **base_state,
        "replan_count": 2,  # At max
        "messages": [
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "request_replan",
                        "args": {"reason": "One more replan"},
                        "id": "tc_blocked",
                        "type": "tool_call",
                    }
                ],
            )
        ],
    }
    assert router(state_max_replan) == "bounded_terminate"


# ---------------------------------------------------------------------------
# Test 3: specialist_node resolves correct step with non-contiguous indices
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_specialist_node_with_revised_plan() -> None:
    """specialist_node picks the correct pending step from a revised plan.

    After a replan, the plan has completed step 0 (evm_analyst) and a new
    pending step 1 (visualization_specialist). When the visualization_specialist
    node runs, it must resolve step 1, NOT re-execute step 0.
    """
    revised_plan = PlanDocument(
        original_request="Analyze EVM and build a dashboard",
        steps=[
            PlanStep(
                step_index=0,
                specialist="evm_analyst",
                task_description="Calculate CPI and SPI for the project",
                status="completed",
                result_summary="CPI=0.94, SPI=1.02 with trends",
            ),
            PlanStep(
                step_index=1,
                specialist="visualization_specialist",
                task_description="Build EVM dashboard from step 0 data",
                status="pending",
                dependencies=[0],
            ),
        ],
        estimated_complexity="moderate",
        requires_planning=True,
    )

    # Build a minimal ToolContext with a mock event bus
    mock_session = MagicMock()
    mock_event_bus = MagicMock()
    mock_event_bus.publish = MagicMock()
    mock_event_bus.execution_id = "test-exec-id"

    tool_context = ToolContext(
        session=mock_session,
        user_id="test-user",
        _event_bus=mock_event_bus,
    )
    tool_context._stop_event = MagicMock()
    tool_context._stop_event.is_set.return_value = False

    # Create a mock specialist graph that returns deterministic output
    mock_specialist_graph = AsyncMock()
    mock_specialist_graph.ainvoke.return_value = {
        "messages": [AIMessage(content="Dashboard built with CPI/SPI charts")],
        "tool_call_count": 0,
    }

    # Build the orchestrator and extract the specialist wrapper
    orchestrator = SupervisorOrchestrator(
        model=MagicMock(),
        context=tool_context,
    )

    wrapper_fn = orchestrator._create_specialist_wrapper(
        specialist_name="visualization_specialist",
        specialist_graph=mock_specialist_graph,
    )

    # Simulate graph state after replan: step 0 completed, step 1 pending
    state: dict[str, Any] = {
        "messages": [HumanMessage(content="Analyze EVM and build a dashboard")],
        "active_agent": "visualization_specialist",
        "tool_call_count": 0,
        "max_tool_iterations": 25,
        "briefing_data": {
            "original_request": "Analyze EVM and build a dashboard",
            "sections": [
                {
                    "specialist_name": "evm_analyst",
                    "findings": "CPI=0.94, SPI=1.02",
                    "key_findings": ["CPI below 1.0 indicates cost overrun"],
                    "open_questions": [],
                    "delegation_notes": "",
                    "task_description": "Calculate CPI and SPI",
                }
            ],
            "supervisor_analysis": "",
            "task_history": [],
        },
        "supervisor_iterations": 1,
        "max_supervisor_iterations": 10,
        "completed_specialists": {"evm_analyst"},
        "plan_data": revised_plan.model_dump(),
        "completed_steps": {0},
        "current_step_index": 0,
        "current_invocation_id": "inv-001",
        "replan_count": 1,
        "max_replan_count": 2,
        "replan_context": "",
    }

    result = await wrapper_fn(state)

    # The result is a Command that routes back to supervisor
    assert hasattr(result, "update")
    assert hasattr(result, "goto")
    assert result.goto == "supervisor"

    update = result.update
    assert update["active_agent"] == "supervisor"
    assert "visualization_specialist" in update["completed_specialists"]
    assert 1 in update["completed_steps"]

    # Verify plan step was marked completed
    updated_plan = PlanDocument.from_state(update["plan_data"])
    viz_step = updated_plan.get_step(1)
    assert viz_step is not None
    assert viz_step.status == "completed"
    assert "Dashboard" in viz_step.result_summary

    # Step 0 must remain completed, untouched
    evm_step = updated_plan.get_step(0)
    assert evm_step is not None
    assert evm_step.status == "completed"
    assert "CPI=0.94" in evm_step.result_summary

    # Specialist graph was invoked with assignment containing the correct step context
    call_args = mock_specialist_graph.ainvoke.call_args
    invoked_state = call_args[0][0]  # First positional arg
    invoked_messages = invoked_state["messages"]
    assert len(invoked_messages) == 1
    assignment_text = invoked_messages[0].content
    # Must reference step 2 (1-indexed in display) and visualization task
    assert "Plan Step 2/2" in assignment_text
    assert "EVM dashboard" in assignment_text


# ---------------------------------------------------------------------------
# Test 4: full planner_node error fallback preserves existing plan
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_planner_replan_error_preserves_existing_plan() -> None:
    """If the replan LLM call fails, planner_node keeps the existing plan."""
    existing_plan = _make_completed_plan_after_step0()

    mock_llm = AsyncMock()
    mock_llm.ainvoke.side_effect = RuntimeError("LLM service unavailable")

    state: dict[str, Any] = {
        "messages": [HumanMessage(content="Analyze EVM and build a dashboard")],
        "plan_data": existing_plan.model_dump(),
        "replan_context": "Step 1 seems redundant",
        "briefing_data": None,
    }

    result = await planner_node(state, mock_llm, specialist_catalog=_SPECIALIST_CATALOG)

    plan = PlanDocument.from_state(result["plan_data"])

    # Original 3 steps preserved unchanged
    assert len(plan.steps) == 3
    assert plan.steps[0].status == "completed"
    assert plan.steps[1].status == "pending"
    assert plan.steps[2].status == "pending"

    # replan_context is still cleared (error path resets it)
    assert result["replan_context"] == ""


# ---------------------------------------------------------------------------
# Test 5: replan tool produces correct Command with incrementing count
# ---------------------------------------------------------------------------


def test_replan_tool_incremental_count() -> None:
    """request_replan tool increments replan_count from the current state value."""
    tool = create_replan_tool()

    # First replan: count goes 0 -> 1
    state_0: dict[str, Any] = {"messages": [], "replan_count": 0}
    result_0 = tool.func(reason="First replan", state=state_0, tool_call_id="tc1")
    assert result_0.update["replan_count"] == 1

    # Second replan: count goes 1 -> 2
    state_1: dict[str, Any] = {"messages": [], "replan_count": 1}
    result_1 = tool.func(reason="Second replan", state=state_1, tool_call_id="tc2")
    assert result_1.update["replan_count"] == 2


# ---------------------------------------------------------------------------
# Test 6: specialist_node skips already-completed specialist without plan step
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_specialist_node_skips_without_pending_plan_step() -> None:
    """specialist_node routes to supervisor with guidance when specialist is
    completed and no pending step remains.

    As of the failed-step-containment fix, a completed specialist with no
    pending plan step no longer silently routes to END; instead the
    plan-mode containment guard returns a Command(goto="supervisor")
    carrying a guidance SystemMessage ("respond, do not delegate").  The
    specialist graph is still NOT invoked.
    """
    plan = PlanDocument(
        original_request="Analyze EVM",
        steps=[
            PlanStep(
                step_index=0,
                specialist="evm_analyst",
                task_description="Calculate CPI",
                status="completed",
                result_summary="CPI=0.94",
            ),
        ],
        requires_planning=True,
    )

    mock_session = MagicMock()
    mock_event_bus = MagicMock()
    mock_event_bus.publish = MagicMock()
    mock_event_bus.execution_id = "test-exec-id"

    tool_context = ToolContext(
        session=mock_session,
        user_id="test-user",
        _event_bus=mock_event_bus,
    )
    tool_context._stop_event = MagicMock()
    tool_context._stop_event.is_set.return_value = False

    mock_specialist_graph = AsyncMock()

    orchestrator = SupervisorOrchestrator(
        model=MagicMock(),
        context=tool_context,
    )

    wrapper_fn = orchestrator._create_specialist_wrapper(
        specialist_name="evm_analyst",
        specialist_graph=mock_specialist_graph,
    )

    state: dict[str, Any] = {
        "messages": [HumanMessage(content="Analyze EVM")],
        "active_agent": "evm_analyst",
        "tool_call_count": 0,
        "max_tool_iterations": 25,
        "briefing_data": {},
        "supervisor_iterations": 1,
        "max_supervisor_iterations": 10,
        "completed_specialists": {"evm_analyst"},
        "plan_data": plan.model_dump(),
        "completed_steps": {0},
        "current_step_index": -1,
        "current_invocation_id": "",
        "replan_count": 0,
        "max_replan_count": 2,
        "replan_context": "",
    }

    result = await wrapper_fn(state)

    # Routes to supervisor (with guidance), NOT to END, and the specialist
    # graph is NOT invoked.
    assert hasattr(result, "goto")
    assert result.goto == "supervisor"
    assert result.update["active_agent"] == "supervisor"
    msgs = result.update.get("messages")
    assert msgs and "do NOT delegate" in msgs[0].content
    mock_specialist_graph.ainvoke.assert_not_awaited()
