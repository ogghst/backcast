"""Tests for dynamic replanning in supervisor graph."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain.agents.middleware.types import ModelRequest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.tools import BaseTool
from langgraph.types import Command

from app.ai.handoff_tools import create_replan_tool
from app.ai.middleware.plan_aware_tools import PlanAwareToolMiddleware
from app.ai.plan import PlanDocument, PlannerOutput, PlannerStepOutput, PlanStep
from app.ai.planner import _merge_replanned_steps, planner_node
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
    # As of the bounded-termination fix, the max-replan force-END path routes
    # to ``bounded_terminate`` (grounded notice then END) instead of bare END.
    assert result == "bounded_terminate"


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

    valid_specialists = frozenset(
        {"project_manager", "evm_analyst", "visualization_specialist"}
    )
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
async def test_plan_aware_middleware_allows_replan(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify PlanAwareToolMiddleware does not strip request_replan from the tool list."""
    # AI_DELEGATION_ENFORCED is env-driven (backend/.env); force it on here so this
    # test exercises the domain-tool filtering path deterministically, independent
    # of whatever the environment sets.
    monkeypatch.setattr(
        "app.ai.middleware.plan_aware_tools.AI_DELEGATION_ENFORCED", True
    )
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


# =====================================================================
# Test 7: replan with brace-laden dynamic content does not raise
# =====================================================================


@pytest.mark.asyncio
async def test_planner_replan_path_with_braces_in_dynamic_content() -> None:
    """Replan returns the LLM's revision when all dynamic values contain braces.

    Characterization test for the replan assembly now that it uses
    ``render_prompt`` (which never re-scans injected values).  Braces in the
    injected values -- ``replan_context``, the plan step ``task_description``
    / ``result_summary`` (via ``to_prompt_text``), and briefing findings (via
    ``to_markdown``), including ``{__class__}`` -- must not raise and the
    LLM's revised plan must be returned (not the silently-preserved existing
    plan).

    Note: ``str.format`` does NOT actually raise on braces in *values* (only
    on stray braces in the template), and ``_REPLANNER_PROMPT_TEMPLATE`` is a
    hardcoded module constant, so this scenario did not crash historically.
    This test guards the path against future regressions -- e.g. if the
    replanner template ever becomes DB-configurable -- and locks in the
    single-pass, non-rescanning contract.
    """
    existing_plan = PlanDocument(
        original_request="Analyze {project} structure",  # brace in request
        steps=[
            PlanStep(
                step_index=0,
                specialist="evm_analyst",
                task_description="Check {__class__} leak in CPI {calc}",  # braces
                status="completed",
                result_summary="CPI=0.94 with {specialist_section} artifact",
            ),
            PlanStep(
                step_index=1,
                specialist="evm_analyst",
                task_description="Step 1 {pending}",
                status="pending",
            ),
        ],
        requires_planning=True,
    )

    revised_output = PlannerOutput(
        original_request="Analyze {project} structure",
        requires_planning=True,
        estimated_complexity="moderate",
        steps=[
            PlannerStepOutput(
                step_index=0,
                specialist="evm_analyst",
                task_description="Revised task containing {bracket} too",
                dependencies=[],
                expected_output="Revised {result}",
            ),
        ],
    )

    mock_llm = AsyncMock()
    mock_llm.ainvoke.return_value = MagicMock(content=revised_output.model_dump_json())

    # Briefing findings carry braces too (to_markdown output is injected)
    briefing_data: dict[str, Any] = {
        "original_request": "Analyze {project} structure",
        "sections": [
            {
                "specialist_name": "evm_analyst",
                "findings": "CPI=0.94 {__class__} artifact in {plan_section}",
                "key_findings": ["{__class__} present"],
                "open_questions": [],
                "delegation_notes": "",
                "task_description": "Check {__class__} leak",
            }
        ],
        "supervisor_analysis": "",
        "task_history": [],
    }

    state: dict[str, Any] = {
        "messages": [HumanMessage(content="Analyze {project} structure")],
        "plan_data": existing_plan.model_dump(),
        "replan_context": "Step 1 redundant: {__class__} makes {plan_section} moot",
        "briefing_data": briefing_data,
    }

    catalog = [
        {"name": "evm_analyst", "description": "EVM metric {analysis}"},
    ]

    # Must not raise; must return the LLM's revised plan (NOT the existing plan).
    result = await planner_node(state, mock_llm, specialist_catalog=catalog)

    assert result["replan_context"] == ""
    plan = PlanDocument.from_state(result["plan_data"])

    # Completed step 0 preserved; revised step added at index 1.
    assert len(plan.steps) == 2
    assert plan.steps[0].status == "completed"
    assert plan.steps[1].status == "pending"
    assert plan.steps[1].specialist == "evm_analyst"
    assert "Revised task" in plan.steps[1].task_description

    # LLM was actually called (the assembly did not bail to the fallback path).
    mock_llm.ainvoke.assert_awaited_once()
