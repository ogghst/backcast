"""Role-Based Access Control (RBAC) service.

Provides authorization functionality based on roles and permissions.
Supports pluggable implementations via abstract base class.
"""

import json
import logging
from abc import ABC, abstractmethod
from collections.abc import Callable
from functools import wraps
from pathlib import Path
from typing import Any, ParamSpec

from app.core.config import settings

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


P = ParamSpec("P")


def require_permission(*required_permissions: str) -> Callable[[Callable[P, Any]], Callable[P, Any]]:
    """Decorator to check if user has required permissions before function execution.

    This decorator can be used for both AI tools and API routes to enforce RBAC.
    It reads user_role from either a 'context' parameter (dict/object) or a
    'user_role' parameter, then checks permissions via RBACServiceABC.

    Args:
        *required_permissions: One or more permission strings to check.
                             All permissions must be granted for access.

    Returns:
        Decorated function that raises PermissionError if unauthorized.

    Raises:
        PermissionError: If user lacks any of the required permissions.

    Example:
        ```python
        @require_permission("project-read")
        async def get_project(project_id: str, user_role: str = None) -> dict:
            # Function executes only if user has "project-read" permission
            pass

        @require_permission("project-write", "project-read")
        async def update_project(project_id: str, context: dict = None) -> dict:
            # Function executes only if user has both permissions
            pass
        ```

    Note:
        The decorated function must have one of these parameters:
        - `user_role: str` - Direct role parameter
        - `context: dict` or `context: Any` - Dict-like object with user_role key
    """
    def decorator(func: Callable[P, Any]) -> Callable[P, Any]:
        # Attach metadata for inspection
        func._required_permissions = list(required_permissions)  # type: ignore[attr-defined]

        @wraps(func)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> Any:
            # Resolve user_role from kwargs
            user_role: str | None = None

            # Try to get from context parameter
            context_obj = kwargs.get("context")
            if context_obj is not None:
                if isinstance(context_obj, dict):
                    role = context_obj.get("user_role")
                    user_role = role if isinstance(role, str) else None
                elif hasattr(context_obj, "user_role"):
                    role = getattr(context_obj, "user_role", None)
                    user_role = role if isinstance(role, str) else None

            # Try to get from direct user_role parameter
            if user_role is None:
                role_param = kwargs.get("user_role")
                user_role = role_param if isinstance(role_param, str) else None

            # Validate we have a user_role
            if not user_role:
                raise PermissionError("Permission denied: user_role not provided")

            # Check permissions via RBAC service
            rbac_service = get_rbac_service()
            for permission in required_permissions:
                if not rbac_service.has_permission(user_role, permission):
                    raise PermissionError(
                        f"Permission denied: {permission} required "
                        f"(user_role: {user_role})"
                    )

            # All permissions granted, execute function
            return await func(*args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> Any:
            # Resolve user_role from kwargs
            user_role: str | None = None

            # Try to get from context parameter
            context_obj = kwargs.get("context")
            if context_obj is not None:
                if isinstance(context_obj, dict):
                    role = context_obj.get("user_role")
                    user_role = role if isinstance(role, str) else None
                elif hasattr(context_obj, "user_role"):
                    role = getattr(context_obj, "user_role", None)
                    user_role = role if isinstance(role, str) else None

            # Try to get from direct user_role parameter
            if user_role is None:
                role_param = kwargs.get("user_role")
                user_role = role_param if isinstance(role_param, str) else None

            # Validate we have a user_role
            if not user_role:
                raise PermissionError("Permission denied: user_role not provided")

            # Check permissions via RBAC service
            rbac_service = get_rbac_service()
            for permission in required_permissions:
                if not rbac_service.has_permission(user_role, permission):
                    raise PermissionError(
                        f"Permission denied: {permission} required "
                        f"(user_role: {user_role})"
                    )

            # All permissions granted, execute function
            return func(*args, **kwargs)

        # Return appropriate wrapper based on whether function is async
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


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
            base_dir = Path(__file__).resolve().parent.parent.parent
            config_path = base_dir / "config" / "rbac.json"

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
            raise FileNotFoundError(
                f"RBAC configuration file not found: {self.config_path}"
            )

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
        path = Path(settings.RBAC_POLICY_FILE)
        if not path.is_absolute():
            # Resolve relative to project root (backend/)
            base_dir = Path(__file__).resolve().parent.parent.parent
            path = base_dir / path
        _rbac_service = JsonRBACService(config_path=path)
    return _rbac_service


def set_rbac_service(service: RBACServiceABC) -> None:
    """Set the global RBAC service instance.

    Useful for testing to inject a mock service.

    Args:
        service: The RBAC service instance to use
    """
    global _rbac_service
    _rbac_service = service
