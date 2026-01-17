"""Schedule Baseline Service - branchable entity management.

Service for managing Schedule Baselines with full branching and versioning support.
"""

from datetime import datetime
from typing import Any, cast
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.branching.service import BranchableService
from app.core.versioning.commands import CreateVersionCommand
from app.models.domain.cost_element import CostElement
from app.models.domain.schedule_baseline import ScheduleBaseline
from app.models.schemas.schedule_baseline import ScheduleBaselineCreate


class ScheduleBaselineService(BranchableService[ScheduleBaseline]):  # type: ignore[type-var,unused-ignore]
    """Service for Schedule Baseline management (branchable + versionable).

    Provides CRUD operations with branching support for managing
    schedule baselines used in EVM Planned Value (PV) calculations.
    """

    def __init__(self, db: AsyncSession):
        """Initialize service with database session.

        Args:
            db: Async database session
        """
        super().__init__(ScheduleBaseline, db)

    async def get_current(
        self, root_id: UUID, branch: str = "main"
    ) -> ScheduleBaseline | None:
        """Get the current active version for a root entity on a specific branch.

        Override parent method to use 'schedule_baseline_id' field instead of
        the auto-generated field name.

        Args:
            root_id: Root UUID identifier for the ScheduleBaseline
            branch: Branch name (default: "main")

        Returns:
            Current ScheduleBaseline or None
        """
        stmt = (
            select(ScheduleBaseline)
            .where(
                ScheduleBaseline.schedule_baseline_id == root_id,
                ScheduleBaseline.branch == branch,
                func.upper(cast(Any, ScheduleBaseline).valid_time).is_(None),
                cast(Any, ScheduleBaseline).deleted_at.is_(None),
            )
            .order_by(cast(Any, ScheduleBaseline).valid_time.desc())
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
    ) -> ScheduleBaseline:
        """Create the initial version of a ScheduleBaseline.

        Override parent method to use 'schedule_baseline_id' field instead of
        the auto-generated field name.

        Args:
            root_id: Root UUID identifier for the ScheduleBaseline
            actor_id: User creating the ScheduleBaseline
            control_date: Optional control date for valid_time (defaults to now)
            branch: Branch name (default: "main")
            **data: Additional fields for the ScheduleBaseline

        Returns:
            Created ScheduleBaseline
        """
        data["schedule_baseline_id"] = root_id

        cmd = CreateVersionCommand(
            entity_class=ScheduleBaseline,
            root_id=root_id,
            actor_id=actor_id,
            control_date=control_date,
            branch=branch,
            **data,
        )
        return await cmd.execute(self.session)

    async def create(
        self,
        create_schema: ScheduleBaselineCreate,
        actor_id: UUID,
        control_date: datetime | None = None,
        branch: str = "main",
    ) -> ScheduleBaseline:
        """Create a new ScheduleBaseline from a schema.

        Args:
            create_schema: ScheduleBaselineCreate schema with entity data
            actor_id: User creating the baseline
            control_date: Optional control date for valid_time
            branch: Branch name (default: "main")

        Returns:
            Created ScheduleBaseline
        """
        from uuid import uuid4

        root_id = create_schema.schedule_baseline_id or uuid4()

        return await self.create_root(
            root_id=root_id,
            actor_id=actor_id,
            control_date=control_date,
            branch=branch,
            cost_element_id=create_schema.cost_element_id,
            name=create_schema.name,
            start_date=create_schema.start_date,
            end_date=create_schema.end_date,
            progression_type=create_schema.progression_type,
            description=create_schema.description,
        )

    async def get_by_id(
        self, schedule_baseline_id: UUID, branch: str = "main"
    ) -> ScheduleBaseline | None:
        """Get schedule baseline by root ID and branch."""
        stmt = (
            select(ScheduleBaseline)
            .where(
                ScheduleBaseline.schedule_baseline_id == schedule_baseline_id,
                ScheduleBaseline.branch == branch,
                func.upper(cast(Any, ScheduleBaseline).valid_time).is_(None),
                cast(Any, ScheduleBaseline).deleted_at.is_(None),
            )
            .order_by(cast(Any, ScheduleBaseline).valid_time.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def soft_delete(
        self,
        root_id: UUID,
        actor_id: UUID,
        branch: str = "main",
        control_date: datetime | None = None,
    ) -> ScheduleBaseline:
        """Soft delete schedule baseline using BranchableService.soft_delete."""
        return await super().soft_delete(
            root_id=root_id,
            actor_id=actor_id,
            branch=branch,
            control_date=control_date,
        )

    def _get_base_stmt(self) -> Any:
        """Get base select statement with Cost Element name join.

        Returns a select statement that joins with CostElement to include
        the cost element name in queries.
        """
        # Subquery for current CostElement versions
        ce_subq = (
            select(
                CostElement.cost_element_id, CostElement.name.label("cost_element_name")
            )
            .where(
                func.upper(cast(Any, CostElement).valid_time).is_(None),
                cast(Any, CostElement).deleted_at.is_(None),
            )
            .subquery()
        )

        return select(ScheduleBaseline, ce_subq.c.cost_element_name).join(
            ce_subq, ScheduleBaseline.cost_element_id == ce_subq.c.cost_element_id
        )
