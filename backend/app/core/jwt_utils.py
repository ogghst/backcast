"""JWT validation utilities.

Provides centralized JWT token validation for both HTTP and WebSocket routes.
"""

from dataclasses import dataclass
from typing import Literal

from jose import ExpiredSignatureError, JWTError, jwt
from pydantic import ValidationError

from app.core.config import settings
from app.models.schemas.user import TokenPayload


@dataclass(frozen=True)
class JWTResult:
    """Result of JWT validation."""

    is_valid: bool
    subject: str | None = None
    error_detail: str | None = None
    close_code: Literal[4008, 1008] | None = None


def validate_jwt_token(token: str) -> JWTResult:
    """Validate JWT token and return structured result.

    Args:
        token: JWT token string from Authorization header or query param

    Returns:
        JWTResult with validation status and error details

    Note:
        - Returns close_code=4008 for expired tokens (client should refresh)
        - Returns close_code=1008 for other errors (client must re-authenticate)
    """
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        token_data = TokenPayload(**payload)

        if token_data.sub is None:
            return JWTResult(
                is_valid=False, error_detail="Token missing subject", close_code=1008
            )

        return JWTResult(is_valid=True, subject=token_data.sub)

    except ExpiredSignatureError:
        return JWTResult(is_valid=False, error_detail="Token expired", close_code=4008)
    except (JWTError, ValidationError):
        return JWTResult(is_valid=False, error_detail="Invalid token", close_code=1008)
