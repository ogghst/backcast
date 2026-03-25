"""Unit tests for app.ai.tools.subagent_task module.

Tests the build_task_tool() function which creates a StructuredTool named 'task'
for subagent delegation, replicating the SDK's _build_task_tool() behavior.

Test IDs from plan:
- T-003: build_task_tool returns StructuredTool with correct name and args
- T-004: Invalid subagent_type returns error string
- T-005: Valid invocation returns Command with ToolMessage
- T-006: Async atask function calls subagent.ainvoke() and returns Command
- T-007: State passed to subagent excludes messages, todos, structured_response keys
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain.tools import ToolRuntime
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import StructuredTool
from langgraph.types import Command

from app.ai.tools.subagent_task import (
    _EXCLUDED_STATE_KEYS,
    TASK_SYSTEM_PROMPT,
    TASK_TOOL_DESCRIPTION,
    build_task_tool,
)


class _DummyStreamWriter:
    """Minimal stream writer stub for ToolRuntime construction."""

    def write(self, data: Any) -> None:
        pass


def _make_runtime(
    state: dict[str, Any] | None = None,
    tool_call_id: str | None = "call-123",
) -> ToolRuntime:
    """Create a real ToolRuntime instance for testing."""
    return ToolRuntime(
        state=state or {},
        context={},
        config=RunnableConfig(),
        stream_writer=_DummyStreamWriter(),
        tool_call_id=tool_call_id,
        store=None,
    )


def _make_mock_runnable(return_messages: list[Any] | None = None) -> MagicMock:
    """Create a mock runnable that simulates a compiled subagent graph."""
    runnable = MagicMock()
    runnable.invoke = MagicMock(return_value=return_messages or {"messages": [AIMessage(content="result")]})
    runnable.ainvoke = AsyncMock(return_value=return_messages or {"messages": [AIMessage(content="result")]})
    return runnable


def _make_subagents() -> list[dict[str, Any]]:
    """Create a list of CompiledSubAgent-like dicts for testing."""
    return [
        {
            "name": "test_agent",
            "description": "A test agent for unit tests",
            "runnable": _make_mock_runnable(),
        },
        {
            "name": "other_agent",
            "description": "Another test agent",
            "runnable": _make_mock_runnable(
                return_messages={"messages": [AIMessage(content="other result")]}
            ),
        },
    ]


class TestBuildTaskToolReturnsStructuredTool:
    """T-003: build_task_tool returns StructuredTool with correct name and args."""

    def test_returns_structured_tool(self) -> None:
        """build_task_tool() returns a StructuredTool instance."""
        subagents = _make_subagents()
        tool = build_task_tool(subagents)

        assert isinstance(tool, StructuredTool)

    def test_tool_name_is_task(self) -> None:
        """The tool is named 'task'."""
        subagents = _make_subagents()
        tool = build_task_tool(subagents)

        assert tool.name == "task"

    def test_tool_has_description_with_available_agents(self) -> None:
        """Tool description includes available agent names."""
        subagents = _make_subagents()
        tool = build_task_tool(subagents)

        assert "test_agent" in tool.description
        assert "other_agent" in tool.description

    def test_tool_args_include_description_and_subagent_type(self) -> None:
        """Tool args schema includes 'description' and 'subagent_type' parameters."""
        subagents = _make_subagents()
        tool = build_task_tool(subagents)

        # Check fields directly (model_json_schema fails on ToolRuntime type)
        fields = tool.args_schema.model_fields
        assert "description" in fields
        assert "subagent_type" in fields

    def test_empty_subagents_returns_tool_with_no_agents(self) -> None:
        """build_task_tool with empty list still returns a valid tool."""
        tool = build_task_tool([])

        assert isinstance(tool, StructuredTool)
        assert tool.name == "task"


class TestBuildTaskToolInvalidSubagent:
    """T-004: Invalid subagent_type returns error string."""

    def test_invalid_subagent_returns_error_string(self) -> None:
        """Calling tool with nonexistent subagent_type returns error string (not Command)."""
        subagents = _make_subagents()
        tool = build_task_tool(subagents)

        runtime = _make_runtime(tool_call_id="test-call-id")

        result = tool.invoke({"description": "test", "subagent_type": "nonexistent", "runtime": runtime})

        assert isinstance(result, str)
        assert "nonexistent" in result
        assert "does not exist" in result

    def test_invalid_subagent_lists_allowed_types(self) -> None:
        """Error message lists the allowed subagent types."""
        subagents = _make_subagents()
        tool = build_task_tool(subagents)

        runtime = _make_runtime(tool_call_id="test-call-id")

        result = tool.invoke({"description": "test", "subagent_type": "fake", "runtime": runtime})

        assert "test_agent" in result
        assert "other_agent" in result


class TestBuildTaskToolValidInvocation:
    """T-005: Valid invocation returns Command with ToolMessage."""

    def test_valid_invocation_returns_command(self) -> None:
        """Calling tool with valid subagent returns Command."""
        subagents = _make_subagents()
        tool = build_task_tool(subagents)

        runtime = _make_runtime()

        result = tool.invoke({"description": "Do something", "subagent_type": "test_agent", "runtime": runtime})

        assert isinstance(result, Command)

    def test_command_update_contains_tool_message(self) -> None:
        """Command's update dict contains a ToolMessage in messages list."""
        subagents = _make_subagents()
        tool = build_task_tool(subagents)

        runtime = _make_runtime()

        result = tool.invoke({"description": "Do something", "subagent_type": "test_agent", "runtime": runtime})

        assert isinstance(result, Command)
        messages = result.update["messages"]
        assert len(messages) == 1
        assert isinstance(messages[0], ToolMessage)
        assert messages[0].tool_call_id == "call-123"

    def test_tool_message_content_from_subagent_result(self) -> None:
        """ToolMessage content is the text of the last AIMessage from subagent."""
        subagents = _make_subagents()
        tool = build_task_tool(subagents)

        runtime = _make_runtime()

        result = tool.invoke({"description": "Do something", "subagent_type": "test_agent", "runtime": runtime})

        assert isinstance(result, Command)
        tool_msg = result.update["messages"][0]
        assert tool_msg.content == "result"

    def test_missing_tool_call_id_raises_value_error(self) -> None:
        """Calling tool with no tool_call_id raises ValueError."""
        subagents = _make_subagents()
        tool = build_task_tool(subagents)

        runtime = _make_runtime(tool_call_id=None)

        with pytest.raises(ValueError, match="Tool call ID is required"):
            tool.invoke({"description": "Do something", "subagent_type": "test_agent", "runtime": runtime})

    def test_subagent_invoked_with_human_message(self) -> None:
        """Subagent is invoked with a HumanMessage containing the description."""
        subagents = _make_subagents()
        tool = build_task_tool(subagents)

        runtime = _make_runtime()

        tool.invoke({"description": "Analyze the EVM data", "subagent_type": "test_agent", "runtime": runtime})

        # Verify the subagent was invoked
        subagents[0]["runnable"].invoke.assert_called_once()
        call_args = subagents[0]["runnable"].invoke.call_args[0][0]

        assert "messages" in call_args
        assert len(call_args["messages"]) == 1
        assert isinstance(call_args["messages"][0], HumanMessage)
        assert call_args["messages"][0].content == "Analyze the EVM data"


