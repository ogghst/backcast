"""Cost Registration model and related schemas."""
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import DECIMAL, Column, Date, DateTime
from sqlmodel import Field, Relationship, SQLModel

from app.models.cost_element import CostElement

# Import for forward references
from app.models.user import User


class CostRegistrationBase(SQLModel):
    """Base cost registration schema with common fields."""

    registration_date: date = Field(sa_column=Column(Date, nullable=False))
    amount: Decimal = Field(
        default=Decimal("0.00"), sa_column=Column(DECIMAL(15, 2), nullable=False)
    )
    cost_category: str = Field(
        max_length=50
    )  # Will be validated as enum in application logic
    invoice_number: str | None = Field(default=None, max_length=100)
    description: str = Field()
    is_quality_cost: bool = Field(default=False)


class CostRegistrationCreate(CostRegistrationBase):
    """Schema for creating a new cost registration."""

    cost_element_id: uuid.UUID
    created_by_id: uuid.UUID


class CostRegistrationUpdate(SQLModel):
    """Schema for updating a cost registration."""

    registration_date: date | None = None
    amount: Decimal | None = Field(
        default=None, sa_column=Column(DECIMAL(15, 2), nullable=True)
    )
    cost_category: str | None = Field(default=None, max_length=50)
    invoice_number: str | None = Field(default=None, max_length=100)
    description: str | None = None
    is_quality_cost: bool | None = None


class CostRegistration(CostRegistrationBase, table=True):
    """Cost Registration database model."""

    cost_registration_id: uuid.UUID = Field(
        default_factory=uuid.uuid4, primary_key=True
    )
    cost_element_id: uuid.UUID = Field(
        foreign_key="costelement.cost_element_id", nullable=False
    )
    created_by_id: uuid.UUID = Field(foreign_key="user.id", nullable=False)
    # quality_event_id will be added after QualityEvent model is implemented
    # quality_event_id: uuid.UUID | None = Field(
    #     default=None,
    #     foreign_key="qualityevent.quality_event_id",
    #     nullable=True
    # )

    # Relationships
    cost_element: CostElement | None = Relationship()
    created_by: User | None = Relationship()

    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    last_modified_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class CostRegistrationPublic(CostRegistrationBase):
    """Public cost registration schema for API responses."""

    cost_registration_id: uuid.UUID
    cost_element_id: uuid.UUID
    created_by_id: uuid.UUID
    created_at: datetime
    last_modified_at: datetime
