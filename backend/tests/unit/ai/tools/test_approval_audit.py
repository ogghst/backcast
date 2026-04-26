"""Unit tests for approval audit logging (Phase 3).

Tests T-017 and T-018:
- T-017: Tool execution logged
- T-018: Approval logged with user, decision, timestamp
"""

import json
import logging
from datetime import datetime
from uuid import uuid4

import pytest

from app.ai.tools.approval_audit import ApprovalAuditLogger
from app.ai.tools.types import ExecutionMode, RiskLevel


@pytest.fixture
def session_id():
    """Test session ID."""
    return uuid4()


@pytest.fixture
def user_id():
    """Test user ID."""
    return uuid4()


@pytest.fixture
def audit_logger(session_id, user_id):
    """Create audit logger for testing."""
    return ApprovalAuditLogger(session_id, user_id)


# T-017: test_tool_execution_logged
def test_tool_execution_logged(audit_logger, caplog):
    """Test that tool execution is logged with all required fields.

    Expected behavior:
    - Audit entry created on tool call
    - Entry includes tool_name, tool_args, risk_level, execution_mode
    - Entry includes timestamp
    """
    # Arrange
    tool_name = "delete_project"
    tool_args = {"project_id": "123"}
    risk_level = RiskLevel.CRITICAL
    execution_mode = ExecutionMode.STANDARD

    # Act
    with caplog.at_level(logging.INFO):
        audit_logger.log_tool_execution(
            tool_name=tool_name,
            tool_args=tool_args,
            risk_level=risk_level,
            execution_mode=execution_mode,
        )

    # Assert
    # Check that a log entry was created
    assert len(caplog.records) > 0

    # Find the tool execution log entry
    tool_log = None
    for record in caplog.records:
        if "Tool execution:" in record.message:
            tool_log = record.message
            break

    assert tool_log is not None, "Tool execution log not found"

    # Parse the JSON log entry
    log_data = json.loads(tool_log.split("Tool execution: ")[1])

    # Verify required fields
    assert log_data["event"] == "tool_execution"
    assert log_data["tool_name"] == tool_name
    assert log_data["tool_args"] == tool_args
    assert log_data["risk_level"] == risk_level.value
    assert log_data["execution_mode"] == execution_mode.value
    assert "timestamp" in log_data
    assert "session_id" in log_data
    assert "user_id" in log_data


# T-018: test_approval_logged
def test_approval_logged(audit_logger, caplog):
    """Test that approval is logged with user, decision, and timestamp.

    Expected behavior:
    - Audit entry created on approval decision
    - Entry includes user_id, approved/rejected, timestamp
    - Entry includes approval_id and tool_name
    """
    # Arrange
    approval_id = str(uuid4())
    tool_name = "delete_project"
    approved = True
    user_id = uuid4()
    response_time = 5.2

    # Act
    with caplog.at_level(logging.INFO):
        audit_logger.log_approval_response(
            approval_id=approval_id,
            tool_name=tool_name,
            approved=approved,
            user_id=user_id,
            response_time_seconds=response_time,
        )

    # Assert
    # Check that a log entry was created
    assert len(caplog.records) > 0

    # Find the approval response log entry
    approval_log = None
    for record in caplog.records:
        if "Approval response:" in record.message:
            approval_log = record.message
            break

    assert approval_log is not None, "Approval response log not found"

    # Parse the JSON log entry
    log_data = json.loads(approval_log.split("Approval response: ")[1])

    # Verify required fields
    assert log_data["event"] == "approval_response"
    assert log_data["approval_id"] == approval_id
    assert log_data["tool_name"] == tool_name
    assert log_data["approved"] == approved
    assert log_data["user_id"] == str(user_id)
    assert log_data["response_time_seconds"] == response_time
    assert "timestamp" in log_data


def test_approval_request_logged(audit_logger, caplog):
    """Test that approval request is logged."""
    # Arrange
    approval_id = str(uuid4())
    tool_name = "delete_project"
    tool_args = {"project_id": "123"}
    expires_at = datetime.now()

    # Act
    with caplog.at_level(logging.INFO):
        audit_logger.log_approval_request(
            approval_id=approval_id,
            tool_name=tool_name,
            tool_args=tool_args,
            expires_at=expires_at,
        )

    # Assert
    assert len(caplog.records) > 0

    approval_log = None
    for record in caplog.records:
        if "Approval request:" in record.message:
            approval_log = record.message
            break

    assert approval_log is not None

    log_data = json.loads(approval_log.split("Approval request: ")[1])

    assert log_data["event"] == "approval_request"
    assert log_data["approval_id"] == approval_id
    assert log_data["tool_name"] == tool_name
    assert log_data["tool_args"] == tool_args


def test_approval_timeout_logged(audit_logger, caplog):
    """Test that approval timeout is logged."""
    # Arrange
    approval_id = str(uuid4())
    tool_name = "delete_project"

    # Act
    with caplog.at_level(logging.WARNING):
        audit_logger.log_approval_timeout(
            approval_id=approval_id,
            tool_name=tool_name,
        )

    # Assert
    assert len(caplog.records) > 0

    timeout_log = None
    for record in caplog.records:
        if "Approval timeout:" in record.message:
            timeout_log = record.message
            break

    assert timeout_log is not None

    log_data = json.loads(timeout_log.split("Approval timeout: ")[1])

    assert log_data["event"] == "approval_timeout"
    assert log_data["approval_id"] == approval_id
    assert log_data["tool_name"] == tool_name


def test_tool_result_logged(audit_logger, caplog):
    """Test that tool result is logged."""
    # Arrange
    tool_name = "delete_project"
    success = True
    execution_time = 0.5

    # Act
    with caplog.at_level(logging.INFO):
        audit_logger.log_tool_result(
            tool_name=tool_name,
            success=success,
            execution_time_seconds=execution_time,
        )

    # Assert
    assert len(caplog.records) > 0

    result_log = None
    for record in caplog.records:
        if "Tool result:" in record.message:
            result_log = record.message
            break

    assert result_log is not None

    log_data = json.loads(result_log.split("Tool result: ")[1])

    assert log_data["event"] == "tool_result"
    assert log_data["tool_name"] == tool_name
    assert log_data["success"] == success
    assert log_data["execution_time_seconds"] == execution_time


def test_error_logged(audit_logger, caplog):
    """Test that errors are logged."""
    # Arrange
    error_type = "websocket_error"
    message = "WebSocket connection closed"
    context = {"session_id": str(uuid4())}

    # Act
    with caplog.at_level(logging.ERROR):
        audit_logger.log_error(
            error_type=error_type,
            message=message,
            context=context,
        )

    # Assert
    assert len(caplog.records) > 0

    error_log = None
    for record in caplog.records:
        if "Error:" in record.message:
            error_log = record.message
            break

    assert error_log is not None

    log_data = json.loads(error_log.split("Error: ")[1])

    assert log_data["event"] == "error"
    assert log_data["error_type"] == error_type
    assert log_data["message"] == message
    assert log_data["context"] == context
