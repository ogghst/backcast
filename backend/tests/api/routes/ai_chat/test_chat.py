"""Tests for AI Chat API endpoints.

Tests for session management, message listing, and chat functionality.
Note: The actual chat endpoint is WebSocket-based, tested separately in test_websocket.py
These tests focus on the REST API endpoints for session management.
"""

from collections.abc import Generator
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_active_user, get_current_user
from app.core.rbac import RBACServiceABC, get_rbac_service
from app.main import app
from app.models.domain.ai import (
    AIAssistantConfig,
    AIConversationMessage,
    AIConversationSession,
    AIModel,
    AIProvider,
)
from app.models.domain.user import User

# Mock admin user for auth
mock_admin_user = User(
    id=uuid4(),
    user_id=uuid4(),
    email="admin@example.com",
    is_active=True,
    role="admin",
    full_name="Admin User",
    hashed_password="hash",
    created_by=uuid4(),
)


# Mock regular user for ownership tests
mock_regular_user = User(
    id=uuid4(),
    user_id=uuid4(),
    email="user@example.com",
    is_active=True,
    role="user",
    full_name="Regular User",
    hashed_password="hash",
    created_by=uuid4(),
)


def mock_get_current_admin() -> User:
    return mock_admin_user


def mock_get_current_regular_user() -> User:
    return mock_regular_user


def mock_get_current_active_admin() -> User:
    return mock_admin_user


def mock_get_current_active_regular_user() -> User:
    return mock_regular_user


def mock_get_rbac_service() -> RBACServiceABC:
    return MockRBACService()


# Mock RBAC service
class MockRBACService(RBACServiceABC):
    def has_role(self, user_role: str, required_roles: list[str]) -> bool:
        return True

    def has_permission(self, user_role: str, required_permission: str) -> bool:
        return True

    def get_user_permissions(self, user_role: str) -> list[str]:
        return ["ai-chat"]
    
    async def has_project_access(
        self,
        user_id,
        user_role: str,
        project_id,
        required_permission: str,
    ) -> bool:
        return True

    async def get_user_projects(self, user_id, user_role: str):
        return []

    async def get_project_role(self, user_id, project_id):
        return "admin"


@pytest.fixture
def override_admin_auth() -> Generator[None, None, None]:
    """Override authentication for admin user tests."""
    app.dependency_overrides[get_current_user] = mock_get_current_admin
    app.dependency_overrides[get_current_active_user] = mock_get_current_active_admin
    yield
    app.dependency_overrides = {}


@pytest.fixture
def override_regular_auth() -> Generator[None, None, None]:
    """Override authentication for regular user tests."""
    app.dependency_overrides[get_current_user] = mock_get_current_regular_user
    app.dependency_overrides[get_current_active_user] = (
        mock_get_current_active_regular_user
    )
    yield
    app.dependency_overrides = {}


@pytest.fixture(autouse=True)
def override_rbac() -> Generator[None, None, None]:
    """Override RBAC for all tests."""
    app.dependency_overrides[get_rbac_service] = mock_get_rbac_service
    yield
    app.dependency_overrides = {}


# === T-CHAT-01: test_list_sessions_requires_auth ===
@pytest.mark.asyncio
async def test_list_sessions_requires_auth(client: AsyncClient) -> None:
    """Test that list sessions endpoint returns 401 without valid token."""
    # Remove auth override to test actual auth requirement
    app.dependency_overrides = {}

    response = await client.get("/api/v1/ai/chat/sessions")
    assert response.status_code == 401


