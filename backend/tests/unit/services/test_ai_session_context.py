"""Tests for Phase 3E: Session Context Enhancement."""

from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schemas.ai import AIConversationSessionCreate, AIConversationSessionPublic
from app.services.ai_config_service import AIConfigService


@pytest.mark.asyncio
async def test_create_session_with_project_context(db_session: AsyncSession) -> None:
    """Test creating a session with project context."""
    from app.models.schemas.ai import AIAssistantConfigCreate, AIModelCreate, AIProviderCreate

    service = AIConfigService(db_session)

    # Setup: Create provider, model, and assistant config
    provider = await service.create_provider(
        AIProviderCreate(provider_type="openai", name="Test Provider")
    )

    model = await service.create_model(
        AIModelCreate(
            provider_id=provider.id,
            model_id="gpt-4",
            display_name="GPT-4",
        )
    )

    assistant = await service.create_assistant_config(
        AIAssistantConfigCreate(
            name="Test Assistant",
            model_id=model.id,
            allowed_tools=[],
        )
    )

    # Test: Create session with project_id
    user_id = uuid4()
    project_id = uuid4()
    branch_id = uuid4()

    session = await service.create_session(
        user_id=user_id,
        assistant_config_id=assistant.id,
        title="Test Session with Context",
        project_id=project_id,
        branch_id=branch_id,
    )

    # Verify session was created with context
    assert session.id is not None
    assert session.user_id == str(user_id)
    assert session.assistant_config_id == str(assistant.id)
    assert session.title == "Test Session with Context"
    assert session.project_id == str(project_id)
    assert session.branch_id == str(branch_id)


@pytest.mark.asyncio
async def test_create_session_without_context(db_session: AsyncSession) -> None:
    """Test creating a session without project/branch context."""
    from app.models.schemas.ai import AIAssistantConfigCreate, AIModelCreate, AIProviderCreate

    service = AIConfigService(db_session)

    # Setup: Create provider, model, and assistant config
    provider = await service.create_provider(
        AIProviderCreate(provider_type="openai", name="Test Provider")
    )

    model = await service.create_model(
        AIModelCreate(
            provider_id=provider.id,
            model_id="gpt-4",
            display_name="GPT-4",
        )
    )

    assistant = await service.create_assistant_config(
        AIAssistantConfigCreate(
            name="Test Assistant",
            model_id=model.id,
            allowed_tools=[],
        )
    )

    # Test: Create session without context (backward compatibility)
    user_id = uuid4()

    session = await service.create_session(
        user_id=user_id,
        assistant_config_id=assistant.id,
        title="Test Session without Context",
        project_id=None,
        branch_id=None,
    )

    # Verify session was created without context
    assert session.id is not None
    assert session.user_id == str(user_id)
    assert session.assistant_config_id == str(assistant.id)
    assert session.title == "Test Session without Context"
    assert session.project_id is None
    assert session.branch_id is None


@pytest.mark.asyncio
async def test_session_schema_serialization_with_context(db_session: AsyncSession) -> None:
    """Test that AIConversationSessionPublic serializes context fields correctly."""
    from app.models.schemas.ai import AIAssistantConfigCreate, AIModelCreate, AIProviderCreate

    service = AIConfigService(db_session)

    # Setup: Create provider, model, and assistant config
    provider = await service.create_provider(
        AIProviderCreate(provider_type="openai", name="Test Provider")
    )

    model = await service.create_model(
        AIModelCreate(
            provider_id=provider.id,
            model_id="gpt-4",
            display_name="GPT-4",
        )
    )

    assistant = await service.create_assistant_config(
        AIAssistantConfigCreate(
            name="Test Assistant",
            model_id=model.id,
            allowed_tools=[],
        )
    )

    # Create session with context
    user_id = uuid4()
    project_id = uuid4()
    branch_id = uuid4()

    session = await service.create_session(
        user_id=user_id,
        assistant_config_id=assistant.id,
        project_id=project_id,
        branch_id=branch_id,
    )

    # Test serialization
    public_schema = AIConversationSessionPublic.model_validate(session)

    assert public_schema.id == session.id
    assert public_schema.user_id == user_id
    assert public_schema.project_id == project_id
    assert public_schema.branch_id == branch_id
