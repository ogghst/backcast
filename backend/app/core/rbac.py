"""Role-Based Access Control (RBAC) service.

Provides authorization functionality based on roles and permissions.
Supports pluggable implementations via abstract base class.
"""

import json
import logging
from abc import ABC, abstractmethod
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from enum import Enum
from functools import wraps
from pathlib import Path
from typing import Any, ParamSpec
from uuid import UUID

from app.core.config import settings

logger = logging.getLogger(__name__)


class ProjectRole(str, Enum):
    """Project-level roles for RBAC.

    Roles define the level of access a user has within a specific project.
    Permissions are hierarchical: admin > editor > viewer.
    """

    ADMIN = "admin"
    EDITOR = "editor"
    VIEWER = "viewer"

    @classmethod
    def permissions(cls, role: str) -> list[str]:
        """Get permissions for a given project role.

        Args:
            role: The project role to get permissions for

        Returns:
            List of permission strings for the role
        """
        role_permissions = {
            cls.ADMIN.value: [
                "project-read",
                "project-write",
                "project-delete",
                "project-admin",
                "cost-element-read",
                "cost-element-write",
                "cost-element-delete",
                "forecast-read",
                "forecast-write",
                "change-order-read",
                "change-order-write",
                "change-order-approve",
            ],
            cls.EDITOR.value: [
                "project-read",
                "project-write",
                "cost-element-read",
                "cost-element-write",
                "forecast-read",
                "forecast-write",
                "change-order-read",
                "change-order-write",
            ],
            cls.VIEWER.value: [
                "project-read",
                "cost-element-read",
                "forecast-read",
                "change-order-read",
            ],
        }
        return role_permissions.get(role, [])


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

    @abstractmethod
    async def has_project_access(
        self,
        user_id: UUID,
        user_role: str,
        project_id: UUID,
        required_permission: str,
    ) -> bool:
        """Check if user has access to a project with required permission.

        Args:
            user_id: The user's ID
            user_role: The user's system-level role
            project_id: The project to check access for
            required_permission: The permission required

        Returns:
            True if user has access, False otherwise
        """
        pass

    @abstractmethod
    async def get_user_projects(self, user_id: UUID, user_role: str) -> list[UUID]:
        """Get list of project IDs the user has access to.

        Args:
            user_id: The user's ID
            user_role: The user's system-level role

        Returns:
            List of project IDs the user can access
        """
        pass

    @abstractmethod
    async def get_project_role(self, user_id: UUID, project_id: UUID) -> str | None:
        """Get user's role within a specific project.

        Args:
            user_id: The user's ID
            project_id: The project to check

        Returns:
            The user's project role, or None if not a member
        """
        pass


P = ParamSpec("P")


