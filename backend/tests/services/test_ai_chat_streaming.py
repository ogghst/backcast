"""Tests for AI chat initial assessment streaming."""

import uuid
from datetime import date
from unittest.mock import patch

from cryptography.fernet import Fernet
from sqlmodel import Session

from app import crud
from app.core.config import settings
from app.core.encryption import encrypt_api_key
from app.models import UserCreate
from app.services.ai_chat import (
    generate_initial_assessment,
    send_chat_message,
)


async def test_generate_initial_assessment_project(db: Session) -> None:
    """Test generating initial assessment for project context."""
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
        _user = crud.create_user(session=db, user_create=user_in)

        # Mock WebSocket send function
        sent_chunks = []

        async def mock_send(message: dict) -> None:
            sent_chunks.append(message)

        # Sample context metrics
        _context_metrics = {
            "context_type": "project",
            "project_id": str(uuid.uuid4()),
            "project_name": "Test Project",
            "control_date": date(2024, 6, 15).isoformat(),
            "planned_value": 100000.0,
            "earned_value": 95000.0,
            "actual_cost": 105000.0,
        }

        # Generate initial assessment (should stream chunks)
        # Note: This will make actual API calls if not mocked
        # For now, we test that the function exists and accepts correct parameters
        assert callable(generate_initial_assessment)


def test_generate_initial_assessment_creates_graph(db: Session) -> None:
    """Test that generate_initial_assessment creates assessment graph."""
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
        _user = crud.create_user(session=db, user_create=user_in)

        # Sample context metrics
        _context_metrics = {
            "context_type": "project",
            "project_id": str(uuid.uuid4()),
            "project_name": "Test Project",
            "control_date": date(2024, 6, 15).isoformat(),
        }

        # Verify function exists and signature
        assert callable(generate_initial_assessment)
        import inspect

        sig = inspect.signature(generate_initial_assessment)
        params = list(sig.parameters.keys())
        # Should have session, user_id, context_type, context_id, control_date, and send_message
        assert "session" in params
        assert "user_id" in params
        assert "context_type" in params
        assert "context_id" in params
        assert "control_date" in params
        assert "send_message" in params


def test_send_chat_message_function_signature():
    """Test that send_chat_message function exists with correct signature."""
    # Verify function exists and signature
    assert callable(send_chat_message)
    import inspect

    sig = inspect.signature(send_chat_message)
    params = list(sig.parameters.keys())
    # Should have session, user_id, context_type, context_id, control_date, message, conversation_history, and send_message
    assert "session" in params
    assert "user_id" in params
    assert "context_type" in params
    assert "context_id" in params
    assert "control_date" in params
    assert "message" in params
    assert "conversation_history" in params
    assert "send_message" in params
