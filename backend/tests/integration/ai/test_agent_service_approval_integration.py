"""Integration tests for AgentService approval workflow.

Tests the full end-to-end approval flow:
1. Critical tool call triggers InterruptNode
2. Approval request sent via WebSocket
3. User responds with approval/rejection
4. Graph resumes and tool executes or returns error
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import WebSocket
from langchain_openai import ChatOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.agent_service import AgentService
from app.ai.graph import create_graph
from app.ai.tools import ToolContext, create_project_tools
from app.ai.tools.interrupt_node import InterruptNode
from app.ai.tools.types import ExecutionMode, RiskLevel
from app.models.schemas.ai import WSApprovalRequestMessage


@pytest.fixture
def mock_websocket():
    """Create a mock WebSocket connection."""
    from starlette.websockets import WebSocketState

    websocket = AsyncMock(spec=WebSocket)
    websocket.send_json = AsyncMock()
    websocket.client_state = WebSocketState.CONNECTED  # Simulate connected state
    return websocket


@pytest.fixture
def mock_llm():
    """Create a mock LLM."""
    llm = MagicMock(spec=ChatOpenAI)
    return llm


@pytest.fixture
def mock_session():
    """Create a mock database session."""
    session = AsyncMock(spec=AsyncSession)
    return session


@pytest.fixture
def tool_context(mock_session):
    """Create a ToolContext for testing."""
    return ToolContext(
        mock_session,
        str(uuid4()),
        user_role="admin",
        execution_mode=ExecutionMode.STANDARD,
    )


@pytest.mark.asyncio
async def test_agent_service_registers_interrupt_node(
    mock_session, mock_websocket, mock_llm, tool_context
):
    """Test that AgentService registers InterruptNode when graph is created."""
    # Arrange
    session_id = uuid4()
    agent_service = AgentService(mock_session)

    # Create InterruptNode directly (simpler approach for this test)
    tools = create_project_tools(tool_context)
    interrupt_node = InterruptNode(tools, tool_context, mock_websocket, session_id)

    # Act
    agent_service.register_interrupt_node(session_id, interrupt_node)

    # Assert
    assert isinstance(interrupt_node, InterruptNode)
    retrieved = agent_service.get_interrupt_node(session_id)
    assert retrieved is interrupt_node


@pytest.mark.asyncio
async def test_agent_service_approval_response_routing(
    mock_session, mock_websocket, mock_llm, tool_context
):
    """Test that AgentService routes approval responses to InterruptNode."""
    # Arrange
    session_id = uuid4()
    approval_id = str(uuid4())
    agent_service = AgentService(mock_session)

    # Create InterruptNode directly and register with AgentService
    tools = create_project_tools(tool_context)
    interrupt_node = InterruptNode(tools, tool_context, mock_websocket, session_id)
    agent_service.register_interrupt_node(session_id, interrupt_node)

    # Add a pending approval
    interrupt_node.pending_approvals[approval_id] = {
        "approved": None,
        "tool_name": "test_tool",
        "tool_args": {},
        "expires_at": datetime.now() + timedelta(minutes=5),
    }

    # Act
    success = agent_service.register_approval_response(session_id, approval_id, True)

    # Assert
    assert success is True
    assert interrupt_node.pending_approvals[approval_id]["approved"] is True


@pytest.mark.asyncio
async def test_agent_service_approval_response_nonexistent_session(
    mock_session, mock_websocket, mock_llm, tool_context
):
    """Test that AgentService handles approval response for nonexistent session."""
    # Arrange
    session_id = uuid4()
    approval_id = str(uuid4())
    agent_service = AgentService(mock_session)

    # Act
    success = agent_service.register_approval_response(session_id, approval_id, True)

    # Assert
    assert success is False


@pytest.mark.asyncio
async def test_interrupt_node_sends_approval_request(
    mock_session, mock_websocket, mock_llm, tool_context
):
    """Test that InterruptNode sends approval request via WebSocket."""
    # Arrange
    session_id = uuid4()
    tools = create_project_tools(tool_context)
    interrupt_node = InterruptNode(tools, tool_context, mock_websocket, session_id)

    # Act
    approval_id = await interrupt_node._send_approval_request(
        "test_tool", {"arg1": "value1"}, RiskLevel.HIGH
    )

    # Assert
    assert approval_id is not None
    assert approval_id in interrupt_node.pending_approvals
    mock_websocket.send_json.assert_called_once()

    # Verify the message format
    call_args = mock_websocket.send_json.call_args[0][0]
    message = WSApprovalRequestMessage.model_validate(call_args)
    assert message.type == "approval_request"
    assert message.approval_id == approval_id
    assert message.tool_name == "test_tool"
    assert message.tool_args == {"arg1": "value1"}


@pytest.mark.asyncio
async def test_interrupt_node_checks_approval_status(
    mock_session, mock_websocket, mock_llm, tool_context
):
    """Test that InterruptNode correctly checks approval status."""
    # Arrange
    session_id = uuid4()
    tools = create_project_tools(tool_context)
    interrupt_node = InterruptNode(tools, tool_context, mock_websocket, session_id)

    approval_id = str(uuid4())
    interrupt_node.pending_approvals[approval_id] = {
        "approved": None,
        "tool_name": "test_tool",
        "tool_args": {},
        "expires_at": datetime.now() + timedelta(minutes=5),
    }

    # Act & Assert - Waiting for approval
    approved, error = interrupt_node._check_approval(approval_id)
    assert approved is False
    assert error is None  # Still waiting - no error message

    # Act & Assert - Approved
    interrupt_node.register_approval_response(approval_id, True)
    approved, error = interrupt_node._check_approval(approval_id)
    assert approved is True
    assert error is None

    # Act & Assert - Rejected
    approval_id_2 = str(uuid4())
    interrupt_node.pending_approvals[approval_id_2] = {
        "approved": None,
        "tool_name": "test_tool",
        "tool_args": {},
        "expires_at": datetime.now() + timedelta(minutes=5),
    }
    interrupt_node.register_approval_response(approval_id_2, False)
    approved, error = interrupt_node._check_approval(approval_id_2)
    assert approved is False
    assert error == "Tool execution was rejected by user"


@pytest.mark.asyncio
async def test_full_approval_flow(mock_session, mock_websocket, mock_llm, tool_context):
    """Test the full approval flow from request to response."""
    # Arrange
    session_id = uuid4()
    agent_service = AgentService(mock_session)

    # Create graph with InterruptNode
    tools = create_project_tools(tool_context)
    graph, interrupt_node = create_graph(
        llm=mock_llm,
        tools=tools,
        context=tool_context,
        websocket=mock_websocket,
        session_id=session_id,
    )

    if interrupt_node:
        agent_service.register_interrupt_node(session_id, interrupt_node)

        # Simulate critical tool call
        from app.ai.tools.types import RiskLevel

        approval_id = await interrupt_node._send_approval_request(
            "critical_tool", {"param": "value"}, RiskLevel.CRITICAL
        )

        # Verify approval request was sent
        assert mock_websocket.send_json.call_count == 1
        call_args = mock_websocket.send_json.call_args[0][0]
        message = WSApprovalRequestMessage.model_validate(call_args)
        assert message.approval_id == approval_id

        # Simulate user approval
        success = agent_service.register_approval_response(
            session_id, approval_id, True
        )
        assert success is True

        # Verify approval was registered
        approved, _ = interrupt_node._check_approval(approval_id)
        assert approved is True
