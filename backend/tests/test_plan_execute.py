"""Tests for the Plan-Execute Graph implementation.

Covers:
- PlanDocument / PlanStep model construction, mutation, and serialization
- planner_node (LLM-based request decomposition)
- BriefingDocument with plan section and step_index
- Handoff tool step_index propagation
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from app.ai.briefing import BriefingDocument, BriefingSection
from app.ai.handoff_tools import create_handoff_tool
from app.ai.plan import PlanDocument, PlannerOutput, PlannerStepOutput, PlanStep
from app.ai.planner import (
    _build_planner_prompt,
    _convert_planner_output,
    _extract_user_request,
    _fallback_plan,
    planner_node,
)

# Full specialist catalog for planner tests that need multi-specialist validation.
# In production this comes from the DB; tests use this to simulate it.
_TEST_SPECIALIST_CATALOG: list[dict[str, str]] = [
    {"name": "project_manager", "description": "Project CRUD and tracking"},
    {"name": "evm_analyst", "description": "Earned Value calculations"},
    {"name": "visualization_specialist", "description": "Charts and diagrams"},
    {"name": "general_purpose", "description": "Catch-all"},
]
_TEST_SPECIALIST_NAMES = frozenset(e["name"] for e in _TEST_SPECIALIST_CATALOG)


def _make_mock_llm(planner_output: PlannerOutput) -> AsyncMock:
    """Create a mock LLM that returns an AIMessage with JSON content."""
    from langchain_core.messages import AIMessage

    llm = AsyncMock()
    llm.ainvoke = AsyncMock(
        return_value=AIMessage(content=planner_output.model_dump_json())
    )
    return llm


# =====================================================================
# PlanStep / PlanDocument model tests
# =====================================================================


class TestPlanStepCreation:
    """PlanStep field defaults and construction."""

    def test_plan_step_creation(self) -> None:
        step = PlanStep(
            step_index=0,
            specialist="evm_analyst",
            task_description="Calculate CPI for project PRJ-100",
            dependencies=[1, 2],
            input_from_dependencies="Budget data from step 1, schedule from step 2",
            expected_output="CPI value and variance analysis",
        )
        assert step.step_index == 0
        assert step.specialist == "evm_analyst"
        assert step.task_description == "Calculate CPI for project PRJ-100"
        assert step.dependencies == [1, 2]
        assert step.input_from_dependencies == (
            "Budget data from step 1, schedule from step 2"
        )
        assert step.expected_output == "CPI value and variance analysis"
        assert step.status == "pending"
        assert step.result_summary is None

    def test_plan_step_defaults(self) -> None:
        step = PlanStep(
            step_index=3,
            specialist="general_purpose",
            task_description="Do something",
        )
        assert step.dependencies == []
        assert step.input_from_dependencies is None
        assert step.expected_output == ""
        assert step.status == "pending"
        assert step.result_summary is None


class TestPlanDocumentCreation:
    """PlanDocument construction and from_state reconstruction."""

    def test_plan_document_creation(self) -> None:
        steps = [
            PlanStep(
                step_index=0,
                specialist="project_manager",
                task_description="List active projects",
                expected_output="List of project IDs",
            ),
            PlanStep(
                step_index=1,
                specialist="evm_analyst",
                task_description="Calculate EVM metrics",
                dependencies=[0],
                expected_output="EVM indices",
            ),
            PlanStep(
                step_index=2,
                specialist="visualization_specialist",
                task_description="Build dashboard",
                dependencies=[1],
                expected_output="Dashboard charts",
            ),
        ]
        doc = PlanDocument(
            original_request="Analyze EVM performance and create dashboard",
            steps=steps,
            estimated_complexity="complex",
            requires_planning=True,
        )
        assert doc.original_request == "Analyze EVM performance and create dashboard"
        assert len(doc.steps) == 3
        assert doc.estimated_complexity == "complex"
        assert doc.requires_planning is True
        assert doc.specialist_catalog is None

    def test_plan_document_defaults(self) -> None:
        doc = PlanDocument(original_request="Simple request")
        assert doc.steps == []
        assert doc.estimated_complexity == "simple"
        assert doc.requires_planning is False

    def test_plan_document_from_state(self) -> None:
        data = {
            "original_request": "Test request",
            "steps": [
                {
                    "step_index": 0,
                    "specialist": "evm_analyst",
                    "task_description": "Analyze metrics",
                    "dependencies": [],
                    "status": "pending",
                }
            ],
            "estimated_complexity": "moderate",
            "requires_planning": True,
        }
        doc = PlanDocument.from_state(data)
        assert doc.original_request == "Test request"
        assert len(doc.steps) == 1
        assert doc.steps[0].specialist == "evm_analyst"
        assert doc.estimated_complexity == "moderate"
        assert doc.requires_planning is True

    def test_plan_document_from_state_invalid(self) -> None:
        doc = PlanDocument.from_state({"garbage": True})
        assert doc.original_request == "(recovered)"
        assert doc.steps == []
        assert doc.requires_planning is False

    def test_plan_document_from_state_empty(self) -> None:
        doc = PlanDocument.from_state({})
        assert doc.original_request == "(recovered)"


class TestGetNextPendingStep:
    """Navigation to the next executable step."""

    def _make_doc(self) -> PlanDocument:
        return PlanDocument(
            original_request="test",
            steps=[
                PlanStep(
                    step_index=0,
                    specialist="project_manager",
                    task_description="List projects",
                ),
                PlanStep(
                    step_index=1,
                    specialist="evm_analyst",
                    task_description="Calculate EVM",
                    dependencies=[0],
                ),
                PlanStep(
                    step_index=2,
                    specialist="visualization_specialist",
                    task_description="Build charts",
                    dependencies=[1],
                ),
            ],
            requires_planning=True,
        )

    def test_get_next_pending_step(self) -> None:
        doc = self._make_doc()
        step = doc.get_next_pending_step()
        assert step is not None
        assert step.step_index == 0

    def test_get_next_pending_step_after_first_completed(self) -> None:
        doc = self._make_doc()
        doc.mark_step_completed(0, "Found 3 projects")
        step = doc.get_next_pending_step()
        assert step is not None
        assert step.step_index == 1

    def test_get_next_pending_step_all_completed(self) -> None:
        doc = self._make_doc()
        doc.mark_step_completed(0, "Done 0")
        doc.mark_step_completed(1, "Done 1")
        doc.mark_step_completed(2, "Done 2")
        step = doc.get_next_pending_step()
        assert step is None

    def test_get_next_pending_step_blocked(self) -> None:
        """Step with unmet dependencies is skipped."""
        doc = PlanDocument(
            original_request="test",
            steps=[
                PlanStep(
                    step_index=0,
                    specialist="evm_analyst",
                    task_description="Analyze",
                    status="failed",
                ),
                PlanStep(
                    step_index=1,
                    specialist="visualization_specialist",
                    task_description="Chart",
                    dependencies=[0],
                ),
            ],
        )
        # Step 0 is failed (not completed), step 1 depends on 0 -> blocked
        step = doc.get_next_pending_step()
        assert step is None


class TestMarkStep:
    """Step status mutations."""

    def test_mark_step_completed(self) -> None:
        doc = PlanDocument(
            original_request="test",
            steps=[
                PlanStep(
                    step_index=0,
                    specialist="project_manager",
                    task_description="List projects",
                ),
            ],
        )
        doc.mark_step_completed(0, "Found 5 active projects")
        assert doc.steps[0].status == "completed"
        assert doc.steps[0].result_summary == "Found 5 active projects"

    def test_mark_step_completed_nonexistent(self) -> None:
        doc = PlanDocument(
            original_request="test",
            steps=[
                PlanStep(
                    step_index=0,
                    specialist="project_manager",
                    task_description="List projects",
                ),
            ],
        )
        # Should not raise
        doc.mark_step_completed(99, "Does not exist")
        assert doc.steps[0].status == "pending"

    def test_mark_step_failed(self) -> None:
        doc = PlanDocument(
            original_request="test",
            steps=[
                PlanStep(
                    step_index=0,
                    specialist="evm_analyst",
                    task_description="Calculate CPI",
                ),
            ],
        )
        doc.mark_step_failed(0, "No cost registrations found")
        assert doc.steps[0].status == "failed"
        assert doc.steps[0].result_summary == "No cost registrations found"

    def test_mark_step_failed_nonexistent(self) -> None:
        doc = PlanDocument(
            original_request="test",
            steps=[
                PlanStep(
                    step_index=0,
                    specialist="evm_analyst",
                    task_description="Calculate CPI",
                ),
            ],
        )
        doc.mark_step_failed(99, "Nothing")
        assert doc.steps[0].status == "pending"


class TestAreDependenciesMet:
    """Dependency resolution logic."""

    def test_no_dependencies(self) -> None:
        doc = PlanDocument(
            original_request="test",
            steps=[
                PlanStep(
                    step_index=0,
                    specialist="project_manager",
                    task_description="List projects",
                ),
            ],
        )
        assert doc.are_dependencies_met(0) is True

    def test_completed_dependencies(self) -> None:
        doc = PlanDocument(
            original_request="test",
            steps=[
                PlanStep(
                    step_index=0,
                    specialist="project_manager",
                    task_description="List projects",
                ),
                PlanStep(
                    step_index=1,
                    specialist="evm_analyst",
                    task_description="Analyze",
                    dependencies=[0],
                ),
            ],
        )
        doc.mark_step_completed(0, "Done")
        assert doc.are_dependencies_met(1) is True

    def test_pending_dependencies(self) -> None:
        doc = PlanDocument(
            original_request="test",
            steps=[
                PlanStep(
                    step_index=0,
                    specialist="project_manager",
                    task_description="List projects",
                ),
                PlanStep(
                    step_index=1,
                    specialist="evm_analyst",
                    task_description="Analyze",
                    dependencies=[0],
                ),
            ],
        )
        # Step 0 still pending
        assert doc.are_dependencies_met(1) is False

    def test_nonexistent_step_returns_false(self) -> None:
        doc = PlanDocument(original_request="test", steps=[])
        assert doc.are_dependencies_met(0) is False

    def test_nonexistent_dependency_returns_false(self) -> None:
        """A dependency referencing a step that doesn't exist is unmet."""
        doc = PlanDocument(
            original_request="test",
            steps=[
                PlanStep(
                    step_index=0,
                    specialist="evm_analyst",
                    task_description="Analyze",
                    dependencies=[5],  # no step with index 5
                ),
            ],
        )
        assert doc.are_dependencies_met(0) is False


