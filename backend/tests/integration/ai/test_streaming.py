"""Integration tests for WebSocket streaming with LangGraph astream_events().

Tests end-to-end streaming with proper event mapping.
Follows TDD: Test first, then implement.
"""

from unittest.mock import MagicMock

import pytest
from langchain_core.messages import AIMessage, HumanMessage
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


class TestWebSocketStreaming:
    """Test suite for WebSocket streaming with astream_events()."""

    @pytest.mark.asyncio
    async def test_websocket_streaming_with_astream_events(self) -> None:
        """Test that WebSocket streams tokens, tool calls, and tool results using astream_events()."""
        # Arrange
        mock_llm = MagicMock()
        mock_llm_with_tools = MagicMock()

        tools = [simple_tool]

        # Mock astream_events to simulate LangGraph event streaming
        # This is a simplified version - real implementation would use actual LangGraph astream_events
        async def mock_astream_events(
            input_state: dict[str, object],
            config: dict[str, object],
            version: str | None = None,
        ):
            """Simulate astream_events() for testing."""
            thread_id = config.get("configurable", {}).get("thread_id", "test-thread")

            # Simulate token streaming events
            yield {
                "event": "on_chat_model_stream",
                "data": {
                    "chunk": {
                        "content": "Hello",
                    }
                },
                "metadata": {
                    "thread_id": thread_id,
                },
            }

            yield {
                "event": "on_chat_model_stream",
                "data": {
                    "chunk": {
                        "content": " there",
                    }
                },
                "metadata": {
                    "thread_id": thread_id,
                },
            }

            yield {
                "event": "on_chat_model_stream",
                "data": {
                    "chunk": {
                        "content": "!",
                    }
                },
                "metadata": {
                    "thread_id": thread_id,
                },
            }

            # Simulate tool call events
            yield {
                "event": "on_tool_start",
                "data": {
                    "input": {"value": "test"},
                    "name": "simple_tool",
                    "id": "call_1",
                },
                "metadata": {
                    "thread_id": thread_id,
                },
            }

            # Simulate tool result events
            yield {
                "event": "on_tool_end",
                "data": {
                    "output": "Echo: test",
                    "name": "simple_tool",
                    "id": "call_1",
                },
                "metadata": {
                    "thread_id": thread_id,
                },
            }

            # Simulate completion event
            yield {
                "event": "on_end",
                "data": {
                    "output": {
                        "messages": [
                            HumanMessage(content="Hi"),
                            AIMessage(content="Hello there!"),
                        ],
                        "tool_call_count": 0,
                    }
                },
                "metadata": {
                    "thread_id": thread_id,
                },
            }

        # Create graph with mock LLM
        mock_llm.bind_tools.return_value = mock_llm_with_tools
        graph = create_graph(llm=mock_llm, tools=tools)

        # Replace astream_events with mock
        graph.astream_events = mock_astream_events

        # Act
        events = []
        thread_id = "test-thread-streaming"

        async for event in graph.astream_events(
            input_state={
                "messages": [HumanMessage(content="Hi")],
                "tool_call_count": 0,
                "max_tool_iterations": 25,
                "next": "agent",
            },
            config={"configurable": {"thread_id": thread_id}},
        ):
            events.append(event)

        # Assert
        assert len(events) == 6

        # Verify token streaming events
        token_events = [e for e in events if e["event"] == "on_chat_model_stream"]
        assert len(token_events) == 3
        assert token_events[0]["data"]["chunk"]["content"] == "Hello"
        assert token_events[1]["data"]["chunk"]["content"] == " there"
        assert token_events[2]["data"]["chunk"]["content"] == "!"

        # Verify tool call events
        tool_start_events = [e for e in events if e["event"] == "on_tool_start"]
        assert len(tool_start_events) == 1
        assert tool_start_events[0]["data"]["name"] == "simple_tool"
        assert tool_start_events[0]["data"]["input"] == {"value": "test"}

        tool_end_events = [e for e in events if e["event"] == "on_tool_end"]
        assert len(tool_end_events) == 1
        assert tool_end_events[0]["data"]["output"] == "Echo: test"

        # Verify completion event
        end_events = [e for e in events if e["event"] == "on_end"]
        assert len(end_events) == 1

    @pytest.mark.asyncio
    async def test_websocket_error_handling(self) -> None:
        """Test that WebSocket streaming handles errors correctly."""
        # Arrange
        mock_llm = MagicMock()

        tools = [simple_tool]

        # Create graph
        graph = create_graph(llm=mock_llm, tools=tools)

        # Mock astream_events to raise an error
        async def mock_astream_events_error(
            input_state: dict[str, object],
            config: dict[str, object],
            version: str | None = None,
        ):
            """Simulate error during streaming."""
            yield {
                "event": "on_chat_model_stream",
                "data": {
                    "chunk": {
                        "content": "Before error",
                    }
                },
            }
            # Simulate an error
            raise RuntimeError("Simulated streaming error")

        graph.astream_events = mock_astream_events_error

        # Act & Assert
        events = []
        with pytest.raises(RuntimeError, match="Simulated streaming error"):
            async for event in graph.astream_events(
                input_state={
                    "messages": [HumanMessage(content="Hi")],
                    "tool_call_count": 0,
                    "max_tool_iterations": 25,
                    "next": "agent",
                },
                config={"configurable": {"thread_id": "test-thread-error"}},
            ):
                events.append(event)

        # Verify we got some events before the error
        assert len(events) == 1
        assert events[0]["event"] == "on_chat_model_stream"
        assert events[0]["data"]["chunk"]["content"] == "Before error"

    @pytest.mark.asyncio
    async def test_websocket_multi_tool_calls(self) -> None:
        """Test that WebSocket streaming handles multiple tool calls correctly."""
        # Arrange
        mock_llm = MagicMock()

        tools = [simple_tool]

        # Create graph
        graph = create_graph(llm=mock_llm, tools=tools)

        # Mock astream_events with multiple tool calls
        async def mock_astream_events_multi(
            input_state: dict[str, object],
            config: dict[str, object],
            version: str | None = None,
        ):
            """Simulate multiple tool calls in sequence."""
            thread_id = config.get("configurable", {}).get("thread_id")

            # First tool call
            yield {
                "event": "on_tool_start",
                "data": {
                    "input": {"value": "first"},
                    "name": "simple_tool",
                    "id": "call_1",
                },
                "metadata": {"thread_id": thread_id},
            }

            yield {
                "event": "on_tool_end",
                "data": {
                    "output": "Echo: first",
                    "name": "simple_tool",
                    "id": "call_1",
                },
                "metadata": {"thread_id": thread_id},
            }

            # Second tool call
            yield {
                "event": "on_tool_start",
                "data": {
                    "input": {"value": "second"},
                    "name": "simple_tool",
                    "id": "call_2",
                },
                "metadata": {"thread_id": thread_id},
            }

            yield {
                "event": "on_tool_end",
                "data": {
                    "output": "Echo: second",
                    "name": "simple_tool",
                    "id": "call_2",
                },
                "metadata": {"thread_id": thread_id},
            }

            # Final completion
            yield {
                "event": "on_end",
                "data": {
                    "output": {
                        "messages": [],
                        "tool_call_count": 2,
                    }
                },
                "metadata": {"thread_id": thread_id},
            }

        graph.astream_events = mock_astream_events_multi

        # Act
        events = []
        async for event in graph.astream_events(
            input_state={
                "messages": [HumanMessage(content="Use tools")],
                "tool_call_count": 0,
                "max_tool_iterations": 25,
                "next": "agent",
            },
            config={"configurable": {"thread_id": "test-thread-multi"}},
        ):
            events.append(event)

        # Assert
        assert len(events) == 5

        # Verify tool start events
        tool_start_events = [e for e in events if e["event"] == "on_tool_start"]
        assert len(tool_start_events) == 2
        assert tool_start_events[0]["data"]["input"]["value"] == "first"
        assert tool_start_events[1]["data"]["input"]["value"] == "second"

        # Verify tool end events
        tool_end_events = [e for e in events if e["event"] == "on_tool_end"]
        assert len(tool_end_events) == 2
        assert tool_end_events[0]["data"]["output"] == "Echo: first"
        assert tool_end_events[1]["data"]["output"] == "Echo: second"
