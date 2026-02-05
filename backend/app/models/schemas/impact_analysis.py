"""
Impact Analysis Schemas for Change Order Comparison.

This module defines Pydantic models for comparing financial and schedule
impact between main branch and change order branches.

Per Phase 3 Plan:
- KPI Comparison: BAC, Budget Delta, Gross Margin (EVM metrics deferred to Sprint 8)
- Entity Changes: Added/Modified/Removed WBEs and Cost Elements (financial fields only)
- Waterfall Chart: Cost bridge visualization
- Time Series: Weekly S-curve data for budget comparison
"""

from datetime import date
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from typing_extensions import TypedDict

# Type alias for entity change types
type EntityChangeType = Literal["added", "modified", "removed"]


class ScheduleBaselineComparison(TypedDict):
    """Result of schedule baseline comparison between branches.

    Used internally by ImpactAnalysisService for schedule analysis.
    """

    start_delta_days: int  # Days difference in start date (change - main)
    end_delta_days: int  # Days difference in end date (change - main)
    duration_delta_days: int  # Days difference in duration (change - main)
    progression_changed: bool  # Whether progression type changed
    main_progression_type: str  # Progression type in main branch
    change_progression_type: str  # Progression type in change branch


class EVMMetricsComparison(TypedDict):
    """Result of EVM metrics comparison between branches.

    Used internally by ImpactAnalysisService for EVM analysis.
    """

    cpi_delta: Decimal  # Cost Performance Index delta (change - main)
    spi_delta: Decimal  # Schedule Performance Index delta (change - main)
    tcpi_delta: Decimal  # To-Complete Performance Index delta (change - main)
    eac_delta: Decimal  # Estimate at Completion delta (change - main)


class VACComparison(TypedDict):
    """Result of VAC (Variance at Completion) comparison between branches.

    Used internally by ImpactAnalysisService for VAC analysis.
    """

    vac_delta: Decimal  # Variance at Completion delta (change - main)
    main_vac: Decimal  # Variance at Completion in main branch (BAC - EAC)
    change_vac: Decimal  # Variance at Completion in change branch (BAC - EAC)


class KPIMetric(BaseModel):
    """A single KPI value comparison between main and change branch."""

    model_config = ConfigDict(strict=True)

    main_value: Decimal | None = Field(
        default=None,
        description="Value in main branch",
    )
    change_value: Decimal | None = Field(
        default=None,
        description="Value in change branch",
    )
    delta: Decimal = Field(
        default=Decimal("0"),
        description="Absolute difference (change - main)",
    )
    delta_percent: float | None = Field(
        default=None,
        description="Percentage difference ((change - main) / main * 100), null if main is 0",
    )


class KPIScorecard(BaseModel):
    """KPI comparison scorecard for impact analysis."""

    model_config = ConfigDict(strict=True)

    bac: KPIMetric = Field(description="Budget at Completion comparison")
    budget_delta: KPIMetric = Field(description="Total budget allocation delta")
    gross_margin: KPIMetric = Field(description="Gross margin comparison")
    actual_costs: KPIMetric = Field(description="Actual costs (AC) comparison")
    revenue_delta: KPIMetric = Field(description="Revenue allocation delta")

    # Phase 5: Schedule metrics
    schedule_start_date: KPIMetric | None = Field(
        default=None,
        description="Schedule start date comparison (ISO format string)",
    )
    schedule_end_date: KPIMetric | None = Field(
        default=None,
        description="Schedule end date comparison (ISO format string)",
    )
    schedule_duration: KPIMetric | None = Field(
        default=None,
        description="Schedule duration in days",
    )

    # Phase 5: EVM metrics
    eac: KPIMetric | None = Field(
        default=None,
        description="Estimate at Completion (EAC) comparison",
    )
    cpi: KPIMetric | None = Field(
        default=None,
        description="Cost Performance Index (CPI) comparison",
    )
    spi: KPIMetric | None = Field(
        default=None,
        description="Schedule Performance Index (SPI) comparison",
    )
    tcpi: KPIMetric | None = Field(
        default=None,
        description="To-Complete Performance Index (TCPI) comparison",
    )
    vac: KPIMetric | None = Field(
        default=None,
        description="Variance at Completion (VAC) comparison",
    )


class EntityChange(BaseModel):
    """A single entity change between branches."""

    model_config = ConfigDict(strict=True)

    id: int = Field(description="Entity ID")
    name: str = Field(description="Entity name")
    change_type: EntityChangeType = Field(description="Type of change")
    # Financial fields only per requirements
    budget_delta: Decimal | None = Field(
        default=None,
        description="Budget allocation change (for modified/removed)",
    )
    revenue_delta: Decimal | None = Field(
        default=None,
        description="Revenue allocation change (for modified/removed)",
    )
    cost_delta: Decimal | None = Field(
        default=None,
        description="Cost change (for modified/removed)",
    )


class EntityChanges(BaseModel):
    """Entity changes grouped by type."""

    model_config = ConfigDict(strict=True)

    wbes: list[EntityChange] = Field(
        default_factory=list,
        description="Work Breakdown Element changes",
    )
    cost_elements: list[EntityChange] = Field(
        default_factory=list,
        description="Cost Element changes",
    )
    cost_registrations: list[EntityChange] = Field(
        default_factory=list,
        description="Cost Registration (actual costs) changes",
    )


class WaterfallSegment(BaseModel):
    """A single segment in the waterfall chart."""

    model_config = ConfigDict(strict=True)

    name: str = Field(description="Segment label")
    value: Decimal = Field(description="Segment value (can be negative for decreases)")
    is_delta: bool = Field(
        default=False,
        description="True if this represents a change (not a baseline)",
    )


class TimeSeriesPoint(BaseModel):
    """A single point in time-series data."""

    model_config = ConfigDict(strict=True)

    week_start: date = Field(description="Week start date")
    main_value: Decimal | None = Field(
        default=None,
        description="Value in main branch for this week",
    )
    change_value: Decimal | None = Field(
        default=None,
        description="Value in change branch for this week",
    )


class TimeSeriesData(BaseModel):
    """Weekly time-series data for S-curve comparison."""

    model_config = ConfigDict(strict=True)

    metric_name: str = Field(description="Metric being tracked (e.g., 'budget')")
    data_points: list[TimeSeriesPoint] = Field(
        default_factory=list,
        description="Weekly data points",
    )


class ImpactAnalysisResponse(BaseModel):
    """Complete impact analysis response for a change order."""

    model_config = ConfigDict(strict=True)

    change_order_id: UUID = Field(description="Change Order ID (UUID)")
    branch_name: str = Field(
        description="Branch name being compared (e.g., 'co-CO-2026-001')"
    )
    main_branch_name: str = Field(description="Main branch name (always 'main')")
    kpi_scorecard: KPIScorecard = Field(description="KPI comparison")
    entity_changes: EntityChanges = Field(description="Entity changes")
    waterfall: list[WaterfallSegment] = Field(
        default_factory=list,
        description="Waterfall chart data",
    )
    time_series: list[TimeSeriesData] = Field(
        default_factory=list,
        description="S-curve comparison data",
    )
