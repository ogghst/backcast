"""Tests for AI chat OpenAI configuration retrieval."""

import uuid
from unittest.mock import patch

import pytest
from cryptography.fernet import Fernet
from sqlmodel import Session, select

from app import crud
from app.core.config import settings
from app.core.encryption import encrypt_api_key
from app.models import AppConfiguration, AppConfigurationCreate, UserCreate
from app.services.ai_chat import get_openai_config


def test_get_openai_config_user_has_config(db: Session) -> None:
    """Test getting OpenAI config when user has their own configuration."""
    # Generate a test Fernet key
    test_key = Fernet.generate_key()

    with patch.object(settings, "FERNET_KEY", test_key.decode()):
        # Create user with OpenAI config
        email = f"user_{uuid.uuid4().hex[:8]}@example.com"
        password = "testpassword123"

        # Encrypt API key
        api_key = "sk-test123456789abcdef"
        encrypted_key = encrypt_api_key(api_key)

        user_in = UserCreate(
            email=email,
            password=password,
            openai_base_url="https://api.openai.com/v1",
            openai_api_key_encrypted=encrypted_key,
            openai_model="gpt-4o-mini",
        )
        user = crud.create_user(session=db, user_create=user_in)

        # Get config
        config = get_openai_config(session=db, user_id=user.id)

        # Verify user's config is returned
        assert config["base_url"] == "https://api.openai.com/v1"
        assert config["api_key"] == api_key  # Should be decrypted
        assert config["model"] == "gpt-4o-mini"
        assert config["source"] == "user"


def test_get_openai_config_user_has_only_base_url(db: Session) -> None:
    """Test getting OpenAI config when user has only base URL, falls back to default API key."""
    # Clean up existing configs
    db.exec(
        select(AppConfiguration).where(
            AppConfiguration.config_key.in_(
                ["ai_default_openai_base_url", "ai_default_openai_api_key_encrypted"]
            )
        )
    ).all()
    for config in db.exec(
        select(AppConfiguration).where(
            AppConfiguration.config_key.in_(
                ["ai_default_openai_base_url", "ai_default_openai_api_key_encrypted"]
            )
        )
    ).all():
        db.delete(config)
    db.commit()

    # Generate a test Fernet key
    test_key = Fernet.generate_key()

    with patch.object(settings, "FERNET_KEY", test_key.decode()):
        # Create default config
        default_base_url_config = AppConfigurationCreate(
            config_key="ai_default_openai_base_url",
            config_value="https://api.openai.com/v1/default",
            description="Default OpenAI API base URL",
            is_active=True,
        )
        default_base_url = AppConfiguration.model_validate(default_base_url_config)
        db.add(default_base_url)
        db.commit()
        db.refresh(default_base_url)

        default_api_key = "sk-default123456789"
        encrypted_default_key = encrypt_api_key(default_api_key)

        default_api_key_config = AppConfigurationCreate(
            config_key="ai_default_openai_api_key_encrypted",
            config_value=encrypted_default_key,
            description="Default OpenAI API key (encrypted)",
            is_active=True,
        )
        default_api_key_obj = AppConfiguration.model_validate(default_api_key_config)
        db.add(default_api_key_obj)
        db.commit()
        db.refresh(default_api_key_obj)

        default_model_config = AppConfigurationCreate(
            config_key="ai_default_openai_model",
            config_value="gpt-4o-mini",
            description="Default OpenAI model",
            is_active=True,
        )
        default_model_obj = AppConfiguration.model_validate(default_model_config)
        db.add(default_model_obj)
        db.commit()
        db.refresh(default_model_obj)

        # Create user with only base URL
        email = f"user_{uuid.uuid4().hex[:8]}@example.com"
        password = "testpassword123"
        user_in = UserCreate(
            email=email,
            password=password,
            openai_base_url="https://api.openai.com/v1/user",
        )
        user = crud.create_user(session=db, user_create=user_in)

        # Get config
        config = get_openai_config(session=db, user_id=user.id)

        # Should use user's base URL but default API key and model
        assert config["base_url"] == "https://api.openai.com/v1/user"
        assert config["api_key"] == default_api_key
        assert config["model"] == "gpt-4o-mini"
        assert config["source"] == "mixed"  # User base URL, default API key


