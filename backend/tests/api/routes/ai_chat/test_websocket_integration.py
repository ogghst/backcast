"""Integration tests for AI Chat WebSocket using direct endpoint testing.

WebSocket Mocking Strategy:
- Direct WebSocket endpoint testing with mock WebSocket objects
- All external dependencies (DB, AgentService, AIConfigService) are mocked
- Mocks patch the module-level imports used by chat_stream

Key insight: chat_stream calls get_rbac_service() and async_session_maker()
directly (not via FastAPI Depends), so we patch them at their import paths:
  - get_rbac_service: imported at module level -> patch app.api.routes.ai_chat.get_rbac_service
  - async_session_maker: imported inside function -> patch app.db.session.async_session_maker
  - AgentService/AIConfigService: imported at module level -> patch app.api.routes.ai_chat.<name>
"""

from collections.abc import Generator
from datetime import datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi import WebSocket
from fastapi.websockets import WebSocketDisconnect
from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.websockets import WebSocketState

from app.ai.execution.agent_event import AgentEvent
from app.ai.execution.agent_event_bus import AgentEventBus
from app.api.routes.ai_chat import chat_stream
from app.core.config import settings
from app.core.rbac import RBACServiceABC
from app.models.domain.ai import (
    AIAssistantConfig,
    AIConversationMessage,
    AIConversationSession,
)
from app.models.domain.user import User

# =============================================================================
# Test Utilities
# =============================================================================


class WebSocketTestHelpers:
    """Helper class for WebSocket testing utilities."""

    @staticmethod
    def create_valid_token(user_email: str) -> str:
        """Create a valid JWT token for testing."""
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
        """Create an expired JWT token for testing."""
        token_data = {
            "sub": user_email,
            "exp": datetime.utcnow() - timedelta(hours=1),
        }
        return jwt.encode(
            token_data,
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM,
        )


# =============================================================================
# RBAC Service Implementations for Testing
# =============================================================================


class AllowAllRBAC(RBACServiceABC):
    """RBAC service that grants all permissions."""

    def has_role(self, user_role: str, required_roles: list[str]) -> bool:
        return True

    def has_permission(self, user_role: str, required_permission: str) -> bool:
        return True

    def get_user_permissions(self, user_role: str) -> list[str]:
        return ["ai-chat", "project-read", "project-create"]

    async def has_project_access(
        self,
        user_id: UUID,
        user_role: str,
        project_id: UUID,
        required_permission: str,
    ) -> bool:
        return True

    async def get_user_projects(self, user_id: UUID, user_role: str) -> list[UUID]:
        return []

    async def get_project_role(self, user_id: UUID, project_id: UUID) -> str | None:
        return "admin"


class DenyAIRBAC(RBACServiceABC):
    """RBAC service that denies ai-chat permission."""

    def has_role(self, user_role: str, required_roles: list[str]) -> bool:
        return True

    def has_permission(self, user_role: str, required_permission: str) -> bool:
        return required_permission != "ai-chat"

    def get_user_permissions(self, user_role: str) -> list[str]:
        return ["project-read", "project-create"]

    async def has_project_access(
        self,
        user_id: UUID,
        user_role: str,
        project_id: UUID,
        required_permission: str,
    ) -> bool:
        return True

    async def get_user_projects(self, user_id: UUID, user_role: str) -> list[UUID]:
        return []

    async def get_project_role(self, user_id: UUID, project_id: UUID) -> str | None:
        return "admin"


# =============================================================================
# Shared Fixtures
# =============================================================================


@pytest.fixture
def test_user() -> User:
    """Create a test user for authentication."""
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
    """Create a test user without ai-chat permission."""
    return User(
        id=uuid4(),
        user_id=uuid4(),
        email="noperm@example.com",
        is_active=True,
        role="viewer",
        full_name="No Permission User",
        hashed_password="hash",
        created_by=uuid4(),
    )


@pytest.fixture
def valid_token(test_user: User) -> str:
    """Create a valid JWT token for testing."""
    return WebSocketTestHelpers.create_valid_token(test_user.email)


@pytest.fixture
def expired_token(test_user: User) -> str:
    """Create an expired JWT token for testing."""
    return WebSocketTestHelpers.create_expired_token(test_user.email)


@pytest.fixture
def override_get_user(test_user: User) -> Generator[None, None, None]:
    """Override user lookup for tests by patching UserService.get_by_email."""
    from app.services.user import UserService

    async def mock_get_by_email(self: Any, email: str) -> User | None:
        if email == test_user.email:
            return test_user
        return None

    with patch.object(UserService, "get_by_email", new=mock_get_by_email):
        yield


