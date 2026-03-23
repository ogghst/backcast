"""Backcast security middleware for Deep Agents SDK.

Implements three-tier security:
1. JWT authentication (handled at API layer)
2. RBAC permission checking
3. Risk-based execution modes

Note: This middleware applies security to Backcast tools (decorated with @ai_tool).
External tools (e.g., Deep Agents SDK built-in tools like write_todos, task) are
allowed through without Backcast-specific checks, as they have their own security.
"""

import contextvars
import logging
from typing import Any

from langchain.agents.middleware.types import AgentMiddleware
from langchain_core.messages import ToolMessage
from langgraph.prebuilt.tool_node import ToolCallRequest

from app.ai.tools.types import ExecutionMode, RiskLevel, ToolContext
from app.core.rbac import get_rbac_service

logger = logging.getLogger(__name__)

# Context variable to store the current ToolContext for this async context
# This avoids putting non-serializable objects (AsyncSession) in the state
_current_context: contextvars.ContextVar[ToolContext | None] = contextvars.ContextVar(
    "_current_context", default=None
)


class BackcastSecurityMiddleware(AgentMiddleware):
    """Middleware for applying Backcast security to Deep Agents.

    This class provides security checking by implementing the AgentMiddleware
    interface from langchain.agents.middleware.types.

    Attributes:
        context: ToolContext containing user_role and execution_mode for checks
        tools: List of tools available for execution
    """

    def __init__(self, context: ToolContext, tools: list[Any] | None = None) -> None:
        """Initialize BackcastSecurityMiddleware with context and tools.

        Args:
            context: ToolContext with user_role and execution_mode for checks
            tools: Optional list of tools for permission checking
        """
        super().__init__()
        self.context = context
        self.tools = tools or []

    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Any,
    ) -> ToolMessage:
        """Wrap tool call to check permissions, risk, and inject context.

        Args:
            request: ToolCallRequest containing tool_call information
            handler: Callable to execute the tool

        Returns:
            ToolMessage with result or error

        Note:
            Context is stored in a context variable to avoid including
            non-serializable objects (AsyncSession) in the state.
        """
        tool_call = request.tool_call
        tool_name = tool_call.get("name", "")
        tool_id = tool_call.get("id", "")
        tool_args = dict(tool_call.get("args", {}))

        # 1. Check permissions
        error_message = await self._check_tool_permission(tool_name, tool_args)
        if error_message:
            return ToolMessage(content=error_message, tool_call_id=tool_id)

        # 2. Check risk level (only if permission granted)
        allowed, risk_error = self._check_risk_level(tool_name)
        if not allowed:
            return ToolMessage(
                content=risk_error or "Tool execution not allowed based on risk level",
                tool_call_id=tool_id
            )

        # 3. Store context in context variable for tool to retrieve
        # This avoids putting non-serializable objects (AsyncSession) in the state
        _current_context.set(self.context)

        # Execute tool with original args (context will be retrieved from context variable)
        return await handler(request)

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
            Tools not in the Backcast tools list (e.g., Deep Agents SDK built-in tools)
            are allowed through without Backcast-specific permission checks, as they
            have their own security mechanisms.
        """
        # Find the tool by name in Backcast tools list
        tool = None
        for t in self.tools:
            if t.name == tool_name:
                tool = t
                break

        # If tool is not found in Backcast tools, allow it to pass through
        # This handles external tools like Deep Agents SDK built-in tools (write_todos, task)
        # These tools have their own security and don't need Backcast-specific checks
        if tool is None:
            logger.debug(f"Tool '{tool_name}' not in Backcast tools list, allowing as external tool")
            return None

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

    def _check_risk_level(
        self,
        tool_name: str,
    ) -> tuple[bool, str | None]:
        """Check if a tool is allowed based on execution mode and risk level.

        Args:
            tool_name: Name of the tool to check

        Returns:
            Tuple of (allowed, error_message)

        Note:
            Tools not in the Backcast tools list (e.g., Deep Agents SDK built-in tools)
            are allowed through without Backcast-specific risk checks, as they
            have their own security mechanisms.
        """
        # Find the tool by name in Backcast tools list
        tool = None
        for t in self.tools:
            if t.name == tool_name:
                tool = t
                break

        # If tool is not found in Backcast tools, allow it to pass through
        # This handles external tools like Deep Agents SDK built-in tools (write_todos, task)
        # These tools have their own security and don't need Backcast-specific risk checks
        if tool is None:
            logger.debug(f"Tool '{tool_name}' not in Backcast tools list, allowing as external tool")
            return True, None

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

    def set_tools(self, tools: list[Any]) -> None:
        """Set the tools list for permission checking.

        Args:
            tools: List of BaseTool instances
        """
        self.tools = tools


def get_context() -> ToolContext | None:
    """Get the current ToolContext from the context variable.

    Returns:
        The current ToolContext or None if not set

    Note:
        This function is used by tools to retrieve the context that was
        set by the BackcastSecurityMiddleware. Using a context variable
        avoids putting non-serializable objects (AsyncSession) in the state.
    """
    return _current_context.get()
