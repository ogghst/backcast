"""Middleware to enforce sequential (non-parallel) tool calling.

Injects `parallel_tool_calls=False` into model_settings so the LLM
never returns more than one tool call per turn, preventing concurrent
tool execution and database connection pool exhaustion.
"""

from collections.abc import Awaitable, Callable
from typing import Any

from langchain.agents.middleware.types import (
    AgentMiddleware,
    ModelRequest,
    ModelResponse,
)


class SequentialToolCallsMiddleware(AgentMiddleware):
    """Ensures the model emits only one tool call per turn."""

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse | Any:
        request.model_settings["parallel_tool_calls"] = False
        return await handler(request)
