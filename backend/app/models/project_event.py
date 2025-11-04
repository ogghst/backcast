"""Project Event model and related schemas."""
import uuid
from datetime import date, datetime

from sqlalchemy import Column, Date, DateTime
from sqlmodel import Field, Relationship, SQLModel

from app.models.project import Project

# Import for forward references
from app.models.user import User


class ProjectEventBase(SQLModel):
    """Base project event schema with common fields."""

    event_date: date = Field(sa_column=Column(Date, nullable=False))
    event_type: str = Field(
        max_length=100
    )  # Will be validated as enum in application logic
    department: str = Field(max_length=100)
    description: str = Field()
    notes: str | None = Field(default=None)
    is_deleted: bool = Field(default=False)


class ProjectEventCreate(ProjectEventBase):
    """Schema for creating a new project event."""

    project_id: uuid.UUID
    created_by_id: uuid.UUID


class ProjectEventUpdate(SQLModel):
    """Schema for updating a project event."""

    event_date: date | None = None
    event_type: str | None = Field(default=None, max_length=100)
    department: str | None = Field(default=None, max_length=100)
    description: str | None = None
    notes: str | None = None
    is_deleted: bool | None = None


class ProjectEvent(ProjectEventBase, table=True):
    """Project Event database model."""

    event_id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    project_id: uuid.UUID = Field(foreign_key="project.project_id", nullable=False)
    created_by_id: uuid.UUID = Field(foreign_key="user.id", nullable=False)

    # Relationships
    project: Project | None = Relationship()
    created_by: User | None = Relationship()

    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    last_modified_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class ProjectEventPublic(ProjectEventBase):
    """Public project event schema for API responses."""

    event_id: uuid.UUID
    project_id: uuid.UUID
    created_by_id: uuid.UUID
    created_at: datetime
    last_modified_at: datetime
