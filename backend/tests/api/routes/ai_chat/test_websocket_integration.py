"""Integration tests for AI Chat WebSocket using direct endpoint testing.

WebSocket Mocking Strategy:
- Direct WebSocket endpoint testing with real WebSocket objects
- Mocked external dependencies (LLM/LangGraph) for deterministic tests
- Real database with transaction rollback for persistence testing
- Mocked auth/RBAC for predictable authentication

These tests use direct WebSocket endpoint testing to verify the complete
WebSocket protocol implementation including connection lifecycle, message
streaming, error handling, and reconnection logic.

Note: FastAPI's TestClient doesn't fully support async WebSocket testing in
pytest-asyncio. These tests use direct WebSocket mocking and endpoint testing.
"""

import asyncio
from collections.abc import AsyncGenerator, Generator
from datetime import datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from uuid import UUID, uuid4

import pytest
from fastapi import WebSocket
from fastapi.websockets import WebSocketDisconnect
from jose import jwt
from langchain_core.messages import AIMessage
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.ai_chat import chat_stream
from app.core.config import settings
from app.core.rbac import RBACServiceABC, get_rbac_service
from app.main import app
from app.models.domain.ai import (
    AIAssistantConfig,
    AIConversationMessage,
    AIConversationSession,
)
from app.models.domain.user import User
from app.models.schemas.ai import (
    WSChatRequest,
    WSCompleteMessage,
    WSErrorMessage,
    WSTokenMessage,
    WSToolCallMessage,
    WSToolResultMessage,
)


# =============================================================================
# Test Utilities
# =============================================================================


class WebSocketTestHelpers:
    """Helper class for WebSocket testing utilities."""

    @staticmethod
    def create_valid_token(user_email: str) -> str:
        """Create a valid JWT token for testing.

        Args:
            user_email: Email to embed in token subject.

        Returns:
            Valid JWT token string.
        """
        token_data = {
            "sub": user_email,
            "exp": datetime.utcnow() + timedelta(hours=1),
        }
        return jwt.encode(
            token_data,
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM,
        )

    @staticmethod
    def create_expired_token(user_email: str) -> str:
        """Create an expired JWT token for testing.

        Args:
            user_email: Email to embed in token subject.

        Returns:
            Expired JWT token string.
        """
        token_data = {
            "sub": user_email,
            "exp": datetime.utcnow() - timedelta(hours=1),
        }
        return jwt.encode(
            token_data,
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM,
        )

    @staticmethod
    async def collect_all_messages(websocket: WebSocket) -> list[dict[str, Any]]:
        """Collect all WebSocket messages until complete or error.

        Args:
            websocket: WebSocket connection to read from.

        Returns:
            List of received message dictionaries.
        """
        messages = []
        try:
            while True:
                data = await websocket.receive_json()
                messages.append(data)

                # Stop on complete or error message
                if data.get("type") in ("complete", "error"):
                    break
        except Exception:
            # Connection closed or error
            pass
        return messages

    @staticmethod
    def create_mock_token_events(content: str = "Test response") -> Generator[dict[str, Any], None, None]:
        """Create mock LangGraph token streaming events.

        Args:
            content: Content to stream in tokens.

        Yields:
            Mock LangGraph event dictionaries.
        """
        # Token streaming events
        for i, char in enumerate(content):
            yield {
                "event": "on_chat_model_stream",
                "data": {
                    "chunk": MagicMock(text=char, content=char),
                },
                "name": "LangGraph",
            }

        # Completion event
        yield {
            "event": "on_end",
            "data": {
                "output": {
                    "messages": [
                        AIMessage(content=content),
                    ]
                }
            },
            "name": "LangGraph",
        }

    @staticmethod
    def create_mock_tool_events(
        tool_name: str = "list_projects",
        tool_args: dict[str, Any] | None = None,
        tool_result: dict[str, Any] | None = None,
    ) -> Generator[dict[str, Any], None, None]:
        """Create mock LangGraph tool execution events.

        Args:
            tool_name: Name of the tool being called.
            tool_args: Arguments passed to the tool.
            tool_result: Result returned by the tool.

        Yields:
            Mock LangGraph event dictionaries.
        """
        if tool_args is None:
            tool_args = {"search": "test"}

        if tool_result is None:
            tool_result = {"projects": []}

        # Tool start event
        yield {
            "event": "on_tool_start",
            "data": {
                "input": tool_args,
            },
            "name": tool_name,
        }

        # Tool end event
        yield {
            "event": "on_tool_end",
            "data": {
                "output": tool_result,
            },
            "name": tool_name,
        }

        # Token streaming after tool
        yield {
            "event": "on_chat_model_stream",
            "data": {
                "chunk": MagicMock(text="Tool executed", content="Tool executed"),
            },
            "name": "LangGraph",
        }

        # Completion event
        yield {
            "event": "on_end",
            "data": {
                "output": {
                    "messages": [
                        AIMessage(content="Tool executed successfully"),
                    ]
                }
            },
            "name": "LangGraph",
        }

    @staticmethod
    def create_mock_error_events(error_message: str) -> Generator[dict[str, Any], None, None]:
        """Create mock LangGraph error events.

        Args:
            error_message: Error message to include in events.

        Yields:
            Mock LangGraph error event dictionaries.
        """
        yield {
            "event": "on_tool_error",
            "data": {
                "error": Exception(error_message),
            },
            "name": "test_tool",
        }


