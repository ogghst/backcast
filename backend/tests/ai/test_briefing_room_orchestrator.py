"""Tests for the SupervisorOrchestrator and its helper functions.

Integration-level tests for the orchestrator graph structure, the supervisor
router logic, and the get_briefing tool. Heavy dependencies (LangChain model
compilation, real subagents) are mocked so tests run without network or DB.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import END

from app.ai.briefing import BriefingDocument, BriefingSection, TaskAssignment
from app.ai.config import AgentConfig
from app.ai.supervisor_orchestrator import (
    SupervisorOrchestrator,
    _briefing_update,
    _create_get_briefing_tool,
)
from app.ai.tools.types import ExecutionMode, ToolContext


def _make_tool_context() -> ToolContext:
    """Build a ToolContext with mock session for testing."""
    return ToolContext(
        session=MagicMock(),
        user_id="test-user",
        user_role="admin",
        execution_mode=ExecutionMode.STANDARD,
    )


def _make_briefing_data(
    original_request: str = "Test request",
    sections: list[BriefingSection] | None = None,
) -> dict:
    """Build a serialized BriefingDocument dict for testing."""
    doc = BriefingDocument(
        original_request=original_request,
        sections=sections or [],
    )
    return doc.model_dump()


# ---------------------------------------------------------------------------
# _briefing_update
# ---------------------------------------------------------------------------


class TestBriefingUpdate:
    """Tests for the _briefing_update helper."""

    def test_returns_state_update_with_sections(self) -> None:
        doc = BriefingDocument(
            original_request="Analyze project",
            sections=[
                BriefingSection(
                    specialist_name="evm_analyst",
                    task_description="Run EVM",
                    findings="CPI=0.9",
                )
            ],
        )
        result = _briefing_update(doc)

        assert result["briefing_data"] == doc.model_dump()
        assert result["supervisor_iterations"] == 0
        assert result["max_supervisor_iterations"] == 3
        assert result["completed_specialists"] == set()
        # Should contain a SystemMessage with briefing markdown
        assert len(result["messages"]) == 1
        assert isinstance(result["messages"][0], SystemMessage)
        assert "Analyze project" in result["messages"][0].content

    def test_returns_no_findings_when_empty_sections(self) -> None:
        """When briefing has no sections, the system message says 'No findings yet.'."""
        doc = BriefingDocument(original_request="Hello")
        result = _briefing_update(doc)

        assert len(result["messages"]) == 1
        msg = result["messages"][0]
        assert isinstance(msg, SystemMessage)
        assert "No findings yet." in msg.content


# ---------------------------------------------------------------------------
# _create_get_briefing_tool
# ---------------------------------------------------------------------------


class TestCreateGetBriefingTool:
    """Tests for the _create_get_briefing_tool factory."""

    def test_returns_briefing_from_valid_state(self) -> None:
        tool = _create_get_briefing_tool()
        briefing_data = _make_briefing_data("Check budget status")
        state = {"briefing_data": briefing_data}
        result = tool.invoke({"state": state})
        assert "Check budget status" in result

    def test_returns_default_when_no_briefing_data(self) -> None:
        tool = _create_get_briefing_tool()
        result = tool.invoke({"state": {}})
        assert result == "No briefing available yet."

    def test_returns_default_when_briefing_data_invalid(self) -> None:
        """Tool should handle invalid briefing_data gracefully."""
        tool = _create_get_briefing_tool()
        result = tool.invoke({"state": {"briefing_data": {"garbage": True}}})
        assert result == "No briefing available yet."


# ---------------------------------------------------------------------------
# _make_supervisor_router
# ---------------------------------------------------------------------------


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
        router = SupervisorOrchestrator._make_supervisor_router(["evm_analyst"])

        state = {"messages": [AIMessage(content="Here is the answer.")]}
        assert router(state) == END

    def test_router_routes_to_end_on_empty_messages(self) -> None:
        router = SupervisorOrchestrator._make_supervisor_router(["evm_analyst"])
        assert router({"messages": []}) == END

    def test_router_routes_to_end_on_non_handoff_tool_call(self) -> None:
        router = SupervisorOrchestrator._make_supervisor_router(["evm_analyst"])

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
        router = SupervisorOrchestrator._make_supervisor_router(["evm_analyst"])

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
        router = SupervisorOrchestrator._make_supervisor_router(["evm_analyst"])

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
        router = SupervisorOrchestrator._make_supervisor_router(["evm_analyst"])

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
        router = SupervisorOrchestrator._make_supervisor_router(["evm_analyst"])

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


class TestSupervisorRouterCompletionLogic:
    """Tests for completion detection and specialist tracking logic."""

    def test_router_prevents_redispatch_to_completed_specialists(self) -> None:
        """Router should END if handoff targets a specialist that already completed."""
        router = SupervisorOrchestrator._make_supervisor_router(
            ["project_manager", "evm_analyst"]
        )

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

        assert router(state) == END

    def test_router_allows_dispatch_to_new_specialist(self) -> None:
        """Router should allow handoff to a specialist that hasn't completed yet."""
        router = SupervisorOrchestrator._make_supervisor_router(
            ["project_manager", "evm_analyst"]
        )

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

        assert router(state) == "evm_analyst"

    def test_uses_lower_max_iterations_default(self) -> None:
        """Router should default to 3 max iterations."""
        router = SupervisorOrchestrator._make_supervisor_router(["project_manager"])

        state: dict = {
            "messages": [],
            "supervisor_iterations": 2,
        }

        assert router(state) == END

        state["supervisor_iterations"] = 3
        assert router(state) == END

        state["supervisor_iterations"] = 4
        assert router(state) == END


