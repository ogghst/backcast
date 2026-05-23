"""Pure extraction helpers for LangChain message types.

Provides functions to pull final AI responses and tool output content from
LangGraph message lists, handling edge cases like DeepSeek models that
sometimes return empty final AIMessages after tool execution.
"""

from __future__ import annotations

from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langgraph.types import Command

__all__ = [
    "extract_final_ai_response",
    "extract_tool_output_content",
    "find_last_ai_reasoning_kwargs",
    "is_transient_stream_error",
]


def find_last_ai_reasoning_kwargs(messages: list[BaseMessage]) -> dict[str, Any]:
    """Find reasoning_content from the last AIMessage and return additional_kwargs.

    Returns an empty dict if no reasoning_content is found. Used by handoff
    tools to propagate DeepSeek thinking mode across synthetic messages.
    """
    for msg in reversed(messages):
        if isinstance(msg, AIMessage):
            rc = msg.additional_kwargs.get("reasoning_content")
            if rc:
                return {"additional_kwargs": {"reasoning_content": rc}}
            return {}
    return {}


def is_transient_stream_error(exc: Exception) -> bool:
    """Check if a streaming error is transient and worth retrying."""
    if isinstance(exc, (ConnectionResetError, OSError)):
        return True
    err_type = type(exc).__name__
    err_module = type(exc).__module__
    return (err_type == "ReadError" and "httpcore" in err_module) or (
        err_type == "RemoteProtocolError" and "httpx" in err_module
    )


def extract_final_ai_response(messages: list[BaseMessage]) -> str:
    """Extract the last AIMessage without tool_calls from a message list.

    Falls back to concatenating ToolMessage content if the final AIMessage
    is empty (handles DeepSeek models that sometimes return empty content
    after tool execution).

    Args:
        messages: LangChain message history from graph invocation.

    Returns:
        Extracted text content, or empty string if nothing found.
    """
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and not msg.tool_calls:
            content = str(msg.content).strip()
            if content:
                return content

    # Fallback: concatenate tool results in original order
    tool_parts: list[str] = []
    for msg in reversed(messages):
        if isinstance(msg, ToolMessage) and msg.content:
            tool_parts.append(str(msg.content))
    if tool_parts:
        return "\n\n".join(reversed(tool_parts))
    return ""


def extract_tool_output_content(tool_output: Any) -> str:
    """Extract string content from various tool output types.

    Handles ToolMessage, LangGraph Command, dict with "content" key,
    and raw strings. Returns empty string if extraction fails.

    Args:
        tool_output: Tool result from LangGraph tool node execution.

    Returns:
        Extracted text content, or empty string.
    """
    if isinstance(tool_output, ToolMessage):
        raw = tool_output.content
        return raw if isinstance(raw, str) else str(raw)
    if isinstance(tool_output, Command):
        update_dict = tool_output.update
        if isinstance(update_dict, dict):
            messages = update_dict.get("messages", [])
            if messages:
                last_msg = messages[-1]
                if isinstance(last_msg, dict):
                    return last_msg.get("content", "")
                if hasattr(last_msg, "content"):
                    return str(last_msg.content)
                return str(last_msg)
    if isinstance(tool_output, dict) and "content" in tool_output:
        content = tool_output["content"]
        return content if isinstance(content, str) else str(content)
    if isinstance(tool_output, str):
        return tool_output
    return str(tool_output) if tool_output is not None else ""
