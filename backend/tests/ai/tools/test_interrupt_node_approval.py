"""Tests for InterruptNode approval logic by risk level.

Tests the fix for AI tool approval in standard mode:
- LOW risk tools should execute without approval in standard mode
- HIGH risk tools should require approval in standard mode
- CRITICAL risk tools should require approval in standard mode
- All tools should execute without approval in expert mode
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from langchain_core.tools import StructuredTool

from app.ai.tools.interrupt_node import InterruptNode
from app.ai.tools.types import ExecutionMode, RiskLevel, ToolContext, ToolMetadata


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
    websocket.client_state = MagicMock()
    return websocket


@pytest.fixture
def low_risk_tool():
    """Create a low-risk tool for testing."""

    async def read_only_tool(context: ToolContext) -> str:
        return "Read-only operation completed"

    tool = StructuredTool.from_function(
        func=read_only_tool,
        name="read_only_tool",
        description="Read-only operation (LOW RISK)",
    )
    tool._tool_metadata = ToolMetadata(
        name="read_only_tool",
        description="Read-only operation",
        permissions=["read:data"],
        risk_level=RiskLevel.LOW,
    )
    return tool


@pytest.fixture
def high_risk_tool():
    """Create a high-risk tool for testing."""

    async def create_project(context: ToolContext, name: str) -> str:
        return f"Project '{name}' created"

    tool = StructuredTool.from_function(
        func=create_project,
        name="create_project",
        description="Create project (HIGH RISK)",
    )
    tool._tool_metadata = ToolMetadata(
        name="create_project",
        description="Create project",
        permissions=["create:project"],
        risk_level=RiskLevel.HIGH,
    )
    return tool


@pytest.fixture
def critical_tool():
    """Create a critical-risk tool for testing."""

    async def delete_project(context: ToolContext, project_id: str) -> str:
        return f"Project {project_id} deleted"

    tool = StructuredTool.from_function(
        func=delete_project,
        name="delete_project",
        description="Delete project (CRITICAL RISK)",
    )
    tool._tool_metadata = ToolMetadata(
        name="delete_project",
        description="Delete project",
        permissions=["delete:project"],
        risk_level=RiskLevel.CRITICAL,
    )
    return tool


@pytest.mark.asyncio
async def test_low_risk_tool_no_approval_in_standard_mode(
    tool_context, mock_websocket, low_risk_tool
):
    """Test that LOW risk tools execute without approval in standard mode."""
    # Arrange
    session_id = uuid4()
    interrupt_node = InterruptNode(
        tools=[low_risk_tool],
        context=tool_context,
        websocket=mock_websocket,
        session_id=session_id,
    )

    # Create a mock tool call request
    tool_call_id = str(uuid4())
    tool_call_request = MagicMock()
    tool_call_request.tool_call = {
        "id": tool_call_id,
        "name": "read_only_tool",
        "args": {},
    }

    # Mock execute function that returns a ToolMessage
    from langchain_core.messages import ToolMessage

    async def mock_execute(request):
        return ToolMessage(
            content="Read-only operation completed", tool_call_id=tool_call_id
        )

    execute = AsyncMock(side_effect=mock_execute)

    # Act
    result = await interrupt_node._awrap_tool_call(tool_call_request, execute)

    # Assert
    # LOW risk tools should NOT send approval request
    mock_websocket.send_json.assert_not_called()
    # Should call execute (no interrupt)
    assert execute.called
    # Result should be a ToolMessage
    assert isinstance(result, ToolMessage)


@pytest.mark.asyncio
async def test_high_risk_tool_requires_approval_in_standard_mode(
    tool_context, mock_websocket, high_risk_tool
):
    """Test that HIGH risk tools require approval in standard mode."""
    # Arrange
    session_id = uuid4()
    interrupt_node = InterruptNode(
        tools=[high_risk_tool],
        context=tool_context,
        websocket=mock_websocket,
        session_id=session_id,
    )

    tool_call_id = str(uuid4())
    tool_call_request = MagicMock()
    tool_call_request.tool_call = {
        "id": tool_call_id,
        "name": "create_project",
        "args": {"name": "Test Project"},
    }

    # Mock execute function
    from langchain_core.messages import ToolMessage

    async def mock_execute(request):
        return ToolMessage(content="Project created", tool_call_id=tool_call_id)

    execute = AsyncMock(side_effect=mock_execute)

    # Act
    result = await interrupt_node._awrap_tool_call(tool_call_request, execute)

    # Assert
    # HIGH risk tools should send approval request
    mock_websocket.send_json.assert_called_once()
    # Should NOT call execute (waiting for approval)
    assert not execute.called
    # Result should be a ToolMessage with approval pending message
    assert isinstance(result, ToolMessage)
    assert "approval" in result.content.lower() or "waiting" in result.content.lower()


@pytest.mark.asyncio
async def test_critical_tool_requires_approval_in_standard_mode(
    tool_context, mock_websocket, critical_tool
):
    """Test that CRITICAL risk tools require approval in standard mode."""
    # Arrange
    session_id = uuid4()
    interrupt_node = InterruptNode(
        tools=[critical_tool],
        context=tool_context,
        websocket=mock_websocket,
        session_id=session_id,
    )

    tool_call_id = str(uuid4())
    tool_call_request = MagicMock()
    tool_call_request.tool_call = {
        "id": tool_call_id,
        "name": "delete_project",
        "args": {"project_id": str(uuid4())},
    }

    # Mock execute function
    from langchain_core.messages import ToolMessage

    async def mock_execute(request):
        return ToolMessage(content="Project deleted", tool_call_id=tool_call_id)

    execute = AsyncMock(side_effect=mock_execute)

    # Act
    result = await interrupt_node._awrap_tool_call(tool_call_request, execute)

    # Assert
    # CRITICAL risk tools should send approval request
    mock_websocket.send_json.assert_called_once()
    # Should NOT call execute (waiting for approval)
    assert not execute.called
    # Result should be a ToolMessage with approval pending message
    assert isinstance(result, ToolMessage)
    assert "approval" in result.content.lower() or "waiting" in result.content.lower()


@pytest.mark.asyncio
async def test_all_risk_tools_no_approval_in_expert_mode(
    db_session, mock_websocket, low_risk_tool, high_risk_tool, critical_tool
):
    """Test that all tools execute without approval in expert mode."""
    # Arrange - Create context with EXPERT mode
    expert_context = ToolContext(
        session=db_session,
        user_id=str(uuid4()),
        user_role="admin",
        execution_mode=ExecutionMode.EXPERT,
    )

    from langchain_core.messages import ToolMessage

    tools = [low_risk_tool, high_risk_tool, critical_tool]

    # Test each tool type
    for tool in tools:
        session_id = uuid4()
        interrupt_node = InterruptNode(
            tools=[tool],
            context=expert_context,
            websocket=mock_websocket,
            session_id=session_id,
        )

        tool_call_id = str(uuid4())
        tool_call_request = MagicMock()
        tool_call_request.tool_call = {
            "id": tool_call_id,
            "name": tool.name,
            "args": {},
        }

        # Mock execute function
        async def mock_execute(request, _tool=tool, _tool_call_id=tool_call_id):
            return ToolMessage(
                content=f"{_tool.name} executed", tool_call_id=_tool_call_id
            )

        execute = AsyncMock(side_effect=mock_execute)

        # Act
        result = await interrupt_node._awrap_tool_call(tool_call_request, execute)

        # Assert
        # No approval request should be sent in expert mode
        mock_websocket.send_json.assert_not_called()
        # Should call execute directly
        assert execute.called
        # Result should be a ToolMessage
        assert isinstance(result, ToolMessage)

        # Reset for next iteration
        execute.reset_mock()
        mock_websocket.send_json.reset_mock()


@pytest.mark.asyncio
async def test_risk_level_enum_ordering():
    """Test that RiskLevel enum supports ordering comparisons."""
    # RiskLevel should be ordered: LOW < HIGH < CRITICAL
    assert RiskLevel.LOW < RiskLevel.HIGH
    assert RiskLevel.HIGH < RiskLevel.CRITICAL
    assert RiskLevel.LOW < RiskLevel.CRITICAL

    # Test >= operator for approval logic
    assert RiskLevel.HIGH >= RiskLevel.HIGH
    assert RiskLevel.CRITICAL >= RiskLevel.HIGH
    assert RiskLevel.CRITICAL >= RiskLevel.CRITICAL
    assert not (RiskLevel.LOW >= RiskLevel.HIGH)