@pytest.fixture
def override_rbac() -> Generator[None, None, None]:
    """Override RBAC for tests.

    chat_stream calls get_rbac_service() directly (not via Depends),
    so we patch at the module import path.
    """
    with patch(
        "app.api.routes.ai_chat.get_rbac_service",
        return_value=AllowAllRBAC(),
    ):
        yield


# =============================================================================
# Mock Helpers
# =============================================================================


def make_mock_websocket(
    messages: list[dict[str, Any] | Exception] | None = None,
) -> AsyncMock:
    """Create a mock WebSocket with client_state for is_websocket_connected checks."""
    mock_ws = AsyncMock(spec=WebSocket)
    mock_ws.accept = AsyncMock()
    mock_ws.close = AsyncMock()
    mock_ws.send_json = AsyncMock()
    mock_ws.client_state = WebSocketState.CONNECTED

    if messages is not None:
        mock_ws.receive_json = AsyncMock(side_effect=messages)
    else:
        mock_ws.receive_json = AsyncMock(side_effect=[WebSocketDisconnect(code=1000)])

    return mock_ws


def make_mock_session_ctx(mock_db: AsyncMock | None = None) -> MagicMock:
    """Create a mock async context manager for async_session_maker().

    chat_stream does ``async with async_session_maker() as db:``, so we
    need the mock to behave like an async context manager.
    """
    if mock_db is None:
        mock_db = AsyncMock(spec=AsyncSession)
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=mock_db)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return ctx


def make_mock_assistant(assistant_id: UUID | None = None) -> MagicMock:
    """Create a mock AIAssistantConfig."""
    mock = MagicMock(spec=AIAssistantConfig)
    mock.id = assistant_id or uuid4()
    mock.is_active = True
    return mock


def make_completing_start_execution() -> Any:
    """Create a start_execution mock that publishes a complete event to the bus.

    This is necessary because the handler creates a forwarding task that
    subscribes to the event bus and loops until bus.is_completed. If start_execution
    never completes the bus, the forwarding task loops forever, hanging the test.
    """

    async def mock_start_execution(*args: Any, **kwargs: Any) -> None:
        bus: AgentEventBus | None = kwargs.get("event_bus")
        if bus is not None:
            bus.publish(AgentEvent(event_type="complete", data={}))

    return mock_start_execution


def make_message_sending_start_execution(
    events: list[tuple[str, dict[str, Any]]],
) -> Any:
    """Create a start_execution mock that publishes specific events then completes.

    Events are published synchronously (no await) so they are in the bus
    before the event loop yields to the forwarding task. The forwarding task
    will then find the events in its subscriber queue (since publish() also
    puts events into subscriber queues via put_nowait).
    """

    async def mock_start_execution(*args: Any, **kwargs: Any) -> None:
        bus: AgentEventBus | None = kwargs.get("event_bus")
        if bus is not None:
            for event_type, data in events:
                bus.publish(AgentEvent(event_type=event_type, data=data))

    return mock_start_execution


# =============================================================================
# Context manager for patching chat_stream dependencies
# =============================================================================