def test_get_openai_config_user_has_only_api_key(db: Session) -> None:
    """Test getting OpenAI config when user has only API key, falls back to default base URL."""
    # Clean up existing configs
    for config in db.exec(
        select(AppConfiguration).where(
            AppConfiguration.config_key.in_(
                [
                    "ai_default_openai_base_url",
                    "ai_default_openai_api_key_encrypted",
                    "ai_default_openai_model",
                ]
            )
        )
    ).all():
        db.delete(config)
    db.commit()

    # Generate a test Fernet key
    test_key = Fernet.generate_key()

    with patch.object(settings, "FERNET_KEY", test_key.decode()):
        # Create default config
        default_base_url_config = AppConfigurationCreate(
            config_key="ai_default_openai_base_url",
            config_value="https://api.openai.com/v1/default",
            description="Default OpenAI API base URL",
            is_active=True,
        )
        default_base_url = AppConfiguration.model_validate(default_base_url_config)
        db.add(default_base_url)
        db.commit()
        db.refresh(default_base_url)

        default_model_config = AppConfigurationCreate(
            config_key="ai_default_openai_model",
            config_value="gpt-4o-mini",
            description="Default OpenAI model",
            is_active=True,
        )
        default_model_obj = AppConfiguration.model_validate(default_model_config)
        db.add(default_model_obj)
        db.commit()
        db.refresh(default_model_obj)

        # Create user with only API key
        email = f"user_{uuid.uuid4().hex[:8]}@example.com"
        password = "testpassword123"

        user_api_key = "sk-user123456789"
        encrypted_user_key = encrypt_api_key(user_api_key)

        user_in = UserCreate(
            email=email,
            password=password,
            openai_api_key_encrypted=encrypted_user_key,
        )
        user = crud.create_user(session=db, user_create=user_in)

        # Get config
        config = get_openai_config(session=db, user_id=user.id)

        # Should use default base URL and model but user's API key
        assert config["base_url"] == "https://api.openai.com/v1/default"
        assert config["api_key"] == user_api_key
        assert config["model"] == "gpt-4o-mini"
        assert config["source"] == "mixed"  # Default base URL, user API key


def test_get_openai_config_user_has_no_config_uses_defaults(db: Session) -> None:
    """Test getting OpenAI config when user has no config, uses default app configuration."""
    # Clean up existing configs
    for config in db.exec(
        select(AppConfiguration).where(
            AppConfiguration.config_key.in_(
                [
                    "ai_default_openai_base_url",
                    "ai_default_openai_api_key_encrypted",
                    "ai_default_openai_model",
                ]
            )
        )
    ).all():
        db.delete(config)
    db.commit()

    # Generate a test Fernet key
    test_key = Fernet.generate_key()

    with patch.object(settings, "FERNET_KEY", test_key.decode()):
        # Create default config
        default_base_url_config = AppConfigurationCreate(
            config_key="ai_default_openai_base_url",
            config_value="https://api.openai.com/v1/default",
            description="Default OpenAI API base URL",
            is_active=True,
        )
        default_base_url = AppConfiguration.model_validate(default_base_url_config)
        db.add(default_base_url)
        db.commit()
        db.refresh(default_base_url)

        default_api_key = "sk-default123456789"
        encrypted_default_key = encrypt_api_key(default_api_key)

        default_api_key_config = AppConfigurationCreate(
            config_key="ai_default_openai_api_key_encrypted",
            config_value=encrypted_default_key,
            description="Default OpenAI API key (encrypted)",
            is_active=True,
        )
        default_api_key_obj = AppConfiguration.model_validate(default_api_key_config)
        db.add(default_api_key_obj)
        db.commit()
        db.refresh(default_api_key_obj)

        default_model_config = AppConfigurationCreate(
            config_key="ai_default_openai_model",
            config_value="gpt-4o-mini",
            description="Default OpenAI model",
            is_active=True,
        )
        default_model_obj = AppConfiguration.model_validate(default_model_config)
        db.add(default_model_obj)
        db.commit()
        db.refresh(default_model_obj)

        # Create user without config
        email = f"user_{uuid.uuid4().hex[:8]}@example.com"
        password = "testpassword123"
        user_in = UserCreate(email=email, password=password)
        user = crud.create_user(session=db, user_create=user_in)

        # Get config
        config = get_openai_config(session=db, user_id=user.id)

        # Should use defaults
        assert config["base_url"] == "https://api.openai.com/v1/default"
        assert config["api_key"] == default_api_key
        assert config["model"] == "gpt-4o-mini"
        assert config["source"] == "default"


