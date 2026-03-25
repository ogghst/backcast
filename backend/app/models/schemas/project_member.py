"""Pydantic schemas for ProjectMember entity."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import ProjectRole


class ProjectMemberBase(BaseModel):
    """Base schema for ProjectMember with common fields."""

    role: ProjectRole = Field(..., description="Project role for the user")


class ProjectMemberCreate(ProjectMemberBase):
    """Schema for creating a new project member assignment."""

    user_id: UUID = Field(..., description="UUID of the user to assign")
    project_id: UUID = Field(..., description="UUID of the project")
    assigned_by: UUID | None = Field(None, description="UUID of the user assigning the role")


class ProjectMemberUpdate(BaseModel):
    """Schema for updating a project member's role."""

    role: ProjectRole = Field(..., description="New project role for the user")
    assigned_by: UUID = Field(..., description="UUID of the user updating the role")


class ProjectMemberRead(ProjectMemberBase):
    """Schema for reading project member data."""

    id: UUID
    user_id: UUID
    project_id: UUID
    role: ProjectRole
    assigned_at: datetime
    assigned_by: UUID | None = None
    created_at: datetime
    updated_at: datetime

    # Optional populated fields
    user_name: str | None = Field(None, description="Full name of the assigned user")
    user_email: str | None = Field(None, description="Email of the assigned user")
    assigned_by_name: str | None = Field(
        None, description="Full name of the user who assigned the role"
    )
    project_name: str | None = Field(None, description="Name of the project")

    model_config = ConfigDict(from_attributes=True)


class ProjectMemberResponse(BaseModel):
    """Schema for project member API responses."""

    id: UUID
    user_id: UUID
    project_id: UUID
    role: ProjectRole
    assigned_at: datetime
    assigned_by: UUID | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Alias for backward compatibility
ProjectMemberPublic = ProjectMemberRead
