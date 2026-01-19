"""Forecast Service - branchable entity management."""

from datetime import datetime
from decimal import Decimal
from typing import Any, cast
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.branching.service import BranchableService
from app.core.versioning.commands import CreateVersionCommand
from app.models.domain.cost_element import CostElement
from app.models.domain.forecast import Forecast
from app.models.schemas.forecast import ForecastCreate


class ForecastAlreadyExistsError(Exception):
    """Raised when attempting to create a duplicate forecast for a cost element.

    Attributes:
        cost_element_id: The UUID of the cost element.
        branch: The branch name.
    """

    def __init__(self, cost_element_id: str, branch: str) -> None:
        self.cost_element_id = cost_element_id
        self.branch = branch
        super().__init__(
            f"Forecast already exists for cost_element {cost_element_id} on branch {branch}"
        )


class ForecastService(BranchableService[Forecast]):  # type: ignore[type-var,unused-ignore]
    """Service for Forecast management (branchable + versionable)."""

    def __init__(self, db: AsyncSession):
        """Initialize service with database session.

        Args:
            db: Async database session
        """
        super().__init__(Forecast, db)

    async def get_current(self, root_id: UUID, branch: str = "main") -> Forecast | None:
        """Get the current active version for a root entity on a specific branch.

        Override parent method to use 'forecast_id' field instead of
        the auto-generated field name.
        """
        stmt = (
            select(Forecast)
            .where(
                Forecast.forecast_id == root_id,
                Forecast.branch == branch,
                func.upper(cast(Any, Forecast).valid_time).is_(None),
                cast(Any, Forecast).deleted_at.is_(None),
            )
            .order_by(cast(Any, Forecast).valid_time.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_root(
        self,
        root_id: UUID,
        actor_id: UUID,
        control_date: datetime | None = None,
        branch: str = "main",
        **data: Any,
    ) -> Forecast:
        """Create the initial version of a Forecast.

        Override parent method to use 'forecast_id' field instead of
        the auto-generated field name.

        Args:
            root_id: Root UUID identifier for the Forecast
            actor_id: User creating the Forecast
            control_date: Optional control date for valid_time (defaults to now)
            branch: Branch name (default: "main")
            **data: Additional fields for the Forecast

        Returns:
            Created Forecast
        """
        data["forecast_id"] = root_id

        cmd = CreateVersionCommand(
            entity_class=Forecast,
            root_id=root_id,
            actor_id=actor_id,
            control_date=control_date,
            branch=branch,
            **data,
        )
        return await cmd.execute(self.session)

    async def create(
        self,
        forecast_in: ForecastCreate,
        actor_id: UUID,
        branch: str | None = None,
        control_date: datetime | None = None,
    ) -> Forecast:
        """Create new forecast using CreateVersionCommand."""
        forecast_data = forecast_in.model_dump(exclude_unset=True)
        forecast_data.pop("control_date", None)

        # Use provided forecast_id (for seeding) or generate new one
        root_id = forecast_in.forecast_id or uuid4()
        forecast_data["forecast_id"] = root_id

        # Use schema branch if provided, otherwise use parameter
        if "branch" not in forecast_data or forecast_data["branch"] == "main":
            forecast_data["branch"] = branch or "main"

        cmd = CreateVersionCommand(
            entity_class=Forecast,  # type: ignore[type-var,unused-ignore]
            root_id=root_id,
            actor_id=actor_id,
            control_date=control_date,
            **forecast_data,
        )
        return await cmd.execute(self.session)

    async def get_by_id(
        self, forecast_id: UUID, branch: str = "main"
    ) -> Forecast | None:
        """Get forecast by root ID and branch."""
        stmt = (
            select(Forecast)
            .where(
                Forecast.forecast_id == forecast_id,
                Forecast.branch == branch,
                func.upper(cast(Any, Forecast).valid_time).is_(None),
                cast(Any, Forecast).deleted_at.is_(None),
            )
            .order_by(cast(Any, Forecast).valid_time.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def soft_delete(  # type: ignore[override]
        self,
        forecast_id: UUID,
        actor_id: UUID,
        branch: str = "main",
        control_date: datetime | None = None,
    ) -> None:
        """Soft delete forecast using BranchableService.soft_delete.

        This uses the BranchableSoftDeleteCommand which is branch-aware.
        """
        # Call parent method from BranchableService
        await super().soft_delete(
            root_id=forecast_id,
            actor_id=actor_id,
            branch=branch,
            control_date=control_date,
        )

    async def list(
        self,
        filters: dict[str, Any] | None = None,
        branch: str = "main",
        skip: int = 0,
        limit: int = 100,
    ) -> list[Forecast]:
        """List forecasts with optional filters.

        Args:
            filters: Dict of field filters (e.g., {"cost_element_id": uuid})
            branch: Branch name to query (default: "main")
            skip: Number of records to skip (for pagination)
            limit: Maximum number of records to return

        Returns:
            List of forecasts matching the criteria
        """
        # Build base query for current versions on specified branch
        stmt = select(Forecast).where(
            Forecast.branch == branch,
            func.upper(cast(Any, Forecast).valid_time).is_(None),
            cast(Any, Forecast).deleted_at.is_(None),
        )

        # Apply filters if provided
        # Note: cost_element_id filter removed since Forecast no longer has that field
        # Use get_for_cost_element() instead to query via cost element

        # Apply ordering (newest first by creation time)
        stmt = stmt.order_by(cast(Any, Forecast).transaction_time.desc())

        # Apply pagination
        stmt = stmt.offset(skip).limit(limit)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_for_cost_element(
        self, cost_element_id: UUID, branch: str = "main"
    ) -> Forecast | None:
        """Get the forecast associated with a cost element via cost_element.forecast_id.

        Uses the inverted FK pattern: queries via CostElement.forecast_id instead of
        Forecast.cost_element_id (which no longer exists).

        Args:
            cost_element_id: The UUID of the cost element
            branch: Branch name to query (default: "main")

        Returns:
            Forecast if found, None otherwise
        """
        # Query via cost_element.forecast_id (inverted FK pattern)
        stmt = (
            select(Forecast)
            .join(CostElement, CostElement.forecast_id == Forecast.forecast_id)
            .where(
                CostElement.cost_element_id == cost_element_id,
                CostElement.branch == branch,
                Forecast.branch == branch,
                # CRITICAL: Only match cost elements WITH a forecast
                CostElement.forecast_id.is_not(None),
                # "Current" filter (no as_of)
                func.upper(Forecast.valid_time).is_(None),
                Forecast.deleted_at.is_(None),
            )
            .order_by(Forecast.valid_time.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_for_cost_element(
        self,
        cost_element_id: UUID,
        actor_id: UUID,
        branch: str = "main",
        control_date: datetime | None = None,
        **data: Any,
    ) -> Forecast:
        """Create a forecast for a cost element, enforcing 1:1 relationship.

        Args:
            cost_element_id: The UUID of the cost element
            actor_id: User creating the forecast
            branch: Branch name (default: "main")
            control_date: Optional control date for valid_time
            **data: Additional forecast fields (eac_amount, basis_of_estimate, etc.)

        Returns:
            Created Forecast

        Raises:
            ForecastAlreadyExistsError: If a forecast already exists for this cost element
        """
        # Check for existing forecast
        existing = await self.get_for_cost_element(cost_element_id, branch)
        if existing:
            raise ForecastAlreadyExistsError(
                cost_element_id=str(cost_element_id), branch=branch
            )

        # Create new forecast
        forecast_id = uuid4()
        data["forecast_id"] = forecast_id
        data["branch"] = branch

        cmd = CreateVersionCommand(
            entity_class=Forecast,
            root_id=forecast_id,
            actor_id=actor_id,
            control_date=control_date,
            **data,
        )
        forecast = await cmd.execute(self.session)

        # Update cost element with forecast_id reference
        # Get current cost element version
        ce_stmt = (
            select(CostElement)
            .where(
                CostElement.cost_element_id == cost_element_id,
                CostElement.branch == branch,
                func.upper(CostElement.valid_time).is_(None),
                CostElement.deleted_at.is_(None),
            )
            .order_by(CostElement.valid_time.desc())
            .limit(1)
        )
        ce_result = await self.session.execute(ce_stmt)
        cost_element = ce_result.scalar_one_or_none()

        if cost_element:
            cost_element.forecast_id = forecast_id
            await self.session.flush()

        return forecast

    async def ensure_exists(
        self,
        cost_element_id: UUID,
        actor_id: UUID,
        branch: str = "main",
        budget_amount: Decimal | None = None,
    ) -> Forecast:
        """Ensure a forecast exists for the cost element, creating if necessary.

        Args:
            cost_element_id: The UUID of the cost element
            actor_id: User creating the forecast if needed
            branch: Branch name (default: "main")
            budget_amount: Optional budget amount for default forecast

        Returns:
            Existing or newly created Forecast
        """
        # Check for existing forecast
        existing = await self.get_for_cost_element(cost_element_id, branch)
        if existing:
            return existing

        # Create default forecast
        eac_amount = budget_amount if budget_amount is not None else Decimal("0.00")
        return await self.create_for_cost_element(
            cost_element_id=cost_element_id,
            actor_id=actor_id,
            branch=branch,
            eac_amount=eac_amount,
            basis_of_estimate="Initial forecast",
        )
