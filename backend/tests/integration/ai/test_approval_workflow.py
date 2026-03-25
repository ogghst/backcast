"""Integration tests for approval workflow (Phase 3).

Tests T-007 to T-009, T-015 to T-016:
- T-007: Critical tool triggers interrupt
- T-008: User approval resumes execution
- T-009: User rejection skips tool
- T-015: Approval request message format
- T-016: Approval response message format
"""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, Mock
from uuid import UUID, uuid4

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import StructuredTool
from langgraph.checkpoint.memory import MemorySaver

from app.ai.agent_service import AgentService
from app.ai.graph import create_graph
from app.ai.tools.interrupt_node import InterruptNode
from app.ai.tools.types import ExecutionMode, RiskLevel, ToolContext, ToolMetadata
from app.models.schemas.ai import (
    WSApprovalRequestMessage,
    WSApprovalResponseMessage,
)


@pytest.fixture
def db_session():
    """Mock database session."""
    return AsyncMock()


@pytest.fixture
def tool_context(db_session):
    """Create tool context for testing."""
    return ToolContext(
        session=db_session,
        user_id=str(uuid4()),
        user_role="admin",
        execution_mode=ExecutionMode.STANDARD,
    )


@pytest.fixture
def mock_websocket():
    """Mock WebSocket connection."""
    websocket = AsyncMock()
    websocket.send_json = AsyncMock()
    return websocket


@pytest.fixture
def critical_tool(tool_context):
    """Create a critical-risk tool for testing."""
    async def delete_all_data(context: ToolContext) -> str:
        return "All data deleted"

    tool = StructuredTool.from_function(
        func=delete_all_data,
        name="delete_all_data",
        description="Delete all data (CRITICAL RISK)",
    )
    tool._tool_metadata = ToolMetadata(
        name="delete_all_data",
        description="Delete all data",
        permissions=["delete:all"],
        risk_level=RiskLevel.CRITICAL,
    )
    return tool


@pytest.fixture
def high_risk_tool(tool_context):
    """Create a high-risk tool for testing."""
    async def update_project(context: ToolContext, project_id: str) -> str:
        return f"Project {project_id} updated"

    tool = StructuredTool.from_function(
        func=update_project,
        name="update_project",
        description="Update project (HIGH RISK)",
    )
    tool._tool_metadata = ToolMetadata(
        name="update_project",
        description="Update project",
        permissions=["update:project"],
        risk_level=RiskLevel.HIGH,
    )
    return tool


# T-007: test_critical_tool_triggers_interrupt
@pytest.mark.asyncio
async def test_critical_tool_triggers_interrupt(
    tool_context, critical_tool, mock_websocket
):
    """Test that critical tools trigger interrupt in standard mode.

    Expected behavior:
    - Graph pauses when critical tool is called in standard mode
    - Approval request message is sent via WebSocket
    - Message includes tool_name, tool_args, approval_id
    """
    # Arrange
    from langchain_openai import ChatOpenAI

    # Create a mock LLM that will call the critical tool
    mock_llm = MagicMock(spec=ChatOpenAI)
    mock_llm.bind_tools = MagicMock(return_value=mock_llm)

    # Create AIMessage with tool call
    tool_call_id = "test_tool_call_001"
    ai_message_with_tool_call = AIMessage(
        content="I will delete all data now",
        tool_calls=[
            {
                "id": tool_call_id,
                "name": "delete_all_data",
                "args": {},
            }
        ],
    )

    # Make ainvoke return the AIMessage with tool call
    mock_llm.ainvoke = AsyncMock(return_value=ai_message_with_tool_call)

    # Create graph with InterruptNode
    # Note: We need to modify create_graph to include InterruptNode
    # For now, test InterruptNode directly
    interrupt_node = InterruptNode(
        tools=[critical_tool],
        context=tool_context,
        websocket=mock_websocket,
        session_id=uuid4(),
    )

    # Act
    # Simulate tool call that would trigger interrupt
    tool_call_request = MagicMock()
    tool_call_request.tool_call = {
        "id": tool_call_id,
        "name": "delete_all_data",
        "args": {},
    }

    # Mock execute function
    execute = AsyncMock()

    # Call the interrupt node's wrapper
    result = await interrupt_node._awrap_tool_call(tool_call_request, execute)

    # Assert
    # 1. Result should be a ToolMessage with approval request info
    assert isinstance(result, ToolMessage)
    assert "approval" in result.content.lower() or "interrupt" in result.content.lower()

    # 2. WebSocket should have received approval request
    mock_websocket.send_json.assert_called_once()
    sent_message = mock_websocket.send_json.call_args[0][0]

    # 3. Message format validation (T-015)
    assert sent_message["type"] == "approval_request"
    assert "approval_id" in sent_message
    assert sent_message["tool_name"] == "delete_all_data"
    assert sent_message["risk_level"] == "critical"
    assert "expires_at" in sent_message

    # 4. Expires at should be ~5 minutes from now
    expires_at = sent_message["expires_at"]
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    expected_expiry = datetime.now() + timedelta(minutes=5)
    time_diff = abs((expires_at - expected_expiry).total_seconds())
    assert time_diff < 5  # Within 5 seconds tolerance


