"""Work Breakdown Element (WBE) model and related schemas."""

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import ConfigDict
from sqlalchemy import DECIMAL, Column, Date, DateTime
from sqlmodel import Field, Relationship, SQLModel

from app.models.branch_version_mixin import BranchVersionMixin

# Import Project for forward reference
from app.models.project import Project


class WBEBase(SQLModel):
    model_config = ConfigDict(populate_by_name=True)
    """Base WBE schema with common fields."""

    machine_type: str = Field(max_length=100)
    serial_number: str | None = Field(default=None, max_length=100)
    contracted_delivery_date: date | None = Field(
        default=None, sa_column=Column(Date, nullable=True)
    )
    revenue_allocation: Decimal = Field(
        default=Decimal("0.00"), sa_column=Column(DECIMAL(15, 2), nullable=False)
    )
    business_status: str = Field(
        default="designing",
        max_length=50,
    )
    notes: str | None = Field(default=None)


class WBECreate(WBEBase):
    """Schema for creating a new WBE."""

    project_id: uuid.UUID


class WBEUpdate(SQLModel):
    """Schema for updating a WBE."""

    machine_type: str | None = Field(default=None, max_length=100)
    serial_number: str | None = Field(default=None, max_length=100)
    contracted_delivery_date: date | None = None
    revenue_allocation: Decimal | None = Field(
        default=None, sa_column=Column(DECIMAL(15, 2), nullable=True)
    )
    business_status: str | None = Field(default=None, max_length=50)
    notes: str | None = None


class WBE(WBEBase, BranchVersionMixin, table=True):
    """WBE database model."""

    wbe_id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    project_id: uuid.UUID = Field(foreign_key="project.project_id", nullable=False)
    project: Project | None = Relationship()

    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class WBEPublic(WBEBase):
    """Public WBE schema for API responses."""

    entity_id: uuid.UUID
    wbe_id: uuid.UUID
    project_id: uuid.UUID
    status: str  # Versioning status (from BranchVersionMixin)
    version: int
    branch: str


class WBEsPublic(SQLModel):
    """Schema for list of WBEs."""

    data: list[WBEPublic]
    count: int
