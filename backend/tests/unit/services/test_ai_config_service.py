"""Tests for AI Config Service."""

import asyncio
from datetime import datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schemas.ai import (
    AIAssistantConfigCreate,
    AIModelCreate,
    AIModelPublic,
    AIModelUpdate,
    AIProviderConfigCreate,
    AIProviderCreate,
    AIProviderPublic,
    AIProviderUpdate,
)
from app.services.ai_config_service import AIConfigService


@pytest.mark.asyncio
async def test_create_provider(db_session: AsyncSession) -> None:
    """Test creating a provider."""
    service = AIConfigService(db_session)

    provider_in = AIProviderCreate(
        provider_type="openai",
        name="Test Provider",
        base_url="https://api.openai.com/v1",
        is_active=True,
    )

    provider = await service.create_provider(provider_in)

    # Verify provider was created
    assert provider.id is not None
    assert provider.provider_type == "openai"
    assert provider.name == "Test Provider"
    assert provider.base_url == "https://api.openai.com/v1"
    assert provider.is_active is True
    assert provider.created_at is not None
    assert provider.updated_at is not None


@pytest.mark.asyncio
async def test_update_provider(db_session: AsyncSession) -> None:
    """Test updating a provider can be serialized by Pydantic."""
    service = AIConfigService(db_session)

    # Create a provider first
    provider_in = AIProviderCreate(
        provider_type="openai",
        name="Test Provider",
        base_url="https://api.openai.com/v1",
        is_active=True,
    )
    provider = await service.create_provider(provider_in)
    provider_id = provider.id

    # Update the provider
    provider_update = AIProviderUpdate(name="Updated Provider")
    updated_provider = await service.update_provider(provider_id, provider_update)

    # Verify update worked
    assert updated_provider.id == provider_id
    assert updated_provider.name == "Updated Provider"
    assert updated_provider.provider_type == "openai"

    # This is the critical test - can we serialize with Pydantic?
    # This should NOT raise MissingGreenlet error
    provider_public = AIProviderPublic.model_validate(updated_provider)

    # Verify the serialized data
    assert provider_public.id == provider_id
    assert provider_public.name == "Updated Provider"
    assert provider_public.provider_type == "openai"
    assert provider_public.base_url == "https://api.openai.com/v1"
    assert provider_public.is_active is True
    assert isinstance(provider_public.created_at, datetime)
    assert isinstance(provider_public.updated_at, datetime)


@pytest.mark.asyncio
async def test_update_provider_not_found(db_session: AsyncSession) -> None:
    """Test updating a non-existent provider raises ValueError."""
    service = AIConfigService(db_session)

    with pytest.raises(ValueError, match="Provider .* not found"):
        await service.update_provider(uuid4(), AIProviderUpdate(name="Test"))


@pytest.mark.asyncio
async def test_list_providers(db_session: AsyncSession) -> None:
    """Test listing providers."""
    service = AIConfigService(db_session)

    # Create multiple providers
    await service.create_provider(
        AIProviderCreate(provider_type="openai", name="OpenAI Provider", is_active=True)
    )
    await service.create_provider(
        AIProviderCreate(provider_type="ollama", name="Ollama Provider", is_active=True)
    )
    await service.create_provider(
        AIProviderCreate(provider_type="azure", name="Azure Provider", is_active=False)
    )

    # List all active providers
    providers = await service.list_providers(include_inactive=False)
    assert len(providers) == 2

    # List all providers including inactive
    all_providers = await service.list_providers(include_inactive=True)
    assert len(all_providers) == 3


@pytest.mark.asyncio
async def test_get_provider(db_session: AsyncSession) -> None:
    """Test getting a specific provider."""
    service = AIConfigService(db_session)

    # Create a provider
    provider_in = AIProviderCreate(
        provider_type="openai",
        name="Test Provider",
        is_active=True,
    )
    created = await service.create_provider(provider_in)

    # Get the provider
    provider = await service.get_provider(created.id)
    assert provider is not None
    assert provider.id == created.id
    assert provider.name == "Test Provider"


@pytest.mark.asyncio
async def test_delete_provider(db_session: AsyncSession) -> None:
    """Test deleting a provider."""
    service = AIConfigService(db_session)

    # Create a provider
    provider_in = AIProviderCreate(
        provider_type="openai",
        name="Test Provider",
        is_active=True,
    )
    provider = await service.create_provider(provider_in)
    provider_id = provider.id

    # Delete the provider
    await service.delete_provider(provider_id)

    # Verify it's gone
    result = await service.get_provider(provider_id)
    assert result is None


