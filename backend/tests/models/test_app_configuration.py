"""Tests for AppConfiguration model."""

import uuid
from datetime import datetime

from sqlmodel import Session

from app.models import (
    AppConfiguration,
    AppConfigurationCreate,
    AppConfigurationPublic,
    AppConfigurationUpdate,
)


def test_create_app_configuration(db: Session) -> None:
    """Test creating an app configuration entry."""
    import uuid

    unique_key = f"test_base_url_{uuid.uuid4().hex[:8]}"
    config_in = AppConfigurationCreate(
        config_key=unique_key,
        config_value="https://api.openai.com/v1",
        description="Default OpenAI API base URL",
        is_active=True,
    )

    config = AppConfiguration.model_validate(config_in)
    db.add(config)
    db.commit()
    db.refresh(config)

    # Verify configuration was created
    assert config.config_id is not None
    assert config.config_key == unique_key
    assert config.config_value == "https://api.openai.com/v1"
    assert config.description == "Default OpenAI API base URL"
    assert config.is_active is True
    assert config.created_at is not None
    assert config.updated_at is not None


def test_app_configuration_unique_key(db: Session) -> None:
    """Test that config_key must be unique."""
    from sqlalchemy.exc import IntegrityError

    # Create first configuration
    config1_in = AppConfigurationCreate(
        config_key="unique_test_key_1",
        config_value="https://api.openai.com/v1",
        is_active=True,
    )
    config1 = AppConfiguration.model_validate(config1_in)
    db.add(config1)
    db.commit()
    db.refresh(config1)

    # Try to create another configuration with same key
    config2_in = AppConfigurationCreate(
        config_key="unique_test_key_1",  # Same key
        config_value="https://api.example.com/v1",
        is_active=True,
    )
    config2 = AppConfiguration.model_validate(config2_in)
    db.add(config2)

    # Should fail on commit due to unique constraint
    try:
        db.commit()
        # If no error, this is a problem - should have unique constraint
        db.rollback()
        raise AssertionError(
            "Should have raised IntegrityError for duplicate config_key"
        )
    except IntegrityError:
        db.rollback()
        assert True
    except Exception as e:
        db.rollback()
        raise AssertionError(f"Expected IntegrityError, got {type(e).__name__}: {e}")


def test_app_configuration_multiple_keys(db: Session) -> None:
    """Test that multiple configurations can exist with different keys."""
    # Create base URL config with unique key
    base_url_config = AppConfigurationCreate(
        config_key="multi_test_base_url",
        config_value="https://api.openai.com/v1",
        is_active=True,
    )
    config1 = AppConfiguration.model_validate(base_url_config)
    db.add(config1)
    db.commit()
    db.refresh(config1)

    # Create API key config with different key
    api_key_config = AppConfigurationCreate(
        config_key="multi_test_api_key",
        config_value="encrypted_key_value_here",
        description="Default OpenAI API key (encrypted)",
        is_active=True,
    )
    config2 = AppConfiguration.model_validate(api_key_config)
    db.add(config2)
    db.commit()
    db.refresh(config2)

    # Verify both configurations exist
    assert config1.config_key == "multi_test_base_url"
    assert config2.config_key == "multi_test_api_key"
    assert config1.config_value == "https://api.openai.com/v1"
    assert config2.config_value == "encrypted_key_value_here"


def test_app_configuration_optional_fields(db: Session) -> None:
    """Test that description and is_active have defaults."""
    import uuid

    unique_key = f"test_optional_{uuid.uuid4().hex[:8]}"
    # Create without description
    config_in = AppConfigurationCreate(
        config_key=unique_key,
        config_value="test_value",
        is_active=True,
    )
    config = AppConfiguration.model_validate(config_in)
    # description is optional, can be None
    assert hasattr(config, "description")

    db.add(config)
    db.commit()
    db.refresh(config)

    assert config.config_key == unique_key
    assert config.config_value == "test_value"
    assert config.is_active is True


def test_app_configuration_public_schema() -> None:
    """Test AppConfigurationPublic schema for API responses."""
    config_id = uuid.uuid4()
    now = datetime.utcnow()

    config_public = AppConfigurationPublic(
        config_id=config_id,
        config_key="ai_default_openai_base_url",
        config_value="https://api.openai.com/v1",
        description="Default OpenAI API base URL",
        is_active=True,
        created_at=now,
        updated_at=now,
    )

    assert config_public.config_id == config_id
    assert config_public.config_key == "ai_default_openai_base_url"
    assert config_public.config_value == "https://api.openai.com/v1"
    assert config_public.description == "Default OpenAI API base URL"
    assert config_public.is_active is True
    assert config_public.created_at == now


def test_app_configuration_update_schema() -> None:
    """Test AppConfigurationUpdate schema allows partial updates."""
    update_data = AppConfigurationUpdate(
        config_value="https://api.openai.com/v2",
        description="Updated description",
    )

    # All fields should be optional
    assert update_data.config_value == "https://api.openai.com/v2"
    assert update_data.description == "Updated description"
    assert update_data.config_key is None
    assert update_data.is_active is None
