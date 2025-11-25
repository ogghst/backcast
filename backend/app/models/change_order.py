"""Change Order model and related schemas."""

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import DECIMAL, Column, Date, DateTime
from sqlmodel import Field, Relationship, SQLModel

from app.models.project import Project

# Import for forward references
from app.models.user import User
from app.models.version_status_mixin import VersionStatusMixin
from app.models.wbe import WBE


class ChangeOrderBase(SQLModel):
    """Base change order schema with common fields."""

    change_order_number: str = Field(unique=True, index=True, max_length=50)
    title: str = Field(max_length=200)
    description: str = Field()
    requesting_party: str = Field(max_length=100)
    justification: str | None = Field(default=None)
    effective_date: date = Field(sa_column=Column(Date, nullable=False))
    cost_impact: Decimal | None = Field(
        default=None, sa_column=Column(DECIMAL(15, 2), nullable=True)
    )
    revenue_impact: Decimal | None = Field(
        default=None, sa_column=Column(DECIMAL(15, 2), nullable=True)
    )
    workflow_status: str = Field(
        max_length=50
    )  # Will be validated as enum in application logic (renamed from 'status' to avoid conflict with versioning status)


class ChangeOrderCreate(ChangeOrderBase):
    """Schema for creating a new change order."""

    project_id: uuid.UUID
    created_by_id: uuid.UUID
    change_order_number: str | None = Field(
        default=None, max_length=50
    )  # Optional - will be auto-generated if not provided


class ChangeOrderUpdate(SQLModel):
    """Schema for updating a change order."""

    change_order_number: str | None = Field(default=None, max_length=50)
    title: str | None = Field(default=None, max_length=200)
    description: str | None = None
    requesting_party: str | None = Field(default=None, max_length=100)
    justification: str | None = None
    effective_date: date | None = None
    cost_impact: Decimal | None = Field(
        default=None, sa_column=Column(DECIMAL(15, 2), nullable=True)
    )
    revenue_impact: Decimal | None = Field(
        default=None, sa_column=Column(DECIMAL(15, 2), nullable=True)
    )
    workflow_status: str | None = Field(default=None, max_length=50)


class ChangeOrder(ChangeOrderBase, VersionStatusMixin, table=True):
    """Change Order database model."""

    change_order_id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    project_id: uuid.UUID = Field(foreign_key="project.project_id", nullable=False)
    wbe_id: uuid.UUID | None = Field(
        default=None, foreign_key="wbe.wbe_id", nullable=True
    )
    branch: str | None = Field(
        default=None, max_length=50, nullable=True
    )  # Branch name associated with this change order (e.g., 'co-001')
    created_by_id: uuid.UUID = Field(foreign_key="user.id", nullable=False)
    approved_by_id: uuid.UUID | None = Field(
        default=None, foreign_key="user.id", nullable=True
    )
    approved_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    implemented_by_id: uuid.UUID | None = Field(
        default=None, foreign_key="user.id", nullable=True
    )
    implemented_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )

    # Relationships
    project: Project | None = Relationship()
    wbe: WBE | None = Relationship()
    created_by: User | None = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[ChangeOrder.created_by_id]"}
    )
    approved_by: User | None = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[ChangeOrder.approved_by_id]"}
    )
    implemented_by: User | None = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[ChangeOrder.implemented_by_id]"}
    )

    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class ChangeOrderPublic(ChangeOrderBase):
    """Public change order schema for API responses."""

    change_order_id: uuid.UUID
    project_id: uuid.UUID
    wbe_id: uuid.UUID | None = Field(default=None)
    branch: str | None = Field(default=None)
    created_by_id: uuid.UUID
    approved_by_id: uuid.UUID | None = Field(default=None)
    approved_at: datetime | None = Field(default=None)
    implemented_by_id: uuid.UUID | None = Field(default=None)
    implemented_at: datetime | None = Field(default=None)
    created_at: datetime
    entity_id: uuid.UUID
    status: str  # Versioning status (from VersionStatusMixin)
    version: int