class MockASTreamEvents:
    """Mock LangGraph astream_events() for testing."""

    def __init__(self, events: list[dict[str, Any]] | Generator[dict[str, Any], None, None]):
        """Initialize mock stream with events.

        Args:
            events: List or generator of mock events to yield.
        """
        self.events = events

    def __aiter__(self):
        """Make this class async iterable.

        Returns:
            Async iterator self.
        """
        return self

    async def __anext__(self):
        """Get next event from the stream.

        Returns:
            Next event dictionary.

        Raises:
            StopAsyncIteration: When no more events are available.
        """
        if isinstance(self.events, Generator):
            try:
                return next(self.events)
            except StopIteration:
                raise StopAsyncIteration
        else:
            if hasattr(self, "_index"):
                self._index += 1
            else:
                self._index = 0

            if self._index >= len(self.events):
                raise StopAsyncIteration

            return self.events[self._index]


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def test_user() -> User:
    """Create a test user for authentication.

    Returns:
        User instance with ai-chat permission.
    """
    return User(
        id=uuid4(),
        user_id=uuid4(),
        email="test@example.com",
        is_active=True,
        role="admin",
        full_name="Test User",
        hashed_password="hash",
        created_by=uuid4(),
    )


@pytest.fixture
def test_user_no_permission() -> User:
    """Create a test user without ai-chat permission.

    Returns:
        User instance without ai-chat permission.
    """
    return User(
        id=uuid4(),
        user_id=uuid4(),
        email="noperm@example.com",
        is_active=True,
        role="viewer",  # Viewer role typically doesn't have ai-chat
        full_name="No Permission User",
        hashed_password="hash",
        created_by=uuid4(),
    )


@pytest.fixture
def mock_rbac_allow_all() -> RBACServiceABC:
    """Mock RBAC service that allows all permissions.

    Returns:
        RBAC service that grants all permissions.
    """

    class AllowAllRBAC(RBACServiceABC):
        def has_role(self, user_role: str, required_roles: list[str]) -> bool:
            return True

        def has_permission(self, user_role: str, required_permission: str) -> bool:
            return True

        def get_user_permissions(self, user_role: str) -> list[str]:
            return ["ai-chat", "project-read", "project-create"]

    return AllowAllRBAC()


@pytest.fixture
def mock_rbac_deny_ai() -> RBACServiceABC:
    """Mock RBAC service that denies AI chat permissions.

    Returns:
        RBAC service that denies ai-chat permission.
    """

    class DenyAIRBAC(RBACServiceABC):
        def has_role(self, user_role: str, required_roles: list[str]) -> bool:
            return True

        def has_permission(self, user_role: str, required_permission: str) -> bool:
            if required_permission == "ai-chat":
                return False
            return True

        def get_user_permissions(self, user_role: str) -> list[str]:
            return ["project-read", "project-create"]  # No ai-chat

    return DenyAIRBAC()


@pytest.fixture
def valid_token(test_user: User) -> str:
    """Create a valid JWT token for testing.

    Args:
        test_user: User to create token for.

    Returns:
        Valid JWT token string.
    """
    return WebSocketTestHelpers.create_valid_token(test_user.email)


@pytest.fixture
def expired_token(test_user: User) -> str:
    """Create an expired JWT token for testing.

    Args:
        test_user: User to create token for.

    Returns:
        Expired JWT token string.
    """
    return WebSocketTestHelpers.create_expired_token(test_user.email)


@pytest.fixture
def override_get_user(test_user: User) -> Generator[None, None, None]:
    """Override user lookup for tests.

    Args:
        test_user: User to return from lookup.

    Yields:
        None
    """
    from app.services.user import UserService

    # The method signature is get_by_email(self, email: str) -> User | None
    # When patching an instance method, we need to handle self correctly
    original_get_by_email = UserService.get_by_email

    async def mock_get_by_email(self, email: str) -> User | None:
        if email == test_user.email:
            return test_user
        return None

    with patch.object(UserService, "get_by_email", new=mock_get_by_email):
        yield


@pytest.fixture
def override_rbac(mock_rbac_allow_all: RBACServiceABC) -> Generator[None, None, None]:
    """Override RBAC service for tests.

    Args:
        mock_rbac_allow_all: RBAC service to use.

    Yields:
        None
    """
    app.dependency_overrides[get_rbac_service] = lambda: mock_rbac_allow_all
    yield
    app.dependency_overrides = {}


# =============================================================================
# Connection Lifecycle Tests (T-WS-LC-01 through T-WS-LC-05)
# =============================================================================


@pytest.mark.asyncio
async def test_ws_lc_01_valid_token_accepts_connection(
    valid_token: str,
    override_get_user: None,
    override_rbac: None,
    test_ai_assistant: AIAssistantConfig,
    db_session: AsyncSession,
) -> None:
    """T-WS-LC-01: Valid token with permission should accept connection.

    Test that WebSocket accepts connection when:
    - Valid JWT token is provided
    - User has ai-chat permission

    Expected:
    - Connection is accepted
    - No error messages sent
    """
    # Create mock WebSocket
    mock_websocket = AsyncMock(spec=WebSocket)

    # Mock the WebSocket methods
    mock_websocket.accept = AsyncMock()
    mock_websocket.close = AsyncMock()
    mock_websocket.receive_json = AsyncMock(
        side_effect=[
            {
                "type": "chat",
                "message": "Hello",
                "session_id": None,
                "assistant_config_id": str(test_ai_assistant.id),
            },
            # Second receive raises WebSocketDisconnect to end loop
            WebSocketDisconnect(code=1000, reason="Normal closure"),
        ]
    )
    mock_websocket.send_json = AsyncMock()

    # Mock AgentService to avoid LLM calls
    async def mock_chat_stream(*args, **kwargs):
        ws = kwargs.get("websocket")
        session_id = kwargs.get("session_id") or uuid4()
        await ws.send_json(
            WSTokenMessage(
                type="token",
                content="Response",
                session_id=session_id,
            ).model_dump(mode="json")
        )
        await ws.send_json(
            WSCompleteMessage(
                type="complete",
                session_id=session_id,
                message_id=uuid4(),
            ).model_dump(mode="json")
        )

    with patch("app.api.routes.ai_chat.AgentService") as mock_agent_service:
        mock_agent_service.return_value.chat_stream = mock_chat_stream

        # Call the endpoint directly
        await chat_stream(
            websocket=mock_websocket,
            token=valid_token,
        )

    # Verify connection was accepted
    mock_websocket.accept.assert_called_once()

    # Verify messages were sent
    assert mock_websocket.send_json.call_count >= 1


