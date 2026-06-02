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

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain.change_order import ChangeOrder
from app.models.domain.control_account import ControlAccount
from app.models.domain.work_package import WorkPackage

if TYPE_CHECKING:
    from app.services.change_order_config_service import ChangeOrderConfigService


class FinancialImpactService:
    """Service for calculating financial impact levels for change orders.

    Calculates financial impact by comparing budgets between main branch
    and change order branch. Classifies impact level according to configurable
    thresholds from the workflow configuration service.
    """

    def __init__(
        self,
        db_session: AsyncSession,
        config_service: ChangeOrderConfigService | None = None,
    ) -> None:
        """Initialize the service with a database session.

        Args:
            db_session: Async database session for queries
            config_service: Optional config service for threshold lookup.
                If not provided, thresholds will be fetched on demand.
        """
        self._db = db_session
        self._config_service = config_service

    async def calculate_impact_level(self, change_order_id: UUID) -> str:
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

        from app.models.domain.wbs_element import WBSElement

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
        branch_name = f"BR-{change_order.code}"

        # Calculate total budget from main branch using WorkPackage budgets
        main_budget_stmt = (
            select(func.sum(WorkPackage.budget_amount))
            .select_from(WorkPackage)
            .join(
                ControlAccount,
                WorkPackage.control_account_id == ControlAccount.control_account_id,
            )
            .join(
                WBSElement, ControlAccount.wbs_element_id == WBSElement.wbs_element_id
            )
            .where(
                WBSElement.project_id == project_id,
                WorkPackage.branch == "main",
                ControlAccount.branch == "main",
                WBSElement.branch == "main",
                typing_cast(Any, WorkPackage).valid_time.op("@>")(as_of_tstz),
                func.lower(typing_cast(Any, WorkPackage).valid_time) <= as_of_tstz,
                typing_cast(Any, WorkPackage).deleted_at.is_(None),
                typing_cast(Any, ControlAccount).deleted_at.is_(None),
                typing_cast(Any, WBSElement).deleted_at.is_(None),
            )
        )
        main_budget_result = await self._db.execute(main_budget_stmt)
        main_budget = main_budget_result.scalar() or Decimal("0")

        # Calculate total budget from change branch using WorkPackage budgets
        change_budget_stmt = (
            select(func.sum(WorkPackage.budget_amount))
            .select_from(WorkPackage)
            .join(
                ControlAccount,
                WorkPackage.control_account_id == ControlAccount.control_account_id,
            )
            .join(
                WBSElement, ControlAccount.wbs_element_id == WBSElement.wbs_element_id
            )
            .where(
                WBSElement.project_id == project_id,
                WorkPackage.branch == branch_name,
                ControlAccount.branch == branch_name,
                WBSElement.branch == branch_name,
                typing_cast(Any, WorkPackage).valid_time.op("@>")(as_of_tstz),
                func.lower(typing_cast(Any, WorkPackage).valid_time) <= as_of_tstz,
                typing_cast(Any, WorkPackage).deleted_at.is_(None),
                typing_cast(Any, ControlAccount).deleted_at.is_(None),
                typing_cast(Any, WBSElement).deleted_at.is_(None),
            )
        )
        change_budget_result = await self._db.execute(change_budget_stmt)
        change_budget = change_budget_result.scalar() or Decimal("0")

        # Calculate absolute budget delta
        budget_delta = abs(change_budget - main_budget)

        # Classify impact level based on configurable thresholds
        return await self._classify_impact_level(budget_delta)

    async def _classify_impact_level(self, budget_delta: Decimal) -> str:
        """Classify financial impact level based on budget delta.

        Reads thresholds from the workflow configuration service.

        Args:
            budget_delta: Absolute budget change amount (EUR)

        Returns:
            Impact level string: LOW, MEDIUM, HIGH, or CRITICAL
        """
        from app.services.change_order_config_service import (
            ChangeOrderConfigService,
        )

        if self._config_service is not None:
            thresholds = await self._config_service.get_thresholds()
            return self._config_service.classify_financial_impact(
                budget_delta, thresholds
            )

        # Fallback: create a temporary config service for this session
        config_service = ChangeOrderConfigService(self._db)
        thresholds = await config_service.get_thresholds()
        return config_service.classify_financial_impact(budget_delta, thresholds)

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

        from app.models.domain.wbs_element import WBSElement

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
        branch_name = f"BR-{change_order.code}"

        # Calculate budgets using WorkPackage.budget_amount
        main_budget_stmt = (
            select(func.sum(WorkPackage.budget_amount))
            .select_from(WorkPackage)
            .join(
                ControlAccount,
                WorkPackage.control_account_id == ControlAccount.control_account_id,
            )
            .join(
                WBSElement, ControlAccount.wbs_element_id == WBSElement.wbs_element_id
            )
            .where(
                WBSElement.project_id == project_id,
                WorkPackage.branch == "main",
                ControlAccount.branch == "main",
                WBSElement.branch == "main",
                typing_cast(Any, WorkPackage).valid_time.op("@>")(as_of_tstz),
                func.lower(typing_cast(Any, WorkPackage).valid_time) <= as_of_tstz,
                typing_cast(Any, WorkPackage).deleted_at.is_(None),
                typing_cast(Any, ControlAccount).deleted_at.is_(None),
                typing_cast(Any, WBSElement).deleted_at.is_(None),
            )
        )
        main_budget_result = await self._db.execute(main_budget_stmt)
        main_budget = main_budget_result.scalar() or Decimal("0")

        change_budget_stmt = (
            select(func.sum(WorkPackage.budget_amount))
            .select_from(WorkPackage)
            .join(
                ControlAccount,
                WorkPackage.control_account_id == ControlAccount.control_account_id,
            )
            .join(
                WBSElement, ControlAccount.wbs_element_id == WBSElement.wbs_element_id
            )
            .where(
                WBSElement.project_id == project_id,
                WorkPackage.branch == branch_name,
                ControlAccount.branch == branch_name,
                WBSElement.branch == branch_name,
                typing_cast(Any, WorkPackage).valid_time.op("@>")(as_of_tstz),
                func.lower(typing_cast(Any, WorkPackage).valid_time) <= as_of_tstz,
                typing_cast(Any, WorkPackage).deleted_at.is_(None),
                typing_cast(Any, ControlAccount).deleted_at.is_(None),
                typing_cast(Any, WBSElement).deleted_at.is_(None),
            )
        )
        change_budget_result = await self._db.execute(change_budget_stmt)
        change_budget = change_budget_result.scalar() or Decimal("0")

        # Calculate revenue impact (if revenue_allocation exists)
        main_revenue_stmt = select(func.sum(WBSElement.revenue_allocation)).where(
            WBSElement.project_id == project_id,
            WBSElement.branch == "main",
            typing_cast(Any, WBSElement).valid_time.op("@>")(as_of_tstz),
            func.lower(typing_cast(Any, WBSElement).valid_time) <= as_of_tstz,
            typing_cast(Any, WBSElement).deleted_at.is_(None),
        )
        main_revenue_result = await self._db.execute(main_revenue_stmt)
        main_revenue = main_revenue_result.scalar() or Decimal("0")

        change_revenue_stmt = select(func.sum(WBSElement.revenue_allocation)).where(
            WBSElement.project_id == project_id,
            WBSElement.branch == branch_name,
            typing_cast(Any, WBSElement).valid_time.op("@>")(as_of_tstz),
            func.lower(typing_cast(Any, WBSElement).valid_time) <= as_of_tstz,
            typing_cast(Any, WBSElement).deleted_at.is_(None),
        )
        change_revenue_result = await self._db.execute(change_revenue_stmt)
        change_revenue = change_revenue_result.scalar() or Decimal("0")

        budget_delta = change_budget - main_budget
        revenue_delta = change_revenue - main_revenue
        impact_level = await self._classify_impact_level(abs(budget_delta))

        return {
            "main_budget": float(main_budget),
            "change_budget": float(change_budget),
            "budget_delta": float(budget_delta),
            "main_revenue": float(main_revenue),
            "change_revenue": float(change_revenue),
            "revenue_delta": float(revenue_delta),
            "impact_level": impact_level,
        }