def test_get_openai_config_no_defaults_raises_error(db: Session) -> None:
    """Test that missing default configuration raises ValueError."""
    # Clean up existing configs
    for config in db.exec(
        select(AppConfiguration).where(
            AppConfiguration.config_key.in_(
                [
                    "ai_default_openai_base_url",
                    "ai_default_openai_api_key_encrypted",
                    "ai_default_openai_model",
                ]
            )
        )
    ).all():
        db.delete(config)
    db.commit()

    # Create user without config
    email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    password = "testpassword123"
    user_in = UserCreate(email=email, password=password)
    user = crud.create_user(session=db, user_create=user_in)

    # Try to get config - should raise error since no defaults exist
    with pytest.raises(ValueError, match="OpenAI base URL not found"):
        get_openai_config(session=db, user_id=user.id)


def test_get_openai_config_user_partial_and_incomplete_defaults(db: Session) -> None:
    """Test behavior when user has partial config and defaults are incomplete."""
    # Clean up existing configs
    for config in db.exec(
        select(AppConfiguration).where(
            AppConfiguration.config_key.in_(
                [
                    "ai_default_openai_base_url",
                    "ai_default_openai_api_key_encrypted",
                    "ai_default_openai_model",
                ]
            )
        )
    ).all():
        db.delete(config)
    db.commit()

    # Generate a test Fernet key
    test_key = Fernet.generate_key()

    with patch.object(settings, "FERNET_KEY", test_key.decode()):
        # Create only default base URL (no default API key)
        default_base_url_config = AppConfigurationCreate(
            config_key="ai_default_openai_base_url",
            config_value="https://api.openai.com/v1/default",
            description="Default OpenAI API base URL",
            is_active=True,
        )
        default_base_url = AppConfiguration.model_validate(default_base_url_config)
        db.add(default_base_url)
        db.commit()
        db.refresh(default_base_url)

        default_model_config = AppConfigurationCreate(
            config_key="ai_default_openai_model",
            config_value="gpt-4o-mini",
            description="Default OpenAI model",
            is_active=True,
        )
        default_model_obj = AppConfiguration.model_validate(default_model_config)
        db.add(default_model_obj)
        db.commit()
        db.refresh(default_model_obj)

        # Create user with only API key (no base URL)
        email = f"user_{uuid.uuid4().hex[:8]}@example.com"
        password = "testpassword123"

        user_api_key = "sk-user123456789"
        encrypted_user_key = encrypt_api_key(user_api_key)

        user_in = UserCreate(
            email=email,
            password=password,
            openai_api_key_encrypted=encrypted_user_key,
        )
        user = crud.create_user(session=db, user_create=user_in)

        # Should use default base URL and model, but user API key
        config = get_openai_config(session=db, user_id=user.id)
        assert config["base_url"] == "https://api.openai.com/v1/default"
        assert config["api_key"] == user_api_key
        assert config["model"] == "gpt-4o-mini"
        assert config["source"] == "mixed"