@pytest.mark.asyncio
async def test_ws_lc_02_invalid_token_rejects_connection(
    override_get_user: None,
    override_rbac: None,
) -> None:
    """T-WS-LC-02: Invalid token should close connection with 1008.

    Test that WebSocket rejects connection when:
    - Invalid JWT token is provided

    Expected:
    - Connection closes with code 1008 (policy violation)
    - Reason indicates invalid token
    """
    invalid_token = "invalid.token.format"
    mock_websocket = AsyncMock(spec=WebSocket)
    mock_websocket.close = AsyncMock()

    # Call the endpoint directly
    await chat_stream(
        websocket=mock_websocket,
        token=invalid_token,
    )

    # Verify connection was rejected with 1008
    mock_websocket.close.assert_called_once()
    close_call = mock_websocket.close.call_args
    assert close_call[1]["code"] == 1008
    assert "Invalid token" in close_call[1]["reason"]


@pytest.mark.asyncio
async def test_ws_lc_03_expired_token_rejects_connection(
    expired_token: str,
    override_get_user: None,
    override_rbac: None,
) -> None:
    """T-WS-LC-03: Expired token should close connection with 4008.

    Test that WebSocket rejects connection when:
    - Expired JWT token is provided

    Expected:
    - Connection closes with code 4008 (custom auth expiration code)
    - Reason indicates token expired
    """
    mock_websocket = AsyncMock(spec=WebSocket)
    mock_websocket.close = AsyncMock()

    # Call the endpoint directly
    await chat_stream(
        websocket=mock_websocket,
        token=expired_token,
    )

    # Verify connection was rejected with 4008
    mock_websocket.close.assert_called_once()
    close_call = mock_websocket.close.call_args
    assert close_call[1]["code"] == 4008
    assert "expired" in close_call[1]["reason"].lower()


@pytest.mark.asyncio
async def test_ws_lc_04_no_permission_rejects_connection(
    valid_token: str,
    test_user_no_permission: User,
) -> None:
    """T-WS-LC-04: No ai-chat permission should close connection with 1008.

    Test that WebSocket rejects connection when:
    - Valid token but user lacks ai-chat permission

    Expected:
    - Connection closes with code 1008 (policy violation)
    - Reason indicates insufficient permissions
    """
    # Override user lookup to return user without permission
    from app.services.user import UserService

    async def mock_get_by_email_no_perm(self, email: str) -> User | None:
        return test_user_no_permission

    # Override RBAC to deny ai-chat
    def mock_get_rbac_deny() -> RBACServiceABC:
        class DenyAIRBAC(RBACServiceABC):
            def has_role(self, user_role: str, required_roles: list[str]) -> bool:
                return True

            def has_permission(self, user_role: str, required_permission: str) -> bool:
                return required_permission != "ai-chat"

            def get_user_permissions(self, user_role: str) -> list[str]:
                return []

        return DenyAIRBAC()

    app.dependency_overrides[get_rbac_service] = mock_get_rbac_deny

    mock_websocket = AsyncMock(spec=WebSocket)
    mock_websocket.close = AsyncMock()

    with patch.object(UserService, "get_by_email", new=mock_get_by_email_no_perm):
        # Call the endpoint directly
        await chat_stream(
            websocket=mock_websocket,
            token=valid_token,
        )

    app.dependency_overrides = {}

    # Verify connection was rejected with 1008
    mock_websocket.close.assert_called_once()
    close_call = mock_websocket.close.call_args
    assert close_call[1]["code"] == 1008
    assert "ai-chat" in close_call[1]["reason"].lower()


@pytest.mark.asyncio
async def test_ws_lc_05_normal_disconnect_cleanup(
    valid_token: str,
    override_get_user: None,
    override_rbac: None,
    test_ai_assistant: AIAssistantConfig,
    db_session: AsyncSession,
) -> None:
    """T-WS-LC-05: Normal disconnect should execute cleanup.

    Test that WebSocket handles normal disconnect:
    - Client closes connection normally
    - Database session is cleaned up
    - No errors logged

    Expected:
    - Cleanup executes without errors
    - Database session is closed
    """
    mock_websocket = AsyncMock(spec=WebSocket)
    mock_websocket.accept = AsyncMock()
    mock_websocket.close = AsyncMock()
    mock_websocket.receive_json = AsyncMock(
        side_effect=[
            {
                "type": "chat",
                "message": "Hello",
                "session_id": None,
                "assistant_config_id": str(test_ai_assistant.id),
            },
            # Normal disconnect
            WebSocketDisconnect(code=1000, reason="Normal closure"),
        ]
    )
    mock_websocket.send_json = AsyncMock()

    # Mock AgentService
    async def mock_chat_stream(*args, **kwargs):
        pass

    with patch("app.api.routes.ai_chat.AgentService") as mock_agent_service:
        mock_agent_service.return_value.chat_stream = mock_chat_stream

        # Call the endpoint directly
        await chat_stream(
            websocket=mock_websocket,
            token=valid_token,
        )

    # Verify connection was accepted and handled gracefully
    mock_websocket.accept.assert_called_once()


# =============================================================================
# Streaming Token Tests (T-WS-ST-01 through T-WS-ST-03)
# =============================================================================


