"""Budget Allocation model and related schemas."""
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import DECIMAL, Column, Date, DateTime
from sqlmodel import Field, Relationship, SQLModel

from app.models.cost_element import CostElement

# Import for forward references
from app.models.user import User


class BudgetAllocationBase(SQLModel):
    """Base budget allocation schema with common fields."""

    allocation_date: date = Field(sa_column=Column(Date, nullable=False))
    budget_amount: Decimal = Field(
        default=Decimal("0.00"), sa_column=Column(DECIMAL(15, 2), nullable=False)
    )
    revenue_amount: Decimal | None = Field(
        default=None, sa_column=Column(DECIMAL(15, 2), nullable=True)
    )
    allocation_type: str = Field(
        max_length=50
    )  # Will be validated as enum in application logic
    description: str | None = Field(default=None)


class BudgetAllocationCreate(BudgetAllocationBase):
    """Schema for creating a new budget allocation."""

    cost_element_id: uuid.UUID
    created_by_id: uuid.UUID


class BudgetAllocationUpdate(SQLModel):
    """Schema for updating a budget allocation."""

    allocation_date: date | None = None
    budget_amount: Decimal | None = Field(
        default=None, sa_column=Column(DECIMAL(15, 2), nullable=True)
    )
    revenue_amount: Decimal | None = Field(
        default=None, sa_column=Column(DECIMAL(15, 2), nullable=True)
    )
    allocation_type: str | None = Field(default=None, max_length=50)
    description: str | None = None


class BudgetAllocation(BudgetAllocationBase, table=True):
    """Budget Allocation database model."""

    budget_allocation_id: uuid.UUID = Field(
        default_factory=uuid.uuid4, primary_key=True
    )
    cost_element_id: uuid.UUID = Field(
        foreign_key="costelement.cost_element_id", nullable=False
    )
    created_by_id: uuid.UUID = Field(foreign_key="user.id", nullable=False)
    # related_change_order_id will be added after ChangeOrder model is implemented
    # related_change_order_id: uuid.UUID | None = Field(
    #     default=None,
    #     foreign_key="changeorder.change_order_id",
    #     nullable=True
    # )

    # Relationships
    cost_element: CostElement | None = Relationship()
    created_by: User | None = Relationship()

    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class BudgetAllocationPublic(BudgetAllocationBase):
    """Public budget allocation schema for API responses."""

    budget_allocation_id: uuid.UUID
    cost_element_id: uuid.UUID
    created_by_id: uuid.UUID
    created_at: datetime
