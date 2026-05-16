"""Tests for specialist wrapper node factory (now inside SupervisorOrchestrator).

Tests ``SupervisorOrchestrator._create_specialist_wrapper`` which wraps
specialist agents in isolated nodes that receive only the compiled briefing
document.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.types import Command

from app.ai.briefing_compiler import initialize_briefing
from app.ai.supervisor_orchestrator import SupervisorOrchestrator
from app.ai.tools.types import ExecutionMode, ToolContext


def _make_tool_context() -> ToolContext:
    """Build a minimal ToolContext for test orchestration."""
    return ToolContext(
        session=MagicMock(),
        user_id="test-user",
        user_role="admin",
        execution_mode=ExecutionMode.STANDARD,
    )


def _make_initial_state(**overrides: object) -> dict[str, object]:
    """Build a minimal BackcastSupervisorState-like dict for testing."""
    data = initialize_briefing("What's the status?")
    state: dict[str, object] = {
        "messages": [HumanMessage(content="What's the status?")],
        "briefing_data": data,
        "active_agent": "supervisor",
        "tool_call_count": 0,
        "max_tool_iterations": 25,
        "supervisor_iterations": 0,
        "max_supervisor_iterations": 3,
        "completed_specialists": set(),
    }
    state.update(overrides)
    return state


def _get_update(result: Command[Any]) -> dict[str, Any]:
    """Extract and validate the Command update dict."""
    assert result.update is not None
    return result.update


class TestCreateBriefingSpecialistNode:
    """Tests for the specialist node factory function."""

    @pytest.mark.asyncio
    async def test_reads_briefing_from_state(self) -> None:
        mock_graph = AsyncMock()
        mock_graph.ainvoke.return_value = {
            "messages": [AIMessage(content="Project is 45% complete")],
            "tool_call_count": 2,
        }

        orch = SupervisorOrchestrator(
            model="openai:gpt-4o", context=_make_tool_context()
        )
        node = orch._create_specialist_wrapper(
            specialist_name="project_manager",
            specialist_graph=mock_graph,
        )

        state = _make_initial_state()
        await node(state)

        mock_graph.ainvoke.assert_called_once()
        call_args = mock_graph.ainvoke.call_args
        input_state = call_args[0][0]
        messages = input_state["messages"]

        # Single HumanMessage with assignment + briefing + scope boundary
        assert len(messages) == 1
        assert isinstance(messages[0], HumanMessage)
        assert "Briefing" in messages[0].content

    @pytest.mark.asyncio
    async def test_captures_final_output(self) -> None:
        mock_graph = AsyncMock()
        mock_graph.ainvoke.return_value = {
            "messages": [AIMessage(content="CPI: 0.95, SPI: 1.05")],
            "tool_call_count": 3,
        }

        orch = SupervisorOrchestrator(
            model="openai:gpt-4o", context=_make_tool_context()
        )
        node = orch._create_specialist_wrapper(
            specialist_name="evm_analyst",
            specialist_graph=mock_graph,
        )

        state = _make_initial_state()
        result = await node(state)

        assert isinstance(result, Command)
        upd = _get_update(result)
        assert "evm_analyst" in str(upd.get("briefing_data", ""))
        assert upd["active_agent"] == "supervisor"
        assert upd["tool_call_count"] == 3
        assert upd["supervisor_iterations"] == 1
        assert upd["completed_specialists"] == {"evm_analyst"}

    @pytest.mark.asyncio
    async def test_handles_tool_calls_in_summary(self) -> None:
        mock_graph = AsyncMock()
        mock_graph.ainvoke.return_value = {
            "messages": [
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "list_projects",
                            "args": {"project_id": "123"},
                            "id": "tc1",
                        }
                    ],
                ),
                ToolMessage(content="result", tool_call_id="tc1"),
                AIMessage(content="Found project PRJ-001"),
            ],
            "tool_call_count": 1,
        }

        orch = SupervisorOrchestrator(
            model="openai:gpt-4o", context=_make_tool_context()
        )
        node = orch._create_specialist_wrapper(
            specialist_name="project_manager",
            specialist_graph=mock_graph,
        )

        state = _make_initial_state()
        result = await node(state)

        assert isinstance(result, Command)
        assert _get_update(result)["active_agent"] == "supervisor"

    @pytest.mark.asyncio
    async def test_handles_empty_result(self) -> None:
        mock_graph = AsyncMock()
        mock_graph.ainvoke.return_value = {
            "messages": [],
            "tool_call_count": 0,
        }

        orch = SupervisorOrchestrator(
            model="openai:gpt-4o", context=_make_tool_context()
        )
        node = orch._create_specialist_wrapper(
            specialist_name="test",
            specialist_graph=mock_graph,
        )

        state = _make_initial_state()
        result = await node(state)

        assert isinstance(result, Command)
        upd = _get_update(result)
        assert "briefing_data" in upd
        assert upd["active_agent"] == "supervisor"
        assert "completed_specialists" in upd

    @pytest.mark.asyncio
    async def test_passes_max_iterations_to_graph(self) -> None:
        mock_graph = AsyncMock()
        mock_graph.ainvoke.return_value = {
            "messages": [AIMessage(content="done")],
            "tool_call_count": 0,
        }

        orch = SupervisorOrchestrator(
            model="openai:gpt-4o", context=_make_tool_context()
        )
        node = orch._create_specialist_wrapper(
            specialist_name="test",
            specialist_graph=mock_graph,
        )

        state = _make_initial_state(max_tool_iterations=10)
        await node(state)

        call_args = mock_graph.ainvoke.call_args
        input_state = call_args[0][0]
        assert input_state["max_tool_iterations"] == 10
        invoke_config = call_args[1].get("config", {})
        assert invoke_config.get("recursion_limit") == 10

    @pytest.mark.asyncio
    async def test_skips_tool_call_ai_messages_for_findings(self) -> None:
        """Last AIMessage with tool_calls should not be used as findings."""
        mock_graph = AsyncMock()
        mock_graph.ainvoke.return_value = {
            "messages": [
                AIMessage(
                    content="I will look that up",
                    tool_calls=[
                        {
                            "name": "get_project",
                            "args": {"id": "1"},
                            "id": "tc1",
                        }
                    ],
                ),
                ToolMessage(content="project data", tool_call_id="tc1"),
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "get_costs",
                            "args": {"project_id": "1"},
                            "id": "tc2",
                        }
                    ],
                ),
            ],
            "tool_call_count": 2,
        }

        orch = SupervisorOrchestrator(
            model="openai:gpt-4o", context=_make_tool_context()
        )
        node = orch._create_specialist_wrapper(
            specialist_name="test",
            specialist_graph=mock_graph,
        )

        state = _make_initial_state()
        result = await node(state)

        assert isinstance(result, Command)
        assert _get_update(result)["active_agent"] == "supervisor"

    @pytest.mark.asyncio
    async def test_early_exit_when_specialist_already_completed(self) -> None:
        """Specialist should return Command with goto=END if already in completed_specialists."""
        mock_graph = AsyncMock()

        orch = SupervisorOrchestrator(
            model="openai:gpt-4o", context=_make_tool_context()
        )
        node = orch._create_specialist_wrapper(
            specialist_name="project_manager",
            specialist_graph=mock_graph,
        )

        state = _make_initial_state(completed_specialists={"project_manager"})
        result = await node(state)

        assert isinstance(result, Command)
        assert result.goto == "__end__"
        assert _get_update(result) == {
            "active_agent": "supervisor",
            "supervisor_iterations": 1,
        }
        mock_graph.ainvoke.assert_not_called()

    @pytest.mark.asyncio
    async def test_normal_execution_when_specialist_not_completed(self) -> None:
        """Specialist should execute normally when not in completed_specialists."""
        mock_graph = AsyncMock()
        mock_graph.ainvoke.return_value = {
            "messages": [AIMessage(content="Project created")],
            "tool_call_count": 1,
        }

        orch = SupervisorOrchestrator(
            model="openai:gpt-4o", context=_make_tool_context()
        )
        node = orch._create_specialist_wrapper(
            specialist_name="project_manager",
            specialist_graph=mock_graph,
        )

        state = _make_initial_state(completed_specialists=set())
        result = await node(state)

        assert isinstance(result, Command)
        mock_graph.ainvoke.assert_called_once()
        assert _get_update(result)["completed_specialists"] == {"project_manager"}

    @pytest.mark.asyncio
    async def test_early_exit_increments_iteration_count(self) -> None:
        """Early exit should increment supervisor_iterations to enforce iteration cap."""
        mock_graph = AsyncMock()

        orch = SupervisorOrchestrator(
            model="openai:gpt-4o", context=_make_tool_context()
        )
        node = orch._create_specialist_wrapper(
            specialist_name="project_manager",
            specialist_graph=mock_graph,
        )

        state = _make_initial_state(completed_specialists={"project_manager"})
        result = await node(state)

        assert isinstance(result, Command)
        assert _get_update(result) == {
            "active_agent": "supervisor",
            "supervisor_iterations": 1,
        }
        assert result.goto == "__end__"
        mock_graph.ainvoke.assert_not_called()

    @pytest.mark.asyncio
    async def test_returns_error_state_on_specialist_exception(self) -> None:
        """Specialist failure should return Command with error in briefing, not raise."""
        mock_graph = AsyncMock()
        mock_graph.ainvoke.side_effect = Exception("Recursion limit reached")

        orch = SupervisorOrchestrator(
            model="openai:gpt-4o", context=_make_tool_context()
        )
        node = orch._create_specialist_wrapper(
            specialist_name="evm_analyst",
            specialist_graph=mock_graph,
        )

        state = _make_initial_state()
        result = await node(state)

        assert isinstance(result, Command)
        upd = _get_update(result)
        assert upd["active_agent"] == "supervisor"
        # Error path does NOT add to completed_specialists (allows retry)
        assert "completed_specialists" not in upd
        # Error should be captured in briefing_data
        briefing_data = upd.get("briefing_data", {})
        assert "evm_analyst" in str(briefing_data)
        assert "error" in str(briefing_data).lower() or "Error" in str(briefing_data)
        assert upd["supervisor_iterations"] == 1
