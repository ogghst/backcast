"""Integration tests for StateGraph execution.

Tests end-to-end graph execution including ToolNode from langgraph.prebuilt.
Follows TDD: Test first, then implement.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool

from app.ai.graph import create_graph


@tool
def simple_tool(value: str) -> str:
    """A simple test tool that echoes the input.

    Args:
        value: Input value to echo

    Returns:
        The input value with a prefix
    """
    return f"Echo: {value}"


@tool
def simple_tool_2(number: int) -> str:
    """A second simple test tool that doubles the input.

    Args:
        number: Input number to double

    Returns:
        The doubled number as a string
    """
    return f"Doubled: {number * 2}"


class TestStateGraphCompilation:
    """Test suite for StateGraph compilation and execution."""

    @pytest.mark.asyncio
    async def test_stategraph_compilation_and_execution(self) -> None:
        """Test that StateGraph compiles and can be invoked."""
        # Arrange
        mock_llm = MagicMock()
        mock_llm_with_tools = AsyncMock()
        mock_llm.bind_tools.return_value = mock_llm_with_tools

        # Mock LLM response without tool calls - use ainvoke for async
        mock_response = AIMessage(content="Hello! How can I help you?")
        mock_llm_with_tools.ainvoke.return_value = mock_response

        tools = [simple_tool]

        # Act
        graph = create_graph(llm=mock_llm, tools=tools)

        # Assert
        assert graph is not None
        assert hasattr(graph, "ainvoke")
        assert hasattr(graph, "astream")

        # Test invocation - use ainvoke for async nodes
        result = await graph.ainvoke(
            {
                "messages": [HumanMessage(content="Hello")],
                "tool_call_count": 0,
                "max_tool_iterations": 25,
                "next": "agent",
            },
            config={"configurable": {"thread_id": "test-thread-1"}},
        )

        # Verify result
        assert "messages" in result
        assert len(result["messages"]) >= 1
        # Last message should be the AI response
        assert isinstance(result["messages"][-1], AIMessage)
        assert result["messages"][-1].content == "Hello! How can I help you?"


class TestToolNodeExecution:
    """Test suite for ToolNode execution from langgraph.prebuilt."""

    @pytest.mark.asyncio
    async def test_tool_node_execution(self) -> None:
        """Test that ToolNode from langgraph.prebuilt executes tool calls."""
        # Arrange
        mock_llm = MagicMock()
        mock_llm_with_tools = AsyncMock()

        # Create tools
        tools = [simple_tool, simple_tool_2]

        # Mock LLM response WITH tool calls
        mock_response = AIMessage(
            content="I'll use the tools",
            tool_calls=[
                {
                    "id": "call_1",
                    "name": "simple_tool",
                    "args": {"value": "test"},
                },
                {
                    "id": "call_2",
                    "name": "simple_tool_2",
                    "args": {"number": 5},
                },
            ],
        )

        # First call returns tool calls, second call returns final response
        mock_llm_with_tools.ainvoke.side_effect = [
            mock_response,
            AIMessage(content="Done with tools"),
        ]

        mock_llm.bind_tools.return_value = mock_llm_with_tools

        # Act
        graph = create_graph(llm=mock_llm, tools=tools)

        result = await graph.ainvoke(
            {
                "messages": [HumanMessage(content="Use the tools")],
                "tool_call_count": 0,
                "max_tool_iterations": 25,
                "next": "agent",
            },
            config={"configurable": {"thread_id": "test-thread-2"}},
        )

        # Assert
        assert "messages" in result

        # Check that we have all expected messages:
        # 1. HumanMessage
        # 2. AIMessage with tool_calls
        # 3. ToolMessage for simple_tool
        # 4. ToolMessage for simple_tool_2
        # 5. AIMessage final response
        messages = result["messages"]
        assert len(messages) == 5

        # Verify message sequence
        assert isinstance(messages[0], HumanMessage)
        assert isinstance(messages[1], AIMessage)
        assert len(messages[1].tool_calls) == 2

        # Verify tool results
        assert isinstance(messages[2], ToolMessage)
        assert messages[2].tool_call_id == "call_1"
        assert "Echo: test" in messages[2].content

        assert isinstance(messages[3], ToolMessage)
        assert messages[3].tool_call_id == "call_2"
        assert "Doubled: 10" in messages[3].content

        # Verify final response
        assert isinstance(messages[4], AIMessage)
        assert messages[4].content == "Done with tools"

    @pytest.mark.asyncio
    async def test_tool_node_handles_single_tool_call(self) -> None:
        """Test that ToolNode handles a single tool call correctly."""
        # Arrange
        mock_llm = MagicMock()
        mock_llm_with_tools = AsyncMock()

        tools = [simple_tool]

        # Mock LLM response with single tool call
        mock_response = AIMessage(
            content="I'll use the tool",
            tool_calls=[
                {
                    "id": "call_1",
                    "name": "simple_tool",
                    "args": {"value": "single"},
                }
            ],
        )

        mock_llm_with_tools.ainvoke.side_effect = [
            mock_response,
            AIMessage(content="Tool executed"),
        ]

        mock_llm.bind_tools.return_value = mock_llm_with_tools

        # Act
        graph = create_graph(llm=mock_llm, tools=tools)

        result = await graph.ainvoke(
            {
                "messages": [HumanMessage(content="Use one tool")],
                "tool_call_count": 0,
                "max_tool_iterations": 25,
                "next": "agent",
            },
            config={"configurable": {"thread_id": "test-thread-3"}},
        )

        # Assert
        messages = result["messages"]
        assert len(messages) == 4  # Human, AI with tool_call, Tool result, AI final

        # Verify tool result
        assert isinstance(messages[2], ToolMessage)
        assert "Echo: single" in messages[2].content

    @pytest.mark.asyncio
    async def test_agent_tools_agent_flow(self) -> None:
        """Test the complete agent -> tools -> agent flow."""
        # Arrange
        mock_llm = MagicMock()
        mock_llm_with_tools = AsyncMock()

        tools = [simple_tool]

        # Simulate multi-turn conversation
        mock_llm_with_tools.ainvoke.side_effect = [
            # First turn: Request tool use
            AIMessage(
                content="Let me check that for you",
                tool_calls=[
                    {
                        "id": "call_1",
                        "name": "simple_tool",
                        "args": {"value": "multi-turn"},
                    }
                ],
            ),
            # Second turn: After tool execution, provide final answer
            AIMessage(content="Based on the tool result, here's the answer"),
        ]

        mock_llm.bind_tools.return_value = mock_llm_with_tools

        # Act
        graph = create_graph(llm=mock_llm, tools=tools)

        result = await graph.ainvoke(
            {
                "messages": [HumanMessage(content="Start multi-turn")],
                "tool_call_count": 0,
                "max_tool_iterations": 25,
                "next": "agent",
            },
            config={"configurable": {"thread_id": "test-thread-4"}},
        )

        # Assert - verify the flow
        messages = result["messages"]

        # Verify agent was called twice (initial + after tool execution)
        assert mock_llm_with_tools.ainvoke.call_count == 2

        # Verify tool_call_count was incremented
        assert result["tool_call_count"] == 1

        # Verify final message is from agent
        assert isinstance(messages[-1], AIMessage)
        assert messages[-1].content == "Based on the tool result, here's the answer"
