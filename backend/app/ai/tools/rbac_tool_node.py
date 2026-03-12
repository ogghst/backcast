"""RBACToolNode for permission-checked tool execution.

Extends LangGraph's ToolNode to add permission checking before tool execution.
Reads tool metadata and validates user permissions via RBACService.
"""

from typing import Any

from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.tools import BaseTool
from langgraph.prebuilt import ToolNode

from app.ai.tools.types import ToolContext
from app.core.rbac import get_rbac_service


class RBACToolNode(ToolNode):
    """ToolNode subclass with RBAC permission checking.

    Wraps LangGraph's ToolNode to add permission checks before tool execution.
    Reads _tool_metadata from tools to determine required permissions.

    Attributes:
        tools: List of tools available for execution
        context: ToolContext containing user_role for permission checks

    Example:
        ```python
        from app.ai.tools import create_project_tools
        from app.ai.tools.rbac_tool_node import RBACToolNode

        context = ToolContext(session, user_id, user_role="admin")
        tools = create_project_tools(context)
        tool_node = RBACToolNode(tools, context)

        # Add to StateGraph
        workflow.add_node("tools", tool_node)
        ```
    """

    def __init__(
        self,
        tools: list[BaseTool],
        context: ToolContext,
    ) -> None:
        """Initialize RBACToolNode with tools and context.

        Args:
            tools: List of BaseTool instances to execute
            context: ToolContext with user_role for permission checks
        """
        super().__init__(tools, awrap_tool_call=self._awrap_tool_call)
        self.context = context
        self.tools = tools

    def _check_tool_permission(self, tool_name: str) -> str | None:
        """Check if user has permission to execute a tool.

        Args:
            tool_name: Name of the tool to check

        Returns:
            None if permitted, error message string if denied

        Note:
            Reads _tool_metadata.permissions from the tool instance.
            Uses RBACServiceABC.has_permission for the check.
        """
        # Find the tool by name
        tool = None
        for t in self.tools:
            if t.name == tool_name:
                tool = t
                break

        if tool is None:
            return f"Tool not found: {tool_name}"

        # Get tool metadata
        metadata = getattr(tool, "_tool_metadata", None)
        if metadata is None:
            # No metadata means no permission requirements
            return None

        # Check each required permission
        rbac_service = get_rbac_service()
        for permission in metadata.permissions:
            if not rbac_service.has_permission(self.context.user_role, permission):
                return (
                    f"Permission denied: {permission} required "
                    f"(user_role: {self.context.user_role}, tool: {tool_name})"
                )

        # All permissions granted
        return None

    async def _awrap_tool_call(
        self,
        request: Any,
        execute: Any,
    ) -> Any:
        """Wrap tool call to check permissions and inject context.

        Args:
            request: ToolCallRequest containing tool_call information
            execute: Function to execute the tool

        Returns:
            ToolMessage with result or error
        """
        tool_call = request.tool_call
        tool_name = tool_call.get("name", "")
        tool_id = tool_call.get("id", "")

        # 1. Check permissions
        error_message = self._check_tool_permission(tool_name)
        if error_message:
            return ToolMessage(
                content=error_message,
                tool_call_id=tool_id
            )

        # 2. Inject context into args
        new_tool_args = dict(tool_call.get("args", {}))
        new_tool_args["context"] = self.context

        # Create new tool_call dictionary with modified args
        new_tool_call = dict(tool_call)
        new_tool_call["args"] = new_tool_args

        # Create overridden request and execute
        new_request = request.override(tool_call=new_tool_call)
        return await execute(new_request)