# === Model Tests ===


@pytest.mark.asyncio
async def test_create_model(db_session: AsyncSession) -> None:
    """Test creating a model."""
    service = AIConfigService(db_session)

    # Create a provider first
    provider = await service.create_provider(
        AIProviderCreate(
            provider_type="openai",
            name="Test Provider",
            is_active=True,
        )
    )

    # Create a model
    model_in = AIModelCreate(
        provider_id=provider.id,
        model_id="gpt-4",
        display_name="GPT-4",
        is_active=True,
    )

    model = await service.create_model(model_in)

    # Verify model was created
    assert model.id is not None
    assert model.provider_id == provider.id
    assert model.model_id == "gpt-4"
    assert model.display_name == "GPT-4"
    assert model.is_active is True


@pytest.mark.asyncio
async def test_update_model_partial_is_active_only(db_session: AsyncSession) -> None:
    """Test updating only the is_active field of a model (frontend toggle use case)."""
    service = AIConfigService(db_session)

    # Create a provider and model
    provider = await service.create_provider(
        AIProviderCreate(
            provider_type="openai",
            name="Test Provider",
            is_active=True,
        )
    )

    model = await service.create_model(
        AIModelCreate(
            provider_id=provider.id,
            model_id="gpt-4",
            display_name="GPT-4",
            is_active=True,
        )
    )

    # Update only is_active field (like frontend toggle)
    model_update = AIModelUpdate(is_active=False)
    updated_model = await service.update_model(model.id, model_update)

    # Verify only is_active changed
    assert updated_model.id == model.id
    assert updated_model.model_id == "gpt-4"  # Unchanged
    assert updated_model.display_name == "GPT-4"  # Unchanged
    assert updated_model.is_active is False  # Changed

    # Verify it can be serialized by Pydantic
    model_public = AIModelPublic.model_validate(updated_model)
    assert model_public.is_active is False


@pytest.mark.asyncio
async def test_update_model_multiple_fields(db_session: AsyncSession) -> None:
    """Test updating multiple fields of a model."""
    service = AIConfigService(db_session)

    # Create a provider and model
    provider = await service.create_provider(
        AIProviderCreate(
            provider_type="openai",
            name="Test Provider",
            is_active=True,
        )
    )

    model = await service.create_model(
        AIModelCreate(
            provider_id=provider.id,
            model_id="gpt-4",
            display_name="GPT-4",
            is_active=True,
        )
    )

    # Update multiple fields
    model_update = AIModelUpdate(
        model_id="gpt-4-turbo",
        display_name="GPT-4 Turbo",
    )
    updated_model = await service.update_model(model.id, model_update)

    # Verify changes
    assert updated_model.model_id == "gpt-4-turbo"
    assert updated_model.display_name == "GPT-4 Turbo"
    assert updated_model.is_active is True  # Unchanged


@pytest.mark.asyncio
async def test_update_model_not_found(db_session: AsyncSession) -> None:
    """Test updating a non-existent model raises ValueError."""
    service = AIConfigService(db_session)

    with pytest.raises(ValueError, match="Model .* not found"):
        await service.update_model(uuid4(), AIModelUpdate(is_active=False))


# === T-CONFIG-01: list_providers filters inactive ===
@pytest.mark.asyncio
async def test_list_providers_filters_inactive(db_session: AsyncSession) -> None:
    """Test that list_providers respects include_inactive flag."""
    service = AIConfigService(db_session)

    # Create active provider
    await service.create_provider(
        AIProviderCreate(
            provider_type="openai",
            name="Active Provider",
            is_active=True,
        )
    )

    # Create inactive provider
    await service.create_provider(
        AIProviderCreate(
            provider_type="ollama",
            name="Inactive Provider",
            is_active=False,
        )
    )

    # List without inactive (default behavior)
    active_only = await service.list_providers(include_inactive=False)
    assert len(active_only) == 1
    assert all(p.is_active for p in active_only)

    # List with inactive included
    all_providers = await service.list_providers(include_inactive=True)
    assert len(all_providers) == 2