# T-008: test_user_approval_resumes_execution
@pytest.mark.asyncio
async def test_user_approval_resumes_execution(
    tool_context, critical_tool, mock_websocket
):
    """Test that approved tool executes after user approval.

    Expected behavior:
    - Tool executes normally after approval_response received
    - Tool result is returned to the user
    """
    # Arrange
    from langchain_openai import ChatOpenAI

    session_id = uuid4()

    # Create InterruptNode
    interrupt_node = InterruptNode(
        tools=[critical_tool],
        context=tool_context,
        websocket=mock_websocket,
        session_id=session_id,
    )

    # Pre-register an approval (simulating user already approved)
    approval_id = str(uuid4())
    interrupt_node.register_approval_response(approval_id, approved=True)

    # Update the pending approval to mark it as approved
    interrupt_node.pending_approvals[approval_id] = {
        "approved": True,
        "tool_name": "delete_all_data",
        "expires_at": datetime.now() + timedelta(minutes=5),
    }

    # Act - Mock _send_approval_request to return our pre-registered approval_id
    original_send = interrupt_node._send_approval_request
    async def mock_send_request(tool_name, tool_args, risk_level, tool_call=None, execute=None):
        return approval_id
    interrupt_node._send_approval_request = mock_send_request

    # Create tool call request
    tool_call_request = MagicMock()
    tool_call_request.tool_call = {
        "id": "test_tool_call_002",
        "name": "delete_all_data",
        "args": {},
    }

    # Mock execute function that returns success
    execute = AsyncMock(return_value=ToolMessage(content="All data deleted", tool_call_id="test_tool_call_002"))

    # Call the interrupt node's wrapper
    result = await interrupt_node._awrap_tool_call(tool_call_request, execute)

    # Assert
    # 1. Tool should have executed (execute was called)
    execute.assert_called_once()

    # 2. Result should contain the tool's output
    assert isinstance(result, ToolMessage)
    assert result.content == "All data deleted"

    # Restore original method
    interrupt_node._send_approval_request = original_send


# T-009: test_user_rejection_skips_tool
@pytest.mark.asyncio
async def test_user_rejection_skips_tool(
    tool_context, critical_tool, mock_websocket
):
    """Test that rejected tool is skipped and returns error.

    Expected behavior:
    - Tool is NOT executed when user rejects
    - Error message is returned instead
    """
    # Arrange
    session_id = uuid4()
    approval_id = str(uuid4())

    # Create InterruptNode
    interrupt_node = InterruptNode(
        tools=[critical_tool],
        context=tool_context,
        websocket=mock_websocket,
        session_id=session_id,
    )

    # Pre-register a rejection (simulating user already rejected)
    interrupt_node.register_approval_response(approval_id, approved=False)

    # Update the pending approval to mark it as rejected
    interrupt_node.pending_approvals[approval_id] = {
        "approved": False,
        "tool_name": "delete_all_data",
        "expires_at": datetime.now() + timedelta(minutes=5),
    }

    # Act - Mock _send_approval_request to return our pre-registered approval_id
    original_send = interrupt_node._send_approval_request
    async def mock_send_request(tool_name, tool_args, risk_level, tool_call=None, execute=None):
        return approval_id
    interrupt_node._send_approval_request = mock_send_request

    tool_call_request = MagicMock()
    tool_call_request.tool_call = {
        "id": "test_tool_call_003",
        "name": "delete_all_data",
        "args": {},
    }

    # Mock execute function (should NOT be called)
    execute = AsyncMock()

    # Call the interrupt node's wrapper
    result = await interrupt_node._awrap_tool_call(tool_call_request, execute)

    # Assert
    # 1. Tool should NOT have executed
    execute.assert_not_called()

    # 2. Result should be an error ToolMessage
    assert isinstance(result, ToolMessage)
    assert "rejected" in result.content.lower() or "not approved" in result.content.lower()

    # Restore original method
    interrupt_node._send_approval_request = original_send


