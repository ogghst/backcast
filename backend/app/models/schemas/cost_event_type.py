"""Pydantic schemas for Cost Event Type entity."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CostEventTypeBase(BaseModel):
    """Base schema for Cost Event Type."""

    code: str = Field(..., min_length=1, max_length=50, description="Type code")
    name: str = Field(..., min_length=1, max_length=255, description="Display name")
    color: str = Field("blue", max_length=30, description="Ant Design color name")
    is_quality: bool = Field(
        False, description="Whether this type contributes to COQ metrics"
    )
    description: str | None = None


class CostEventTypeCreate(CostEventTypeBase):
    """Schema for creating a new Cost Event Type."""

    cost_event_type_id: UUID | None = Field(
        None,
        description="Root Cost Event Type ID (internal use only for seeding)",
    )
    control_date: datetime | None = Field(
        None, description="Optional control date for creation (valid_time start)"
    )


class CostEventTypeUpdate(BaseModel):
    """Schema for updating an existing Cost Event Type."""

    code: str | None = Field(None, min_length=1, max_length=50)
    name: str | None = Field(None, min_length=1, max_length=255)
    color: str | None = Field(None, max_length=30)
    is_quality: bool | None = None
    description: str | None = None


class CostEventTypeRead(CostEventTypeBase):
    """Schema for reading Cost Event Type data."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    cost_event_type_id: UUID
    created_by: UUID