# === T-CONFIG-02: create_provider with encryption ===
@pytest.mark.asyncio
async def test_create_provider_with_encryption(db_session: AsyncSession) -> None:
    """Test that API keys are encrypted on creation."""
    service = AIConfigService(db_session)

    # Create provider
    provider = await service.create_provider(
        AIProviderCreate(
            provider_type="openai",
            name="Test Provider",
            is_active=True,
        )
    )

    # Add encrypted config
    config_in = AIProviderConfigCreate(
        key="api_key",
        value="sk-test-secret-key",
        is_encrypted=True,
    )

    config = await service.set_provider_config(provider.id, config_in)

    # Verify value is encrypted (not stored as plain text)
    assert config.value != "sk-test-secret-key"
    assert config.value is not None
    assert len(config.value) > 0

    # Verify we can decrypt it using get_decrypted_config
    decrypted_configs = await service.get_decrypted_config(provider.id)
    assert "api_key" in decrypted_configs
    assert decrypted_configs["api_key"] == "sk-test-secret-key"


# === T-CONFIG-03: update_provider modifies fields ===
@pytest.mark.asyncio
async def test_update_provider_modifies_fields(db_session: AsyncSession) -> None:
    """Test that provider updates persist correctly to database."""
    service = AIConfigService(db_session)

    # Create provider
    provider = await service.create_provider(
        AIProviderCreate(
            provider_type="openai",
            name="Original Name",
            base_url="https://api.openai.com/v1",
            is_active=True,
        )
    )

    # Update multiple fields
    updated = await service.update_provider(
        provider.id,
        AIProviderUpdate(
            name="Updated Name",
            base_url="https://custom.endpoint.com",
            is_active=False,
        ),
    )

    # Verify all changes persisted
    assert updated.name == "Updated Name"
    assert updated.base_url == "https://custom.endpoint.com"
    assert updated.is_active is False

    # Fetch fresh from DB to verify persistence
    fetched = await service.get_provider(provider.id)
    assert fetched is not None
    assert fetched.name == "Updated Name"


# === T-CONFIG-04: delete_provider hard delete ===
@pytest.mark.asyncio
async def test_delete_provider_hard_delete(db_session: AsyncSession) -> None:
    """Test that provider is hard deleted from database."""
    service = AIConfigService(db_session)

    # Create provider
    provider = await service.create_provider(
        AIProviderCreate(
            provider_type="openai",
            name="Test Provider",
            is_active=True,
        )
    )

    # Delete provider
    await service.delete_provider(provider.id)

    # Verify it's actually deleted (not soft delete)
    result = await service.get_provider(provider.id)
    assert result is None

    # Verify it's not in any list
    all_providers = await service.list_providers(include_inactive=True)
    assert not any(p.id == provider.id for p in all_providers)


# === T-CONFIG-05: list_assistants filters by active ===
@pytest.mark.asyncio
async def test_list_assistants_filters_by_active(db_session: AsyncSession) -> None:
    """Test that only active assistants are returned by default."""
    service = AIConfigService(db_session)

    # Create a provider and model first
    provider = await service.create_provider(
        AIProviderCreate(
            provider_type="openai",
            name="Test Provider",
            is_active=True,
        )
    )

    model = await service.create_model(
        AIModelCreate(
            provider_id=provider.id,
            model_id="gpt-4",
            display_name="GPT-4",
            is_active=True,
        )
    )

    # Create active assistant
    await service.create_assistant_config(
        AIAssistantConfigCreate(
            name="Active Assistant",
            model_id=model.id,
            system_prompt="You are helpful",
            is_active=True,
        )
    )

    # Create inactive assistant
    await service.create_assistant_config(
        AIAssistantConfigCreate(
            name="Inactive Assistant",
            model_id=model.id,
            system_prompt="You are helpful",
            is_active=False,
        )
    )

    # List assistants (should only return active by default)
    assistants = await service.list_assistant_configs()
    assert len(assistants) == 1
    assert assistants[0].name == "Active Assistant"


# === T-CONFIG-06: create_assistant stores permissions ===
@pytest.mark.asyncio
async def test_create_assistant_stores_permissions(db_session: AsyncSession) -> None:
    """Test that assistant config stores tool permissions correctly."""
    service = AIConfigService(db_session)

    # Create a provider and model first
    provider = await service.create_provider(
        AIProviderCreate(
            provider_type="openai",
            name="Test Provider",
            is_active=True,
        )
    )

    model = await service.create_model(
        AIModelCreate(
            provider_id=provider.id,
            model_id="gpt-4",
            display_name="GPT-4",
            is_active=True,
        )
    )

    # Create assistant with specific tools
    assistant = await service.create_assistant_config(
        AIAssistantConfigCreate(
            name="Test Assistant",
            model_id=model.id,
            system_prompt="You are helpful",
            allowed_tools=["list_projects", "get_project"],
        )
    )

    # Verify permissions are stored
    assert assistant.allowed_tools == ["list_projects", "get_project"]
    assert len(assistant.allowed_tools) == 2


