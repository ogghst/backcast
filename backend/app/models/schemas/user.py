from datetime import datetime
from typing import TYPE_CHECKING, Annotated, Any
from uuid import UUID

from pydantic import BaseModel, BeforeValidator, ConfigDict, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession

if TYPE_CHECKING:
    from app.models.domain.user import User


def convert_range_to_list(v: Any) -> list[datetime | None] | None:
    """Convert PostgreSQL Range object to list of [lower, upper]."""
    if v is None:
        return None
    if hasattr(v, "lower") and hasattr(v, "upper"):
        return [v.lower, v.upper]
    return v


# Type alias for range fields that need conversion
RangeToList = Annotated[
    list[datetime | None] | None, BeforeValidator(convert_range_to_list)
]


# Shared properties (no role — role is managed via UserRoleAssignment)
class UserBase(BaseModel):
    """Base generic User schema."""

    email: EmailStr
    full_name: str
    department: str | None = None


# Properties to receive via API on creation
class UserRegister(UserBase):
    """Schema for user registration."""

    role: str = "viewer"
    user_id: UUID | None = Field(
        None,
        description="Root User ID (internal use only for seeding)",
        exclude=True,  # Exclude from OpenAPI docs
    )
    password: str = Field(
        min_length=8, description="Password must be at least 8 characters"
    )
    control_date: datetime | None = Field(
        None, description="Optional control date for creation (valid_time start)"
    )


# Properties to receive via API on update
class UserUpdate(BaseModel):
    """Schema for user updates."""

    full_name: str | None = None
    department: str | None = None
    role: str | None = None
    password: str | None = None
    is_active: bool | None = None
    control_date: datetime | None = Field(
        None, description="Optional control date for valid_time"
    )


# Properties to return to client (public implementation)
class UserRead(UserBase):
    """Schema for reading user data (excludes password)."""

    id: UUID
    user_id: UUID
    is_active: bool
    created_at: datetime | None = None  # For temporal compatibility
    password_changed_at: datetime | None = None  # Track password changes
    preferences: dict[str, Any] | None = None  # User preferences as JSON

    model_config = ConfigDict(from_attributes=True)


# Public user schema with RBAC permissions
class UserPublic(BaseModel):
    """User public data with RBAC permissions for frontend.

    Must be constructed via from_user() or from_user_async().
    Role is resolved from UserRoleAssignment, not the User model.
    """

    id: UUID
    user_id: UUID  # For compatibility with versioning
    email: str
    full_name: str
    role: str
    is_active: bool
    permissions: list[str] = Field(
        default_factory=list,
        description="List of permission strings (e.g., 'user-read', 'department-delete')",
    )

    @classmethod
    def from_user(cls, user: "User") -> "UserPublic":
        """Create UserPublic from User domain object with fallback role.

        DEPRECATED: Use from_user_async() for proper role and permission loading.
        This synchronous version cannot look up roles from UserRoleAssignment and
        will return "viewer" as a fallback role with empty permissions.

        Args:
            user: User domain object

        Returns:
            UserPublic instance with fallback role and empty permissions
        """
        return cls(
            id=user.id,
            user_id=user.user_id,
            email=user.email,
            full_name=user.full_name,
            role="viewer",
            is_active=user.is_active,
            permissions=[],
        )

    @classmethod
    async def from_user_async(
        cls, user: "User", session: "AsyncSession"
    ) -> "UserPublic":
        """Create UserPublic from User domain object with RBAC permissions.

        Resolves the user's global role from UserRoleAssignment and loads
        permissions for that role via the unified RBAC service.

        Args:
            user: User domain object
            session: Database session for RBAC service

        Returns:
            UserPublic instance with permissions populated
        """
        from app.core.rbac_unified import (
            get_unified_rbac_service,
            set_unified_rbac_session,
        )

        try:
            set_unified_rbac_session(session)
            unified_service = get_unified_rbac_service()

            # Resolve role from UserRoleAssignment
            roles = await unified_service.get_user_roles(
                user.user_id, "global", None
            )
            display_role = roles[0] if roles else "viewer"

            # Try cache first for permissions
            perms = unified_service._get_cached_permissions(display_role)

            # If cache miss, load from database
            if perms is None:
                from sqlalchemy import select

                from app.models.domain.rbac import RBACRole, RBACRolePermission

                stmt = (
                    select(RBACRolePermission.permission)
                    .join(RBACRole, RBACRolePermission.role_id == RBACRole.id)
                    .where(RBACRole.name == display_role)
                )
                result = await session.execute(stmt)
                perms = [row[0] for row in result.all()]

                if perms:
                    unified_service._cache_permissions(display_role, perms)

            permissions = perms if perms is not None else []

        finally:
            set_unified_rbac_session(None)

        return cls(
            id=user.id,
            user_id=user.user_id,
            email=user.email,
            full_name=user.full_name,
            role=display_role,
            is_active=user.is_active,
            permissions=permissions,
        )


# Schema for version history - includes temporal fields
class UserHistory(UserRead):
    """Schema for reading user version history (includes temporal fields)."""

    valid_time: RangeToList = Field(
        None, description="Valid time range for this version"
    )
    transaction_time: RangeToList = Field(
        None, description="Transaction time range for this version"
    )
    created_by: UUID
    created_by_name: str | None = None
    deleted_by: UUID | None = None

    model_config = ConfigDict(from_attributes=True)


# Login schema
class UserLogin(BaseModel):
    """Schema for user login credentials."""

    email: EmailStr
    password: str


# Token schema
class Token(BaseModel):
    """Schema for authentication token."""

    access_token: str
    token_type: str = "bearer"


# Token response with refresh token
class TokenResponse(BaseModel):
    """Schema for authentication token response including refresh token."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


# Refresh token request
class RefreshRequest(BaseModel):
    """Schema for refresh token request."""

    refresh_token: str


class TokenPayload(BaseModel):
    """Schema for token payload data."""

    sub: str | None = None
