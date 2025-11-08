"""Earned Value Entry model and related schemas."""
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import DECIMAL, Column, Date, DateTime
from sqlmodel import Field, Relationship, SQLModel

from app.models.baseline_log import BaselineLog
from app.models.cost_element import CostElement

# Import for forward references
from app.models.user import User


class EarnedValueEntryBase(SQLModel):
    """Base earned value entry schema with common fields."""

    completion_date: date = Field(sa_column=Column(Date, nullable=False))
    percent_complete: Decimal = Field(
        default=Decimal("0.00"), sa_column=Column(DECIMAL(5, 2), nullable=False)
    )
    earned_value: Decimal | None = Field(
        default=None, sa_column=Column(DECIMAL(15, 2), nullable=True)
    )
    deliverables: str | None = Field(default=None)
    description: str | None = Field(default=None)


class EarnedValueEntryCreate(EarnedValueEntryBase):
    """Schema for creating a new earned value entry.

    Note: created_by_id is set automatically by the API from current_user.
    """

    cost_element_id: uuid.UUID


class EarnedValueEntryUpdate(SQLModel):
    """Schema for updating an earned value entry."""

    completion_date: date | None = None
    percent_complete: Decimal | None = Field(
        default=None, sa_column=Column(DECIMAL(5, 2), nullable=True)
    )
    earned_value: Decimal | None = Field(
        default=None, sa_column=Column(DECIMAL(15, 2), nullable=True)
    )
    deliverables: str | None = None
    description: str | None = None


class EarnedValueEntry(EarnedValueEntryBase, table=True):
    """Earned Value Entry database model."""

    earned_value_id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    cost_element_id: uuid.UUID = Field(
        foreign_key="costelement.cost_element_id", nullable=False
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
    last_modified_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class EarnedValueEntryPublic(EarnedValueEntryBase):
    """Public earned value entry schema for API responses."""

    earned_value_id: uuid.UUID
    cost_element_id: uuid.UUID
    baseline_id: uuid.UUID | None = Field(default=None)
    created_by_id: uuid.UUID
    created_at: datetime
    last_modified_at: datetime


class EarnedValueEntriesPublic(SQLModel):
    """Public earned value entries list schema."""

    data: list[EarnedValueEntryPublic]
    count: int
