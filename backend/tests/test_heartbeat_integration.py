"""Test WebSocket heartbeat functionality for approval polling."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.ai.tools.interrupt_node import InterruptNode
from app.ai.tools.types import ExecutionMode, RiskLevel, ToolContext
from app.models.schemas.ai import WSPollingHeartbeatMessage


@pytest.fixture
def mock_websocket():
    """Create a mock WebSocket connection."""
    websocket = AsyncMock()
    websocket.client_state = MagicMock()
    websocket.client_state.DISCONNECTED = "disconnected"
    return websocket


@pytest.fixture
def mock_session():
    """Create a mock database session."""
    return AsyncMock()


@pytest.fixture
def tool_context(mock_session):
    """Create a ToolContext for testing."""
    return ToolContext(
        session=mock_session,
        user_id=uuid4(),
        user_role="admin",
        execution_mode=ExecutionMode.STANDARD,
    )


@pytest.fixture
def interrupt_node(tool_context, mock_websocket):
    """Create an InterruptNode for testing."""
    session_id = uuid4()
    return InterruptNode(
        tools=[],
        context=tool_context,
        websocket=mock_websocket,
        session_id=session_id,
    )


@pytest.mark.asyncio
async def test_send_heartbeat_sends_message(interrupt_node, mock_websocket):
    """Test that _send_heartbeat sends the correct WebSocket message."""
    approval_id = "test-approval-id"
    elapsed = 10.5
    remaining = 19.5

    await interrupt_node._send_heartbeat(approval_id, elapsed, remaining)

    # Verify WebSocket send was called
    mock_websocket.send_json.assert_called_once()

    # Verify the message structure
    call_args = mock_websocket.send_json.call_args[0][0]
    assert call_args["type"] == "polling_heartbeat"
    assert call_args["approval_id"] == approval_id
    assert call_args["elapsed_seconds"] == elapsed
    assert call_args["remaining_seconds"] == remaining


@pytest.mark.asyncio
async def test_send_heartbeat_when_websocket_disconnected(
    interrupt_node, mock_websocket
):
    """Test that _send_heartbeat handles disconnected WebSocket gracefully."""
    # Simulate disconnected WebSocket by setting to DISCONNECTED state
    from starlette.websockets import WebSocketState

    mock_websocket.client_state = WebSocketState.DISCONNECTED

    approval_id = "test-approval-id"
    elapsed = 10.5
    remaining = 19.5

    # Should not raise exception
    await interrupt_node._send_heartbeat(approval_id, elapsed, remaining)

    # WebSocket send should not be called when disconnected
    mock_websocket.send_json.assert_not_called()


@pytest.mark.asyncio
async def test_polling_with_heartbeat(interrupt_node, mock_websocket):
    """Test that heartbeat messages are sent during polling simulation."""
    approval_id = "test-approval-id"

    # Send initial approval request
    await interrupt_node._send_approval_request(
        tool_name="test_tool",
        tool_args={},
        risk_level=RiskLevel.HIGH,
    )

    # Reset the mock to track only heartbeat messages
    mock_websocket.send_json.reset_mock()

    # Simulate sending 3 heartbeats over 15 seconds
    await interrupt_node._send_heartbeat(approval_id, 5.0, 25.0)
    await interrupt_node._send_heartbeat(approval_id, 10.0, 20.0)
    await interrupt_node._send_heartbeat(approval_id, 15.0, 15.0)

    # Verify 3 heartbeat messages were sent
    assert mock_websocket.send_json.call_count == 3

    # Verify the content of the last heartbeat
    last_call = mock_websocket.send_json.call_args_list[-1][0][0]
    assert last_call["type"] == "polling_heartbeat"
    assert last_call["approval_id"] == approval_id
    assert last_call["elapsed_seconds"] == 15.0
    assert last_call["remaining_seconds"] == 15.0


def test_polling_heartbeat_message_schema():
    """Test that WSPollingHeartbeatMessage validates correctly."""
    msg = WSPollingHeartbeatMessage(
        approval_id="test-approval-id",
        elapsed_seconds=10.5,
        remaining_seconds=19.5,
    )

    assert msg.type == "polling_heartbeat"
    assert msg.approval_id == "test-approval-id"
    assert msg.elapsed_seconds == 10.5
    assert msg.remaining_seconds == 19.5

    # Test serialization
    serialized = msg.model_dump(mode="json")
    assert serialized["type"] == "polling_heartbeat"
    assert serialized["approval_id"] == "test-approval-id"
    assert serialized["elapsed_seconds"] == 10.5
    assert serialized["remaining_seconds"] == 19.5
