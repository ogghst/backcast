"""RBACToolNode for permission-checked tool execution.

Extends LangGraph's ToolNode to add permission checking before tool execution.
Reads tool metadata and validates user permissions via RBACService.
Integrates with risk checking to ensure both permission and risk checks pass.
"""

from typing import Any

from langchain_core.messages import ToolMessage
from langchain_core.tools import BaseTool
from langgraph.prebuilt import ToolNode

from app.ai.tools.types import ExecutionMode, RiskLevel, ToolContext
from app.core.rbac import get_rbac_service


class RBACToolNode(ToolNode):
    """ToolNode subclass with RBAC permission checking and risk checking.

    Wraps LangGraph's ToolNode to add permission and risk checks before tool execution.
    Reads _tool_metadata from tools to determine required permissions and risk levels.

    Attributes:
        tools: List of tools available for execution
        context: ToolContext containing user_role and execution_mode for checks

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
            context: ToolContext with user_role and execution_mode for checks
        """
        super().__init__(tools, awrap_tool_call=self._awrap_tool_call)
        self.context = context
        self.tools = tools

    async def _check_tool_permission(
        self,
        tool_name: str,
        tool_args: dict[str, Any],
    ) -> str | None:
        """Check if user has permission to execute a tool.

        Args:
            tool_name: Name of the tool to check
            tool_args: Arguments passed to the tool (may contain project_id)

        Returns:
            None if permitted, error message string if denied

        Note:
            Reads _tool_metadata.permissions from the tool instance.
            Uses RBACServiceABC.has_project_access for project-level checks when available.
            Falls back to RBACServiceABC.has_permission for global permissions.
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

        # Extract project_id from tool_args if present
        project_id = tool_args.get("project_id")

        # Get RBAC service
        rbac_service = get_rbac_service()

        # Inject session if service supports it and project_id is provided
        if project_id is not None and hasattr(rbac_service, "session"):
            if rbac_service.session is None:
                rbac_service.session = self.context.session

        # Check each required permission
        for permission in metadata.permissions:
            # Use project-level access check if project_id is provided
            if project_id is not None and hasattr(rbac_service, "has_project_access"):
                from uuid import UUID

                try:
                    project_uuid = UUID(project_id) if isinstance(project_id, str) else project_id
                    user_uuid = UUID(self.context.user_id)

                    has_access = await rbac_service.has_project_access(
                        user_id=user_uuid,
                        user_role=self.context.user_role,
                        project_id=project_uuid,
                        required_permission=permission,
                    )

                    if not has_access:
                        return (
                            f"Permission denied: {permission} required "
                            f"for project {project_id} "
                            f"(user_role: {self.context.user_role}, tool: {tool_name})"
                        )
                except (ValueError, TypeError):
                    # Invalid UUID format, deny permission
                    return (
                        f"Permission denied: Invalid project_id format "
                        f"(tool: {tool_name})"
                    )
            else:
                # Global permission check
                if not rbac_service.has_permission(self.context.user_role, permission):
                    return (
                        f"Permission denied: {permission} required "
                        f"(user_role: {self.context.user_role}, tool: {tool_name})"
                    )

        # All permissions granted
        return None

    def check_tool_risk(
        self,
        tool_name: str,
    ) -> tuple[bool, str | None]:
        """Check if a tool is allowed based on execution mode and risk level.

        Args:
            tool_name: Name of the tool to check

        Returns:
            Tuple of (allowed, error_message)
            - allowed: True if tool can be executed, False otherwise
            - error_message: Error message if not allowed, None otherwise
        """
        # Find the tool by name
        tool = None
        for t in self.tools:
            if t.name == tool_name:
                tool = t
                break

        if tool is None:
            return False, f"Tool not found: {tool_name}"

        # Get tool metadata
        metadata = getattr(tool, "_tool_metadata", None)
        if metadata is None:
            # No metadata means no risk level - assume high (safe default)
            risk_level = RiskLevel.HIGH
        else:
            risk_level = metadata.risk_level

        # Check based on execution mode
        mode = self.context.execution_mode

        if mode == ExecutionMode.SAFE:
            if risk_level != RiskLevel.LOW:
                return (
                    False,
                    f"Tool '{tool_name}' requires {risk_level.value} risk level. "
                    f"Safe mode only allows low-risk tools."
                )
        elif mode == ExecutionMode.STANDARD:
            if risk_level == RiskLevel.CRITICAL:
                return (
                    False,
                    f"Tool '{tool_name}' has critical risk level. "
                    f"Standard mode requires approval for critical tools."
                )
        # Expert mode allows all tools

        return True, None

    async def _awrap_tool_call(
        self,
        request: Any,
        execute: Any,
    ) -> Any:
        """Wrap tool call to check permissions, risk, and inject context.

        Args:
            request: ToolCallRequest containing tool_call information
            execute: Function to execute the tool

        Returns:
            ToolMessage with result or error
        """
        tool_call = request.tool_call
        tool_name = tool_call.get("name", "")
        tool_id = tool_call.get("id", "")
        tool_args = dict(tool_call.get("args", {}))

        # 1. Check permissions (async now)
        error_message = await self._check_tool_permission(tool_name, tool_args)
        if error_message:
            return ToolMessage(
                content=error_message,
                tool_call_id=tool_id
            )

        # 2. Check risk level (only if permission granted)
        allowed, risk_error = self.check_tool_risk(tool_name)
        if not allowed:
            return ToolMessage(
                content=risk_error or "Tool execution not allowed based on risk level",
                tool_call_id=tool_id
            )

        # 3. Inject context into args
        tool_args["context"] = self.context

        # Create new tool_call dictionary with modified args
        new_tool_call = dict(tool_call)
        new_tool_call["args"] = tool_args

        # Create overridden request and execute
        new_request = request.override(tool_call=new_tool_call)
        return await execute(new_request)
