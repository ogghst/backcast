"""Pydantic schemas for EVM (Earned Value Management) metrics."""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.versioning.enums import BranchMode


class EntityType(str, Enum):
    """Entity type for EVM metrics.

    Defines the granularity level for EVM calculations:
    - COST_ELEMENT: Individual cost element (leaf node)
    - WBE: Work Breakdown Element (intermediate node)
    - PROJECT: Project level (root node)
    """

    COST_ELEMENT = "cost_element"
    WBE = "wbe"
    PROJECT = "project"


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

    # Basic EVM metrics (float for JSON serialization as numbers)
    bac: float = Field(
        ..., description="Budget at Completion (total planned budget)"
    )
    pv: float = Field(
        ..., description="Planned Value (budgeted cost of work scheduled)"
    )
    ac: float = Field(..., description="Actual Cost (cost incurred to date)")
    ev: float = Field(
        ..., description="Earned Value (budgeted cost of work performed)"
    )

    # Variances (negative = unfavorable)
    cv: float = Field(
        ..., description="Cost Variance (EV - AC, negative = over budget)"
    )
    sv: float = Field(
        ..., description="Schedule Variance (EV - PV, negative = behind schedule)"
    )

    # Performance indices (< 1.0 = unfavorable)
    cpi: float | None = Field(
        None, description="Cost Performance Index (EV / AC, < 1.0 = over budget)"
    )
    spi: float | None = Field(
        None, description="Schedule Performance Index (EV / PV, < 1.0 = behind schedule)"
    )

    # Forecast-based performance metrics (New)
    cpi_forecast: float | None = Field(
        None, description="Implied cost efficiency to meet forecast (BAC / EAC)"
    )

    # Forecast-based metrics (from forecast entity)
    eac: float | None = Field(
        None,
        description="Estimate at Completion (from forecast.eac_amount, "
        "projected total cost at completion)",
    )
    vac: float | None = Field(
        None,
        description="Variance at Completion = BAC - EAC (negative = over budget, "
        "positive = under budget)",
    )
    etc: float | None = Field(
        None,
        description="Estimate to Complete = EAC - AC (remaining work cost)",
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
    progress_percentage: float | None = Field(
        None, description="Progress percentage (0-100)"
    )
    warning: str | None = Field(
        None, description="Warning message (e.g., no progress reported)"
    )


class EVMMetricsResponse(BaseModel):
    """Generic EVM metrics response for any entity type.

    Provides a flat structure with all EVM metrics explicitly defined.
    Supports cost_element, wbe, and project entity types.

    Metrics:
    - BAC: Budget at Completion (total planned budget)
    - PV: Planned Value (budgeted cost of work scheduled)
    - AC: Actual Cost (actual cost incurred)
    - EV: Earned Value (budgeted cost of work performed)
    - CV: Cost Variance (EV - AC)
    - SV: Schedule Variance (EV - PV)
    - CPI: Cost Performance Index (EV / AC)
    - SPI: Schedule Performance Index (EV / PV)
    - EAC: Estimate at Completion
    - VAC: Variance at Completion (BAC - EAC)
    - ETC: Estimate to Complete (EAC - AC)

    This schema uses a flat structure with all metrics as individual fields,
    not a list-based approach, for better type safety and API clarity.
    """

    model_config = ConfigDict(from_attributes=True)

    # Entity identification
    entity_type: EntityType = Field(
        ..., description="Entity type (cost_element, wbe, or project)"
    )
    entity_id: UUID = Field(..., description="Entity ID (cost element, WBE, or project)")

    # Basic EVM metrics (float for JSON serialization as numbers)
    bac: float = Field(
        ..., description="Budget at Completion (total planned budget)"
    )
    pv: float = Field(
        ..., description="Planned Value (budgeted cost of work scheduled)"
    )
    ac: float = Field(..., description="Actual Cost (cost incurred to date)")
    ev: float = Field(
        ..., description="Earned Value (budgeted cost of work performed)"
    )

    # Variances (negative = unfavorable)
    cv: float = Field(
        ..., description="Cost Variance (EV - AC, negative = over budget)"
    )
    sv: float = Field(
        ..., description="Schedule Variance (EV - PV, negative = behind schedule)"
    )

    # Performance indices (< 1.0 = unfavorable)
    cpi: float | None = Field(
        None, description="Cost Performance Index (EV / AC, < 1.0 = over budget)"
    )
    spi: float | None = Field(
        None, description="Schedule Performance Index (EV / PV, < 1.0 = behind schedule)"
    )

    # Forecast-based metrics
    eac: float | None = Field(
        None,
        description="Estimate at Completion (projected total cost at completion)",
    )
    vac: float | None = Field(
        None,
        description="Variance at Completion = BAC - EAC (negative = over budget)",
    )
    etc: float | None = Field(
        None,
        description="Estimate to Complete = EAC - AC (remaining work cost)",
    )

    # Metadata
    control_date: datetime = Field(
        ..., description="Control date for time-travel query"
    )
    branch: str = Field(
        ..., description="Branch name"
    )
    branch_mode: BranchMode = Field(
        ..., description="Branch mode (ISOLATED or MERGE)"
    )
    progress_percentage: float | None = Field(
        None, description="Progress percentage (0-100)"
    )
    warning: str | None = Field(
        None, description="Warning message (e.g., no progress reported)"
    )


class EVMTimeSeriesPoint(BaseModel):
    """Single data point for EVM time-series charts.

    Represents EVM metrics at a specific point in time for charting.
    Used in time-series responses for trend visualization.
    """

    model_config = ConfigDict(from_attributes=True)

    date: datetime = Field(..., description="Date of the data point")
    pv: Decimal = Field(..., description="Planned Value at this date")
    ev: Decimal = Field(..., description="Earned Value at this date")
    ac: Decimal = Field(..., description="Actual Cost at this date")
    forecast: Decimal = Field(
        ..., description="Forecast value at this date"
    )
    actual: Decimal = Field(..., description="Actual value at this date")


class EVMTimeSeriesGranularity(str, Enum):
    """Time granularity for EVM time-series aggregation.

    Defines the time interval for data point aggregation:
    - DAY: Daily data points
    - WEEK: Weekly data points (default)
    - MONTH: Monthly data points
    """

    DAY = "day"
    WEEK = "week"
    MONTH = "month"


class EVMTimeSeriesResponse(BaseModel):
    """EVM time-series data for charts.

    Contains aggregated EVM metrics over a time range with specified granularity.
    Used for rendering trend charts and performance curves.

    Server-side aggregation is performed based on the requested granularity.
    """

    model_config = ConfigDict(from_attributes=True)

    granularity: EVMTimeSeriesGranularity = Field(
        ..., description="Time granularity (day, week, month)"
    )
    points: list[EVMTimeSeriesPoint] = Field(
        ..., description="List of time-series data points"
    )
    start_date: datetime = Field(
        ..., description="Start date of the time series"
    )
    end_date: datetime = Field(
        ..., description="End date of the time series"
    )
    total_points: int = Field(
        ..., description="Total number of data points"
    )