class TestValidateSpecialists:
    """Specialist name validation against the known catalog."""

    def test_valid_specialists(self) -> None:
        doc = PlanDocument(
            original_request="test",
            steps=[
                PlanStep(
                    step_index=0,
                    specialist="evm_analyst",
                    task_description="Analyze",
                ),
                PlanStep(
                    step_index=1,
                    specialist="project_manager",
                    task_description="List",
                ),
            ],
        )
        invalid = doc.validate_specialists(list(_TEST_SPECIALIST_NAMES))
        assert invalid == []

    def test_invalid_specialists_returned(self) -> None:
        doc = PlanDocument(
            original_request="test",
            steps=[
                PlanStep(
                    step_index=0,
                    specialist="evm_analyst",
                    task_description="Analyze",
                ),
                PlanStep(
                    step_index=1,
                    specialist="nonexistent_specialist",
                    task_description="Hack",
                ),
                PlanStep(
                    step_index=2,
                    specialist="another_fake",
                    task_description="Hack 2",
                ),
            ],
        )
        invalid = doc.validate_specialists(list(_TEST_SPECIALIST_NAMES))
        assert "nonexistent_specialist" in invalid
        assert "another_fake" in invalid
        assert "evm_analyst" not in invalid

    def test_duplicate_invalid_deduped(self) -> None:
        doc = PlanDocument(
            original_request="test",
            steps=[
                PlanStep(
                    step_index=0,
                    specialist="fake",
                    task_description="A",
                ),
                PlanStep(
                    step_index=1,
                    specialist="fake",
                    task_description="B",
                ),
            ],
        )
        invalid = doc.validate_specialists(list(_TEST_SPECIALIST_NAMES))
        assert invalid == ["fake"]

    def test_empty_plan_no_specialists(self) -> None:
        doc = PlanDocument(original_request="test")
        assert doc.validate_specialists([]) == []


