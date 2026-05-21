"""Pydantic schemas for Project entity."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import ProjectStatus
from app.models.schemas.mixins import TemporalComputedMixin
from app.models.schemas.temporal_validators import TemporalRange
from app.models.schemas.validators import NotEmptyString


class ProjectBase(BaseModel):
    """Base schema for Project with common fields."""

    name: str = Field(..., max_length=200, description="Project name")
    code: str = Field(..., max_length=50, description="Unique project code")
    contract_value: Decimal | None = Field(None, ge=0, description="Contract value")
    currency: str = Field("EUR", min_length=3, max_length=3, description="ISO 4217 currency code")
    status: ProjectStatus = Field(ProjectStatus.DRAFT, description="Project status")
    start_date: datetime | None = Field(None, description="Project start date")
    end_date: datetime | None = Field(None, description="Project end date")
    description: str | None = Field(None, max_length=5000, description="Description")


class ProjectCreate(ProjectBase):
    """Schema for creating a new project."""

    project_id: UUID | None = Field(
        None,
        description="Root Project ID (internal use only for seeding)",
        exclude=True,  # Exclude from OpenAPI docs
    )
    branch: str = Field(
        "main",
        description="Branch name for creation (defaults to main if not specified)",
    )
    control_date: datetime | None = Field(
        None, description="Optional control date for creation (valid_time start)"
    )


class ProjectUpdate(BaseModel):
    """Schema for updating an existing project."""

    name: NotEmptyString = Field(None, max_length=200)
    contract_value: Decimal | None = Field(None, ge=0)
    currency: str | None = Field(None, min_length=3, max_length=3, description="ISO 4217 currency code")
    status: ProjectStatus | None = Field(None, description="Project status")
    start_date: datetime | None = None
    end_date: datetime | None = None
    description: str | None = Field(None, max_length=5000)
    branch: str | None = Field(
        None, description="Branch name for update (defaults to current branch)"
    )
    control_date: datetime | None = Field(
        None, description="Optional control date for update (valid_time start)"
    )


class ProjectRead(ProjectBase, TemporalComputedMixin):
    """Schema for reading project data."""

    id: UUID
    project_id: UUID
    branch: str
    budget: Decimal = Field(
        Decimal("0"),
        description="Computed project budget (sum of all cost element budgets)",
    )
    created_at: datetime | None = None
    created_by: UUID | None = None
    created_by_name: str | None = None
    deleted_by: UUID | None = None
    valid_time: TemporalRange = None
    transaction_time: TemporalRange = None

    model_config = ConfigDict(from_attributes=True)


# Alias for backward compatibility
ProjectPublic = ProjectRead
