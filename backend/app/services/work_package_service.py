"""Work Package Service - ANSI-748 PMI budget holder.

Extends BranchableService for Work Package operations within the ANSI-748 model.
Work Packages are the primary budget holders, belonging to Control Accounts.
They replace the old QualityImpact concept for the ANSI-748 domain.

This service is distinct from the old work_package_service.py which handled
QualityImpact entities. This is the ANSI-748 PMI Work Package.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, cast
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.branching.service import BranchableService
from app.core.versioning.commands import CreateVersionCommand
from app.core.versioning.enums import BranchMode
from app.models.domain.control_account import ControlAccount
from app.models.domain.cost_element import CostElement
from app.models.domain.cost_registration import CostRegistration
from app.models.domain.wbs_element import WBSElement
from app.models.domain.work_package import WorkPackage
from app.models.schemas.work_package import WorkPackageCreate, WorkPackageUpdate


class WorkPackageService(BranchableService[WorkPackage]):  # type: ignore[type-var,unused-ignore]
    """Service for Work Package entity operations (PMI budget holder).

    Extends BranchableService with work-package-specific methods including
    budget status computation and breadcrumb navigation through the
    ControlAccount -> WBSElement -> Project hierarchy.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(WorkPackage, session)

    async def create_root(
        self,
        root_id: UUID,
        actor_id: UUID,
        control_date: datetime | None = None,
        branch: str = "main",
        **data: Any,
    ) -> WorkPackage:
        """Create the initial version of a Work Package."""
        data["work_package_id"] = root_id

        cmd = CreateVersionCommand(
            entity_class=WorkPackage,
            root_id=root_id,
            actor_id=actor_id,
            control_date=control_date,
            branch=branch,
            **data,
        )
        return await cmd.execute(self.session)

    async def create_work_package(
        self,
        data: WorkPackageCreate,
        actor_id: UUID,
        control_date: datetime | None = None,
    ) -> WorkPackage:
        """Create new work package with auto-creation of schedule baseline and forecast.

        Both a ScheduleBaseline and a Forecast are always created alongside the
        work package. If no schedule dates are provided, sensible defaults are
        used (control_date or now as start, start + 90 days as end). If no
        forecast params are provided, the budget_amount is used as EAC.

        Args:
            data: Work package creation data.
            actor_id: User creating the package.
            control_date: Optional control date for valid_time start.

        Returns:
            The created WorkPackage entity.
        """
        if control_date is None:
            control_date = getattr(data, "control_date", None)

        wp_data = data.model_dump(
            exclude_unset=True,
            exclude={
                "control_date",
                "schedule_start_date",
                "schedule_end_date",
                "schedule_progression_type",
                "eac_amount",
                "basis_of_estimate",
            },
        )

        root_id = data.work_package_id
        wp_data["work_package_id"] = root_id

        # Validate Control Account existence
        ca_exists = await self.session.execute(
            select(ControlAccount.id)
            .where(
                ControlAccount.control_account_id == data.control_account_id,
                func.upper(cast(Any, ControlAccount).valid_time).is_(None),
                cast(Any, ControlAccount).deleted_at.is_(None),
            )
            .limit(1)
        )
        if not ca_exists.scalar_one_or_none():
            raise ValueError(f"Control Account {data.control_account_id} not found")

        cmd = CreateVersionCommand(
            entity_class=WorkPackage,
            root_id=root_id,
            actor_id=actor_id,
            control_date=control_date,
            **wp_data,
        )
        wp = await cmd.execute(self.session)

        # Always auto-create schedule baseline
        from app.services.schedule_baseline_service import ScheduleBaselineService

        sb_service = ScheduleBaselineService(self.session)
        await sb_service.ensure_exists(
            work_package_id=root_id,
            actor_id=actor_id,
            branch=data.branch,
            control_date=control_date,
            start_date=data.schedule_start_date,
            end_date=data.schedule_end_date,
            progression_type=data.schedule_progression_type,
        )

        # Always auto-create forecast
        from app.services.forecast_service import ForecastService

        fc_service = ForecastService(self.session)
        eac_amount = (
            data.eac_amount if data.eac_amount is not None else data.budget_amount
        )
        basis_of_estimate = data.basis_of_estimate or "Initial forecast"
        await fc_service.create_for_work_package(
            work_package_id=root_id,
            actor_id=actor_id,
            branch=data.branch,
            eac_amount=eac_amount,
            basis_of_estimate=basis_of_estimate,
            control_date=control_date,
        )

        return wp

    async def update_work_package(
        self,
        work_package_id: UUID,
        data: WorkPackageUpdate,
        actor_id: UUID,
        control_date: datetime | None = None,
    ) -> WorkPackage:
        """Update work package, creating a new version.

        Also propagates schedule baseline and forecast updates if the
        corresponding fields are present in the update data. If no
        baseline or forecast exists yet, one is created first.

        Args:
            work_package_id: Root ID of the work package.
            data: Update data.
            actor_id: User making the update.
            control_date: Optional control date.

        Returns:
            Updated WorkPackage entity.
        """
        if control_date is None:
            control_date = getattr(data, "control_date", None)

        update_data = data.model_dump(exclude_unset=True)
        update_data.pop("control_date", None)
        branch = update_data.pop("branch", None) or "main"

        # Extract schedule/forecast fields before WP update
        schedule_fields = {
            k: v
            for k, v in (
                ("name", update_data.pop("schedule_name", None)),
                ("start_date", update_data.pop("schedule_start_date", None)),
                ("end_date", update_data.pop("schedule_end_date", None)),
                (
                    "progression_type",
                    update_data.pop("schedule_progression_type", None),
                ),
                ("description", update_data.pop("schedule_description", None)),
            )
            if v is not None
        }
        forecast_fields: dict[str, Any] = {}
        for field in ("eac_amount", "basis_of_estimate"):
            if field in update_data:
                forecast_fields[field] = update_data.pop(field)

        from app.core.branching.commands import UpdateCommand

        cmd = UpdateCommand(  # type: ignore[type-var]
            entity_class=WorkPackage,
            root_id=work_package_id,
            actor_id=actor_id,
            branch=branch,
            control_date=control_date,
            updates=update_data,
        )
        wp = await cmd.execute(self.session)

        # Propagate schedule baseline updates
        if schedule_fields:
            from app.services.schedule_baseline_service import ScheduleBaselineService

            sb_service = ScheduleBaselineService(self.session)
            # Ensure baseline exists, then update it
            baseline = await sb_service.ensure_exists(
                work_package_id=work_package_id,
                actor_id=actor_id,
                branch=branch,
                control_date=control_date,
            )
            if schedule_fields:
                from app.models.schemas.schedule_baseline import ScheduleBaselineUpdate

                sb_update = ScheduleBaselineUpdate(
                    **schedule_fields,
                    branch=branch,
                    control_date=control_date,
                )
                await sb_service.update_schedule_baseline(
                    root_id=baseline.schedule_baseline_id,
                    baseline_in=sb_update,
                    actor_id=actor_id,
                    branch=branch,
                    control_date=control_date,
                )

        # Propagate forecast updates
        if forecast_fields:
            from app.services.forecast_service import ForecastService

            fc_service = ForecastService(self.session)
            # Ensure forecast exists, then update it
            forecast = await fc_service.ensure_exists(
                work_package_id=work_package_id,
                actor_id=actor_id,
                branch=branch,
                budget_amount=wp.budget_amount,
                control_date=control_date,
            )
            if forecast_fields:
                from app.models.schemas.forecast import ForecastUpdate

                fc_update = ForecastUpdate(
                    **forecast_fields,
                    branch=branch,
                    control_date=control_date,
                )
                await fc_service.update_forecast(
                    forecast_id=forecast.forecast_id,
                    forecast_in=fc_update,
                    actor_id=actor_id,
                    control_date=control_date,
                )

        return wp

    async def get_work_packages(
        self,
        control_account_id: UUID | None = None,
        status: str | None = None,
        skip: int = 0,
        limit: int = 100,
        branch: str = "main",
        branch_mode: BranchMode = BranchMode.MERGED,
        as_of: datetime | None = None,
    ) -> tuple[list[WorkPackage], int]:
        """Get work packages with optional filtering and pagination.

        Args:
            control_account_id: Optional Control Account filter.
            status: Optional status filter.
            skip: Records to skip.
            limit: Maximum records.
            branch: Branch name.
            branch_mode: Branch isolation mode.
            as_of: Optional timestamp for time-travel.

        Returns:
            Tuple of (list of work packages, total count).
        """
        stmt = select(WorkPackage)

        stmt = self._apply_branch_mode_filter(
            stmt, branch=branch, branch_mode=branch_mode, as_of=as_of
        )

        if as_of:
            stmt = self._apply_bitemporal_filter(stmt, as_of)
        else:
            stmt = stmt.where(
                func.upper(cast(Any, WorkPackage).valid_time).is_(None),
                cast(Any, WorkPackage).deleted_at.is_(None),
            )

        if control_account_id is not None:
            stmt = stmt.where(WorkPackage.control_account_id == control_account_id)

        if status is not None:
            stmt = stmt.where(WorkPackage.status == status)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar_one()

        stmt = stmt.order_by(cast(Any, WorkPackage).valid_time.desc())
        stmt = stmt.offset(skip).limit(limit)

        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    async def get_breadcrumb(self, work_package_id: UUID) -> dict[str, Any]:
        """Get breadcrumb trail for a Work Package.

        Hierarchy: Project -> WBSElement -> ControlAccount -> WorkPackage

        Args:
            work_package_id: Work Package root ID.

        Returns:
            Dict with breadcrumb hierarchy.

        Raises:
            ValueError: If Work Package not found.
        """
        from app.models.domain.project import Project

        # Get current work package
        wp_stmt = (
            select(WorkPackage)
            .where(
                WorkPackage.work_package_id == work_package_id,
                func.upper(cast(Any, WorkPackage).valid_time).is_(None),
                cast(Any, WorkPackage).deleted_at.is_(None),
            )
            .limit(1)
        )
        wp_result = await self.session.execute(wp_stmt)
        wp = wp_result.scalar_one_or_none()
        if not wp:
            raise ValueError(f"Work Package {work_package_id} not found")

        # Get Control Account
        ca_stmt = (
            select(ControlAccount)
            .where(
                ControlAccount.control_account_id == wp.control_account_id,
                func.upper(cast(Any, ControlAccount).valid_time).is_(None),
                cast(Any, ControlAccount).deleted_at.is_(None),
            )
            .limit(1)
        )
        ca_result = await self.session.execute(ca_stmt)
        ca = ca_result.scalar_one_or_none()

        if not ca:
            raise ValueError(f"Control Account {wp.control_account_id} not found")

        # Get WBS Element
        wbs_stmt = (
            select(WBSElement)
            .where(
                WBSElement.wbs_element_id == ca.wbs_element_id,
                func.upper(cast(Any, WBSElement).valid_time).is_(None),
                cast(Any, WBSElement).deleted_at.is_(None),
            )
            .limit(1)
        )
        wbs_result = await self.session.execute(wbs_stmt)
        wbs = wbs_result.scalar_one_or_none()

        if not wbs:
            raise ValueError(f"WBS Element {ca.wbs_element_id} not found")

        # Get Project
        project_stmt = (
            select(Project)
            .where(
                Project.project_id == wbs.project_id,
                func.upper(cast(Any, Project).valid_time).is_(None),
                cast(Any, Project).deleted_at.is_(None),
            )
            .limit(1)
        )
        project_result = await self.session.execute(project_stmt)
        project = project_result.scalar_one_or_none()

        if not project:
            raise ValueError(f"Project {wbs.project_id} not found")

        return {
            "project": {
                "id": project.id,
                "project_id": project.project_id,
                "code": project.code,
                "name": project.name,
            },
            "wbs_element": {
                "id": wbs.id,
                "wbs_element_id": wbs.wbs_element_id,
                "code": wbs.code,
                "name": wbs.name,
            },
            "control_account": {
                "id": ca.id,
                "control_account_id": ca.control_account_id,
                "name": ca.name,
            },
            "work_package": {
                "id": wp.id,
                "work_package_id": wp.work_package_id,
                "code": wp.code,
                "name": wp.name,
            },
        }

    async def get_budget_status(
        self,
        work_package_id: UUID,
        as_of: datetime | None = None,
        branch: str = "main",
    ) -> dict[str, Any]:
        """Get budget status for a Work Package.

        Compares budget_amount against sum of CostRegistration amounts
        through CostElements under this WorkPackage.

        Args:
            work_package_id: Work Package root ID.
            as_of: Optional timestamp for time-travel.
            branch: Branch name.

        Returns:
            Dict with budget, used, remaining, percentage.

        Raises:
            ValueError: If Work Package not found.
        """
        # Get the work package budget
        wp_stmt = select(WorkPackage).where(
            WorkPackage.work_package_id == work_package_id,
            WorkPackage.branch == branch,
            func.upper(cast(Any, WorkPackage).valid_time).is_(None),
            cast(Any, WorkPackage).deleted_at.is_(None),
        )
        wp_result = await self.session.execute(wp_stmt.limit(1))
        wp = wp_result.scalar_one_or_none()

        if wp is None and branch != "main":
            wp_stmt_main = select(WorkPackage).where(
                WorkPackage.work_package_id == work_package_id,
                WorkPackage.branch == "main",
                func.upper(cast(Any, WorkPackage).valid_time).is_(None),
                cast(Any, WorkPackage).deleted_at.is_(None),
            )
            wp_result_main = await self.session.execute(wp_stmt_main.limit(1))
            wp = wp_result_main.scalar_one_or_none()

        if wp is None:
            raise ValueError(f"Work Package {work_package_id} not found")

        budget = wp.budget_amount

        # Sum actual costs through CostElements under this WorkPackage
        used_stmt = select(func.sum(CostRegistration.amount)).where(
            CostRegistration.cost_element_id.in_(
                select(CostElement.cost_element_id).where(
                    CostElement.work_package_id == work_package_id,
                )
            )
        )

        if as_of is not None:
            used_stmt = self._apply_bitemporal_filter(used_stmt, as_of)
        else:
            used_stmt = used_stmt.where(
                func.upper(CostRegistration.valid_time).is_(None),
                CostRegistration.deleted_at.is_(None),
            )

        used_result = await self.session.execute(used_stmt)
        used = Decimal(str(used_result.scalar_one() or 0))

        remaining = budget - used
        percentage = (used / budget * Decimal("100")) if budget > 0 else Decimal("0")

        return {
            "work_package_id": work_package_id,
            "budget": budget,
            "used": used,
            "remaining": remaining,
            "percentage": percentage,
        }

    async def get_as_of_batch(
        self,
        entity_ids: list[UUID],
        as_of: datetime | None = None,
        branch: str = "main",
        branch_mode: BranchMode | None = None,
    ) -> dict[UUID, WorkPackage]:
        """Bulk time-travel fetch for multiple work packages.

        Args:
            entity_ids: List of root IDs.
            as_of: Timestamp for time-travel (None = current).
            branch: Branch name.
            branch_mode: Branch resolution mode.

        Returns:
            Dictionary mapping work_package_id to WorkPackage.
        """
        if not entity_ids:
            return {}

        stmt = (
            select(WorkPackage)
            .where(WorkPackage.work_package_id.in_(entity_ids))
            .where(cast(Any, WorkPackage).deleted_at.is_(None))
        )

        if as_of is not None:
            stmt = self._apply_bitemporal_filter(stmt, as_of)
        else:
            stmt = stmt.where(func.upper(cast(Any, WorkPackage).valid_time).is_(None))

        rows = await self.session.execute(stmt)
        return {e.work_package_id: e for e in rows.scalars()}