class TestToPromptText:
    """Prompt serialization output."""

    def test_to_prompt_text(self) -> None:
        doc = PlanDocument(
            original_request="Analyze EVM and build dashboard",
            steps=[
                PlanStep(
                    step_index=0,
                    specialist="evm_analyst",
                    task_description="Calculate EVM metrics",
                    expected_output="CPI, SPI values",
                ),
                PlanStep(
                    step_index=1,
                    specialist="visualization_specialist",
                    task_description="Build dashboard",
                    dependencies=[0],
                    input_from_dependencies="EVM metrics from step 0",
                ),
            ],
            estimated_complexity="moderate",
            requires_planning=True,
        )
        text = doc.to_prompt_text()
        assert "## Execution Plan" in text
        assert "Request: Analyze EVM and build dashboard" in text
        assert "Complexity: moderate" in text
        assert "Steps: 2" in text
        assert "[ ] evm_analyst: Calculate EVM metrics" in text
        assert "[ ] visualization_specialist: Build dashboard" in text
        assert "depends on [0]" in text
        assert "Input: EVM metrics from step 0" in text

    def test_to_prompt_text_completed_step(self) -> None:
        doc = PlanDocument(
            original_request="test",
            steps=[
                PlanStep(
                    step_index=0,
                    specialist="project_manager",
                    task_description="List projects",
                ),
            ],
        )
        doc.mark_step_completed(0, "Found 3 projects")
        text = doc.to_prompt_text()
        assert "[x] project_manager: List projects" in text
        assert "Result: Found 3 projects" in text

    def test_to_prompt_text_failed_step(self) -> None:
        doc = PlanDocument(
            original_request="test",
            steps=[
                PlanStep(
                    step_index=0,
                    specialist="evm_analyst",
                    task_description="Bad analysis",
                ),
            ],
        )
        doc.mark_step_failed(0, "Data unavailable")
        text = doc.to_prompt_text()
        assert "[!] evm_analyst: Bad analysis" in text
        assert "Result: Data unavailable" in text


