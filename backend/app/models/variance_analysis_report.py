"""Variance Analysis Report response models."""

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import DECIMAL, Column, Date
from sqlmodel import Field, SQLModel

from app.models.evm_indices import EVMIndicesProjectPublic


class VarianceAnalysisReportRowPublic(SQLModel):
    """A single row in the variance analysis report representing a cost element."""

    cost_element_id: uuid.UUID = Field(nullable=False)
    wbe_id: uuid.UUID = Field(nullable=False)
    wbe_name: str = Field(max_length=200, description="WBE machine_type")
    wbe_serial_number: str | None = Field(
        default=None, max_length=100, description="WBE serial_number"
    )
    department_code: str = Field(max_length=50)
    department_name: str = Field(max_length=200)
    cost_element_type_id: uuid.UUID | None = Field(default=None, nullable=True)
    cost_element_type_name: str | None = Field(
        default=None, max_length=200, description="Cost element type name"
    )
    # Core EVM metrics (for context)
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
    # Performance indices (for context)
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
    # Variance metrics (PRIMARY FOCUS)
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
    # Variance percentages (PRIMARY FOCUS)
    cv_percentage: Decimal | None = Field(
        default=None,
        sa_column=Column(DECIMAL(7, 4), nullable=True),
        description="Cost Variance Percentage (CV%) = CV / BAC * 100. None when BAC = 0.",
    )
    sv_percentage: Decimal | None = Field(
        default=None,
        sa_column=Column(DECIMAL(7, 4), nullable=True),
        description="Schedule Variance Percentage (SV%) = SV / BAC * 100. None when BAC = 0.",
    )
    # Severity indicators
    variance_severity: str | None = Field(
        default=None,
        max_length=20,
        description="Overall variance severity: 'critical', 'warning', or 'normal'. None if percentages undefined.",
    )
    has_cost_variance_issue: bool = Field(
        default=False, description="True if cost variance is negative (over-budget)"
    )
    has_schedule_variance_issue: bool = Field(
        default=False,
        description="True if schedule variance is negative (behind-schedule)",
    )


class VarianceAnalysisReportPublic(SQLModel):
    """Variance Analysis Report response containing filtered rows and project summary."""

    project_id: uuid.UUID = Field(nullable=False)
    project_name: str = Field(max_length=200)
    control_date: date = Field(sa_column=Column(Date, nullable=False))
    rows: list[VarianceAnalysisReportRowPublic] = Field(
        default_factory=list,
        description="Report rows (filtered to problem areas by default)",
    )
    summary: EVMIndicesProjectPublic = Field(
        description="Aggregated project totals (EVM metrics)"
    )
    total_problem_areas: int = Field(
        default=0, description="Count of cost elements with negative CV or SV"
    )
    config_used: dict[str, str] = Field(
        default_factory=dict,
        description="Variance threshold configuration used for severity calculation",
    )


class VarianceTrendPointPublic(SQLModel):
    """A single point in variance trend analysis representing a month."""

    month: date = Field(
        sa_column=Column(Date, nullable=False),
        description="First day of the month for this trend point",
    )
    cost_variance: Decimal = Field(
        default=Decimal("0.00"),
        sa_column=Column(DECIMAL(15, 2), nullable=False),
        description="Cost Variance (CV) as of end of month",
    )
    schedule_variance: Decimal = Field(
        default=Decimal("0.00"),
        sa_column=Column(DECIMAL(15, 2), nullable=False),
        description="Schedule Variance (SV) as of end of month",
    )
    cv_percentage: Decimal | None = Field(
        default=None,
        sa_column=Column(DECIMAL(7, 4), nullable=True),
        description="Cost Variance Percentage (CV%) = CV / BAC * 100. None when BAC = 0.",
    )
    sv_percentage: Decimal | None = Field(
        default=None,
        sa_column=Column(DECIMAL(7, 4), nullable=True),
        description="Schedule Variance Percentage (SV%) = SV / BAC * 100. None when BAC = 0.",
    )


class VarianceTrendPublic(SQLModel):
    """Variance Trend Analysis response containing monthly variance evolution over time."""

    project_id: uuid.UUID = Field(nullable=False)
    cost_element_id: uuid.UUID | None = Field(
        default=None,
        nullable=True,
        description="Cost element ID if cost element level, None if project/WBE level",
    )
    wbe_id: uuid.UUID | None = Field(
        default=None,
        nullable=True,
        description="WBE ID if WBE level, None if project level",
    )
    control_date: date = Field(
        sa_column=Column(Date, nullable=False),
        description="Current control date (trend ends at this date)",
    )
    trend_points: list[VarianceTrendPointPublic] = Field(
        default_factory=list,
        description="Monthly variance trend points from project start to control date",
    )
