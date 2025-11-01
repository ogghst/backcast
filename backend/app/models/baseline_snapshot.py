"""Baseline Snapshot model and related schemas."""
import uuid
from datetime import date, datetime

from sqlalchemy import Column, Date, DateTime
from sqlmodel import Field, Relationship, SQLModel

from app.models.project import Project

# Import for forward references
from app.models.user import User


class BaselineSnapshotBase(SQLModel):
    """Base baseline snapshot schema with common fields."""

    baseline_date: date = Field(sa_column=Column(Date, nullable=False))
    milestone_type: str = Field(
        max_length=100
    )  # Will be validated as enum in application logic
    description: str | None = Field(default=None)
    department: str | None = Field(default=None, max_length=100)
    is_pmb: bool = Field(default=False)


class BaselineSnapshotCreate(BaselineSnapshotBase):
    """Schema for creating a new baseline snapshot."""

    project_id: uuid.UUID
    created_by_id: uuid.UUID


class BaselineSnapshotUpdate(SQLModel):
    """Schema for updating a baseline snapshot."""

    baseline_date: date | None = None
    milestone_type: str | None = Field(default=None, max_length=100)
    description: str | None = None
    department: str | None = Field(default=None, max_length=100)
    is_pmb: bool | None = None


class BaselineSnapshot(BaselineSnapshotBase, table=True):
    """Baseline Snapshot database model."""

    snapshot_id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    project_id: uuid.UUID = Field(foreign_key="project.project_id", nullable=False)
    created_by_id: uuid.UUID = Field(foreign_key="user.id", nullable=False)

    # Relationships
    project: Project | None = Relationship()
    created_by: User | None = Relationship()

    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class BaselineSnapshotPublic(BaselineSnapshotBase):
    """Public baseline snapshot schema for API responses."""

    snapshot_id: uuid.UUID
    project_id: uuid.UUID
    created_by_id: uuid.UUID
    created_at: datetime