# T-015: test_approval_request_message_format
@pytest.mark.asyncio
async def test_approval_request_message_format(
    tool_context, critical_tool, mock_websocket
):
    """Test that approval request message has correct format.

    Expected behavior:
    - Message includes all required fields
    - Fields have correct types
    - approval_id is unique
    """
    # Arrange
    session_id = uuid4()
    interrupt_node = InterruptNode(
        tools=[critical_tool],
        context=tool_context,
        websocket=mock_websocket,
        session_id=session_id,
    )

    # Act
    tool_call_request = MagicMock()
    tool_call_request.tool_call = {
        "id": "test_tool_call_004",
        "name": "delete_all_data",
        "args": {"confirm": True},
    }

    execute = AsyncMock()
    await interrupt_node._awrap_tool_call(tool_call_request, execute)

    # Assert
    assert mock_websocket.send_json.called
    sent_message = mock_websocket.send_json.call_args[0][0]

    # Validate message structure
    WSApprovalRequestMessage.model_validate(sent_message)  # Will raise if invalid

    # Check required fields
    assert sent_message["type"] == "approval_request"
    assert sent_message["tool_name"] == "delete_all_data"
    assert sent_message["tool_args"] == {"confirm": True}
    assert sent_message["risk_level"] == "critical"
    # session_id might be serialized as string in JSON
    assert str(sent_message["session_id"]) == str(session_id)

    # Check approval_id is valid UUID
    approval_id = sent_message["approval_id"]
    UUID(approval_id)  # Will raise if invalid

    # Check expires_at is future datetime
    expires_at = sent_message["expires_at"]
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    assert expires_at > datetime.now() + timedelta(minutes=4)


# T-016: test_approval_response_message_format
def test_approval_response_message_format():
    """Test that approval response message schema validates correctly.

    Expected behavior:
    - Schema accepts valid approval response
    - Schema requires all fields
    - Schema validates approved boolean
    """
    # Arrange
    approval_id = str(uuid4())
    user_id = uuid4()

    # Act & Assert - Valid approved response
    approved_response = WSApprovalResponseMessage(
        type="approval_response",
        approval_id=approval_id,
        approved=True,
        user_id=user_id,
        timestamp=datetime.now(),
    )
    assert approved_response.approved is True

    # Act & Assert - Valid rejected response
    rejected_response = WSApprovalResponseMessage(
        type="approval_response",
        approval_id=approval_id,
        approved=False,
        user_id=user_id,
        timestamp=datetime.now(),
    )
    assert rejected_response.approved is False

    # Act & Assert - Missing required field should fail
    with pytest.raises(ValueError):
        WSApprovalResponseMessage(
            type="approval_response",
            approval_id=approval_id,
            # Missing 'approved'
            user_id=user_id,
            timestamp=datetime.now(),
        )


# Additional tests for edge cases

@pytest.mark.asyncio
async def test_graph_resume_after_approval(
    tool_context, critical_tool, mock_websocket
):
    """Test that graph resumes execution after user approval.

    This tests the complete resume flow:
    1. Tool call triggers interrupt
    2. Approval request sent
    3. User approves
    4. Tool executes via resume
    """
    # Arrange
    session_id = uuid4()
    interrupt_node = InterruptNode(
        tools=[critical_tool],
        context=tool_context,
        websocket=mock_websocket,
        session_id=session_id,
    )

    # Simulate tool call that triggers interrupt
    tool_call_id = "test_tool_call_resume_001"
    tool_call_request = MagicMock()
    tool_call_request.tool_call = {
        "id": tool_call_id,
        "name": "delete_all_data",
        "args": {},
    }

    # Mock execute function
    execute = AsyncMock(return_value=ToolMessage(content="All data deleted", tool_call_id=tool_call_id))

    # Act - Call the interrupt node's wrapper (sends approval request)
    result = await interrupt_node._awrap_tool_call(tool_call_request, execute)

    # Assert - Should return error message (waiting for approval)
    assert isinstance(result, ToolMessage)
    assert "approval" in result.content.lower() or "waiting" in result.content.lower()

    # Get the approval_id from the WebSocket call
    sent_message = mock_websocket.send_json.call_args[0][0]
    approval_id = sent_message["approval_id"]

    # Verify interrupt state was stored
    interrupt_state = interrupt_node.get_interrupt_state(approval_id)
    assert interrupt_state is not None
    assert interrupt_state["tool_name"] == "delete_all_data"

    # Act - Register approval
    interrupt_node.register_approval_response(approval_id, approved=True)

    # Act - Execute after approval
    resume_result = await interrupt_node.execute_after_approval(approval_id)

    # Assert - Tool should have executed
    assert resume_result is not None
    assert isinstance(resume_result, ToolMessage)
    assert resume_result.content == "All data deleted"
    assert resume_result.tool_call_id == tool_call_id

    # Assert - State should be cleaned up
    assert interrupt_node.get_interrupt_state(approval_id) is None
    assert approval_id not in interrupt_node.pending_approvals