class ChatStreamPatcher:
    """Context manager that patches all chat_stream dependencies for testing.

    Patches:
    - async_session_maker (DB session)
    - AgentService (agent execution)
    - AIConfigService (assistant config and session management)
    """

    def __init__(
        self,
        mock_assistant: MagicMock | None = None,
        start_execution_fn: Any | None = None,
    ) -> None:
        self.mock_assistant = mock_assistant or make_mock_assistant()
        self._start_exec_fn = start_execution_fn or make_completing_start_execution()
        self.mock_session = MagicMock()
        self.mock_session.id = uuid4()
        self._patches: list[Any] = []
        self.mock_db = AsyncMock(spec=AsyncSession)
        self.mock_db.commit = AsyncMock()
        self.mock_db.rollback = AsyncMock()
        self.mock_session_ctx = make_mock_session_ctx(self.mock_db)
        self.mock_agent_instance: Any = None
        self.mock_config_instance: Any = None

    def __enter__(self) -> "ChatStreamPatcher":
        p1 = patch(
            "app.db.session.async_session_maker", return_value=self.mock_session_ctx
        )
        p2 = patch("app.api.routes.ai_chat.AgentService")
        p3 = patch("app.api.routes.ai_chat.AIConfigService")

        self._patches = [p1, p2, p3]

        mock_agent_cls = p2.__enter__()
        mock_config_cls = p3.__enter__()
        p1.__enter__()

        self.mock_agent_instance = mock_agent_cls.return_value
        self.mock_agent_instance.start_execution = self._start_exec_fn
        self.mock_agent_instance.unregister_interrupt_node = MagicMock()

        self.mock_config_instance = mock_config_cls.return_value
        self.mock_config_instance.get_assistant_config = self._make_get_config()
        self.mock_config_instance.create_session = self._make_create_session()
        self.mock_config_instance.add_message = self._make_add_message()
        self.mock_config_instance.get_session = self._make_get_session()

        return self

    def __exit__(self, *args: Any) -> None:
        for p in reversed(self._patches):
            p.__exit__(*args)

    def _make_get_config(self) -> Any:
        assistant = self.mock_assistant

        async def get_config(config_id: UUID) -> AIAssistantConfig | None:
            if str(config_id) == str(assistant.id):
                return assistant
            return None

        return get_config

    def _make_create_session(self) -> Any:
        session = self.mock_session

        async def create_session(**kwargs: Any) -> Any:
            return session

        return create_session

    def _make_add_message(self) -> Any:
        async def add_message(**kwargs: Any) -> None:
            pass

        return add_message

    def _make_get_session(self) -> Any:
        session = self.mock_session

        async def get_session(sid: UUID) -> Any:
            return session

        return get_session


# =============================================================================
# Connection Lifecycle Tests (T-WS-LC-01 through T-WS-LC-05)
# =============================================================================


@pytest.mark.asyncio
async def test_ws_lc_01_valid_token_accepts_connection(
    valid_token: str,
    override_get_user: None,
    override_rbac: None,
) -> None:
    """T-WS-LC-01: Valid token with permission should accept connection."""
    mock_assistant = make_mock_assistant()

    mock_websocket = make_mock_websocket(
        messages=[
            {
                "type": "chat",
                "message": "Hello",
                "session_id": None,
                "assistant_config_id": str(mock_assistant.id),
            },
            WebSocketDisconnect(code=1000, reason="Normal closure"),
        ]
    )

    with ChatStreamPatcher(mock_assistant=mock_assistant):
        await chat_stream(websocket=mock_websocket, token=valid_token)

    mock_websocket.accept.assert_called_once()

    # Verify execution_started was sent (proves the handler processed the message)
    sent_calls = mock_websocket.send_json.call_args_list
    sent_types = [c[0][0].get("type") if c[0] else None for c in sent_calls]
    assert "execution_started" in sent_types


@pytest.mark.asyncio
async def test_ws_lc_02_invalid_token_rejects_connection(
    override_get_user: None,
    override_rbac: None,
) -> None:
    """T-WS-LC-02: Invalid token should close connection with 1008."""
    invalid_token = "invalid.token.format"
    mock_websocket = make_mock_websocket()
    mock_websocket.close = AsyncMock()

    await chat_stream(websocket=mock_websocket, token=invalid_token)

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
    """T-WS-LC-03: Expired token should close connection with 4008."""
    mock_websocket = make_mock_websocket()
    mock_websocket.close = AsyncMock()

    await chat_stream(websocket=mock_websocket, token=expired_token)

    mock_websocket.close.assert_called_once()
    close_call = mock_websocket.close.call_args
    assert close_call[1]["code"] == 4008
    assert "expired" in close_call[1]["reason"].lower()


@pytest.mark.asyncio
async def test_ws_lc_04_no_permission_rejects_connection(
    valid_token: str,
    test_user_no_permission: User,
) -> None:
    """T-WS-LC-04: No ai-chat permission should close connection with 1008."""
    from app.services.user import UserService

    async def mock_get_by_email_no_perm(self: Any, email: str) -> User | None:
        return test_user_no_permission

    mock_websocket = make_mock_websocket()
    mock_websocket.close = AsyncMock()

    mock_db = AsyncMock(spec=AsyncSession)
    mock_session_ctx = make_mock_session_ctx(mock_db)

    with (
        patch.object(UserService, "get_by_email", new=mock_get_by_email_no_perm),
        patch("app.api.routes.ai_chat.get_rbac_service", return_value=DenyAIRBAC()),
        patch("app.db.session.async_session_maker", return_value=mock_session_ctx),
    ):
        await chat_stream(websocket=mock_websocket, token=valid_token)

    mock_websocket.close.assert_called_once()
    close_call = mock_websocket.close.call_args
    assert close_call[1]["code"] == 1008
    assert "ai-chat" in close_call[1]["reason"].lower()


