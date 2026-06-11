"""Tests for dynamic replanning in supervisor graph."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain.agents.middleware.types import ModelRequest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.tools import BaseTool
from langgraph.graph import END
from langgraph.types import Command

from app.ai.handoff_tools import create_replan_tool
from app.ai.middleware.plan_aware_tools import PlanAwareToolMiddleware
from app.ai.plan import PlanDocument, PlanStep, PlannerOutput, PlannerStepOutput
from app.ai.planner import _merge_replanned_steps
from app.ai.supervisor_orchestrator import SupervisorOrchestrator


# =====================================================================
# Test 1: create_replan_tool returns correct Command
# =====================================================================


@pytest.mark.asyncio
async def test_replan_tool_returns_command_to_planner() -> None:
    """Verify create_replan_tool() returns Command(goto='planner') with correct state updates."""
    tool = create_replan_tool()

    reason = "Findings make step 2 redundant"
    state: dict[str, Any] = {
        "messages": [],
        "replan_count": 0,
    }
    tool_call_id = "tc_replan_001"

    result = tool.func(reason=reason, state=state, tool_call_id=tool_call_id)

    assert isinstance(result, Command)
    assert result.goto == "planner"
    assert result.graph == Command.PARENT

    update = result.update
    assert update["replan_count"] == 1
    assert update["replan_context"] == reason
    assert update["active_agent"] == "planner"

    # Must NOT touch these fields
    assert "supervisor_iterations" not in update
    assert "completed_specialists" not in update
    assert "completed_steps" not in update


# =====================================================================
# Test 2: Router detects request_replan
# =====================================================================


def test_router_detects_request_replan() -> None:
    """Verify the supervisor router returns 'planner' when request_replan tool is called."""
    router = SupervisorOrchestrator._make_supervisor_router(
        specialist_names=["evm_analyst"],
    )

    state: dict[str, Any] = {
        "messages": [
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "request_replan",
                        "args": {"reason": "test"},
                        "id": "tc1",
                        "type": "tool_call",
                    }
                ],
            )
        ],
        "replan_count": 0,
        "max_replan_count": 2,
        "supervisor_iterations": 0,
        "max_supervisor_iterations": 10,
    }

    result = router(state)
    assert result == "planner"


# =====================================================================
# Test 3: Router blocks replan at max count
# =====================================================================


def test_router_blocks_replan_at_max_count() -> None:
    """Verify the router returns END when max replan count is reached."""
    router = SupervisorOrchestrator._make_supervisor_router(
        specialist_names=["evm_analyst"],
    )

    state: dict[str, Any] = {
        "messages": [
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "request_replan",
                        "args": {"reason": "test"},
                        "id": "tc1",
                        "type": "tool_call",
                    }
                ],
            )
        ],
        "replan_count": 2,
        "max_replan_count": 2,
        "supervisor_iterations": 0,
        "max_supervisor_iterations": 10,
    }

    result = router(state)
    assert result == END


# =====================================================================
# Test 4: _merge_replanned_steps preserves completed steps
# =====================================================================


def test_merge_replanned_steps_preserves_completed() -> None:
    """Verify completed steps keep their original indices and revised steps get new indices."""
    existing_plan = PlanDocument(
        original_request="Analyze project",
        steps=[
            PlanStep(
                step_index=0,
                specialist="project_manager",
                task_description="List projects",
                status="completed",
                result_summary="Found 3 projects",
            ),
            PlanStep(
                step_index=1,
                specialist="evm_analyst",
                task_description="Calculate EVM",
                status="pending",
            ),
        ],
        requires_planning=True,
    )

    new_output = PlannerOutput(
        original_request="Analyze project",
        requires_planning=True,
        estimated_complexity="moderate",
        steps=[
            PlannerStepOutput(
                step_index=0,
                specialist="evm_analyst",
                task_description="Calculate CPI only",
                dependencies=[],
                expected_output="CPI value",
            ),
        ],
    )

    valid_specialists = frozenset({"project_manager", "evm_analyst"})
    merged = _merge_replanned_steps(existing_plan, new_output, valid_specialists)

    # Step 0 preserved as completed
    assert len(merged.steps) == 2
    assert merged.steps[0].step_index == 0
    assert merged.steps[0].status == "completed"
    assert merged.steps[0].specialist == "project_manager"
    assert merged.steps[0].result_summary == "Found 3 projects"

    # Revised step gets index 1 (after last completed at index 0)
    assert merged.steps[1].step_index == 1
    assert merged.steps[1].status == "pending"
    assert merged.steps[1].specialist == "evm_analyst"
    assert merged.steps[1].task_description == "Calculate CPI only"

    # Specialist validation passes
    invalid = merged.validate_specialists(list(valid_specialists))
    assert invalid == []


# =====================================================================
# Test 5: _merge_replanned_steps index continuity
# =====================================================================


def test_merge_replanned_steps_index_continuity() -> None:
    """Verify revised steps get indices starting after the last completed step."""
    existing_plan = PlanDocument(
        original_request="Complex analysis",
        steps=[
            PlanStep(
                step_index=0,
                specialist="project_manager",
                task_description="List projects",
                status="completed",
                result_summary="Done",
            ),
            PlanStep(
                step_index=1,
                specialist="evm_analyst",
                task_description="Calculate metrics",
                status="completed",
                result_summary="Metrics done",
            ),
            PlanStep(
                step_index=2,
                specialist="visualization_specialist",
                task_description="Build dashboard",
                status="completed",
                result_summary="Dashboard built",
            ),
        ],
        requires_planning=True,
    )

    new_output = PlannerOutput(
        original_request="Complex analysis",
        requires_planning=True,
        estimated_complexity="moderate",
        steps=[
            PlannerStepOutput(
                step_index=0,
                specialist="evm_analyst",
                task_description="Deep-dive risk analysis",
                dependencies=[],
                expected_output="Risk report",
            ),
            PlannerStepOutput(
                step_index=1,
                specialist="visualization_specialist",
                task_description="Risk heat map",
                dependencies=[0],
                expected_output="Heat map chart",
            ),
        ],
    )

    valid_specialists = frozenset({"project_manager", "evm_analyst", "visualization_specialist"})
    merged = _merge_replanned_steps(existing_plan, new_output, valid_specialists)

    # 3 completed + 2 revised
    assert len(merged.steps) == 5

    # Completed steps keep indices 0, 1, 2
    assert merged.steps[0].step_index == 0
    assert merged.steps[0].status == "completed"
    assert merged.steps[1].step_index == 1
    assert merged.steps[1].status == "completed"
    assert merged.steps[2].step_index == 2
    assert merged.steps[2].status == "completed"

    # Revised steps get indices 3 and 4
    assert merged.steps[3].step_index == 3
    assert merged.steps[3].status == "pending"
    assert merged.steps[3].specialist == "evm_analyst"
    assert merged.steps[4].step_index == 4
    assert merged.steps[4].status == "pending"
    assert merged.steps[4].specialist == "visualization_specialist"


# =====================================================================
# Test 6: PlanAwareToolMiddleware allows request_replan
# =====================================================================


@pytest.mark.asyncio
async def test_plan_aware_middleware_allows_replan() -> None:
    """Verify PlanAwareToolMiddleware does not strip request_replan from the tool list."""
    middleware = PlanAwareToolMiddleware()

    # Create mock tools
    replan_tool = create_replan_tool()
    get_briefing_mock = MagicMock(spec=BaseTool)
    get_briefing_mock.name = "get_briefing"
    domain_tool_mock = MagicMock(spec=BaseTool)
    domain_tool_mock.name = "get_project"

    tools: list[BaseTool | dict[str, Any]] = [
        get_briefing_mock,
        replan_tool,
        domain_tool_mock,
    ]

    # Build a multi-step plan that should trigger filtering
    plan = PlanDocument(
        original_request="test",
        steps=[
            PlanStep(step_index=0, specialist="evm_analyst", task_description="Step 0"),
            PlanStep(step_index=1, specialist="evm_analyst", task_description="Step 1"),
        ],
        requires_planning=True,
    )

    state: dict[str, Any] = {
        "messages": [],
        "plan_data": plan.model_dump(),
    }

    # Use a real ModelRequest so .override() produces a correct copy
    mock_model = MagicMock()
    request = ModelRequest(
        model=mock_model,
        messages=[],
        system_message=SystemMessage(content="You are a supervisor."),
        tools=tools,
        state=state,
    )

    # Track whether handler received filtered tools
    captured_request: ModelRequest[Any] | None = None

    async def handler(req: ModelRequest[Any]) -> Any:
        nonlocal captured_request
        captured_request = req
        # Simulate model response with no tool calls
        mock_response = MagicMock()
        mock_response.result = [AIMessage(content="done")]
        return mock_response

    await middleware.awrap_model_call(request, handler)

    # After filtering, request_replan must still be present
    assert captured_request is not None
    tool_names = [
        t.name if isinstance(t, BaseTool) else str(t.get("name", ""))
        for t in captured_request.tools
    ]
    assert "request_replan" in tool_names
    assert "get_briefing" in tool_names
    # Domain tool should be filtered out
    assert "get_project" not in tool_names