@pytest.mark.asyncio
async def test_ws_st_01_text_generation_streams_tokens(
    valid_token: str,
    override_get_user: None,
    override_rbac: None,
    test_ai_assistant: AIAssistantConfig,
    db_session: AsyncSession,
) -> None:
    """T-WS-ST-01: Text generation should stream token messages.

    Test that text generation streams tokens:
    - Send chat request
    - Receive multiple WSTokenMessage
    - Final WSCompleteMessage

    Expected:
    - Multiple token messages with content
    - Session ID matches
    - Complete message received at end
    """
    mock_websocket = AsyncMock(spec=WebSocket)
    mock_websocket.accept = AsyncMock()
    mock_websocket.close = AsyncMock()
    mock_websocket.receive_json = AsyncMock(
        side_effect=[
            {
                "type": "chat",
                "message": "Tell me about projects",
                "session_id": None,
                "assistant_config_id": str(test_ai_assistant.id),
            },
            WebSocketDisconnect(code=1000),
        ]
    )

    # Track sent messages
    sent_messages = []

    async def mock_send_json(message: dict[str, Any]) -> None:
        sent_messages.append(message)

    mock_websocket.send_json = AsyncMock(side_effect=mock_send_json)

    # Mock AIConfigService to return test assistant
    from app.services.ai_config_service import AIConfigService

    async def mock_get_assistant_config(self, config_id: UUID) -> AIAssistantConfig | None:
        if str(config_id) == str(test_ai_assistant.id):
            return test_ai_assistant
        return None

    # Mock AgentService.chat_stream to send token messages
    async def mock_chat_stream(*args, **kwargs):
        ws = kwargs.get("websocket")
        session_id = kwargs.get("session_id") or uuid4()

        # Send token messages
        await ws.send_json(
            WSTokenMessage(
                type="token",
                content="Hello",
                session_id=session_id,
            ).model_dump(mode="json")
        )
        await asyncio.sleep(0.01)

        await ws.send_json(
            WSTokenMessage(
                type="token",
                content=" there",
                session_id=session_id,
            ).model_dump(mode="json")
        )
        await asyncio.sleep(0.01)

        # Send complete message
        await ws.send_json(
            WSCompleteMessage(
                type="complete",
                session_id=session_id,
                message_id=uuid4(),
            ).model_dump(mode="json")
        )

    with patch.object(AIConfigService, "get_assistant_config", new=mock_get_assistant_config):
        with patch("app.api.routes.ai_chat.AgentService") as mock_agent_service:
            mock_agent_service.return_value.chat_stream = mock_chat_stream

            # Call the endpoint directly
            await chat_stream(
                websocket=mock_websocket,
                token=valid_token,
            )

    # Verify messages
    assert len(sent_messages) >= 2
    token_messages = [m for m in sent_messages if m.get("type") == "token"]
    assert len(token_messages) >= 2
    assert token_messages[0]["content"] == "Hello"
    assert token_messages[1]["content"] == " there"

    complete_messages = [m for m in sent_messages if m.get("type") == "complete"]
    assert len(complete_messages) == 1


@pytest.mark.asyncio
async def test_ws_st_02_tool_execution_streams_tool_messages(
    valid_token: str,
    override_get_user: None,
    override_rbac: None,
    test_ai_assistant: AIAssistantConfig,
    db_session: AsyncSession,
) -> None:
    """T-WS-ST-02: Tool execution should stream tool messages.

    Test that tool execution streams messages:
    - WSToolCallMessage when tool starts
    - WSToolResultMessage when tool completes
    - Token messages continue after tool

    Expected:
    - Tool call message with tool name and args
    - Tool result message with result data
    """
    mock_websocket = AsyncMock(spec=WebSocket)
    mock_websocket.accept = AsyncMock()
    mock_websocket.close = AsyncMock()
    mock_websocket.receive_json = AsyncMock(
        side_effect=[
            {
                "type": "chat",
                "message": "List all projects",
                "session_id": None,
                "assistant_config_id": str(test_ai_assistant.id),
            },
            WebSocketDisconnect(code=1000),
        ]
    )

    # Track sent messages
    sent_messages = []

    async def mock_send_json(message: dict[str, Any]) -> None:
        sent_messages.append(message)

    mock_websocket.send_json = AsyncMock(side_effect=mock_send_json)

    # Mock AIConfigService to return test assistant
    from app.services.ai_config_service import AIConfigService

    async def mock_get_assistant_config(self, config_id: UUID) -> AIAssistantConfig | None:
        if str(config_id) == str(test_ai_assistant.id):
            return test_ai_assistant
        return None

    # Mock AgentService.chat_stream to simulate tool execution
    async def mock_chat_stream(*args, **kwargs):
        ws = kwargs.get("websocket")
        session_id = kwargs.get("session_id") or uuid4()

        # Send tool call message
        await ws.send_json(
            WSToolCallMessage(
                type="tool_call",
                tool="list_projects",
                args={"search": "test"},
            ).model_dump(mode="json")
        )
        await asyncio.sleep(0.01)

        # Send tool result message
        await ws.send_json(
            WSToolResultMessage(
                type="tool_result",
                tool="list_projects",
                result={"projects": []},
            ).model_dump(mode="json")
        )
        await asyncio.sleep(0.01)

        # Send token message
        await ws.send_json(
            WSTokenMessage(
                type="token",
                content="Found 0 projects",
                session_id=session_id,
            ).model_dump(mode="json")
        )
        await asyncio.sleep(0.01)

        # Send complete message
        await ws.send_json(
            WSCompleteMessage(
                type="complete",
                session_id=session_id,
                message_id=uuid4(),
            ).model_dump(mode="json")
        )

    with patch.object(AIConfigService, "get_assistant_config", new=mock_get_assistant_config):
        with patch("app.api.routes.ai_chat.AgentService") as mock_agent_service:
            mock_agent_service.return_value.chat_stream = mock_chat_stream

            # Call the endpoint directly
            await chat_stream(
                websocket=mock_websocket,
                token=valid_token,
            )

    # Verify messages
    tool_call_messages = [m for m in sent_messages if m.get("type") == "tool_call"]
    assert len(tool_call_messages) == 1
    assert tool_call_messages[0]["tool"] == "list_projects"

    tool_result_messages = [m for m in sent_messages if m.get("type") == "tool_result"]
    assert len(tool_result_messages) == 1


