"""Approval audit logging for AI tool execution.

Tracks all tool executions and approval requests with timestamps,
user decisions, and outcomes for compliance and debugging.

Used in Phase 3: Approval Workflow
"""

import json
import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from app.ai.tools.types import ExecutionMode, RiskLevel

logger = logging.getLogger(__name__)


class ApprovalAuditLogger:
    """Logger for tracking tool executions and approvals.

    Provides structured audit logging for:
    - Tool execution attempts
    - Approval requests sent
    - User approval decisions
    - Tool execution results
    - Timeouts and errors

    Attributes:
        session_id: Chat session ID for grouping related events
        user_id: User ID for attribution

    Example:
        ```python
        from app.ai.tools.approval_audit import ApprovalAuditLogger

        audit_logger = ApprovalAuditLogger(session_id, user_id)
        audit_logger.log_tool_execution("delete_project", {"project_id": "123"}, RiskLevel.CRITICAL)
        audit_logger.log_approval_request("approval-123", "delete_project", approved=True)
        ```
    """

    def __init__(self, session_id: UUID, user_id: UUID) -> None:
        """Initialize audit logger for a session.

        Args:
            session_id: Chat session ID
            user_id: User ID for attribution
        """
        self.session_id = session_id
        self.user_id = user_id

    def log_tool_execution(
        self,
        tool_name: str,
        tool_args: dict[str, Any],
        risk_level: RiskLevel,
        execution_mode: ExecutionMode,
    ) -> None:
        """Log a tool execution attempt.

        Args:
            tool_name: Name of the tool being executed
            tool_args: Arguments passed to the tool
            risk_level: Risk level of the tool
            execution_mode: Current execution mode
        """
        log_entry = {
            "event": "tool_execution",
            "session_id": str(self.session_id),
            "user_id": str(self.user_id),
            "timestamp": datetime.now().isoformat(),
            "tool_name": tool_name,
            "tool_args": tool_args,
            "risk_level": risk_level.value,
            "execution_mode": execution_mode.value,
        }

        logger.info(f"Tool execution: {json.dumps(log_entry)}")

    def log_approval_request(
        self,
        approval_id: str,
        tool_name: str,
        tool_args: dict[str, Any],
        expires_at: datetime,
    ) -> None:
        """Log an approval request sent to the user.

        Args:
            approval_id: Unique approval request ID
            tool_name: Name of the tool requiring approval
            tool_args: Arguments that will be passed to the tool
            expires_at: Expiration timestamp for the approval
        """
        log_entry = {
            "event": "approval_request",
            "session_id": str(self.session_id),
            "user_id": str(self.user_id),
            "timestamp": datetime.now().isoformat(),
            "approval_id": approval_id,
            "tool_name": tool_name,
            "tool_args": tool_args,
            "expires_at": expires_at.isoformat(),
        }

        logger.info(f"Approval request: {json.dumps(log_entry)}")

    def log_approval_response(
        self,
        approval_id: str,
        tool_name: str,
        approved: bool,
        user_id: UUID,
        response_time_seconds: float | None = None,
    ) -> None:
        """Log a user's approval response.

        Args:
            approval_id: Approval request ID being responded to
            tool_name: Name of the tool
            approved: True if approved, False if rejected
            user_id: User ID making the decision
            response_time_seconds: Time from request to response (optional)
        """
        log_entry = {
            "event": "approval_response",
            "session_id": str(self.session_id),
            "user_id": str(user_id),
            "timestamp": datetime.now().isoformat(),
            "approval_id": approval_id,
            "tool_name": tool_name,
            "approved": approved,
            "response_time_seconds": response_time_seconds,
        }

        logger.info(f"Approval response: {json.dumps(log_entry)}")

    def log_approval_timeout(
        self,
        approval_id: str,
        tool_name: str,
    ) -> None:
        """Log an approval timeout.

        Args:
            approval_id: Approval request ID that timed out
            tool_name: Name of the tool
        """
        log_entry = {
            "event": "approval_timeout",
            "session_id": str(self.session_id),
            "user_id": str(self.user_id),
            "timestamp": datetime.now().isoformat(),
            "approval_id": approval_id,
            "tool_name": tool_name,
        }

        logger.warning(f"Approval timeout: {json.dumps(log_entry)}")

    def log_tool_result(
        self,
        tool_name: str,
        success: bool,
        error_message: str | None = None,
        execution_time_seconds: float | None = None,
    ) -> None:
        """Log the result of a tool execution.

        Args:
            tool_name: Name of the tool
            success: True if execution succeeded, False otherwise
            error_message: Error message if execution failed
            execution_time_seconds: Time taken to execute the tool
        """
        log_entry = {
            "event": "tool_result",
            "session_id": str(self.session_id),
            "user_id": str(self.user_id),
            "timestamp": datetime.now().isoformat(),
            "tool_name": tool_name,
            "success": success,
            "error_message": error_message,
            "execution_time_seconds": execution_time_seconds,
        }

        if success:
            logger.info(f"Tool result: {json.dumps(log_entry)}")
        else:
            logger.error(f"Tool result: {json.dumps(log_entry)}")

    def log_error(
        self,
        error_type: str,
        message: str,
        context: dict[str, Any] | None = None,
    ) -> None:
        """Log an error event.

        Args:
            error_type: Type of error (e.g., "websocket_error", "permission_denied")
            message: Error message
            context: Additional context information
        """
        log_entry = {
            "event": "error",
            "session_id": str(self.session_id),
            "user_id": str(self.user_id),
            "timestamp": datetime.now().isoformat(),
            "error_type": error_type,
            "message": message,
            "context": context or {},
        }

        logger.error(f"Error: {json.dumps(log_entry)}")
