"""Authentication provider abstraction."""

from abc import ABC, abstractmethod
from typing import Any


class AuthProvider(ABC):
    """Abstract authentication provider.

    Future implementations: OIDCAuthProvider (Entra, Google, etc.)
    """

    @abstractmethod
    async def validate_token(self, token: str) -> dict[str, Any] | None:
        """Validate an authentication token.

        Returns decoded token payload, or None if invalid.
        """
        pass


class LocalAuthProvider(AuthProvider):
    """Local authentication using JWT.

    Wraps the existing JWT logic in app.core.security without changing behavior.
    """

    async def validate_token(self, token: str) -> dict[str, Any] | None:
        """Validate JWT token using centralized jwt_utils."""
        from app.core.jwt_utils import validate_jwt_token

        result = validate_jwt_token(token)
        if not result.is_valid:
            return None
        return {"sub": result.subject}
