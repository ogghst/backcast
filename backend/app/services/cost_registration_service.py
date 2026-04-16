"""Cost Registration Service - versionable cost tracking management."""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, cast
from uuid import UUID, uuid4

from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.versioning.commands import (
    CreateVersionCommand,
    SoftDeleteCommand,
    UpdateVersionCommand,
)
from app.core.versioning.enums import BranchMode
from app.core.versioning.service import TemporalService
from app.models.domain.cost_element import CostElement
from app.models.domain.cost_registration import CostRegistration
from app.models.domain.project import Project
from app.models.domain.wbe import WBE
from app.models.schemas.cost_registration import (
    CostRegistrationCreate,
    CostRegistrationUpdate,
)
from app.models.schemas.project_budget_settings import BudgetWarning
from app.services.project_budget_settings_service import (
    ProjectBudgetSettingsService,
)


class BudgetStatus(BaseModel):
    """Budget status for a cost element."""

    cost_element_id: UUID
    budget: Decimal
    used: Decimal
    remaining: Decimal
    percentage: Decimal


class ProjectBudgetStatus(BaseModel):
    """Budget status for a project (aggregated across all cost elements)."""

    project_id: UUID
    project_budget: Decimal
    total_spend: Decimal
    remaining: Decimal
    percentage: Decimal


