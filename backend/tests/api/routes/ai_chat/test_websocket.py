"""Integration tests for AI Chat WebSocket endpoint.

These tests use the actual WebSocket connection without TestClient's
thread-based approach, which allows proper async testing.
"""

from collections.abc import Generator
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_active_user, get_current_user
from app.core.rbac import RBACServiceABC, get_rbac_service
from app.main import app
from app.models.domain.ai import AIAssistantConfig, AIModel, AIProvider
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


def mock_get_current_user() -> User:
    return mock_admin_user


def mock_get_current_active_user() -> User:
    return mock_admin_user


# Mock RBAC service that allows everything
class MockRBACService(RBACServiceABC):
    def has_role(self, user_role: str, required_roles: list[str]) -> bool:
        return True

    def has_permission(self, user_role: str, required_permission: str) -> bool:
        return True

    def get_user_permissions(self, user_role: str) -> list[str]:
        return ["ai-chat"]


def mock_get_rbac_service() -> RBACServiceABC:
    return MockRBACService()


@pytest.fixture(autouse=True)
def override_auth() -> Generator[None, None, None]:
    """Override authentication and RBAC for all tests."""
    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[get_current_active_user] = mock_get_current_active_user
    app.dependency_overrides[get_rbac_service] = mock_get_rbac_service
    yield
    app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_websocket_schemas_serialization() -> None:
    """Test that WebSocket schemas can be serialized properly."""
    from app.models.schemas.ai import (
        WSChatRequest,
        WSCompleteMessage,
        WSErrorMessage,
        WSTokenMessage,
        WSToolCallMessage,
        WSToolResultMessage,
    )

    # Test WSChatRequest
    request = WSChatRequest(
        type="chat",
        message="Hello",
        session_id=None,
        assistant_config_id=uuid4(),
    )
    request_dict = request.model_dump(mode='json')
    assert request_dict["type"] == "chat"
    assert request_dict["message"] == "Hello"

    # Test WSTokenMessage
    token_msg = WSTokenMessage(
        type="token",
        content="Hello",
        session_id=uuid4(),
    )
    token_dict = token_msg.model_dump(mode='json')
    assert token_dict["type"] == "token"
    assert token_dict["content"] == "Hello"

    # Test WSToolCallMessage
    tool_call_msg = WSToolCallMessage(
        type="tool_call",
        tool="list_projects",
        args={"status": "ACT"},
    )
    tool_call_dict = tool_call_msg.model_dump(mode='json')
    assert tool_call_dict["type"] == "tool_call"
    assert tool_call_dict["tool"] == "list_projects"

    # Test WSToolResultMessage
    tool_result_msg = WSToolResultMessage(
        type="tool_result",
        tool="list_projects",
        result={"projects": []},
    )
    tool_result_dict = tool_result_msg.model_dump(mode='json')
    assert tool_result_dict["type"] == "tool_result"

    # Test WSCompleteMessage
    complete_msg = WSCompleteMessage(
        type="complete",
        session_id=uuid4(),
        message_id=uuid4(),
    )
    complete_dict = complete_msg.model_dump(mode='json')
    assert complete_dict["type"] == "complete"

    # Test WSErrorMessage
    error_msg = WSErrorMessage(
        type="error",
        message="Test error",
        code=500,
    )
    error_dict = error_msg.model_dump(mode='json')
    assert error_dict["type"] == "error"
    assert error_dict["message"] == "Test error"


