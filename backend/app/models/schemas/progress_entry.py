"""Pydantic schemas for Progress Entry."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProgressEntryBase(BaseModel):
    """Shared properties for Progress Entry."""

    progress_percentage: Decimal = Field(
        ...,
        ge=Decimal("0.00"),
        le=Decimal("100.00"),
        decimal_places=2,
        description="Work completion percentage (0.00 to 100.00)",
    )
    reported_date: datetime = Field(
        ...,
        description="When progress was measured (business date)",
    )
    notes: str | None = Field(
        None,
        description="Optional notes about progress (e.g., justification for decrease)",
    )

    @field_validator("progress_percentage")
    @classmethod
    def validate_progress_percentage(cls, v: Decimal) -> Decimal:
        """Validate that progress_percentage is within valid range."""
        if v < Decimal("0.00") or v > Decimal("100.00"):
            raise ValueError("Progress percentage must be between 0 and 100")
        return v


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
    reported_by_user_id: UUID = Field(
        ..., description="ID of the user reporting the progress"
    )


class ProgressEntryUpdate(BaseModel):
    """Properties that can be updated on a Progress Entry."""

    progress_percentage: Decimal | None = Field(
        None,
        ge=Decimal("0.00"),
        le=Decimal("100.00"),
        decimal_places=2,
    )
    reported_date: datetime | None = None
    notes: str | None = None


class ProgressEntryRead(ProgressEntryBase):
    """Properties returned to client."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    progress_entry_id: UUID
    cost_element_id: UUID
    reported_by_user_id: UUID
    created_by: UUID