class CostRegistrationService(TemporalService[CostRegistration]):  # type: ignore[type-var,unused-ignore]
    """Service for Cost Registration management (versionable, not branchable).

    Cost registrations track actual expenditures against cost elements.
    They are versionable (NOT branchable) - costs are global facts.
    """

    def __init__(self, db: AsyncSession):
        """Initialize service with database session.

        Args:
            db: Async database session
        """
        super().__init__(CostRegistration, db)

    async def get_project_budget_status(
        self, project_id: UUID, branch: str = "main"
    ) -> ProjectBudgetStatus:
        """Get project-level budget status (aggregated across all cost elements).

        Calculates total spend across all cost registrations in the project
        and compares against the project's overall budget.

        Args:
            project_id: The project to get status for
            branch: Branch context for queries (defaults to "main")

        Returns:
            ProjectBudgetStatus with project_budget, total_spend, remaining, percentage
        """
        # Get project budget
        project_stmt = select(Project).where(
            Project.project_id == project_id,
            Project.branch == branch,
            func.upper(Project.valid_time).is_(None),
            Project.deleted_at.is_(None),
        )
        project_result = await self.session.execute(project_stmt.limit(1))
        project = project_result.scalar_one_or_none()

        if project is None and branch != "main":
            # Fallback to main branch
            project_stmt_main = select(Project).where(
                Project.project_id == project_id,
                Project.branch == "main",
                func.upper(Project.valid_time).is_(None),
                Project.deleted_at.is_(None),
            )
            project_result_main = await self.session.execute(project_stmt_main.limit(1))
            project = project_result_main.scalar_one_or_none()

        if project is None:
            raise ValueError(f"Project {project_id} not found on branch {branch} or main")

        project_budget = project.budget

        # Calculate total spend across all cost elements in the project
        # Join: Project -> WBE -> CostElement -> CostRegistration
        # Cost registrations are global (not branchable), so we don't need to check multiple branches
        total_spend_stmt = (
            select(func.sum(CostRegistration.amount))
            .join(CostElement, CostRegistration.cost_element_id == CostElement.cost_element_id)
            .join(WBE, CostElement.wbe_id == WBE.wbe_id)
            .where(
                WBE.project_id == project_id,
                func.upper(CostRegistration.valid_time).is_(None),
                CostRegistration.deleted_at.is_(None),
                func.upper(CostElement.valid_time).is_(None),
                CostElement.deleted_at.is_(None),
                func.upper(WBE.valid_time).is_(None),
                WBE.deleted_at.is_(None),
            )
        )

        result = await self.session.execute(total_spend_stmt)
        total_spend = result.scalar_one() or Decimal("0")
        total_spend = Decimal(str(total_spend))

        # Calculate remaining and percentage
        remaining = project_budget - total_spend
        percentage = (total_spend / project_budget * Decimal("100")) if project_budget > 0 else Decimal("0")

        return ProjectBudgetStatus(
            project_id=project_id,
            project_budget=project_budget,
            total_spend=total_spend,
            remaining=remaining,
            percentage=percentage,
        )

    async def validate_budget_status(
        self,
        cost_element_id: UUID,
        project_id: UUID,
        user_id: UUID,
        branch: str = "main",
    ) -> BudgetWarning | None:
        """Validate budget status and return warning if threshold exceeded.

        Checks if the PROJECT's total budget usage exceeds the project's
        warning threshold (aggregated across all cost elements).
        Returns None if no warning needed.

        Args:
            cost_element_id: The cost element being charged (for context)
            project_id: The project context for validation
            user_id: The user making the registration (for admin override check)
            branch: Branch to check budget against (defaults to "main")

        Returns:
            BudgetWarning if project-level threshold exceeded, None otherwise
        """
        # Get project budget settings
        settings_service = ProjectBudgetSettingsService(self.session)
        threshold = await settings_service.get_warning_threshold(project_id)

        # Get PROJECT-level budget status (aggregated across all cost elements)
        project_budget_status = await self.get_project_budget_status(
            project_id=project_id, branch=branch
        )

        # Check if threshold exceeded
        if project_budget_status.percentage < threshold:
            return None

        # Threshold exceeded - create warning
        return BudgetWarning(
            exceeds_threshold=True,
            threshold_percent=threshold,
            current_percent=project_budget_status.percentage,
            message=(
                f"Project budget usage at {project_budget_status.percentage:.1f}% "
                f"exceeds warning threshold of {threshold:.1f}% "
                f"(€{project_budget_status.total_spend:,.2f} of €{project_budget_status.project_budget:,.2f})"
            ),
        )

    async def create_cost_registration(
        self,
        registration_in: CostRegistrationCreate,
        actor_id: UUID,
        branch: str = "main",
        control_date: datetime | None = None,
    ) -> CostRegistration:
        """Create new cost registration using CreateVersionCommand.

        Args:
            registration_in: The cost registration data
            actor_id: The user creating the registration
            control_date: Optional control date for valid_time (defaults to now).
                          Use this for testing time-travel scenarios or data seeding.
            branch: Branch to check budget against (defaults to "main").
                    Cost registrations are global, but budget validation needs a context.
        """
        # Extract control_date from schema if not provided
        if control_date is None:
            control_date = getattr(registration_in, "control_date", None)

        # Dump registration data and exclude control_date (not a model field)
        registration_data = registration_in.model_dump(
            exclude_unset=True,
            exclude={"control_date"},  # Exclude from entity fields
        )

        # Use provided cost_registration_id (for seeding) or generate new one
        root_id = registration_in.cost_registration_id or uuid4()
        registration_data["cost_registration_id"] = root_id

        # Default registration_date to current datetime (control date) if not provided
        if (
            "registration_date" not in registration_data
            or registration_data["registration_date"] is None
        ):
            registration_data["registration_date"] = datetime.now(tz=UTC)

        # CRITICAL: Use control_date for valid_time (defaults to now for production)
        # registration_date is a business field and should NOT affect valid_time
        # This ensures time-travel queries work correctly with as_of parameter
        actual_control_date = control_date

        # 1. Validate Cost Element existence (Application-level Integrity)
        ce_exists = await self.session.execute(
            select(CostElement.id)
            .where(
                CostElement.cost_element_id == registration_in.cost_element_id,
                CostElement.branch == branch,
                func.upper(cast(Any, CostElement).valid_time).is_(None),
                cast(Any, CostElement).deleted_at.is_(None),
            )
            .limit(1)
        )
        if not ce_exists.scalar_one_or_none():
            # Fallback to main branch
            ce_exists_main = await self.session.execute(
                select(CostElement.id)
                .where(
                    CostElement.cost_element_id == registration_in.cost_element_id,
                    CostElement.branch == "main",
                    func.upper(cast(Any, CostElement).valid_time).is_(None),
                    cast(Any, CostElement).deleted_at.is_(None),
                )
                .limit(1)
            )
            if not ce_exists_main.scalar_one_or_none():
                raise ValueError(
                    f"Cost Element {registration_in.cost_element_id} not found on branch {branch} or main"
                )

        # Get Cost Element to validate budget and fetch project_id
        ce_stmt = select(CostElement).where(
            CostElement.cost_element_id == registration_in.cost_element_id,
            CostElement.branch == branch,
            func.upper(cast(Any, CostElement).valid_time).is_(None),
            cast(Any, CostElement).deleted_at.is_(None),
        )
        ce_result = await self.session.execute(ce_stmt.limit(1))
        cost_element = ce_result.scalar_one_or_none()

        if cost_element is None and branch != "main":
            # Fallback to main branch
            ce_stmt_main = select(CostElement).where(
                CostElement.cost_element_id == registration_in.cost_element_id,
                CostElement.branch == "main",
                func.upper(cast(Any, CostElement).valid_time).is_(None),
                cast(Any, CostElement).deleted_at.is_(None),
            )
            ce_result_main = await self.session.execute(ce_stmt_main.limit(1))
            cost_element = ce_result_main.scalar_one_or_none()

        if cost_element is None:
            raise ValueError(
                f"Cost Element {registration_in.cost_element_id} not found on branch {branch} or main"
            )

        # Get WBE to fetch project_id for budget validation
        wbe_stmt = select(WBE).where(
            WBE.wbe_id == cost_element.wbe_id,
            WBE.branch == branch,
            func.upper(cast(Any, WBE).valid_time).is_(None),
            cast(Any, WBE).deleted_at.is_(None),
        )
        wbe_result = await self.session.execute(wbe_stmt.limit(1))
        wbe = wbe_result.scalar_one_or_none()

        if wbe is None and branch != "main":
            # Fallback to main branch
            wbe_stmt_main = select(WBE).where(
                WBE.wbe_id == cost_element.wbe_id,
                WBE.branch == "main",
                func.upper(cast(Any, WBE).valid_time).is_(None),
                cast(Any, WBE).deleted_at.is_(None),
            )
            wbe_result_main = await self.session.execute(wbe_stmt_main.limit(1))
            wbe = wbe_result_main.scalar_one_or_none()

        if wbe is None:
            raise ValueError(
                f"WBE {cost_element.wbe_id} not found on branch {branch} or main"
            )

        # Create the cost registration (budget validation is non-blocking)
        # The warning will be included in the response via the API layer
        cmd = CreateVersionCommand(
            entity_class=CostRegistration,  # type: ignore[type-var,unused-ignore]
            root_id=root_id,
            actor_id=actor_id,
            control_date=actual_control_date,
            **registration_data,
        )
        return await cmd.execute(self.session)

    async def update_cost_registration(
        self,
        cost_registration_id: UUID,
        registration_in: CostRegistrationUpdate,
        actor_id: UUID,
        control_date: datetime | None = None,
    ) -> CostRegistration:
        """Update cost registration using UpdateVersionCommand.

        Args:
            cost_registration_id: The cost registration to update
            registration_in: The update data
            actor_id: The user making the update
            control_date: Optional control date for valid_time (defaults to now)
        """
        # Extract control_date from schema if not provided
        if control_date is None:
            control_date = getattr(registration_in, "control_date", None)

        # Dump update data and exclude control_date (not a model field)
        update_data = registration_in.model_dump(
            exclude_unset=True,
            exclude={"control_date"},  # Exclude from entity fields
        )

        # Custom command class to handle multi-word entity name
        class CostRegistrationUpdateCommand(UpdateVersionCommand[CostRegistration]):  # type: ignore[type-var,unused-ignore]
            def _root_field_name(self) -> str:
                return "cost_registration_id"

        cmd = CostRegistrationUpdateCommand(
            entity_class=CostRegistration,  # type: ignore[type-var,unused-ignore]
            root_id=cost_registration_id,
            actor_id=actor_id,
            control_date=control_date,
            **update_data,
        )
        return await cmd.execute(self.session)

    async def soft_delete(
        self,
        cost_registration_id: UUID,
        actor_id: UUID,
        control_date: datetime | None = None,
    ) -> None:
        """Soft delete cost registration using SoftDeleteCommand."""

        class CostRegistrationSoftDeleteCommand(SoftDeleteCommand[CostRegistration]):  # type: ignore[type-var,unused-ignore]
            def _root_field_name(self) -> str:
                return "cost_registration_id"

        cmd = CostRegistrationSoftDeleteCommand(
            entity_class=CostRegistration,  # type: ignore[type-var,unused-ignore]
            root_id=cost_registration_id,
            actor_id=actor_id,
            control_date=control_date,
        )
        await cmd.execute(self.session)

    async def get_by_id(self, cost_registration_id: UUID) -> CostRegistration | None:
        """Get current cost registration by root ID."""
        stmt = (
            select(CostRegistration)
            .where(
                CostRegistration.cost_registration_id == cost_registration_id,
                func.upper(CostRegistration.valid_time).is_(None),
                CostRegistration.deleted_at.is_(None),
            )
            .order_by(CostRegistration.valid_time.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_cost_registrations(
        self,
        filters: dict[str, Any] | None = None,
        skip: int = 0,
        limit: int = 100,
        as_of: datetime | None = None,
        wbe_id: UUID | None = None,
        project_id: UUID | None = None,
    ) -> tuple[list[CostRegistration], int]:
        """Get cost registrations with filtering, pagination, and time-travel support.

        Args:
            filters: Optional filters dict (e.g., {"cost_element_id": UUID})
            skip: Number of records to skip (for pagination)
            limit: Maximum number of records to return
            as_of: Optional timestamp for time-travel query (Valid Time Travel semantics)
            wbe_id: Optional WBE root ID to filter by (joins through CostElement)
            project_id: Optional Project root ID to filter by (joins through CostElement -> WBE)

        Returns:
            Tuple of (list of cost registrations, total count)
        """
        # Build base query
        stmt = select(CostRegistration).where(
            CostRegistration.cost_element_id.isnot(None)
        )

        # FIX: Use standardized bitemporal filter instead of custom implementation
        # The custom filter was missing:
        # - func.lower(valid_time) <= as_of (prevents future entities from being included)
        # - TIMESTAMP casting (ensures proper timezone handling)
        if as_of is not None:
            stmt = self._apply_bitemporal_filter(stmt, as_of)
        else:
            stmt = stmt.where(func.upper(CostRegistration.valid_time).is_(None))
            stmt = stmt.where(CostRegistration.deleted_at.is_(None))

        # Apply filters
        if filters:
            if "cost_element_id" in filters:
                stmt = stmt.where(
                    CostRegistration.cost_element_id == filters["cost_element_id"]
                )

        # Join through CostElement to filter by WBE
        if wbe_id is not None:
            ce_subq = (
                select(CostElement.cost_element_id)
                .where(
                    CostElement.wbe_id == wbe_id,
                    func.upper(cast(Any, CostElement).valid_time).is_(None),
                    cast(Any, CostElement).deleted_at.is_(None),
                )
                .correlate(CostRegistration)
            )
            stmt = stmt.where(
                CostRegistration.cost_element_id.in_(ce_subq)
            )

        # Join through CostElement -> WBE to filter by Project
        if project_id is not None:
            wbe_subq = (
                select(CostElement.cost_element_id)
                .join(WBE, CostElement.wbe_id == WBE.wbe_id)
                .where(
                    WBE.project_id == project_id,
                    func.upper(cast(Any, CostElement).valid_time).is_(None),
                    cast(Any, CostElement).deleted_at.is_(None),
                    func.upper(cast(Any, WBE).valid_time).is_(None),
                    cast(Any, WBE).deleted_at.is_(None),
                )
                .correlate(CostRegistration)
            )
            stmt = stmt.where(
                CostRegistration.cost_element_id.in_(wbe_subq)
            )

        # Get total count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar_one()

        # Apply default sorting and pagination
        stmt = stmt.order_by(CostRegistration.registration_date.desc())
        stmt = stmt.offset(skip).limit(limit)

        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    async def get_total_for_cost_element(
        self, cost_element_id: UUID, as_of: datetime | None = None
    ) -> Any:  # Return Decimal for sum
        """Calculate total costs for a cost element (time-travel aware).

        Args:
            cost_element_id: The cost element to sum costs for
            as_of: Optional timestamp for historical query (time-travel)

        Returns:
            Sum of all cost registrations for the cost element

        Example:
            >>> # Get current total
            >>> total = await service.get_total_for_cost_element(cost_element_id)
            >>>
            >>> # Get total as of specific date
            >>> from datetime import datetime
            >>> as_of = datetime(2026, 1, 1, 12, 0, 0)
            >>> historical_total = await service.get_total_for_cost_element(
            ...     cost_element_id, as_of=as_of
            ... )
        """
        # Build query for time-travel support
        stmt = select(func.sum(CostRegistration.amount)).where(
            CostRegistration.cost_element_id == cost_element_id,
        )

        # FIX: Use standardized bitemporal filter instead of custom implementation
        # The custom filter was missing:
        # - func.lower(valid_time) <= as_of (prevents future entities from being included)
        # - TIMESTAMP casting (ensures proper timezone handling)
        if as_of is not None:
            stmt = self._apply_bitemporal_filter(stmt, as_of)
        else:
            stmt = stmt.where(func.upper(CostRegistration.valid_time).is_(None))
            stmt = stmt.where(CostRegistration.deleted_at.is_(None))

        result = await self.session.execute(stmt)
        return result.scalar_one() or 0

    async def get_cost_registration_as_of(
        self,
        cost_registration_id: UUID,
        as_of: datetime,
        branch: str = "main",
        branch_mode: BranchMode | None = None,
    ) -> CostRegistration | None:
        """Get cost registration as it was at specific timestamp.

        Provides Business Time Travel semantics (valid_time only) for cost registrations.
        Uses standardized bitemporal filter for temporal queries.

        Args:
            cost_registration_id: The unique identifier of the cost registration
            as_of: Timestamp to query (historical state based on valid_time)
            branch: Branch name to query (always "main" for non-branchable entities)
            branch_mode: Resolution mode for branches (not applicable, kept for interface consistency)

        Returns:
            CostRegistration if found at the specified timestamp, None otherwise
        """
        # Build base query
        stmt = select(CostRegistration).where(
            CostRegistration.cost_registration_id == cost_registration_id,
        )

        # Apply standardized bitemporal filter (Valid Time Travel semantics)
        stmt = self._apply_bitemporal_filter(stmt, as_of)

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_budget_status(
        self, cost_element_id: UUID, as_of: datetime | None = None, branch: str = "main"
    ) -> BudgetStatus:
        """Get budget status for a cost element with time-travel support.

        Returns budget, used, remaining, and percentage used.
        Respects time-travel queries via the as_of parameter for Valid Time Travel.

        Args:
            cost_element_id: The cost element to get status for
            as_of: Optional timestamp for time-travel query (historical view)
            branch: Branch context to resolve Cost Element budget (defaults to "main")

        Returns:
            BudgetStatus with budget, used, remaining, percentage
        """
        # Get the cost element's budget (current budget, not time-traveled)
        # Note: CostElement budget itself could be time-traveled in future iterations
        stmt = select(CostElement).where(
            CostElement.cost_element_id == cost_element_id,
            CostElement.branch == branch,
            func.upper(CostElement.valid_time).is_(None),
            CostElement.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        cost_element = result.scalar_one_or_none()

        if cost_element is None and branch != "main":
            # Fallback to main branch
            stmt_main = select(CostElement).where(
                CostElement.cost_element_id == cost_element_id,
                CostElement.branch == "main",
                func.upper(CostElement.valid_time).is_(None),
                CostElement.deleted_at.is_(None),
            )
            result_main = await self.session.execute(stmt_main)
            cost_element = result_main.scalar_one_or_none()

        if cost_element is None:
            raise ValueError(
                f"Cost element {cost_element_id} not found on branch {branch} or main"
            )

        budget = cost_element.budget_amount

        # Get total costs for this cost element (time-travel aware)
        used = await self.get_total_for_cost_element(cost_element_id, as_of=as_of)
        used = Decimal(str(used)) if used else Decimal("0")

        # Calculate remaining and percentage
        remaining = budget - used
        percentage = (used / budget * Decimal("100")) if budget > 0 else Decimal("0")

        return BudgetStatus(
            cost_element_id=cost_element_id,
            budget=budget,
            used=used,
            remaining=remaining,
            percentage=percentage,
        )

    async def get_costs_by_period(
        self,
        cost_element_id: UUID,
        period: str,  # "daily", "weekly", "monthly"
        start_date: datetime,
        end_date: datetime | None = None,
        as_of: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """Get cost aggregations by time period.

        Args:
            cost_element_id: The cost element to aggregate costs for
            period: Period type ("daily", "weekly", "monthly")
            start_date: Start date for aggregation
            end_date: End date for aggregation (defaults to now)
            as_of: Optional timestamp for time-travel query

        Returns:
            List of dicts with period_start and total_amount

        Example:
            >>> costs = await service.get_costs_by_period(
            ...     cost_element_id,
            ...     period="weekly",
            ...     start_date=datetime(2026, 1, 1),
            ...     end_date=datetime(2026, 1, 31)
            ... )
            >>> # Returns: [
            ... #   {"period_start": "2026-01-01", "total_amount": 1500.00},
            ... #   {"period_start": "2026-01-08", "total_amount": 2000.00},
            ... #   ...
            ... # ]
        """
        if end_date is None:
            end_date = datetime.now(tz=UTC)

        # Map API period names to PostgreSQL date_trunc units
        # API uses: "daily", "weekly", "monthly"
        # PostgreSQL expects: "day", "week", "month"
        period_mapping = {
            "daily": "day",
            "weekly": "week",
            "monthly": "month",
        }
        pg_period = period_mapping.get(period, period)

        # Build base query with time-travel support
        stmt = select(
            func.date_trunc(pg_period, CostRegistration.registration_date).label(
                "period_start"
            ),
            func.sum(CostRegistration.amount).label("total_amount"),
        ).where(
            CostRegistration.cost_element_id == cost_element_id,
            CostRegistration.registration_date >= start_date,
            CostRegistration.registration_date <= end_date,
        )

        # FIX: Use standardized bitemporal filter instead of custom implementation
        # The custom filter was missing:
        # - func.lower(valid_time) <= as_of (prevents future entities from being included)
        # - TIMESTAMP casting (ensures proper timezone handling)
        if as_of is not None:
            stmt = self._apply_bitemporal_filter(stmt, as_of)
        else:
            stmt = stmt.where(func.upper(CostRegistration.valid_time).is_(None))
            stmt = stmt.where(CostRegistration.deleted_at.is_(None))

        # Group by period and order
        stmt = stmt.group_by("period_start").order_by("period_start")

        result = await self.session.execute(stmt)
        return [
            {
                "period_start": row.period_start.isoformat(),
                "total_amount": float(row.total_amount),
            }
            for row in result.all()
        ]

    async def get_cumulative_costs(
        self,
        cost_element_id: UUID,
        start_date: datetime,
        end_date: datetime | None = None,
        as_of: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """Get cumulative costs over time.

        Args:
            cost_element_id: The cost element to get cumulative costs for
            start_date: Start date for calculation
            end_date: End date for calculation (defaults to now)
            as_of: Optional timestamp for time-travel query

        Returns:
            List of dicts with registration_date and cumulative_amount
        """
        if end_date is None:
            end_date = datetime.now(tz=UTC)

        # Build base query with time-travel support
        stmt = select(
            CostRegistration.registration_date,
            CostRegistration.amount,
        ).where(
            CostRegistration.cost_element_id == cost_element_id,
            CostRegistration.registration_date >= start_date,
            CostRegistration.registration_date <= end_date,
        )

        # FIX: Use standardized bitemporal filter instead of custom implementation
        # The custom filter was missing:
        # - func.lower(valid_time) <= as_of (prevents future entities from being included)
        # - TIMESTAMP casting (ensures proper timezone handling)
        if as_of is not None:
            stmt = self._apply_bitemporal_filter(stmt, as_of)
        else:
            stmt = stmt.where(func.upper(CostRegistration.valid_time).is_(None))
            stmt = stmt.where(CostRegistration.deleted_at.is_(None))

        # Order by date for cumulative calculation
        stmt = stmt.order_by(CostRegistration.registration_date)

        # Execute query
        result = await self.session.execute(stmt)
        rows = result.all()

        # Calculate cumulative sum
        cumulative_amount = Decimal("0")
        cumulative_costs = []
        for row in rows:
            cumulative_amount += row.amount
            cumulative_costs.append(
                {
                    "registration_date": row.registration_date.isoformat(),
                    "amount": float(row.amount),
                    "cumulative_amount": float(cumulative_amount),
                }
            )

        return cumulative_costs

    async def get_cumulative_costs_batch(
        self,
        cost_element_ids: list[UUID],
        start_date: datetime,
        end_date: datetime | None = None,
        as_of: datetime | None = None,
    ) -> dict[UUID, list[dict[str, Any]]]:
        """Get cumulative costs over time for multiple cost elements.

        Batch version of get_cumulative_costs that fetches all cost
        registrations in a single query instead of N individual queries.

        Args:
            cost_element_ids: List of cost element UUIDs to query
            start_date: Start date for calculation
            end_date: End date for calculation (defaults to now)
            as_of: Optional timestamp for time-travel query

        Returns:
            Dictionary mapping each cost_element_id to its cumulative
            costs list (same format as get_cumulative_costs).
        """
        if not cost_element_ids:
            return {}

        if end_date is None:
            end_date = datetime.now(tz=UTC)

        # Build batch query with time-travel support
        stmt = select(
            CostRegistration.cost_element_id,
            CostRegistration.registration_date,
            CostRegistration.amount,
        ).where(
            CostRegistration.cost_element_id.in_(cost_element_ids),
            CostRegistration.registration_date >= start_date,
            CostRegistration.registration_date <= end_date,
        )

        # Apply bitemporal filter
        if as_of is not None:
            stmt = self._apply_bitemporal_filter(stmt, as_of)
        else:
            stmt = stmt.where(func.upper(CostRegistration.valid_time).is_(None))
            stmt = stmt.where(CostRegistration.deleted_at.is_(None))

        # Order by cost element then date for grouped cumulative calc
        stmt = stmt.order_by(
            CostRegistration.cost_element_id,
            CostRegistration.registration_date,
        )

        result = await self.session.execute(stmt)
        rows = result.all()

        # Group rows by cost_element_id preserving insertion order
        grouped: dict[UUID, list[Any]] = {}
        for row in rows:
            grouped.setdefault(row.cost_element_id, []).append(row)

        # Calculate cumulative sum per cost element
        batch_result: dict[UUID, list[dict[str, Any]]] = {}
        for ce_id in cost_element_ids:
            ce_rows = grouped.get(ce_id, [])
            cumulative_amount = Decimal("0")
            costs: list[dict[str, Any]] = []
            for row in ce_rows:
                cumulative_amount += row.amount
                costs.append(
                    {
                        "registration_date": row.registration_date.isoformat(),
                        "amount": float(row.amount),
                        "cumulative_amount": float(cumulative_amount),
                    }
                )
            batch_result[ce_id] = costs

        return batch_result

    async def _get_costs_by_period_for_ces(
        self,
        ce_ids: list[UUID],
        period: str,
        start_date: datetime,
        end_date: datetime | None = None,
        as_of: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """Batch version of get_costs_by_period for multiple cost elements.

        Uses IN clause + date_trunc + sum to aggregate across all CEs
        in a single query instead of N sequential queries.
        """
        if not ce_ids:
            return []

        if end_date is None:
            end_date = datetime.now(tz=UTC)

        period_mapping = {"daily": "day", "weekly": "week", "monthly": "month"}
        pg_period = period_mapping.get(period, period)

        stmt = select(
            func.date_trunc(pg_period, CostRegistration.registration_date).label(
                "period_start"
            ),
            func.sum(CostRegistration.amount).label("total_amount"),
        ).where(
            CostRegistration.cost_element_id.in_(ce_ids),
            CostRegistration.registration_date >= start_date,
            CostRegistration.registration_date <= end_date,
        )

        if as_of is not None:
            stmt = self._apply_bitemporal_filter(stmt, as_of)
        else:
            stmt = stmt.where(func.upper(CostRegistration.valid_time).is_(None))
            stmt = stmt.where(CostRegistration.deleted_at.is_(None))

        stmt = stmt.group_by("period_start").order_by("period_start")

        result = await self.session.execute(stmt)
        return [
            {
                "period_start": row.period_start.isoformat(),
                "total_amount": float(row.total_amount),
            }
            for row in result.all()
        ]

    async def _resolve_cost_element_ids(
        self, entity_type: str, entity_id: UUID
    ) -> list[UUID]:
        """Resolve WBE or project ID to child cost element root IDs.

        Args:
            entity_type: "wbe" or "project"
            entity_id: Root ID of the WBE or project

        Returns:
            List of cost_element_id root UUIDs (current, non-deleted versions only).
        """
        if entity_type == "wbe":
            stmt = select(CostElement.cost_element_id).where(
                CostElement.wbe_id == entity_id,
                func.upper(cast(Any, CostElement).valid_time).is_(None),
                cast(Any, CostElement).deleted_at.is_(None),
            )
        elif entity_type == "project":
            stmt = (
                select(CostElement.cost_element_id)
                .join(WBE, CostElement.wbe_id == WBE.wbe_id)
                .where(
                    WBE.project_id == entity_id,
                    func.upper(cast(Any, CostElement).valid_time).is_(None),
                    cast(Any, CostElement).deleted_at.is_(None),
                    func.upper(cast(Any, WBE).valid_time).is_(None),
                    cast(Any, WBE).deleted_at.is_(None),
                )
            )
        else:
            raise ValueError(
                f"Unsupported entity_type '{entity_type}' for cost element resolution"
            )

        result = await self.session.execute(stmt)
        return [row.cost_element_id for row in result.all()]

    async def get_aggregated_costs_by_entity(
        self,
        entity_type: str,
        entity_id: UUID,
        period: str,
        start_date: datetime,
        end_date: datetime | None = None,
        as_of: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """Get cost aggregations by time period for a cost element, WBE, or project.

        For WBE/project, resolves child cost elements, fetches aggregated costs
        per CE, then merges by period_start (summing total_amounts).

        Args:
            entity_type: "cost_element", "wbe", or "project"
            entity_id: Root ID of the entity
            period: Period type ("daily", "weekly", "monthly")
            start_date: Start date for aggregation
            end_date: End date for aggregation (defaults to now)
            as_of: Optional timestamp for time-travel query

        Returns:
            List of dicts with period_start and total_amount, sorted by period_start.
        """
        if entity_type == "cost_element":
            return await self.get_costs_by_period(
                cost_element_id=entity_id,
                period=period,
                start_date=start_date,
                end_date=end_date,
                as_of=as_of,
            )

        # Resolve to cost element IDs
        ce_ids = await self._resolve_cost_element_ids(entity_type, entity_id)
        if not ce_ids:
            return []

        # Single batch query — date_trunc + sum with IN clause merges across
        # all CEs in one round-trip (no N+1).
        return await self._get_costs_by_period_for_ces(
            ce_ids=ce_ids,
            period=period,
            start_date=start_date,
            end_date=end_date,
            as_of=as_of,
        )

    async def get_cumulative_costs_by_entity(
        self,
        entity_type: str,
        entity_id: UUID,
        start_date: datetime,
        end_date: datetime | None = None,
        as_of: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """Get cumulative costs over time for a cost element, WBE, or project.

        For WBE/project, resolves child cost elements, uses the batch method,
        then merges all series into one sorted by date (summing amounts at the
        same date and recalculating cumulative totals).

        Args:
            entity_type: "cost_element", "wbe", or "project"
            entity_id: Root ID of the entity
            start_date: Start date for calculation
            end_date: End date for calculation (defaults to now)
            as_of: Optional timestamp for time-travel query

        Returns:
            List of dicts with registration_date, amount, and cumulative_amount.
        """
        if entity_type == "cost_element":
            return await self.get_cumulative_costs(
                cost_element_id=entity_id,
                start_date=start_date,
                end_date=end_date,
                as_of=as_of,
            )

        # Resolve to cost element IDs and use batch method
        ce_ids = await self._resolve_cost_element_ids(entity_type, entity_id)
        if not ce_ids:
            return []

        batch_result = await self.get_cumulative_costs_batch(
            cost_element_ids=ce_ids,
            start_date=start_date,
            end_date=end_date,
            as_of=as_of,
        )

        # Merge all series: sum amounts at same date
        merged: dict[str, float] = {}
        for _ce_id, entries in batch_result.items():
            for entry in entries:
                key = entry["registration_date"]
                merged[key] = merged.get(key, 0.0) + entry["amount"]

        # Sort by date and recalculate cumulative
        cumulative_amount = Decimal("0")
        result: list[dict[str, Any]] = []
        for date_key in sorted(merged.keys()):
            amount = merged[date_key]
            cumulative_amount += Decimal(str(amount))
            result.append(
                {
                    "registration_date": date_key,
                    "amount": amount,
                    "cumulative_amount": float(cumulative_amount),
                }
            )

        return result

    async def get_totals_for_cost_elements(
        self,
        cost_element_ids: list[UUID],
        as_of: datetime | None = None,
    ) -> dict[UUID, Decimal]:
        """Calculate total costs for multiple cost elements efficiently.

        Args:
            cost_element_ids: List of cost element UUIDs
            as_of: Optional timestamp for historical query (time-travel)

        Returns:
            Dictionary mapping cost_element_id to total cost (Decimal)
        """
        if not cost_element_ids:
            return {}

        stmt = (
            select(
                CostRegistration.cost_element_id,
                func.sum(CostRegistration.amount).label("total"),
            )
            .where(CostRegistration.cost_element_id.in_(cost_element_ids))
            .group_by(CostRegistration.cost_element_id)
        )

        # Apply time-travel filter
        if as_of is not None:
            stmt = self._apply_bitemporal_filter(stmt, as_of)
        else:
            stmt = stmt.where(func.upper(CostRegistration.valid_time).is_(None))
            stmt = stmt.where(CostRegistration.deleted_at.is_(None))

        result = await self.session.execute(stmt)

        totals = {id: Decimal("0.00") for id in cost_element_ids}
        for row in result.all():
            totals[row.cost_element_id] = row.total or Decimal("0.00")

        return totals
