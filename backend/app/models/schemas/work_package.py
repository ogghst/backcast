"""Pydantic schemas for Work Package entity (ANSI-748 PMI budget holder)."""

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from app.models.schemas.mixins import EntityMetadataMixin, TemporalComputedMixin
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
    custom_fields: dict[str, Any] | None = Field(
        None, description="Admin-template custom field values"
    )
    custom_entity_template_root_id: UUID | None = Field(
        None, description="Bound CustomEntityTemplate root ID"
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
    # Schedule baseline params (a baseline is always created per WP)
    schedule_start_date: datetime | None = Field(
        None,
        description="Start date for the WP's schedule baseline (defaults to control_date if omitted)",
    )
    schedule_end_date: datetime | None = Field(
        None,
        description="End date for the WP's schedule baseline (defaults to start + 90 days if omitted)",
    )
    schedule_progression_type: str | None = Field(
        None,
        description="Progression type for the schedule baseline (LINEAR, GAUSSIAN, LOGARITHMIC)",
    )
    # Forecast params (a forecast is always created per WP)
    eac_amount: Decimal | None = Field(
        None,
        description="EAC amount for the WP's forecast (defaults to budget_amount if omitted)",
    )
    basis_of_estimate: str | None = Field(
        None,
        description="Basis of estimate for the WP's forecast (defaults to 'Initial forecast')",
    )
    custom_field_definitions_snapshot: dict[str, Any] | None = Field(
        None,
        description="Server-captured field-definition snapshot (read-only)",
        exclude=True,
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
    custom_fields: dict[str, Any] | None = Field(
        None, description="Admin-template custom field values"
    )
    custom_entity_template_root_id: UUID | None = Field(
        None, description="Bound CustomEntityTemplate root ID"
    )


class WorkPackageRead(WorkPackageBase, TemporalComputedMixin, EntityMetadataMixin):
    """Schema for reading Work Package data."""

    id: UUID
    work_package_id: UUID
    control_account_id: UUID
    schedule_baseline_id: UUID | None = None
    forecast_id: UUID | None = None
    branch: str
    created_by: UUID
    deleted_by: UUID | None = None
    valid_time: TemporalRange = None
    transaction_time: TemporalRange = None
    # Denormalized names for convenience
    control_account_name: str | None = None
    custom_field_definitions_snapshot: dict[str, Any] | None = Field(
        None,
        description="Immutable field-definition snapshot captured at create",
    )

    model_config = ConfigDict(from_attributes=True)


# Alias for backward compatibility
WorkPackagePublic = WorkPackageRead
