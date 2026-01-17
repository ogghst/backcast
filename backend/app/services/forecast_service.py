"""Forecast Service - branchable entity management."""

from datetime import datetime
from typing import Any, cast
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.branching.service import BranchableService
from app.core.versioning.commands import CreateVersionCommand
from app.models.domain.forecast import Forecast
from app.models.schemas.forecast import ForecastCreate


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
        if filters:
            if "cost_element_id" in filters:
                stmt = stmt.where(
                    Forecast.cost_element_id == filters["cost_element_id"]
                )

        # Apply ordering (newest first by creation time)
        stmt = stmt.order_by(cast(Any, Forecast).transaction_time.desc())

        # Apply pagination
        stmt = stmt.offset(skip).limit(limit)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())
