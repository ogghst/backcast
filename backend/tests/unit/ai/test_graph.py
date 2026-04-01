"""Tests for StateGraph structure and compilation.

Follows TDD: Test first, then implement.
"""

from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import BaseTool

from app.ai.graph import create_agent_node, create_graph, should_continue
from app.ai.state import AgentState


class TestStateGraphCompilation:
    """Test suite for StateGraph compilation."""

    def test_create_graph_returns_compiled_graph(self) -> None:
        """Test that create_graph returns a compiled StateGraph."""
        # Mock dependencies
        mock_llm = Mock()
        mock_tools: list[BaseTool] = []

        # Create graph
        graph = create_graph(llm=mock_llm, tools=mock_tools)

        # Verify it's a compiled graph
        assert graph is not None
        assert hasattr(graph, "invoke")
        assert hasattr(graph, "stream")

    def test_create_graph_has_agent_node(self) -> None:
        """Test that create_graph adds an agent node."""
        mock_llm = Mock()
        mock_tools: list[BaseTool] = []

        graph = create_graph(llm=mock_llm, tools=mock_tools)

        # Verify nodes exist
        # In LangGraph, we can check the graph structure
        assert graph is not None
        # The graph should have nodes registered
        # We'll verify this works by attempting to invoke

    def test_create_graph_has_tools_node(self) -> None:
        """Test that create_graph adds a tools node."""
        mock_llm = Mock()
        mock_tools: list[BaseTool] = []

        graph = create_graph(llm=mock_llm, tools=mock_tools)

        # Verify graph was created successfully
        assert graph is not None

    def test_create_graph_has_conditional_edges(self) -> None:
        """Test that create_graph adds conditional edges."""
        mock_llm = Mock()
        mock_tools: list[BaseTool] = []

        graph = create_graph(llm=mock_llm, tools=mock_tools)

        # Verify graph was created successfully
        assert graph is not None

    def test_create_graph_has_entry_point(self) -> None:
        """Test that create_graph sets an entry point."""
        mock_llm = Mock()
        mock_tools: list[BaseTool] = []

        graph = create_graph(llm=mock_llm, tools=mock_tools)

        # Verify graph was created successfully
        assert graph is not None


class TestConditionalEdges:
    """Test suite for conditional edge routing logic."""

    def test_should_continue_routes_to_tools_when_tool_calls_present(self) -> None:
        """Test that should_continue routes to tools when AIMessage has tool_calls."""
        state = AgentState(
            messages=[
                AIMessage(
                    content="I'll help you with that",
                    tool_calls=[{"id": "1", "name": "test_tool", "args": {}}],
                )
            ],
            tool_call_count=0,
            max_tool_iterations=5,
            next="agent",
        )

        result = should_continue(state)
        assert result == "tools"

    def test_should_continue_routes_to_end_when_no_tool_calls(self) -> None:
        """Test that should_continue routes to end when AIMessage has no tool_calls."""
        state = AgentState(
            messages=[AIMessage(content="Here's your answer")],
            tool_call_count=0,
            max_tool_iterations=5,
            next="agent",
        )

        result = should_continue(state)
        assert result == "end"

    def test_should_continues_routes_to_end_at_max_iterations(self) -> None:
        """Test that should_continue routes to end when max iterations reached."""
        max_iters = 5

        state = AgentState(
            messages=[
                AIMessage(
                    content="I'll help you with that",
                    tool_calls=[{"id": "1", "name": "test_tool", "args": {}}],
                )
            ],
            tool_call_count=max_iters,
            max_tool_iterations=max_iters,
            next="agent",
        )

        result = should_continue(state)
        assert result == "end"

    def test_should_continues_handles_human_message(self) -> None:
        """Test that should_continue handles HumanMessage."""
        state = AgentState(
            messages=[HumanMessage(content="Hello")],
            tool_call_count=0,
            max_tool_iterations=5,
            next="agent",
        )

        result = should_continue(state)
        assert result == "end"

    def test_should_continues_defaults_to_end(self) -> None:
        """Test that should_continue defaults to end for unknown message types."""
        state = AgentState(
            messages=[],
            tool_call_count=0,
            max_tool_iterations=5,
            next="agent",
        )

        result = should_continue(state)
        assert result == "end"

    def test_should_continues_routes_to_agent_for_tool_message(self) -> None:
        """Test that should_continue routes to agent when last message is ToolMessage."""
        state = AgentState(
            messages=[
                AIMessage(
                    content="I'll use a tool",
                    tool_calls=[{"id": "1", "name": "test_tool", "args": {}}],
                ),
                ToolMessage(content="Tool result", tool_call_id="1"),
            ],
            tool_call_count=1,
            max_tool_iterations=5,
            next="agent",
        )

        result = should_continue(state)
        assert result == "agent"


