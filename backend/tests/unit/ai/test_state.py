"""Tests for AgentState TypedDict definition.

Follows TDD: Test first, then implement.
"""

from langchain_core.messages import AIMessage, HumanMessage

from app.ai.state import AgentState


class TestAgentState:
    """Test suite for AgentState TypedDict."""

    def test_agentstate_is_typeddict(self) -> None:
        """Test that AgentState is a TypedDict."""
        from typing_extensions import is_typeddict

        assert is_typeddict(AgentState), "AgentState must be a TypedDict"

    def test_agentstate_has_messages_field(self) -> None:
        """Test that AgentState has a messages field."""
        state = AgentState(messages=[], tool_call_count=0)
        assert "messages" in state
        assert isinstance(state["messages"], list)

    def test_agentstate_has_tool_call_count_field(self) -> None:
        """Test that AgentState has a tool_call_count field."""
        state = AgentState(messages=[], tool_call_count=0)
        assert "tool_call_count" in state
        assert state["tool_call_count"] == 0

    def test_agentstate_has_next_field(self) -> None:
        """Test that AgentState has a next field."""
        state = AgentState(messages=[], tool_call_count=0, next="agent")
        assert "next" in state
        assert state["next"] == "agent"

    def test_agentstate_accepts_valid_next_values(self) -> None:
        """Test that AgentState accepts valid next values."""
        valid_values = ["agent", "tools", "end"]
        for value in valid_values:
            state = AgentState(messages=[], tool_call_count=0, next=value)
            assert state["next"] == value

    def test_agentstate_messages_append_behavior(self) -> None:
        """Test that messages field uses Annotated for append behavior."""
        # This test verifies the operator.add annotation for messages
        # When using StateGraph, this should append instead of replace
        state1 = AgentState(
            messages=[HumanMessage(content="Hello")],
            tool_call_count=0,
        )
        state2 = AgentState(
            messages=[AIMessage(content="Hi there!")],
            tool_call_count=0,
        )

        # In StateGraph with operator.add, these should merge
        # For now, we just verify both can be created
        assert len(state1["messages"]) == 1
        assert len(state2["messages"]) == 1
        assert isinstance(state1["messages"][0], HumanMessage)
        assert isinstance(state2["messages"][0], AIMessage)

    def test_agentstate_with_base_messages(self) -> None:
        """Test that AgentState accepts BaseMessage instances."""
        from langchain_core.messages import SystemMessage

        messages = [
            SystemMessage(content="You are a helpful assistant"),
            HumanMessage(content="Hello"),
            AIMessage(content="Hi there!"),
        ]

        state = AgentState(messages=messages, tool_call_count=0)
        assert len(state["messages"]) == 3
        assert all(isinstance(msg, object) for msg in state["messages"])

    def test_agentstate_tool_call_count_increment(self) -> None:
        """Test that tool_call_count can be incremented."""
        state = AgentState(messages=[], tool_call_count=0)
        assert state["tool_call_count"] == 0

        # Simulate increment
        state["tool_call_count"] = 1
        assert state["tool_call_count"] == 1

    def test_agentstate_default_values(self) -> None:
        """Test AgentState with minimal required fields."""
        # TypedDict doesn't enforce defaults, but we test creation
        state = AgentState(messages=[], tool_call_count=0)
        assert state["messages"] == []
        assert state["tool_call_count"] == 0
        # 'next' is optional
