"""Pydantic schemas for Progress Entry."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

from app.core.temporal import format_temporal_range_for_api


class ProgressEntryBase(BaseModel):
    """Shared properties for Progress Entry."""

    progress_percentage: Decimal = Field(
        ...,
        ge=Decimal("0.00"),
        le=Decimal("100.00"),
        decimal_places=2,
        description="Work completion percentage (0.00 to 100.00)",
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
    control_date: datetime | None = Field(
        None,
        description="Control date for the progress entry (when the progress was measured). Defaults to current time if not provided.",
    )


class ProgressEntryRead(ProgressEntryBase):
    """Properties returned to client."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    progress_entry_id: UUID
    cost_element_id: UUID
    created_by: UUID
    valid_time: str  # TSTZRANGE serialized as string
    transaction_time: str  # TSTZRANGE serialized as string
    deleted_at: datetime | None = None

    @field_validator("valid_time", "transaction_time", mode="before")
    @classmethod
    def convert_range_to_str(cls, v: object) -> str | None:
        if v and not isinstance(v, str):
            return str(v)
        return v  # type: ignore

    @computed_field  # type: ignore[prop-decorator]
    @property
    def valid_time_formatted(self) -> dict[str, str | bool | None]:
        return format_temporal_range_for_api(self.valid_time)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def transaction_time_formatted(self) -> dict[str, str | bool | None]:
        return format_temporal_range_for_api(self.transaction_time)
