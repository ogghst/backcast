"""Pydantic schemas for EVM (Earned Value Management) metrics."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.versioning.enums import BranchMode


class EVMMetricsRead(BaseModel):
    """Earned Value Management metrics for a cost element.

    Provides comprehensive EVM analysis for project performance measurement.
    All metrics support time-travel queries via control_date parameter
    and branch isolation via branch and branch_mode parameters.

    Metrics:
    - BAC: Budget at Completion (total planned budget)
    - PV: Planned Value (budgeted cost of work scheduled)
    - AC: Actual Cost (actual cost incurred)
    - EV: Earned Value (budgeted cost of work performed)
    - CV: Cost Variance (EV - AC)
    - SV: Schedule Variance (EV - PV)
    - CPI: Cost Performance Index (EV / AC)
    - SPI: Schedule Performance Index (EV / PV)

    Formulas:
    - BAC = cost_element.budget_amount (as of control_date)
    - PV = BAC × progress_percentage (from schedule baseline as of control_date)
    - AC = sum(cost_registrations.amount) (global facts, not branchable)
    - EV = BAC × progress_percentage (from progress entries)
    - CV = EV - AC (negative = over budget)
    - SV = EV - PV (negative = behind schedule)
    - CPI = EV / AC (< 1.0 = over budget)
    - SPI = EV / PV (< 1.0 = behind schedule)

    Time-Travel & Branching:
    - All branchable entities (CostElement, ScheduleBaseline) are fetched
      as they were at the control_date (time-travel)
    - Branch mode (ISOLATED/MERGE) determines whether to fall back to parent branches
    - Cost registrations and progress entries are global facts (not branchable)
    """

    model_config = ConfigDict(from_attributes=True)

    # Basic EVM metrics
    bac: Decimal = Field(
        ..., description="Budget at Completion (total planned budget)"
    )
    pv: Decimal = Field(
        ..., description="Planned Value (budgeted cost of work scheduled)"
    )
    ac: Decimal = Field(..., description="Actual Cost (cost incurred to date)")
    ev: Decimal = Field(
        ..., description="Earned Value (budgeted cost of work performed)"
    )

    # Variances (negative = unfavorable)
    cv: Decimal = Field(
        ..., description="Cost Variance (EV - AC, negative = over budget)"
    )
    sv: Decimal = Field(
        ..., description="Schedule Variance (EV - PV, negative = behind schedule)"
    )

    # Performance indices (< 1.0 = unfavorable)
    cpi: Decimal | None = Field(
        None, description="Cost Performance Index (EV / AC, < 1.0 = over budget)"
    )
    spi: Decimal | None = Field(
        None, description="Schedule Performance Index (EV / PV, < 1.0 = behind schedule)"
    )

    # Metadata
    cost_element_id: UUID = Field(..., description="Cost Element ID")
    control_date: datetime = Field(
        ..., description="Control date for time-travel query (entities fetched at this valid_time)"
    )
    branch: str = Field(
        ..., description="Branch name (ISOLATED uses only this branch, MERGE falls back to parents)"
    )
    branch_mode: BranchMode = Field(
        ..., description="Branch mode (ISOLATED or MERGE)"
    )
    progress_percentage: Decimal | None = Field(
        None, description="Progress percentage (0-100)"
    )
    warning: str | None = Field(
        None, description="Warning message (e.g., no progress reported)"
    )
