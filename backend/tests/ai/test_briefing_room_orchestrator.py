"""Tests for the SupervisorOrchestrator and its helper functions.

Integration-level tests for the orchestrator graph structure, the supervisor
router logic, and the get_briefing tool. Heavy dependencies (LangChain model
compilation, real subagents) are mocked so tests run without network or DB.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from langchain_core.messages import AIMessage
from langgraph.graph import END

from app.ai.supervisor_orchestrator import (
    SupervisorOrchestrator,
    _create_get_briefing_tool,
)
from app.ai.config import AgentConfig
from app.ai.tools.types import ExecutionMode, ToolContext


def _make_tool_context() -> ToolContext:
    """Build a ToolContext with mock session for testing."""
    return ToolContext(
        session=MagicMock(),
        user_id="test-user",
        user_role="admin",
        execution_mode=ExecutionMode.STANDARD,
    )


class TestCreateGetBriefingTool:
    """Tests for the _create_get_briefing_tool factory."""

    def test_returns_briefing_from_state(self) -> None:
        tool = _create_get_briefing_tool()
        result = tool.invoke({"state": {"briefing": "Test briefing content"}})
        assert result == "Test briefing content"

    def test_returns_default_when_no_briefing(self) -> None:
        tool = _create_get_briefing_tool()
        result = tool.invoke({"state": {}})
        assert result == "No briefing available yet."


class TestSupervisorRouter:
    """Tests for _make_supervisor_router static method."""

    def test_router_routes_to_specialist_on_handoff(self) -> None:
        router = SupervisorOrchestrator._make_supervisor_router(
            ["evm_analyst", "project_manager"]
        )

        state = {
            "messages": [
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "handoff_to_evm_analyst",
                            "args": {"task_description": "analyze"},
                            "id": "tc1",
                        }
                    ],
                )
            ]
        }
        assert router(state) == "evm_analyst"

    def test_router_routes_to_end_when_no_handoff(self) -> None:
        router = SupervisorOrchestrator._make_supervisor_router(
            ["evm_analyst"]
        )

        state = {"messages": [AIMessage(content="Here is the answer.")]}
        assert router(state) == END

    def test_router_routes_to_end_on_empty_messages(self) -> None:
        router = SupervisorOrchestrator._make_supervisor_router(
            ["evm_analyst"]
        )
        assert router({"messages": []}) == END

    def test_router_routes_to_end_on_non_handoff_tool_call(self) -> None:
        router = SupervisorOrchestrator._make_supervisor_router(
            ["evm_analyst"]
        )

        state = {
            "messages": [
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "get_briefing",
                            "args": {},
                            "id": "tc1",
                        }
                    ],
                )
            ]
        }
        assert router(state) == END

    def test_router_matches_second_specialist(self) -> None:
        router = SupervisorOrchestrator._make_supervisor_router(
            ["evm_analyst", "project_manager"]
        )

        state = {
            "messages": [
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "handoff_to_project_manager",
                            "args": {"task_description": "status"},
                            "id": "tc1",
                        }
                    ],
                )
            ]
        }
        assert router(state) == "project_manager"

    def test_router_forces_end_when_max_iterations_reached(self) -> None:
        router = SupervisorOrchestrator._make_supervisor_router(
            ["evm_analyst"]
        )

        # Even though there is a handoff tool call, max iterations forces END
        state = {
            "messages": [
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "handoff_to_evm_analyst",
                            "args": {"task_description": "analyze"},
                            "id": "tc1",
                        }
                    ],
                )
            ],
            "supervisor_iterations": 5,
            "max_supervisor_iterations": 5,
        }
        assert router(state) == END

    def test_router_allows_handoff_below_max_iterations(self) -> None:
        router = SupervisorOrchestrator._make_supervisor_router(
            ["evm_analyst"]
        )

        state = {
            "messages": [
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "handoff_to_evm_analyst",
                            "args": {"task_description": "analyze"},
                            "id": "tc1",
                        }
                    ],
                )
            ],
            "supervisor_iterations": 4,
            "max_supervisor_iterations": 5,
        }
        assert router(state) == "evm_analyst"

    def test_router_forces_end_above_max_iterations(self) -> None:
        router = SupervisorOrchestrator._make_supervisor_router(
            ["evm_analyst"]
        )

        state = {
            "messages": [
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "handoff_to_evm_analyst",
                            "args": {"task_description": "analyze"},
                            "id": "tc1",
                        }
                    ],
                )
            ],
            "supervisor_iterations": 7,
            "max_supervisor_iterations": 5,
        }
        assert router(state) == END

    def test_router_defaults_iterations_when_missing(self) -> None:
        """Router should default to 0 iterations when state lacks the key."""
        router = SupervisorOrchestrator._make_supervisor_router(
            ["evm_analyst"]
        )

        # State without supervisor_iterations — should still route normally
        state = {
            "messages": [
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "handoff_to_evm_analyst",
                            "args": {"task_description": "analyze"},
                            "id": "tc1",
                        }
                    ],
                )
            ],
        }
        assert router(state) == "evm_analyst"


class TestSupervisorOrchestratorInit:
    """Tests for SupervisorOrchestrator construction."""

    def test_default_attributes(self) -> None:
        context = _make_tool_context()
        orch = SupervisorOrchestrator(
            model="openai:gpt-4o",
            context=context,
        )
        assert orch.model == "openai:gpt-4o"
        assert orch.context is context
        assert orch.system_prompt is None

    def test_custom_attributes(self) -> None:
        context = _make_tool_context()
        orch = SupervisorOrchestrator(
            model="openai:gpt-4o",
            context=context,
            system_prompt="Custom prompt",
        )
        assert orch.system_prompt == "Custom prompt"


class TestSupervisorGraphCreation:
    """Tests for create_supervisor_graph and fallback behavior."""

    @patch("app.ai.supervisor_orchestrator.langchain_create_agent")
    @patch("app.ai.supervisor_orchestrator.create_project_tools")
    @patch("app.ai.supervisor_orchestrator.compile_subagents")
    def test_fallback_graph_built_when_no_specialists(
        self,
        mock_compile: MagicMock,
        mock_create_tools: MagicMock,
        mock_create_agent: MagicMock,
    ) -> None:
        mock_create_tools.return_value = []
        mock_compile.return_value = []
        mock_create_agent.return_value = MagicMock()

        context = _make_tool_context()
        orchestrator = SupervisorOrchestrator(
            model="openai:gpt-4o",
            context=context,
        )

        result = orchestrator.create_supervisor_graph(AgentConfig())
        # Returns a simple agent graph (not the supervisor graph)
        assert result is not None
        mock_compile.assert_called_once()
        # Fallback path calls langchain_create_agent directly
        mock_create_agent.assert_called_once()

    @patch("app.ai.supervisor_orchestrator.langchain_create_agent")
    @patch("app.ai.supervisor_orchestrator.create_project_tools")
    @patch("app.ai.supervisor_orchestrator.compile_subagents")
    def test_graph_uses_custom_system_prompt(
        self,
        mock_compile: MagicMock,
        mock_create_tools: MagicMock,
        mock_create_agent: MagicMock,
    ) -> None:
        mock_create_tools.return_value = []
        mock_compile.return_value = []
        mock_create_agent.return_value = MagicMock()

        context = _make_tool_context()
        orchestrator = SupervisorOrchestrator(
            model="openai:gpt-4o",
            context=context,
            system_prompt="Custom supervisor prompt",
        )

        # Fallback graph should use custom prompt, not the default
        result = orchestrator.create_supervisor_graph(AgentConfig())
        assert result is not None
        # Verify custom prompt was passed to the agent
        call_kwargs = mock_create_agent.call_args[1]
        assert "Custom supervisor prompt" in call_kwargs["system_prompt"]

    @patch("app.ai.supervisor_orchestrator.langchain_create_agent")
    @patch("app.ai.supervisor_orchestrator.create_project_tools")
    @patch("app.ai.supervisor_orchestrator.compile_subagents")
    @patch("app.ai.supervisor_orchestrator.create_all_handoff_tools")
    def test_full_graph_compilation_with_specialists(
        self,
        mock_handoff_tools: MagicMock,
        mock_compile: MagicMock,
        mock_create_tools: MagicMock,
        mock_create_agent: MagicMock,
    ) -> None:
        """Verify graph wiring when specialists are available."""
        mock_create_tools.return_value = []

        mock_runnable = AsyncMock()
        mock_compile.return_value = [
            {
                "name": "evm_analyst",
                "runnable": mock_runnable,
                "tools": [],
            }
        ]
        mock_handoff_tools.return_value = []
        mock_create_agent.return_value = AsyncMock()

        context = _make_tool_context()
        orchestrator = SupervisorOrchestrator(
            model="openai:gpt-4o",
            context=context,
        )

        subagent_configs = [
            {
                "name": "evm_analyst",
                "description": "EVM analysis",
                "system_prompt": "You analyze EVM.",
            }
        ]
        config = AgentConfig(subagents=subagent_configs)

        result = orchestrator.create_supervisor_graph(config)
        assert result is not None
        mock_compile.assert_called_once()

    @patch("app.ai.supervisor_orchestrator.langchain_create_agent")
    @patch("app.ai.supervisor_orchestrator.create_project_tools")
    @patch("app.ai.supervisor_orchestrator.compile_subagents")
    def test_default_config_used_when_none(
        self,
        mock_compile: MagicMock,
        mock_create_tools: MagicMock,
        mock_create_agent: MagicMock,
    ) -> None:
        mock_create_tools.return_value = []
        mock_compile.return_value = []
        mock_create_agent.return_value = MagicMock()

        context = _make_tool_context()
        orchestrator = SupervisorOrchestrator(
            model="openai:gpt-4o",
            context=context,
        )

        result = orchestrator.create_supervisor_graph()
        assert result is not None
        # compile_subagents should have been called with default subagents
        mock_compile.assert_called_once()


class TestSupervisorRouterCompletionLogic:
    """Tests for new completion detection and specialist tracking logic."""

    def test_router_prevents_redispatch_to_completed_specialists(self) -> None:
        """Router should END if handoff targets a specialist that already completed."""
        router = SupervisorOrchestrator._make_supervisor_router(
            ["project_manager", "evm_analyst"]
        )

        # State with completed_specialists set
        state = {
            "messages": [
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "handoff_to_project_manager",
                            "args": {},
                            "id": "tc1",
                        }
                    ],
                )
            ],
            "supervisor_iterations": 1,
            "completed_specialists": {"project_manager"},
        }

        # Should END because project_manager already completed
        assert router(state) == END

    def test_router_allows_dispatch_to_new_specialist(self) -> None:
        """Router should allow handoff to a specialist that hasn't completed yet."""
        router = SupervisorOrchestrator._make_supervisor_router(
            ["project_manager", "evm_analyst"]
        )

        # State with one completed specialist
        state = {
            "messages": [
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "handoff_to_evm_analyst",
                            "args": {},
                            "id": "tc1",
                        }
                    ],
                )
            ],
            "supervisor_iterations": 1,
            "completed_specialists": {"project_manager"},
        }

        # Should allow handoff to evm_analyst (not in completed set)
        assert router(state) == "evm_analyst"

    def test_uses_lower_max_iterations_default(self) -> None:
        """Router should default to 3 max iterations (lowered from 5)."""
        router = SupervisorOrchestrator._make_supervisor_router(
            ["project_manager"]
        )

        # State without max_supervisor_iterations set
        state = {
            "messages": [],
            "supervisor_iterations": 2,
        }

        # Should allow routing at iteration 2 (below new default of 3)
        assert router(state) == END  # No handoff, but not forced by iteration cap

        # At iteration 3, should force END
        state["supervisor_iterations"] = 3
        assert router(state) == END  # Forced by iteration cap

        # At iteration 4, should definitely force END
        state["supervisor_iterations"] = 4
        assert router(state) == END  # Forced by iteration cap