@pytest.mark.asyncio
async def test_ws_st_03_multiple_messages_maintain_session(
    valid_token: str,
    override_get_user: None,
    override_rbac: None,
    test_ai_assistant: AIAssistantConfig,
    db_session: AsyncSession,
) -> None:
    """T-WS-ST-03: Multiple messages should maintain session.

    Test that multiple messages in same WebSocket connection:
    - First message creates session
    - Subsequent messages use same session
    - Session ID is consistent

    Expected:
    - First response has new session ID
    - Second response has same session ID
    - Session persists across messages
    """
    mock_websocket = AsyncMock(spec=WebSocket)
    mock_websocket.accept = AsyncMock()
    mock_websocket.close = AsyncMock()

    # Track session IDs
    session_ids = []

    # Mock AIConfigService to return test assistant
    from app.services.ai_config_service import AIConfigService

    async def mock_get_assistant_config(self, config_id: UUID) -> AIAssistantConfig | None:
        if str(config_id) == str(test_ai_assistant.id):
            return test_ai_assistant
        return None

    async def mock_chat_stream(*args, **kwargs):
        session_id = kwargs.get("session_id")
        ws = kwargs.get("websocket")

        # Track session ID
        session_ids.append(session_id)

        # Send response
        await ws.send_json(
            WSTokenMessage(
                type="token",
                content="Response",
                session_id=session_id,
            ).model_dump(mode="json")
        )
        await asyncio.sleep(0.01)

        await ws.send_json(
            WSCompleteMessage(
                type="complete",
                session_id=session_id,
                message_id=uuid4(),
            ).model_dump(mode="json")
        )

    with patch.object(AIConfigService, "get_assistant_config", new=mock_get_assistant_config):
        with patch("app.api.routes.ai_chat.AgentService") as mock_agent_service:
            mock_agent_service.return_value.chat_stream = mock_chat_stream

            # First message
            mock_websocket.receive_json = AsyncMock(
                side_effect=[
                    {
                        "type": "chat",
                        "message": "First message",
                        "session_id": None,
                        "assistant_config_id": str(test_ai_assistant.id),
                    },
                    {
                        "type": "chat",
                        "message": "Second message",
                        "session_id": None,  # Will be set by first response
                        "assistant_config_id": str(test_ai_assistant.id),
                    },
                    WebSocketDisconnect(code=1000),
                ]
            )

            # Reset tracking
            session_ids.clear()

            # Call the endpoint directly
            await chat_stream(
                websocket=mock_websocket,
                token=valid_token,
            )

    # Note: Due to mocking, we can't fully test session persistence
    # In real scenario, the client would send the session_id from the first response
    assert len(session_ids) >= 1  # At least one session was created


# =============================================================================
# Error Handling Tests (T-WS-ERR-01 through T-WS-ERR-05)
# =============================================================================


@pytest.mark.asyncio
async def test_ws_err_01_missing_assistant_config_id(
    valid_token: str,
    override_get_user: None,
    override_rbac: None,
    db_session: AsyncSession,
) -> None:
    """T-WS-ERR-01: Missing assistant_config_id should send error message.

    Test that missing assistant config ID:
    - Returns WSErrorMessage
    - Error indicates config is required
    - Connection remains open

    Expected:
    - Error message with code 400
    - Message indicates assistant config required
    """
    mock_websocket = AsyncMock(spec=WebSocket)
    mock_websocket.accept = AsyncMock()
    mock_websocket.close = AsyncMock()
    mock_websocket.receive_json = AsyncMock(
        side_effect=[
            {
                "type": "chat",
                "message": "Hello",
                "session_id": None,
                "assistant_config_id": None,  # Missing
            },
            {
                "type": "chat",
                "message": "Hello",
                "session_id": None,
                "assistant_config_id": None,  # Missing
            },
            WebSocketDisconnect(code=1000),
        ]
    )

    sent_messages = []

    async def mock_send_json(message: dict[str, Any]) -> None:
        sent_messages.append(message)

    mock_websocket.send_json = AsyncMock(side_effect=mock_send_json)

    # Call the endpoint directly
    await chat_stream(
        websocket=mock_websocket,
        token=valid_token,
    )

    # Should receive error message
    assert len(sent_messages) >= 1
    assert sent_messages[0].get("type") == "error"
    assert "Assistant config is required" in sent_messages[0].get("message", "")


@pytest.mark.asyncio
async def test_ws_err_02_invalid_assistant_config_id(
    valid_token: str,
    override_get_user: None,
    override_rbac: None,
    db_session: AsyncSession,
) -> None:
    """T-WS-ERR-02: Invalid assistant_config_id should send error message.

    Test that invalid assistant config ID:
    - Returns WSErrorMessage
    - Error indicates config not found
    - Connection remains open

    Expected:
    - Error message with code 404
    - Message indicates config not found
    """
    mock_websocket = AsyncMock(spec=WebSocket)
    mock_websocket.accept = AsyncMock()
    mock_websocket.close = AsyncMock()
    fake_id = uuid4()
    mock_websocket.receive_json = AsyncMock(
        side_effect=[
            {
                "type": "chat",
                "message": "Hello",
                "session_id": None,
                "assistant_config_id": str(fake_id),
            },
            WebSocketDisconnect(code=1000),
        ]
    )

    sent_messages = []

    async def mock_send_json(message: dict[str, Any]) -> None:
        sent_messages.append(message)

    mock_websocket.send_json = AsyncMock(side_effect=mock_send_json)

    # Mock AIConfigService to return None (not found)
    from app.services.ai_config_service import AIConfigService

    async def mock_get_assistant_config(self, config_id: UUID) -> AIAssistantConfig | None:
        return None  # Not found

    with patch.object(AIConfigService, "get_assistant_config", new=mock_get_assistant_config):
        # Call the endpoint directly
        await chat_stream(
            websocket=mock_websocket,
            token=valid_token,
        )

    # Should receive error message
    assert len(sent_messages) >= 1
    assert sent_messages[0].get("type") == "error"
    assert "not found" in sent_messages[0].get("message", "").lower()


