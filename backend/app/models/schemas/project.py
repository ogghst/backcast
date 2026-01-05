"""Pydantic schemas for Project entity."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ProjectBase(BaseModel):
    """Base schema for Project with common fields."""

    name: str = Field(..., max_length=200, description="Project name")
    code: str = Field(..., max_length=50, description="Unique project code")
    budget: Decimal = Field(..., ge=0, description="Project budget")
    contract_value: Decimal | None = Field(None, ge=0, description="Contract value")
    start_date: datetime | None = Field(None, description="Project start date")
    end_date: datetime | None = Field(None, description="Project end date")
    description: str | None = Field(None, max_length=5000, description="Description")


class ProjectCreate(ProjectBase):
    """Schema for creating a new project."""

    pass


class ProjectUpdate(BaseModel):
    """Schema for updating an existing project."""

    name: str | None = Field(None, max_length=200)
    budget: Decimal | None = Field(None, ge=0)
    contract_value: Decimal | None = Field(None, ge=0)
    start_date: datetime | None = None
    end_date: datetime | None = None
    description: str | None = Field(None, max_length=5000)


class ProjectRead(ProjectBase):
    """Schema for reading project data."""

    id: UUID
    project_id: UUID
    branch: str
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


# Alias for backward compatibility
ProjectPublic = ProjectRead
