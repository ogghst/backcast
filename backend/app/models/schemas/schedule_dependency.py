"""Pydantic schemas for Schedule Dependency."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DependencyType:
    """Dependency type constants for schedule dependencies."""

    FS = "FS"
    SS = "SS"
    FF = "FF"
    SF = "SF"


DEPENDENCY_TYPE_CHOICES = [
    DependencyType.FS,
    DependencyType.SS,
    DependencyType.FF,
    DependencyType.SF,
]


class ScheduleDependencyCreate(BaseModel):
    """Schema for creating a new Schedule Dependency."""

    predecessor_id: UUID = Field(..., description="Schedule Baseline ID of predecessor")
    successor_id: UUID = Field(..., description="Schedule Baseline ID of successor")
    dependency_type: str = Field(
        DependencyType.FS, description="Dependency type (FS, SS, FF, SF)"
    )
    lag_days: int = Field(
        0, description="Lag in days between predecessor and successor"
    )
    project_id: UUID = Field(..., description="Project root ID")
    branch: str = Field(
        "main",
        description="Branch name (defaults to main)",
    )


class ScheduleDependencyUpdate(BaseModel):
    """Schema for updating an existing Schedule Dependency."""

    dependency_type: str | None = Field(
        None, description="Dependency type (FS, SS, FF, SF)"
    )
    lag_days: int | None = Field(
        None, description="Lag in days between predecessor and successor"
    )


class ScheduleDependencyRead(BaseModel):
    """Schema for reading Schedule Dependency data."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    schedule_dependency_id: UUID
    predecessor_id: UUID
    successor_id: UUID
    dependency_type: str
    lag_days: int
    branch: str
    project_id: UUID
    created_at: datetime
    updated_at: datetime
