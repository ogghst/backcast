"""Project model and related schemas."""
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import DECIMAL, Column, Date, DateTime
from sqlmodel import Field, Relationship, SQLModel

# Import User for forward reference
from app.models.user import User


class ProjectBase(SQLModel):
    """Base project schema with common fields."""

    project_name: str = Field(max_length=200)
    customer_name: str = Field(max_length=200)
    contract_value: Decimal = Field(
        default=Decimal("0.00"), sa_column=Column(DECIMAL(15, 2), nullable=False)
    )
    project_code: str | None = Field(default=None, max_length=100)
    pricelist_code: str | None = Field(default=None, max_length=100)
    start_date: date = Field(sa_column=Column(Date, nullable=False))
    planned_completion_date: date = Field(sa_column=Column(Date, nullable=False))
    actual_completion_date: date | None = Field(
        default=None, sa_column=Column(Date, nullable=True)
    )
    status: str = Field(
        max_length=50, default="active"
    )  # Will be validated as enum in application logic
    notes: str | None = Field(default=None)


class ProjectCreate(ProjectBase):
    """Schema for creating a new project."""

    project_manager_id: uuid.UUID


class ProjectUpdate(SQLModel):
    """Schema for updating a project."""

    project_name: str | None = Field(default=None, max_length=200)
    customer_name: str | None = Field(default=None, max_length=200)
    contract_value: Decimal | None = Field(
        default=None, sa_column=Column(DECIMAL(15, 2), nullable=True)
    )
    project_code: str | None = Field(default=None, max_length=100)
    pricelist_code: str | None = Field(default=None, max_length=100)
    start_date: date | None = None
    planned_completion_date: date | None = None
    actual_completion_date: date | None = None
    project_manager_id: uuid.UUID | None = None
    status: str | None = Field(default=None, max_length=50)
    notes: str | None = None


class Project(ProjectBase, table=True):
    """Project database model."""

    project_id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    project_manager_id: uuid.UUID = Field(foreign_key="user.id", nullable=False)
    project_manager: User | None = Relationship()

    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class ProjectPublic(ProjectBase):
    """Public project schema for API responses."""

    project_id: uuid.UUID
    project_manager_id: uuid.UUID


class ProjectsPublic(SQLModel):
    """Schema for list of projects."""

    data: list[ProjectPublic]
    count: int
