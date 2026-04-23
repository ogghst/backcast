"""User directory provider abstraction."""

from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID


class UserProvider(ABC):
    """Abstract user directory provider.

    Future implementations: EntraUserProvider, HybridUserProvider
    """

    @abstractmethod
    async def get_user(self, user_id: UUID) -> dict[str, Any] | None:
        """Get user by ID.

        Returns user dict or None if not found.
        """
        pass

    @abstractmethod
    async def get_user_by_email(self, email: str) -> dict[str, Any] | None:
        """Get user by email address."""
        pass


class LocalUserProvider(UserProvider):
    """Local user directory.

    Thin placeholder -- the existing UserService in app.services.user
    handles user lookups directly. This class defines the interface
    for future OIDC/Entra implementations.
    """

    async def get_user(self, user_id: UUID) -> dict[str, Any] | None:
        """Not yet implemented -- use UserService directly."""
        raise NotImplementedError("Use UserService.get_user() for local lookups")

    async def get_user_by_email(self, email: str) -> dict[str, Any] | None:
        """Not yet implemented -- use UserService directly."""
        raise NotImplementedError("Use UserService.get_by_email() for local lookups")