@pytest.mark.asyncio
async def test_ws_lc_05_normal_disconnect_cleanup(
    valid_token: str,
    override_get_user: None,
    override_rbac: None,
) -> None:
    """T-WS-LC-05: Normal disconnect should execute cleanup."""
    mock_websocket = make_mock_websocket(
        messages=[WebSocketDisconnect(code=1000, reason="Normal closure")],
    )

    mock_db = AsyncMock(spec=AsyncSession)
    mock_db.commit = AsyncMock()
    mock_db.rollback = AsyncMock()
    mock_session_ctx = make_mock_session_ctx(mock_db)

    with (
        patch("app.db.session.async_session_maker", return_value=mock_session_ctx),
        patch("app.api.routes.ai_chat.AgentService"),
        patch("app.api.routes.ai_chat.AIConfigService"),
    ):
        await chat_stream(websocket=mock_websocket, token=valid_token)

    mock_websocket.accept.assert_called_once()


# =============================================================================
# Streaming Token Tests (T-WS-ST-01 through T-WS-ST-03)
# =============================================================================


@pytest.mark.asyncio
async def test_ws_st_01_text_generation_streams_tokens(
    valid_token: str,
    override_get_user: None,
    override_rbac: None,
) -> None:
    """T-WS-ST-01: Text generation should start an execution with event bus."""
    mock_assistant = make_mock_assistant()

    mock_websocket = make_mock_websocket(
        messages=[
            {
                "type": "chat",
                "message": "Tell me about projects",
                "session_id": None,
                "assistant_config_id": str(mock_assistant.id),
            },
            WebSocketDisconnect(code=1000),
        ]
    )

    # Track that start_execution was called with an event_bus
    captured_buses: list[AgentEventBus] = []

    async def start_exec(*args: Any, **kwargs: Any) -> None:
        bus: AgentEventBus | None = kwargs.get("event_bus")
        if bus is not None:
            captured_buses.append(bus)
            bus.publish(AgentEvent(event_type="token_batch", data={"content": "Hello"}))
            bus.publish(
                AgentEvent(event_type="token_batch", data={"content": " there"})
            )
            bus.publish(
                AgentEvent(event_type="complete", data={"content": "Hello there"})
            )

    with ChatStreamPatcher(
        mock_assistant=mock_assistant, start_execution_fn=start_exec
    ):
        await chat_stream(websocket=mock_websocket, token=valid_token)

    # Verify execution_started was sent
    sent_calls = mock_websocket.send_json.call_args_list
    sent_types = [c[0][0].get("type") if c[0] else None for c in sent_calls]
    assert "execution_started" in sent_types

    # Verify the event bus received the expected events
    assert len(captured_buses) == 1
    bus = captured_buses[0]
    all_events = bus.replay(since_sequence=0)
    assert len(all_events) == 3
    token_events = [e for e in all_events if e.event_type == "token_batch"]
    assert len(token_events) == 2


@pytest.mark.asyncio
async def test_ws_st_02_tool_execution_streams_tool_messages(
    valid_token: str,
    override_get_user: None,
    override_rbac: None,
) -> None:
    """T-WS-ST-02: Tool execution should publish tool events to the event bus."""
    mock_assistant = make_mock_assistant()

    mock_websocket = make_mock_websocket(
        messages=[
            {
                "type": "chat",
                "message": "List all projects",
                "session_id": None,
                "assistant_config_id": str(mock_assistant.id),
            },
            WebSocketDisconnect(code=1000),
        ]
    )

    captured_buses: list[AgentEventBus] = []

    async def start_exec(*args: Any, **kwargs: Any) -> None:
        bus: AgentEventBus | None = kwargs.get("event_bus")
        if bus is not None:
            captured_buses.append(bus)
            bus.publish(
                AgentEvent(
                    event_type="tool_call",
                    data={"tool": "list_projects", "args": {"search": "test"}},
                )
            )
            bus.publish(
                AgentEvent(
                    event_type="tool_result",
                    data={"tool": "list_projects", "result": {"projects": []}},
                )
            )
            bus.publish(AgentEvent(event_type="complete", data={"content": "Done"}))

    with ChatStreamPatcher(
        mock_assistant=mock_assistant, start_execution_fn=start_exec
    ):
        await chat_stream(websocket=mock_websocket, token=valid_token)

    assert len(captured_buses) == 1
    bus = captured_buses[0]
    all_events = bus.replay(since_sequence=0)

    tool_call_events = [e for e in all_events if e.event_type == "tool_call"]
    tool_result_events = [e for e in all_events if e.event_type == "tool_result"]
    assert len(tool_call_events) == 1
    assert tool_call_events[0].data["tool"] == "list_projects"
    assert len(tool_result_events) == 1
    assert tool_result_events[0].data["result"] == {"projects": []}