@pytest.mark.asyncio
async def test_graph_resume_rejection_skips_execution(
    tool_context, critical_tool, mock_websocket
):
    """Test that graph resume skips tool execution when rejected."""
    # Arrange
    session_id = uuid4()
    interrupt_node = InterruptNode(
        tools=[critical_tool],
        context=tool_context,
        websocket=mock_websocket,
        session_id=session_id,
    )

    # Simulate tool call that triggers interrupt
    tool_call_id = "test_tool_call_reject_001"
    tool_call_request = MagicMock()
    tool_call_request.tool_call = {
        "id": tool_call_id,
        "name": "delete_all_data",
        "args": {},
    }

    execute = AsyncMock(return_value=ToolMessage(content="All data deleted", tool_call_id=tool_call_id))

    # Act - Call the interrupt node's wrapper
    await interrupt_node._awrap_tool_call(tool_call_request, execute)

    # Get the approval_id
    sent_message = mock_websocket.send_json.call_args[0][0]
    approval_id = sent_message["approval_id"]

    # Act - Register rejection
    interrupt_node.register_approval_response(approval_id, approved=False)

    # Act - Try to execute after rejection
    resume_result = await interrupt_node.execute_after_approval(approval_id)

    # Assert - Tool should NOT have executed
    assert resume_result is not None
    assert isinstance(resume_result, ToolMessage)
    assert "rejected" in resume_result.content.lower()
    assert resume_result.content != "All data deleted"

    # Assert - execute should not have been called
    execute.assert_not_called()


@pytest.mark.asyncio
async def test_high_risk_tool_triggers_interrupt(
    tool_context, high_risk_tool, mock_websocket
):
    """Test that high-risk tools DO trigger interrupt in standard mode (after fix)."""
    # Arrange
    interrupt_node = InterruptNode(
        tools=[high_risk_tool],
        context=tool_context,
        websocket=mock_websocket,
        session_id=uuid4(),
    )

    # Act
    tool_call_request = MagicMock()
    tool_call_request.tool_call = {
        "id": "test_tool_call_005",
        "name": "update_project",
        "args": {"project_id": "proj-123"},
    }

    execute = AsyncMock(return_value=ToolMessage(content="Project updated", tool_call_id="test_tool_call_005"))
    result = await interrupt_node._awrap_tool_call(tool_call_request, execute)

    # Assert
    # 1. WebSocket SHOULD have been called (approval required for HIGH risk)
    mock_websocket.send_json.assert_called_once()

    # 2. Tool should NOT have executed (waiting for approval)
    execute.assert_not_called()

    # 3. Result should indicate approval is needed
    assert isinstance(result, ToolMessage)
    assert "approval" in result.content.lower() or "waiting" in result.content.lower()

    # 4. Verify risk_level in approval request is "high"
    sent_message = mock_websocket.send_json.call_args[0][0]
    assert sent_message["risk_level"] == "high"


@pytest.mark.asyncio
async def test_approval_timeout(tool_context, critical_tool, mock_websocket):
    """Test that expired approvals are rejected."""
    # Arrange
    session_id = uuid4()
    approval_id = str(uuid4())

    interrupt_node = InterruptNode(
        tools=[critical_tool],
        context=tool_context,
        websocket=mock_websocket,
        session_id=session_id,
    )

    # Add expired approval
    interrupt_node.pending_approvals[approval_id] = {
        "approved": True,
        "tool_name": "delete_all_data",
        "expires_at": datetime.now() - timedelta(minutes=1),  # Expired
    }

    # Act - Mock _send_approval_request to return our expired approval_id
    original_send = interrupt_node._send_approval_request
    async def mock_send_request(tool_name, tool_args, risk_level, tool_call=None, execute=None):
        return approval_id
    interrupt_node._send_approval_request = mock_send_request

    tool_call_request = MagicMock()
    tool_call_request.tool_call = {
        "id": "test_tool_call_006",
        "name": "delete_all_data",
        "args": {},
    }

    execute = AsyncMock()
    result = await interrupt_node._awrap_tool_call(tool_call_request, execute)

    # Assert
    # 1. Tool should NOT execute
    execute.assert_not_called()

    # 2. Result should indicate timeout
    assert isinstance(result, ToolMessage)
    assert "timeout" in result.content.lower() or "expired" in result.content.lower()

    # Restore original method
    interrupt_node._send_approval_request = original_send