# ---------------------------------------------------------------------------
# SupervisorOrchestrator.__init__
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# create_supervisor_graph
# ---------------------------------------------------------------------------


def _patch_build_middleware() -> MagicMock:
    """Return a mock for _build_middleware that returns a generic list.

    Patching is needed because _build_middleware tries to instantiate
    SummarizationMiddleware which requires a real OpenAI API key.
    """
    return patch.object(
        SupervisorOrchestrator,
        "_build_middleware",
        return_value=[MagicMock(name="summ"), MagicMock(name="base_mw")],
    )


class TestSupervisorGraphCreation:
    """Tests for create_supervisor_graph and fallback behavior."""

    @patch("app.ai.supervisor_orchestrator.langchain_create_agent")
    @patch("app.ai.supervisor_orchestrator.filter_tools_for_context")
    @patch("app.ai.supervisor_orchestrator.compile_subagents")
    @pytest.mark.asyncio
    async def test_fallback_graph_built_when_no_specialists(
        self,
        mock_compile: MagicMock,
        mock_filter_tools: MagicMock,
        mock_create_agent: MagicMock,
    ) -> None:
        mock_filter_tools.return_value = []
        mock_compile.return_value = []
        mock_create_agent.return_value = MagicMock()

        context = _make_tool_context()
        orchestrator = SupervisorOrchestrator(
            model="openai:gpt-4o",
            context=context,
        )

        with _patch_build_middleware():
            result = await orchestrator.create_supervisor_graph(AgentConfig())

        assert result is not None
        mock_compile.assert_called_once()
        mock_create_agent.assert_called_once()

    @patch("app.ai.supervisor_orchestrator.langchain_create_agent")
    @patch("app.ai.supervisor_orchestrator.filter_tools_for_context")
    @patch("app.ai.supervisor_orchestrator.compile_subagents")
    @pytest.mark.asyncio
    async def test_graph_uses_custom_system_prompt(
        self,
        mock_compile: MagicMock,
        mock_filter_tools: MagicMock,
        mock_create_agent: MagicMock,
    ) -> None:
        mock_filter_tools.return_value = []
        mock_compile.return_value = []
        mock_create_agent.return_value = MagicMock()

        context = _make_tool_context()
        orchestrator = SupervisorOrchestrator(
            model="openai:gpt-4o",
            context=context,
            system_prompt="Custom supervisor prompt",
        )

        with _patch_build_middleware():
            result = await orchestrator.create_supervisor_graph(AgentConfig())

        assert result is not None
        call_kwargs = mock_create_agent.call_args[1]
        assert "Custom supervisor prompt" in call_kwargs["system_prompt"]

    @patch("app.ai.supervisor_orchestrator.langchain_create_agent")
    @patch("app.ai.supervisor_orchestrator.filter_tools_for_context")
    @patch("app.ai.supervisor_orchestrator.compile_subagents")
    @patch("app.ai.supervisor_orchestrator.create_all_handoff_tools")
    @pytest.mark.asyncio
    async def test_full_graph_compilation_with_specialists(
        self,
        mock_handoff_tools: MagicMock,
        mock_compile: MagicMock,
        mock_filter_tools: MagicMock,
        mock_create_agent: MagicMock,
    ) -> None:
        """Verify graph wiring when specialists are available."""
        mock_filter_tools.return_value = []

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

        with _patch_build_middleware():
            result = await orchestrator.create_supervisor_graph(config)

        assert result is not None
        mock_compile.assert_called_once()

    @patch("app.ai.supervisor_orchestrator.langchain_create_agent")
    @patch("app.ai.supervisor_orchestrator.filter_tools_for_context")
    @patch("app.ai.supervisor_orchestrator.compile_subagents")
    @pytest.mark.asyncio
    async def test_default_config_used_when_none(
        self,
        mock_compile: MagicMock,
        mock_filter_tools: MagicMock,
        mock_create_agent: MagicMock,
    ) -> None:
        mock_filter_tools.return_value = []
        mock_compile.return_value = []
        mock_create_agent.return_value = MagicMock()

        context = _make_tool_context()
        orchestrator = SupervisorOrchestrator(
            model="openai:gpt-4o",
            context=context,
        )

        with _patch_build_middleware():
            result = await orchestrator.create_supervisor_graph()

        assert result is not None
        mock_compile.assert_called_once()

    @patch("app.ai.supervisor_orchestrator.langchain_create_agent")
    @patch("app.ai.supervisor_orchestrator.filter_tools_for_context")
    @patch("app.ai.supervisor_orchestrator.compile_subagents")
    @patch("app.ai.supervisor_orchestrator.create_all_handoff_tools")
    @pytest.mark.asyncio
    async def test_temporal_context_tool_added_when_present(
        self,
        mock_handoff_tools: MagicMock,
        mock_compile: MagicMock,
        mock_filter_tools: MagicMock,
        mock_create_agent: MagicMock,
    ) -> None:
        """When a get_temporal_context tool exists, it is added to supervisor tools."""
        temporal_tool = MagicMock()
        temporal_tool.name = "get_temporal_context"

        other_tool = MagicMock()
        other_tool.name = "list_projects"

        mock_filter_tools.return_value = [other_tool, temporal_tool]
        mock_compile.return_value = [
            {
                "name": "evm_analyst",
                "runnable": AsyncMock(),
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
        config = AgentConfig(
            subagents=[
                {"name": "evm_analyst", "description": "desc", "system_prompt": "sp"}
            ]
        )

        with _patch_build_middleware():
            result = await orchestrator.create_supervisor_graph(config)

        assert result is not None

        # Verify that supervisor agent was created with the temporal tool
        supervisor_call = mock_create_agent.call_args_list[0]
        tools_passed = supervisor_call[1]["tools"]
        tool_names = [t.name for t in tools_passed]
        assert "get_temporal_context" in tool_names

    @patch("app.ai.supervisor_orchestrator.langchain_create_agent")
    @patch("app.ai.supervisor_orchestrator.filter_tools_for_context")
    @patch("app.ai.supervisor_orchestrator.compile_subagents")
    @patch("app.ai.supervisor_orchestrator.create_all_handoff_tools")
    @pytest.mark.asyncio
    async def test_no_temporal_context_tool_when_absent(
        self,
        mock_handoff_tools: MagicMock,
        mock_compile: MagicMock,
        mock_filter_tools: MagicMock,
        mock_create_agent: MagicMock,
    ) -> None:
        """When no get_temporal_context tool exists, it is not added."""
        other_tool = MagicMock()
        other_tool.name = "list_projects"

        mock_filter_tools.return_value = [other_tool]
        mock_compile.return_value = [
            {
                "name": "evm_analyst",
                "runnable": AsyncMock(),
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
        config = AgentConfig(
            subagents=[
                {"name": "evm_analyst", "description": "desc", "system_prompt": "sp"}
            ]
        )

        with _patch_build_middleware():
            await orchestrator.create_supervisor_graph(config)

        supervisor_call = mock_create_agent.call_args_list[0]
        tools_passed = supervisor_call[1]["tools"]
        tool_names = [t.name for t in tools_passed]
        assert "get_temporal_context" not in tool_names

    @patch("app.ai.supervisor_orchestrator.langchain_create_agent")
    @patch("app.ai.supervisor_orchestrator.filter_tools_for_context")
    @patch("app.ai.supervisor_orchestrator.compile_subagents")
    @patch("app.ai.supervisor_orchestrator.create_all_handoff_tools")
    @pytest.mark.asyncio
    async def test_graph_wired_with_multiple_specialists(
        self,
        mock_handoff_tools: MagicMock,
        mock_compile: MagicMock,
        mock_filter_tools: MagicMock,
        mock_create_agent: MagicMock,
    ) -> None:
        """Verify graph handles multiple specialists correctly."""
        mock_filter_tools.return_value = []
        mock_compile.return_value = [
            {
                "name": "evm_analyst",
                "runnable": AsyncMock(),
                "tools": [],
            },
            {
                "name": "project_manager",
                "runnable": AsyncMock(),
                "tools": [],
            },
        ]
        mock_handoff_tools.return_value = []
        mock_create_agent.return_value = AsyncMock()

        context = _make_tool_context()
        orchestrator = SupervisorOrchestrator(
            model="openai:gpt-4o",
            context=context,
        )
        config = AgentConfig(
            subagents=[
                {"name": "evm_analyst", "description": "desc", "system_prompt": "sp"},
                {
                    "name": "project_manager",
                    "description": "desc",
                    "system_prompt": "sp",
                },
            ]
        )

        with _patch_build_middleware():
            result = await orchestrator.create_supervisor_graph(config)

        assert result is not None
        mock_handoff_tools.assert_called_once()


# ---------------------------------------------------------------------------
# initialize_briefing_node (inner function in create_supervisor_graph)
# ---------------------------------------------------------------------------


class TestInitializeBriefingNode:
    """Tests for the initialize_briefing_node closure inside create_supervisor_graph.

    The node is created as a closure inside create_supervisor_graph. To test it,
    we mock all external calls and intercept add_node to capture the closure.
    """

    @patch("app.ai.supervisor_orchestrator.langchain_create_agent")
    @patch("app.ai.supervisor_orchestrator.filter_tools_for_context")
    @patch("app.ai.supervisor_orchestrator.compile_subagents")
    @patch("app.ai.supervisor_orchestrator.create_all_handoff_tools")
    @patch("app.ai.supervisor_orchestrator.initialize_briefing")
    @pytest.mark.asyncio
    async def test_creates_new_briefing_on_first_message(
        self,
        mock_init_briefing: MagicMock,
        mock_handoff: MagicMock,
        mock_compile: MagicMock,
        mock_filter: MagicMock,
        mock_create_agent: MagicMock,
    ) -> None:
        """When no existing briefing_data, creates a new briefing."""
        mock_filter.return_value = []
        mock_compile.return_value = [
            {"name": "evm_analyst", "runnable": AsyncMock(), "tools": []}
        ]
        mock_handoff.return_value = []
        mock_create_agent.return_value = AsyncMock()

        new_briefing = BriefingDocument(
            original_request="What is the CPI?"
        ).model_dump()
        mock_init_briefing.return_value = new_briefing

        context = _make_tool_context()
        orchestrator = SupervisorOrchestrator(
            model="openai:gpt-4o",
            context=context,
        )
        config = AgentConfig(
            subagents=[
                {"name": "evm_analyst", "description": "d", "system_prompt": "s"}
            ]
        )

        added_nodes: dict[str, object] = {}

        with (
            _patch_build_middleware(),
            patch("app.ai.supervisor_orchestrator.StateGraph") as MockGraph,
        ):
            mock_parent = MagicMock()
            mock_parent.add_node.side_effect = lambda name, fn: added_nodes.update(
                {name: fn}
            )
            mock_parent.compile.return_value = MagicMock()
            MockGraph.return_value = mock_parent

            await orchestrator.create_supervisor_graph(config)

        assert "initialize_briefing" in added_nodes
        init_fn = added_nodes["initialize_briefing"]

        state = {
            "messages": [HumanMessage(content="What is the CPI?")],
        }
        result = await init_fn(state)

        mock_init_briefing.assert_called_once_with("What is the CPI?")
        assert result["supervisor_iterations"] == 0
        assert result["max_supervisor_iterations"] == 3
        assert result["completed_specialists"] == set()
        assert len(result["messages"]) == 1

    @patch("app.ai.supervisor_orchestrator.langchain_create_agent")
    @patch("app.ai.supervisor_orchestrator.filter_tools_for_context")
    @patch("app.ai.supervisor_orchestrator.compile_subagents")
    @patch("app.ai.supervisor_orchestrator.create_all_handoff_tools")
    @patch("app.ai.supervisor_orchestrator.initialize_briefing")
    @pytest.mark.asyncio
    async def test_reuses_existing_briefing_from_state(
        self,
        mock_init_briefing: MagicMock,
        mock_handoff: MagicMock,
        mock_compile: MagicMock,
        mock_filter: MagicMock,
        mock_create_agent: MagicMock,
    ) -> None:
        """When briefing_data exists in state and is valid, it is reused."""
        mock_filter.return_value = []
        mock_compile.return_value = [
            {"name": "evm_analyst", "runnable": AsyncMock(), "tools": []}
        ]
        mock_handoff.return_value = []
        mock_create_agent.return_value = AsyncMock()

        context = _make_tool_context()
        orchestrator = SupervisorOrchestrator(
            model="openai:gpt-4o",
            context=context,
        )
        config = AgentConfig(
            subagents=[
                {"name": "evm_analyst", "description": "d", "system_prompt": "s"}
            ]
        )

        added_nodes: dict[str, object] = {}

        with (
            _patch_build_middleware(),
            patch("app.ai.supervisor_orchestrator.StateGraph") as MockGraph,
        ):
            mock_parent = MagicMock()
            mock_parent.add_node.side_effect = lambda name, fn: added_nodes.update(
                {name: fn}
            )
            mock_parent.compile.return_value = MagicMock()
            MockGraph.return_value = mock_parent

            await orchestrator.create_supervisor_graph(config)

        init_fn = added_nodes["initialize_briefing"]

        existing_briefing = _make_briefing_data(
            original_request="Old request",
            sections=[
                BriefingSection(
                    specialist_name="evm_analyst",
                    task_description="EVM",
                    findings="CPI=0.9",
                )
            ],
        )

        state = {
            "messages": [HumanMessage(content="New follow-up question")],
            "briefing_data": existing_briefing,
        }
        result = await init_fn(state)

        # Should NOT have called initialize_briefing (reuse path)
        mock_init_briefing.assert_not_called()
        assert result["supervisor_iterations"] == 0
        doc = BriefingDocument.model_validate(result["briefing_data"])
        assert doc.original_request == "New follow-up question"

    @patch("app.ai.supervisor_orchestrator.langchain_create_agent")
    @patch("app.ai.supervisor_orchestrator.filter_tools_for_context")
    @patch("app.ai.supervisor_orchestrator.compile_subagents")
    @patch("app.ai.supervisor_orchestrator.create_all_handoff_tools")
    @patch("app.ai.supervisor_orchestrator.initialize_briefing")
    @pytest.mark.asyncio
    async def test_recovers_when_existing_briefing_invalid(
        self,
        mock_init_briefing: MagicMock,
        mock_handoff: MagicMock,
        mock_compile: MagicMock,
        mock_filter: MagicMock,
        mock_create_agent: MagicMock,
    ) -> None:
        """When existing briefing_data is invalid, creates a new briefing."""
        mock_filter.return_value = []
        mock_compile.return_value = [
            {"name": "evm_analyst", "runnable": AsyncMock(), "tools": []}
        ]
        mock_handoff.return_value = []
        mock_create_agent.return_value = AsyncMock()

        new_briefing = BriefingDocument(
            original_request="Recovered request"
        ).model_dump()
        mock_init_briefing.return_value = new_briefing

        context = _make_tool_context()
        orchestrator = SupervisorOrchestrator(
            model="openai:gpt-4o",
            context=context,
        )
        config = AgentConfig(
            subagents=[
                {"name": "evm_analyst", "description": "d", "system_prompt": "s"}
            ]
        )

        added_nodes: dict[str, object] = {}

        with (
            _patch_build_middleware(),
            patch("app.ai.supervisor_orchestrator.StateGraph") as MockGraph,
        ):
            mock_parent = MagicMock()
            mock_parent.add_node.side_effect = lambda name, fn: added_nodes.update(
                {name: fn}
            )
            mock_parent.compile.return_value = MagicMock()
            MockGraph.return_value = mock_parent

            await orchestrator.create_supervisor_graph(config)

        init_fn = added_nodes["initialize_briefing"]

        state = {
            "messages": [HumanMessage(content="Recovered request")],
            "briefing_data": {"invalid": "data", "missing_fields": True},
        }
        result = await init_fn(state)

        mock_init_briefing.assert_called_once_with("Recovered request")
        assert result["supervisor_iterations"] == 0

    @patch("app.ai.supervisor_orchestrator.langchain_create_agent")
    @patch("app.ai.supervisor_orchestrator.filter_tools_for_context")
    @patch("app.ai.supervisor_orchestrator.compile_subagents")
    @patch("app.ai.supervisor_orchestrator.create_all_handoff_tools")
    @patch("app.ai.supervisor_orchestrator.initialize_briefing")
    @pytest.mark.asyncio
    async def test_handles_non_string_message_content(
        self,
        mock_init_briefing: MagicMock,
        mock_handoff: MagicMock,
        mock_compile: MagicMock,
        mock_filter: MagicMock,
        mock_create_agent: MagicMock,
    ) -> None:
        """When HumanMessage has non-string content, it is str()'d."""
        mock_filter.return_value = []
        mock_compile.return_value = [
            {"name": "evm_analyst", "runnable": AsyncMock(), "tools": []}
        ]
        mock_handoff.return_value = []
        mock_create_agent.return_value = AsyncMock()

        new_briefing = BriefingDocument(original_request="str_content").model_dump()
        mock_init_briefing.return_value = new_briefing

        context = _make_tool_context()
        orchestrator = SupervisorOrchestrator(
            model="openai:gpt-4o",
            context=context,
        )
        config = AgentConfig(
            subagents=[
                {"name": "evm_analyst", "description": "d", "system_prompt": "s"}
            ]
        )

        added_nodes: dict[str, object] = {}

        with (
            _patch_build_middleware(),
            patch("app.ai.supervisor_orchestrator.StateGraph") as MockGraph,
        ):
            mock_parent = MagicMock()
            mock_parent.add_node.side_effect = lambda name, fn: added_nodes.update(
                {name: fn}
            )
            mock_parent.compile.return_value = MagicMock()
            MockGraph.return_value = mock_parent

            await orchestrator.create_supervisor_graph(config)

        init_fn = added_nodes["initialize_briefing"]

        # HumanMessage with list content (multimodal)
        state = {
            "messages": [HumanMessage(content=[{"type": "text", "text": "hello"}])],
        }
        await init_fn(state)

        mock_init_briefing.assert_called_once()


# ---------------------------------------------------------------------------
# _create_specialist_wrapper
# ---------------------------------------------------------------------------


class TestSpecialistWrapper:
    """Tests for _create_specialist_wrapper and the returned specialist_node."""

    @pytest.mark.asyncio
    async def test_early_exit_when_specialist_already_completed(self) -> None:
        """Specialist node returns Command(goto=END) when already in completed set."""
        orchestrator = SupervisorOrchestrator(
            model="openai:gpt-4o",
            context=_make_tool_context(),
        )
        mock_graph = AsyncMock()
        wrapper = orchestrator._create_specialist_wrapper(
            specialist_name="evm_analyst",
            specialist_graph=mock_graph,
        )

        state = {
            "messages": [],
            "completed_specialists": {"evm_analyst"},
            "supervisor_iterations": 1,
        }
        result = await wrapper(state)

        assert result.goto == END
        assert result.update["active_agent"] == "supervisor"
        assert result.update["supervisor_iterations"] == 2
        mock_graph.ainvoke.assert_not_called()

    @pytest.mark.asyncio
    async def test_successful_specialist_invocation(self) -> None:
        """Normal specialist run: invokes graph, extracts findings, returns Command."""
        orchestrator = SupervisorOrchestrator(
            model="openai:gpt-4o",
            context=_make_tool_context(),
        )
        mock_graph = AsyncMock()
        mock_graph.ainvoke.return_value = {
            "messages": [AIMessage(content="CPI is 0.9, project is under budget.")],
            "tool_call_count": 3,
        }

        wrapper = orchestrator._create_specialist_wrapper(
            specialist_name="evm_analyst",
            specialist_graph=mock_graph,
        )

        briefing_data = _make_briefing_data("Analyze CPI")
        state = {
            "messages": [],
            "completed_specialists": set(),
            "supervisor_iterations": 0,
            "briefing_data": briefing_data,
            "max_tool_iterations": 25,
        }
        result = await wrapper(state)

        assert result.goto == "supervisor"
        assert result.update["active_agent"] == "supervisor"
        assert result.update["supervisor_iterations"] == 1
        assert result.update["completed_specialists"] == {"evm_analyst"}
        assert "briefing_data" in result.update
        mock_graph.ainvoke.assert_called_once()

    @pytest.mark.asyncio
    async def test_specialist_error_does_not_mark_completed(self) -> None:
        """When specialist raises, it is NOT marked completed (allows retry)."""
        orchestrator = SupervisorOrchestrator(
            model="openai:gpt-4o",
            context=_make_tool_context(),
        )
        mock_graph = AsyncMock()
        mock_graph.ainvoke.side_effect = RuntimeError("API timeout")

        wrapper = orchestrator._create_specialist_wrapper(
            specialist_name="evm_analyst",
            specialist_graph=mock_graph,
        )

        state = {
            "messages": [],
            "completed_specialists": set(),
            "supervisor_iterations": 0,
            "briefing_data": _make_briefing_data("Analyze"),
            "max_tool_iterations": 25,
        }
        result = await wrapper(state)

        assert result.goto == "supervisor"
        assert result.update["active_agent"] == "supervisor"
        assert result.update["supervisor_iterations"] == 1
        # completed_specialists not set on error
        assert "evm_analyst" not in result.update.get("completed_specialists", set())

    @pytest.mark.asyncio
    async def test_specialist_with_task_history_uses_latest_task(self) -> None:
        """When briefing has task_history, the latest task description is used."""
        orchestrator = SupervisorOrchestrator(
            model="openai:gpt-4o",
            context=_make_tool_context(),
        )
        mock_graph = AsyncMock()
        mock_graph.ainvoke.return_value = {
            "messages": [AIMessage(content="Analysis complete.")],
            "tool_call_count": 1,
        }

        wrapper = orchestrator._create_specialist_wrapper(
            specialist_name="evm_analyst",
            specialist_graph=mock_graph,
        )

        briefing_data = _make_briefing_data("Analyze project")
        doc = BriefingDocument.model_validate(briefing_data)
        doc.add_task_assignment(
            TaskAssignment(
                specialist="evm_analyst",
                description="Calculate CPI for project X",
                rationale="User asked about cost performance",
            )
        )

        state = {
            "messages": [],
            "completed_specialists": set(),
            "supervisor_iterations": 0,
            "briefing_data": doc.model_dump(),
            "max_tool_iterations": 25,
        }
        await wrapper(state)

        call_args = mock_graph.ainvoke.call_args
        messages_arg = call_args[0][0]["messages"]
        msg_content = messages_arg[0].content
        assert "Calculate CPI for project X" in msg_content
        assert "User asked about cost performance" in msg_content

    @pytest.mark.asyncio
    async def test_specialist_with_no_briefing_data(self) -> None:
        """When no briefing data exists, specialist still runs with defaults."""
        orchestrator = SupervisorOrchestrator(
            model="openai:gpt-4o",
            context=_make_tool_context(),
        )
        mock_graph = AsyncMock()
        mock_graph.ainvoke.return_value = {
            "messages": [AIMessage(content="Done.")],
            "tool_call_count": 0,
        }

        wrapper = orchestrator._create_specialist_wrapper(
            specialist_name="evm_analyst",
            specialist_graph=mock_graph,
        )

        state = {
            "messages": [],
            "completed_specialists": set(),
            "supervisor_iterations": 0,
            "briefing_data": {},
            "max_tool_iterations": 25,
        }
        result = await wrapper(state)

        assert result.goto == "supervisor"
        call_args = mock_graph.ainvoke.call_args
        messages_arg = call_args[0][0]["messages"]
        assert "Execute specialist task from briefing" in messages_arg[0].content

    @pytest.mark.asyncio
    async def test_specialist_with_invalid_briefing_data_uses_defaults(self) -> None:
        """When briefing_data cannot be validated, specialist uses default task."""
        orchestrator = SupervisorOrchestrator(
            model="openai:gpt-4o",
            context=_make_tool_context(),
        )
        mock_graph = AsyncMock()
        mock_graph.ainvoke.return_value = {
            "messages": [AIMessage(content="Done.")],
            "tool_call_count": 0,
        }

        wrapper = orchestrator._create_specialist_wrapper(
            specialist_name="evm_analyst",
            specialist_graph=mock_graph,
        )

        state = {
            "messages": [],
            "completed_specialists": set(),
            "supervisor_iterations": 0,
            "briefing_data": {"garbage": True, "not_valid": 123},
            "max_tool_iterations": 25,
        }
        result = await wrapper(state)

        assert result.goto == "supervisor"
        # Should have used default task description since briefing was invalid
        call_args = mock_graph.ainvoke.call_args
        messages_arg = call_args[0][0]["messages"]
        assert "Execute specialist task from briefing" in messages_arg[0].content

    @pytest.mark.asyncio
    async def test_specialist_invoked_with_correct_recursion_limit(self) -> None:
        """Specialist graph is invoked with recursion_limit from state."""
        orchestrator = SupervisorOrchestrator(
            model="openai:gpt-4o",
            context=_make_tool_context(),
        )
        mock_graph = AsyncMock()
        mock_graph.ainvoke.return_value = {
            "messages": [AIMessage(content="Done.")],
            "tool_call_count": 2,
        }

        wrapper = orchestrator._create_specialist_wrapper(
            specialist_name="evm_analyst",
            specialist_graph=mock_graph,
        )

        state = {
            "messages": [],
            "completed_specialists": set(),
            "supervisor_iterations": 0,
            "briefing_data": {},
            "max_tool_iterations": 15,
        }
        await wrapper(state)

        call_args = mock_graph.ainvoke.call_args
        assert call_args[1]["config"]["recursion_limit"] == 15

    @pytest.mark.asyncio
    async def test_transient_error_retries_and_succeeds(self) -> None:
        """Transient errors are retried; specialist succeeds on 3rd attempt."""
        orchestrator = SupervisorOrchestrator(
            model="openai:gpt-4o",
            context=_make_tool_context(),
        )
        mock_graph = AsyncMock()
        transient_err = ConnectionResetError("peer closed connection")
        mock_graph.ainvoke.side_effect = [
            transient_err,
            transient_err,
            {"messages": [AIMessage(content="Recovered.")], "tool_call_count": 1},
        ]

        wrapper = orchestrator._create_specialist_wrapper(
            specialist_name="evm_analyst",
            specialist_graph=mock_graph,
        )

        with patch("app.ai.supervisor_orchestrator.settings") as mock_settings:
            mock_settings.AI_SPECIALIST_MAX_RETRIES = 3
            result = await wrapper(
                {
                    "messages": [],
                    "completed_specialists": set(),
                    "supervisor_iterations": 0,
                    "briefing_data": _make_briefing_data("Test"),
                    "max_tool_iterations": 25,
                }
            )

        assert result.goto == "supervisor"
        assert result.update["completed_specialists"] == {"evm_analyst"}
        assert mock_graph.ainvoke.call_count == 3

    @pytest.mark.asyncio
    async def test_non_transient_error_no_retry(self) -> None:
        """Non-transient errors are NOT retried; returns error immediately."""
        orchestrator = SupervisorOrchestrator(
            model="openai:gpt-4o",
            context=_make_tool_context(),
        )
        mock_graph = AsyncMock()
        mock_graph.ainvoke.side_effect = ValueError("bad input")

        wrapper = orchestrator._create_specialist_wrapper(
            specialist_name="evm_analyst",
            specialist_graph=mock_graph,
        )

        with patch("app.ai.supervisor_orchestrator.settings") as mock_settings:
            mock_settings.AI_SPECIALIST_MAX_RETRIES = 3
            result = await wrapper(
                {
                    "messages": [],
                    "completed_specialists": set(),
                    "supervisor_iterations": 0,
                    "briefing_data": _make_briefing_data("Test"),
                    "max_tool_iterations": 25,
                }
            )

        assert result.goto == "supervisor"
        assert "evm_analyst" not in result.update.get("completed_specialists", set())
        assert mock_graph.ainvoke.call_count == 1

    @pytest.mark.asyncio
    async def test_transient_error_exhausts_retries(self) -> None:
        """All retries exhausted returns error Command after max_retries + 1 attempts."""
        orchestrator = SupervisorOrchestrator(
            model="openai:gpt-4o",
            context=_make_tool_context(),
        )
        mock_graph = AsyncMock()
        mock_graph.ainvoke.side_effect = ConnectionResetError("peer closed")

        wrapper = orchestrator._create_specialist_wrapper(
            specialist_name="evm_analyst",
            specialist_graph=mock_graph,
        )

        with patch("app.ai.supervisor_orchestrator.settings") as mock_settings:
            mock_settings.AI_SPECIALIST_MAX_RETRIES = 3
            result = await wrapper(
                {
                    "messages": [],
                    "completed_specialists": set(),
                    "supervisor_iterations": 0,
                    "briefing_data": _make_briefing_data("Test"),
                    "max_tool_iterations": 25,
                }
            )

        assert result.goto == "supervisor"
        assert "evm_analyst" not in result.update.get("completed_specialists", set())
        assert mock_graph.ainvoke.call_count == 4  # 3 retries + 1 initial


# ---------------------------------------------------------------------------
# _build_middleware
# ---------------------------------------------------------------------------


class TestBuildMiddleware:
    """Tests for _build_middleware method."""

    def test_returns_list_with_summarization_and_base(self) -> None:
        """Middleware stack includes SummarizationMiddleware + base Backcast middleware."""
        orchestrator = SupervisorOrchestrator(
            model="openai:gpt-4o",
            context=_make_tool_context(),
        )

        mock_base_mw = MagicMock(name="temporal")
        mock_summ = MagicMock(name="summarization")

        with (
            patch(
                "app.ai.supervisor_orchestrator.build_backcast_middleware"
            ) as mock_build,
            patch.dict(
                "sys.modules",
                {
                    "langchain.agents.middleware.summarization": MagicMock(
                        SummarizationMiddleware=MagicMock(return_value=mock_summ)
                    )
                },
            ),
        ):
            mock_build.return_value = [mock_base_mw]
            result = orchestrator._build_middleware([])

        mock_build.assert_called_once()
        assert isinstance(result, list)
        assert len(result) == 2  # summ + base
        assert result[0] is mock_summ
        assert result[1] is mock_base_mw


# ---------------------------------------------------------------------------
# _build_fallback_graph
# ---------------------------------------------------------------------------


class TestBuildFallbackGraph:
    """Tests for _build_fallback_graph method."""

    @patch("app.ai.supervisor_orchestrator.langchain_create_agent")
    @patch("app.ai.supervisor_orchestrator.filter_tools_for_context")
    @pytest.mark.asyncio
    async def test_fallback_uses_default_prompt_when_none(
        self,
        mock_filter: MagicMock,
        mock_create_agent: MagicMock,
    ) -> None:
        mock_filter.return_value = []
        mock_create_agent.return_value = MagicMock()

        context = _make_tool_context()
        orchestrator = SupervisorOrchestrator(
            model="openai:gpt-4o",
            context=context,
        )
        config = AgentConfig()

        with (
            patch("app.ai.supervisor_orchestrator.compile_subagents", return_value=[]),
            _patch_build_middleware(),
        ):
            await orchestrator.create_supervisor_graph(config)

        mock_create_agent.assert_called_once()
        call_kwargs = mock_create_agent.call_args[1]
        assert "Briefing Room" in call_kwargs["system_prompt"]

    @patch("app.ai.supervisor_orchestrator.langchain_create_agent")
    @patch("app.ai.supervisor_orchestrator.filter_tools_for_context")
    @pytest.mark.asyncio
    async def test_fallback_uses_custom_prompt(
        self,
        mock_filter: MagicMock,
        mock_create_agent: MagicMock,
    ) -> None:
        mock_filter.return_value = []
        mock_create_agent.return_value = MagicMock()

        context = _make_tool_context()
        orchestrator = SupervisorOrchestrator(
            model="openai:gpt-4o",
            context=context,
            system_prompt="My custom fallback prompt",
        )
        config = AgentConfig()

        with (
            patch("app.ai.supervisor_orchestrator.compile_subagents", return_value=[]),
            _patch_build_middleware(),
        ):
            await orchestrator.create_supervisor_graph(config)

        call_kwargs = mock_create_agent.call_args[1]
        assert "My custom fallback prompt" in call_kwargs["system_prompt"]

    @patch("app.ai.supervisor_orchestrator.langchain_create_agent")
    @patch("app.ai.supervisor_orchestrator.filter_tools_for_context")
    @pytest.mark.asyncio
    async def test_fallback_passes_all_tools_directly(
        self,
        mock_filter: MagicMock,
        mock_create_agent: MagicMock,
    ) -> None:
        """Fallback graph gets all filtered tools, not just handoff tools."""
        tool_a = MagicMock()
        tool_a.name = "tool_a"
        tool_b = MagicMock()
        tool_b.name = "tool_b"

        mock_filter.return_value = [tool_a, tool_b]
        mock_create_agent.return_value = MagicMock()

        context = _make_tool_context()
        orchestrator = SupervisorOrchestrator(
            model="openai:gpt-4o",
            context=context,
        )
        config = AgentConfig()

        with (
            patch("app.ai.supervisor_orchestrator.compile_subagents", return_value=[]),
            _patch_build_middleware(),
        ):
            await orchestrator.create_supervisor_graph(config)

        call_kwargs = mock_create_agent.call_args[1]
        assert call_kwargs["tools"] == [tool_a, tool_b]