class TestRequiresPlanningFalse:
    """Single-step plan documents."""

    def test_requires_planning_false(self) -> None:
        doc = PlanDocument(
            original_request="Show me project ACME budget",
            steps=[
                PlanStep(
                    step_index=0,
                    specialist="project_manager",
                    task_description="Show project budget",
                ),
            ],
            requires_planning=False,
        )
        assert doc.requires_planning is False
        assert len(doc.steps) == 1
        step = doc.get_next_pending_step()
        assert step is not None
        assert step.specialist == "project_manager"


# =====================================================================
# planner_node tests
# =====================================================================


class TestPlannerNode:
    """planner_node LLM-based decomposition and fallback behavior."""

    @pytest.mark.asyncio
    async def test_planner_simple_request(self) -> None:
        """Single-domain request produces requires_planning=false."""
        output = PlannerOutput(
            original_request="Show me project ACME budget status",
            requires_planning=False,
            estimated_complexity="simple",
            steps=[
                PlannerStepOutput(
                    step_index=0,
                    specialist="project_manager",
                    task_description="Show project ACME budget status",
                    dependencies=[],
                    expected_output="Budget summary for ACME",
                )
            ],
        )
        llm = _make_mock_llm(output)

        state: dict[str, Any] = {
            "messages": [HumanMessage(content="Show me project ACME budget status")],
        }
        result = await planner_node(
            state, llm, specialist_catalog=_TEST_SPECIALIST_CATALOG
        )
        plan_data = result["plan_data"]
        assert plan_data["requires_planning"] is False
        assert len(plan_data["steps"]) == 1
        assert plan_data["steps"][0]["specialist"] == "project_manager"

    @pytest.mark.asyncio
    async def test_planner_complex_request(self) -> None:
        """Multi-domain request produces requires_planning=true with multiple steps."""
        output = PlannerOutput(
            original_request="Analyze EVM performance and create dashboard",
            requires_planning=True,
            estimated_complexity="complex",
            steps=[
                PlannerStepOutput(
                    step_index=0,
                    specialist="evm_analyst",
                    task_description="Calculate EVM metrics",
                    dependencies=[],
                    expected_output="CPI, SPI values",
                ),
                PlannerStepOutput(
                    step_index=1,
                    specialist="visualization_specialist",
                    task_description="Build dashboard from metrics",
                    dependencies=[0],
                    expected_output="EVM dashboard",
                ),
            ],
        )
        llm = _make_mock_llm(output)

        state: dict[str, Any] = {
            "messages": [
                HumanMessage(content="Analyze EVM performance and create dashboard")
            ],
        }
        result = await planner_node(
            state, llm, specialist_catalog=_TEST_SPECIALIST_CATALOG
        )
        plan_data = result["plan_data"]
        assert plan_data["requires_planning"] is True
        assert len(plan_data["steps"]) == 2
        assert plan_data["estimated_complexity"] == "complex"
        assert plan_data["steps"][1]["dependencies"] == [0]

    @pytest.mark.asyncio
    async def test_planner_fallback_on_error(self) -> None:
        """LLM exception triggers single-step fallback."""
        structured_mock = AsyncMock()
        structured_mock.ainvoke = AsyncMock(side_effect=RuntimeError("LLM unavailable"))
        llm = AsyncMock()
        llm.with_structured_output = MagicMock(return_value=structured_mock)

        state: dict[str, Any] = {
            "messages": [HumanMessage(content="Do something complex")],
        }
        result = await planner_node(state, llm)
        plan_data = result["plan_data"]
        assert plan_data["requires_planning"] is False
        assert len(plan_data["steps"]) == 1
        assert plan_data["steps"][0]["specialist"] == "general_purpose"

    @pytest.mark.asyncio
    async def test_planner_preserves_user_request(self) -> None:
        """original_request in the plan matches the user message."""
        output = PlannerOutput(
            original_request="What is the CPI for PRJ-100?",
            requires_planning=False,
            estimated_complexity="simple",
            steps=[
                PlannerStepOutput(
                    step_index=0,
                    specialist="evm_analyst",
                    task_description="Calculate CPI for PRJ-100",
                    dependencies=[],
                    expected_output="CPI value",
                )
            ],
        )
        llm = _make_mock_llm(output)

        state: dict[str, Any] = {
            "messages": [HumanMessage(content="What is the CPI for PRJ-100?")],
        }
        result = await planner_node(
            state, llm, specialist_catalog=_TEST_SPECIALIST_CATALOG
        )
        plan_data = result["plan_data"]
        assert plan_data["original_request"] == "What is the CPI for PRJ-100?"

    @pytest.mark.asyncio
    async def test_planner_no_user_message(self) -> None:
        """Missing user message produces a fallback plan."""
        llm = AsyncMock()
        state: dict[str, Any] = {"messages": []}
        result = await planner_node(state, llm)
        plan_data = result["plan_data"]
        assert plan_data["original_request"] == "(no request)"
        assert plan_data["requires_planning"] is False
        # LLM should not have been called
        llm.with_structured_output.assert_not_called()

    @pytest.mark.asyncio
    async def test_planner_unknown_specialist_defaults(self) -> None:
        """Unknown specialist name from LLM defaults to general_purpose."""
        output = PlannerOutput(
            original_request="test unknown",
            requires_planning=False,
            estimated_complexity="simple",
            steps=[
                PlannerStepOutput(
                    step_index=0,
                    specialist="super_hacker",
                    task_description="break things",
                )
            ],
        )
        llm = _make_mock_llm(output)

        state: dict[str, Any] = {
            "messages": [HumanMessage(content="test unknown")],
        }
        result = await planner_node(state, llm)
        plan_data = result["plan_data"]
        assert plan_data["steps"][0]["specialist"] == "general_purpose"


