"""Authentication dependencies for FastAPI routes.

Provides dependency injection for current user authentication and authorization.

UserIdentity is a lightweight dataclass. The JWT sub claim carries the
user_id (UUID string). After token validation, the user's is_active status
is checked against the database to reject deactivated accounts. The active
check is cached in-memory with a TTL to avoid a temporal DB query on every
request.

RoleChecker and ProjectRoleChecker delegate to the unified RBAC system
(UnifiedRBACService) for all permission checks.
"""

from dataclasses import dataclass
from typing import Annotated, Any, cast
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import TTLCache
from app.core.jwt_utils import validate_jwt_token
from app.core.rbac_unified import (
    get_unified_rbac_service,
    set_unified_rbac_session,
)
from app.core.temporal_queries import is_current_version
from app.db.session import get_db
from app.models.domain.user import User
from app.models.domain.user_role_assignment import ScopeType
from app.services.user import UserService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# ---------------------------------------------------------------------------
# In-memory TTL cache for user is_active checks (positive results only)
# ---------------------------------------------------------------------------
_user_active_cache: TTLCache[UUID, bool] = TTLCache(ttl=300.0, maxsize=10_000)


def invalidate_user_active_cache(user_id: UUID) -> None:
    """Invalidate cached is_active status for a user.

    Call this when a user is deactivated or soft-deleted
    to ensure immediate effect on subsequent requests.
    """
    _user_active_cache.invalidate(user_id)


def get_user_service(session: AsyncSession = Depends(get_db)) -> UserService:
    return UserService(session)


@dataclass(frozen=True)
class UserIdentity:
    """Lightweight authenticated user identity.

    Carries only the user_id extracted from the JWT sub claim.
    Routes that need the full User ORM object (e.g. /auth/me) must
    perform their own DB lookup using this user_id.
    """

    user_id: UUID


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> UserIdentity:
    """Get current user identity from JWT token.

    Validates the JWT, then checks that the user is still active in the
    database. Deactivated users with a valid token are rejected.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    jwt_result = validate_jwt_token(token)
    if not jwt_result.is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=jwt_result.error_detail,
            headers={"WWW-Authenticate": "Bearer"},
        )

    if jwt_result.subject is None:
        raise credentials_exception

    try:
        user_id = UUID(jwt_result.subject)
    except ValueError:
        raise credentials_exception from None

    # Verify user is still active — cache-first to avoid temporal DB hit
    if user_id in _user_active_cache:
        return UserIdentity(user_id=user_id)

    # Cache miss — query DB
    stmt = (
        select(User.is_active)
        .where(
            User.user_id == user_id,
            is_current_version(
                cast(Any, User).valid_time,
                cast(Any, User).deleted_at,
            ),
        )
        .limit(1)
    )
    result = await session.execute(stmt)
    row = result.scalar_one_or_none()

    if row is None or not row:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is deactivated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Cache the positive result
    _user_active_cache.set(user_id, True)
    return UserIdentity(user_id=user_id)


class RoleChecker:
    """FastAPI dependency for role-based and permission-based authorization.

    Delegates to the UnifiedRBACService for permission checks.

    Can be used in four modes (combined with OR logic across whichever
    are provided):
    1. Role-only: RoleChecker(["admin", "manager"])
    2. Single permission: RoleChecker(required_permission="delete")
    3. Any-of permissions: RoleChecker(
           required_permissions=["project-read", "portfolio-read"]
       )  -- grants access if the user holds ANY of the listed permissions.
    4. Combined: RoleChecker(["admin"], required_permission="delete")

    The any-of mode (``required_permissions``) is what allows a route to be
    reachable by holders of *different* read permissions (e.g. the dashboard
    layout routes serve both project-read and portfolio-read roles).
    """

    def __init__(
        self,
        allowed_roles: list[str] | None = None,
        required_permission: str | None = None,
        required_permissions: list[str] | None = None,
    ) -> None:
        """Initialize RoleChecker dependency.

        Args:
            allowed_roles: List of roles that are allowed access (any-of).
            required_permission: Single permission string required for access.
                Kept for backward compatibility; equivalent to
                ``required_permissions=[required_permission]``.
            required_permissions: List of permission strings; access is granted
                if the user holds ANY of them. Mutually independent of
                ``required_permission`` (both are checked when set).

        Note:
            At least one of ``allowed_roles``, ``required_permission``, or
            ``required_permissions`` must be provided. If more than one is
            provided, access is granted if ANY condition is met (OR logic).
        """
        self.allowed_roles = allowed_roles
        self.required_permission = required_permission
        self.required_permissions = required_permissions

    async def __call__(
        self,
        current_user: Annotated[UserIdentity, Depends(get_current_user)],
        session: Annotated[AsyncSession, Depends(get_db)],
    ) -> UserIdentity:
        """Check if current user has required role or permission.

        Args:
            current_user: The authenticated user identity from JWT token
            session: Database session

        Returns:
            The current user identity if authorized

        Raises:
            HTTPException: 403 Forbidden if user lacks required role/permission
        """
        try:
            set_unified_rbac_session(session)
            unified_service = get_unified_rbac_service()

            # Check role-based authorization via unified system
            if self.allowed_roles is not None:
                global_roles = await unified_service.get_user_roles(
                    current_user.user_id, ScopeType.GLOBAL, None
                )
                if any(role in global_roles for role in self.allowed_roles):
                    return current_user

            # Check single-permission authorization via unified system
            if self.required_permission is not None:
                has_perm = await unified_service.has_permission(
                    user_id=current_user.user_id,
                    required_permission=self.required_permission,
                    scope_type=ScopeType.GLOBAL,
                    scope_id=None,
                )
                if has_perm:
                    return current_user

            # Check any-of permissions: grant if the user holds ANY of them
            if self.required_permissions is not None:
                for perm in self.required_permissions:
                    has_perm = await unified_service.has_permission(
                        user_id=current_user.user_id,
                        required_permission=perm,
                        scope_type=ScopeType.GLOBAL,
                        scope_id=None,
                    )
                    if has_perm:
                        return current_user
        finally:
            set_unified_rbac_session(None)

        # Neither role nor permission granted access
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )


class ProjectRoleChecker:
    """FastAPI dependency for project-level role-based authorization.

    Delegates to the UnifiedRBACService for project-scoped permission checks.
    """

    def __init__(self, required_permission: str) -> None:
        """Initialize ProjectRoleChecker dependency.

        Args:
            required_permission: Permission string required for project access
        """
        self.required_permission = required_permission

    async def __call__(
        self,
        project_id: UUID,
        current_user: Annotated[UserIdentity, Depends(get_current_user)],
        session: Annotated[AsyncSession, Depends(get_db)],
    ) -> UserIdentity:
        """Check if current user has required permission for the project.

        Args:
            project_id: The project ID to check access for
            current_user: The authenticated user identity from JWT token
            session: Database session for project-level lookups

        Returns:
            The current user identity if authorized

        Raises:
            HTTPException: 403 Forbidden if user lacks required permission
        """
        try:
            set_unified_rbac_session(session)
            unified_service = get_unified_rbac_service()

            has_perm = await unified_service.has_permission(
                user_id=current_user.user_id,
                required_permission=self.required_permission,
                scope_type=ScopeType.PROJECT,
                scope_id=project_id,
            )
            if has_perm:
                return current_user
        finally:
            set_unified_rbac_session(None)

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Insufficient permissions for project {project_id}",
        )