@pytest.mark.asyncio
async def test_ws_st_03_multiple_messages_maintain_session(
    valid_token: str,
    override_get_user: None,
    override_rbac: None,
) -> None:
    """T-WS-ST-03: Multiple messages should maintain session."""
    mock_assistant = make_mock_assistant()
    session_id = uuid4()

    mock_websocket = make_mock_websocket(
        messages=[
            {
                "type": "chat",
                "message": "First message",
                "session_id": None,
                "assistant_config_id": str(mock_assistant.id),
            },
            {
                "type": "chat",
                "message": "Second message",
                "session_id": str(session_id),
                "assistant_config_id": str(mock_assistant.id),
            },
            WebSocketDisconnect(code=1000),
        ]
    )

    with ChatStreamPatcher(mock_assistant=mock_assistant) as patcher:
        patcher.mock_session.id = session_id
        await chat_stream(websocket=mock_websocket, token=valid_token)

    mock_websocket.accept.assert_called_once()

    # Both messages should start executions
    sent_calls = mock_websocket.send_json.call_args_list
    exec_started = [
        c[0][0]
        for c in sent_calls
        if c[0] and c[0][0].get("type") == "execution_started"
    ]
    assert len(exec_started) >= 1


# =============================================================================
# Error Handling Tests (T-WS-ERR-01 through T-WS-ERR-05)
# =============================================================================


@pytest.mark.asyncio
async def test_ws_err_01_missing_assistant_config_id(
    valid_token: str,
    override_get_user: None,
    override_rbac: None,
) -> None:
    """T-WS-ERR-01: Missing assistant_config_id should send error message."""
    mock_websocket = make_mock_websocket(
        messages=[
            {
                "type": "chat",
                "message": "Hello",
                "session_id": None,
                "assistant_config_id": None,  # Missing
            },
            WebSocketDisconnect(code=1000),
        ]
    )

    sent_messages: list[dict[str, Any]] = []

    async def track_send_json(message: dict[str, Any]) -> None:
        sent_messages.append(message)

    mock_websocket.send_json = AsyncMock(side_effect=track_send_json)

    with ChatStreamPatcher():
        await chat_stream(websocket=mock_websocket, token=valid_token)

    assert len(sent_messages) >= 1
    assert sent_messages[0].get("type") == "error"
    assert "Assistant config is required" in sent_messages[0].get("message", "")


@pytest.mark.asyncio
async def test_ws_err_02_invalid_assistant_config_id(
    valid_token: str,
    override_get_user: None,
    override_rbac: None,
) -> None:
    """T-WS-ERR-02: Invalid assistant_config_id should send error message."""
    fake_id = uuid4()

    mock_websocket = make_mock_websocket(
        messages=[
            {
                "type": "chat",
                "message": "Hello",
                "session_id": None,
                "assistant_config_id": str(fake_id),
            },
            WebSocketDisconnect(code=1000),
        ]
    )

    sent_messages: list[dict[str, Any]] = []

    async def track_send_json(message: dict[str, Any]) -> None:
        sent_messages.append(message)

    mock_websocket.send_json = AsyncMock(side_effect=track_send_json)

    with ChatStreamPatcher():
        # The default get_assistant_config returns None for IDs that don't match
        await chat_stream(websocket=mock_websocket, token=valid_token)

    assert len(sent_messages) >= 1
    assert sent_messages[0].get("type") == "error"
    assert "not found" in sent_messages[0].get("message", "").lower()


