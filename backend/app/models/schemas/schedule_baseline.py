"""Pydantic schemas for Schedule Baseline."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ProgressionType:
    """Progression type constants for schedule baselines."""

    LINEAR = "LINEAR"
    GAUSSIAN = "GAUSSIAN"
    LOGARITHMIC = "LOGARITHMIC"


PROGRESSION_TYPE_CHOICES = [
    ProgressionType.LINEAR,
    ProgressionType.GAUSSIAN,
    ProgressionType.LOGARITHMIC,
]


class ScheduleBaselineBase(BaseModel):
    """Shared properties for Schedule Baseline."""

    name: str = Field(..., min_length=1, max_length=255, description="Baseline name")
    start_date: datetime = Field(..., description="Schedule start date")
    end_date: datetime = Field(..., description="Schedule end date")
    progression_type: str = Field(
        ProgressionType.LINEAR,
        description="Type of progression curve (LINEAR, GAUSSIAN, LOGARITHMIC)",
    )
    description: str | None = Field(
        None, description="Optional description of the baseline"
    )


class ScheduleBaselineCreate(ScheduleBaselineBase):
    """Properties required for creating a Schedule Baseline.

    Note: cost_element_id is obtained from the URL path when creating
    a baseline for a specific cost element, not from the request body.
    """

    schedule_baseline_id: UUID | None = Field(
        None,
        description="Root Schedule Baseline ID (internal use only for seeding)",
        exclude=True,  # Exclude from OpenAPI docs
    )


class ScheduleBaselineUpdate(BaseModel):
    """Properties that can be updated on a Schedule Baseline."""

    name: str | None = Field(None, min_length=1, max_length=255)
    start_date: datetime | None = None
    end_date: datetime | None = None
    progression_type: str | None = None
    description: str | None = None


class ScheduleBaselineRead(ScheduleBaselineBase):
    """Properties returned to client."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    schedule_baseline_id: UUID
    cost_element_id: UUID
    created_by: UUID
    branch: str
    cost_element_code: str | None = None
    cost_element_name: str | None = None