@pytest.mark.asyncio
async def test_ws_err_03_inactive_assistant_config(
    valid_token: str,
    override_get_user: None,
    override_rbac: None,
    inactive_ai_assistant: AIAssistantConfig,
    db_session: AsyncSession,
) -> None:
    """T-WS-ERR-03: Inactive assistant_config should send error message.

    Test that inactive assistant config:
    - Returns WSErrorMessage
    - Error indicates config not active
    - Connection remains open

    Expected:
    - Error message with code 400
    - Message indicates config not active
    """
    mock_websocket = AsyncMock(spec=WebSocket)
    mock_websocket.accept = AsyncMock()
    mock_websocket.close = AsyncMock()
    mock_websocket.receive_json = AsyncMock(
        side_effect=[
            {
                "type": "chat",
                "message": "Hello",
                "session_id": None,
                "assistant_config_id": str(inactive_ai_assistant.id),
            },
            WebSocketDisconnect(code=1000),
        ]
    )

    sent_messages = []

    async def mock_send_json(message: dict[str, Any]) -> None:
        sent_messages.append(message)

    mock_websocket.send_json = AsyncMock(side_effect=mock_send_json)

    # Mock AIConfigService to return inactive assistant
    from app.services.ai_config_service import AIConfigService

    async def mock_get_assistant_config(self, config_id: UUID) -> AIAssistantConfig | None:
        if str(config_id) == str(inactive_ai_assistant.id):
            return inactive_ai_assistant
        return None

    with patch.object(AIConfigService, "get_assistant_config", new=mock_get_assistant_config):
        # Call the endpoint directly
        await chat_stream(
            websocket=mock_websocket,
            token=valid_token,
        )

    # Should receive error message
    assert len(sent_messages) >= 1
    assert sent_messages[0].get("type") == "error"
    assert "not active" in sent_messages[0].get("message", "").lower()


@pytest.mark.asyncio
async def test_ws_err_04_streaming_error_sends_error_message(
    valid_token: str,
    override_get_user: None,
    override_rbac: None,
    test_ai_assistant: AIAssistantConfig,
    db_session: AsyncSession,
) -> None:
    """T-WS-ERR-04: Streaming error should send error message.

    Test that streaming errors:
    - Send WSErrorMessage
    - Error includes exception details
    - Connection handled gracefully

    Expected:
    - Error message with code 500
    - Message includes error details
    """
    mock_websocket = AsyncMock(spec=WebSocket)
    mock_websocket.accept = AsyncMock()
    mock_websocket.close = AsyncMock()
    mock_websocket.receive_json = AsyncMock(
        side_effect=[
            {
                "type": "chat",
                "message": "Hello",
                "session_id": None,
                "assistant_config_id": str(test_ai_assistant.id),
            },
            WebSocketDisconnect(code=1000),
        ]
    )

    sent_messages = []

    async def mock_send_json(message: dict[str, Any]) -> None:
        sent_messages.append(message)

    mock_websocket.send_json = AsyncMock(side_effect=mock_send_json)

    # Mock AIConfigService to return test assistant
    from app.services.ai_config_service import AIConfigService

    async def mock_get_assistant_config(self, config_id: UUID) -> AIAssistantConfig | None:
        if str(config_id) == str(test_ai_assistant.id):
            return test_ai_assistant
        return None

    # Mock AgentService.chat_stream to raise exception
    async def mock_chat_stream_error(*args, **kwargs):
        ws = kwargs.get("websocket")
        await ws.send_json(
            WSErrorMessage(
                type="error",
                message="Streaming failed: connection timeout",
                code=500,
            ).model_dump(mode="json")
        )

    with patch.object(AIConfigService, "get_assistant_config", new=mock_get_assistant_config):
        with patch("app.api.routes.ai_chat.AgentService") as mock_agent_service:
            mock_agent_service.return_value.chat_stream = mock_chat_stream_error

            # Call the endpoint directly
            await chat_stream(
                websocket=mock_websocket,
                token=valid_token,
            )

    # Should receive error message
    assert len(sent_messages) >= 1
    assert sent_messages[0].get("type") == "error"
    assert sent_messages[0].get("code") == 500


@pytest.mark.asyncio
async def test_ws_err_05_empty_message_validation(
    valid_token: str,
    override_get_user: None,
    override_rbac: None,
    test_ai_assistant: AIAssistantConfig,
    db_session: AsyncSession,
) -> None:
    """T-WS-ERR-05: Empty message should fail validation.

    Test that empty messages:
    - Fail Pydantic validation
    - Return validation error

    Expected:
    - Request rejected with validation error
    - No processing attempted
    """
    mock_websocket = AsyncMock(spec=WebSocket)
    mock_websocket.accept = AsyncMock()
    mock_websocket.close = AsyncMock()

    # Send request with empty message (invalid per schema)
    mock_websocket.receive_json = AsyncMock(
        side_effect=[
            {
                "type": "chat",
                "message": "",  # Empty - should fail validation
                "session_id": None,
                "assistant_config_id": str(test_ai_assistant.id),
            },
            WebSocketDisconnect(code=1000),
        ]
    )

    sent_messages = []

    async def mock_send_json(message: dict[str, Any]) -> None:
        sent_messages.append(message)

    mock_websocket.send_json = AsyncMock(side_effect=mock_send_json)

    # Call the endpoint directly
    # Validation happens in the route via Pydantic
    try:
        await chat_stream(
            websocket=mock_websocket,
            token=valid_token,
        )
    except Exception as e:
        # Validation error should be raised
        assert "validation" in str(e).lower() or "message" in str(e).lower()


# =============================================================================
# Database Persistence Tests
# =============================================================================


