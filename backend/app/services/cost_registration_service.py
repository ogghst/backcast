"""Cost Registration Service - versionable cost tracking management."""

from datetime import datetime
from decimal import Decimal
from typing import Any
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
from app.models.schemas.cost_registration import (
    CostRegistrationCreate,
    CostRegistrationUpdate,
)


class BudgetExceededError(Exception):
    """Raised when cost registration would exceed cost element budget.

    Attributes:
        budget: The budget amount for the cost element
        used: The current total used amount
        requested: The amount being requested to add
    """

    def __init__(self, budget: Decimal, used: Decimal, requested: Decimal) -> None:
        self.budget = budget
        self.used = used
        self.requested = requested
        super().__init__(
            f"Budget exceeded: budget={budget}, used={used}, requested={requested}"
        )


class BudgetStatus(BaseModel):
    """Budget status for a cost element."""

    cost_element_id: UUID
    budget: Decimal
    used: Decimal
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

    async def create(  # type: ignore[override]
        self, registration_in: CostRegistrationCreate, actor_id: UUID
    ) -> CostRegistration:
        """Create new cost registration using CreateVersionCommand."""
        registration_data = registration_in.model_dump(exclude_unset=True)

        # Use provided cost_registration_id (for seeding) or generate new one
        root_id = registration_in.cost_registration_id or uuid4()
        registration_data["cost_registration_id"] = root_id

        # Default registration_date to current datetime (control date) if not provided
        if (
            "registration_date" not in registration_data
            or registration_data["registration_date"] is None
        ):
            registration_data["registration_date"] = datetime.now()

        # Budget validation
        cost_element_id = registration_in.cost_element_id
        new_amount = registration_data.get("amount", Decimal("0"))

        # Get current total for the cost element
        current_total = await self.get_total_for_cost_element(cost_element_id)
        current_total = Decimal(str(current_total)) if current_total else Decimal("0")

        # Get the cost element's budget
        stmt = select(CostElement).where(
            CostElement.cost_element_id == cost_element_id,
            func.upper(CostElement.valid_time).is_(None),
            CostElement.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        cost_element = result.scalar_one_or_none()

        if cost_element is not None:
            budget = cost_element.budget_amount
            # Check if budget would be exceeded
            if current_total + new_amount > budget:
                raise BudgetExceededError(
                    budget=budget,
                    used=current_total,
                    requested=new_amount,
                )

        # CRITICAL: Use registration_date as control_date for proper time travel
        # This ensures valid_time starts from the business date (registration_date)
        # not from the system timestamp when the record was created
        control_date = registration_data.get("registration_date", datetime.now())

        cmd = CreateVersionCommand(
            entity_class=CostRegistration,  # type: ignore[type-var,unused-ignore]
            root_id=root_id,
            actor_id=actor_id,
            control_date=control_date,
            **registration_data,
        )
        return await cmd.execute(self.session)

    async def update(  # type: ignore[override]
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
        update_data = registration_in.model_dump(exclude_unset=True)

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
    ) -> tuple[list[CostRegistration], int]:
        """Get cost registrations with filtering and pagination."""
        stmt = select(CostRegistration).where(
            func.upper(CostRegistration.valid_time).is_(None),
            CostRegistration.deleted_at.is_(None),
        )

        # Apply filters
        if filters:
            if "cost_element_id" in filters:
                stmt = stmt.where(
                    CostRegistration.cost_element_id == filters["cost_element_id"]
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
        from sqlalchemy import or_

        # Build query for time-travel support
        stmt = select(func.sum(CostRegistration.amount)).where(
            CostRegistration.cost_element_id == cost_element_id,
        )

        # Time-travel filter
        if as_of is not None:
            # Valid at the specified time (contains operator: range @> timestamp)
            stmt = stmt.where(CostRegistration.valid_time.op("@>")(as_of))
            # Include records that were not deleted before as_of
            # (deleted_at IS NULL OR deleted_at > as_of)
            stmt = stmt.where(
                or_(
                    CostRegistration.deleted_at.is_(None),
                    CostRegistration.deleted_at > as_of,
                )
            )
        else:
            # Current versions only (open-ended valid_time and not deleted)
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
        Unlike System Time Travel, this does NOT check transaction_time, because costs
        are recorded as they happen, and we want to query based on when the cost was
        incurred, not when it was recorded in the system.

        Args:
            cost_registration_id: The unique identifier of the cost registration
            as_of: Timestamp to query (historical state based on valid_time)
            branch: Branch name to query (always "main" for non-branchable entities)
            branch_mode: Resolution mode for branches (not applicable, kept for interface consistency)

        Returns:
            CostRegistration if found at the specified timestamp, None otherwise
        """
        from sqlalchemy import or_

        # Build query with valid_time filtering only (not transaction_time)
        stmt = select(CostRegistration).where(
            CostRegistration.cost_registration_id == cost_registration_id,
            # Check as_of is within valid_time range
            CostRegistration.valid_time.op("@>")(as_of),
            # CRITICAL: Also check as_of >= lower bound (entity existed)
            func.lower(CostRegistration.valid_time) <= as_of,
            # Include records that were not deleted before as_of
            or_(
                CostRegistration.deleted_at.is_(None),
                CostRegistration.deleted_at > as_of,
            ),
        ).limit(1)

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_budget_status(self, cost_element_id: UUID) -> BudgetStatus:
        """Get budget status for a cost element.

        Returns budget, used, remaining, and percentage used.

        Args:
            cost_element_id: The cost element to get status for

        Returns:
            BudgetStatus with budget, used, remaining, percentage
        """
        # Get the cost element's budget
        stmt = select(CostElement).where(
            CostElement.cost_element_id == cost_element_id,
            func.upper(CostElement.valid_time).is_(None),
            CostElement.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        cost_element = result.scalar_one_or_none()

        if cost_element is None:
            raise ValueError(f"Cost element {cost_element_id} not found")

        budget = cost_element.budget_amount

        # Get total costs for this cost element
        used = await self.get_total_for_cost_element(cost_element_id)
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
