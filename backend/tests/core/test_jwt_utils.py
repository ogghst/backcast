"""Tests for JWT validation utilities."""

import pytest
from jose import jwt

from app.core.config import settings
from app.core.jwt_utils import JWTResult, validate_jwt_token
from app.models.domain.user import User


class TestValidateJWTToken:
    """Tests for validate_jwt_token function."""

    def test_valid_token_returns_success(self, db_session):
        """Test that a valid token returns is_valid=True with subject."""
        import time

        # Create a test user
        user = User(
            email="test@example.com",
            full_name="Test User",
            role="viewer",
            is_active=True,
        )
        db_session.add(user)
        db_session.commit()

        # Generate a valid token with proper expiration time
        now = int(time.time())
        payload = {
            "sub": user.email,
            "exp": now + (settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60),
        }
        token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

        # Validate token
        result = validate_jwt_token(token)

        assert result.is_valid is True
        assert result.subject == user.email
        assert result.error_detail is None
        assert result.close_code is None

    def test_expired_token_returns_4008_close_code(self):
        """Test that an expired token returns close_code=4008."""
        # Create an expired token (exp in the past)
        payload = {
            "sub": "test@example.com",
            "exp": 0,  # Epoch 0 is definitely expired
        }
        token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

        # Validate token
        result = validate_jwt_token(token)

        assert result.is_valid is False
        assert result.subject is None
        assert result.error_detail == "Token expired"
        assert result.close_code == 4008

    def test_invalid_token_returns_1008_close_code(self):
        """Test that an invalid token returns close_code=1008."""
        # Use a completely invalid token
        token = "invalid.token.string"

        # Validate token
        result = validate_jwt_token(token)

        assert result.is_valid is False
        assert result.subject is None
        assert result.error_detail == "Invalid token"
        assert result.close_code == 1008

    def test_token_without_subject_returns_error(self):
        """Test that a token without subject returns error."""
        import time

        # Create a token without 'sub' field
        now = int(time.time())
        payload = {
            "exp": now + (settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60),
        }
        token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

        # Validate token
        result = validate_jwt_token(token)

        assert result.is_valid is False
        assert result.subject is None
        assert result.error_detail == "Token missing subject"
        assert result.close_code == 1008

    def test_malformed_token_returns_1008_close_code(self):
        """Test that a malformed token returns close_code=1008."""
        import time

        # Use a token with invalid signature
        now = int(time.time())
        payload = {
            "sub": "test@example.com",
            "exp": now + (settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60),
        }
        token = jwt.encode(payload, "wrong-secret", algorithm=settings.ALGORITHM)

        # Validate token
        result = validate_jwt_token(token)

        assert result.is_valid is False
        assert result.subject is None
        assert result.error_detail == "Invalid token"
        assert result.close_code == 1008


class TestJWTResult:
    """Tests for JWTResult dataclass."""

    def test_jwt_result_is_frozen(self):
        """Test that JWTResult is frozen (immutable)."""
        from dataclasses import FrozenInstanceError

        result = JWTResult(is_valid=True, subject="test@example.com")

        with pytest.raises(FrozenInstanceError):
            result.is_valid = False  # type: ignore[misc]

    def test_jwt_result_defaults(self):
        """Test JWTResult default values."""
        result = JWTResult(is_valid=False)

        assert result.is_valid is False
        assert result.subject is None
        assert result.error_detail is None
        assert result.close_code is None

    def test_jwt_result_with_all_fields(self):
        """Test JWTResult with all fields set."""
        result = JWTResult(
            is_valid=False,
            subject=None,
            error_detail="Test error",
            close_code=4008,
        )

        assert result.is_valid is False
        assert result.subject is None
        assert result.error_detail == "Test error"
        assert result.close_code == 4008