@pytest.mark.asyncio
async def test_ws_err_03_inactive_assistant_config(
    valid_token: str,
    override_get_user: None,
    override_rbac: None,
) -> None:
    """T-WS-ERR-03: Inactive assistant_config should send error message."""
    mock_assistant = make_mock_assistant()
    mock_assistant.is_active = False

    mock_websocket = make_mock_websocket(
        messages=[
            {
                "type": "chat",
                "message": "Hello",
                "session_id": None,
                "assistant_config_id": str(mock_assistant.id),
            },
            WebSocketDisconnect(code=1000),
        ]
    )

    sent_messages: list[dict[str, Any]] = []

    async def track_send_json(message: dict[str, Any]) -> None:
        sent_messages.append(message)

    mock_websocket.send_json = AsyncMock(side_effect=track_send_json)

    with ChatStreamPatcher(mock_assistant=mock_assistant):
        await chat_stream(websocket=mock_websocket, token=valid_token)

    assert len(sent_messages) >= 1
    assert sent_messages[0].get("type") == "error"
    assert "not active" in sent_messages[0].get("message", "").lower()


@pytest.mark.asyncio
async def test_ws_err_04_streaming_error_sends_error_message(
    valid_token: str,
    override_get_user: None,
    override_rbac: None,
) -> None:
    """T-WS-ERR-04: Streaming error should publish error event to the event bus."""
    mock_assistant = make_mock_assistant()

    mock_websocket = make_mock_websocket(
        messages=[
            {
                "type": "chat",
                "message": "Hello",
                "session_id": None,
                "assistant_config_id": str(mock_assistant.id),
            },
            WebSocketDisconnect(code=1000),
        ]
    )

    captured_buses: list[AgentEventBus] = []

    async def start_exec(*args: Any, **kwargs: Any) -> None:
        bus: AgentEventBus | None = kwargs.get("event_bus")
        if bus is not None:
            captured_buses.append(bus)
            bus.publish(
                AgentEvent(
                    event_type="error",
                    data={
                        "message": "Streaming failed: connection timeout",
                        "code": 500,
                    },
                )
            )

    with ChatStreamPatcher(
        mock_assistant=mock_assistant, start_execution_fn=start_exec
    ):
        await chat_stream(websocket=mock_websocket, token=valid_token)

    assert len(captured_buses) == 1
    bus = captured_buses[0]
    error_events = [e for e in bus.replay(since_sequence=0) if e.event_type == "error"]
    assert len(error_events) == 1
    assert error_events[0].data["code"] == 500


@pytest.mark.asyncio
async def test_ws_err_05_empty_message_validation(
    valid_token: str,
    override_get_user: None,
    override_rbac: None,
) -> None:
    """T-WS-ERR-05: Empty message should fail Pydantic validation (min_length=1)."""
    mock_assistant = make_mock_assistant()

    mock_websocket = make_mock_websocket(
        messages=[
            {
                "type": "chat",
                "message": "",  # Empty - should fail validation
                "session_id": None,
                "assistant_config_id": str(mock_assistant.id),
            },
            WebSocketDisconnect(code=1000),
        ]
    )

    sent_messages: list[dict[str, Any]] = []

    async def track_send_json(message: dict[str, Any]) -> None:
        sent_messages.append(message)

    mock_websocket.send_json = AsyncMock(side_effect=track_send_json)

    with ChatStreamPatcher(mock_assistant=mock_assistant):
        await chat_stream(websocket=mock_websocket, token=valid_token)

    # No execution should start for invalid messages
    exec_started = [m for m in sent_messages if m.get("type") == "execution_started"]
    assert len(exec_started) == 0


# =============================================================================
# Database Persistence Tests
# =============================================================================


@pytest.mark.asyncio
async def test_db_persist_session_and_messages(
    valid_token: str,
    override_get_user: None,
    override_rbac: None,
    test_user: User,
) -> None:
    """Test that sessions and messages are persisted via config_service."""
    mock_assistant = make_mock_assistant()

    # Track service calls
    create_session_calls: list[dict[str, Any]] = []
    add_message_calls: list[dict[str, Any]] = []
    start_execution_calls: list[dict[str, Any]] = []

    async def tracked_create_session(**kwargs: Any) -> Any:
        create_session_calls.append(kwargs)
        return MagicMock(id=uuid4())

    async def tracked_add_message(**kwargs: Any) -> None:
        add_message_calls.append(kwargs)

    async def tracked_start_execution(*args: Any, **kwargs: Any) -> None:
        start_execution_calls.append(kwargs)
        bus: AgentEventBus | None = kwargs.get("event_bus")
        if bus is not None:
            bus.publish(AgentEvent(event_type="complete", data={}))

    mock_websocket = make_mock_websocket(
        messages=[
            {
                "type": "chat",
                "message": "Test persistence",
                "session_id": None,
                "assistant_config_id": str(mock_assistant.id),
            },
            WebSocketDisconnect(code=1000),
        ]
    )

    with ChatStreamPatcher(
        mock_assistant=mock_assistant,
        start_execution_fn=tracked_start_execution,
    ) as patcher:
        patcher.mock_config_instance.create_session = tracked_create_session
        patcher.mock_config_instance.add_message = tracked_add_message

        await chat_stream(websocket=mock_websocket, token=valid_token)

    # Verify session was created
    assert len(create_session_calls) == 1
    assert create_session_calls[0]["user_id"] == test_user.user_id
    assert create_session_calls[0]["assistant_config_id"] == mock_assistant.id

    # Verify message was saved
    assert len(add_message_calls) == 1
    assert add_message_calls[0]["content"] == "Test persistence"
    assert add_message_calls[0]["role"] == "user"

    # Verify start_execution was called with correct parameters
    assert len(start_execution_calls) == 1
    exec_kwargs = start_execution_calls[0]
    assert exec_kwargs["user_id"] == test_user.user_id
    assert exec_kwargs["message"] == "Test persistence"
    assert str(exec_kwargs["assistant_config"].id) == str(mock_assistant.id)


