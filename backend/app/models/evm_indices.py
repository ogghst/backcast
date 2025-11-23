"""EVM performance indices response models."""

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import DECIMAL, Column, Date
from sqlmodel import Field, SQLModel


class EVMIndicesBase(SQLModel):
    """Base schema for EVM performance indices responses."""

    level: str = Field(max_length=20)
    control_date: date = Field(sa_column=Column(Date, nullable=False))
    cpi: Decimal | None = Field(
        default=None,
        sa_column=Column(DECIMAL(7, 4), nullable=True),
        description="Cost Performance Index (CPI) = EV / AC. None when AC = 0.",
    )
    spi: Decimal | None = Field(
        default=None,
        sa_column=Column(DECIMAL(7, 4), nullable=True),
        description="Schedule Performance Index (SPI) = EV / PV. None when PV = 0.",
    )
    tcpi: Decimal | str | None = Field(
        default=None,
        description="To-Complete Performance Index (TCPI) = (BAC - EV) / (BAC - AC). Returns 'overrun' when BAC ≤ AC.",
    )
    planned_value: Decimal = Field(
        default=Decimal("0.00"), sa_column=Column(DECIMAL(15, 2), nullable=False)
    )
    earned_value: Decimal = Field(
        default=Decimal("0.00"), sa_column=Column(DECIMAL(15, 2), nullable=False)
    )
    actual_cost: Decimal = Field(
        default=Decimal("0.00"), sa_column=Column(DECIMAL(15, 2), nullable=False)
    )
    budget_bac: Decimal = Field(
        default=Decimal("0.00"), sa_column=Column(DECIMAL(15, 2), nullable=False)
    )
    eac: Decimal | None = Field(
        default=None,
        sa_column=Column(DECIMAL(15, 2), nullable=True),
        description="Estimate at Completion (EAC) calculated from forecast or BAC fallback.",
    )
    forecasted_quality: Decimal | None = Field(
        default=None,
        sa_column=Column(DECIMAL(7, 4), nullable=True),
        description="Forecasted quality percentage (0.0000 to 1.0000). Percentage of EAC that comes from forecasts vs BAC fallback.",
    )
    cost_variance: Decimal = Field(
        default=Decimal("0.00"),
        sa_column=Column(DECIMAL(15, 2), nullable=False),
        description="Cost Variance (CV) = EV - AC. Negative = over-budget, positive = under-budget, zero = on-budget.",
    )
    schedule_variance: Decimal = Field(
        default=Decimal("0.00"),
        sa_column=Column(DECIMAL(15, 2), nullable=False),
        description="Schedule Variance (SV) = EV - PV. Negative = behind-schedule, positive = ahead-of-schedule, zero = on-schedule.",
    )


class EVMIndicesCostElementPublic(EVMIndicesBase):
    """EVM performance indices response for cost elements."""

    cost_element_id: uuid.UUID = Field(nullable=False)


class EVMIndicesWBEPublic(EVMIndicesBase):
    """EVM performance indices response for WBEs."""

    wbe_id: uuid.UUID = Field(nullable=False)


class EVMIndicesProjectPublic(EVMIndicesBase):
    """EVM performance indices response for projects."""

    project_id: uuid.UUID = Field(nullable=False)
