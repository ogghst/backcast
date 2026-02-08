"""Financial Impact Service for Change Order impact level calculation.

This service calculates the financial impact of change orders by comparing
budget deltas between branches. The impact level determines the required
approval authority per the approval matrix.

Context: Used by ChangeOrderWorkflowService on submission to auto-calculate
impact level and assign appropriate approver.

Service Layer:
- Orchestrates business logic for financial impact calculation
- Integrates with ImpactAnalysisService for budget comparison data
- Raises ValueError for business errors (routes convert to HTTPException)
"""

from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain.change_order import ChangeOrder, ImpactLevel


class FinancialImpactService:
    """Service for calculating financial impact levels for change orders.

    Calculates financial impact by comparing budgets between main branch
    and change order branch. Classifies impact level according to approval
    matrix thresholds.

    Impact Levels:
    - LOW: < €10,000 (Project Manager approval)
    - MEDIUM: €10,000 - €50,000 (Department Head approval)
    - HIGH: €50,000 - €100,000 (Director approval)
    - CRITICAL: > €100,000 (Executive Committee approval)
    """

    # Impact level thresholds (in EUR)
    THRESHOLD_LOW_MAX = Decimal("10000")
    THRESHOLD_MEDIUM_MAX = Decimal("50000")
    THRESHOLD_HIGH_MAX = Decimal("100000")

    def __init__(self, db_session: AsyncSession) -> None:
        """Initialize the service with a database session.

        Args:
            db_session: Async database session for queries
        """
        self._db = db_session

    async def calculate_impact_level(
        self, change_order_id: UUID
    ) -> str:
        """Calculate the financial impact level for a change order.

        Compares budget deltas between main branch and change order branch
        to determine the financial impact. Uses absolute value of total
        budget changes (increases and decreases both count).

        Args:
            change_order_id: UUID of the change order

        Returns:
            Impact level string: LOW, MEDIUM, HIGH, or CRITICAL

        Raises:
            ValueError: If change order not found or branch invalid

        Example:
            >>> service = FinancialImpactService(session)
            >>> impact = await service.calculate_impact_level(co_id)
            >>> print(impact)
            'MEDIUM'
        """
        from typing import Any
        from typing import cast as typing_cast

        from sqlalchemy import cast as sql_cast
        from sqlalchemy import func, select
        from sqlalchemy.dialects.postgresql import TIMESTAMP

        from app.models.domain.wbe import WBE

        # Get change order to find branch and project
        as_of_tstz = sql_cast(func.clock_timestamp(), TIMESTAMP(timezone=True))
        co_stmt = (
            select(ChangeOrder)
            .where(
                ChangeOrder.change_order_id == change_order_id,
                ChangeOrder.branch == "main",
                typing_cast(Any, ChangeOrder).valid_time.op("@>")(as_of_tstz),
                func.lower(typing_cast(Any, ChangeOrder).valid_time) <= as_of_tstz,
                typing_cast(Any, ChangeOrder).deleted_at.is_(None),
            )
            .order_by(typing_cast(Any, ChangeOrder).valid_time.desc())
            .limit(1)
        )
        co_result = await self._db.execute(co_stmt)
        change_order = co_result.scalar_one_or_none()

        if change_order is None:
            raise ValueError(f"Change order {change_order_id} not found")

        project_id = change_order.project_id
        branch_name = f"br-{change_order.code}"

        # Calculate total budget from main branch
        main_budget_stmt = select(func.sum(WBE.budget_allocation)).where(
            WBE.project_id == project_id,
            WBE.branch == "main",
            typing_cast(Any, WBE).valid_time.op("@>")(as_of_tstz),
            func.lower(typing_cast(Any, WBE).valid_time) <= as_of_tstz,
            typing_cast(Any, WBE).deleted_at.is_(None),
        )
        main_budget_result = await self._db.execute(main_budget_stmt)
        main_budget = main_budget_result.scalar() or Decimal("0")

        # Calculate total budget from change branch
        change_budget_stmt = select(func.sum(WBE.budget_allocation)).where(
            WBE.project_id == project_id,
            WBE.branch == branch_name,
            typing_cast(Any, WBE).valid_time.op("@>")(as_of_tstz),
            func.lower(typing_cast(Any, WBE).valid_time) <= as_of_tstz,
            typing_cast(Any, WBE).deleted_at.is_(None),
        )
        change_budget_result = await self._db.execute(change_budget_stmt)
        change_budget = change_budget_result.scalar() or Decimal("0")

        # Calculate absolute budget delta
        budget_delta = abs(change_budget - main_budget)

        # Classify impact level based on thresholds
        return self._classify_impact_level(budget_delta)

    def _classify_impact_level(self, budget_delta: Decimal) -> str:
        """Classify financial impact level based on budget delta.

        Args:
            budget_delta: Absolute budget change amount (EUR)

        Returns:
            Impact level string: LOW, MEDIUM, HIGH, or CRITICAL
        """
        if budget_delta < self.THRESHOLD_LOW_MAX:
            return ImpactLevel.LOW
        elif budget_delta < self.THRESHOLD_MEDIUM_MAX:
            return ImpactLevel.MEDIUM
        elif budget_delta < self.THRESHOLD_HIGH_MAX:
            return ImpactLevel.HIGH
        else:
            return ImpactLevel.CRITICAL

    async def get_financial_impact_details(
        self, change_order_id: UUID
    ) -> dict[str, str | float]:
        """Get detailed financial impact information for a change order.

        Provides comprehensive financial impact details including:
        - Main branch budget
        - Change branch budget
        - Budget delta
        - Impact level
        - Revenue impact (if available)

        Args:
            change_order_id: UUID of the change order

        Returns:
            Dictionary with financial impact details

        Raises:
            ValueError: If change order not found or branch invalid
        """
        from typing import Any
        from typing import cast as typing_cast

        from sqlalchemy import cast as sql_cast
        from sqlalchemy import func, select
        from sqlalchemy.dialects.postgresql import TIMESTAMP

        from app.models.domain.wbe import WBE

        # Get change order
        as_of_tstz = sql_cast(func.clock_timestamp(), TIMESTAMP(timezone=True))
        co_stmt = (
            select(ChangeOrder)
            .where(
                ChangeOrder.change_order_id == change_order_id,
                ChangeOrder.branch == "main",
                typing_cast(Any, ChangeOrder).valid_time.op("@>")(as_of_tstz),
                func.lower(typing_cast(Any, ChangeOrder).valid_time) <= as_of_tstz,
                typing_cast(Any, ChangeOrder).deleted_at.is_(None),
            )
            .order_by(typing_cast(Any, ChangeOrder).valid_time.desc())
            .limit(1)
        )
        co_result = await self._db.execute(co_stmt)
        change_order = co_result.scalar_one_or_none()

        if change_order is None:
            raise ValueError(f"Change order {change_order_id} not found")

        project_id = change_order.project_id
        branch_name = f"br-{change_order.code}"

        # Calculate budgets
        main_budget_stmt = select(func.sum(WBE.budget_allocation)).where(
            WBE.project_id == project_id,
            WBE.branch == "main",
            typing_cast(Any, WBE).valid_time.op("@>")(as_of_tstz),
            func.lower(typing_cast(Any, WBE).valid_time) <= as_of_tstz,
            typing_cast(Any, WBE).deleted_at.is_(None),
        )
        main_budget_result = await self._db.execute(main_budget_stmt)
        main_budget = main_budget_result.scalar() or Decimal("0")

        change_budget_stmt = select(func.sum(WBE.budget_allocation)).where(
            WBE.project_id == project_id,
            WBE.branch == branch_name,
            typing_cast(Any, WBE).valid_time.op("@>")(as_of_tstz),
            func.lower(typing_cast(Any, WBE).valid_time) <= as_of_tstz,
            typing_cast(Any, WBE).deleted_at.is_(None),
        )
        change_budget_result = await self._db.execute(change_budget_stmt)
        change_budget = change_budget_result.scalar() or Decimal("0")

        # Calculate revenue impact (if revenue_allocation exists)
        main_revenue_stmt = select(func.sum(WBE.revenue_allocation)).where(
            WBE.project_id == project_id,
            WBE.branch == "main",
            typing_cast(Any, WBE).valid_time.op("@>")(as_of_tstz),
            func.lower(typing_cast(Any, WBE).valid_time) <= as_of_tstz,
            typing_cast(Any, WBE).deleted_at.is_(None),
        )
        main_revenue_result = await self._db.execute(main_revenue_stmt)
        main_revenue = main_revenue_result.scalar() or Decimal("0")

        change_revenue_stmt = select(func.sum(WBE.revenue_allocation)).where(
            WBE.project_id == project_id,
            WBE.branch == branch_name,
            typing_cast(Any, WBE).valid_time.op("@>")(as_of_tstz),
            func.lower(typing_cast(Any, WBE).valid_time) <= as_of_tstz,
            typing_cast(Any, WBE).deleted_at.is_(None),
        )
        change_revenue_result = await self._db.execute(change_revenue_stmt)
        change_revenue = change_revenue_result.scalar() or Decimal("0")

        budget_delta = change_budget - main_budget
        revenue_delta = change_revenue - main_revenue
        impact_level = self._classify_impact_level(abs(budget_delta))

        return {
            "main_budget": float(main_budget),
            "change_budget": float(change_budget),
            "budget_delta": float(budget_delta),
            "main_revenue": float(main_revenue),
            "change_revenue": float(change_revenue),
            "revenue_delta": float(revenue_delta),
            "impact_level": impact_level,
        }
