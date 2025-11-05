"""Cost Timeline model and related schemas."""
from datetime import date
from decimal import Decimal

from sqlalchemy import DECIMAL, Column, Date
from sqlmodel import Field, SQLModel


class CostTimelinePointPublic(SQLModel):
    """Public schema for a single cost timeline point."""

    point_date: date = Field(sa_column=Column(Date, nullable=False))
    cumulative_cost: Decimal = Field(
        sa_column=Column(DECIMAL(15, 2), nullable=False)
    )  # Cumulative cost up to this date
    period_cost: Decimal = Field(
        sa_column=Column(DECIMAL(15, 2), nullable=False)
    )  # Cost for this specific period


class CostTimelinePublic(SQLModel):
    """Public schema for cost timeline response."""

    data: list[CostTimelinePointPublic] = Field(
        default_factory=list
    )  # Time series points
    total_cost: Decimal = Field(
        default=Decimal("0.00"), sa_column=Column(DECIMAL(15, 2), nullable=False)
    )  # Total cost across all registrations
