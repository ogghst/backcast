"""Baseline Log model and related schemas."""
import uuid
from datetime import date, datetime

from sqlalchemy import Column, Date, DateTime
from sqlmodel import Field, Relationship, SQLModel

# Import User for forward reference
from app.models.user import User


class BaselineLogBase(SQLModel):
    """Base baseline log schema with common fields."""

    baseline_type: str = Field(
        max_length=50
    )  # Will be validated as enum in application logic
    baseline_date: date = Field(sa_column=Column(Date, nullable=False))
    description: str | None = Field(default=None)


class BaselineLogCreate(BaselineLogBase):
    """Schema for creating a new baseline log entry."""

    created_by_id: uuid.UUID


class BaselineLogUpdate(SQLModel):
    """Schema for updating a baseline log entry."""

    baseline_type: str | None = Field(default=None, max_length=50)
    baseline_date: date | None = None
    description: str | None = None


class BaselineLog(BaselineLogBase, table=True):
    """Baseline Log database model."""

    baseline_id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_by_id: uuid.UUID = Field(foreign_key="user.id", nullable=False)
    created_by: User | None = Relationship()

    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class BaselineLogPublic(BaselineLogBase):
    """Public baseline log schema for API responses."""

    baseline_id: uuid.UUID
    created_by_id: uuid.UUID
    created_at: datetime
