"""Backcast security middleware for Deep Agents SDK.

Implements three-tier security:
1. JWT authentication (handled at API layer)
2. RBAC permission checking
3. Risk-based execution modes with InterruptNode integration

Note: This middleware applies security to Backcast tools (decorated with @ai_tool).
External tools (e.g., Deep Agents SDK built-in tools like write_todos, task) are
allowed through without Backcast-specific checks, as they have their own security.
"""

import asyncio
import contextvars
import logging
import time
from typing import Any
from uuid import UUID

from langchain.agents.middleware.types import AgentMiddleware
from langchain_core.messages import ToolMessage
from langgraph.prebuilt.tool_node import ToolCallRequest

from app.ai.graph_cache import get_request_interrupt_node, get_request_tool_context
from app.ai.tools.interrupt_node import InterruptNode
from app.ai.tools.types import ExecutionMode, RiskLevel, ToolContext
from app.core.config import settings
from app.core.rbac import get_rbac_service, set_rbac_session

logger = logging.getLogger(__name__)

# Context variable to store the current ToolContext for this async context
# This avoids putting non-serializable objects (AsyncSession) in the state
_current_context: contextvars.ContextVar[ToolContext | None] = contextvars.ContextVar(
    "_current_context", default=None
)

# Context variable to store the current InterruptNode for this async context
# This allows the middleware to interact with the approval system
_current_interrupt_node: contextvars.ContextVar[InterruptNode | None] = (
    contextvars.ContextVar("_current_interrupt_node", default=None)
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
        self._tools_by_name: dict[str, Any] = {t.name: t for t in self._security_tools}
        self._interrupt_node = interrupt_node
        self._approval_semaphore = asyncio.Semaphore(1)
        self._consecutive_approval_timeouts: int = 0

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

        # Resolve per-request context ONCE (supports cached graphs).
        # ContextVar takes priority over construction-time self.context.
        ctx = get_request_tool_context() or self.context
        interrupt_node = get_request_interrupt_node() or self._interrupt_node

        # Log tool call entry
        tool_call_start = time.time()
        logger.info(
            f"[TOOL_CALL_ENTRY] awrap_tool_call | "
            f"tool_name={tool_name} | "
            f"tool_id={tool_id} | "
            f"arg_keys={list(tool_args.keys())} | "
            f"user_role={ctx.user_role} | "
            f"execution_mode={ctx.execution_mode.value}"
        )

        # 1. Check permissions
        error_message = await self._check_tool_permission(tool_name, tool_args, ctx)
        if error_message:
            return ToolMessage(content=error_message, tool_call_id=tool_id)

        # 2. Check risk level and handle approval if needed (only if permission granted)
        tool_call_dict: dict[str, Any] = dict(tool_call) if tool_call else {}
        try:
            allowed, risk_error = await self._check_risk_level_with_approval(
                tool_name, tool_args, tool_call_dict, handler, ctx, interrupt_node
            )
        except asyncio.CancelledError:
            # Task was cancelled during approval polling
            tool_call_duration_ms = (time.time() - tool_call_start) * 1000
            logger.info(
                f"[TOOL_CALL_EXIT] awrap_tool_call | "
                f"tool_name={tool_name} | "
                f"duration_ms={tool_call_duration_ms:.2f} | "
                f"status=cancelled | "
                f"error=Approval polling cancelled"
            )
            raise

        if not allowed:
            # If not allowed, return error (this handles both risk blocks and rejections)
            error_content = (
                risk_error
                if isinstance(risk_error, str)
                else "Tool execution not allowed"
            )
            tool_call_duration_ms = (time.time() - tool_call_start) * 1000
            logger.info(
                f"[TOOL_CALL_EXIT] awrap_tool_call | "
                f"tool_name={tool_name} | "
                f"duration_ms={tool_call_duration_ms:.2f} | "
                f"status=denied | "
                f"error={error_content[:100]}"
            )
            return ToolMessage(content=error_content, tool_call_id=tool_id)

        # 3. Store context in context variable for tool to retrieve
        # This avoids putting non-serializable objects (AsyncSession) in the state
        _current_context.set(ctx)
        _current_interrupt_node.set(interrupt_node)

        # Execute tool with original args (context will be retrieved from context variable)
        # If approval was handled, the handler may have already been called
        result = risk_error  # If risk_error is a ToolMessage, it's the result

        # Log tool call exit
        tool_call_duration_ms = (time.time() - tool_call_start) * 1000
        if isinstance(result, ToolMessage):
            # Result from approval handling
            logger.info(
                f"[TOOL_CALL_EXIT] awrap_tool_call | "
                f"tool_name={tool_name} | "
                f"duration_ms={tool_call_duration_ms:.2f} | "
                f"status=approved"
            )
            return result

        # Execute the handler
        try:
            final_result = await handler(request)
            logger.info(
                f"[TOOL_CALL_EXIT] awrap_tool_call | "
                f"tool_name={tool_name} | "
                f"duration_ms={tool_call_duration_ms:.2f} | "
                f"status=success"
            )
            return final_result
        except Exception as e:
            logger.info(
                f"[TOOL_CALL_EXIT] awrap_tool_call | "
                f"tool_name={tool_name} | "
                f"duration_ms={tool_call_duration_ms:.2f} | "
                f"status=error | "
                f"error_type={type(e).__name__} | "
                f"error={str(e)}"
            )
            raise

    async def _check_single_permission(
        self,
        rbac_service: Any,
        ctx: ToolContext,
        permission: str,
        project_id: str | None,
        tool_name: str,
    ) -> str | None:
        """Check a single permission for the current context.

        Handles both project-level and global permission checks. When
        project_id is provided, injects the session and uses project-scoped
        RBAC if available, otherwise falls back to global role check.

        Args:
            rbac_service: RBAC service instance for permission checks
            ctx: Resolved ToolContext for the current request
            permission: Permission string to check (e.g. "project:read")
            project_id: Optional project ID for project-level checks
            tool_name: Name of the tool requesting the permission

        Returns:
            None if permitted, error message string if denied
        """
        if project_id is not None:
            set_rbac_session(ctx.session)

            if not hasattr(rbac_service, "has_project_access"):
                # Fallback to global check when project access not supported
                if not rbac_service.has_permission(ctx.user_role, permission):
                    return (
                        f"Permission denied: {permission} required "
                        f"(user_role: {ctx.user_role}, tool: {tool_name})"
                    )
                return None

            # Project-level access check
            try:
                project_uuid = (
                    UUID(project_id) if isinstance(project_id, str) else project_id
                )
                user_uuid = UUID(ctx.user_id)

                has_access = await rbac_service.has_project_access(
                    user_id=user_uuid,
                    user_role=ctx.user_role,
                    project_id=project_uuid,
                    required_permission=permission,
                )

                if not has_access:
                    return (
                        f"Permission denied: {permission} required "
                        f"for project {project_id} "
                        f"(user_role: {ctx.user_role}, tool: {tool_name})"
                    )
            except (ValueError, TypeError):
                return (
                    f"Permission denied: Invalid project_id format (tool: {tool_name})"
                )
        else:
            # Global permission check (no project context, no session injection needed)
            if not rbac_service.has_permission(ctx.user_role, permission):
                return (
                    f"Permission denied: {permission} required "
                    f"(user_role: {ctx.user_role}, tool: {tool_name})"
                )

        return None

    async def _check_tool_permission(
        self,
        tool_name: str,
        tool_args: dict[str, Any],
        ctx: ToolContext,
    ) -> str | None:
        """Check if user has permission to execute a tool.

        Context: Called by BackcastSecurityMiddleware.awrap_tool_call before
        risk-level checks to enforce RBAC permissions on Backcast-specific tools.

        Args:
            tool_name: Name of the tool to check
            tool_args: Arguments passed to the tool (may contain project_id)
            ctx: Resolved ToolContext for the current request

        Returns:
            None if permitted, error message string if denied

        Note:
            Tools not in the Backcast tools list (e.g., Deep Agents SDK built-in tools)
            are allowed through without Backcast-specific permission checks, as they
            have their own security mechanisms.
        """
        # Find the tool by name via indexed lookup
        tool = self._tools_by_name.get(tool_name)

        # If tool is not found in Backcast tools, allow it to pass through
        # This handles external tools like Deep Agents SDK built-in tools (write_todos, task)
        # These tools have their own security and don't need Backcast-specific checks
        if tool is None:
            logger.debug(
                f"Tool '{tool_name}' not in Backcast tools list, allowing as external tool"
            )
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

        # Check all permissions using unified method
        for permission in metadata.permissions:
            error = await self._check_single_permission(
                rbac_service=rbac_service,
                ctx=ctx,
                permission=permission,
                project_id=project_id,
                tool_name=tool_name,
            )
            if error:
                return error

        return None

    def _check_risk_level(
        self,
        tool_name: str,
        ctx: ToolContext,
    ) -> tuple[bool, str | None]:
        """Check if a tool is allowed based on execution mode and risk level.

        Context: Called by BackcastSecurityMiddleware._check_risk_level_with_approval
        to determine whether a tool's risk level permits execution under the current
        execution mode (SAFE, STANDARD, or EXPERT).

        Args:
            tool_name: Name of the tool to check
            ctx: Resolved ToolContext for the current request

        Returns:
            Tuple of (allowed, error_message)

        Note:
            Tools not in the Backcast tools list (e.g., Deep Agents SDK built-in tools)
            are allowed through without Backcast-specific risk checks, as they
            have their own security mechanisms.
        """
        # Find the tool by name via indexed lookup
        tool = self._tools_by_name.get(tool_name)

        # If tool is not found in Backcast tools, allow it to pass through
        # This handles external tools like Deep Agents SDK built-in tools (write_todos, task)
        # These tools have their own security and don't need Backcast-specific risk checks
        if tool is None:
            logger.debug(
                f"Tool '{tool_name}' not in Backcast tools list, allowing as external tool"
            )
            return True, None

        # Get tool metadata
        metadata = getattr(tool, "_tool_metadata", None)
        if metadata is None:
            # No metadata means no risk level - assume high (safe default)
            risk_level = RiskLevel.HIGH
        else:
            risk_level = metadata.risk_level

        # Check based on execution mode
        mode = ctx.execution_mode

        # DEBUG: Log execution mode and risk level
        logger.info(
            f"RISK_CHECK: tool='{tool_name}', mode={mode.value}, risk_level={risk_level.value}"
        )

        if mode == ExecutionMode.SAFE:
            if risk_level != RiskLevel.LOW:
                logger.warning(
                    f"BLOCKING tool '{tool_name}' in SAFE mode (risk_level={risk_level.value})"
                )
                return (
                    False,
                    f"Tool '{tool_name}' requires {risk_level.value} risk level. "
                    f"Safe mode only allows low-risk tools.",
                )
        elif mode == ExecutionMode.STANDARD:
            if risk_level == RiskLevel.CRITICAL:
                return (
                    False,
                    f"Tool '{tool_name}' has critical risk level. "
                    f"Standard mode blocks critical tools. Switch to expert mode.",
                )
        # Expert mode allows all tools

        return True, None

    async def _poll_for_approval(
        self,
        approval_id: str,
        tool_name: str,
        interrupt_node: InterruptNode,
        max_wait_time: float | None = None,
    ) -> tuple[bool, str | None]:
        """Poll for user approval response with timeout and heartbeat.

        Context: Called by BackcastSecurityMiddleware._check_risk_level_with_approval
        after sending an approval request. Manages the polling loop including
        cancellation checks, WebSocket liveness, and periodic heartbeats.

        Args:
            approval_id: Unique identifier for the approval request
            tool_name: Name of the tool awaiting approval (for logging)
            interrupt_node: InterruptNode instance for checking approval status
            max_wait_time: Maximum seconds to wait for user response.
                Defaults to ``settings.AI_APPROVAL_TIMEOUT_SECONDS``.

        Returns:
            Tuple of (approved, error_message)
            - (True, None) if user approved
            - (False, error_string) if rejected, timed out, or connection lost

        Raises:
            asyncio.CancelledError: If the task is cancelled during polling
        """
        if max_wait_time is None:
            max_wait_time = settings.AI_APPROVAL_TIMEOUT_SECONDS
        poll_interval = settings.AI_APPROVAL_POLL_INTERVAL_MS / 1000.0
        heartbeat_interval = settings.AI_APPROVAL_HEARTBEAT_INTERVAL_SECONDS
        last_heartbeat_time = time.time()
        polling_start_time = time.time()

        logger.info(
            f"[APPROVAL_POLLING_START] _poll_for_approval | "
            f"approval_id={approval_id} | "
            f"tool_name={tool_name} | "
            f"max_wait_time={max_wait_time}s"
        )

        try:
            while (time.time() - polling_start_time) < max_wait_time:
                # Check if task was cancelled (e.g., WebSocket disconnected)
                current_task = asyncio.current_task()
                if current_task is not None and current_task.cancelled():
                    waited_seconds = time.time() - polling_start_time
                    logger.info(
                        f"[APPROVAL_POLLING_CANCELLED] _poll_for_approval | "
                        f"approval_id={approval_id} | "
                        f"tool_name={tool_name} | "
                        f"waited_seconds={waited_seconds:.2f}"
                    )
                    raise asyncio.CancelledError()

                # Check if WebSocket is still connected - user cannot approve if disconnected
                if (
                    interrupt_node.websocket
                    and not interrupt_node._is_websocket_connected(
                        interrupt_node.websocket
                    )
                ):
                    waited_seconds = time.time() - polling_start_time
                    logger.warning(
                        f"[APPROVAL_WEBSOCKET_DISCONNECTED] _poll_for_approval | "
                        f"approval_id={approval_id} | "
                        f"tool_name={tool_name} | "
                        f"waited_seconds={waited_seconds:.2f}"
                    )
                    return (
                        False,
                        "WebSocket connection lost. Approval request cancelled. Please reconnect and try again.",
                    )

                await asyncio.sleep(poll_interval)

                # Calculate actual elapsed wall-clock time
                elapsed_seconds = time.time() - polling_start_time

                # Prevents connection timeout due to inactivity
                if time.time() - last_heartbeat_time >= heartbeat_interval:
                    remaining = max_wait_time - elapsed_seconds
                    await interrupt_node._send_heartbeat(
                        approval_id=approval_id,
                        elapsed_seconds=elapsed_seconds,
                        remaining_seconds=remaining,
                    )
                    last_heartbeat_time = time.time()

                approved, approval_error = interrupt_node._check_approval(approval_id)

                if approved:
                    # User approved - clean up and let normal handler execute the tool
                    wait_duration = time.time() - polling_start_time
                    logger.info(
                        f"[APPROVAL_GRANTED] _poll_for_approval | "
                        f"approval_id={approval_id} | "
                        f"tool_name={tool_name} | "
                        f"wait_seconds={wait_duration:.2f}"
                    )
                    # Clean up approval state
                    if approval_id in interrupt_node.pending_approvals:
                        del interrupt_node.pending_approvals[approval_id]
                    if approval_id in interrupt_node.interrupt_state:
                        del interrupt_node.interrupt_state[approval_id]
                    return True, None

                if approval_error is not None:
                    # User rejected, expired, or not found
                    logger.info(
                        f"[APPROVAL_ERROR] _poll_for_approval | "
                        f"approval_id={approval_id} | "
                        f"tool_name={tool_name} | "
                        f"error={approval_error}"
                    )
                    return False, approval_error
                # If approval_error is None, still waiting - continue polling

            # Timeout reached
            wait_duration = time.time() - polling_start_time
            logger.info(
                f"[APPROVAL_TIMEOUT] _poll_for_approval | "
                f"approval_id={approval_id} | "
                f"tool_name={tool_name} | "
                f"waited_seconds={wait_duration:.2f} | "
                f"max_wait_time={max_wait_time}s"
            )
            return False, "Approval request timed out. Please try again."

        except asyncio.CancelledError:
            # Task was cancelled (e.g., WebSocket disconnected)
            wait_duration = time.time() - polling_start_time
            logger.info(
                f"[APPROVAL_POLLING_CANCELLED] _poll_for_approval | "
                f"approval_id={approval_id} | "
                f"tool_name={tool_name} | "
                f"waited_seconds={wait_duration:.2f}"
            )
            # Re-raise to allow proper cleanup
            raise

    async def _check_risk_level_with_approval(
        self,
        tool_name: str,
        tool_args: dict[str, Any],
        tool_call: dict[str, Any],
        handler: Any,
        ctx: ToolContext,
        interrupt_node: InterruptNode | None,
    ) -> tuple[bool, str | None | ToolMessage]:
        """Check risk level and handle approval for HIGH tools in standard mode.

        Context: Called by BackcastSecurityMiddleware.awrap_tool_call after
        permission checks pass. Manages the human-in-the-loop approval polling
        loop for tools rated HIGH or CRITICAL in STANDARD execution mode.

        Args:
            tool_name: Name of the tool to check
            tool_args: Arguments passed to the tool
            tool_call: Tool call dictionary from request
            handler: Callable to execute the tool
            ctx: Resolved ToolContext for the current request
            interrupt_node: Resolved InterruptNode for approval handling

        Returns:
            Tuple of (allowed, error_message_or_result)
            - allowed: True if tool can proceed, False otherwise
            - error_message_or_result: None if allowed, error message if denied,
                                       or ToolMessage if execution completed

        Note:
            HIGH risk tools in STANDARD mode require approval. CRITICAL tools are blocked entirely.
            Uses InterruptNode to send approval requests via WebSocket.
            Waits for user approval with polling (max 60 seconds).
        """
        # First, do the basic risk check
        allowed, error_message = self._check_risk_level(tool_name, ctx)
        if not allowed:
            return False, error_message

        # Find the tool by name via indexed lookup
        tool = self._tools_by_name.get(tool_name)

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

        # Check if we need approval (HIGH in STANDARD mode)
        mode = ctx.execution_mode
        needs_approval = (
            risk_level >= RiskLevel.HIGH
            and mode == ExecutionMode.STANDARD
            and interrupt_node is not None
        )

        if not needs_approval:
            return True, None

        if interrupt_node is None:
            logger.error("InterruptNode is None but approval is needed")
            return False, "Approval system unavailable"

        # Send approval request via InterruptNode
        logger.info(
            f"APPROVAL_NEEDED: tool='{tool_name}', risk_level={risk_level.value}"
        )

        # Serialize approval requests — only one at a time
        async with self._approval_semaphore:
            approval_id = await interrupt_node._send_approval_request(
                tool_name=tool_name,
                tool_args=tool_args,
                risk_level=risk_level,
                tool_call=tool_call,
            )

            # Poll for approval response
            approved, approval_error = await self._poll_for_approval(
                approval_id=approval_id,
                tool_name=tool_name,
                interrupt_node=interrupt_node,
            )

        if not approved:
            if approval_error and "timed out" in approval_error:
                self._consecutive_approval_timeouts += 1
                if self._consecutive_approval_timeouts >= 3:
                    logger.warning(
                        f"Approval timed out {self._consecutive_approval_timeouts} "
                        f"consecutive times for tool '{tool_name}'. Failing permanently."
                    )
                    return False, (
                        f"Approval timed out {self._consecutive_approval_timeouts} consecutive times. "
                        f"Please try again later."
                    )
            return False, approval_error

        self._consecutive_approval_timeouts = 0
        return True, None

    def set_tools(self, tools: list[Any]) -> None:
        """Set the tools list for permission checking.

        Args:
            tools: List of BaseTool instances
        """
        self._security_tools = tools
        self._tools_by_name = {t.name: t for t in tools}

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
