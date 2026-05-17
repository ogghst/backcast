"""Tests for SequentialToolNode — sequential tool execution.

Verifies that the SequentialToolNode executes tools sequentially instead of
in parallel, logs warnings on multiple calls, preserves output format, and
that the monkey-patch function correctly patches ToolNode._afunc.
"""

import logging
from typing import Any
from unittest.mock import MagicMock

import pytest
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.tools import BaseTool, StructuredTool

from app.ai.tools.sequential_tool_node import (
    SequentialToolNode,
    patch_tool_node_for_sequential_execution,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_tool(name: str, func: Any = None) -> BaseTool:
    """Create a simple BaseTool with a given name and async coroutine."""
    if func is None:

        async def _default(**kwargs: Any) -> str:
            """Default test tool."""
            return f"result from {name}"

        func = _default

    return StructuredTool.from_function(
        coroutine=func,
        name=name,
        description=f"Test tool {name}",
    )


def _make_tool_calls(names: list[str]) -> list[dict[str, Any]]:
    """Create minimal tool_call dicts matching what LangGraph expects."""
    return [
        {"name": n, "args": {}, "id": f"call_{i}", "type": "tool_call"}
        for i, n in enumerate(names)
    ]


def _make_runtime() -> MagicMock:
    """Create a mock Runtime object with all attributes _afunc needs."""
    runtime = MagicMock()
    runtime.context = None
    runtime.store = None
    runtime.stream_writer = None
    runtime.execution_info = None
    runtime.server_info = None
    return runtime


def _make_input(tool_calls: list[dict[str, Any]]) -> dict[str, Any]:
    """Create a minimal input dict with an AIMessage carrying tool_calls."""
    ai_msg = AIMessage(content="", tool_calls=tool_calls)
    return {"messages": [ai_msg]}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestSequentialToolNode:
    """Test suite for SequentialToolNode."""

    @pytest.mark.asyncio
    async def test_sequential_tool_node_executes_tools_in_order(self) -> None:
        """Three mock tools must execute in strict sequential order."""
        execution_order: list[str] = []

        async def tool_a(**kwargs: Any) -> str:
            execution_order.append("a")
            return "result_a"

        async def tool_b(**kwargs: Any) -> str:
            execution_order.append("b")
            return "result_b"

        async def tool_c(**kwargs: Any) -> str:
            execution_order.append("c")
            return "result_c"

        tools = [
            _make_tool("tool_a", tool_a),
            _make_tool("tool_b", tool_b),
            _make_tool("tool_c", tool_c),
        ]
        node = SequentialToolNode(tools)

        tool_calls = _make_tool_calls(["tool_a", "tool_b", "tool_c"])
        inp = _make_input(tool_calls)
        config: dict[str, Any] = {"configurable": {}}

        await node._afunc(inp, config, _make_runtime())

        assert execution_order == ["a", "b", "c"]

    @pytest.mark.asyncio
    async def test_sequential_tool_node_logs_warning_on_multiple_calls(self) -> None:
        """WARNING must be logged when more than one tool call is present."""
        from unittest.mock import patch

        async def tool_x(**kwargs: Any) -> str:
            return "x"

        async def tool_y(**kwargs: Any) -> str:
            return "y"

        tools = [_make_tool("tool_x", tool_x), _make_tool("tool_y", tool_y)]
        node = SequentialToolNode(tools)

        tool_calls = _make_tool_calls(["tool_x", "tool_y"])
        inp = _make_input(tool_calls)
        config: dict[str, Any] = {"configurable": {}}

        with patch("app.ai.tools.sequential_tool_node.logger") as mock_logger:
            await node._afunc(inp, config, _make_runtime())

        mock_logger.warning.assert_called_once()
        args = mock_logger.warning.call_args[0]
        assert "sequentially" in args[0]
        assert args[1] == 2
        assert "tool_x" in args[2] and "tool_y" in args[2]

    @pytest.mark.asyncio
    async def test_sequential_tool_node_single_call_no_warning(self) -> None:
        """No WARNING when only one tool call is present."""
        from unittest.mock import patch

        async def tool_single(**kwargs: Any) -> str:
            return "single"

        tools = [_make_tool("tool_single", tool_single)]
        node = SequentialToolNode(tools)

        tool_calls = _make_tool_calls(["tool_single"])
        inp = _make_input(tool_calls)
        config: dict[str, Any] = {"configurable": {}}

        with patch("app.ai.tools.sequential_tool_node.logger") as mock_logger:
            await node._afunc(inp, config, _make_runtime())

        mock_logger.warning.assert_not_called()

    @pytest.mark.asyncio
    async def test_sequential_tool_node_preserves_tool_message_format(self) -> None:
        """Output must match the standard ToolNode format (list of ToolMessage)."""

        async def tool_alpha(**kwargs: Any) -> str:
            return "alpha_result"

        tools = [_make_tool("tool_alpha", tool_alpha)]
        node = SequentialToolNode(tools)

        tool_calls = _make_tool_calls(["tool_alpha"])
        inp = _make_input(tool_calls)
        config: dict[str, Any] = {"configurable": {}}

        result = await node._afunc(inp, config, _make_runtime())

        # Result is a dict with "messages" key when input_type == "dict"
        assert isinstance(result, dict)
        assert "messages" in result
        messages = result["messages"]
        assert len(messages) == 1
        assert isinstance(messages[0], ToolMessage)
        assert messages[0].content == "alpha_result"
        assert messages[0].tool_call_id == "call_0"

    @pytest.mark.asyncio
    async def test_tool_node_monkey_patch_applied(self) -> None:
        """After calling patch function, plain ToolNode._afunc must be sequential."""
        from langgraph.prebuilt import ToolNode

        execution_order: list[str] = []

        async def tool_p(**kwargs: Any) -> str:
            execution_order.append("p")
            return "p_result"

        async def tool_q(**kwargs: Any) -> str:
            execution_order.append("q")
            return "q_result"

        tools = [_make_tool("tool_p", tool_p), _make_tool("tool_q", tool_q)]

        # Apply the monkey-patch
        patch_tool_node_for_sequential_execution()

        # Create a PLAIN ToolNode — not SequentialToolNode
        node = ToolNode(tools)

        tool_calls = _make_tool_calls(["tool_p", "tool_q"])
        inp = _make_input(tool_calls)
        config: dict[str, Any] = {"configurable": {}}

        result = await node._afunc(inp, config, _make_runtime())

        # Must have executed sequentially
        assert execution_order == ["p", "q"]
        assert isinstance(result, dict)
        assert "messages" in result
        messages = result["messages"]
        assert len(messages) == 2
        for msg in messages:
            assert isinstance(msg, ToolMessage)
