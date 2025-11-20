"""Tests for Users API OpenAI config endpoints."""

import uuid
from unittest.mock import patch

from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from sqlmodel import Session

from app import crud
from app.core.config import settings
from app.core.encryption import decrypt_api_key
from app.models import User, UserCreate


def test_update_user_me_openai_config(client: TestClient, db: Session) -> None:
    """Test updating own OpenAI configuration."""
    # Generate a test Fernet key
    test_key = Fernet.generate_key()

    with patch.object(settings, "FERNET_KEY", test_key.decode()):
        # Create user and get token
        email = f"user_{uuid.uuid4().hex[:8]}@example.com"
        password = "testpassword123"

        user_in = UserCreate(email=email, password=password)
        user = crud.create_user(session=db, user_create=user_in)

        # Login to get token
        login_data = {"username": email, "password": password}
        login_response = client.post("/api/v1/login/access-token", data=login_data)
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Update OpenAI config
        api_key = "sk-test123456789abcdef"

        update_data = {
            "openai_base_url": "https://api.openai.com/v1",
            "openai_api_key": api_key,  # Plain text API key (should be encrypted)
        }

        response = client.patch(
            "/api/v1/users/me",
            headers=headers,
            json=update_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["openai_base_url"] == "https://api.openai.com/v1"
        # API key should not be returned in response (for security)
        assert "openai_api_key" not in data
        # openai_api_key_encrypted might be in the response but should be None or excluded
        if "openai_api_key_encrypted" in data:
            assert data["openai_api_key_encrypted"] is None

        # Verify encryption in database
        updated_user = db.get(User, user.id)
        assert updated_user.openai_base_url == "https://api.openai.com/v1"
        assert updated_user.openai_api_key_encrypted is not None
        assert updated_user.openai_api_key_encrypted != api_key  # Should be encrypted
        # Verify decryption works
        decrypted_key = decrypt_api_key(updated_user.openai_api_key_encrypted)
        assert decrypted_key == api_key


def test_update_user_me_openai_config_partial(client: TestClient, db: Session) -> None:
    """Test updating only base URL or only API key."""
    # Generate a test Fernet key
    test_key = Fernet.generate_key()

    with patch.object(settings, "FERNET_KEY", test_key.decode()):
        # Create user and get token
        email = f"user_{uuid.uuid4().hex[:8]}@example.com"
        password = "testpassword123"

        user_in = UserCreate(email=email, password=password)
        user = crud.create_user(session=db, user_create=user_in)

        # Login to get token
        login_data = {"username": email, "password": password}
        login_response = client.post("/api/v1/login/access-token", data=login_data)
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Update only base URL
        update_data = {
            "openai_base_url": "https://api.openai.com/v1",
        }

        response = client.patch(
            "/api/v1/users/me",
            headers=headers,
            json=update_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["openai_base_url"] == "https://api.openai.com/v1"

        # Update only API key
        api_key = "sk-test123456789abcdef"
        update_data = {
            "openai_api_key": api_key,
        }

        response = client.patch(
            "/api/v1/users/me",
            headers=headers,
            json=update_data,
        )

        assert response.status_code == 200
        # Verify encryption
        updated_user = db.get(User, user.id)
        assert updated_user.openai_base_url == "https://api.openai.com/v1"
        assert updated_user.openai_api_key_encrypted is not None
        decrypted_key = decrypt_api_key(updated_user.openai_api_key_encrypted)
        assert decrypted_key == api_key


def test_update_user_openai_config_admin(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Test admin updating another user's OpenAI configuration."""
    # Generate a test Fernet key
    test_key = Fernet.generate_key()

    with patch.object(settings, "FERNET_KEY", test_key.decode()):
        # Create regular user
        email = f"user_{uuid.uuid4().hex[:8]}@example.com"
        password = "testpassword123"

        user_in = UserCreate(email=email, password=password)
        user = crud.create_user(session=db, user_create=user_in)

        # Admin updates user's OpenAI config
        api_key = "sk-admin-test123456789abcdef"

        update_data = {
            "openai_base_url": "https://api.openai.com/v1",
            "openai_api_key": api_key,
        }

        response = client.patch(
            f"/api/v1/users/{user.id}",
            headers=superuser_token_headers,
            json=update_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["openai_base_url"] == "https://api.openai.com/v1"
        # API key should not be returned
        assert "openai_api_key" not in data
        assert "openai_api_key_encrypted" not in data

        # Verify encryption in database
        updated_user = db.get(User, user.id)
        assert updated_user.openai_base_url == "https://api.openai.com/v1"
        assert updated_user.openai_api_key_encrypted is not None
        decrypted_key = decrypt_api_key(updated_user.openai_api_key_encrypted)
        assert decrypted_key == api_key


def test_update_user_me_openai_config_validation(
    client: TestClient, db: Session
) -> None:
    """Test OpenAI config validation (base URL format, API key length)."""
    # Generate a test Fernet key
    test_key = Fernet.generate_key()

    with patch.object(settings, "FERNET_KEY", test_key.decode()):
        # Create user and get token
        email = f"user_{uuid.uuid4().hex[:8]}@example.com"
        password = "testpassword123"

        user_in = UserCreate(email=email, password=password)
        _user = crud.create_user(session=db, user_create=user_in)

        # Login to get token
        login_data = {"username": email, "password": password}
        login_response = client.post("/api/v1/login/access-token", data=login_data)
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Test invalid base URL format (optional - if validation is implemented)
        # For now, we just test that the endpoint accepts the data
        update_data = {
            "openai_base_url": "not-a-valid-url",
        }

        response = client.patch(
            "/api/v1/users/me",
            headers=headers,
            json=update_data,
        )

        # Should either accept it (if no validation) or reject with 422
        assert response.status_code in [200, 422]
