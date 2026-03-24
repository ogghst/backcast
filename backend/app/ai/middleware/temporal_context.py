"""Temporal context middleware for Deep Agents SDK.

Ensures temporal parameters (as_of, branch_name, branch_mode) are:
1. Injected into tool calls
2. Not modifiable by LLM (security against prompt injection)
3. Logged for observability
"""

import logging
from typing import Any

from langchain.agents.middleware.types import AgentMiddleware
from langchain_core.messages import ToolMessage
from langgraph.prebuilt.tool_node import ToolCallRequest

from app.ai.tools.types import ToolContext

logger = logging.getLogger(__name__)


class TemporalContextMiddleware(AgentMiddleware):
    """Middleware for injecting temporal context into tool calls.

    This class provides temporal context injection by implementing the
    AgentMiddleware interface from langchain.agents.middleware.types.

    Attributes:
        context: ToolContext containing temporal parameters (as_of, branch_name, branch_mode)
    """

    def __init__(self, context: ToolContext) -> None:
        """Initialize TemporalContextMiddleware with context.

        Args:
            context: ToolContext containing temporal parameters
        """
        super().__init__()
        self.context = context

    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Any,
    ) -> ToolMessage:
        """Wrap tool call to inject temporal context.

        Args:
            request: ToolCallRequest containing tool_call information
            handler: Callable to execute the tool

        Returns:
            Result from handler execution

        Note:
            This function modifies the tool_call arguments to inject temporal parameters.
            The temporal parameters come from the session context, not from the LLM,
            preventing prompt injection attacks that try to bypass temporal constraints.
        """
        tool_call = request.tool_call
        tool_name = tool_call.get("name", "")
        tool_args = dict(tool_call.get("args", {}))

        # Log temporal context injection
        logger.info(
            f"[TEMPORAL_CONTEXT_INJECTION] awrap_tool_call | "
            f"tool_name={tool_name} | "
            f"as_of={self.context.as_of} | "
            f"branch_name={self.context.branch_name} | "
            f"branch_mode={self.context.branch_mode} | "
            f"project_id={self.context.project_id} | "
            f"execution_mode={self.context.execution_mode.value}"
        )

        # Override temporal parameters (prevents LLM bypass)
        # This ensures the temporal context from the session is used,
        # not any values the LLM might try to inject
        if self.context.as_of:
            tool_args["as_of"] = self.context.as_of.isoformat()
        if self.context.branch_name:
            tool_args["branch_name"] = self.context.branch_name
        if self.context.branch_mode:
            tool_args["branch_mode"] = self.context.branch_mode
        if self.context.project_id:
            tool_args["project_id"] = str(self.context.project_id)

        # Create new tool_call dictionary with modified args
        # Note: tool_call is already a ToolCall (TypedDict), so we need to cast
        new_tool_call: Any = dict(tool_call)
        new_tool_call["args"] = tool_args

        # Create overridden request and execute
        new_request = request.override(tool_call=new_tool_call)
        return await handler(new_request)

    def inject_temporal_context(
        self,
        tool_args: dict[str, Any],
    ) -> dict[str, Any]:
        """Synchronous version for direct context injection.

        Args:
            tool_args: Original tool arguments

        Returns:
            Modified tool arguments with temporal context injected

        Note:
            This is a synchronous helper for cases where async middleware
            hooks are not available.
        """
        # Create a copy to avoid modifying the original
        result = dict(tool_args)

        if self.context.as_of:
            result["as_of"] = self.context.as_of.isoformat()
        if self.context.branch_name:
            result["branch_name"] = self.context.branch_name
        if self.context.branch_mode:
            result["branch_mode"] = self.context.branch_mode
        if self.context.project_id:
            result["project_id"] = str(self.context.project_id)

        return result
