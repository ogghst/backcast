"""Cost Element model and related schemas."""

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import ConfigDict
from sqlalchemy import DECIMAL, Column, DateTime
from sqlmodel import Field, Relationship, SQLModel

from app.models.branch_version_mixin import BranchVersionMixin
from app.models.cost_element_type import CostElementType
from app.models.wbe import WBE


class CostElementBase(SQLModel):
    model_config = ConfigDict(populate_by_name=True)
    """Base cost element schema with common fields."""

    department_code: str = Field(max_length=50)
    department_name: str = Field(max_length=100)
    budget_bac: Decimal = Field(
        default=Decimal("0.00"), sa_column=Column(DECIMAL(15, 2), nullable=False)
    )
    revenue_plan: Decimal = Field(
        default=Decimal("0.00"), sa_column=Column(DECIMAL(15, 2), nullable=False)
    )
    business_status: str = Field(
        max_length=50,
        default="planned",
    )
    notes: str | None = Field(default=None)


class CostElementCreate(CostElementBase):
    """Schema for creating a new cost element."""

    wbe_id: uuid.UUID
    cost_element_type_id: uuid.UUID


class CostElementUpdate(SQLModel):
    """Schema for updating a cost element."""

    department_code: str | None = Field(default=None, max_length=50)
    department_name: str | None = Field(default=None, max_length=100)
    budget_bac: Decimal | None = Field(
        default=None, sa_column=Column(DECIMAL(15, 2), nullable=True)
    )
    revenue_plan: Decimal | None = Field(
        default=None, sa_column=Column(DECIMAL(15, 2), nullable=True)
    )
    business_status: str | None = Field(default=None, max_length=50)
    notes: str | None = None


class CostElement(CostElementBase, BranchVersionMixin, table=True):
    """Cost Element database model."""

    cost_element_id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    wbe_id: uuid.UUID = Field(foreign_key="wbe.wbe_id", nullable=False)
    cost_element_type_id: uuid.UUID = Field(
        foreign_key="costelementtype.cost_element_type_id", nullable=False
    )

    # Relationships
    wbe: WBE | None = Relationship()
    cost_element_type: CostElementType | None = Relationship()

    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class CostElementPublic(CostElementBase):
    """Public cost element schema for API responses."""

    entity_id: uuid.UUID
    cost_element_id: uuid.UUID
    wbe_id: uuid.UUID
    cost_element_type_id: uuid.UUID
    status: str  # Versioning status (from BranchVersionMixin)
    version: int
    branch: str


class CostElementsPublic(SQLModel):
    """Schema for list of cost elements."""

    data: list[CostElementPublic]
    count: int
