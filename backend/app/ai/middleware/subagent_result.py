"""SubagentResultMiddleware for intercepting subagent task tool results.

Intercepts the Deep Agents SDK 'task' tool execution to:
1. Capture the original subagent result content
2. Store it in a context variable for agent_service.py to retrieve
3. Return a truncated acknowledgment to the main agent

This prevents the main agent from repeating the subagent's output
verbatim in its synthesis response, since the full result is already
delivered to the user via the Activity Panel.
"""

import contextvars
import logging
from typing import Any, cast

from langchain.agents.middleware.types import AgentMiddleware
from langchain_core.messages import ToolMessage
from langgraph.prebuilt.tool_node import ToolCallRequest
from langgraph.types import Command

logger = logging.getLogger(__name__)

# Context variable to store the original subagent result for this async context.
# agent_service.py retrieves this via get_last_subagent_result() after
# the on_tool_end event fires for the task tool.
_last_subagent_result: contextvars.ContextVar[str] = contextvars.ContextVar(
    "_last_subagent_result", default=""
)

# Truncated message returned to the main agent in place of the full subagent result.
_TRUNCATED_ACKNOWLEDGMENT = "[Subagent result delivered to user via Activity Panel]"


class SubagentResultMiddleware(AgentMiddleware):
    """Middleware that intercepts task tool results to prevent main agent repetition.

    When the Deep Agents SDK 'task' tool executes, it returns a Command object
    containing a ToolMessage with the subagent's full response. Without
    interception, the main agent receives this full text and tends to repeat
    it in its synthesis response.

    This middleware:
    - Captures the original subagent content into a ContextVar
    - Replaces the ToolMessage content with a brief acknowledgment
    - Allows agent_service.py to send the original content via the Activity Panel

    Attributes:
        tools: Empty list to avoid registering any tools (follows BackcastSecurityMiddleware pattern)
    """

    tools: list[Any] = []

    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Any,
    ) -> ToolMessage | Command[Any]:
        """Wrap tool call to intercept task tool execution.

        For the 'task' tool, captures the original subagent result and returns
        a truncated version to the main agent. All other tools pass through
        unchanged.

        Args:
            request: ToolCallRequest containing tool_call information
            handler: Callable to execute the tool

        Returns:
            ToolMessage or Command with potentially truncated content for task tool
        """
        tool_call = request.tool_call
        tool_name = tool_call.get("name", "")

        # Only intercept the task (subagent delegation) tool
        if tool_name != "task":
            return await handler(request)

        logger.info(
            f"[SUBAGENT_RESULT_INTERCEPT] awrap_tool_call | "
            f"tool_name={tool_name} | "
            f"tool_call_id={tool_call.get('id', '')}"
        )

        # Execute the tool to get the result
        result = await handler(request)

        # Extract the original subagent content and store in ContextVar
        original_content = self._extract_content(result)
        if original_content:
            _last_subagent_result.set(original_content)
            logger.info(
                f"[SUBAGENT_RESULT_CAPTURED] Stored subagent result | "
                f"content_length={len(original_content)}"
            )

            # Replace the content in the result with a truncated acknowledgment
            result = self._replace_content(result, _TRUNCATED_ACKNOWLEDGMENT)
            logger.info(
                "[SUBAGENT_RESULT_TRUNCATED] Returned truncated acknowledgment to main agent"
            )
        else:
            logger.warning(
                "[SUBAGENT_RESULT_INTERCEPT] Could not extract content from task tool result"
            )

        return result

    @staticmethod
    def _extract_content(result: ToolMessage | Command[Any]) -> str:
        """Extract text content from a ToolMessage or Command result.

        Args:
            result: The tool execution result (ToolMessage or Command)

        Returns:
            Extracted content string, or empty string if extraction fails
        """
        if isinstance(result, ToolMessage):
            content = result.content
            return content if isinstance(content, str) else str(content)

        if isinstance(result, Command) and result.update is not None:
            messages = result.update.get("messages", [])
            if messages and isinstance(messages[0], ToolMessage):
                content = messages[0].content
                return content if isinstance(content, str) else str(content)
            if messages and isinstance(messages[0], str):
                return messages[0]

        return ""

    @staticmethod
    def _replace_content(
        result: ToolMessage | Command[Any], new_content: str
    ) -> ToolMessage | Command[Any]:
        """Replace content in a ToolMessage or Command with truncated text.

        Args:
            result: The original tool execution result
            new_content: The truncated content to substitute

        Returns:
            Modified ToolMessage or Command with replaced content
        """
        if isinstance(result, ToolMessage):
            return ToolMessage(
                content=new_content,
                tool_call_id=result.tool_call_id,
                additional_kwargs=result.additional_kwargs,
            )

        if isinstance(result, Command) and result.update is not None:
            messages = result.update.get("messages", [])
            if messages and isinstance(messages[0], ToolMessage):
                truncated_message = ToolMessage(
                    content=new_content,
                    tool_call_id=messages[0].tool_call_id,
                    additional_kwargs=messages[0].additional_kwargs,
                )
                return Command(
                    update={
                        **cast(dict[str, Any], result.update),
                        "messages": [truncated_message],
                    }
                )

        return result


def get_last_subagent_result() -> str:
    """Get the last subagent result stored by SubagentResultMiddleware.

    Returns:
        The original subagent content string, or empty string if not set
    """
    return _last_subagent_result.get()


def clear_last_subagent_result() -> None:
    """Clear the last subagent result from the context variable.

    Should be called after retrieving the result to prevent stale data
    from being used in subsequent tool calls.
    """
    _last_subagent_result.set("")
