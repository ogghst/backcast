"""Forecast model and related schemas."""
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import DECIMAL, Column, Date, DateTime
from sqlmodel import Field, Relationship, SQLModel

from app.models.cost_element import CostElement

# Import for forward references
from app.models.user import User


class ForecastBase(SQLModel):
    """Base forecast schema with common fields."""

    forecast_date: date = Field(sa_column=Column(Date, nullable=False))
    estimate_at_completion: Decimal = Field(
        default=Decimal("0.00"), sa_column=Column(DECIMAL(15, 2), nullable=False)
    )
    forecast_type: str = Field(
        max_length=50
    )  # Will be validated as enum in application logic
    assumptions: str | None = Field(default=None)
    is_current: bool = Field(default=False)


class ForecastCreate(ForecastBase):
    """Schema for creating a new forecast."""

    cost_element_id: uuid.UUID
    estimator_id: uuid.UUID


class ForecastUpdate(SQLModel):
    """Schema for updating a forecast."""

    forecast_date: date | None = None
    estimate_at_completion: Decimal | None = Field(
        default=None, sa_column=Column(DECIMAL(15, 2), nullable=True)
    )
    forecast_type: str | None = Field(default=None, max_length=50)
    assumptions: str | None = None
    is_current: bool | None = None


class Forecast(ForecastBase, table=True):
    """Forecast database model."""

    forecast_id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    cost_element_id: uuid.UUID = Field(
        foreign_key="costelement.cost_element_id", nullable=False
    )
    estimator_id: uuid.UUID = Field(foreign_key="user.id", nullable=False)

    # Relationships
    cost_element: CostElement | None = Relationship()
    estimator: User | None = Relationship()

    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    last_modified_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class ForecastPublic(ForecastBase):
    """Public forecast schema for API responses."""

    forecast_id: uuid.UUID
    cost_element_id: uuid.UUID
    estimator_id: uuid.UUID
    created_at: datetime
    last_modified_at: datetime
