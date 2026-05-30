"""Pydantic schemas for Work Package entity (ANSI-748 PMI budget holder)."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from app.models.schemas.mixins import TemporalComputedMixin
from app.models.schemas.temporal_validators import TemporalRange
from app.models.schemas.validators import NotEmptyString


class WorkPackageBase(BaseModel):
    """Base schema for Work Package."""

    name: str = Field(
        ..., min_length=1, max_length=255, description="Work package name"
    )
    code: str = Field(..., min_length=1, max_length=50, description="Work package code")
    budget_amount: Decimal = Field(
        Decimal("0"), ge=0, decimal_places=2, description="Allocated budget"
    )
    description: str | None = None
    status: str = Field(
        default="open",
        pattern="^(open|closed)$",
        description="Work package lifecycle status",
    )


class WorkPackageCreate(WorkPackageBase):
    """Schema for creating a new Work Package."""

    work_package_id: UUID = Field(
        default_factory=uuid4, description="Root Work Package ID"
    )
    control_account_id: UUID = Field(..., description="Parent Control Account root ID")
    branch: str = Field(
        "main",
        description="Branch name for creation (defaults to main if not specified)",
    )
    control_date: datetime | None = Field(
        None, description="Optional control date for creation (valid_time start)"
    )
    # Optional schedule baseline creation params
    schedule_start_date: datetime | None = Field(
        None, description="Optional start date for the auto-created schedule baseline"
    )
    schedule_end_date: datetime | None = Field(
        None, description="Optional end date for the auto-created schedule baseline"
    )
    schedule_progression_type: str | None = Field(
        None,
        description="Optional progression type for the schedule (LINEAR, GAUSSIAN, LOGARITHMIC)",
    )
    # Forecast creation params (auto-created with defaults if not provided)
    eac_amount: Decimal | None = Field(
        None,
        description="Optional EAC amount for auto-created forecast (defaults to budget_amount)",
    )
    basis_of_estimate: str | None = Field(
        None,
        description="Optional basis of estimate for auto-created forecast (defaults to 'Initial forecast')",
    )


class WorkPackageUpdate(BaseModel):
    """Schema for updating an existing Work Package."""

    name: NotEmptyString = Field(None, max_length=255)
    code: NotEmptyString = Field(None, max_length=50)
    budget_amount: Decimal | None = Field(None, ge=0, decimal_places=2)
    description: str | None = None
    status: str | None = Field(None, pattern="^(open|closed)$")
    branch: str | None = Field(
        None, description="Branch name for update (defaults to current branch)"
    )
    control_date: datetime | None = Field(
        None, description="Optional control date for update (valid_time start)"
    )
    # Schedule baseline update params
    schedule_name: str | None = Field(None, max_length=255)
    schedule_start_date: datetime | None = None
    schedule_end_date: datetime | None = None
    schedule_progression_type: str | None = None
    schedule_description: str | None = None
    # Forecast update params
    eac_amount: Decimal | None = Field(None, ge=0, decimal_places=2)
    basis_of_estimate: str | None = Field(None, max_length=5000)


class WorkPackageRead(WorkPackageBase, TemporalComputedMixin):
    """Schema for reading Work Package data."""

    id: UUID
    work_package_id: UUID
    control_account_id: UUID
    schedule_baseline_id: UUID | None = None
    forecast_id: UUID | None = None
    branch: str
    created_by: UUID
    created_by_name: str | None = None
    deleted_by: UUID | None = None
    valid_time: TemporalRange = None
    transaction_time: TemporalRange = None
    # Denormalized names for convenience
    control_account_name: str | None = None

    model_config = ConfigDict(from_attributes=True)


# Alias for backward compatibility
WorkPackagePublic = WorkPackageRead
