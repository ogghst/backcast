"""Cost Element Schedule model and related schemas."""
import uuid
from datetime import date, datetime

from sqlalchemy import Column, Date, DateTime, UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel

from app.models.baseline_log import BaselineLog
from app.models.cost_element import CostElement

# Import for forward references
from app.models.user import User


class CostElementScheduleBase(SQLModel):
    """Base cost element schedule schema with common fields."""

    start_date: date = Field(sa_column=Column(Date, nullable=False))
    end_date: date = Field(sa_column=Column(Date, nullable=False))
    progression_type: str = Field(
        max_length=50
    )  # Will be validated as enum in application logic
    notes: str | None = Field(default=None)


class CostElementScheduleCreate(CostElementScheduleBase):
    """Schema for creating a new cost element schedule."""

    cost_element_id: uuid.UUID
    created_by_id: uuid.UUID


class CostElementScheduleUpdate(SQLModel):
    """Schema for updating a cost element schedule."""

    start_date: date | None = None
    end_date: date | None = None
    progression_type: str | None = Field(default=None, max_length=50)
    notes: str | None = None


class CostElementSchedule(CostElementScheduleBase, table=True):
    """Cost Element Schedule database model."""

    __table_args__ = (
        UniqueConstraint(
            "cost_element_id", name="uq_cost_element_schedule_cost_element"
        ),
    )

    schedule_id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    cost_element_id: uuid.UUID = Field(
        foreign_key="costelement.cost_element_id", nullable=False, unique=True
    )
    baseline_id: uuid.UUID | None = Field(
        default=None, foreign_key="baselinelog.baseline_id", nullable=True
    )
    created_by_id: uuid.UUID = Field(foreign_key="user.id", nullable=False)

    # Relationships
    cost_element: CostElement | None = Relationship()
    baseline_log: BaselineLog | None = Relationship()
    created_by: User | None = Relationship()

    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class CostElementSchedulePublic(CostElementScheduleBase):
    """Public cost element schedule schema for API responses."""

    schedule_id: uuid.UUID
    cost_element_id: uuid.UUID
    baseline_id: uuid.UUID | None = Field(default=None)
    created_by_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