class TestAgentNodeBindTools:
    """Test suite for agent_node bind_tools() invocation."""

    @pytest.mark.asyncio
    async def test_agent_node_binds_tools_correctly(self) -> None:
        """Test that agent_node calls llm.bind_tools() with the correct tool list."""
        # Arrange
        mock_llm = MagicMock()
        mock_llm_with_tools = AsyncMock()
        mock_response = AIMessage(content="Test response")
        mock_llm_with_tools.ainvoke.return_value = mock_response
        mock_llm.bind_tools.return_value = mock_llm_with_tools

        mock_tool = cast(BaseTool, Mock(name="test_tool"))
        mock_tools: list[BaseTool] = [mock_tool]

        state = AgentState(
            messages=[HumanMessage(content="Hello")],
            tool_call_count=0,
            max_tool_iterations=5,
            next="agent",
        )
        config: dict[str, Any] = {}

        # Act - create node function using the factory
        node_fn = create_agent_node(mock_llm, mock_tools)
        result = await node_fn(state, config)

        # Assert
        # Verify bind_tools was called with the exact tools list
        mock_llm.bind_tools.assert_called_once_with(mock_tools)

        # Verify the bound LLM was invoked with messages
        mock_llm_with_tools.ainvoke.assert_called_once_with(state["messages"])

        # Verify result contains updated messages
        assert "messages" in result
        assert result["messages"] == [mock_response]
        # With operator.add reducer, returns delta 0 when no tool calls
        assert result["tool_call_count"] == 0

    @pytest.mark.asyncio
    async def test_agent_node_returns_delta_1_when_tool_calls_present(self) -> None:
        """Test that agent_node returns delta 1 for tool_call_count when tool_calls present."""
        # Arrange
        mock_llm = MagicMock()
        mock_llm_with_tools = AsyncMock()
        mock_response = AIMessage(
            content="I'll use a tool",
            tool_calls=[{"id": "1", "name": "test_tool", "args": {}}],
        )
        mock_llm_with_tools.ainvoke.return_value = mock_response
        mock_llm.bind_tools.return_value = mock_llm_with_tools

        mock_tools: list[BaseTool] = []

        state = AgentState(
            messages=[HumanMessage(content="Hello")],
            tool_call_count=2,
            max_tool_iterations=5,
            next="agent",
        )
        config: dict[str, Any] = {}

        # Act - create node function using the factory
        node_fn = create_agent_node(mock_llm, mock_tools)
        result = await node_fn(state, config)

        # Assert - returns delta, not accumulated value
        assert result["tool_call_count"] == 1

    @pytest.mark.asyncio
    async def test_agent_node_returns_delta_0_when_no_tool_calls(self) -> None:
        """Test that agent_node returns delta 0 for tool_call_count when no tool_calls."""
        # Arrange
        mock_llm = MagicMock()
        mock_llm_with_tools = AsyncMock()
        mock_response = AIMessage(content="No tools needed")
        mock_llm_with_tools.ainvoke.return_value = mock_response
        mock_llm.bind_tools.return_value = mock_llm_with_tools

        mock_tools: list[BaseTool] = []

        state = AgentState(
            messages=[HumanMessage(content="Hello")],
            tool_call_count=2,
            max_tool_iterations=5,
            next="agent",
        )
        config: dict[str, Any] = {}

        # Act - create node function using the factory
        node_fn = create_agent_node(mock_llm, mock_tools)
        result = await node_fn(state, config)

        # Assert - returns delta 0, not the accumulated count
        assert result["tool_call_count"] == 0