# =====================================================================
# Planner helper function tests
# =====================================================================


class TestPlannerHelpers:
    """Unit tests for internal planner utilities."""

    def test_build_planner_prompt_basic(self) -> None:
        prompt = _build_planner_prompt("Show budget")
        assert "User request: Show budget" in prompt

    def test_build_planner_prompt_with_context(self) -> None:
        prompt = _build_planner_prompt(
            "Follow-up question", briefing_context="Previous analysis..."
        )
        assert "Existing briefing context" in prompt
        assert "Previous analysis..." in prompt

    def test_extract_user_request(self) -> None:
        messages = [
            HumanMessage(content="First message"),
            AIMessage(content="Response"),
            HumanMessage(content="Latest message"),
        ]
        assert _extract_user_request(messages) == "Latest message"

    def test_extract_user_request_empty(self) -> None:
        assert _extract_user_request([]) == ""

    def test_extract_user_request_no_human(self) -> None:
        messages = [AIMessage(content="Just AI")]
        assert _extract_user_request(messages) == ""

    def test_fallback_plan(self) -> None:
        plan = _fallback_plan("Emergency request")
        assert plan.original_request == "Emergency request"
        assert plan.requires_planning is False
        assert len(plan.steps) == 1
        assert plan.steps[0].specialist == "general_purpose"


# =====================================================================
# _convert_planner_output tests
# =====================================================================


