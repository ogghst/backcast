"""Forecast Service - branchable entity management.

Forecasts are now associated with Work Packages (PMI budget holders)
rather than Cost Elements. The WorkPackage model owns forecast_id.
"""

from __future__ import annotations

import builtins
from datetime import datetime
from decimal import Decimal
from typing import Any, cast
from uuid import UUID, uuid4

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.branching.service import BranchableService
from app.core.temporal_queries import (
    current_join_filter,
    is_current_version_on_branch,
)
from app.core.versioning.commands import CreateVersionCommand
from app.models.domain.forecast import Forecast
from app.models.domain.work_package import WorkPackage
from app.models.schemas.forecast import ForecastCreate, ForecastUpdate


class ForecastAlreadyExistsError(Exception):
    """Raised when attempting to create a duplicate forecast for a work package.

    Attributes:
        work_package_id: The UUID of the work package.
        branch: The branch name.
    """

    def __init__(self, work_package_id: str, branch: str) -> None:
        self.work_package_id = work_package_id
        self.branch = branch
        super().__init__(
            f"Forecast already exists for work package {work_package_id} on branch {branch}"
        )


class ForecastService(BranchableService[Forecast]):  # type: ignore[type-var,unused-ignore]
    """Service for Forecast management (branchable + versionable)."""

    def __init__(self, db: AsyncSession):
        """Initialize service with database session.

        Args:
            db: Async database session
        """
        super().__init__(Forecast, db)

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

    async def create_forecast(
        self,
        forecast_in: ForecastCreate,
        actor_id: UUID,
        branch: str | None = None,
        control_date: datetime | None = None,
    ) -> Forecast:
        """Create new forecast using CreateVersionCommand."""
        forecast_data = forecast_in.model_dump(exclude_unset=True)
        if control_date is None:
            control_date = getattr(forecast_in, "control_date", None)
        forecast_data.pop("control_date", None)

        root_id = forecast_in.forecast_id or uuid4()
        forecast_data["forecast_id"] = root_id

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
        """Get forecast by root ID and branch with creator name."""
        from app.models.domain.user import User

        UserAlias = cast(Any, User)
        creator_subq = (
            select(UserAlias.user_id, UserAlias.full_name)
            .distinct(UserAlias.user_id)
            .order_by(UserAlias.user_id, UserAlias.transaction_time.desc())
            .subquery("creator_lookup")
        )

        stmt = (
            select(
                Forecast,
                creator_subq.c.full_name.label("created_by_name"),
            )
            .outerjoin(
                creator_subq,
                Forecast.created_by == creator_subq.c.user_id,
            )
            .where(
                Forecast.forecast_id == forecast_id,
                is_current_version_on_branch(
                    cast(Any, Forecast).valid_time,
                    Forecast.branch,
                    branch,
                    cast(Any, Forecast).deleted_at,
                ),
            )
            .order_by(cast(Any, Forecast).valid_time.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        row = result.first()
        if row is None:
            return None
        entity = row[0]
        entity.created_by_name = row[1]
        return entity

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
            filters: Dict of field filters (e.g., {"work_package_id": uuid})
            branch: Branch name to query (default: "main")
            skip: Number of records to skip (for pagination)
            limit: Maximum number of records to return

        Returns:
            List of forecasts matching the criteria
        """
        stmt = select(Forecast).where(
            is_current_version_on_branch(
                cast(Any, Forecast).valid_time,
                Forecast.branch,
                branch,
                cast(Any, Forecast).deleted_at,
            ),
        )

        stmt = stmt.order_by(cast(Any, Forecast).transaction_time.desc())
        stmt = stmt.offset(skip).limit(limit)

        # Add creator-name outerjoin so created_by_name is populated per row.
        from app.models.domain.user import User

        UserAlias = cast(Any, User)
        creator_subq = (
            select(UserAlias.user_id, UserAlias.full_name)
            .distinct(UserAlias.user_id)
            .order_by(UserAlias.user_id, UserAlias.transaction_time.desc())
            .subquery("creator_lookup")
        )
        fetch_stmt = stmt.with_only_columns(
            Forecast,
            creator_subq.c.full_name.label("created_by_name"),
        ).outerjoin(
            creator_subq,
            Forecast.created_by == creator_subq.c.user_id,
        )

        result = await self.session.execute(fetch_stmt)
        items: list[Forecast] = []
        for row in result.all():
            entity = row[0]
            entity.created_by_name = row[1]
            items.append(entity)
        return items

    async def get_for_work_package(
        self, work_package_id: UUID, branch: str = "main"
    ) -> Forecast | None:
        """Get the forecast associated with a work package via work_package.forecast_id.

        Uses the inverted FK pattern: queries via WorkPackage.forecast_id instead of
        Forecast.work_package_id (which does not exist).

        Args:
            work_package_id: The UUID of the work package
            branch: Branch name to query (default: "main")

        Returns:
            Forecast if found, None otherwise
        """
        from app.models.domain.user import User

        UserAlias = cast(Any, User)
        creator_subq = (
            select(UserAlias.user_id, UserAlias.full_name)
            .distinct(UserAlias.user_id)
            .order_by(UserAlias.user_id, UserAlias.transaction_time.desc())
            .subquery("creator_lookup")
        )

        stmt = (
            select(
                Forecast,
                creator_subq.c.full_name.label("created_by_name"),
            )
            .join(WorkPackage, WorkPackage.forecast_id == Forecast.forecast_id)
            .outerjoin(
                creator_subq,
                Forecast.created_by == creator_subq.c.user_id,
            )
            .where(
                WorkPackage.work_package_id == work_package_id,
                WorkPackage.branch == branch,
                Forecast.branch == branch,
                WorkPackage.forecast_id.is_not(None),
                current_join_filter(
                    (Forecast.valid_time, Forecast.deleted_at),
                    (WorkPackage.valid_time, cast(Any, WorkPackage).deleted_at),
                ),
            )
            .order_by(Forecast.valid_time.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        row = result.first()
        if row is None:
            return None
        entity = row[0]
        entity.created_by_name = row[1]
        return entity

    async def create_for_work_package(
        self,
        work_package_id: UUID,
        actor_id: UUID,
        branch: str = "main",
        control_date: datetime | None = None,
        **data: Any,
    ) -> Forecast:
        """Create a forecast for a work package, enforcing 1:1 relationship.

        Args:
            work_package_id: The UUID of the work package
            actor_id: User creating the forecast
            branch: Branch name (default: "main")
            control_date: Optional control date for valid_time
            **data: Additional forecast fields (eac_amount, basis_of_estimate, etc.)

        Returns:
            Created Forecast

        Raises:
            ForecastAlreadyExistsError: If a forecast already exists for this work package
        """
        existing = await self.get_for_work_package(work_package_id, branch)
        if existing:
            raise ForecastAlreadyExistsError(
                work_package_id=str(work_package_id), branch=branch
            )

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

        # Link work package to forecast via UpdateCommand
        from app.core.branching.commands import UpdateCommand

        update_cmd = UpdateCommand(
            entity_class=WorkPackage,
            root_id=work_package_id,
            actor_id=actor_id,
            branch=branch,
            control_date=control_date,
            updates={"forecast_id": forecast_id},
        )
        await update_cmd.execute(self.session)

        return forecast

    async def update_forecast(
        self,
        forecast_id: UUID,
        forecast_in: ForecastUpdate,
        actor_id: UUID,
        control_date: datetime | None = None,
    ) -> Forecast:
        """Update forecast using branch-aware UpdateCommand."""
        if control_date is None:
            control_date = forecast_in.control_date
        branch = forecast_in.branch or "main"

        update_data = forecast_in.model_dump(exclude_unset=True)
        update_data.pop("control_date", None)
        update_data.pop("branch", None)

        from app.core.branching.commands import UpdateCommand

        cmd = UpdateCommand(
            entity_class=Forecast,  # type: ignore[type-var,unused-ignore]
            root_id=forecast_id,
            actor_id=actor_id,
            branch=branch,
            control_date=control_date,
            updates=update_data,
        )
        return await cmd.execute(self.session)

    async def ensure_exists(
        self,
        work_package_id: UUID,
        actor_id: UUID,
        branch: str = "main",
        budget_amount: Decimal | None = None,
        control_date: datetime | None = None,
    ) -> Forecast:
        """Ensure a forecast exists for the work package, creating if necessary.

        Args:
            work_package_id: The UUID of the work package
            actor_id: User creating the forecast if needed
            branch: Branch name (default: "main")
            budget_amount: Optional budget amount for default forecast
            control_date: Optional control date for valid_time

        Returns:
            Existing or newly created Forecast
        """
        existing = await self.get_for_work_package(work_package_id, branch)
        if existing:
            return existing

        eac_amount = budget_amount if budget_amount is not None else Decimal("0.00")
        return await self.create_for_work_package(
            work_package_id=work_package_id,
            actor_id=actor_id,
            branch=branch,
            eac_amount=eac_amount,
            basis_of_estimate="Initial forecast",
            control_date=control_date,
        )

    async def get_forecasts_for_work_packages(
        self,
        work_package_ids: builtins.list[UUID],
        branch: str = "main",
        as_of: datetime | None = None,
    ) -> dict[UUID, Forecast]:
        """Get forecasts for multiple work packages efficiently.

        Args:
            work_package_ids: List of work package UUIDs
            branch: Branch name (default: "main")
            as_of: Time travel timestamp (None = current, past = historical point)

        Returns:
            Dictionary mapping work_package_id to Forecast
        """
        if not work_package_ids:
            return {}

        if as_of is not None:
            from sqlalchemy import cast as sql_cast
            from sqlalchemy.dialects.postgresql import TIMESTAMP

            as_of_tstz = sql_cast(as_of, TIMESTAMP(timezone=True))
            stmt = (
                select(WorkPackage.work_package_id, Forecast)
                .join(WorkPackage, WorkPackage.forecast_id == Forecast.forecast_id)
                .where(
                    WorkPackage.work_package_id.in_(work_package_ids),
                    WorkPackage.branch == branch,
                    WorkPackage.forecast_id.is_not(None),
                    or_(
                        cast(Any, Forecast).deleted_at.is_(None),
                        cast(Any, Forecast).deleted_at > as_of,
                    ),
                    or_(
                        cast(Any, WorkPackage).deleted_at.is_(None),
                        cast(Any, WorkPackage).deleted_at > as_of,
                    ),
                    Forecast.valid_time.op("@>")(as_of_tstz),
                    func.lower(Forecast.valid_time) <= as_of_tstz,
                    WorkPackage.valid_time.op("@>")(as_of_tstz),
                    func.lower(WorkPackage.valid_time) <= as_of_tstz,
                )
            )
        else:
            stmt = (
                select(WorkPackage.work_package_id, Forecast)
                .join(WorkPackage, WorkPackage.forecast_id == Forecast.forecast_id)
                .where(
                    WorkPackage.work_package_id.in_(work_package_ids),
                    WorkPackage.branch == branch,
                    WorkPackage.forecast_id.is_not(None),
                    is_current_version_on_branch(
                        Forecast.valid_time,
                        Forecast.branch,
                        branch,
                        cast(Any, Forecast).deleted_at,
                    ),
                    is_current_version_on_branch(
                        cast(Any, WorkPackage).valid_time,
                        WorkPackage.branch,
                        branch,
                        cast(Any, WorkPackage).deleted_at,
                    ),
                )
            )

        result = await self.session.execute(stmt)

        forecasts = {}
        for row in result.all():
            wp_id, forecast = row
            forecasts[wp_id] = forecast

        return forecasts

    # --- Backward-compatible aliases ---

    async def get_for_cost_element(
        self, cost_element_id: UUID, branch: str = "main"
    ) -> Forecast | None:
        """Backward-compatible alias for get_for_work_package()."""
        return await self.get_for_work_package(cost_element_id, branch)

    async def create_for_cost_element(
        self,
        cost_element_id: UUID,
        actor_id: UUID,
        branch: str = "main",
        control_date: datetime | None = None,
        **data: Any,
    ) -> Forecast:
        """Backward-compatible alias for create_for_work_package()."""
        return await self.create_for_work_package(
            work_package_id=cost_element_id,
            actor_id=actor_id,
            branch=branch,
            control_date=control_date,
            **data,
        )

    async def get_forecasts_for_cost_elements(
        self,
        cost_element_ids: builtins.list[UUID],
        branch: str = "main",
        as_of: datetime | None = None,
    ) -> dict[UUID, Forecast]:
        """Backward-compatible alias for get_forecasts_for_work_packages()."""
        return await self.get_forecasts_for_work_packages(
            cost_element_ids, branch=branch, as_of=as_of
        )
