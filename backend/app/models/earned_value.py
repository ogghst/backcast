"""Earned value response models."""

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import DECIMAL, Column, Date
from sqlmodel import Field, SQLModel


class EarnedValueBase(SQLModel):
    """Base schema for earned value responses."""

    level: str = Field(max_length=20)
    control_date: date = Field(sa_column=Column(Date, nullable=False))
    earned_value: Decimal = Field(
        default=Decimal("0.00"), sa_column=Column(DECIMAL(15, 2), nullable=False)
    )
    percent_complete: Decimal = Field(
        default=Decimal("0.0000"), sa_column=Column(DECIMAL(7, 4), nullable=False)
    )
    budget_bac: Decimal = Field(
        default=Decimal("0.00"), sa_column=Column(DECIMAL(15, 2), nullable=False)
    )
    eac: str | None = Field(default=None)
    forecasted_quality: str | None = Field(default=None)


class EarnedValueCostElementPublic(EarnedValueBase):
    """Earned value response for cost elements."""

    cost_element_id: uuid.UUID = Field(nullable=False)


class EarnedValueWBEPublic(EarnedValueBase):
    """Earned value response for WBEs."""

    wbe_id: uuid.UUID = Field(nullable=False)


class EarnedValueProjectPublic(EarnedValueBase):
    """Earned value response for projects."""

    project_id: uuid.UUID = Field(nullable=False)
