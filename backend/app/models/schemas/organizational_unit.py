"""Pydantic schemas for Organizational Unit entity."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.schemas.temporal_validators import TemporalRange

if TYPE_CHECKING:
    pass


class OrganizationalUnitBase(BaseModel):
    """Base schema for Organizational Unit."""

    name: str = Field(
        ..., max_length=255, description="Organizational unit display name"
    )
    manager_id: UUID | None = Field(
        None, description="UUID of the organizational unit manager"
    )
    is_active: bool = Field(
        True, description="Whether the organizational unit is active"
    )
    description: str | None = Field(
        None, max_length=5000, description="Organizational unit description"
    )
    parent_unit_id: UUID | None = Field(
        None, description="Parent Organizational Unit root ID for hierarchy"
    )


class OrganizationalUnitCreate(OrganizationalUnitBase):
    """Schema for creating a new Organizational Unit."""

    organizational_unit_id: UUID | None = Field(
        None,
        description="Root Organizational Unit ID (internal use only for seeding)",
        exclude=True,
    )
    code: str = Field(
        ...,
        max_length=50,
        pattern="^[A-Z0-9_-]+$",
        description="Unique organizational unit code (immutable)",
    )
    branch: str = Field(
        "main",
        description="Branch name for creation (defaults to main if not specified)",
    )
    control_date: datetime | None = Field(
        None, description="Optional control date for creation (valid_time start)"
    )


class OrganizationalUnitUpdate(BaseModel):
    """Schema for updating an existing Organizational Unit."""

    name: str | None = Field(None, max_length=255)
    code: str | None = Field(None, max_length=50, pattern="^[A-Z0-9_-]+$")
    manager_id: UUID | None = None
    is_active: bool | None = None
    description: str | None = Field(None, max_length=5000)
    parent_unit_id: UUID | None = None
    branch: str | None = Field(
        None, description="Branch name for update (defaults to current branch)"
    )
    control_date: datetime | None = Field(
        None, description="Optional control date for update (valid_time start)"
    )


class OrganizationalUnitRead(OrganizationalUnitBase):
    """Schema for reading organizational unit data."""

    id: UUID
    organizational_unit_id: UUID
    code: str
    parent_unit_name: str | None = Field(
        None, description="Parent unit display name (computed)"
    )
    branch: str
    is_active: bool
    created_at: datetime | None = None
    created_by: UUID
    created_by_name: str | None = None
    deleted_by: UUID | None = None
    valid_time: TemporalRange = None
    transaction_time: TemporalRange = None

    model_config = ConfigDict(from_attributes=True)


# Alias for backward compatibility
OrganizationalUnitPublic = OrganizationalUnitRead