def test_get_openai_config_user_partial_missing_default_api_key_raises_error(
    db: Session,
) -> None:
    """Test that missing default API key when user doesn't have one raises error."""
    # Clean up existing configs
    for config in db.exec(
        select(AppConfiguration).where(
            AppConfiguration.config_key.in_(
                [
                    "ai_default_openai_base_url",
                    "ai_default_openai_api_key_encrypted",
                    "ai_default_openai_model",
                ]
            )
        )
    ).all():
        db.delete(config)
    db.commit()

    # Create only default base URL (no default API key)
    default_base_url_config = AppConfigurationCreate(
        config_key="ai_default_openai_base_url",
        config_value="https://api.openai.com/v1/default",
        description="Default OpenAI API base URL",
        is_active=True,
    )
    default_base_url = AppConfiguration.model_validate(default_base_url_config)
    db.add(default_base_url)
    db.commit()
    db.refresh(default_base_url)

    # Create user without any config
    email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    password = "testpassword123"
    user_in = UserCreate(email=email, password=password)
    user = crud.create_user(session=db, user_create=user_in)

    # Should raise error since no API key available
    with pytest.raises(ValueError, match="OpenAI API key not found"):
        get_openai_config(session=db, user_id=user.id)


def test_get_openai_config_inactive_default_ignored(db: Session) -> None:
    """Test that inactive default configurations are ignored."""
    # Clean up existing configs
    for config in db.exec(
        select(AppConfiguration).where(
            AppConfiguration.config_key.in_(
                [
                    "ai_default_openai_base_url",
                    "ai_default_openai_api_key_encrypted",
                    "ai_default_openai_model",
                ]
            )
        )
    ).all():
        db.delete(config)
    db.commit()

    # Create inactive default config
    default_base_url_config = AppConfigurationCreate(
        config_key="ai_default_openai_base_url",
        config_value="https://api.openai.com/v1/inactive",
        description="Inactive default OpenAI API base URL",
        is_active=False,  # Inactive
    )
    default_base_url = AppConfiguration.model_validate(default_base_url_config)
    db.add(default_base_url)
    db.commit()
    db.refresh(default_base_url)

    # Create user without config
    email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    password = "testpassword123"
    user_in = UserCreate(email=email, password=password)
    user = crud.create_user(session=db, user_create=user_in)

    # Should raise error since inactive defaults are ignored
    with pytest.raises(ValueError, match="OpenAI base URL not found"):
        get_openai_config(session=db, user_id=user.id)


def test_get_openai_config_decrypts_encrypted_keys(db: Session) -> None:
    """Test that encrypted API keys are properly decrypted."""
    # Generate a test Fernet key
    test_key = Fernet.generate_key()

    with patch.object(settings, "FERNET_KEY", test_key.decode()):
        # Create user with encrypted API key (no default config needed for this test)
        email = f"user_{uuid.uuid4().hex[:8]}@example.com"
        password = "testpassword123"

        api_key = "sk-test-decrypt-123456789"
        encrypted_key = encrypt_api_key(api_key)

        user_in = UserCreate(
            email=email,
            password=password,
            openai_base_url="https://api.openai.com/v1",
            openai_api_key_encrypted=encrypted_key,
            openai_model="gpt-4o-mini",
        )
        user = crud.create_user(session=db, user_create=user_in)

        # Get config
        config = get_openai_config(session=db, user_id=user.id)

        # Verify decrypted key matches original
        assert config["api_key"] == api_key
        assert config["api_key"] != encrypted_key  # Should be decrypted
        assert config["model"] == "gpt-4o-mini"


def test_get_openai_config_returns_user_model(db: Session) -> None:
    """Test that get_openai_config returns model from user configuration."""
    # Generate a test Fernet key
    test_key = Fernet.generate_key()

    with patch.object(settings, "FERNET_KEY", test_key.decode()):
        # Create user with model configured
        email = f"user_{uuid.uuid4().hex[:8]}@example.com"
        password = "testpassword123"

        api_key = "sk-test123456789abcdef"
        encrypted_key = encrypt_api_key(api_key)

        user_in = UserCreate(
            email=email,
            password=password,
            openai_base_url="https://api.deepseek.com/v1",
            openai_api_key_encrypted=encrypted_key,
            openai_model="deepseek-reasoner",
        )
        user = crud.create_user(session=db, user_create=user_in)

        # Get config
        config = get_openai_config(session=db, user_id=user.id)

        # Verify model comes from user config
        assert "model" in config
        assert config["model"] == "deepseek-reasoner"
        assert config["base_url"] == "https://api.deepseek.com/v1"


