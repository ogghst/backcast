"""Pydantic schemas for DashboardLayout entity."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DashboardLayoutCreate(BaseModel):
    """Schema for creating a new dashboard layout."""

    name: str = Field(..., description="Layout name", max_length=255)
    description: str | None = Field(None, description="Layout description")
    project_id: UUID | None = Field(None, description="Project scope (null = global)")
    is_template: bool = Field(False, description="Whether this layout is a reusable template")
    is_default: bool = Field(False, description="Whether this is the user's default layout for this scope")
    widgets: list[dict[str, object]] = Field(default_factory=list, description="Widget instances array")


class DashboardLayoutUpdate(BaseModel):
    """Schema for updating a dashboard layout. All fields optional."""

    name: str | None = Field(None, description="Layout name", max_length=255)
    description: str | None = Field(None, description="Layout description")
    is_template: bool | None = Field(None, description="Whether this layout is a reusable template")
    is_default: bool | None = Field(None, description="Whether this is the user's default layout")
    widgets: list[dict[str, object]] | None = Field(None, description="Widget instances array")


class DashboardLayoutRead(BaseModel):
    """Schema for reading dashboard layout data."""

    id: UUID
    name: str
    description: str | None
    user_id: UUID
    project_id: UUID | None
    is_template: bool
    is_default: bool
    widgets: list[dict[str, object]]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CloneTemplateRequest(BaseModel):
    """Schema for cloning a template layout."""

    project_id: UUID | None = Field(None, description="Project scope for the cloned layout")
