"""Pydantic schemas for Control Account entity."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.schemas.mixins import TemporalComputedMixin
from app.models.schemas.temporal_validators import TemporalRange
from app.models.schemas.validators import NotEmptyString


class ControlAccountBase(BaseModel):
    """Base schema for Control Account."""

    name: str = Field(
        ..., min_length=1, max_length=255, description="Control account name"
    )
    code: str | None = Field(None, max_length=50, description="Control account code")
    description: str | None = Field(None, description="Control account description")


class ControlAccountCreate(ControlAccountBase):
    """Schema for creating a new Control Account."""

    control_account_id: UUID | None = Field(
        None,
        description="Root Control Account ID (internal use only for seeding)",
        exclude=True,
    )
    wbs_element_id: UUID = Field(..., description="WBS Element root ID")
    organizational_unit_id: UUID = Field(..., description="Organizational Unit root ID")
    branch: str = Field(
        "main",
        description="Branch name for creation (defaults to main if not specified)",
    )
    control_date: datetime | None = Field(
        None, description="Optional control date for creation (valid_time start)"
    )


class ControlAccountUpdate(BaseModel):
    """Schema for updating an existing Control Account."""

    name: NotEmptyString = Field(None, max_length=255)
    code: str | None = Field(None, max_length=50)
    description: str | None = None
    wbs_element_id: UUID | None = None
    organizational_unit_id: UUID | None = None
    branch: str | None = Field(
        None, description="Branch name for update (defaults to current branch)"
    )
    control_date: datetime | None = Field(
        None, description="Optional control date for update (valid_time start)"
    )


class ControlAccountRead(ControlAccountBase, TemporalComputedMixin):
    """Schema for reading Control Account data."""

    id: UUID
    control_account_id: UUID
    wbs_element_id: UUID
    organizational_unit_id: UUID
    branch: str
    created_by: UUID
    created_by_name: str | None = None
    deleted_by: UUID | None = None
    valid_time: TemporalRange = None
    transaction_time: TemporalRange = None
    # Denormalized names for convenience
    wbs_element_name: str | None = None
    organizational_unit_name: str | None = None

    model_config = ConfigDict(from_attributes=True)


# Alias for backward compatibility
ControlAccountPublic = ControlAccountRead
