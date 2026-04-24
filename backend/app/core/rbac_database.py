"""Database-backed RBAC service implementation.

Loads role-permission mappings from PostgreSQL rbac_roles tables into an
in-memory cache.  The cache is populated eagerly via ``refresh_cache()``
(called at startup) and refreshed after any RBAC write operation.

Sync methods (``has_role``, ``has_permission``, ``get_user_permissions``)
read exclusively from cache -- they **never** perform database queries.
If the cache is empty, they return fail-secure defaults (deny access,
empty permissions).

Async methods (``has_project_access``, ``get_user_projects``,
``get_project_role``) query the ``ProjectMember`` table and use their own
project-membership cache, identical to ``JsonRBACService``.
"""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select

from app.core.rbac import RBACServiceABC, get_rbac_session

logger = logging.getLogger(__name__)


class DatabaseRBACService(RBACServiceABC):
    """RBAC implementation reading from PostgreSQL rbac_roles tables.

    Uses in-memory cache with TTL for performance.
    Single-server deployment: no distributed cache needed.
    """

    _PROJECT_CACHE_TTL = timedelta(minutes=5)

    def __init__(self, session: Any = None) -> None:  # noqa: ARG002 (session accepted for backward compatibility, ignored)
        """Initialize the database RBAC service.

        Args:
            session: Accepted for backward compatibility with tests and JsonRBACService,
                    but not used. Database sessions are managed per-request via
                    contextvars to avoid session leaks.
        """
        # Permissions cache: {role_name: (permissions_list, timestamp)}
        self._permissions_cache: dict[str, tuple[list[str], datetime]] = {}
        # Project membership cache: {(user_id, project_id) -> (role, timestamp)}
        self._project_cache: dict[tuple[UUID, UUID], tuple[str, datetime]] = {}

    # ------------------------------------------------------------------
    # Cache management
    # ------------------------------------------------------------------

    async def refresh_cache(self) -> None:
        """Load all role-permission mappings from database into cache.

        Called at startup and after write operations that modify roles or
        permissions.  Replaces the entire cache with fresh data.
        """
        session = get_rbac_session()
        if session is None:
            logger.warning("Cannot refresh RBAC cache: no database session")
            return

        from app.models.domain.rbac import RBACRole, RBACRolePermission

        result = await session.execute(
            select(
                RBACRole.name,
                RBACRolePermission.permission,
            ).join(
                RBACRolePermission,
                RBACRole.permissions,
            )
        )

        role_perms: dict[str, list[str]] = {}
        for role_name, permission in result.all():
            role_perms.setdefault(role_name, []).append(permission)

        now = datetime.now(UTC)
        # Replace entire cache -- stale roles that no longer exist in DB are removed
        self._permissions_cache.clear()
        for role_name, perms in role_perms.items():
            self._permissions_cache[role_name] = (perms, now)

        logger.info(
            "Refreshed RBAC permissions cache: %d roles loaded",
            len(self._permissions_cache),
        )

    def _get_cached_permissions(self, role_name: str) -> list[str] | None:
        """Get permissions from cache.

        Args:
            role_name: The role to look up.

        Returns:
            List of permission strings, or ``None`` if cache miss.
        """
        cached = self._permissions_cache.get(role_name)
        if cached is None:
            return None
        return cached[0]

    def _cache_permissions(self, role_name: str, permissions: list[str]) -> None:
        """Store permissions in cache.

        Args:
            role_name: The role name to cache.
            permissions: List of permission strings.
        """
        self._permissions_cache[role_name] = (permissions, datetime.now(UTC))

    # ------------------------------------------------------------------
    # Sync methods (cache-only)
    # ------------------------------------------------------------------

    def has_role(self, user_role: str, required_roles: list[str]) -> bool:
        """Check if user's role is in the required roles list.

        Args:
            user_role: The role assigned to the user.
            required_roles: List of roles that are allowed.

        Returns:
            True if user_role is in required_roles, False otherwise.
        """
        if not required_roles:
            return False
        return user_role in required_roles

    def has_permission(self, user_role: str, required_permission: str) -> bool:
        """Check if user's role has the required permission.

        Reads from in-memory cache only.  Returns ``False`` on cache miss
        or expired entry (fail-secure).

        Args:
            user_role: The role assigned to the user.
            required_permission: The permission to check for.

        Returns:
            True if the role has the permission, False otherwise.
        """
        permissions = self._get_cached_permissions(user_role)
        if permissions is None:
            return False  # Fail secure: no cache = no access
        return required_permission in permissions

    def get_user_permissions(self, user_role: str) -> list[str]:
        """Get all permissions for a given role.

        Reads from in-memory cache only.  Returns empty list on cache
        miss or expired entry.

        Args:
            user_role: The role to get permissions for.

        Returns:
            List of permission strings, empty list if role unknown or expired.
        """
        permissions = self._get_cached_permissions(user_role)
        if permissions is None:
            return []
        return permissions

    # ------------------------------------------------------------------
    # Project-level helpers (shared with JsonRBACService)
    # ------------------------------------------------------------------

    @staticmethod
    def _role_has_permission(project_role: str, permission: str) -> bool:
        """Check if a project role has a specific permission.

        Supports wildcard matching (e.g., "project-*" matches "project-read").

        Args:
            project_role: The project role to check.
            permission: The permission to verify.

        Returns:
            True if the role has the permission, False otherwise.
        """
        from app.core.enums import ProjectRole as EnumProjectRole

        try:
            role_enum = EnumProjectRole(project_role)
        except ValueError:
            return False

        for role_perm in role_enum.permissions:
            if role_perm == permission:
                return True
            if "*" in role_perm:
                prefix = role_perm.rstrip("*")
                if permission.startswith(prefix):
                    return True

        return False

    # ------------------------------------------------------------------
    # Async methods (database-backed, with project cache)
    # ------------------------------------------------------------------

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
            user_id: The user's ID.
            user_role: The user's system-level role.
            project_id: The project to check access for.
            required_permission: The permission required.

        Returns:
            True if user has access, False otherwise.
        """
        # System admins bypass project-level checks
        if user_role == "admin":
            return True

        # Check cache first
        cache_key = (user_id, project_id)
        if cache_key in self._project_cache:
            cached_role, cached_time = self._project_cache[cache_key]
            if datetime.now(UTC) - cached_time < self._PROJECT_CACHE_TTL:
                return self._role_has_permission(cached_role, required_permission)

        # Database lookup required
        session = get_rbac_session()
        if session is None:
            logger.warning(
                "Cannot check project access for user %s: "
                "no database session provided",
                user_id,
            )
            return False

        from app.models.domain.project_member import ProjectMember

        result = await session.execute(
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
            user_id: The user's ID.
            user_role: The user's system-level role.

        Returns:
            List of project IDs the user can access.
        """
        # System admins have access to all projects
        if user_role == "admin":
            from app.models.domain.project import Project

            session = get_rbac_session()
            if session is None:
                logger.warning(
                    "Cannot get projects for admin user %s: "
                    "no database session provided",
                    user_id,
                )
                return []

            result = await session.execute(select(Project.project_id))
            return [row[0] for row in result.all()]

        # Non-admin users: get their project memberships
        session = get_rbac_session()
        if session is None:
            logger.warning(
                "Cannot get projects for user %s: no database session provided",
                user_id,
            )
            return []

        from app.models.domain.project_member import ProjectMember

        result = await session.execute(
            select(ProjectMember.project_id).where(ProjectMember.user_id == user_id)
        )
        return [row[0] for row in result.all()]

    async def get_project_role(self, user_id: UUID, project_id: UUID) -> str | None:
        """Get user's role within a specific project.

        Args:
            user_id: The user's ID.
            project_id: The project to check.

        Returns:
            The user's project role, or None if not a member.
        """
        # Check cache first
        cache_key = (user_id, project_id)
        if cache_key in self._project_cache:
            cached_role, cached_time = self._project_cache[cache_key]
            if datetime.now(UTC) - cached_time < self._PROJECT_CACHE_TTL:
                return cached_role

        # Database lookup
        session = get_rbac_session()
        if session is None:
            logger.warning(
                "Cannot get project role for user %s: "
                "no database session provided",
                user_id,
            )
            return None

        from app.models.domain.project_member import ProjectMember

        result = await session.execute(
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