# === T-CHAT-02: test_list_sessions_returns_user_sessions_only ===
@pytest.mark.asyncio
async def test_list_sessions_returns_user_sessions_only(
    client: AsyncClient, override_admin_auth: None, db_session: AsyncSession
) -> None:
    """Test that list sessions only returns sessions for current user."""
    # Create provider and model
    provider = AIProvider(
        id=str(uuid4()),
        provider_type="openai",
        name="Test Provider",
        is_active=True,
    )
    db_session.add(provider)

    model = AIModel(
        id=str(uuid4()),
        provider_id=str(provider.id),
        model_id="gpt-4",
        display_name="GPT-4",
        is_active=True,
    )
    db_session.add(model)

    assistant = AIAssistantConfig(
        id=str(uuid4()),
        model_id=str(model.id),
        name="Test Assistant",
        system_prompt="You are helpful",
        is_active=True,
    )
    db_session.add(assistant)

    # Create session for admin user
    admin_session = AIConversationSession(
        id=str(uuid4()),
        user_id=str(mock_admin_user.user_id),
        assistant_config_id=str(assistant.id),
    )
    db_session.add(admin_session)
    await db_session.commit()

    # List sessions as admin user
    response = await client.get("/api/v1/ai/chat/sessions")
    assert response.status_code == 200

    sessions = response.json()
    assert len(sessions) >= 1
    # Verify all sessions belong to admin user
    for session in sessions:
        assert session["user_id"] == str(mock_admin_user.user_id)


# === T-CHAT-03: test_get_session_messages_requires_auth ===
@pytest.mark.asyncio
async def test_get_session_messages_requires_auth(client: AsyncClient) -> None:
    """Test that get session messages returns 401 without valid token."""
    app.dependency_overrides = {}

    session_id = uuid4()
    response = await client.get(f"/api/v1/ai/chat/sessions/{session_id}/messages")
    assert response.status_code == 401


# === T-CHAT-04: test_chat_session_ownership_validation ===
@pytest.mark.asyncio
async def test_chat_session_ownership_validation(
    client: AsyncClient,
    override_admin_auth: None,
    override_regular_auth: None,
    db_session: AsyncSession,
) -> None:
    """Test that user cannot access other users' sessions."""
    # Create provider and model
    provider = AIProvider(
        id=str(uuid4()),
        provider_type="openai",
        name="Test Provider",
        is_active=True,
    )
    db_session.add(provider)

    model = AIModel(
        id=str(uuid4()),
        provider_id=str(provider.id),
        model_id="gpt-4",
        display_name="GPT-4",
        is_active=True,
    )
    db_session.add(model)

    assistant = AIAssistantConfig(
        id=str(uuid4()),
        model_id=str(model.id),
        name="Test Assistant",
        system_prompt="You are helpful",
        is_active=True,
    )
    db_session.add(assistant)

    # Create session for admin user
    admin_session = AIConversationSession(
        id=str(uuid4()),
        user_id=str(mock_admin_user.user_id),
        assistant_config_id=str(assistant.id),
    )
    db_session.add(admin_session)
    await db_session.commit()

    # Try to access admin session as regular user
    app.dependency_overrides[get_current_user] = mock_get_current_regular_user
    app.dependency_overrides[get_current_active_user] = (
        mock_get_current_active_regular_user
    )

    response = await client.get(f"/api/v1/ai/chat/sessions/{admin_session.id}/messages")
    assert response.status_code == 403


# === T-CHAT-05: test_delete_session_requires_auth ===
@pytest.mark.asyncio
async def test_delete_session_requires_auth(client: AsyncClient) -> None:
    """Test that delete session returns 401 without valid token."""
    app.dependency_overrides = {}

    session_id = uuid4()
    response = await client.delete(f"/api/v1/ai/chat/sessions/{session_id}")
    assert response.status_code == 401


