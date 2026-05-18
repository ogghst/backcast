"""Pydantic schemas for Progress Entry."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.schemas.mixins import TemporalComputedMixin
from app.models.schemas.temporal_validators import TemporalRange
from app.models.schemas.validators import ProgressPercentageDecimal


class ProgressEntryBase(BaseModel):
    """Shared properties for Progress Entry."""

    progress_percentage: ProgressPercentageDecimal = Field(
        ...,
        description="Work completion percentage (0.00 to 100.00)",
    )
    notes: str | None = Field(
        None,
        description="Optional notes about progress (e.g., justification for decrease)",
    )


class ProgressEntryCreate(ProgressEntryBase):
    """Properties required for creating a Progress Entry."""

    progress_entry_id: UUID | None = Field(
        None,
        description="Root Progress Entry ID (internal use only for seeding)",
        exclude=True,  # Exclude from OpenAPI docs
    )
    cost_element_id: UUID = Field(
        ..., description="ID of the cost element to track progress for"
    )
    control_date: datetime | None = Field(
        None,
        description="Control date for the progress entry (when the progress was measured). Defaults to current time if not provided.",
    )


class ProgressEntryUpdate(BaseModel):
    """Properties for updating a Progress Entry."""

    progress_percentage: ProgressPercentageDecimal | None = Field(
        None,
        description="Work completion percentage (0.00 to 100.00)",
    )
    notes: str | None = Field(
        None,
        description="Optional notes about progress (e.g., justification for decrease)",
    )
    control_date: datetime | None = Field(
        None,
        description="Control date for the progress entry update",
    )


class ProgressEntryRead(ProgressEntryBase, TemporalComputedMixin):
    """Properties returned to client."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    progress_entry_id: UUID
    cost_element_id: UUID
    created_by: UUID
    valid_time: TemporalRange
    transaction_time: TemporalRange
    deleted_at: datetime | None = None
