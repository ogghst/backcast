"""Middleware to enforce sequential (non-parallel) tool behavior.

Two layers, both native v1 public API:
  1. awrap_model_call: injects parallel_tool_calls=False into model_settings so
     the LLM emits at most one tool call per turn (emission control).
  2. awrap_tool_call: holds one shared asyncio.Lock around the tool execute
     handler so that, if the model ignores #1 and emits multiple calls in one
     AIMessage, they still execute one at a time (execution serialization — the
     native replacement for the deleted private-API tool-node fork).

The lock MUST be a single shared instance per middleware: LangGraph runs the
tool calls from one assistant message concurrently, and each passes through this
wrapper, so they all enter the shared lock. build_backcast_middleware creates a
fresh stack per subagent, so each graph gets its own lock (per-graph serialization).
"""

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

from langchain.agents.middleware.types import (
    AgentMiddleware,
    ModelRequest,
    ModelResponse,
    ToolCallRequest,
)


class SequentialToolCallsMiddleware(AgentMiddleware):
    """Ensures tools execute one at a time (emission + execution control)."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse | Any:
        request.model_settings["parallel_tool_calls"] = False
        return await handler(request)

    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Awaitable[Any]],
    ) -> Any:
        async with self._lock:
            return await handler(request)