def test_get_openai_config_returns_default_model_when_user_has_none(
    db: Session,
) -> None:
    """Test that get_openai_config returns default model when user has no model configured."""
    # Clean up existing configs
    from sqlmodel import select

    for config in db.exec(
        select(AppConfiguration).where(
            AppConfiguration.config_key.in_(
                [
                    "ai_default_openai_base_url",
                    "ai_default_openai_api_key_encrypted",
                    "ai_default_openai_model",
                ]
            )
        )
    ).all():
        db.delete(config)
    db.commit()

    # Generate a test Fernet key
    test_key = Fernet.generate_key()

    with patch.object(settings, "FERNET_KEY", test_key.decode()):
        # Create default configs
        default_base_url_config = AppConfigurationCreate(
            config_key="ai_default_openai_base_url",
            config_value="https://api.openai.com/v1",
            description="Default OpenAI API base URL",
            is_active=True,
        )
        default_base_url = AppConfiguration.model_validate(default_base_url_config)
        db.add(default_base_url)
        db.commit()

        default_api_key = "sk-default123456789"
        encrypted_default_key = encrypt_api_key(default_api_key)

        default_api_key_config = AppConfigurationCreate(
            config_key="ai_default_openai_api_key_encrypted",
            config_value=encrypted_default_key,
            description="Default OpenAI API key (encrypted)",
            is_active=True,
        )
        default_api_key_obj = AppConfiguration.model_validate(default_api_key_config)
        db.add(default_api_key_obj)
        db.commit()

        default_model_config = AppConfigurationCreate(
            config_key="ai_default_openai_model",
            config_value="gpt-4o",
            description="Default OpenAI model",
            is_active=True,
        )
        default_model_obj = AppConfiguration.model_validate(default_model_config)
        db.add(default_model_obj)
        db.commit()

        # Create user without model config
        email = f"user_{uuid.uuid4().hex[:8]}@example.com"
        password = "testpassword123"
        user_in = UserCreate(email=email, password=password)
        user = crud.create_user(session=db, user_create=user_in)

        # Get config
        config = get_openai_config(session=db, user_id=user.id)

        # Verify model comes from default config
        assert "model" in config
        assert config["model"] == "gpt-4o"
        assert config["base_url"] == "https://api.openai.com/v1"


def test_get_openai_config_raises_error_when_no_model_configured(db: Session) -> None:
    """Test that get_openai_config raises error when neither user nor default model is configured."""
    # Clean up existing configs
    from sqlmodel import select

    for config in db.exec(
        select(AppConfiguration).where(
            AppConfiguration.config_key.in_(
                [
                    "ai_default_openai_base_url",
                    "ai_default_openai_api_key_encrypted",
                    "ai_default_openai_model",
                ]
            )
        )
    ).all():
        db.delete(config)
    db.commit()

    # Generate a test Fernet key
    test_key = Fernet.generate_key()

    with patch.object(settings, "FERNET_KEY", test_key.decode()):
        # Create default configs (base_url and api_key, but no model)
        default_base_url_config = AppConfigurationCreate(
            config_key="ai_default_openai_base_url",
            config_value="https://api.openai.com/v1",
            description="Default OpenAI API base URL",
            is_active=True,
        )
        default_base_url = AppConfiguration.model_validate(default_base_url_config)
        db.add(default_base_url)
        db.commit()

        default_api_key = "sk-default123456789"
        encrypted_default_key = encrypt_api_key(default_api_key)

        default_api_key_config = AppConfigurationCreate(
            config_key="ai_default_openai_api_key_encrypted",
            config_value=encrypted_default_key,
            description="Default OpenAI API key (encrypted)",
            is_active=True,
        )
        default_api_key_obj = AppConfiguration.model_validate(default_api_key_config)
        db.add(default_api_key_obj)
        db.commit()

        # Create user without model config
        email = f"user_{uuid.uuid4().hex[:8]}@example.com"
        password = "testpassword123"
        user_in = UserCreate(email=email, password=password)
        user = crud.create_user(session=db, user_create=user_in)

        # Should raise error since no model is configured
        with pytest.raises(ValueError, match="OpenAI model not found"):
            get_openai_config(session=db, user_id=user.id)
