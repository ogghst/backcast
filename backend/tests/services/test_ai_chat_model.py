"""Tests for AI chat LangChain model creation."""

import uuid
from unittest.mock import patch

import pytest
from cryptography.fernet import Fernet
from sqlmodel import Session

from app import crud
from app.core.config import settings
from app.core.encryption import encrypt_api_key
from app.models import AppConfiguration, AppConfigurationCreate, UserCreate
from app.services.ai_chat import create_chat_model


def test_create_chat_model_with_user_config(db: Session) -> None:
    """Test creating ChatOpenAI model with user configuration."""
    # Generate a test Fernet key
    test_key = Fernet.generate_key()

    with patch.object(settings, "FERNET_KEY", test_key.decode()):
        # Create user with OpenAI config
        email = f"user_{uuid.uuid4().hex[:8]}@example.com"
        password = "testpassword123"

        api_key = "sk-test123456789abcdef"
        encrypted_key = encrypt_api_key(api_key)

        user_in = UserCreate(
            email=email,
            password=password,
            openai_base_url="https://api.openai.com/v1",
            openai_api_key_encrypted=encrypted_key,
        )
        user = crud.create_user(session=db, user_create=user_in)

        # Create chat model
        chat_model = create_chat_model(session=db, user_id=user.id)

        # Verify model is created and configured
        assert chat_model is not None
        assert hasattr(chat_model, "openai_api_base")
        assert str(chat_model.openai_api_base) == "https://api.openai.com/v1"
        assert hasattr(chat_model, "openai_api_key")
        # API key is stored as SecretStr, so we check it's not empty
        assert chat_model.openai_api_key is not None
        assert chat_model.streaming is True  # Streaming should be enabled


def test_create_chat_model_with_default_config(db: Session) -> None:
    """Test creating ChatOpenAI model with default app configuration."""
    # Clean up existing configs
    from sqlmodel import select

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

        # Create user without config
        email = f"user_{uuid.uuid4().hex[:8]}@example.com"
        password = "testpassword123"
        user_in = UserCreate(email=email, password=password)
        user = crud.create_user(session=db, user_create=user_in)

        # Create chat model
        chat_model = create_chat_model(session=db, user_id=user.id)

        # Verify model uses default config
        assert chat_model is not None
        assert str(chat_model.openai_api_base) == "https://api.openai.com/v1/default"
        assert chat_model.openai_api_key is not None  # API key is stored as SecretStr
        assert chat_model.streaming is True


def test_create_chat_model_missing_config_raises_error(db: Session) -> None:
    """Test that missing configuration raises ValueError."""
    # Clean up existing configs
    from sqlmodel import select

    for config in db.exec(
        select(AppConfiguration).where(
            AppConfiguration.config_key.in_(
                ["ai_default_openai_base_url", "ai_default_openai_api_key_encrypted"]
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

    # Should raise error
    with pytest.raises(ValueError, match="OpenAI base URL not found"):
        create_chat_model(session=db, user_id=user.id)


def test_create_chat_model_configures_model_parameters(db: Session) -> None:
    """Test that ChatOpenAI model is configured with correct parameters."""
    # Generate a test Fernet key
    test_key = Fernet.generate_key()

    with patch.object(settings, "FERNET_KEY", test_key.decode()):
        # Create user with OpenAI config
        email = f"user_{uuid.uuid4().hex[:8]}@example.com"
        password = "testpassword123"

        api_key = "sk-test123456789abcdef"
        encrypted_key = encrypt_api_key(api_key)

        user_in = UserCreate(
            email=email,
            password=password,
            openai_base_url="https://api.openai.com/v1",
            openai_api_key_encrypted=encrypted_key,
        )
        user = crud.create_user(session=db, user_create=user_in)

        # Create chat model
        chat_model = create_chat_model(session=db, user_id=user.id)

        # Verify model parameters
        assert chat_model is not None
        # Check default model name (should be gpt-4o-mini)
        assert hasattr(chat_model, "model_name")
        assert chat_model.model_name == "gpt-4o-mini"
        # Check temperature (should have a default)
        assert hasattr(chat_model, "temperature")
        assert chat_model.temperature == 0.7
        # Streaming should be enabled
        assert chat_model.streaming is True


def test_create_chat_model_auto_detects_deepseek_model(db: Session) -> None:
    """Test that ChatOpenAI model auto-detects DeepSeek model from base URL."""
    # Generate a test Fernet key
    test_key = Fernet.generate_key()

    with patch.object(settings, "FERNET_KEY", test_key.decode()):
        # Create user with DeepSeek config
        email = f"user_{uuid.uuid4().hex[:8]}@example.com"
        password = "testpassword123"

        api_key = "sk-test123456789abcdef"
        encrypted_key = encrypt_api_key(api_key)

        user_in = UserCreate(
            email=email,
            password=password,
            openai_base_url="https://api.deepseek.com/v1",
            openai_api_key_encrypted=encrypted_key,
        )
        user = crud.create_user(session=db, user_create=user_in)

        # Create chat model
        chat_model = create_chat_model(session=db, user_id=user.id)

        # Verify model is created and configured with DeepSeek model
        assert chat_model is not None
        assert hasattr(chat_model, "model_name")
        assert chat_model.model_name == "deepseek-chat"  # Should auto-detect DeepSeek
        assert str(chat_model.openai_api_base) == "https://api.deepseek.com/v1"
        assert chat_model.openai_api_key is not None
        assert chat_model.streaming is True
