"""Tests for AppConfiguration API routes (admin)."""

import uuid
from unittest.mock import patch

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from sqlmodel import Session

from app import crud
from app.core.config import settings
from app.models import AppConfiguration, UserCreate


def test_create_app_configuration(
    client: TestClient, superuser_token_headers: dict[str, str], _db: Session
) -> None:
    """Test creating app configuration (admin only)."""
    # Generate a test Fernet key
    test_key = Fernet.generate_key()

    with patch.object(settings, "FERNET_KEY", test_key.decode()):
        config_data = {
            "config_key": f"ai_default_openai_base_url_{uuid.uuid4().hex[:8]}",
            "config_value": "https://api.openai.com/v1",
            "description": "Default OpenAI base URL",
            "is_active": True,
        }

        response = client.post(
            "/api/v1/app-configuration/",
            headers=superuser_token_headers,
            json=config_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["config_key"] == config_data["config_key"]
        assert data["config_value"] == config_data["config_value"]
        assert data["description"] == config_data["description"]
        assert data["is_active"] is True


def test_create_app_configuration_requires_admin(
    client: TestClient, db: Session
) -> None:
    """Test that creating app configuration requires admin privileges."""
    # Create regular user and get token
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

    config_data = {
        "config_key": f"ai_default_openai_base_url_{uuid.uuid4().hex[:8]}",
        "config_value": "https://api.openai.com/v1",
        "description": "Default OpenAI base URL",
        "is_active": True,
    }

    response = client.post(
        "/api/v1/app-configuration/",
        headers=headers,
        json=config_data,
    )

    # Should return 403 Forbidden
    assert response.status_code == 403


def test_get_app_configurations(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Test getting all app configurations (admin only)."""
    # Generate a test Fernet key
    test_key = Fernet.generate_key()

    with patch.object(settings, "FERNET_KEY", test_key.decode()):
        # Create a test configuration
        config_key = f"ai_default_openai_base_url_{uuid.uuid4().hex[:8]}"
        # Create config directly using model
        config = AppConfiguration(
            config_key=config_key,
            config_value="https://api.openai.com/v1",
            description="Default OpenAI base URL",
            is_active=True,
        )
        db.add(config)
        db.commit()
        db.refresh(config)

        response = client.get(
            "/api/v1/app-configuration/",
            headers=superuser_token_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert len(data["data"]) > 0
        # Find our test configuration
        configs = [c for c in data["data"] if c["config_key"] == config_key]
        assert len(configs) == 1


def test_update_app_configuration(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Test updating app configuration (admin only)."""
    # Generate a test Fernet key
    test_key = Fernet.generate_key()

    with patch.object(settings, "FERNET_KEY", test_key.decode()):
        # Create a test configuration
        config_key = f"ai_default_openai_base_url_{uuid.uuid4().hex[:8]}"
        # Create config directly using model
        config = AppConfiguration(
            config_key=config_key,
            config_value="https://api.openai.com/v1",
            description="Default OpenAI base URL",
            is_active=True,
        )
        db.add(config)
        db.commit()
        db.refresh(config)

        # Update configuration
        update_data = {
            "config_value": "https://api.openai.com/v2",
            "description": "Updated OpenAI base URL",
        }

        response = client.patch(
            f"/api/v1/app-configuration/{config.config_id}",
            headers=superuser_token_headers,
            json=update_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["config_value"] == update_data["config_value"]
        assert data["description"] == update_data["description"]


def test_app_configuration_endpoint_exists():
    """Test that app configuration endpoint exists."""
    try:
        from app.api.routes import app_configuration

        assert hasattr(app_configuration, "router")
        routes = list(app_configuration.router.routes)
        assert len(routes) > 0
    except ImportError:
        pytest.fail("App configuration router not found - implementation needed")