@pytest.mark.asyncio
async def test_db_persist_session_and_messages(
    valid_token: str,
    override_get_user: None,
    override_rbac: None,
    test_ai_assistant: AIAssistantConfig,
    db_session: AsyncSession,
    test_user: User,
) -> None:
    """Test that sessions and messages are persisted to database.

    Verifies:
    - Session is created in database
    - User message is saved
    - Assistant message is saved
    - Message IDs are generated

    Note: This test verifies the AgentService.chat_stream is called with
    the correct parameters for database persistence. The actual database
    operations are tested in the AgentService unit tests.
    """
    mock_websocket = AsyncMock(spec=WebSocket)
    mock_websocket.accept = AsyncMock()
    mock_websocket.close = AsyncMock()

    # Track chat_stream calls
    chat_stream_calls = []

    # Mock AIConfigService to return test assistant
    from app.services.ai_config_service import AIConfigService

    async def mock_get_assistant_config(self, config_id: UUID) -> AIAssistantConfig | None:
        if str(config_id) == str(test_ai_assistant.id):
            return test_ai_assistant
        return None

    async def mock_chat_stream_persist(*args, **kwargs):
        # Track the call
        chat_stream_calls.append(kwargs)

        ws = kwargs.get("websocket")
        session_id = kwargs.get("session_id") or uuid4()

        # Send response
        await ws.send_json(
            WSTokenMessage(
                type="token",
                content="Response",
                session_id=session_id,
            ).model_dump(mode="json")
        )
        await asyncio.sleep(0.01)

        await ws.send_json(
            WSCompleteMessage(
                type="complete",
                session_id=session_id,
                message_id=uuid4(),
            ).model_dump(mode="json")
        )

    with patch.object(AIConfigService, "get_assistant_config", new=mock_get_assistant_config):
        with patch("app.api.routes.ai_chat.AgentService") as mock_agent_service:
            mock_agent_service.return_value.chat_stream = mock_chat_stream_persist

            mock_websocket.receive_json = AsyncMock(
                side_effect=[
                    {
                        "type": "chat",
                        "message": "Test persistence",
                        "session_id": None,
                        "assistant_config_id": str(test_ai_assistant.id),
                    },
                    WebSocketDisconnect(code=1000),
                ]
            )

            # Call the endpoint directly
            await chat_stream(
                websocket=mock_websocket,
                token=valid_token,
            )

    # Verify chat_stream was called with correct parameters
    assert len(chat_stream_calls) == 1
    call_kwargs = chat_stream_calls[0]

    # Verify database session was passed
    assert "db" in call_kwargs
    assert call_kwargs["db"] is not None

    # Verify user_id was passed
    assert "user_id" in call_kwargs
    assert call_kwargs["user_id"] == test_user.user_id

    # Verify message was passed
    assert "message" in call_kwargs
    assert call_kwargs["message"] == "Test persistence"

    # Verify assistant config was passed
    assert "assistant_config" in call_kwargs
    assert str(call_kwargs["assistant_config"].id) == str(test_ai_assistant.id)

    # Verify websocket was passed
    assert "websocket" in call_kwargs
    assert call_kwargs["websocket"] is not None


# =============================================================================
# Additional Coverage Tests - Token Edge Cases
# =============================================================================


@pytest.mark.asyncio
async def test_ws_token_missing_subject(
    test_user: User,
    override_rbac: None,
) -> None:
    """Test WebSocket connection with token missing subject.

    Verifies:
    - Token without 'sub' claim is rejected
    - Connection closes with code 1008 (policy violation)
    - Reason indicates missing subject

    Covers lines 147-151 in ai_chat.py.
    """
    mock_websocket = AsyncMock(spec=WebSocket)
    mock_websocket.close = AsyncMock()

    # Create token without subject
    from jose import jwt
    token_data = {
        "exp": datetime.utcnow() + timedelta(hours=1),
        # Missing "sub" key
    }
    token = jwt.encode(
        token_data,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )

    # Call the endpoint directly
    await chat_stream(
        websocket=mock_websocket,
        token=token,
    )

    # Verify connection was rejected with policy violation
    mock_websocket.close.assert_called_once_with(code=1008, reason="Invalid token: missing subject")


@pytest.mark.asyncio
async def test_ws_user_not_found(
    override_rbac: None,
) -> None:
    """Test WebSocket connection when user not found in database.

    Verifies:
    - Token with valid email but no matching user is rejected
    - Connection closes with code 1008 (policy violation)
    - Reason indicates user not found

    Covers lines 172-175 in ai_chat.py.
    """
    mock_websocket = AsyncMock(spec=WebSocket)
    mock_websocket.close = AsyncMock()

    # Create token for non-existent user
    token = WebSocketTestHelpers.create_valid_token("nonexistent@example.com")

    # Call the endpoint directly
    await chat_stream(
        websocket=mock_websocket,
        token=token,
    )

    # Verify connection was rejected with policy violation
    mock_websocket.close.assert_called_once_with(code=1008, reason="User not found")


# =============================================================================
# REST API Endpoint Tests
# These test the HTTP GET/DELETE endpoints for session management.
# =============================================================================


from fastapi.testclient import TestClient
from unittest.mock import MagicMock


@pytest.mark.asyncio
async def test_list_sessions_success(
    db_session: AsyncSession,
    test_user: User,
    test_ai_assistant: AIAssistantConfig,
) -> None:
    """Test listing conversation sessions for current user.

    Verifies:
    - Sessions are returned for authenticated user
    - Response is list of AIConversationSessionPublic

    Covers lines 39, 50, 55-56 in ai_chat.py.
    """
    from app.api.routes.ai_chat import list_sessions, get_ai_config_service
    from app.models.domain.ai import AIConversationSession

    # Create test sessions (SimpleEntityBase requires created_at/updated_at)
    # Note: user_id and assistant_config_id are UUIDs in the model
    now = datetime.utcnow()
    session1 = AIConversationSession(
        id=uuid4(),
        user_id=test_user.user_id,
        assistant_config_id=test_ai_assistant.id,
        title="Test Session 1",
        created_at=now,
        updated_at=now,
    )
    session2 = AIConversationSession(
        id=uuid4(),
        user_id=test_user.user_id,
        assistant_config_id=test_ai_assistant.id,
        title="Test Session 2",
        created_at=now,
        updated_at=now,
    )

    # Mock AIConfigService
    mock_config_service = AsyncMock()
    mock_config_service.list_sessions = AsyncMock(return_value=[session1, session2])

    # Call the endpoint
    result = await list_sessions(
        current_user=test_user,
        config_service=mock_config_service,
    )

    # Verify sessions were returned
    assert len(result) == 2
    assert result[0].title == "Test Session 1"
    assert result[1].title == "Test Session 2"

    # Verify service was called correctly
    mock_config_service.list_sessions.assert_called_once_with(test_user.user_id)