class TestBuildTaskToolAsyncInvocation:
    """T-006: Async atask function calls subagent.ainvoke() and returns Command."""

    @pytest.mark.asyncio
    async def test_async_returns_command(self) -> None:
        """Async invocation of the tool returns a Command."""
        subagents = _make_subagents()
        tool = build_task_tool(subagents)

        runtime = _make_runtime(tool_call_id="call-async-123")

        result = await tool.ainvoke({"description": "Do async task", "subagent_type": "test_agent", "runtime": runtime})

        assert isinstance(result, Command)

    @pytest.mark.asyncio
    async def test_async_calls_ainvoke_on_subagent(self) -> None:
        """Async invocation calls ainvoke (not invoke) on the subagent runnable."""
        subagents = _make_subagents()
        tool = build_task_tool(subagents)

        runtime = _make_runtime(tool_call_id="call-async-123")

        await tool.ainvoke({"description": "Do async task", "subagent_type": "test_agent", "runtime": runtime})

        # Verify ainvoke was called, not invoke
        subagents[0]["runnable"].ainvoke.assert_called_once()
        subagents[0]["runnable"].invoke.assert_not_called()

    @pytest.mark.asyncio
    async def test_async_invalid_subagent_returns_error_string(self) -> None:
        """Async invocation with invalid subagent_type returns error string."""
        subagents = _make_subagents()
        tool = build_task_tool(subagents)

        runtime = _make_runtime(tool_call_id="call-async-123")

        result = await tool.ainvoke({"description": "test", "subagent_type": "nonexistent", "runtime": runtime})

        assert isinstance(result, str)
        assert "does not exist" in result


