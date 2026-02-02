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
from app.models.schemas.schedule_baseline import ScheduleBaselineCreate, ScheduleBaselineUpdate


class BaselineAlreadyExistsError(Exception):
    """Exception raised when attempting to create a duplicate schedule baseline for a cost element.

    Each cost element can have exactly one schedule baseline. This exception is raised when
    attempting to create a second baseline for a cost element that already has one.

    Attributes:
        cost_element_id: The UUID of the cost element that already has a baseline
        branch: The branch where the duplicate was detected (default: "main")
    """

    def __init__(self, cost_element_id: UUID, branch: str = "main") -> None:
        """Initialize the exception with cost element ID and branch.

        Args:
            cost_element_id: The UUID of the cost element with existing baseline
            branch: The branch where the duplicate was detected
        """
        self.cost_element_id = cost_element_id
        self.branch = branch
        super().__init__(
            f"Schedule baseline already exists for cost element {cost_element_id} "
            f"in branch '{branch}'. Each cost element can have exactly one baseline."
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
        branch: str = "main",
    ) -> ScheduleBaseline:
        """Create a new ScheduleBaseline from a schema.

        Args:
            create_schema: ScheduleBaselineCreate schema with entity data
            actor_id: User creating the baseline
            branch: Branch name (default: "main")

        Returns:
            Created ScheduleBaseline
        """
        # Extract control_date from schema if present
        control_date = getattr(create_schema, "control_date", None)
        from uuid import uuid4

        root_id = create_schema.schedule_baseline_id or uuid4()

        return await self.create_root(
            root_id=root_id,
            actor_id=actor_id,
            control_date=control_date,
            branch=branch,
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

    async def update(  # type: ignore[override]
        self,
        root_id: UUID,
        baseline_in: ScheduleBaselineUpdate,
        actor_id: UUID,
    ) -> ScheduleBaseline:
        """Update schedule baseline using UpdateVersionCommand.

        Args:
            root_id: The schedule baseline to update
            baseline_in: The update data
            actor_id: The user making the update
        """
        # Extract control_date and branch from schema
        control_date = baseline_in.control_date
        branch = baseline_in.branch or "main"

        # Dump update data and exclude metadata (not entity fields)
        update_data = baseline_in.model_dump(
            exclude_unset=True,
            exclude={"control_date", "branch"},
        )

        # Custom command class to handle branch filtering
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

    async def get_for_cost_element(
        self, cost_element_id: UUID, branch: str = "main"
    ) -> ScheduleBaseline | None:
        """Get the schedule baseline for a specific cost element.

        Uses the inverted relationship (cost_elements.schedule_baseline_id)
        to find the single baseline associated with the cost element.

        Args:
            cost_element_id: The UUID of the cost element
            branch: Branch name (default: "main")

        Returns:
            ScheduleBaseline if found, None otherwise
        """
        # First, get the cost element's schedule_baseline_id
        ce_stmt = select(CostElement.schedule_baseline_id).where(
            CostElement.cost_element_id == cost_element_id,
            CostElement.branch == branch,
            func.upper(cast(Any, CostElement).valid_time).is_(None),
            cast(Any, CostElement).deleted_at.is_(None),
        )
        ce_result = await self.session.execute(ce_stmt)
        schedule_baseline_id = ce_result.scalar_one_or_none()

        # If no baseline ID, return None
        if schedule_baseline_id is None:
            return None

        # Get the baseline using the ID
        return await self.get_by_id(schedule_baseline_id, branch=branch)

    async def ensure_exists(
        self,
        cost_element_id: UUID,
        actor_id: UUID,
        branch: str = "main",
        control_date: datetime | None = None,
    ) -> ScheduleBaseline:
        """Ensure a schedule baseline exists for the cost element.

        Creates a default baseline if none exists, otherwise returns the existing one.

        Args:
            cost_element_id: The UUID of the cost element
            actor_id: User creating the baseline if needed
            branch: Branch name (default: "main")
            control_date: Optional control date for valid_time

        Returns:
            ScheduleBaseline (existing or newly created)
        """
        # Check if baseline already exists
        existing = await self.get_for_cost_element(cost_element_id, branch=branch)
        if existing is not None:
            return existing

        # Create default baseline
        from datetime import UTC, timedelta
        from uuid import uuid4

        now = control_date or datetime.now(UTC)
        baseline_id = uuid4()

        baseline = await self.create_root(
            root_id=baseline_id,
            actor_id=actor_id,
            control_date=control_date,
            branch=branch,
            cost_element_id=cost_element_id,
            name="Default Schedule",
            start_date=now,
            end_date=now + timedelta(days=90),
            progression_type="LINEAR",
        )

        # Update cost element to reference the new baseline
        ce_stmt = (
            select(CostElement)
            .where(
                CostElement.cost_element_id == cost_element_id,
                CostElement.branch == branch,
                func.upper(cast(Any, CostElement).valid_time).is_(None),
                cast(Any, CostElement).deleted_at.is_(None),
            )
            .order_by(cast(Any, CostElement).valid_time.desc())
            .limit(1)
        )
        ce_result = await self.session.execute(ce_stmt)
        cost_element = ce_result.scalar_one_or_none()

        if cost_element:
            cost_element.schedule_baseline_id = baseline_id
            await self.session.flush()

        return baseline

    async def create_for_cost_element(
        self,
        cost_element_id: UUID,
        actor_id: UUID,
        name: str,
        start_date: datetime,
        end_date: datetime,
        progression_type: str = "LINEAR",
        description: str | None = None,
        branch: str = "main",
        control_date: datetime | None = None,
    ) -> ScheduleBaseline:
        """Create a schedule baseline for a specific cost element.

        Validates that no duplicate baseline exists for the cost element
        in the specified branch before creating.

        Args:
            cost_element_id: The UUID of the cost element
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
            BaselineAlreadyExistsError: If a baseline already exists for this cost element
        """
        # Check for existing baseline
        existing = await self.get_for_cost_element(cost_element_id, branch=branch)
        if existing is not None:
            raise BaselineAlreadyExistsError(
                cost_element_id=cost_element_id, branch=branch
            )

        # Create the baseline
        from uuid import uuid4

        baseline_id = uuid4()
        baseline = await self.create_root(
            root_id=baseline_id,
            actor_id=actor_id,
            control_date=control_date,
            branch=branch,
            cost_element_id=cost_element_id,
            name=name,
            start_date=start_date,
            end_date=end_date,
            progression_type=progression_type,
            description=description,
        )

        # Update cost element to reference the new baseline
        ce_stmt = (
            select(CostElement)
            .where(
                CostElement.cost_element_id == cost_element_id,
                CostElement.branch == branch,
                func.upper(cast(Any, CostElement).valid_time).is_(None),
                cast(Any, CostElement).deleted_at.is_(None),
            )
            .order_by(cast(Any, CostElement).valid_time.desc())
            .limit(1)
        )
        ce_result = await self.session.execute(ce_stmt)
        cost_element = ce_result.scalar_one_or_none()

        if cost_element:
            cost_element.schedule_baseline_id = baseline_id
            await self.session.flush()

        return baseline

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
