"""Schedule Baseline Service - branchable entity management.

Service for managing Schedule Baselines with full branching and versioning support.
Schedule baselines are now associated with Work Packages (PMI budget holders)
rather than Cost Elements. The WorkPackage model owns schedule_baseline_id.
"""

from datetime import datetime
from typing import Any, cast
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.branching.service import BranchableService
from app.core.versioning.commands import CreateVersionCommand
from app.models.domain.schedule_baseline import ScheduleBaseline
from app.models.domain.work_package import WorkPackage
from app.models.protocols import VersionableProtocol
from app.models.schemas.schedule_baseline import (
    ScheduleBaselineCreate,
    ScheduleBaselineUpdate,
)


class BaselineAlreadyExistsError(Exception):
    """Exception raised when attempting to create a duplicate schedule baseline for a work package.

    Each work package can have exactly one schedule baseline. This exception is raised when
    attempting to create a second baseline for a work package that already has one.

    Attributes:
        work_package_id: The UUID of the work package that already has a baseline
        branch: The branch where the duplicate was detected (default: "main")
    """

    def __init__(self, work_package_id: UUID, branch: str = "main") -> None:
        """Initialize the exception with work package ID and branch.

        Args:
            work_package_id: The UUID of the work package with existing baseline
            branch: The branch where the duplicate was detected
        """
        self.work_package_id = work_package_id
        self.branch = branch
        super().__init__(
            f"Schedule baseline already exists for work package {work_package_id} "
            f"in branch '{branch}'. Each work package can have exactly one baseline."
        )


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
            entity_class=cast(type[VersionableProtocol], ScheduleBaseline),
            root_id=root_id,
            actor_id=actor_id,
            control_date=control_date,
            branch=branch,
            **data,
        )
        return cast(ScheduleBaseline, await cmd.execute(self.session))

    async def create_schedule_baseline(
        self,
        create_schema: ScheduleBaselineCreate,
        actor_id: UUID,
        branch: str = "main",
        control_date: datetime | None = None,
    ) -> ScheduleBaseline:
        """Create a new ScheduleBaseline from a schema.

        Args:
            create_schema: ScheduleBaselineCreate schema with entity data
            actor_id: User creating the baseline
            branch: Branch name (default: "main")
            control_date: Optional control date

        Returns:
            Created ScheduleBaseline
        """
        control_date = getattr(create_schema, "control_date", None)
        from uuid import uuid4

        root_id = create_schema.schedule_baseline_id or uuid4()

        exclude_fields = {"schedule_baseline_id", "branch", "control_date"}
        data = create_schema.model_dump(exclude_unset=True, exclude=exclude_fields)

        return await self.create_root(
            root_id=root_id,
            actor_id=actor_id,
            control_date=control_date,
            branch=branch,
            **data,
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

    async def update_schedule_baseline(
        self,
        root_id: UUID,
        baseline_in: ScheduleBaselineUpdate,
        actor_id: UUID,
        branch: str = "main",
        control_date: datetime | None = None,
    ) -> ScheduleBaseline:
        """Update schedule baseline using UpdateVersionCommand.

        Args:
            root_id: The schedule baseline to update
            baseline_in: The update data
            actor_id: The user making the update
            branch: The branch to update (default: "main")
            control_date: Optional control date for valid_time
        """
        if control_date is None:
            control_date = baseline_in.control_date
        branch = baseline_in.branch or "main"

        update_data = baseline_in.model_dump(
            exclude_unset=True,
            exclude={"control_date", "branch"},
        )

        from app.core.versioning.commands import UpdateVersionCommand

        class ScheduleBaselineUpdateCommand(UpdateVersionCommand[ScheduleBaseline]):  # type: ignore[type-var,unused-ignore]
            def __init__(
                self,
                entity_class: type[ScheduleBaseline],
                root_id: UUID,
                actor_id: UUID,
                branch: str = "main",
                control_date: datetime | None = None,
                **updates: Any,
            ) -> None:
                super().__init__(
                    entity_class,
                    root_id,
                    actor_id,
                    control_date=control_date,
                    **updates,
                )
                self.branch = branch

            def _root_field_name(self) -> str:
                return "schedule_baseline_id"

            async def _get_current(self, session: AsyncSession) -> Any | None:
                stmt = (
                    select(self.entity_class)
                    .where(
                        getattr(self.entity_class, self._root_field_name())
                        == self.root_id,
                        self.entity_class.branch == self.branch,
                        func.upper(cast(Any, self.entity_class).valid_time).is_(None),
                        cast(Any, self.entity_class).deleted_at.is_(None),
                    )
                    .order_by(cast(Any, self.entity_class).valid_time.desc())
                    .limit(1)
                )
                result = await session.execute(stmt)
                return result.scalar_one_or_none()

        cmd = ScheduleBaselineUpdateCommand(
            entity_class=ScheduleBaseline,  # type: ignore[type-var,unused-ignore]
            root_id=root_id,
            actor_id=actor_id,
            branch=branch,
            control_date=control_date,
            **update_data,
        )
        return await cmd.execute(self.session)

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

    async def get_for_work_package(
        self, work_package_id: UUID, branch: str = "main"
    ) -> ScheduleBaseline | None:
        """Get the schedule baseline for a specific work package.

        Uses the inverted relationship (work_packages.schedule_baseline_id)
        to find the single baseline associated with the work package.

        Args:
            work_package_id: The UUID of the work package
            branch: Branch name (default: "main")

        Returns:
            ScheduleBaseline if found, None otherwise
        """
        wp_stmt = select(WorkPackage.schedule_baseline_id).where(
            WorkPackage.work_package_id == work_package_id,
            WorkPackage.branch == branch,
            func.upper(cast(Any, WorkPackage).valid_time).is_(None),
            cast(Any, WorkPackage).deleted_at.is_(None),
        )
        wp_result = await self.session.execute(wp_stmt)
        schedule_baseline_id = wp_result.scalar_one_or_none()

        if schedule_baseline_id is None:
            return None

        return await self.get_by_id(schedule_baseline_id, branch=branch)

    async def ensure_exists(
        self,
        work_package_id: UUID,
        actor_id: UUID,
        branch: str = "main",
        control_date: datetime | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        progression_type: str | None = None,
    ) -> ScheduleBaseline:
        """Ensure a schedule baseline exists for the work package.

        Creates a default baseline if none exists, otherwise returns the existing one.

        Args:
            work_package_id: The UUID of the work package
            actor_id: User creating the baseline if needed
            branch: Branch name (default: "main")
            control_date: Optional control date for valid_time
            start_date: Optional start date (defaults to control_date or now)
            end_date: Optional end date (defaults to start_date + 90 days)
            progression_type: Optional progression type (defaults to LINEAR)

        Returns:
            ScheduleBaseline (existing or newly created)
        """
        existing = await self.get_for_work_package(work_package_id, branch=branch)
        if existing is not None:
            return existing

        from datetime import UTC, timedelta
        from uuid import uuid4

        now = control_date or datetime.now(UTC)
        baseline_id = uuid4()

        effective_start = start_date or now
        effective_end = end_date or (effective_start + timedelta(days=90))
        effective_progression = progression_type or "LINEAR"

        baseline = await self.create_root(
            root_id=baseline_id,
            actor_id=actor_id,
            control_date=control_date,
            branch=branch,
            name="Default Schedule",
            start_date=effective_start,
            end_date=effective_end,
            progression_type=effective_progression,
        )

        # Link work package to baseline via UpdateCommand
        from app.core.branching.commands import UpdateCommand

        update_cmd = UpdateCommand(
            entity_class=WorkPackage,
            root_id=work_package_id,
            actor_id=actor_id,
            branch=branch,
            control_date=control_date,
            updates={"schedule_baseline_id": baseline_id},
        )
        await update_cmd.execute(self.session)

        return baseline

    async def create_for_work_package(
        self,
        work_package_id: UUID,
        actor_id: UUID,
        name: str,
        start_date: datetime,
        end_date: datetime,
        progression_type: str = "LINEAR",
        description: str | None = None,
        branch: str = "main",
        control_date: datetime | None = None,
    ) -> ScheduleBaseline:
        """Create a schedule baseline for a specific work package.

        Validates that no duplicate baseline exists for the work package
        in the specified branch before creating.

        Args:
            work_package_id: The UUID of the work package
            actor_id: User creating the baseline
            name: Baseline name
            start_date: Schedule start date
            end_date: Schedule end date
            progression_type: Type of progression curve (default: "LINEAR")
            description: Optional description
            branch: Branch name (default: "main")
            control_date: Optional control date for valid_time

        Returns:
            Created ScheduleBaseline

        Raises:
            BaselineAlreadyExistsError: If a baseline already exists for this work package
        """
        existing = await self.get_for_work_package(work_package_id, branch=branch)
        if existing is not None:
            raise BaselineAlreadyExistsError(
                work_package_id=work_package_id, branch=branch
            )

        from uuid import uuid4

        baseline_id = uuid4()
        baseline = await self.create_root(
            root_id=baseline_id,
            actor_id=actor_id,
            control_date=control_date,
            branch=branch,
            name=name,
            start_date=start_date,
            end_date=end_date,
            progression_type=progression_type,
            description=description,
        )

        # Link work package to baseline via UpdateCommand
        from app.core.branching.commands import UpdateCommand

        update_cmd = UpdateCommand(
            entity_class=WorkPackage,
            root_id=work_package_id,
            actor_id=actor_id,
            branch=branch,
            control_date=control_date,
            updates={"schedule_baseline_id": baseline_id},
        )
        await update_cmd.execute(self.session)

        return baseline

    def _get_base_stmt(self) -> Any:
        """Get base select statement with Work Package name join.

        Returns a select statement that joins with WorkPackage to include
        the work package name in queries. Uses the inverted relationship
        where WorkPackage.schedule_baseline_id references ScheduleBaseline.
        """
        wp_subq = (
            select(
                WorkPackage.work_package_id,
                WorkPackage.schedule_baseline_id,
                WorkPackage.name.label("work_package_name"),
            )
            .where(
                func.upper(cast(Any, WorkPackage).valid_time).is_(None),
                cast(Any, WorkPackage).deleted_at.is_(None),
            )
            .subquery()
        )

        return select(ScheduleBaseline, wp_subq.c.work_package_name).join(
            wp_subq,
            wp_subq.c.schedule_baseline_id == ScheduleBaseline.schedule_baseline_id,
        )

    async def get_baselines_for_work_packages(
        self,
        work_package_ids: list[UUID],
        branch: str = "main",
        as_of: datetime | None = None,
    ) -> dict[UUID, ScheduleBaseline]:
        """Get schedule baselines for multiple work packages efficiently.

        Args:
            work_package_ids: List of work package UUIDs
            branch: Branch name (default: "main")
            as_of: Optional timestamp for time-travel query (None = current)

        Returns:
            Dictionary mapping work_package_id to ScheduleBaseline
        """
        if not work_package_ids:
            return {}

        stmt = (
            select(WorkPackage.work_package_id, ScheduleBaseline)
            .join(
                ScheduleBaseline,
                WorkPackage.schedule_baseline_id
                == ScheduleBaseline.schedule_baseline_id,
            )
            .where(
                WorkPackage.work_package_id.in_(work_package_ids),
                WorkPackage.branch == branch,
                cast(Any, WorkPackage).deleted_at.is_(None),
                ScheduleBaseline.branch == branch,
                cast(Any, ScheduleBaseline).deleted_at.is_(None),
            )
        )

        if as_of is not None:
            from sqlalchemy import cast as sql_cast
            from sqlalchemy import or_
            from sqlalchemy.dialects.postgresql import TIMESTAMP

            as_of_tstz = sql_cast(as_of, TIMESTAMP(timezone=True))
            stmt = stmt.where(
                WorkPackage.valid_time.op("@>")(as_of_tstz),
                func.lower(WorkPackage.valid_time) <= as_of_tstz,
                or_(
                    cast(Any, WorkPackage).deleted_at.is_(None),
                    cast(Any, WorkPackage).deleted_at > as_of_tstz,
                ),
                ScheduleBaseline.valid_time.op("@>")(as_of_tstz),
                func.lower(ScheduleBaseline.valid_time) <= as_of_tstz,
                or_(
                    cast(Any, ScheduleBaseline).deleted_at.is_(None),
                    cast(Any, ScheduleBaseline).deleted_at > as_of_tstz,
                ),
            )
        else:
            stmt = stmt.where(
                func.upper(cast(Any, WorkPackage).valid_time).is_(None),
                func.upper(cast(Any, ScheduleBaseline).valid_time).is_(None),
            )

        result = await self.session.execute(stmt)

        baselines = {}
        for row in result.all():
            wp_id, baseline = row
            baselines[wp_id] = baseline

        return baselines

    # --- Backward-compatible aliases ---

    async def get_for_cost_element(
        self, cost_element_id: UUID, branch: str = "main"
    ) -> ScheduleBaseline | None:
        """Backward-compatible alias for get_for_work_package().

        Args:
            cost_element_id: Treated as work_package_id for migration purposes.
            branch: Branch name (default: "main")

        Returns:
            ScheduleBaseline if found, None otherwise
        """
        return await self.get_for_work_package(cost_element_id, branch=branch)

    async def get_baselines_for_cost_elements(
        self,
        cost_element_ids: list[UUID],
        branch: str = "main",
        as_of: datetime | None = None,
    ) -> dict[UUID, ScheduleBaseline]:
        """Backward-compatible alias for get_baselines_for_work_packages().

        Args:
            cost_element_ids: Treated as work_package_ids for migration purposes.
            branch: Branch name (default: "main")
            as_of: Optional timestamp for time-travel query (None = current)

        Returns:
            Dictionary mapping work_package_id to ScheduleBaseline
        """
        return await self.get_baselines_for_work_packages(
            cost_element_ids, branch=branch, as_of=as_of
        )