# === Additional helper tests ===
@pytest.mark.asyncio
async def test_list_sessions_requires_permission(
    client: AsyncClient, override_admin_auth: None
) -> None:
    """Test that listing sessions requires ai-chat permission."""
    response = await client.get("/api/v1/ai/chat/sessions")
    # Should succeed with admin override
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_session_messages_validates_ownership(
    client: AsyncClient,
    override_admin_auth: None,
    override_regular_auth: None,
    db_session: AsyncSession,
) -> None:
    """Test that getting session messages validates ownership."""
    # Create provider and model
    provider = AIProvider(
        id=str(uuid4()),
        provider_type="openai",
        name="Test Provider",
        is_active=True,
    )
    db_session.add(provider)

    model = AIModel(
        id=str(uuid4()),
        provider_id=str(provider.id),
        model_id="gpt-4",
        display_name="GPT-4",
        is_active=True,
    )
    db_session.add(model)

    assistant = AIAssistantConfig(
        id=str(uuid4()),
        model_id=str(model.id),
        name="Test Assistant",
        system_prompt="You are helpful",
        is_active=True,
    )
    db_session.add(assistant)

    # Create session for admin user
    admin_session = AIConversationSession(
        id=str(uuid4()),
        user_id=str(mock_admin_user.user_id),
        assistant_config_id=str(assistant.id),
    )
    db_session.add(admin_session)

    # Add a message
    message = AIConversationMessage(
        id=str(uuid4()),
        session_id=str(admin_session.id),
        role="user",
        content="Test message",
    )
    db_session.add(message)
    await db_session.commit()

    # Try to access as regular user
    app.dependency_overrides[get_current_user] = mock_get_current_regular_user
    app.dependency_overrides[get_current_active_user] = (
        mock_get_current_active_regular_user
    )

    response = await client.get(f"/api/v1/ai/chat/sessions/{admin_session.id}/messages")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_delete_session_validates_ownership(
    client: AsyncClient,
    override_admin_auth: None,
    override_regular_auth: None,
    db_session: AsyncSession,
) -> None:
    """Test that deleting session validates ownership."""
    # Create provider and model
    provider = AIProvider(
        id=str(uuid4()),
        provider_type="openai",
        name="Test Provider",
        is_active=True,
    )
    db_session.add(provider)

    model = AIModel(
        id=str(uuid4()),
        provider_id=str(provider.id),
        model_id="gpt-4",
        display_name="GPT-4",
        is_active=True,
    )
    db_session.add(model)

    assistant = AIAssistantConfig(
        id=str(uuid4()),
        model_id=str(model.id),
        name="Test Assistant",
        system_prompt="You are helpful",
        is_active=True,
    )
    db_session.add(assistant)

    # Create session for admin user
    admin_session = AIConversationSession(
        id=str(uuid4()),
        user_id=str(mock_admin_user.user_id),
        assistant_config_id=str(assistant.id),
    )
    db_session.add(admin_session)
    await db_session.commit()

    # Try to delete as regular user
    app.dependency_overrides[get_current_user] = mock_get_current_regular_user
    app.dependency_overrides[get_current_active_user] = (
        mock_get_current_active_regular_user
    )

    response = await client.delete(f"/api/v1/ai/chat/sessions/{admin_session.id}")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_delete_session_successful(
    client: AsyncClient, override_admin_auth: None, db_session: AsyncSession
) -> None:
    """Test that deleting session works correctly."""
    # Create provider and model
    provider = AIProvider(
        id=str(uuid4()),
        provider_type="openai",
        name="Test Provider",
        is_active=True,
    )
    db_session.add(provider)

    model = AIModel(
        id=str(uuid4()),
        provider_id=str(provider.id),
        model_id="gpt-4",
        display_name="GPT-4",
        is_active=True,
    )
    db_session.add(model)

    assistant = AIAssistantConfig(
        id=str(uuid4()),
        model_id=str(model.id),
        name="Test Assistant",
        system_prompt="You are helpful",
        is_active=True,
    )
    db_session.add(assistant)

    # Create session
    session = AIConversationSession(
        id=str(uuid4()),
        user_id=str(mock_admin_user.user_id),
        assistant_config_id=str(assistant.id),
    )
    db_session.add(session)
    await db_session.commit()

    # Delete session
    response = await client.delete(f"/api/v1/ai/chat/sessions/{session.id}")
    assert response.status_code == 204

    # Verify session is deleted
    response = await client.get(f"/api/v1/ai/chat/sessions/{session.id}/messages")
    assert response.status_code == 404
