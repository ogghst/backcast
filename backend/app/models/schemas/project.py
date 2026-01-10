"""Pydantic schemas for Project entity."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProjectBase(BaseModel):
    """Base schema for Project with common fields."""

    name: str = Field(..., max_length=200, description="Project name")
    code: str = Field(..., max_length=50, description="Unique project code")
    budget: Decimal = Field(..., ge=0, description="Project budget")
    contract_value: Decimal | None = Field(None, ge=0, description="Contract value")
    status: str = Field("Draft", max_length=50, description="Project status")
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
    control_date: datetime | None = Field(
        None, description="Optional control date for creation (valid_time start)"
    )


class ProjectUpdate(BaseModel):
    """Schema for updating an existing project."""

    name: str | None = Field(None, max_length=200)
    budget: Decimal | None = Field(None, ge=0)
    contract_value: Decimal | None = Field(None, ge=0)
    start_date: datetime | None = None
    end_date: datetime | None = None
    description: str | None = Field(None, max_length=5000)
    control_date: datetime | None = Field(
        None, description="Optional control date for update (valid_time start)"
    )


class ProjectRead(ProjectBase):
    """Schema for reading project data."""

    id: UUID
    project_id: UUID
    branch: str
    created_at: datetime | None = None
    created_by: UUID | None = None
    created_by_name: str | None = None
    deleted_by: UUID | None = None
    valid_time: str | None = None
    transaction_time: str | None = None

    @field_validator("valid_time", "transaction_time", mode="before")
    @classmethod
    def convert_range_to_str(cls, v: object) -> str | None:
        if v and not isinstance(v, str):
            return str(v)
        return v  # type: ignore

    model_config = ConfigDict(from_attributes=True)


# Alias for backward compatibility
ProjectPublic = ProjectRead
