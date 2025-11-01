"""Quality Event model and related schemas."""
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import DECIMAL, Column, Date, DateTime
from sqlmodel import Field, Relationship, SQLModel

from app.models.cost_element import CostElement
from app.models.project import Project

# Import for forward references
from app.models.user import User
from app.models.wbe import WBE


class QualityEventBase(SQLModel):
    """Base quality event schema with common fields."""

    event_date: date = Field(sa_column=Column(Date, nullable=False))
    title: str = Field(max_length=200)
    description: str = Field()
    root_cause: str = Field(
        max_length=100
    )  # Will be validated as enum in application logic
    responsible_department: str = Field(max_length=100)
    estimated_cost_impact: Decimal | None = Field(
        default=None, sa_column=Column(DECIMAL(15, 2), nullable=True)
    )
    actual_cost_impact: Decimal | None = Field(
        default=None, sa_column=Column(DECIMAL(15, 2), nullable=True)
    )
    corrective_actions: str | None = Field(default=None)
    preventive_measures: str | None = Field(default=None)
    status: str = Field(
        max_length=100
    )  # Will be validated as enum in application logic
    resolved_date: date | None = Field(
        default=None, sa_column=Column(Date, nullable=True)
    )


class QualityEventCreate(QualityEventBase):
    """Schema for creating a new quality event."""

    project_id: uuid.UUID
    created_by_id: uuid.UUID


class QualityEventUpdate(SQLModel):
    """Schema for updating a quality event."""

    event_date: date | None = None
    title: str | None = Field(default=None, max_length=200)
    description: str | None = None
    root_cause: str | None = Field(default=None, max_length=100)
    responsible_department: str | None = Field(default=None, max_length=100)
    estimated_cost_impact: Decimal | None = Field(
        default=None, sa_column=Column(DECIMAL(15, 2), nullable=True)
    )
    actual_cost_impact: Decimal | None = Field(
        default=None, sa_column=Column(DECIMAL(15, 2), nullable=True)
    )
    corrective_actions: str | None = None
    preventive_measures: str | None = None
    status: str | None = Field(default=None, max_length=100)
    resolved_date: date | None = None


class QualityEvent(QualityEventBase, table=True):
    """Quality Event database model."""

    quality_event_id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    project_id: uuid.UUID = Field(foreign_key="project.project_id", nullable=False)
    wbe_id: uuid.UUID | None = Field(
        default=None, foreign_key="wbe.wbe_id", nullable=True
    )
    cost_element_id: uuid.UUID | None = Field(
        default=None, foreign_key="costelement.cost_element_id", nullable=True
    )
    created_by_id: uuid.UUID = Field(foreign_key="user.id", nullable=False)

    # Relationships
    project: Project | None = Relationship()
    wbe: WBE | None = Relationship()
    cost_element: CostElement | None = Relationship()
    created_by: User | None = Relationship()

    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class QualityEventPublic(QualityEventBase):
    """Public quality event schema for API responses."""

    quality_event_id: uuid.UUID
    project_id: uuid.UUID
    wbe_id: uuid.UUID | None = Field(default=None)
    cost_element_id: uuid.UUID | None = Field(default=None)
    created_by_id: uuid.UUID
    created_at: datetime
