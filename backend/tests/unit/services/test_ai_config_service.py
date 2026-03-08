"""Tests for AI Config Service."""

from datetime import datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schemas.ai import (
    AIModelCreate,
    AIModelPublic,
    AIModelUpdate,
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
async def test_update_provider_updates_timestamp(db_session: AsyncSession) -> None:
    """Test that updating a provider changes the updated_at timestamp."""
    service = AIConfigService(db_session)

    # Create a provider
    provider_in = AIProviderCreate(
        provider_type="openai",
        name="Test Provider",
        is_active=True,
    )
    provider = await service.create_provider(provider_in)
    original_updated_at = provider.updated_at

    # Small delay to ensure timestamp difference
    import asyncio

    await asyncio.sleep(0.01)

    # Update the provider
    provider_update = AIProviderUpdate(name="Updated Provider")
    updated_provider = await service.update_provider(provider.id, provider_update)

    # Verify updated_at changed
    assert updated_provider.updated_at > original_updated_at


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
        AIProviderCreate(
            provider_type="openai", name="OpenAI Provider", is_active=True
        )
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