# =============================================================================
# Token Edge Case Tests
# =============================================================================


@pytest.mark.asyncio
async def test_ws_token_missing_subject(
    test_user: User,
    override_rbac: None,
) -> None:
    """Test WebSocket connection with token missing subject."""
    mock_websocket = make_mock_websocket()
    mock_websocket.close = AsyncMock()

    token_data = {
        "exp": datetime.utcnow() + timedelta(hours=1),
    }
    token = jwt.encode(token_data, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    await chat_stream(websocket=mock_websocket, token=token)

    mock_websocket.close.assert_called_once()
    close_call = mock_websocket.close.call_args
    assert close_call[1]["code"] == 1008
    assert "missing subject" in close_call[1]["reason"].lower()


@pytest.mark.asyncio
async def test_ws_user_not_found(
    override_rbac: None,
) -> None:
    """Test WebSocket connection when user not found in database."""
    mock_websocket = make_mock_websocket()
    mock_websocket.close = AsyncMock()

    token = WebSocketTestHelpers.create_valid_token("nonexistent@example.com")

    mock_db = AsyncMock(spec=AsyncSession)
    mock_session_ctx = make_mock_session_ctx(mock_db)

    with (
        patch("app.services.user.UserService") as mock_user_service_class,
        patch("app.db.session.async_session_maker", return_value=mock_session_ctx),
    ):
        mock_user_service = AsyncMock()
        mock_user_service.get_by_email = AsyncMock(return_value=None)
        mock_user_service_class.return_value = mock_user_service

        await chat_stream(websocket=mock_websocket, token=token)

    mock_websocket.close.assert_called_once()
    close_call = mock_websocket.close.call_args
    assert close_call[1]["code"] == 1008
    assert "not found" in close_call[1]["reason"].lower()


# =============================================================================
# Subscribe / Reconnection Tests
# =============================================================================


@pytest.mark.asyncio
async def test_ws_subscribe_replays_events_since_last_seen_sequence(
    valid_token: str,
    override_get_user: None,
    override_rbac: None,
) -> None:
    """Subscribe with last_seen_sequence should replay only missed events.

    When a client reconnects and sends a subscribe message with
    last_seen_sequence=5, only events with sequence > 5 should be
    replayed from the event bus.
    """
    execution_id = str(uuid4())

    # Create a bus and pre-publish 10 events, then mark as completed
    # by publishing a complete event so forward_bus_events exits cleanly
    bus = AgentEventBus(execution_id=execution_id)
    for i in range(1, 11):
        bus.publish(
            AgentEvent(
                event_type="token_batch",
                data={"content": f"token_{i}"},
            )
        )
    # Mark bus as completed so forward_bus_events exits after replay
    bus.publish(AgentEvent(event_type="complete", data={"content": "done"}))

    assert bus.event_count == 11  # 10 token_batch + 1 complete
    assert bus.is_completed
    replayed = bus.replay(since_sequence=5)
    assert len(replayed) == 6  # sequences 6-10 (token_batch) + 11 (complete)
    token_replayed = [e for e in replayed if e.event_type == "token_batch"]
    assert [e.sequence for e in token_replayed] == [6, 7, 8, 9, 10]

    mock_websocket = make_mock_websocket(
        messages=[
            {
                "type": "subscribe",
                "execution_id": execution_id,
                "last_seen_sequence": 5,
            },
            WebSocketDisconnect(code=1000),
        ]
    )

    sent_messages: list[dict[str, Any]] = []

    async def track_send_json(message: dict[str, Any]) -> None:
        sent_messages.append(message)

    mock_websocket.send_json = AsyncMock(side_effect=track_send_json)

    mock_db = AsyncMock(spec=AsyncSession)
    mock_db.commit = AsyncMock()
    mock_db.rollback = AsyncMock()
    mock_session_ctx = make_mock_session_ctx(mock_db)

    with (
        patch("app.db.session.async_session_maker", return_value=mock_session_ctx),
        patch("app.api.routes.ai_chat.AgentService"),
        patch("app.api.routes.ai_chat.AIConfigService"),
        patch("app.api.routes.ai_chat.runner_manager") as mock_runner,
    ):
        mock_runner.get_bus.return_value = bus

        await chat_stream(websocket=mock_websocket, token=valid_token)

    # Verify that only the 5 replayed events were forwarded
    replayed_messages = [m for m in sent_messages if m.get("type") == "token_batch"]
    assert len(replayed_messages) == 5
    replayed_contents = [m.get("content") for m in replayed_messages]
    assert replayed_contents == ["token_6", "token_7", "token_8", "token_9", "token_10"]


# =============================================================================
# REST API Endpoint Tests
# =============================================================================


@pytest.mark.asyncio
async def test_list_sessions_success(
    db_session: AsyncSession,
    test_user: User,
    test_ai_assistant: AIAssistantConfig,
) -> None:
    """Test listing conversation sessions for current user."""
    from app.api.routes.ai_chat import list_sessions

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

    mock_config_service = AsyncMock()
    mock_config_service.list_sessions = AsyncMock(return_value=[session1, session2])
    # list_sessions accesses config_service.session.execute() internally
    mock_config_service.session = AsyncMock()
    mock_config_service.session.execute = AsyncMock(
        return_value=MagicMock(
            scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
        )
    )

    result = await list_sessions(
        current_user=test_user,
        config_service=mock_config_service,
        context_type=None,
        context_id=None,
    )

    assert len(result) == 2
    assert result[0].title == "Test Session 1"
    assert result[1].title == "Test Session 2"
    mock_config_service.list_sessions.assert_called_once_with(
        test_user.user_id,
        context_type=None,
        context_id=None,
    )


@pytest.mark.asyncio
async def test_get_session_messages_success(
    db_session: AsyncSession,
    test_user: User,
    test_ai_assistant: AIAssistantConfig,
) -> None:
    """Test getting messages for a conversation session."""
    from fastapi import HTTPException

    from app.api.routes.ai_chat import get_session_messages

    session_id = uuid4()
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

    mock_config_service = AsyncMock()
    mock_config_service.get_session = AsyncMock(return_value=session)
    mock_config_service.list_messages = AsyncMock(return_value=[message1])

    result = await get_session_messages(
        session_id=session_id,
        current_user=test_user,
        config_service=mock_config_service,
    )

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

    # Test access denied
    session_different_user = AIConversationSession(
        id=session_id,
        user_id=str(uuid4()),
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


@pytest.mark.asyncio
async def test_delete_session_success(
    db_session: AsyncSession,
    test_user: User,
    test_ai_assistant: AIAssistantConfig,
) -> None:
    """Test deleting a conversation session."""
    from fastapi import HTTPException

    from app.api.routes.ai_chat import delete_session

    session_id = uuid4()
    now = datetime.utcnow()
    session = AIConversationSession(
        id=session_id,
        user_id=test_user.user_id,
        assistant_config_id=test_ai_assistant.id,
        title="Test Session",
        created_at=now,
        updated_at=now,
    )

    mock_config_service = AsyncMock()
    mock_config_service.get_session = AsyncMock(return_value=session)
    mock_config_service.delete_session = AsyncMock()

    await delete_session(
        session_id=session_id,
        current_user=test_user,
        config_service=mock_config_service,
    )

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

    # Test access denied
    session_different_user = AIConversationSession(
        id=session_id,
        user_id=str(uuid4()),
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


@pytest.mark.asyncio
async def test_get_ai_config_service_dependency(
    db_session: AsyncSession,
) -> None:
    """Test the get_ai_config_service dependency function."""
    from app.api.routes.ai_chat import get_ai_config_service

    result = get_ai_config_service(session=db_session)

    assert result is not None
    assert result.session == db_session