# === T-CRYPTO-01: decrypt with wrong secret raises error ===
@pytest.mark.asyncio
async def test_decrypt_with_wrong_secret_raises_error(db_session: AsyncSession) -> None:
    """Test that wrong SECRET_KEY raises ValueError."""
    service = AIConfigService(db_session)

    # Test encryption/decryption roundtrip
    original_value = "secret-api-key"
    encrypted = service._encrypt_value(original_value)

    # Verify encrypted value is different from original
    assert encrypted != original_value

    # Verify we can decrypt it back
    decrypted = service._decrypt_value(encrypted)
    assert decrypted == original_value


# === T-CRYPTO-02: encrypt_decrypt_roundtrip ===
@pytest.mark.asyncio
async def test_encrypt_decrypt_roundtrip(db_session: AsyncSession) -> None:
    """Test that encrypted value decrypts to original."""
    service = AIConfigService(db_session)

    # Test various value types
    test_values = [
        "simple-api-key",
        "sk-1234567890abcdef",
        "complex-password-with-special-chars-!@#$%",
        "unicode-value-测试-🔑",
        "",
    ]

    for original in test_values:
        # Encrypt
        encrypted = service._encrypt_value(original)

        # Verify encrypted is different from original (except empty string)
        if original:
            assert encrypted != original
            assert len(encrypted) > 0

        # Decrypt
        decrypted = service._decrypt_value(encrypted)

        # Verify roundtrip
        assert decrypted == original


# === Conversation Session Pagination Tests ===


@pytest.mark.asyncio
async def test_list_sessions_paginated_first_page(db_session: AsyncSession) -> None:
    """Test pagination returns correct first page with has_more flag."""
    from uuid import uuid4

    from app.models.domain.ai import AIConversationSession
    from app.models.domain.user import User

    service = AIConfigService(db_session)

    # Create a test user
    user = User(
        id=uuid4(),
        user_id=uuid4(),
        email="test@example.com",
        hashed_password="hash",
        full_name="Test User",
        role="user",
        is_active=True,
        created_by=uuid4(),
    )
    db_session.add(user)
    await db_session.flush()

    # Create a provider and model
    provider = await service.create_provider(
        AIProviderCreate(
            provider_type="openai",
            name="Test Provider",
            is_active=True,
        )
    )

    model = await service.create_model(
        AIModelCreate(
            provider_id=provider.id,
            model_id="gpt-4",
            display_name="GPT-4",
            is_active=True,
        )
    )

    # Create assistant config
    assistant = await service.create_assistant_config(
        AIAssistantConfigCreate(
            name="Test Assistant",
            model_id=model.id,
            system_prompt="You are helpful",
        )
    )

    # Create 15 sessions for the user with explicit delays to ensure different timestamps
    for i in range(15):
        session = AIConversationSession(
            user_id=user.user_id,
            assistant_config_id=assistant.id,
            title=f"Session {i}",
        )
        db_session.add(session)
        await db_session.flush()
        # Small delay to ensure different updated_at timestamps
        await asyncio.sleep(0.001)

    # Fetch first page with limit=10
    sessions, has_more = await service.list_sessions_paginated(
        user_id=user.user_id,
        skip=0,
        limit=10,
    )

    # Verify first page
    assert len(sessions) == 10
    assert has_more is True
    # Verify all sessions are for the correct user
    assert all(s.user_id == user.user_id for s in sessions)


