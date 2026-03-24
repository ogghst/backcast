"""Backcast security middleware for Deep Agents SDK.

Implements three-tier security:
1. JWT authentication (handled at API layer)
2. RBAC permission checking
3. Risk-based execution modes with InterruptNode integration

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

from app.ai.tools.interrupt_node import InterruptNode
from app.ai.tools.types import ExecutionMode, RiskLevel, ToolContext
from app.core.rbac import get_rbac_service

logger = logging.getLogger(__name__)

# Context variable to store the current ToolContext for this async context
# This avoids putting non-serializable objects (AsyncSession) in the state
_current_context: contextvars.ContextVar[ToolContext | None] = contextvars.ContextVar(
    "_current_context", default=None
)

# Context variable to store the current InterruptNode for this async context
# This allows the middleware to interact with the approval system
_current_interrupt_node: contextvars.ContextVar[InterruptNode | None] = contextvars.ContextVar(
    "_current_interrupt_node", default=None
)


class BackcastSecurityMiddleware(AgentMiddleware):
    """Middleware for applying Backcast security to Deep Agents.

    This class provides security checking by implementing the AgentMiddleware
    interface from langchain.agents.middleware.types.

    Attributes:
        context: ToolContext containing user_role and execution_mode for checks
        tools: List of tools available for execution
    """

    def __init__(
        self,
        context: ToolContext,
        tools: list[Any] | None = None,
        interrupt_node: InterruptNode | None = None,
    ) -> None:
        """Initialize BackcastSecurityMiddleware with context and tools.

        Args:
            context: ToolContext with user_role and execution_mode for checks
            tools: Optional list of tools for permission checking
            interrupt_node: Optional InterruptNode for handling approvals
        """
        super().__init__()
        self.context = context
        # Use private attribute to avoid exposing tools to LangChain's create_agent
        # which collects tools from ALL middleware via getattr(m, "tools", [])
        self._security_tools = tools or []
        self._interrupt_node = interrupt_node

    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Any,
    ) -> ToolMessage:
        """Wrap tool call to check permissions, risk, and handle approvals.

        Args:
            request: ToolCallRequest containing tool_call information
            handler: Callable to execute the tool

        Returns:
            ToolMessage with result or error

        Note:
            Context is stored in a context variable to avoid including
            non-serializable objects (AsyncSession) in the state.
            Approval requests are sent via InterruptNode if available.
        """
        tool_call = request.tool_call
        tool_name = tool_call.get("name", "")
        tool_id = tool_call.get("id", "")
        tool_args = dict(tool_call.get("args", {}))

        # 1. Check permissions
        error_message = await self._check_tool_permission(tool_name, tool_args)
        if error_message:
            return ToolMessage(content=error_message, tool_call_id=tool_id)

        # 2. Check risk level and handle approval if needed (only if permission granted)
        tool_call_dict: dict[str, Any] = dict(tool_call) if tool_call else {}
        allowed, risk_error = await self._check_risk_level_with_approval(
            tool_name, tool_args, tool_call_dict, handler
        )
        if not allowed:
            # If not allowed, return error (this handles both risk blocks and rejections)
            error_content = risk_error if isinstance(risk_error, str) else "Tool execution not allowed"
            return ToolMessage(
                content=error_content,
                tool_call_id=tool_id
            )

        # 3. Store context in context variable for tool to retrieve
        # This avoids putting non-serializable objects (AsyncSession) in the state
        _current_context.set(self.context)
        _current_interrupt_node.set(self._interrupt_node)

        # Execute tool with original args (context will be retrieved from context variable)
        # If approval was handled, the handler may have already been called
        result = risk_error  # If risk_error is a ToolMessage, it's the result
        if isinstance(result, ToolMessage):
            return result

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
        for t in self._security_tools:
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
        for t in self._security_tools:
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

        # DEBUG: Log execution mode and risk level
        logger.info(f"RISK_CHECK: tool='{tool_name}', mode={mode.value}, risk_level={risk_level.value}")

        if mode == ExecutionMode.SAFE:
            if risk_level != RiskLevel.LOW:
                logger.warning(f"BLOCKING tool '{tool_name}' in SAFE mode (risk_level={risk_level.value})")
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

    async def _check_risk_level_with_approval(
        self,
        tool_name: str,
        tool_args: dict[str, Any],
        tool_call: dict[str, Any],
        handler: Any,
    ) -> tuple[bool, str | None | ToolMessage]:
        """Check risk level and handle approval for HIGH/CRITICAL tools in standard mode.

        Args:
            tool_name: Name of the tool to check
            tool_args: Arguments passed to the tool
            tool_call: Tool call dictionary from request
            handler: Callable to execute the tool

        Returns:
            Tuple of (allowed, error_message_or_result)
            - allowed: True if tool can proceed, False otherwise
            - error_message_or_result: None if allowed, error message if denied,
                                       or ToolMessage if execution completed

        Note:
            HIGH and CRITICAL risk tools in STANDARD mode require approval.
            Uses InterruptNode to send approval requests via WebSocket.
            Waits for user approval with polling (max 30 seconds).
        """
        # First, do the basic risk check
        allowed, error_message = self._check_risk_level(tool_name)
        if not allowed:
            return False, error_message

        # Find the tool by name in Backcast tools list
        tool = None
        for t in self._security_tools:
            if t.name == tool_name:
                tool = t
                break

        # If tool is not found in Backcast tools, allow it to pass through
        if tool is None:
            return True, None

        # Get tool metadata
        metadata = getattr(tool, "_tool_metadata", None)
        if metadata is None:
            # No metadata means no risk level - assume high (safe default)
            risk_level = RiskLevel.HIGH
        else:
            risk_level = metadata.risk_level

        # Check if we need approval (HIGH/CRITICAL in STANDARD mode)
        mode = self.context.execution_mode
        needs_approval = (
            risk_level >= RiskLevel.HIGH and
            mode == ExecutionMode.STANDARD and
            self._interrupt_node is not None
        )

        if needs_approval:
            logger.info(f"APPROVAL_NEEDED: tool='{tool_name}', risk_level={risk_level.value}")

            # Ensure interrupt_node is not None
            if self._interrupt_node is None:
                logger.error("InterruptNode is None but approval is needed")
                return False, "Approval system unavailable"

            # Send approval request via InterruptNode
            approval_id = await self._interrupt_node._send_approval_request(
                tool_name=tool_name,
                tool_args=tool_args,
                risk_level=risk_level,
                tool_call=tool_call,
                execute=handler,
            )

            # Poll for approval response with timeout
            # Give user up to 30 seconds to respond
            import asyncio

            max_wait_time = 30.0  # seconds
            poll_interval = 0.2  # 200ms
            heartbeat_interval = 5.0  # Send heartbeat every 5 seconds
            total_waited = 0.0
            last_heartbeat = 0.0

            logger.info(f"POLLING_FOR_APPROVAL: approval_id={approval_id}, tool='{tool_name}'")

            while total_waited < max_wait_time:
                await asyncio.sleep(poll_interval)
                total_waited += poll_interval

                # Send heartbeat to keep WebSocket connection alive
                # Prevents connection timeout due to inactivity (typically 20-30 seconds)
                if total_waited - last_heartbeat >= heartbeat_interval:
                    remaining = max_wait_time - total_waited
                    await self._interrupt_node._send_heartbeat(
                        approval_id=approval_id,
                        elapsed_seconds=total_waited,
                        remaining_seconds=remaining,
                    )
                    last_heartbeat = total_waited

                approved, approval_error = self._interrupt_node._check_approval(approval_id)

                if approved:
                    # User approved - execute tool
                    logger.info(f"APPROVAL_GRANTED: tool='{tool_name}', executing via InterruptNode")
                    result = await self._interrupt_node.execute_after_approval(approval_id)

                    if result is None:
                        return False, "Tool execution failed after approval"

                    # Return the result as a ToolMessage
                    return True, result
                elif approval_error is not None:
                    # User rejected, expired, or not found
                    logger.warning(f"APPROVAL_ERROR: tool='{tool_name}', error={approval_error}")
                    return False, approval_error
                # If approval_error is None, still waiting - continue polling

            # Timeout reached
            logger.warning(f"APPROVAL_TIMEOUT: tool='{tool_name}', waited {max_wait_time}s")
            return False, f"Approval request timed out after {max_wait_time} seconds. Please try again."

        return True, None

    def set_tools(self, tools: list[Any]) -> None:
        """Set the tools list for permission checking.

        Args:
            tools: List of BaseTool instances
        """
        self._security_tools = tools

    def set_interrupt_node(self, interrupt_node: InterruptNode | None) -> None:
        """Set the InterruptNode for approval handling.

        Args:
            interrupt_node: InterruptNode instance for handling approvals
        """
        self._interrupt_node = interrupt_node


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


def get_interrupt_node() -> InterruptNode | None:
    """Get the current InterruptNode from the context variable.

    Returns:
        The current InterruptNode or None if not set

    Note:
        This function is used to retrieve the InterruptNode that was
        set by the BackcastSecurityMiddleware for approval handling.
    """
    return _current_interrupt_node.get()
