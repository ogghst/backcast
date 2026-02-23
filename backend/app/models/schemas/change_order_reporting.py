"""Pydantic schemas for Change Order Reporting API.

Response schemas for aggregated Change Order statistics and analytics.
These support the Change Order Dashboard functionality.
"""

from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ChangeOrderStatusStats(BaseModel):
    """Statistics by change order status."""

    model_config = ConfigDict(strict=True)

    status: str = Field(
        description="Status value (Draft, Submitted for Approval, etc.)"
    )
    count: int = Field(description="Number of change orders in this status")
    total_value: Decimal | None = Field(
        default=None,
        description="Total cost exposure for COs in this status",
    )


class ChangeOrderImpactStats(BaseModel):
    """Statistics by impact level."""

    model_config = ConfigDict(strict=True)

    impact_level: str = Field(description="Impact level (LOW/MEDIUM/HIGH/CRITICAL)")
    count: int = Field(description="Number of change orders at this impact level")
    total_value: Decimal | None = Field(
        default=None,
        description="Total cost exposure for COs at this impact level",
    )


class ChangeOrderTrendPoint(BaseModel):
    """Single point in the cost trend."""

    model_config = ConfigDict(strict=True)

    trend_date: date = Field(description="Date of the data point (week/month start)")
    cumulative_value: Decimal = Field(
        default=Decimal("0"),
        description="Cumulative cost impact up to this date",
    )
    count: int = Field(
        default=0,
        description="Number of change orders up to this date",
    )


class ApprovalWorkloadItem(BaseModel):
    """Pending approval workload by approver."""

    model_config = ConfigDict(strict=True)

    approver_id: UUID = Field(description="User ID of the approver")
    approver_name: str = Field(description="Full name of the approver")
    pending_count: int = Field(
        default=0,
        description="Number of pending approvals",
    )
    overdue_count: int = Field(
        default=0,
        description="Number of overdue approvals (past SLA deadline)",
    )
    avg_days_waiting: float = Field(
        default=0.0,
        description="Average days waiting for approval",
    )


class AgingChangeOrder(BaseModel):
    """Change order that is stuck or aging."""

    model_config = ConfigDict(strict=True)

    change_order_id: UUID = Field(description="Change Order ID (UUID)")
    code: str = Field(description="Business identifier (e.g., CO-2026-001)")
    title: str = Field(description="Change order title")
    status: str = Field(description="Current status")
    days_in_status: int = Field(description="Number of days in current status")
    impact_level: str | None = Field(
        default=None,
        description="Impact level (LOW/MEDIUM/HIGH/CRITICAL)",
    )
    sla_status: str | None = Field(
        default=None,
        description="SLA status (pending/approaching/overdue)",
    )


class ChangeOrderStatsResponse(BaseModel):
    """Aggregated statistics for change orders.

    Response schema for GET /api/v1/change-orders/stats endpoint.
    Provides comprehensive analytics for the Change Order Dashboard.
    """

    model_config = ConfigDict(strict=True)

    # Summary KPIs
    total_count: int = Field(
        default=0,
        description="Total number of change orders",
    )
    total_cost_exposure: Decimal = Field(
        default=Decimal("0"),
        description="Total potential cost impact (sum of budget deltas)",
    )
    pending_value: Decimal = Field(
        default=Decimal("0"),
        description="Total value of pending change orders (not yet approved/rejected)",
    )
    approved_value: Decimal = Field(
        default=Decimal("0"),
        description="Total value of approved change orders",
    )

    # Distributions
    by_status: list[ChangeOrderStatusStats] = Field(
        default_factory=list,
        description="Breakdown by status",
    )
    by_impact_level: list[ChangeOrderImpactStats] = Field(
        default_factory=list,
        description="Breakdown by impact level",
    )

    # Trend data
    cost_trend: list[ChangeOrderTrendPoint] = Field(
        default_factory=list,
        description="Cumulative cost trend over time",
    )

    # Approval metrics
    avg_approval_time_days: float | None = Field(
        default=None,
        description="Average days from submission to approval (historical)",
    )
    approval_workload: list[ApprovalWorkloadItem] = Field(
        default_factory=list,
        description="Pending approvals grouped by approver",
    )

    # Aging items
    aging_items: list[AgingChangeOrder] = Field(
        default_factory=list,
        description="Change orders that have been in the same status too long",
    )
    aging_threshold_days: int = Field(
        default=7,
        description="Configured threshold for aging detection",
    )
