"""Pydantic schemas for RBAC admin API."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RBACPermissionRead(BaseModel):
    """Single permission within a role."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    permission: str


class RBACRoleCreate(BaseModel):
    """Schema for creating a new RBAC role."""

    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    permissions: list[str] = Field(..., min_length=1)


class RBACRoleUpdate(BaseModel):
    """Schema for updating an existing RBAC role."""

    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = None
    permissions: list[str] | None = None


class RBACRoleRead(BaseModel):
    """Schema for reading RBAC role data."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    is_system: bool
    permissions: list[RBACPermissionRead]
    created_at: datetime
    updated_at: datetime


class RBACProviderStatus(BaseModel):
    """Schema for RBAC provider status."""

    provider: str
    editable: bool