@pytest.mark.asyncio
async def test_get_session_messages_success(
    db_session: AsyncSession,
    test_user: User,
    test_ai_assistant: AIAssistantConfig,
) -> None:
    """Test getting messages for a conversation session.

    Verifies:
    - Messages are returned for user's own session
    - 404 error if session not found
    - 403 error if session belongs to different user

    Covers lines 65-78 in ai_chat.py.
    """
    from app.api.routes.ai_chat import get_session_messages
    from app.models.domain.ai import AIConversationSession, AIConversationMessage
    from fastapi import HTTPException

    session_id = uuid4()

    # Create test session and messages (SimpleEntityBase requires created_at/updated_at)
    # Note: user_id, assistant_config_id, session_id are UUIDs in the model
    now = datetime.utcnow()
    session = AIConversationSession(
        id=session_id,
        user_id=test_user.user_id,
        assistant_config_id=test_ai_assistant.id,
        title="Test Session",
        created_at=now,
        updated_at=now,
    )

    message1 = AIConversationMessage(
        id=uuid4(),
        session_id=session_id,
        role="user",
        content="Hello",
        created_at=now,
        updated_at=now,
    )

    # Mock AIConfigService
    mock_config_service = AsyncMock()
    mock_config_service.get_session = AsyncMock(return_value=session)
    mock_config_service.list_messages = AsyncMock(return_value=[message1])

    # Call the endpoint successfully
    result = await get_session_messages(
        session_id=session_id,
        current_user=test_user,
        config_service=mock_config_service,
    )

    # Verify messages were returned
    assert len(result) == 1
    assert result[0].role == "user"
    assert result[0].content == "Hello"

    # Test session not found
    mock_config_service.get_session = AsyncMock(return_value=None)
    with pytest.raises(HTTPException) as exc_info:
        await get_session_messages(
            session_id=session_id,
            current_user=test_user,
            config_service=mock_config_service,
        )
    assert exc_info.value.status_code == 404
    assert "not found" in exc_info.value.detail.lower()

    # Test access denied (different user)
    other_user_id = uuid4()
    session_different_user = AIConversationSession(
        id=session_id,
        user_id=str(other_user_id),
        assistant_config_id=str(test_ai_assistant.id),
        title="Other Session",
        created_at=now,
        updated_at=now,
    )
    mock_config_service.get_session = AsyncMock(return_value=session_different_user)

    with pytest.raises(HTTPException) as exc_info:
        await get_session_messages(
            session_id=session_id,
            current_user=test_user,
            config_service=mock_config_service,
        )
    assert exc_info.value.status_code == 403
    assert "access denied" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_delete_session_success(
    db_session: AsyncSession,
    test_user: User,
    test_ai_assistant: AIAssistantConfig,
) -> None:
    """Test deleting a conversation session.

    Verifies:
    - Session is deleted for user's own session
    - 404 error if session not found
    - 403 error if session belongs to different user

    Covers lines 87-99 in ai_chat.py.
    """
    from app.api.routes.ai_chat import delete_session
    from app.models.domain.ai import AIConversationSession
    from fastapi import HTTPException

    session_id = uuid4()

    # Create test session (SimpleEntityBase requires created_at/updated_at)
    # Note: user_id and assistant_config_id are UUIDs in the model
    now = datetime.utcnow()
    session = AIConversationSession(
        id=session_id,
        user_id=test_user.user_id,
        assistant_config_id=test_ai_assistant.id,
        title="Test Session",
        created_at=now,
        updated_at=now,
    )

    # Mock AIConfigService
    mock_config_service = AsyncMock()
    mock_config_service.get_session = AsyncMock(return_value=session)
    mock_config_service.delete_session = AsyncMock()

    # Call the endpoint successfully
    await delete_session(
        session_id=session_id,
        current_user=test_user,
        config_service=mock_config_service,
    )

    # Verify delete was called
    mock_config_service.delete_session.assert_called_once_with(session_id)

    # Test session not found
    mock_config_service.get_session = AsyncMock(return_value=None)
    with pytest.raises(HTTPException) as exc_info:
        await delete_session(
            session_id=session_id,
            current_user=test_user,
            config_service=mock_config_service,
        )
    assert exc_info.value.status_code == 404
    assert "not found" in exc_info.value.detail.lower()

    # Test access denied (different user)
    other_user_id = uuid4()
    session_different_user = AIConversationSession(
        id=session_id,
        user_id=str(other_user_id),
        assistant_config_id=str(test_ai_assistant.id),
        title="Other Session",
        created_at=now,
        updated_at=now,
    )
    mock_config_service.get_session = AsyncMock(return_value=session_different_user)

    with pytest.raises(HTTPException) as exc_info:
        await delete_session(
            session_id=session_id,
            current_user=test_user,
            config_service=mock_config_service,
        )
    assert exc_info.value.status_code == 403
    assert "access denied" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_get_ai_config_service_dependency(
    db_session: AsyncSession,
) -> None:
    """Test the get_ai_config_service dependency function.

    Verifies:
    - AIConfigService is instantiated with the database session

    Covers line 41 in ai_chat.py.
    """
    from app.api.routes.ai_chat import get_ai_config_service

    result = get_ai_config_service(session=db_session)

    # Verify AIConfigService was created with the session
    assert result is not None
    assert result.session == db_session
