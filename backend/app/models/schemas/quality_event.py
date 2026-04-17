"""Pydantic schemas for Quality Event."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, computed_field


class QualityEventBase(BaseModel):
    """Shared properties for Quality Event."""

    description: str = Field(..., description="Description of the quality issue")
    cost_impact: Decimal = Field(
        ..., gt=0, decimal_places=2, description="Financial impact (must be positive)"
    )
    event_date: datetime | None = Field(
        None,
        description="When the quality event occurred (defaults to control date if not provided)",
    )
    event_type: str | None = Field(
        None,
        max_length=50,
        description="Category of quality event (e.g., defect, rework, scrap, warranty, other)",
    )
    severity: str | None = Field(
        None,
        max_length=20,
        description="Impact severity level (e.g., low, medium, high, critical)",
    )
    root_cause: str | None = Field(
        None, description="Optional root cause analysis"
    )
    resolution_notes: str | None = Field(
        None, description="Optional resolution description"
    )


class QualityEventCreate(QualityEventBase):
    """Properties required for creating a Quality Event."""

    quality_event_id: UUID | None = Field(
        None,
        description="Root Quality Event ID (internal use only for seeding)",
        exclude=True,  # Exclude from OpenAPI docs
    )
    cost_element_id: UUID = Field(
        ..., description="ID of the cost element to associate the quality event with"
    )
    control_date: datetime | None = Field(
        None, description="Optional control date for creation (valid_time start)"
    )


class QualityEventUpdate(BaseModel):
    """Properties that can be updated on a Quality Event."""

    description: str | None = None
    cost_impact: Decimal | None = Field(None, gt=0, decimal_places=2)
    event_date: datetime | None = None
    event_type: str | None = Field(None, max_length=50)
    severity: str | None = Field(None, max_length=20)
    root_cause: str | None = None
    resolution_notes: str | None = None
    control_date: datetime | None = Field(
        None, description="Optional control date for update (valid_time start)"
    )


class QualityEventRead(QualityEventBase):
    """Properties returned to client."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    quality_event_id: UUID
    cost_element_id: UUID
    created_by: UUID

    @computed_field  # type: ignore[prop-decorator]
    @property
    def event_date_formatted(self) -> dict[str, str | None]:
        """Display-ready event date data.

        Returns pre-formatted date information including:
        - ISO timestamp for machine processing
        - Formatted display string for UI

        This allows the frontend to display dates without additional formatting.

        Example:
            {
                "iso": "2026-01-15T10:00:00+00:00",
                "formatted": "January 15, 2026"
            }
        """
        if not self.event_date:
            return {"iso": None, "formatted": "Unknown"}

        return {
            "iso": self.event_date.isoformat(),
            "formatted": self.event_date.strftime("%B %d, %Y"),
        }