class TestConvertPlannerOutput:
    """Tests for _convert_planner_output: PlannerOutput -> PlanDocument conversion."""

    def test_basic_conversion(self) -> None:
        output = PlannerOutput(
            original_request="Analyze EVM",
            requires_planning=True,
            estimated_complexity="moderate",
            steps=[
                PlannerStepOutput(
                    step_index=0,
                    specialist="evm_analyst",
                    task_description="Calculate EVM metrics",
                    dependencies=[],
                    expected_output="CPI, SPI values",
                ),
            ],
        )
        plan = _convert_planner_output(output, valid_specialists=_TEST_SPECIALIST_NAMES)
        assert isinstance(plan, PlanDocument)
        assert plan.original_request == "Analyze EVM"
        assert plan.requires_planning is True
        assert plan.estimated_complexity == "moderate"
        assert len(plan.steps) == 1
        assert plan.steps[0].status == "pending"
        assert plan.steps[0].result_summary is None

    def test_unknown_specialist_defaults(self) -> None:
        output = PlannerOutput(
            original_request="test",
            requires_planning=False,
            estimated_complexity="simple",
            steps=[
                PlannerStepOutput(
                    step_index=0,
                    specialist="nonexistent_specialist",
                    task_description="Do something",
                ),
            ],
        )
        plan = _convert_planner_output(output, valid_specialists=_TEST_SPECIALIST_NAMES)
        assert plan.steps[0].specialist == "general_purpose"

    def test_unknown_specialist_no_catalog(self) -> None:
        """Without catalog, all specialists default to general_purpose."""
        output = PlannerOutput(
            original_request="test",
            requires_planning=False,
            estimated_complexity="simple",
            steps=[
                PlannerStepOutput(
                    step_index=0,
                    specialist="project_manager",
                    task_description="Do something",
                ),
            ],
        )
        plan = _convert_planner_output(output)  # No valid_specialists
        assert plan.steps[0].specialist == "general_purpose"

    def test_empty_steps_triggers_fallback(self) -> None:
        output = PlannerOutput(
            original_request="test",
            requires_planning=False,
            estimated_complexity="simple",
            steps=[],
        )
        plan = _convert_planner_output(output)
        assert plan.original_request == "test"
        assert len(plan.steps) == 1
        assert plan.steps[0].specialist == "general_purpose"

    def test_multiple_steps_with_dependencies(self) -> None:
        output = PlannerOutput(
            original_request="Analyze and visualize",
            requires_planning=True,
            estimated_complexity="complex",
            steps=[
                PlannerStepOutput(
                    step_index=0,
                    specialist="evm_analyst",
                    task_description="Calculate metrics",
                    expected_output="EVM indices",
                ),
                PlannerStepOutput(
                    step_index=1,
                    specialist="visualization_specialist",
                    task_description="Build dashboard",
                    dependencies=[0],
                    expected_output="Dashboard charts",
                ),
            ],
        )
        plan = _convert_planner_output(output, valid_specialists=_TEST_SPECIALIST_NAMES)
        assert len(plan.steps) == 2
        assert plan.steps[0].specialist == "evm_analyst"
        assert plan.steps[1].specialist == "visualization_specialist"
        assert plan.steps[1].dependencies == [0]


# =====================================================================
# BriefingDocument tests
# =====================================================================


