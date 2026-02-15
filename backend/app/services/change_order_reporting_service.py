"""Change Order Reporting Service for analytics and statistics.

Provides aggregation methods for the Change Order Dashboard.
Computes statistics, trends, and aging items for change orders.
"""

import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain.change_order import ChangeOrder
from app.models.schemas.change_order_reporting import (
    AgingChangeOrder,
    ApprovalWorkloadItem,
    ChangeOrderImpactStats,
    ChangeOrderStatsResponse,
    ChangeOrderStatusStats,
    ChangeOrderTrendPoint,
)

logger = logging.getLogger(__name__)


class ChangeOrderReportingService:
    """Service for Change Order reporting and analytics.

    Provides aggregated statistics for the Change Order Dashboard,
    including status distribution, impact breakdown, cost trends,
    approval workload, and aging items.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_change_order_stats(
        self,
        project_id: UUID,
        branch: str = "main",
        as_of: datetime | None = None,
        aging_threshold_days: int = 7,
    ) -> ChangeOrderStatsResponse:
        """Get comprehensive change order statistics for a project.

        Args:
            project_id: Project UUID to filter by
            branch: Branch name (default: "main")
            as_of: Optional timestamp for time-travel queries
            aging_threshold_days: Days threshold for aging detection (default: 7)

        Returns:
            ChangeOrderStatsResponse with all aggregated statistics
        """
        # Get current timestamp if not provided
        if as_of is None:
            as_of = datetime.now(UTC)

        # Build base query for current change orders (kept for future use)
        _ = self._build_base_query(project_id, branch, as_of)

        # Get summary KPIs
        summary = await self._get_summary_kpis(project_id, branch, as_of)

        # Get distributions
        by_status = await self._get_status_distribution(project_id, branch, as_of)
        by_impact_level = await self._get_impact_distribution(project_id, branch, as_of)

        # Get trend data
        cost_trend = await self._get_cost_trend(project_id, branch, as_of)

        # Get approval workload
        approval_workload = await self._get_approval_workload(project_id, branch, as_of)

        # Get aging items
        aging_items = await self._get_aging_items(
            project_id, branch, as_of, aging_threshold_days
        )

        # Get average approval time
        avg_approval_time = await self._get_avg_approval_time(project_id, branch, as_of)

        return ChangeOrderStatsResponse(
            total_count=summary["total_count"],
            total_cost_exposure=summary["total_cost_exposure"],
            pending_value=summary["pending_value"],
            approved_value=summary["approved_value"],
            by_status=by_status,
            by_impact_level=by_impact_level,
            cost_trend=cost_trend,
            avg_approval_time_days=avg_approval_time,
            approval_workload=approval_workload,
            aging_items=aging_items,
            aging_threshold_days=aging_threshold_days,
        )

    def _build_base_query(
        self, project_id: UUID, branch: str, as_of: datetime
    ) -> Any:
        """Build base query for current change orders."""
        return (
            select(ChangeOrder)
            .where(
                ChangeOrder.project_id == project_id,
                ChangeOrder.branch == branch,
                func.upper(ChangeOrder.valid_time).is_(None),
                ChangeOrder.deleted_at.is_(None),
            )
        )

    async def _get_summary_kpis(
        self, project_id: UUID, branch: str, as_of: datetime
    ) -> dict[str, Any]:
        """Calculate summary KPIs: total count, cost exposure, pending/approved values."""
        # Total count and cost exposure using raw SQL for JSONB access
        count_stmt = text("""
            SELECT
                COUNT(*) as total_count,
                COALESCE(
                    SUM(
                        CAST(
                            impact_analysis_results->'kpi_scorecard'->'budget_delta'->>'delta'
                            AS NUMERIC
                        )
                    ),
                    0
                ) as total_cost_exposure
            FROM change_orders
            WHERE project_id = :project_id
              AND branch = :branch
              AND upper(valid_time) IS NULL
              AND deleted_at IS NULL
        """)

        result = await self.session.execute(
            count_stmt, {"project_id": str(project_id), "branch": branch}
        )
        row = result.one()

        total_count = row.total_count or 0
        total_cost_exposure = Decimal(str(row.total_cost_exposure or 0))

        # Pending value (Submitted for Approval, Under Review, Draft)
        pending_stmt = text("""
            SELECT COALESCE(
                SUM(
                    CAST(
                        impact_analysis_results->'kpi_scorecard'->'budget_delta'->>'delta'
                        AS NUMERIC
                    )
                ),
                0
            ) as pending_value
            FROM change_orders
            WHERE project_id = :project_id
              AND branch = :branch
              AND upper(valid_time) IS NULL
              AND deleted_at IS NULL
              AND status IN ('Draft', 'Submitted for Approval', 'Under Review')
        """)

        pending_result = await self.session.execute(
            pending_stmt, {"project_id": str(project_id), "branch": branch}
        )
        pending_value = Decimal(str(pending_result.scalar() or 0))

        # Approved value
        approved_stmt = text("""
            SELECT COALESCE(
                SUM(
                    CAST(
                        impact_analysis_results->'kpi_scorecard'->'budget_delta'->>'delta'
                        AS NUMERIC
                    )
                ),
                0
            ) as approved_value
            FROM change_orders
            WHERE project_id = :project_id
              AND branch = :branch
              AND upper(valid_time) IS NULL
              AND deleted_at IS NULL
              AND status = 'Approved'
        """)

        approved_result = await self.session.execute(
            approved_stmt, {"project_id": str(project_id), "branch": branch}
        )
        approved_value = Decimal(str(approved_result.scalar() or 0))

        return {
            "total_count": total_count,
            "total_cost_exposure": total_cost_exposure,
            "pending_value": pending_value,
            "approved_value": approved_value,
        }

    async def _get_status_distribution(
        self, project_id: UUID, branch: str, as_of: datetime
    ) -> list[ChangeOrderStatusStats]:
        """Get breakdown of change orders by status."""
        stmt = text("""
            SELECT
                status,
                COUNT(*) as co_count,
                COALESCE(
                    SUM(
                        CAST(
                            impact_analysis_results->'kpi_scorecard'->'budget_delta'->>'delta'
                            AS NUMERIC
                        )
                    ),
                    0
                ) as total_value
            FROM change_orders
            WHERE project_id = :project_id
              AND branch = :branch
              AND upper(valid_time) IS NULL
              AND deleted_at IS NULL
            GROUP BY status
            ORDER BY status
        """)

        result = await self.session.execute(
            stmt, {"project_id": str(project_id), "branch": branch}
        )
        rows = result.all()

        return [
            ChangeOrderStatusStats(
                status=row.status,
                count=row.co_count,
                total_value=Decimal(str(row.total_value or 0)),
            )
            for row in rows
        ]

    async def _get_impact_distribution(
        self, project_id: UUID, branch: str, as_of: datetime
    ) -> list[ChangeOrderImpactStats]:
        """Get breakdown of change orders by impact level."""
        stmt = text("""
            SELECT
                COALESCE(impact_level, 'Unassigned') as impact_level,
                COUNT(*) as co_count,
                COALESCE(
                    SUM(
                        CAST(
                            impact_analysis_results->'kpi_scorecard'->'budget_delta'->>'delta'
                            AS NUMERIC
                        )
                    ),
                    0
                ) as total_value
            FROM change_orders
            WHERE project_id = :project_id
              AND branch = :branch
              AND upper(valid_time) IS NULL
              AND deleted_at IS NULL
            GROUP BY impact_level
            ORDER BY impact_level
        """)

        result = await self.session.execute(
            stmt, {"project_id": str(project_id), "branch": branch}
        )
        rows = result.all()

        return [
            ChangeOrderImpactStats(
                impact_level=row.impact_level or "Unassigned",
                count=row.co_count,
                total_value=Decimal(str(row.total_value or 0)),
            )
            for row in rows
        ]

    async def _get_cost_trend(
        self, project_id: UUID, branch: str, as_of: datetime
    ) -> list[ChangeOrderTrendPoint]:
        """Get cumulative cost trend over time (weekly aggregation).

        Uses the transaction_time lower bound (creation date) for trend calculation.
        """
        stmt = text("""
            SELECT
                date_trunc('week', lower(transaction_time)) as week_start,
                COUNT(*) as co_count,
                COALESCE(
                    SUM(
                        CAST(
                            impact_analysis_results->'kpi_scorecard'->'budget_delta'->>'delta'
                            AS NUMERIC
                        )
                    ),
                    0
                ) as week_value
            FROM change_orders
            WHERE project_id = :project_id
              AND branch = :branch
              AND upper(valid_time) IS NULL
              AND deleted_at IS NULL
              AND lower(transaction_time) <= :as_of
            GROUP BY date_trunc('week', lower(transaction_time))
            ORDER BY week_start
        """)

        result = await self.session.execute(
            stmt, {"project_id": str(project_id), "branch": branch, "as_of": as_of}
        )
        rows = result.all()

        # Calculate cumulative values
        trend_points = []
        cumulative_value = Decimal("0")
        cumulative_count = 0

        for row in rows:
            if row.week_start is None:
                continue

            week_value = Decimal(str(row.week_value or 0))
            cumulative_value += week_value
            cumulative_count += int(row.co_count)

            trend_points.append(
                ChangeOrderTrendPoint(
                    trend_date=row.week_start.date(),
                    cumulative_value=cumulative_value,
                    count=cumulative_count,
                )
            )

        return trend_points

    async def _get_approval_workload(
        self, project_id: UUID, branch: str, as_of: datetime
    ) -> list[ApprovalWorkloadItem]:
        """Get pending approval workload grouped by approver."""
        stmt = text("""
            SELECT
                u.user_id,
                u.full_name,
                COUNT(*) as pending_count,
                SUM(CASE WHEN co.sla_due_date < :as_of THEN 1 ELSE 0 END) as overdue_count,
                AVG(EXTRACT(day FROM (:as_of - COALESCE(co.sla_assigned_at, :as_of)))) as avg_days_waiting
            FROM change_orders co
            LEFT JOIN users u ON co.assigned_approver_id = u.user_id
            WHERE co.project_id = :project_id
              AND co.branch = :branch
              AND co.status IN ('Submitted for Approval', 'Under Review')
              AND upper(co.valid_time) IS NULL
              AND co.deleted_at IS NULL
              AND co.assigned_approver_id IS NOT NULL
            GROUP BY u.user_id, u.full_name
            ORDER BY u.full_name
        """)

        result = await self.session.execute(
            stmt,
            {
                "project_id": str(project_id),
                "branch": branch,
                "as_of": as_of,
            },
        )
        rows = result.all()

        return [
            ApprovalWorkloadItem(
                approver_id=row.user_id,
                approver_name=row.full_name or "Unknown",
                pending_count=row.pending_count or 0,
                overdue_count=row.overdue_count or 0,
                avg_days_waiting=float(row.avg_days_waiting or 0),
            )
            for row in rows
        ]

    async def _get_aging_items(
        self,
        project_id: UUID,
        branch: str,
        as_of: datetime,
        threshold_days: int,
    ) -> list[AgingChangeOrder]:
        """Get change orders that have been in the same status too long.

        Uses audit log to determine when the status last changed.
        """
        cutoff_date = as_of - timedelta(days=threshold_days)

        stmt = text("""
            SELECT
                co.change_order_id,
                co.code,
                co.title,
                co.status,
                co.impact_level,
                co.sla_status,
                latest.changed_at
            FROM change_orders co
            JOIN (
                SELECT DISTINCT ON (change_order_id)
                    change_order_id,
                    new_status,
                    changed_at
                FROM change_order_audit_log
                ORDER BY change_order_id, changed_at DESC
            ) latest ON co.change_order_id = latest.change_order_id
            WHERE co.project_id = :project_id
              AND co.branch = :branch
              AND co.status IN ('Submitted for Approval', 'Under Review')
              AND upper(co.valid_time) IS NULL
              AND co.deleted_at IS NULL
              AND latest.changed_at < :cutoff_date
            ORDER BY latest.changed_at ASC
            LIMIT 20
        """)

        result = await self.session.execute(
            stmt,
            {
                "project_id": str(project_id),
                "branch": branch,
                "cutoff_date": cutoff_date,
            },
        )
        rows = result.all()

        aging_items = []
        for row in rows:
            # Calculate days in status
            days_in_status = (as_of - row.changed_at).days if row.changed_at else 0

            aging_items.append(
                AgingChangeOrder(
                    change_order_id=row.change_order_id,
                    code=row.code,
                    title=row.title,
                    status=row.status,
                    days_in_status=days_in_status,
                    impact_level=row.impact_level,
                    sla_status=row.sla_status,
                )
            )

        return aging_items

    async def _get_avg_approval_time(
        self, project_id: UUID, branch: str, as_of: datetime
    ) -> float | None:
        """Calculate average approval time from audit log.

        Measures time from 'Submitted for Approval' to 'Approved'.
        """
        stmt = text("""
            SELECT AVG(EXTRACT(day FROM (approval.changed_at - submission.changed_at))) as avg_days
            FROM change_order_audit_log submission
            JOIN change_order_audit_log approval
                ON submission.change_order_id = approval.change_order_id
            JOIN change_orders co
                ON co.change_order_id = submission.change_order_id
            WHERE submission.new_status = 'Submitted for Approval'
              AND approval.new_status = 'Approved'
              AND co.project_id = :project_id
              AND co.branch = :branch
        """)

        result = await self.session.execute(
            stmt, {"project_id": str(project_id), "branch": branch}
        )
        avg_days = result.scalar_one_or_none()

        return float(avg_days) if avg_days is not None else None
