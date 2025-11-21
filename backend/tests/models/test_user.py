"""Tests for User model with OpenAI configuration fields."""

import uuid

from sqlmodel import Session

from app import crud
from app.models import (
    UserCreate,
    UserPublic,
    UserUpdate,
    UserUpdateMe,
)


def test_create_user_with_openai_config(db: Session) -> None:
    """Test creating a user with OpenAI configuration fields."""
    email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    password = "testpassword123"

    user_in = UserCreate(
        email=email,
        password=password,
        openai_base_url="https://api.openai.com/v1",
        openai_api_key_encrypted="encrypted_key_123",
    )

    user = crud.create_user(session=db, user_create=user_in)

    # Verify user was created with OpenAI config
    assert user.id is not None
    assert user.email == email
    assert user.openai_base_url == "https://api.openai.com/v1"
    assert user.openai_api_key_encrypted == "encrypted_key_123"


def test_create_user_without_openai_config(db: Session) -> None:
    """Test creating a user without OpenAI configuration (fields should be optional)."""
    email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    password = "testpassword123"

    user_in = UserCreate(email=email, password=password)
    user = crud.create_user(session=db, user_create=user_in)

    # Verify user was created without OpenAI config
    assert user.id is not None
    assert user.email == email
    assert user.openai_base_url is None
    assert user.openai_api_key_encrypted is None


def test_update_user_openai_config(db: Session) -> None:
    """Test updating a user's OpenAI configuration."""
    email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    password = "testpassword123"
    user_in = UserCreate(email=email, password=password)
    user = crud.create_user(session=db, user_create=user_in)

    # Update with OpenAI config
    user_update = UserUpdate(
        openai_base_url="https://api.openai.com/v1",
        openai_api_key_encrypted="encrypted_key_updated",
    )

    updated_user = crud.update_user(session=db, db_user=user, user_in=user_update)

    assert updated_user.openai_base_url == "https://api.openai.com/v1"
    assert updated_user.openai_api_key_encrypted == "encrypted_key_updated"


def test_user_update_me_schema_includes_openai_config() -> None:
    """Test that UserUpdateMe schema includes OpenAI configuration fields."""
    user_update_me = UserUpdateMe(
        openai_base_url="https://api.openai.com/v1",
        openai_api_key_encrypted="encrypted_key_self_update",
    )

    assert user_update_me.openai_base_url == "https://api.openai.com/v1"
    assert user_update_me.openai_api_key_encrypted == "encrypted_key_self_update"


def test_user_public_schema_includes_openai_config() -> None:
    """Test that UserPublic schema includes OpenAI configuration fields."""
    user_id = uuid.uuid4()

    user_public = UserPublic(
        id=user_id,
        email="test@example.com",
        is_active=True,
        openai_base_url="https://api.openai.com/v1",
        openai_api_key_encrypted="encrypted_key",
    )

    assert user_public.openai_base_url == "https://api.openai.com/v1"
    assert user_public.openai_api_key_encrypted == "encrypted_key"


def test_user_base_includes_openai_config() -> None:
    """Test that UserBase schema includes OpenAI configuration fields."""
    from app.models.user import UserBase

    user_base = UserBase(
        email="test@example.com",
        openai_base_url="https://api.openai.com/v1",
        openai_api_key_encrypted="encrypted_key",
    )

    assert user_base.openai_base_url == "https://api.openai.com/v1"
    assert user_base.openai_api_key_encrypted == "encrypted_key"
    # Verify fields are optional (can be None)
    user_base_none = UserBase(email="test2@example.com")
    assert user_base_none.openai_base_url is None
    assert user_base_none.openai_api_key_encrypted is None


def test_user_model_includes_openai_model_field(db: Session) -> None:
    """Test that User model includes openai_model field."""
    email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    password = "testpassword123"

    user_in = UserCreate(
        email=email,
        password=password,
        openai_base_url="https://api.openai.com/v1",
        openai_api_key_encrypted="encrypted_key_123",
        openai_model="gpt-4o-mini",
    )

    user = crud.create_user(session=db, user_create=user_in)

    # Verify user was created with model field
    assert user.id is not None
    assert user.email == email
    assert user.openai_model == "gpt-4o-mini"


def test_user_model_openai_model_is_optional(db: Session) -> None:
    """Test that openai_model field is optional."""
    email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    password = "testpassword123"

    user_in = UserCreate(email=email, password=password)
    user = crud.create_user(session=db, user_create=user_in)

    # Verify model field is None when not provided
    assert user.id is not None
    assert user.openai_model is None


def test_user_update_me_schema_includes_openai_model() -> None:
    """Test that UserUpdateMe schema includes openai_model field."""
    user_update_me = UserUpdateMe(
        openai_base_url="https://api.openai.com/v1",
        openai_api_key="test_key",
        openai_model="deepseek-chat",
    )

    assert user_update_me.openai_model == "deepseek-chat"