class TestBuildTaskToolExcludesStateKeys:
    """T-007: State passed to subagent excludes messages, todos, structured_response keys."""

    def test_excluded_keys_not_passed_to_subagent(self) -> None:
        """State keys in _EXCLUDED_STATE_KEYS are filtered out before invoking subagent."""
        subagents = _make_subagents()
        tool = build_task_tool(subagents)

        runtime = _make_runtime(state={
            "messages": [HumanMessage(content="existing")],
            "todos": [{"task": "old task"}],
            "structured_response": {"key": "value"},
            "some_other_key": "preserved",
            "custom_data": 42,
        })

        tool.invoke({"description": "test", "subagent_type": "test_agent", "runtime": runtime})

        call_args = subagents[0]["runnable"].invoke.call_args[0][0]

        # Excluded keys should NOT be in the state passed to subagent
        for key in _EXCLUDED_STATE_KEYS:
            if key in ["messages"]:
                # messages is replaced, not passed through
                continue
            assert key not in call_args, f"Excluded key '{key}' should not be passed to subagent"

        # Non-excluded keys SHOULD be passed through
        assert call_args["some_other_key"] == "preserved"
        assert call_args["custom_data"] == 42

    def test_messages_replaced_not_merged(self) -> None:
        """Messages in subagent state is replaced with [HumanMessage(description)], not merged."""
        subagents = _make_subagents()
        tool = build_task_tool(subagents)

        runtime = _make_runtime(state={
            "messages": [HumanMessage(content="existing message"), AIMessage(content="old response")],
        })

        tool.invoke({"description": "New task description", "subagent_type": "test_agent", "runtime": runtime})

        call_args = subagents[0]["runnable"].invoke.call_args[0][0]

        # Should have exactly one message - the new HumanMessage
        assert len(call_args["messages"]) == 1
        assert call_args["messages"][0].content == "New task description"

    def test_command_update_excludes_state_keys(self) -> None:
        """Command update does not include excluded state keys from subagent result."""
        subagents = _make_subagents()
        tool = build_task_tool(subagents)

        # Create a subagent that returns extra state keys
        subagents[0]["runnable"].invoke = MagicMock(return_value={
            "messages": [AIMessage(content="result")],
            "todos": [{"task": "subagent todo"}],
            "structured_response": {"summary": "done"},
            "custom_key": "custom_value",
        })

        runtime = _make_runtime()

        result = tool.invoke({"description": "test", "subagent_type": "test_agent", "runtime": runtime})

        assert isinstance(result, Command)
        update = result.update

        # Excluded keys should not be in the update (messages is handled separately)
        assert "todos" not in update
        assert "structured_response" not in update

        # Non-excluded keys should be in the update
        assert update["custom_key"] == "custom_value"


class TestBuildTaskToolErrorPaths:
    """Tests for uncovered error paths to achieve 100% coverage (IMP-003)."""

    def test_subagent_result_missing_messages_raises_value_error(self) -> None:
        """Subagent result without 'messages' key raises ValueError (line 211)."""
        subagents = _make_subagents()
        subagents[0]["runnable"].invoke = MagicMock(return_value={"no_messages_key": "oops"})

        tool = build_task_tool(subagents)
        runtime = _make_runtime()

        with pytest.raises(ValueError, match="messages"):
            tool.invoke({"description": "test", "subagent_type": "test_agent", "runtime": runtime})

    @pytest.mark.asyncio
    async def test_async_missing_tool_call_id_raises_value_error(self) -> None:
        """Async invocation with no tool_call_id raises ValueError (line 312)."""
        subagents = _make_subagents()
        tool = build_task_tool(subagents)

        runtime = _make_runtime(tool_call_id=None)

        with pytest.raises(ValueError, match="Tool call ID is required"):
            await tool.ainvoke({"description": "Do async task", "subagent_type": "test_agent", "runtime": runtime})


class TestExcludedStateKeys:
    """Verify _EXCLUDED_STATE_KEYS matches the SDK's set."""

    def test_excluded_keys_match_sdk(self) -> None:
        """_EXCLUDED_STATE_KEYS contains the same keys as the SDK."""
        expected = {"messages", "todos", "structured_response", "skills_metadata", "memory_contents"}
        assert _EXCLUDED_STATE_KEYS == expected


class TestTaskToolDescription:
    """Verify tool description templates and system prompt."""

    def test_task_tool_description_template(self) -> None:
        """TASK_TOOL_DESCRIPTION contains {available_agents} placeholder."""
        assert "{available_agents}" in TASK_TOOL_DESCRIPTION

    def test_task_system_prompt_exists(self) -> None:
        """TASK_SYSTEM_PROMPT contains when-to-use and when-not-to-use guidance."""
        assert "When to use" in TASK_SYSTEM_PROMPT
        assert "When NOT to use" in TASK_SYSTEM_PROMPT
        assert "task" in TASK_SYSTEM_PROMPT

    def test_custom_description_used_when_provided(self) -> None:
        """build_task_tool uses custom description when provided."""
        subagents = _make_subagents()
        custom_desc = "Custom tool description. Available: {available_agents}"
        tool = build_task_tool(subagents, task_description=custom_desc)

        assert tool.description.startswith("Custom tool description.")
        assert "test_agent" in tool.description
        assert "other_agent" in tool.description

    def test_custom_description_without_placeholder(self) -> None:
        """build_task_tool uses custom description as-is when no placeholder."""
        subagents = _make_subagents()
        custom_desc = "Static description with no placeholder"
        tool = build_task_tool(subagents, task_description=custom_desc)

        assert tool.description == "Static description with no placeholder"


class TestToolMessageContentStripping:
    """Verify trailing whitespace is stripped from subagent results."""

    def test_trailing_whitespace_stripped(self) -> None:
        """ToolMessage content has trailing whitespace stripped."""
        subagents = _make_subagents()
        subagents[0]["runnable"].invoke = MagicMock(return_value={
            "messages": [AIMessage(content="result with trailing space   \n\n")],
        })

        tool = build_task_tool(subagents)

        runtime = _make_runtime()

        result = tool.invoke({"description": "test", "subagent_type": "test_agent", "runtime": runtime})

        assert isinstance(result, Command)
        tool_msg = result.update["messages"][0]
        assert tool_msg.content == "result with trailing space"