class TestBriefingWithPlan:
    """BriefingSection step_index and BriefingDocument plan rendering."""

    def test_briefing_section_with_step_index(self) -> None:
        section = BriefingSection(
            specialist_name="evm_analyst",
            findings="CPI is 0.85, indicating cost overrun",
            step_index=2,
        )
        assert section.step_index == 2

    def test_briefing_section_without_step_index(self) -> None:
        section = BriefingSection(
            specialist_name="evm_analyst",
            findings="Some findings",
        )
        assert section.step_index is None

    def test_briefing_document_with_plan(self) -> None:
        doc = BriefingDocument(
            original_request="Analyze and chart",
            plan=[
                {
                    "specialist": "evm_analyst",
                    "task_description": "Calculate metrics",
                    "status": "completed",
                },
                {
                    "specialist": "visualization_specialist",
                    "task_description": "Build charts",
                    "status": "pending",
                },
            ],
        )
        md = doc.to_markdown()
        assert "## Execution Plan" in md
        assert "Step 1: [evm_analyst] Calculate metrics — completed" in md
        assert "Step 2: [visualization_specialist] Build charts — pending" in md

    def test_briefing_without_plan(self) -> None:
        """No plan section renders nothing plan-related (backward compatible)."""
        doc = BriefingDocument(
            original_request="Simple question",
            sections=[
                BriefingSection(
                    specialist_name="project_manager",
                    findings="Budget is on track",
                ),
            ],
        )
        md = doc.to_markdown()
        assert "## Execution Plan" not in md
        assert "## Specialist Findings" in md
        assert "Budget is on track" in md

    def test_briefing_section_step_index_in_markdown(self) -> None:
        """Sections with step_index show it in the header (0-based index)."""
        doc = BriefingDocument(
            original_request="test",
            sections=[
                BriefingSection(
                    specialist_name="evm_analyst",
                    findings="Metrics calculated",
                    step_index=0,
                ),
                BriefingSection(
                    specialist_name="visualization_specialist",
                    findings="Chart built",
                    step_index=1,
                ),
            ],
        )
        md = doc.to_markdown()
        assert "### evm_analyst (Step 0)" in md
        assert "### visualization_specialist (Step 1)" in md

    def test_briefing_section_iteration_in_markdown(self) -> None:
        """Sections without step_index show iteration number."""
        doc = BriefingDocument(
            original_request="test",
            sections=[
                BriefingSection(
                    specialist_name="project_manager",
                    findings="First finding",
                ),
                BriefingSection(
                    specialist_name="evm_analyst",
                    findings="Second finding",
                ),
            ],
        )
        md = doc.to_markdown()
        assert "### project_manager (Iteration 1)" in md
        assert "### evm_analyst (Iteration 2)" in md


# =====================================================================
# Handoff tool tests
# =====================================================================


class TestHandoffTool:
    """Handoff tool step_index propagation and backward compatibility."""

    def _make_state(
        self,
        briefing_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return {
            "messages": [],
            "briefing_data": briefing_data
            or BriefingDocument(original_request="test").model_dump(),
        }

    def test_handoff_with_step_index(self) -> None:
        tool = create_handoff_tool(
            agent_name="evm_analyst",
            agent_description="EVM analysis specialist",
        )
        # Call tool.func directly to bypass LangChain's injected-arg
        # validation that requires a live graph context.
        result = tool.func(
            task_description="Calculate CPI",
            rationale="Need EVM expertise",
            step_index=2,
            state=self._make_state(),
            tool_call_id="tc_123",
        )
        # Command.update should contain current_step_index
        assert result.update["current_step_index"] == 2
        assert result.update["active_agent"] == "evm_analyst"
        assert result.goto == "evm_analyst"

    def test_handoff_without_step_index(self) -> None:
        tool = create_handoff_tool(
            agent_name="project_manager",
            agent_description="Project management specialist",
        )
        result = tool.func(
            task_description="List projects",
            state=self._make_state(),
            tool_call_id="tc_456",
        )
        assert "current_step_index" not in result.update
        assert result.update["active_agent"] == "project_manager"

    def test_handoff_propagates_analysis(self) -> None:
        tool = create_handoff_tool(
            agent_name="evm_analyst",
            agent_description="EVM analysis specialist",
        )
        briefing = BriefingDocument(original_request="test request")
        result = tool.func(
            task_description="Calculate metrics",
            analysis="User needs CPI and SPI",
            rationale="EVM domain",
            state=self._make_state(briefing.model_dump()),
            tool_call_id="tc_789",
        )
        updated_briefing = BriefingDocument.model_validate(
            result.update["briefing_data"]
        )
        assert updated_briefing.supervisor_analysis == "User needs CPI and SPI"
        assert len(updated_briefing.task_history) == 1
        assert updated_briefing.task_history[0].specialist == "evm_analyst"

    def test_handoff_tool_metadata(self) -> None:
        tool = create_handoff_tool(
            agent_name="evm_analyst",
            agent_description="EVM analysis specialist",
        )
        from app.ai.handoff_tools import METADATA_KEY_HANDOFF_DESTINATION

        assert tool.metadata[METADATA_KEY_HANDOFF_DESTINATION] == "evm_analyst"

    def test_handoff_tool_name_slugified(self) -> None:
        tool = create_handoff_tool(
            agent_name="evm analyst",
            agent_description="EVM specialist",
        )
        assert tool.name == "handoff_to_evm_analyst"
