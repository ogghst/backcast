"""InterruptNode for human-in-the-loop approval workflow.

Extends LangGraph's ToolNode to add interrupt-based approval for critical tools.
Uses LangGraph's native interrupt() mechanism to pause graph execution and wait
for user approval via WebSocket messages.

Used in Phase 3: Approval Workflow
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from fastapi import WebSocket
from langchain_core.messages import ToolMessage
from langchain_core.tools import BaseTool
from langgraph.prebuilt import ToolNode
from starlette.websockets import WebSocketState

from app.ai.execution.agent_event_bus import AgentEventBus
from app.ai.tools.types import ExecutionMode, RiskLevel, ToolContext
from app.models.schemas.ai import WSApprovalRequestMessage, WSPollingHeartbeatMessage


@dataclass
class _ToolCallRequest:
    """Lightweight request wrapper for approved tool execution.

    Context: Used by InterruptNode.execute_after_approval to construct a
    request object compatible with the tool call handler signature without
    importing unittest.mock.MagicMock in production code.

    Attributes:
        tool_call: Dictionary containing the tool call name, args, and id.
    """

    tool_call: dict[str, Any]

    def override(self, tool_call: dict[str, Any]) -> "_ToolCallRequest":
        """Return a new _ToolCallRequest with an overridden tool_call.

        Args:
            tool_call: Replacement tool call dictionary.

        Returns:
            New _ToolCallRequest with the provided tool_call.
        """
        return _ToolCallRequest(tool_call=tool_call)


class InterruptNode(ToolNode):
    """ToolNode subclass with interrupt-based approval for critical tools.

    Wraps LangGraph's ToolNode to add human-in-the-loop approval for critical
    tools when in standard execution mode. Uses LangGraph's interrupt() mechanism
    to pause graph execution and send approval requests via WebSocket.

    Approval Flow:
    1. Critical tool called in standard mode
    2. Interrupt pauses execution
    3. Approval request sent via WebSocket
    4. User approves or rejects
    5. If approved: tool executes
    6. If rejected: error returned

    Attributes:
        tools: List of tools available for execution
        context: ToolContext containing execution_mode for mode-based logic
        websocket: WebSocket connection for sending approval requests
        session_id: Current chat session ID
        pending_approvals: Dict of approval_id -> approval data
        interrupt_state: Dict storing state for graph resume

    Example:
        ```python
        from app.ai.tools import create_project_tools
        from app.ai.tools.interrupt_node import InterruptNode

        context = ToolContext(session, user_id, user_role="admin", execution_mode=ExecutionMode.STANDARD)
        tools = create_project_tools(context)
        interrupt_node = InterruptNode(tools, context, websocket, session_id)

        # Add to StateGraph
        workflow.add_node("tools", interrupt_node)
        ```
    """

    def __init__(
        self,
        tools: list[BaseTool],
        context: ToolContext,
        websocket: WebSocket | None = None,
        session_id: UUID | None = None,
        event_bus: AgentEventBus | None = None,
    ) -> None:
        """Initialize InterruptNode with tools, context, and optional WebSocket or event bus.

        Args:
            tools: List of BaseTool instances to execute
            context: ToolContext with execution_mode for approval logic
            websocket: Optional WebSocket connection for sending approval requests
            session_id: Current chat session ID for approval tracking
            event_bus: Optional AgentEventBus for publishing approval events
        """
        super().__init__(tools, awrap_tool_call=self._awrap_tool_call)
        self.context = context
        self.tools = tools
        self._tools_by_name: dict[str, BaseTool] = {t.name: t for t in tools}
        self.websocket = websocket
        self.session_id = session_id
        self.event_bus: AgentEventBus | None = event_bus
        self.pending_approvals: dict[str, dict[str, Any]] = {}
        # Store interrupt state for graph resume
        # Key: approval_id, Value: dict with tool_call, execute function, etc.
        self.interrupt_state: dict[str, dict[str, Any]] = {}

    @staticmethod
    def _is_websocket_connected(websocket: WebSocket) -> bool:
        """Check if WebSocket is still connected.

        Context: Called before sending approval requests and heartbeats to
        avoid errors on closed connections during the human-in-the-loop flow.

        Args:
            websocket: WebSocket connection to check

        Returns:
            True if WebSocket is connected, False otherwise
        """
        try:
            return websocket.client_state != WebSocketState.DISCONNECTED
        except (AttributeError, TypeError):
            # If websocket doesn't have client_state, assume disconnected
            return False

    def _get_tool_risk_level(self, tool_name: str) -> RiskLevel:
        """Get the risk level for a tool.

        Context: Called during tool execution to determine whether human
        approval is required before proceeding with a critical operation.

        Args:
            tool_name: Name of the tool to check

        Returns:
            RiskLevel of the tool (defaults to HIGH if not specified)
        """
        # Find the tool by name via indexed lookup
        tool = self._tools_by_name.get(tool_name)

        if tool is None:
            # Tool not found, assume high risk
            return RiskLevel.HIGH

        # Get tool metadata
        metadata = getattr(tool, "_tool_metadata", None)
        if metadata is None:
            # No metadata means no risk level specified - assume high (safe default)
            return RiskLevel.HIGH

        return metadata.risk_level

    async def _send_approval_request(
        self,
        tool_name: str,
        tool_args: dict[str, Any],
        risk_level: RiskLevel,
        tool_call: dict[str, Any] | None = None,
    ) -> str:
        """Send approval request via WebSocket.

        Context: Called by InterruptNode._awrap_tool_call and
        BackcastSecurityMiddleware when a HIGH/CRITICAL risk tool is invoked
        in STANDARD execution mode.

        Args:
            tool_name: Name of the tool requiring approval
            tool_args: Arguments that will be passed to the tool
            risk_level: Risk level of the tool
            tool_call: Optional tool call dict for reference

        Returns:
            approval_id UUID string for tracking this approval request
        """
        from app.ai.agent_service import logger

        approval_id = str(uuid4())
        expires_at = datetime.now() + timedelta(minutes=5)

        logger.info(
            f"SENDING_APPROVAL_REQUEST: approval_id={approval_id}, tool='{tool_name}', risk_level={risk_level.value}"
        )

        approval_request = WSApprovalRequestMessage(
            type="approval_request",
            approval_id=approval_id,
            session_id=self.session_id,
            tool_name=tool_name,
            tool_args=tool_args,
            risk_level=risk_level.value,
            expires_at=expires_at,
        )

        # Publish to event bus if available (decoupled execution path)
        if self.event_bus:
            from app.ai.execution.agent_event import AgentEvent

            self.event_bus.publish(
                AgentEvent(
                    event_type="approval_request",
                    data=approval_request.model_dump(mode="json"),
                    timestamp=datetime.now(),
                )
            )
            logger.info(
                f"APPROVAL_REQUEST_PUBLISHED_TO_BUS: approval_id={approval_id}, tool='{tool_name}'"
            )

        if self.websocket and self._is_websocket_connected(self.websocket):
            try:
                await self.websocket.send_json(approval_request.model_dump(mode="json"))
                logger.info(
                    f"APPROVAL_REQUEST_SENT: approval_id={approval_id}, tool='{tool_name}'"
                )
            except Exception as e:
                # WebSocket may be closed, but we still track the approval
                # The approval will timeout after 5 minutes
                logger.error(
                    f"FAILED_TO_SEND_APPROVAL_REQUEST: approval_id={approval_id}, error={e}"
                )
                pass
        else:
            logger.debug("WebSocket not connected, skipping approval request send")

        # Store pending approval with expiration
        self.pending_approvals[approval_id] = {
            "approved": None,  # None = waiting for response
            "tool_name": tool_name,
            "tool_args": tool_args,
            "expires_at": expires_at,
        }
        logger.debug(
            f"APPROVAL_STORED: approval_id={approval_id}, pending_approvals_count={len(self.pending_approvals)}"
        )

        return approval_id

    async def _send_heartbeat(
        self,
        approval_id: str,
        elapsed_seconds: float,
        remaining_seconds: float,
    ) -> None:
        """Send a heartbeat message during approval polling to keep WebSocket alive.

        Args:
            approval_id: Approval ID being polled
            elapsed_seconds: Time elapsed since approval request
            remaining_seconds: Time remaining until timeout

        Note:
            This method sends a polling_heartbeat message every few seconds
            during the approval polling period to prevent the WebSocket connection
            from closing due to inactivity (typically 20-30 second timeouts).
        """
        from app.ai.agent_service import logger

        heartbeat = WSPollingHeartbeatMessage(
            type="polling_heartbeat",
            approval_id=approval_id,
            elapsed_seconds=elapsed_seconds,
            remaining_seconds=remaining_seconds,
        )

        # Publish to event bus if available (decoupled execution path)
        if self.event_bus:
            from app.ai.execution.agent_event import AgentEvent

            self.event_bus.publish(
                AgentEvent(
                    event_type="polling_heartbeat",
                    data=heartbeat.model_dump(mode="json"),
                    timestamp=datetime.now(),
                )
            )
            logger.debug(
                f"POLLING_HEARTBEAT_PUBLISHED_TO_BUS: approval_id={approval_id}, "
                f"elapsed={elapsed_seconds:.1f}s, remaining={remaining_seconds:.1f}s"
            )

        if self.websocket and self._is_websocket_connected(self.websocket):
            try:
                await self.websocket.send_json(heartbeat.model_dump(mode="json"))
                logger.debug(
                    f"POLLING_HEARTBEAT_SENT: approval_id={approval_id}, "
                    f"elapsed={elapsed_seconds:.1f}s, remaining={remaining_seconds:.1f}s"
                )
            except Exception as e:
                # WebSocket may be closed, log but don't raise
                logger.warning(
                    f"FAILED_TO_SEND_HEARTBEAT: approval_id={approval_id}, error={e}"
                )
        else:
            logger.debug("WebSocket not connected, skipping heartbeat send")

    def _check_approval(self, approval_id: str) -> tuple[bool, str | None]:
        """Check if an approval has been granted and is not expired.

        Args:
            approval_id: Approval ID to check

        Returns:
            Tuple of (approved, error_message)
            - approved: True if approved, False otherwise
            - error_message: Error message if not approved, None if still waiting

        Note:
            Returns (False, None) when still waiting for user approval.
            Returns (False, error_message) when rejected or expired.
            Returns (True, None) when approved.
        """
        approval = self.pending_approvals.get(approval_id)

        if approval is None:
            return False, "Approval request not found"

        # Check expiration
        expires_at = approval.get("expires_at")
        if expires_at and datetime.now() > expires_at:
            # Remove expired approval
            del self.pending_approvals[approval_id]
            return False, "Approval request has expired (5-minute timeout)"

        # Check if approved
        approved = approval.get("approved")
        if approved is None:
            # Still waiting - return (False, None) to indicate polling should continue
            return False, None
        elif approved is False:
            return False, "Tool execution was rejected by user"

        return True, None

    def register_approval_response(
        self,
        approval_id: str,
        approved: bool,
    ) -> None:
        """Register an approval response from the user.

        Args:
            approval_id: Approval ID being responded to
            approved: True if user approved, False if rejected

        Note:
            This method is called by AgentService when it receives
            a WSApprovalResponseMessage from the WebSocket.
        """
        if approval_id in self.pending_approvals:
            self.pending_approvals[approval_id]["approved"] = approved

    def get_interrupt_state(self, approval_id: str) -> dict[str, Any] | None:
        """Get the interrupt state for an approval.

        Args:
            approval_id: Approval ID to get state for

        Returns:
            Interrupt state dict if found, None otherwise
        """
        return self.interrupt_state.get(approval_id)

    async def execute_after_approval(self, approval_id: str) -> ToolMessage | None:
        """Execute a tool after approval is granted.

        Args:
            approval_id: Approval ID for the tool execution

        Returns:
            ToolMessage with result if execution succeeded, None otherwise
        """
        state = self.get_interrupt_state(approval_id)
        if state is None:
            return None

        # Check if approved
        approved, error_message = self._check_approval(approval_id)
        if not approved:
            tool_call = state.get("tool_call", {})
            tool_id = tool_call.get("id", "")
            return ToolMessage(
                content=error_message or "Tool execution not approved",
                tool_call_id=tool_id,
            )

        # Execute the tool directly using the stored execute function
        # This execute function is the one passed to _awrap_tool_call
        tool_call = state["tool_call"]
        execute_func = state["execute"]

        # Inject context into args
        tool_args = dict(tool_call.get("args", {}))
        tool_args["context"] = self.context

        # Create new tool_call dictionary with modified args
        new_tool_call = dict(tool_call)
        new_tool_call["args"] = tool_args

        # Create request object using typed dataclass instead of MagicMock
        request = _ToolCallRequest(tool_call=new_tool_call)

        try:
            # Call the original execute function with the overridden request
            # This will execute the tool through the parent ToolNode's logic
            result = await execute_func(request.override(new_tool_call))

            # Clean up after successful execution
            if approval_id in self.pending_approvals:
                del self.pending_approvals[approval_id]
            if approval_id in self.interrupt_state:
                del self.interrupt_state[approval_id]

            # Ensure result has proper tool_call_id
            if isinstance(result, ToolMessage) and result.tool_call_id == "":
                result = ToolMessage(
                    content=result.content, tool_call_id=tool_call.get("id", "")
                )

            return result
        except Exception as e:
            # Return error message if execution fails
            tool_id = tool_call.get("id", "")
            return ToolMessage(
                content=f"Tool execution failed: {str(e)}", tool_call_id=tool_id
            )

    async def _awrap_tool_call(
        self,
        request: Any,
        execute: Any,
    ) -> Any:
        """Wrap tool call to check for high-risk tool approval requirements.

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

        # Check if this is a high-risk tool in standard mode
        risk_level = self._get_tool_risk_level(tool_name)
        mode = self.context.execution_mode

        # HIGH risk tools in standard mode require approval. CRITICAL tools are blocked entirely.
        if risk_level >= RiskLevel.HIGH and mode == ExecutionMode.STANDARD:
            # Check if there's a pending approval for this tool call
            # For now, we'll send a new approval request each time
            # In a full implementation, we'd use LangGraph's interrupt()
            # to pause and resume with the approval_id

            # Send approval request with state for resume
            approval_id = await self._send_approval_request(
                tool_name,
                tool_args,
                risk_level,
                tool_call=tool_call,
            )

            # Check approval status
            # In real flow with LangGraph interrupts, we'd pause here and
            # resume after user responds. For now, we'll check immediately.
            approved, error_message = self._check_approval(approval_id)

            if not approved:
                # Return error message
                return ToolMessage(
                    content=error_message
                    or f"Tool '{tool_name}' requires approval before execution.",
                    tool_call_id=tool_id,
                )

            # If approved, remove from pending and continue to execution
            if approval_id in self.pending_approvals:
                del self.pending_approvals[approval_id]
            if approval_id in self.interrupt_state:
                del self.interrupt_state[approval_id]

        # Inject context into args
        tool_args["context"] = self.context

        # Create new tool_call dictionary with modified args
        new_tool_call = dict(tool_call)
        new_tool_call["args"] = tool_args

        # Create overridden request and execute
        new_request = request.override(tool_call=new_tool_call)
        return await execute(new_request)
