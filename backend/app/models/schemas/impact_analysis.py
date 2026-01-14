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
from typing import Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field


# Type alias for entity change types
EntityChangeType: TypeAlias = Literal["added", "modified", "removed"]


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
    # EVM metrics deferred to Sprint 8
    # eac: KPIMetric | None = None
    # cpi: KPIMetric | None = None
    # spi: KPIMetric | None = None


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

    change_order_id: int = Field(description="Change Order ID")
    branch_id: int = Field(description="Branch ID being compared")
    main_branch_id: int = Field(description="Main branch ID (baseline)")
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
