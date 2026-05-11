"""Authentication dependencies for FastAPI routes.

Provides dependency injection for current user authentication and authorization.

RoleChecker and ProjectRoleChecker delegate to the unified RBAC system
(UnifiedRBACService) for all permission checks.
"""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.jwt_utils import validate_jwt_token
from app.core.rbac_unified import (
    get_unified_rbac_service,
    set_unified_rbac_session,
)
from app.db.session import get_db
from app.models.domain.user import User
from app.models.domain.user_role_assignment import ScopeType
from app.services.user import UserService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_user_service(session: AsyncSession = Depends(get_db)) -> UserService:
    return UserService(session)


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    service: UserService = Depends(get_user_service),
) -> User:
    """Get current user from JWT token."""
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

    user = await service.get_by_email(jwt_result.subject)
    if user is None:
        raise credentials_exception

    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Check if current user is active."""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    return current_user


class RoleChecker:
    """FastAPI dependency for role-based and permission-based authorization.

    Delegates to the UnifiedRBACService for permission checks.

    Can be used in three modes:
    1. Role-only: RoleChecker(["admin", "manager"])
    2. Permission-only: RoleChecker(required_permission="delete")
    3. Combined (OR logic): RoleChecker(["admin"], "delete")
    """

    def __init__(
        self,
        allowed_roles: list[str] | None = None,
        required_permission: str | None = None,
    ) -> None:
        """Initialize RoleChecker dependency.

        Args:
            allowed_roles: List of roles that are allowed access
            required_permission: Permission string that is required for access

        Note:
            At least one of allowed_roles or required_permission must be provided.
            If both are provided, access is granted if EITHER condition is met (OR logic).
        """
        self.allowed_roles = allowed_roles
        self.required_permission = required_permission

    async def __call__(
        self,
        current_user: Annotated[User, Depends(get_current_user)],
        session: Annotated[AsyncSession, Depends(get_db)],
    ) -> User:
        """Check if current user has required role or permission.

        Args:
            current_user: The authenticated user from JWT token
            session: Database session

        Returns:
            The current user if authorized

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

            # Check permission-based authorization via unified system
            if self.required_permission is not None:
                has_perm = await unified_service.has_permission(
                    user_id=current_user.user_id,
                    required_permission=self.required_permission,
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
        current_user: Annotated[User, Depends(get_current_active_user)],
        session: Annotated[AsyncSession, Depends(get_db)],
    ) -> User:
        """Check if current user has required permission for the project.

        Args:
            project_id: The project ID to check access for
            current_user: The authenticated user from JWT token
            session: Database session for project-level lookups

        Returns:
            The current user if authorized

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
