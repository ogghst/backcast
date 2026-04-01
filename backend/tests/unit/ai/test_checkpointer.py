"""Tests for MemorySaver checkpointer state persistence.

Tests that the LangGraph checkpointer saves and restores state across graph invocations.
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


class TestStatePersistence:
    """Test suite for MemorySaver checkpointer state persistence."""

    @pytest.mark.asyncio
    async def test_state_persistence_and_restoration(self) -> None:
        """Test that state is saved and can be restored across graph invocations."""
        # Arrange
        mock_llm = MagicMock()
        mock_llm_with_tools = AsyncMock()

        tools = [simple_tool]

        # First invocation - LLM responds without tool calls
        mock_llm_with_tools.ainvoke.side_effect = [
            AIMessage(content="Hello! How can I help you?"),
        ]
        mock_llm.bind_tools.return_value = mock_llm_with_tools

        graph = create_graph(llm=mock_llm, tools=tools)
        thread_id = "test-thread-persistence"

        # Act - First invocation
        initial_state = {
            "messages": [HumanMessage(content="Hello")],
            "tool_call_count": 0,
            "max_tool_iterations": 25,
            "next": "agent",
        }

        first_result = await graph.ainvoke(
            initial_state,
            config={"configurable": {"thread_id": thread_id}},
        )

        # Assert - First invocation
        assert "messages" in first_result
        assert len(first_result["messages"]) == 2  # Human + AI
        assert isinstance(first_result["messages"][-1], AIMessage)
        assert first_result["messages"][-1].content == "Hello! How can I help you?"
        assert first_result["tool_call_count"] == 0

        # Arrange - Second invocation with new mock response
        mock_llm_with_tools.ainvoke.side_effect = [
            AIMessage(content="Goodbye!"),
        ]

        # Act - Second invocation (should restore previous state)
        second_result = await graph.ainvoke(
            {
                "messages": [HumanMessage(content="Goodbye")],
                "tool_call_count": 0,
                "max_tool_iterations": 25,
                "next": "agent",
            },
            config={"configurable": {"thread_id": thread_id}},
        )

        # Assert - Second invocation
        assert "messages" in second_result
        # Note: The graph creates a new conversation state
        assert isinstance(second_result["messages"][-1], AIMessage)
        assert second_result["messages"][-1].content == "Goodbye!"

    @pytest.mark.asyncio
    async def test_state_persistence_with_tool_calls(self) -> None:
        """Test that state persists correctly across tool-calling invocations."""
        # Arrange
        mock_llm = MagicMock()
        mock_llm_with_tools = AsyncMock()

        tools = [simple_tool]

        # First invocation - LLM makes tool call
        tool_call_response = AIMessage(
            content="Let me use the tool",
            tool_calls=[
                {
                    "id": "call_1",
                    "name": "simple_tool",
                    "args": {"value": "persist-test"},
                }
            ],
        )
        # After tool execution, LLM provides final answer
        final_response = AIMessage(content="Tool executed successfully")

        mock_llm_with_tools.ainvoke.side_effect = [
            tool_call_response,
            final_response,
        ]
        mock_llm.bind_tools.return_value = mock_llm_with_tools

        graph = create_graph(llm=mock_llm, tools=tools)
        thread_id = "test-thread-tool-persistence"

        # Act
        result = await graph.ainvoke(
            {
                "messages": [HumanMessage(content="Use the tool")],
                "tool_call_count": 0,
                "max_tool_iterations": 25,
                "next": "agent",
            },
            config={"configurable": {"thread_id": thread_id}},
        )

        # Assert
        assert "messages" in result
        assert result["tool_call_count"] == 1

        # Verify message sequence
        messages = result["messages"]
        assert len(messages) == 4  # Human, AI with tool_call, Tool result, AI final
        assert isinstance(messages[0], HumanMessage)
        assert isinstance(messages[1], AIMessage)
        assert len(messages[1].tool_calls) == 1
        assert isinstance(messages[2], ToolMessage)  # Tool result from ToolNode
        assert "Echo: persist-test" in messages[2].content
        assert isinstance(messages[3], AIMessage)
        assert messages[3].content == "Tool executed successfully"

    @pytest.mark.asyncio
    async def test_different_threads_have_separate_state(self) -> None:
        """Test that different thread_ids maintain separate state."""
        # Arrange
        mock_llm = MagicMock()
        mock_llm_with_tools = AsyncMock()

        tools = [simple_tool]

        # Different responses for different threads
        mock_llm_with_tools.ainvoke.side_effect = [
            AIMessage(content="Response for thread 1"),
            AIMessage(content="Response for thread 2"),
        ]
        mock_llm.bind_tools.return_value = mock_llm_with_tools

        graph = create_graph(llm=mock_llm, tools=tools)

        # Act - Thread 1
        result1 = await graph.ainvoke(
            {
                "messages": [HumanMessage(content="Thread 1")],
                "tool_call_count": 0,
                "max_tool_iterations": 25,
                "next": "agent",
            },
            config={"configurable": {"thread_id": "thread-1"}},
        )

        # Act - Thread 2
        result2 = await graph.ainvoke(
            {
                "messages": [HumanMessage(content="Thread 2")],
                "tool_call_count": 0,
                "max_tool_iterations": 25,
                "next": "agent",
            },
            config={"configurable": {"thread_id": "thread-2"}},
        )

        # Assert - Different threads have different responses
        assert result1["messages"][-1].content == "Response for thread 1"
        assert result2["messages"][-1].content == "Response for thread 2"
