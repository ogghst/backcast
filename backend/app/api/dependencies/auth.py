"""Authentication dependencies for FastAPI routes.

Provides dependency injection for current user authentication and authorization.
"""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.rbac import RBACServiceABC, get_rbac_service
from app.db.session import get_db
from app.models.domain.user import User
from app.models.schemas.user import TokenPayload
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

    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        token_data = TokenPayload(**payload)
    except (JWTError, ValidationError) as e:
        raise credentials_exception from e

    if token_data.sub is None:
        raise credentials_exception

    user = await service.get_by_email(token_data.sub)
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

    Can be used in three modes:
    1. Role-only: RoleChecker(["admin", "manager"])
    2. Permission-only: RoleChecker(required_permission="delete")
    3. Combined (OR logic): RoleChecker(["admin"], "delete")

    Example usage:
        @app.post("/users/", dependencies=[Depends(RoleChecker(["admin"]))])
        async def create_user(): ...

        @app.delete("/items/{id}", dependencies=[Depends(RoleChecker(required_permission="delete"))])
        async def delete_item(): ...
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
        rbac_service: Annotated[RBACServiceABC, Depends(get_rbac_service)],
    ) -> User:
        """Check if current user has required role or permission.

        Args:
            current_user: The authenticated user from JWT token
            rbac_service: The RBAC service for authorization checks

        Returns:
            The current user if authorized

        Raises:
            HTTPException: 403 Forbidden if user lacks required role/permission
        """
        # Check role-based authorization
        if self.allowed_roles is not None:
            if rbac_service.has_role(current_user.role, self.allowed_roles):
                return current_user

        # Check permission-based authorization
        if self.required_permission is not None:
            if rbac_service.has_permission(current_user.role, self.required_permission):
                return current_user

        # If we reach here, neither role nor permission matched
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )


class ProjectRoleChecker:
    """FastAPI dependency for project-level role-based authorization.

    Checks if a user has the required permission for a specific project.
    System admins bypass project-level checks and always have access.

    Example usage:
        @app.get("/projects/{project_id}/wbes",
                 dependencies=[Depends(ProjectRoleChecker(required_permission="project-read"))])
        async def get_project_wbes(project_id: UUID): ...
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
        rbac_service: Annotated[RBACServiceABC, Depends(get_rbac_service)],
        session: Annotated[AsyncSession, Depends(get_db)],
    ) -> User:
        """Check if current user has required permission for the project.

        Args:
            project_id: The project ID to check access for
            current_user: The authenticated user from JWT token
            rbac_service: The RBAC service for authorization checks
            session: Database session for project-level lookups

        Returns:
            The current user if authorized

        Raises:
            HTTPException: 403 Forbidden if user lacks required permission
        """
        # Inject session into rbac_service if it supports it
        if hasattr(rbac_service, "session"):
            rbac_service.session = session

        # Check if user has access to the project
        has_access = await rbac_service.has_project_access(
            user_id=current_user.user_id,
            user_role=current_user.role,
            project_id=project_id,
            required_permission=self.required_permission,
        )

        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions for project {project_id}",
            )

        return current_user