def require_permission(
    *required_permissions: str,
) -> Callable[[Callable[P, Any]], Callable[P, Any]]:
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

    # Cache TTL for project membership lookups (5 minutes)
    _CACHE_TTL = timedelta(minutes=5)

    def __init__(
        self,
        config_path: Path | None = None,
        session: Any | None = None,
    ) -> None:
        """Initialize the JSON RBAC service.

        Args:
            config_path: Path to the JSON configuration file.
                        Defaults to backend/config/rbac.json
            session: Optional AsyncSession for database lookups.
                    Required for project-level access checks.

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
        self.session = session

        # Project membership cache: {(user_id, project_id) -> (role, timestamp)}
        self._project_cache: dict[tuple[UUID, UUID], tuple[str, datetime]] = {}

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

    def _role_has_permission(self, project_role: str, permission: str) -> bool:
        """Check if a project role has a specific permission.

        Supports wildcard matching (e.g., "project-read" matches "project-*").

        Args:
            project_role: The project role to check
            permission: The permission to verify

        Returns:
            True if the role has the permission, False otherwise
        """
        from app.core.enums import ProjectRole as EnumProjectRole

        # Get the role enum from the string
        try:
            role_enum = EnumProjectRole(project_role)
        except ValueError:
            # Unknown role, no permissions
            return False

        role_permissions = role_enum.permissions

        # Check for exact match or wildcard match
        for role_perm in role_permissions:
            if role_perm == permission:
                return True
            # Wildcard matching: "project-*" matches "project-read"
            if "*" in role_perm:
                prefix = role_perm.rstrip("*")
                if permission.startswith(prefix):
                    return True

        return False

    async def has_project_access(
        self,
        user_id: UUID,
        user_role: str,
        project_id: UUID,
        required_permission: str,
    ) -> bool:
        """Check if user has access to a project with required permission.

        System admins bypass project-level checks and always have access.
        For other users, checks project membership and role permissions.

        Args:
            user_id: The user's ID
            user_role: The user's system-level role
            project_id: The project to check access for
            required_permission: The permission required

        Returns:
            True if user has access, False otherwise
        """
        # System admins bypass project-level checks
        if user_role == "admin":
            return True

        # Check cache first
        cache_key = (user_id, project_id)
        if cache_key in self._project_cache:
            cached_role, cached_time = self._project_cache[cache_key]
            if datetime.now(UTC) - cached_time < self._CACHE_TTL:
                # Use cached role if permission matches
                return self._role_has_permission(cached_role, required_permission)

        # Database lookup required
        if self.session is None:
            logger.warning(
                f"Cannot check project access for user {user_id}: "
                "no database session provided"
            )
            return False

        # Import here to avoid circular dependency
        # ProjectMember model is created in a separate task
        # Query project membership
        from sqlalchemy import select

        from app.models.domain.project_member import ProjectMember

        result = await self.session.execute(
            select(ProjectMember).where(
                ProjectMember.user_id == user_id,
                ProjectMember.project_id == project_id,
            )
        )
        member = result.scalar_one_or_none()

        if member is None:
            return False

        # Update cache
        self._project_cache[cache_key] = (member.role, datetime.now(UTC))

        return self._role_has_permission(member.role, required_permission)

    async def get_user_projects(self, user_id: UUID, user_role: str) -> list[UUID]:
        """Get list of project IDs the user has access to.

        System admins get access to all projects.
        For other users, returns projects where they are a member.

        Args:
            user_id: The user's ID
            user_role: The user's system-level role

        Returns:
            List of project IDs the user can access
        """
        # System admins have access to all projects
        if user_role == "admin":
            # Import here to avoid circular dependency
            from app.models.domain.project import Project

            if self.session is None:
                logger.warning(
                    f"Cannot get projects for admin user {user_id}: "
                    "no database session provided"
                )
                return []

            from sqlalchemy import select

            result = await self.session.execute(select(Project.project_id))
            return [row[0] for row in result.all()]

        # Non-admin users: get their project memberships
        if self.session is None:
            logger.warning(
                f"Cannot get projects for user {user_id}: no database session provided"
            )
            return []

        # Import ProjectMember model (created in separate task)
        from sqlalchemy import select

        from app.models.domain.project_member import ProjectMember

        result = await self.session.execute(
            select(ProjectMember.project_id).where(ProjectMember.user_id == user_id)
        )
        return [row[0] for row in result.all()]

    async def get_project_role(self, user_id: UUID, project_id: UUID) -> str | None:
        """Get user's role within a specific project.

        Args:
            user_id: The user's ID
            project_id: The project to check

        Returns:
            The user's project role, or None if not a member
        """
        # Check cache first
        cache_key = (user_id, project_id)
        if cache_key in self._project_cache:
            cached_role, cached_time = self._project_cache[cache_key]
            if datetime.now(UTC) - cached_time < self._CACHE_TTL:
                return cached_role

        # Database lookup
        if self.session is None:
            logger.warning(
                f"Cannot get project role for user {user_id}: "
                "no database session provided"
            )
            return None

        # Import ProjectMember model (created in separate task)
        from sqlalchemy import select

        from app.models.domain.project_member import ProjectMember

        result = await self.session.execute(
            select(ProjectMember.role).where(
                ProjectMember.user_id == user_id,
                ProjectMember.project_id == project_id,
            )
        )
        role = result.scalar_one_or_none()

        if role is not None:
            # Update cache
            self._project_cache[cache_key] = (role, datetime.now(UTC))

        return role


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


def inject_rbac_session(
    rbac_service: RBACServiceABC,
    session: Any,
) -> bool:
    """Inject database session into RBAC service for project-level access checks.

    Some RBAC service implementations (like JsonRBACService) require a database
    session to perform project-level access checks. This helper function safely
    injects the session if the service supports it.

    Args:
        rbac_service: The RBAC service instance
        session: The database session to inject

    Returns:
        True if session was injected (or already set), False otherwise

    Example:
        ```python
        from app.core.rbac import get_rbac_service, inject_rbac_session

        rbac_service = get_rbac_service()
        inject_rbac_session(rbac_service, context.session)
        ```
    """
    if hasattr(rbac_service, "session") and rbac_service.session is None:
        rbac_service.session = session
        return True
    return False
