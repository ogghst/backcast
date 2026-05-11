"""Unified RBAC service with scoped role assignments.

Provides a single RBAC system that handles:
- Global (system-level) role assignments
- Project-scoped role assignments
- Change order scoped role assignments with authority levels

Replaces: RoleChecker, ProjectRoleChecker, ApprovalMatrixService
Uses cache-first approach with TTL for performance.
Thread-safe via ContextVar session injection pattern.
"""

import contextvars
import logging
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain.rbac import RBACRole, RBACRolePermission
from app.models.domain.user_role_assignment import (
    ScopeType,
    UserRoleAssignment,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# ContextVar for request-scoped session injection
# ---------------------------------------------------------------------------
_unified_rbac_session: contextvars.ContextVar[AsyncSession | None] = (
    contextvars.ContextVar("_unified_rbac_session", default=None)
)


def get_unified_rbac_session() -> AsyncSession | None:
    """Get the request-scoped unified RBAC database session."""
    return _unified_rbac_session.get()


def set_unified_rbac_session(session: AsyncSession | None) -> None:
    """Set the request-scoped unified RBAC database session."""
    _unified_rbac_session.set(session)


# ---------------------------------------------------------------------------
# UnifiedRBACService
# ---------------------------------------------------------------------------


class UnifiedRBACService:
    """Unified RBAC service with scoped role assignments and caching.

    Cache layers:
    - _permissions_cache: {role_name: (permissions_list, timestamp)} (TTL: 1h)
    - _assignment_cache: {(user_id, scope_type, scope_id): (role_names, timestamp)}
      (TTL: 5 min)

    All permission checks are cache-first. Database queries only happen on
    cache miss. Fail-secure: deny access on cache miss or system error.
    """

    _PERMISSIONS_CACHE_TTL = timedelta(hours=1)
    _ASSIGNMENT_CACHE_TTL = timedelta(minutes=5)

    def __init__(self) -> None:
        """Initialize with empty caches."""
        # Permissions cache: role_name -> (permissions_list, cached_at)
        self._permissions_cache: dict[str, tuple[list[str], datetime]] = {}
        # Assignment cache: (user_id, scope_type, scope_id) -> (role_names, cached_at)
        self._assignment_cache: dict[
            tuple[UUID, str, UUID | None], tuple[list[str], datetime]
        ] = {}

    # ------------------------------------------------------------------
    # Cache management
    # ------------------------------------------------------------------

    async def refresh_permissions_cache(self) -> None:
        """Load all role-permission mappings from database into cache.

        Called at startup and after write operations that modify roles or
        permissions. Replaces the entire cache with fresh data.
        """
        session = get_unified_rbac_session()
        if session is None:
            logger.warning("Cannot refresh RBAC permissions cache: no session")
            return

        result = await session.execute(
            select(RBACRole.name, RBACRolePermission.permission).join(
                RBACRolePermission, RBACRole.permissions
            )
        )

        role_perms: dict[str, list[str]] = {}
        for role_name, permission in result.all():
            role_perms.setdefault(role_name, []).append(permission)

        now = datetime.now(UTC)
        self._permissions_cache.clear()
        for role_name, perms in role_perms.items():
            self._permissions_cache[role_name] = (perms, now)

        logger.info(
            "Refreshed unified RBAC permissions cache: %d roles loaded",
            len(self._permissions_cache),
        )

    def _get_cached_permissions(self, role_name: str) -> list[str] | None:
        """Get permissions for a role from cache.

        Returns None on cache miss or expired entry.
        """
        cached = self._permissions_cache.get(role_name)
        if cached is None:
            return None
        perms, cached_at = cached
        if datetime.now(UTC) - cached_at > self._PERMISSIONS_CACHE_TTL:
            return None
        return perms

    def _cache_permissions(self, role_name: str, permissions: list[str]) -> None:
        """Store permissions in cache."""
        self._permissions_cache[role_name] = (permissions, datetime.now(UTC))

    def _get_cached_assignments(
        self, user_id: UUID, scope_type: str, scope_id: UUID | None
    ) -> list[str] | None:
        """Get role names for a user-scope combination from cache.

        Returns None on cache miss or expired entry.
        """
        cache_key = (user_id, scope_type, scope_id)
        cached = self._assignment_cache.get(cache_key)
        if cached is None:
            return None
        role_names, cached_at = cached
        if datetime.now(UTC) - cached_at > self._ASSIGNMENT_CACHE_TTL:
            del self._assignment_cache[cache_key]
            return None
        return role_names

    def _cache_assignments(
        self,
        user_id: UUID,
        scope_type: str,
        scope_id: UUID | None,
        role_names: list[str],
    ) -> None:
        """Store role assignments in cache."""
        cache_key = (user_id, scope_type, scope_id)
        self._assignment_cache[cache_key] = (role_names, datetime.now(UTC))

    def _invalidate_assignment_cache(
        self,
        user_id: UUID,
        scope_type: str | None = None,
        scope_id: UUID | None = None,
    ) -> None:
        """Invalidate assignment cache for a user.

        If scope_type is None, invalidate all entries for the user.
        """
        if scope_type is None:
            keys_to_remove = [k for k in self._assignment_cache if k[0] == user_id]
        else:
            keys_to_remove = [
                k
                for k in self._assignment_cache
                if k[0] == user_id
                and k[1] == scope_type
                and (scope_id is None or k[2] == scope_id)
            ]
        for key in keys_to_remove:
            del self._assignment_cache[key]

    # ------------------------------------------------------------------
    # Permission checking (cache-first)
    # ------------------------------------------------------------------

    def _check_permission_from_roles(
        self, role_names: list[str], required_permission: str
    ) -> bool:
        """Check if any of the given roles have the required permission.

        Reads from permissions cache only. Returns False on cache miss.
        """
        for role_name in role_names:
            perms = self._get_cached_permissions(role_name)
            if perms is not None and required_permission in perms:
                return True
        return False

    async def has_permission(
        self,
        user_id: UUID,
        required_permission: str,
        scope_type: str = ScopeType.GLOBAL,
        scope_id: UUID | None = None,
    ) -> bool:
        """Check if user has permission in the specified scope.

        Resolution order:
        1. Check global roles (always)
        2. Check scoped roles (if scope_type != global)

        Admin role always grants access.

        Args:
            user_id: The user's root ID.
            required_permission: Permission string to check.
            scope_type: The scope to check in.
            scope_id: The scoped entity ID (None for global).

        Returns:
            True if user has the permission, False otherwise.
        """
        # Step 1: Check global roles (always checked)
        global_roles = await self.get_user_roles(user_id, ScopeType.GLOBAL, None)

        # Admin bypasses all checks
        if "admin" in global_roles:
            return True

        # Check global roles for the permission
        if self._check_permission_from_roles(global_roles, required_permission):
            return True

        # Step 2: Check scoped roles if not global scope
        if scope_type != ScopeType.GLOBAL:
            scoped_roles = await self.get_user_roles(user_id, scope_type, scope_id)
            if self._check_permission_from_roles(scoped_roles, required_permission):
                return True

        return False

    async def has_authority_level(
        self,
        user_id: UUID,
        required_authority: str,
        scope_id: UUID | None = None,
    ) -> bool:
        """Check if user has sufficient authority level for approval.

        Reads authority_level from UserRoleAssignment.metadata for
        change_order scoped assignments.

        Args:
            user_id: The user's root ID.
            required_authority: Required authority level string.
            scope_id: The project/change_order scope ID.

        Returns:
            True if user's authority >= required authority.
        """
        # Standard authority hierarchy
        hierarchy = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}

        required_level = hierarchy.get(required_authority, 0)
        if required_level == 0:
            return False

        # Check change_order scoped assignments
        session = get_unified_rbac_session()
        if session is None:
            return False

        stmt = select(UserRoleAssignment).where(
            UserRoleAssignment.user_id == user_id,
            UserRoleAssignment.scope_type == ScopeType.CHANGE_ORDER,
            UserRoleAssignment.scope_id == scope_id,
        )
        result = await session.execute(stmt)
        assignments = result.scalars().all()

        for assignment in assignments:
            if assignment.metadata_ and "authority_level" in assignment.metadata_:
                user_authority = assignment.metadata_["authority_level"]
                user_level = hierarchy.get(user_authority, 0)
                if user_level >= required_level:
                    return True

        # Also check global roles via config mapping
        # Admin always has authority
        global_roles = await self.get_user_roles(user_id, ScopeType.GLOBAL, None)
        if "admin" in global_roles:
            return True

        return False

    # ------------------------------------------------------------------
    # Role assignment queries
    # ------------------------------------------------------------------

    async def get_user_roles(
        self,
        user_id: UUID,
        scope_type: str = ScopeType.GLOBAL,
        scope_id: UUID | None = None,
    ) -> list[str]:
        """Get role names for a user in a specific scope.

        Uses assignment cache. On cache miss, queries the database.

        Args:
            user_id: The user's root ID.
            scope_type: The scope to look up.
            scope_id: The scoped entity ID (None for global).

        Returns:
            List of role names assigned to the user in this scope.
        """
        # Check cache
        cached = self._get_cached_assignments(user_id, scope_type, scope_id)
        if cached is not None:
            return cached

        # Database query
        session = get_unified_rbac_session()
        if session is None:
            return []

        stmt = (
            select(RBACRole.name)
            .join(UserRoleAssignment, UserRoleAssignment.role_id == RBACRole.id)
            .where(
                UserRoleAssignment.user_id == user_id,
                UserRoleAssignment.scope_type == scope_type,
                UserRoleAssignment.scope_id == scope_id
                if scope_id is not None
                else UserRoleAssignment.scope_id.is_(None),
            )
        )
        result = await session.execute(stmt)
        role_names = [row[0] for row in result.all()]

        # Cache the result
        self._cache_assignments(user_id, scope_type, scope_id, role_names)

        return role_names

    async def get_assignments_by_scope(
        self,
        scope_type: str,
        scope_id: UUID | None = None,
    ) -> list[UserRoleAssignment]:
        """Get all role assignments for a scope.

        Args:
            scope_type: The scope type.
            scope_id: The scoped entity ID (None for global).

        Returns:
            List of UserRoleAssignment entities.
        """
        session = get_unified_rbac_session()
        if session is None:
            return []

        conditions = [
            UserRoleAssignment.scope_type == scope_type,
        ]
        if scope_id is not None:
            conditions.append(UserRoleAssignment.scope_id == scope_id)
        else:
            conditions.append(UserRoleAssignment.scope_id.is_(None))

        stmt = select(UserRoleAssignment).where(*conditions)
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def get_all_user_assignments(self, user_id: UUID) -> list[UserRoleAssignment]:
        """Get all role assignments for a user across all scopes.

        Args:
            user_id: The user's root ID.

        Returns:
            List of UserRoleAssignment entities.
        """
        session = get_unified_rbac_session()
        if session is None:
            return []

        stmt = select(UserRoleAssignment).where(UserRoleAssignment.user_id == user_id)
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def get_accessible_projects(self, user_id: UUID) -> list[UUID]:
        """Return list of project IDs the user has access to.

        Admin users with a global admin role get all project IDs.
        Other users get the distinct scope_ids from their project-scoped
        role assignments.

        Args:
            user_id: The user's root ID.

        Returns:
            List of project UUIDs the user can access.
        """
        from app.models.domain.project import Project

        # Admins can access all projects
        global_roles = await self.get_user_roles(user_id, ScopeType.GLOBAL, None)
        if "admin" in global_roles:
            session = get_unified_rbac_session()
            if session is None:
                return []
            result = await session.execute(select(Project.id))
            return [row[0] for row in result.all()]

        # Non-admin: project-scoped assignments
        session = get_unified_rbac_session()
        if session is None:
            return []

        stmt = (
            select(UserRoleAssignment.scope_id)
            .where(
                UserRoleAssignment.user_id == user_id,
                UserRoleAssignment.scope_type == ScopeType.PROJECT,
            )
            .distinct()
        )
        result = await session.execute(stmt)
        return [row[0] for row in result.all() if row[0] is not None]

    async def has_project_access(
        self, user_id: UUID, project_id: UUID, required_permission: str
    ) -> bool:
        """Check if user has access to a project with required permission.

        Convenience wrapper around has_permission with project scope.
        Global admins always pass.

        Args:
            user_id: The user's root ID.
            project_id: The project UUID.
            required_permission: Permission string to check.

        Returns:
            True if user has the permission in this project scope.
        """
        return await self.has_permission(
            user_id, required_permission, ScopeType.PROJECT, project_id
        )

    async def get_project_role(
        self, user_id: UUID, project_id: UUID
    ) -> str | None:
        """Get the user's role name for a specific project.

        Admin users return "project_admin" as they have full access.

        Args:
            user_id: The user's root ID.
            project_id: The project UUID.

        Returns:
            Role name string or None if user is not a project member.
        """
        # Admin shortcut
        global_roles = await self.get_user_roles(user_id, ScopeType.GLOBAL, None)
        if "admin" in global_roles:
            return "project_admin"

        session = get_unified_rbac_session()
        if session is None:
            return None

        stmt = (
            select(RBACRole.name)
            .join(UserRoleAssignment, UserRoleAssignment.role_id == RBACRole.id)
            .where(
                UserRoleAssignment.user_id == user_id,
                UserRoleAssignment.scope_type == ScopeType.PROJECT,
                UserRoleAssignment.scope_id == project_id,
            )
        )
        result = await session.execute(stmt)
        row = result.first()
        return row[0] if row is not None else None

    async def get_user_permissions(
        self,
        user_id: UUID,
        scope_type: str = ScopeType.GLOBAL,
        scope_id: UUID | None = None,
    ) -> list[str]:
        """Get all permissions for a user in a specific scope.

        Combines global role permissions with scoped role permissions.
        Admin role returns ["*"].

        Args:
            user_id: The user's root ID.
            scope_type: The scope to check (default: GLOBAL).
            scope_id: The scoped entity ID (None for global).

        Returns:
            Deduplicated list of permission strings.
        """
        # Collect roles from global + requested scope
        global_roles = await self.get_user_roles(user_id, ScopeType.GLOBAL, None)
        all_roles = set(global_roles)

        if scope_type != ScopeType.GLOBAL:
            scoped_roles = await self.get_user_roles(user_id, scope_type, scope_id)
            all_roles.update(scoped_roles)

        # Admin wildcard
        if "admin" in all_roles:
            return ["*"]

        # Collect permissions from all roles via cache
        permissions: set[str] = set()
        for role_name in all_roles:
            perms = self._get_cached_permissions(role_name)
            if perms is not None:
                permissions.update(perms)

        return sorted(permissions)

    # ------------------------------------------------------------------
    # CRUD operations
    # ------------------------------------------------------------------

    async def assign_role(
        self,
        user_id: UUID,
        role_id: UUID,
        scope_type: str,
        scope_id: UUID | None = None,
        metadata: dict[str, Any] | None = None,
        granted_by: UUID | None = None,
        expires_at: datetime | None = None,
    ) -> UserRoleAssignment:
        """Create a new role assignment.

        Args:
            user_id: The user's root ID.
            role_id: The RBAC role UUID.
            scope_type: Scope type (global/project/change_order).
            scope_id: Scoped entity ID (None for global).
            metadata: Optional metadata (e.g., authority_level).
            granted_by: UUID of the user granting the role.
            expires_at: Optional expiration timestamp.

        Returns:
            The created UserRoleAssignment.

        Raises:
            ValueError: If assignment already exists.
        """
        session = get_unified_rbac_session()
        if session is None:
            msg = "No database session available"
            raise RuntimeError(msg)

        # Check for existing assignment
        conditions = [
            UserRoleAssignment.user_id == user_id,
            UserRoleAssignment.scope_type == scope_type,
        ]
        if scope_id is not None:
            conditions.append(UserRoleAssignment.scope_id == scope_id)
        else:
            conditions.append(UserRoleAssignment.scope_id.is_(None))

        existing = await session.execute(select(UserRoleAssignment).where(*conditions))
        if existing.scalar_one_or_none() is not None:
            msg = (
                f"User {user_id} already has a role assignment for "
                f"scope_type={scope_type}, scope_id={scope_id}"
            )
            raise ValueError(msg)

        assignment = UserRoleAssignment(
            id=uuid4(),
            user_id=user_id,
            role_id=role_id,
            scope_type=scope_type,
            scope_id=scope_id,
            metadata_=metadata,
            granted_by=granted_by,
            granted_at=datetime.now(UTC),
            expires_at=expires_at,
        )

        session.add(assignment)
        await session.flush()

        # Invalidate cache
        self._invalidate_assignment_cache(user_id, scope_type, scope_id)

        logger.info(
            "Assigned role %s to user %s in scope %s/%s",
            role_id,
            user_id,
            scope_type,
            scope_id,
        )

        return assignment

    async def revoke_role(
        self,
        user_id: UUID,
        scope_type: str,
        scope_id: UUID | None = None,
    ) -> bool:
        """Revoke a role assignment.

        Args:
            user_id: The user's root ID.
            scope_type: Scope type.
            scope_id: Scoped entity ID (None for global).

        Returns:
            True if an assignment was found and deleted.
        """
        session = get_unified_rbac_session()
        if session is None:
            msg = "No database session available"
            raise RuntimeError(msg)

        conditions = [
            UserRoleAssignment.user_id == user_id,
            UserRoleAssignment.scope_type == scope_type,
        ]
        if scope_id is not None:
            conditions.append(UserRoleAssignment.scope_id == scope_id)
        else:
            conditions.append(UserRoleAssignment.scope_id.is_(None))

        result = await session.execute(select(UserRoleAssignment).where(*conditions))
        assignment = result.scalar_one_or_none()

        if assignment is None:
            return False

        await session.delete(assignment)
        await session.flush()

        # Invalidate cache
        self._invalidate_assignment_cache(user_id, scope_type, scope_id)

        logger.info(
            "Revoked role from user %s in scope %s/%s",
            user_id,
            scope_type,
            scope_id,
        )

        return True

    async def update_assignment(
        self,
        assignment_id: UUID,
        role_id: UUID | None = None,
        metadata: dict[str, Any] | None = None,
        expires_at: datetime | None = None,
    ) -> UserRoleAssignment | None:
        """Update an existing role assignment.

        Args:
            assignment_id: The assignment UUID.
            role_id: Optional new role UUID.
            metadata: Optional updated metadata.
            expires_at: Optional updated expiration.

        Returns:
            Updated UserRoleAssignment or None if not found.
        """
        session = get_unified_rbac_session()
        if session is None:
            msg = "No database session available"
            raise RuntimeError(msg)

        result = await session.execute(
            select(UserRoleAssignment).where(UserRoleAssignment.id == assignment_id)
        )
        assignment = result.scalar_one_or_none()

        if assignment is None:
            return None

        if role_id is not None:
            assignment.role_id = role_id
        if metadata is not None:
            assignment.metadata_ = metadata
        if expires_at is not None:
            assignment.expires_at = expires_at

        await session.flush()

        # Invalidate cache for this user/scope
        self._invalidate_assignment_cache(
            assignment.user_id, assignment.scope_type, assignment.scope_id
        )

        return assignment


# ---------------------------------------------------------------------------
# Global singleton instance
# ---------------------------------------------------------------------------
_unified_rbac_service: UnifiedRBACService | None = None


def get_unified_rbac_service() -> UnifiedRBACService:
    """Get the global UnifiedRBACService instance (singleton pattern).

    Returns:
        The global UnifiedRBACService instance.
    """
    global _unified_rbac_service
    if _unified_rbac_service is None:
        _unified_rbac_service = UnifiedRBACService()
    return _unified_rbac_service


def set_unified_rbac_service(service: UnifiedRBACService) -> None:
    """Set the global UnifiedRBACService instance (for testing)."""
    global _unified_rbac_service
    _unified_rbac_service = service


# ---------------------------------------------------------------------------
# UnifiedChecker - FastAPI dependency (defined in auth.py to avoid circular import)
# ---------------------------------------------------------------------------