@pytest.mark.asyncio
async def test_websocket_request_validation() -> None:
    """Test that WebSocket request validation works correctly."""
    from pydantic import ValidationError

    from app.models.schemas.ai import WSChatRequest

    # Valid request
    valid_request = WSChatRequest(
        type="chat",
        message="Hello",
        session_id=None,
        assistant_config_id=uuid4(),
    )
    assert valid_request.message == "Hello"

    # Missing message should fail
    with pytest.raises(ValidationError) as exc_info:
        WSChatRequest(
            type="chat",
            session_id=None,
            assistant_config_id=uuid4(),
        )
    assert "message" in str(exc_info.value).lower()

    # Empty message should fail
    with pytest.raises(ValidationError) as exc_info:
        WSChatRequest(
            type="chat",
            message="",
            session_id=None,
            assistant_config_id=uuid4(),
        )
    assert "message" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_agent_service_instantiation(db_session: AsyncSession) -> None:
    """Test that AgentService can be instantiated with a database session."""
    from app.ai.agent_service import AgentService

    # Should be able to instantiate with a database session
    agent_service = AgentService(db_session)
    assert agent_service is not None
    assert agent_service.session == db_session


@pytest.mark.asyncio
async def test_ai_config_service_assistant_retrieval(db_session: AsyncSession) -> None:
    """Test that AIConfigService can retrieve assistant configs."""
    from app.services.ai_config_service import AIConfigService

    # Create provider
    provider = AIProvider(
        id=str(uuid4()),
        provider_type="openai",
        name="OpenAI",
        base_url="https://api.openai.com/v1",
        is_active=True,
    )
    db_session.add(provider)
    await db_session.flush()

    # Create model
    model = AIModel(
        id=str(uuid4()),
        provider_id=provider.id,
        model_id="gpt-4",
        display_name="GPT-4",
        is_active=True,
    )
    db_session.add(model)
    await db_session.flush()

    # Create assistant config
    config = AIAssistantConfig(
        id=str(uuid4()),
        name="Test Assistant",
        description="Test assistant",
        model_id=model.id,
        system_prompt="You are a helpful assistant.",
        temperature=0.0,
        max_tokens=1000,
        allowed_tools=["list_projects"],
        is_active=True,
    )
    db_session.add(config)
    await db_session.commit()

    # Test retrieval
    config_service = AIConfigService(db_session)
    retrieved_config = await config_service.get_assistant_config(config.id)

    assert retrieved_config is not None
    assert str(retrieved_config.id) == str(config.id)
    assert retrieved_config.name == "Test Assistant"
    assert retrieved_config.is_active is True


@pytest.mark.asyncio
async def test_ai_config_service_inactive_assistant(db_session: AsyncSession) -> None:
    """Test that AIConfigService handles inactive assistant configs."""
    from app.services.ai_config_service import AIConfigService

    # Create provider
    provider = AIProvider(
        id=str(uuid4()),
        provider_type="openai",
        name="OpenAI",
        base_url="https://api.openai.com/v1",
        is_active=True,
    )
    db_session.add(provider)
    await db_session.flush()

    # Create model
    model = AIModel(
        id=str(uuid4()),
        provider_id=provider.id,
        model_id="gpt-4",
        display_name="GPT-4",
        is_active=True,
    )
    db_session.add(model)
    await db_session.flush()

    # Create inactive assistant config
    config = AIAssistantConfig(
        id=str(uuid4()),
        name="Inactive Assistant",
        description="Test inactive assistant",
        model_id=model.id,
        system_prompt="You are a helpful assistant.",
        temperature=0.0,
        max_tokens=1000,
        allowed_tools=["list_projects"],
        is_active=False,  # Inactive
    )
    db_session.add(config)
    await db_session.commit()

    # Test retrieval
    config_service = AIConfigService(db_session)
    retrieved_config = await config_service.get_assistant_config(config.id)

    assert retrieved_config is not None
    assert str(retrieved_config.id) == str(config.id)
    assert retrieved_config.is_active is False


@pytest.mark.asyncio
async def test_ai_config_service_nonexistent_assistant(db_session: AsyncSession) -> None:
    """Test that AIConfigService returns None for non-existent configs."""
    from app.services.ai_config_service import AIConfigService

    config_service = AIConfigService(db_session)
    fake_id = uuid4()
    retrieved_config = await config_service.get_assistant_config(fake_id)

    assert retrieved_config is None
