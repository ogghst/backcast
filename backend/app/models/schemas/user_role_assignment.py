"""Pydantic schemas for UserRoleAssignment entity."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.domain.user_role_assignment import ScopeType


class UserRoleAssignmentCreate(BaseModel):
    """Schema for creating a new role assignment."""

    user_id: UUID = Field(..., description="UUID of the user to assign")
    role_id: UUID = Field(..., description="UUID of the RBAC role")
    scope_type: ScopeType = Field(..., description="Scope type")
    scope_id: UUID | None = Field(
        None,
        description="UUID of the scoped entity (NULL for global scope)",
    )
    metadata_: dict[str, Any] | None = Field(
        None, description="Additional metadata (e.g., authority_level)"
    )
    granted_by: UUID | None = Field(
        None, description="UUID of the user granting the role"
    )
    expires_at: datetime | None = Field(
        None, description="Optional expiration timestamp"
    )

    @model_validator(mode="after")
    def validate_scope(self) -> "UserRoleAssignmentCreate":
        """Validate scope_id is set for non-global scopes."""
        if self.scope_type != ScopeType.GLOBAL and self.scope_id is None:
            msg = f"scope_id is required for scope_type={self.scope_type.value}"
            raise ValueError(msg)
        if self.scope_type == ScopeType.GLOBAL and self.scope_id is not None:
            msg = "scope_id must be NULL for global scope"
            raise ValueError(msg)
        return self


class UserRoleAssignmentUpdate(BaseModel):
    """Schema for updating a role assignment."""

    role_id: UUID | None = Field(None, description="New RBAC role UUID")
    metadata_: dict[str, Any] | None = Field(None, description="Updated metadata")
    expires_at: datetime | None = Field(
        None, description="Updated expiration timestamp"
    )


class UserRoleAssignmentRead(BaseModel):
    """Schema for reading role assignment data."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    role_id: UUID
    scope_type: str
    scope_id: UUID | None = None
    metadata_: dict[str, Any] | None = Field(None, serialization_alias="metadata")
    granted_by: UUID | None = None
    granted_at: datetime
    expires_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    # Optional populated fields
    role_name: str | None = Field(None, description="Name of the assigned role")
    user_name: str | None = Field(None, description="Full name of the assigned user")
    granted_by_name: str | None = Field(
        None, description="Full name of the user who granted the role"
    )


class UserRoleAssignmentResponse(BaseModel):
    """Schema for role assignment API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    role_id: UUID
    scope_type: str
    scope_id: UUID | None = None
    metadata_: dict[str, Any] | None = Field(None, serialization_alias="metadata")
    granted_by: UUID | None = None
    granted_at: datetime
    expires_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
