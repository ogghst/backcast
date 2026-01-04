"""Role-Based Access Control (RBAC) service.

Provides authorization functionality based on roles and permissions.
Supports pluggable implementations via abstract base class.
"""

import json
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class RBACServiceABC(ABC):
    """Abstract base class for RBAC services.

    Defines the contract for role-based and permission-based authorization.
    Implementations can use JSON files, databases, or external services.
    """

    @abstractmethod
    def has_role(self, user_role: str, required_roles: list[str]) -> bool:
        """Check if user's role is in the required roles list.

        Args:
            user_role: The role assigned to the user
            required_roles: List of roles that are allowed

        Returns:
            True if user_role is in required_roles, False otherwise
        """
        pass

    @abstractmethod
    def has_permission(self, user_role: str, required_permission: str) -> bool:
        """Check if user's role has the required permission.

        Args:
            user_role: The role assigned to the user
            required_permission: The permission to check for

        Returns:
            True if the role has the permission, False otherwise
        """
        pass

    @abstractmethod
    def get_user_permissions(self, user_role: str) -> list[str]:
        """Get all permissions for a given role.

        Args:
            user_role: The role to get permissions for

        Returns:
            List of permission strings, empty list if role unknown
        """
        pass


class JsonRBACService(RBACServiceABC):
    """JSON file-based RBAC implementation.

    Loads role and permission configuration from a JSON file.
    Suitable for development and small deployments.

    Configuration format:
    {
        "roles": {
            "admin": {
                "permissions": ["create", "read", "update", "delete"]
            },
            "viewer": {
                "permissions": ["read"]
            }
        }
    }
    """

    def __init__(self, config_path: Path | None = None) -> None:
        """Initialize the JSON RBAC service.

        Args:
            config_path: Path to the JSON configuration file.
                        Defaults to backend/config/rbac.json

        Raises:
            FileNotFoundError: If config file doesn't exist
            json.JSONDecodeError: If config file is invalid JSON
        """
        if config_path is None:
            # Default path relative to backend directory
            config_path = Path(__file__).parent.parent.parent / "config" / "rbac.json"

        self.config_path = config_path
        self._config: dict[str, Any] = self._load_config()
        logger.info(f"Loaded RBAC configuration from {self.config_path}")

    def _load_config(self) -> dict[str, Any]:
        """Load and parse the JSON configuration file.

        Returns:
            Parsed configuration dictionary

        Raises:
            FileNotFoundError: If config file doesn't exist
            json.JSONDecodeError: If config file is invalid JSON
        """
        if not self.config_path.exists():
            raise FileNotFoundError(f"RBAC configuration file not found: {self.config_path}")

        with open(self.config_path) as f:
            config: dict[str, Any] = json.load(f)

        return config

    def has_role(self, user_role: str, required_roles: list[str]) -> bool:
        """Check if user's role is in the required roles list.

        Args:
            user_role: The role assigned to the user
            required_roles: List of roles that are allowed

        Returns:
            True if user_role is in required_roles, False otherwise
        """
        if not required_roles:
            return False

        return user_role in required_roles

    def has_permission(self, user_role: str, required_permission: str) -> bool:
        """Check if user's role has the required permission.

        Args:
            user_role: The role assigned to the user
            required_permission: The permission to check for

        Returns:
            True if the role has the permission, False otherwise
        """
        roles = self._config.get("roles", {})
        role_config = roles.get(user_role)

        if role_config is None:
            return False

        permissions = role_config.get("permissions", [])
        return required_permission in permissions

    def get_user_permissions(self, user_role: str) -> list[str]:
        """Get all permissions for a given role.

        Args:
            user_role: The role to get permissions for

        Returns:
            List of permission strings, empty list if role unknown
        """
        roles = self._config.get("roles", {})
        role_config = roles.get(user_role)

        if role_config is None:
            return []

        permissions: list[str] = role_config.get("permissions", [])
        return permissions


# Global singleton instance
_rbac_service: RBACServiceABC | None = None


def get_rbac_service() -> RBACServiceABC:
    """Get the global RBAC service instance (singleton pattern).

    Returns:
        The global RBACServiceABC instance

    Note:
        Creates a JsonRBACService on first call with default config path.
        Can be overridden for testing by setting the global _rbac_service.
    """
    global _rbac_service
    if _rbac_service is None:
        _rbac_service = JsonRBACService()
    return _rbac_service


def set_rbac_service(service: RBACServiceABC) -> None:
    """Set the global RBAC service instance.

    Useful for testing to inject a mock service.

    Args:
        service: The RBAC service instance to use
    """
    global _rbac_service
    _rbac_service = service