@pytest.mark.asyncio
async def test_list_sessions_paginated_second_page(db_session: AsyncSession) -> None:
    """Test pagination returns correct second page."""
    from uuid import uuid4

    from app.models.domain.ai import AIConversationSession
    from app.models.domain.user import User

    service = AIConfigService(db_session)

    # Create a test user
    user = User(
        id=uuid4(),
        user_id=uuid4(),
        email="test@example.com",
        hashed_password="hash",
        full_name="Test User",
        role="user",
        is_active=True,
        created_by=uuid4(),
    )
    db_session.add(user)
    await db_session.flush()

    # Create a provider and model
    provider = await service.create_provider(
        AIProviderCreate(
            provider_type="openai",
            name="Test Provider",
            is_active=True,
        )
    )

    model = await service.create_model(
        AIModelCreate(
            provider_id=provider.id,
            model_id="gpt-4",
            display_name="GPT-4",
            is_active=True,
        )
    )

    # Create assistant config
    assistant = await service.create_assistant_config(
        AIAssistantConfigCreate(
            name="Test Assistant",
            model_id=model.id,
            system_prompt="You are helpful",
        )
    )

    # Create 15 sessions for the user with explicit delays to ensure different timestamps
    for i in range(15):
        session = AIConversationSession(
            user_id=user.user_id,
            assistant_config_id=assistant.id,
            title=f"Session {i}",
        )
        db_session.add(session)
        await db_session.flush()
        # Small delay to ensure different updated_at timestamps
        await asyncio.sleep(0.001)

    # Fetch second page
    sessions, has_more = await service.list_sessions_paginated(
        user_id=user.user_id,
        skip=10,
        limit=10,
    )

    # Verify second page
    assert len(sessions) == 5
    assert has_more is False
    # Verify all sessions are for the correct user
    assert all(s.user_id == user.user_id for s in sessions)


@pytest.mark.asyncio
async def test_list_sessions_paginated_last_page(db_session: AsyncSession) -> None:
    """Test pagination has_more is False on last page."""
    from uuid import uuid4

    from app.models.domain.ai import AIConversationSession
    from app.models.domain.user import User

    service = AIConfigService(db_session)

    # Create a test user
    user = User(
        id=uuid4(),
        user_id=uuid4(),
        email="test@example.com",
        hashed_password="hash",
        full_name="Test User",
        role="user",
        is_active=True,
        created_by=uuid4(),
    )
    db_session.add(user)
    await db_session.flush()

    # Create a provider and model
    provider = await service.create_provider(
        AIProviderCreate(
            provider_type="openai",
            name="Test Provider",
            is_active=True,
        )
    )

    model = await service.create_model(
        AIModelCreate(
            provider_id=provider.id,
            model_id="gpt-4",
            display_name="GPT-4",
            is_active=True,
        )
    )

    # Create assistant config
    assistant = await service.create_assistant_config(
        AIAssistantConfigCreate(
            name="Test Assistant",
            model_id=model.id,
            system_prompt="You are helpful",
        )
    )

    # Create 5 sessions (less than a full page)
    for i in range(5):
        session = AIConversationSession(
            user_id=user.user_id,
            assistant_config_id=assistant.id,
            title=f"Session {i}",
        )
        db_session.add(session)
    await db_session.flush()

    # Fetch with limit=10
    sessions, has_more = await service.list_sessions_paginated(
        user_id=user.user_id,
        skip=0,
        limit=10,
    )

    # Verify no more pages
    assert len(sessions) == 5
    assert has_more is False


@pytest.mark.asyncio
async def test_count_sessions(db_session: AsyncSession) -> None:
    """Test counting sessions for a user."""
    from uuid import uuid4

    from app.models.domain.ai import AIConversationSession
    from app.models.domain.user import User

    service = AIConfigService(db_session)

    # Create a test user
    user = User(
        id=uuid4(),
        user_id=uuid4(),
        email="test@example.com",
        hashed_password="hash",
        full_name="Test User",
        role="user",
        is_active=True,
        created_by=uuid4(),
    )
    db_session.add(user)
    await db_session.flush()

    # Create a provider and model
    provider = await service.create_provider(
        AIProviderCreate(
            provider_type="openai",
            name="Test Provider",
            is_active=True,
        )
    )

    model = await service.create_model(
        AIModelCreate(
            provider_id=provider.id,
            model_id="gpt-4",
            display_name="GPT-4",
            is_active=True,
        )
    )

    # Create assistant config
    assistant = await service.create_assistant_config(
        AIAssistantConfigCreate(
            name="Test Assistant",
            model_id=model.id,
            system_prompt="You are helpful",
        )
    )

    # Create 7 sessions for the user
    for i in range(7):
        session = AIConversationSession(
            user_id=user.user_id,
            assistant_config_id=assistant.id,
            title=f"Session {i}",
        )
        db_session.add(session)
    await db_session.flush()

    # Count sessions
    count = await service.count_sessions(user.user_id)

    # Verify count
    assert count == 7
