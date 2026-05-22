"""Work Package Service - versionable work package management."""

from datetime import datetime
from decimal import Decimal
from typing import Any, cast
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import COQCategory, WorkPackageStatus, WorkPackageType
from app.core.versioning.commands import (
    CreateVersionCommand,
    SoftDeleteCommand,
    UpdateVersionCommand,
)
from app.core.versioning.service import TemporalService
from app.models.domain.cost_element import CostElement
from app.models.domain.cost_registration import CostRegistration
from app.models.domain.wbe import WBE
from app.models.domain.work_package import WorkPackage
from app.models.schemas.work_package import (
    COQMetrics,
    COQTrendGranularity,
    COQTrendPoint,
    COQTrendResponse,
    QualityCostAllocation,
    QualityCostAllocationRead,
    WorkPackageCreate,
    WorkPackageSummary,
    WorkPackageUpdate,
)


class WorkPackageService(TemporalService[WorkPackage]):  # type: ignore[type-var,unused-ignore]
    """Service for WorkPackage management (versionable, not branchable).

    Work packages are project-scoped cost grouping mechanisms. They support
    multiple types (quality_impact, site_visit, etc.) via STI.
    They are versionable (NOT branchable) -- financial facts are
    global across branches.
    """

    def __init__(self, db: AsyncSession) -> None:
        """Initialize service with database session.

        Args:
            db: Async database session
        """
        super().__init__(WorkPackage, db)

    # --- CRUD operations ---

    async def create_work_package(
        self,
        data: WorkPackageCreate,
        actor_id: UUID,
        control_date: datetime | None = None,
    ) -> WorkPackage:
        """Create new work package with optional cost allocations.

        Args:
            data: The work package creation data.
            actor_id: The user creating the package.
            control_date: Optional control date for valid_time start.

        Returns:
            The created WorkPackage entity.

        Raises:
            ValueError: If the project does not exist or package_type is invalid.
        """
        if control_date is None:
            control_date = getattr(data, "control_date", None)

        # Validate package_type against enum
        self._validate_package_type(data.package_type)

        # Validate status
        self._validate_status(data.status)

        # Validate coq_category if provided
        if data.coq_category is not None:
            self._validate_coq_category(data.coq_category)

        impact_data = data.model_dump(
            exclude_unset=True,
            exclude={"control_date", "cost_allocations"},
        )

        root_id = data.work_package_id
        impact_data["work_package_id"] = root_id

        # Validate project exists
        await self._validate_project_exists(data.project_id)

        cmd = CreateVersionCommand(
            entity_class=WorkPackage,  # type: ignore[type-var,unused-ignore]
            root_id=root_id,
            actor_id=actor_id,
            control_date=control_date,
            **impact_data,
        )
        wp = await cmd.execute(self.session)

        # Create cost allocations if provided (only for quality_impact type)
        if data.cost_allocations:
            await self._create_cost_allocations(
                work_package_id=wp.work_package_id,
                external_event_id=data.external_event_id or "unknown",
                allocations_data=data.cost_allocations,
                actor_id=actor_id,
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

        Args:
            work_package_id: Root ID of the work package to update.
            data: The update data.
            actor_id: The user making the update.
            control_date: Optional control date for valid_time start.

        Returns:
            The updated WorkPackage entity (new version).
        """
        if control_date is None:
            control_date = getattr(data, "control_date", None)

        # Validate package_type if being changed
        if data.package_type is not None:
            self._validate_package_type(data.package_type)

        # Validate status if being changed
        if data.status is not None:
            self._validate_status(data.status)

        # Validate coq_category if being changed
        if data.coq_category is not None:
            self._validate_coq_category(data.coq_category)

        update_data = data.model_dump(
            exclude_unset=True,
            exclude={"control_date", "cost_allocations"},
        )

        # Validate project if changed
        if data.project_id is not None:
            await self._validate_project_exists(data.project_id)

        class WorkPackageUpdateCommand(UpdateVersionCommand[WorkPackage]):  # type: ignore[type-var,unused-ignore]
            def _root_field_name(self) -> str:
                return "work_package_id"

        cmd = WorkPackageUpdateCommand(
            entity_class=WorkPackage,  # type: ignore[type-var,unused-ignore]
            root_id=work_package_id,
            actor_id=actor_id,
            control_date=control_date,
            **update_data,
        )
        wp = await cmd.execute(self.session)

        # Replace cost allocations if provided
        if data.cost_allocations is not None:
            # Fetch the current WP to get external_event_id for description
            current_wp = await self.get_by_id(work_package_id)
            external_event_id = (
                current_wp.external_event_id if current_wp else "unknown"
            )
            await self._replace_cost_allocations(
                work_package_id=work_package_id,
                external_event_id=external_event_id or "unknown",
                allocations_data=data.cost_allocations,
                actor_id=actor_id,
            )

        return wp

    async def soft_delete(
        self,
        work_package_id: UUID,
        actor_id: UUID,
        control_date: datetime | None = None,
    ) -> None:
        """Soft delete a work package.

        Args:
            work_package_id: Root ID of the work package to delete.
            actor_id: The user performing the deletion.
            control_date: Optional control date for deletion.
        """

        class WorkPackageSoftDeleteCommand(SoftDeleteCommand[WorkPackage]):  # type: ignore[type-var,unused-ignore]
            def _root_field_name(self) -> str:
                return "work_package_id"

        cmd = WorkPackageSoftDeleteCommand(
            entity_class=WorkPackage,  # type: ignore[type-var,unused-ignore]
            root_id=work_package_id,
            actor_id=actor_id,
            control_date=control_date,
        )
        await cmd.execute(self.session)

    # --- Query operations ---

    async def get_by_id(self, work_package_id: UUID) -> WorkPackage | None:
        """Get current work package by root ID.

        Args:
            work_package_id: Root ID of the work package.

        Returns:
            The current version, or None if not found.
        """
        stmt = (
            select(WorkPackage)
            .where(
                WorkPackage.work_package_id == work_package_id,
                func.upper(WorkPackage.valid_time).is_(None),
                WorkPackage.deleted_at.is_(None),
            )
            .order_by(WorkPackage.valid_time.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_work_packages(
        self,
        project_id: UUID,
        skip: int = 0,
        limit: int = 100,
        coq_category: str | None = None,
        package_type: str | None = None,
        status: str | None = None,
        as_of: datetime | None = None,
    ) -> tuple[list[WorkPackage], int]:
        """Get work packages filtered by project with pagination.

        Args:
            project_id: Required project root ID filter.
            skip: Number of records to skip.
            limit: Maximum records to return.
            coq_category: Optional filter by COQ category (quality-specific).
            package_type: Optional filter by package type.
            status: Optional filter by status.
            as_of: Optional timestamp for time-travel query.

        Returns:
            Tuple of (list of work packages, total count).
        """
        stmt = select(WorkPackage).where(
            WorkPackage.project_id == project_id,
        )

        if as_of is not None:
            stmt = self._apply_bitemporal_filter(stmt, as_of)
        else:
            stmt = stmt.where(func.upper(WorkPackage.valid_time).is_(None))
            stmt = stmt.where(WorkPackage.deleted_at.is_(None))

        if coq_category is not None:
            stmt = stmt.where(WorkPackage.coq_category == coq_category)

        if package_type is not None:
            stmt = stmt.where(WorkPackage.package_type == package_type)

        if status is not None:
            stmt = stmt.where(WorkPackage.status == status)

        # Count query
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar_one()

        # Apply sorting and pagination
        stmt = stmt.order_by(WorkPackage.event_date.desc().nullslast())
        stmt = stmt.offset(skip).limit(limit)

        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    async def get_history(self, work_package_id: UUID) -> list[WorkPackage]:
        """Get full version history for a work package.

        Args:
            work_package_id: Root ID of the work package.

        Returns:
            All versions ordered by transaction time descending.
        """
        return await super().get_history(work_package_id)

    # --- Summary ---

    async def get_summary(
        self,
        project_id: UUID,
        as_of: datetime | None = None,
    ) -> WorkPackageSummary:
        """Get aggregated COQ summary for a project.

        Only includes quality_impact-typed work packages (backward-compatible).
        Uses SQL-level SUM/GROUP BY for efficiency.

        Args:
            project_id: Project root ID.
            as_of: Optional timestamp for time-travel query.

        Returns:
            WorkPackageSummary with cost breakdown and COQ ratio.
        """
        quality_type = WorkPackageType.QUALITY_IMPACT.value

        if as_of is not None:
            # Use a subquery approach for time-travel
            inner_stmt = select(WorkPackage).where(
                WorkPackage.project_id == project_id,
                WorkPackage.package_type == quality_type,
            )
            inner_stmt = self._apply_bitemporal_filter(inner_stmt, as_of)
            inner_subq = inner_stmt.subquery()

            total_stmt = select(
                func.coalesce(func.sum(inner_subq.c.cost_impact), Decimal("0")).label(
                    "total_cost"
                ),
                func.count().label("impact_count"),
                func.coalesce(func.sum(inner_subq.c.schedule_impact_days), 0).label(
                    "total_schedule_days"
                ),
            )
            total_result = await self.session.execute(total_stmt)
            total_row = total_result.one()

            # Category breakdown
            cat_stmt = select(
                inner_subq.c.coq_category,
                func.coalesce(func.sum(inner_subq.c.cost_impact), Decimal("0")).label(
                    "category_cost"
                ),
            ).group_by(inner_subq.c.coq_category)
            cat_result = await self.session.execute(cat_stmt)
            cat_costs = {
                row.coq_category: row.category_cost for row in cat_result.all()
            }
        else:
            # Current versions only
            current_filter = (
                func.upper(WorkPackage.valid_time).is_(None),
                WorkPackage.deleted_at.is_(None),
            )
            total_stmt = select(
                func.coalesce(func.sum(WorkPackage.cost_impact), Decimal("0")).label(
                    "total_cost"
                ),
                func.count().label("impact_count"),
                func.coalesce(func.sum(WorkPackage.schedule_impact_days), 0).label(
                    "total_schedule_days"
                ),
            ).where(
                WorkPackage.project_id == project_id,
                WorkPackage.package_type == quality_type,
                *current_filter,
            )
            total_result = await self.session.execute(total_stmt)
            total_row = total_result.one()

            cat_stmt = (
                select(
                    WorkPackage.coq_category,
                    func.coalesce(
                        func.sum(WorkPackage.cost_impact), Decimal("0")
                    ).label("category_cost"),
                )
                .where(
                    WorkPackage.project_id == project_id,
                    WorkPackage.package_type == quality_type,
                    *current_filter,
                )
                .group_by(WorkPackage.coq_category)
            )
            cat_result = await self.session.execute(cat_stmt)
            cat_costs = {
                row.coq_category: row.category_cost for row in cat_result.all()
            }

        total_cost = Decimal(str(total_row.total_cost))
        impact_count = total_row.impact_count
        total_schedule_days = int(total_row.total_schedule_days or 0)

        prevention_cost = Decimal(str(cat_costs.get("prevention", Decimal("0"))))
        appraisal_cost = Decimal(str(cat_costs.get("appraisal", Decimal("0"))))
        internal_failure_cost = Decimal(
            str(cat_costs.get("internal_failure", Decimal("0")))
        )
        external_failure_cost = Decimal(
            str(cat_costs.get("external_failure", Decimal("0")))
        )
        conformance_cost = prevention_cost + appraisal_cost
        nonconformance_cost = internal_failure_cost + external_failure_cost

        # Compute COQ ratio: total COQ cost / project budget
        coq_ratio = await self._compute_coq_ratio(project_id, total_cost)

        return WorkPackageSummary(
            total_cost=total_cost,
            conformance_cost=conformance_cost,
            nonconformance_cost=nonconformance_cost,
            prevention_cost=prevention_cost,
            appraisal_cost=appraisal_cost,
            internal_failure_cost=internal_failure_cost,
            external_failure_cost=external_failure_cost,
            total_schedule_days=total_schedule_days,
            impact_count=impact_count,
            coq_ratio=coq_ratio,
        )

    # --- COQ Metrics ---

    async def get_coq_metrics(
        self,
        project_id: UUID,
        as_of: datetime | None = None,
    ) -> COQMetrics:
        """Get COQ metrics complementing standard EVM indicators.

        Computes Cost of Quality metrics including CPQ (Cost of Poor Quality),
        CPIq, QPI (Quality Performance Index), and COQ ratio.
        Only includes quality_impact-typed work packages.

        Args:
            project_id: Project root ID.
            as_of: Optional timestamp for time-travel query.

        Returns:
            COQMetrics with all computed indicators.
        """
        quality_type = WorkPackageType.QUALITY_IMPACT.value

        # Build base filters for WorkPackage (quality_impact type only)
        wp_filters = [
            WorkPackage.project_id == project_id,
            WorkPackage.package_type == quality_type,
        ]
        if as_of is not None:
            wp_subq = select(WorkPackage).where(
                WorkPackage.project_id == project_id,
                WorkPackage.package_type == quality_type,
            )
            wp_subq = self._apply_bitemporal_filter(wp_subq, as_of)
            wp_subq = wp_subq.subquery()
        else:
            wp_filters.extend(
                [
                    func.upper(WorkPackage.valid_time).is_(None),
                    WorkPackage.deleted_at.is_(None),
                ]
            )

        # Build base filters for CostRegistration
        cr_filters_current = [
            func.upper(CostRegistration.valid_time).is_(None),
            CostRegistration.deleted_at.is_(None),
        ]

        # 1. Total COQ: sum of CR.amount where work_package_id IS NOT NULL
        if as_of is not None:
            total_coq_stmt = select(
                func.coalesce(func.sum(CostRegistration.amount), Decimal("0"))
            ).where(
                CostRegistration.work_package_id == wp_subq.c.work_package_id,
                *cr_filters_current,
            )
        else:
            total_coq_stmt = (
                select(func.coalesce(func.sum(CostRegistration.amount), Decimal("0")))
                .join(
                    WorkPackage,
                    CostRegistration.work_package_id == WorkPackage.work_package_id,
                )
                .where(
                    *wp_filters,
                    CostRegistration.work_package_id.isnot(None),
                    *cr_filters_current,
                )
            )
        total_coq_result = await self.session.execute(total_coq_stmt)
        total_coq = Decimal(str(total_coq_result.scalar_one()))

        # 2. CPQ: same but filtered by nonconformance
        if as_of is not None:
            cpq_stmt = select(
                func.coalesce(func.sum(CostRegistration.amount), Decimal("0"))
            ).where(
                CostRegistration.work_package_id == wp_subq.c.work_package_id,
                wp_subq.c.coq_category.in_(["internal_failure", "external_failure"]),
                *cr_filters_current,
            )
        else:
            cpq_stmt = (
                select(func.coalesce(func.sum(CostRegistration.amount), Decimal("0")))
                .join(
                    WorkPackage,
                    CostRegistration.work_package_id == WorkPackage.work_package_id,
                )
                .where(
                    *wp_filters,
                    WorkPackage.coq_category.in_(
                        ["internal_failure", "external_failure"]
                    ),
                    CostRegistration.work_package_id.isnot(None),
                    *cr_filters_current,
                )
            )
        cpq_result = await self.session.execute(cpq_stmt)
        cpq = Decimal(str(cpq_result.scalar_one()))

        # 3. Total AC: sum of ALL CostRegistration amounts for cost elements
        #    in this project (via CostElement -> WBE -> project)
        total_ac_stmt = (
            select(func.coalesce(func.sum(CostRegistration.amount), Decimal("0")))
            .join(
                CostElement,
                CostRegistration.cost_element_id == CostElement.cost_element_id,
            )
            .join(WBE, CostElement.wbe_id == WBE.wbe_id)
            .where(
                WBE.project_id == project_id,
                WBE.branch == "main",
                func.upper(cast(Any, WBE).valid_time).is_(None),
                cast(Any, WBE).deleted_at.is_(None),
                CostElement.branch == "main",
                func.upper(cast(Any, CostElement).valid_time).is_(None),
                cast(Any, CostElement).deleted_at.is_(None),
                *cr_filters_current,
            )
        )
        total_ac_result = await self.session.execute(total_ac_stmt)
        total_ac = Decimal(str(total_ac_result.scalar_one()))

        # 4. CPQ% = CPQ / Total AC * 100
        if total_ac > 0:
            cpq_percentage = (cpq / total_ac * Decimal("100")).quantize(Decimal("0.01"))
        else:
            cpq_percentage = Decimal("0.00")

        # 5. CPIq = CPQ / Total AC
        cpiq: Decimal | None = None
        if total_ac > 0:
            cpiq = (cpq / total_ac).quantize(Decimal("0.0001"))

        # 6. QPI via Nassar (2009) linear interpolation
        qpi: Decimal | None = None
        qpi_rating: str | None = None
        if total_ac > 0:
            qpi = self._compute_qpi(cpq_percentage)
            qpi_rating = self._qpi_rating(qpi)

        # 7. COQ ratio
        coq_ratio = await self._compute_coq_ratio(project_id, total_coq)

        return COQMetrics(
            total_coq=total_coq,
            cpq=cpq,
            cpq_percentage=cpq_percentage,
            cpiq=cpiq,
            qpi=qpi,
            qpi_rating=qpi_rating,
            total_ac=total_ac,
            coq_ratio=coq_ratio,
        )

    # --- COQ Trend ---

    async def get_coq_trend(
        self,
        project_id: UUID,
        granularity: COQTrendGranularity = COQTrendGranularity.MONTH,
        as_of: datetime | None = None,
    ) -> COQTrendResponse:
        """Get COQ cost trend over time bucketed by granularity.

        Uses date_trunc + group-by on time bucket and coq_category, then
        assembles COQTrendPoints in Python for clarity and correctness.

        Args:
            project_id: Project root ID.
            granularity: Time bucket size (week or month).
            as_of: Optional timestamp for time-travel query.

        Returns:
            COQTrendResponse with time-series data points.
        """
        quality_type = WorkPackageType.QUALITY_IMPACT.value
        trunc = "week" if granularity == COQTrendGranularity.WEEK else "month"

        # Determine date range from work package event dates
        range_stmt = select(
            func.coalesce(func.min(WorkPackage.event_date), datetime.now()),
            func.coalesce(func.max(WorkPackage.event_date), datetime.now()),
        ).where(
            WorkPackage.project_id == project_id,
            WorkPackage.package_type == quality_type,
            WorkPackage.event_date.isnot(None),
            func.upper(WorkPackage.valid_time).is_(None),
            WorkPackage.deleted_at.is_(None),
        )
        range_result = await self.session.execute(range_stmt)
        start_date, end_date = range_result.one()
        if as_of is not None and as_of < end_date:
            end_date = as_of

        # --- Actual costs (from CostRegistration) ---
        bucket_expr = func.date_trunc(trunc, WorkPackage.event_date)
        actual_stmt = (
            select(
                bucket_expr.label("bucket"),
                WorkPackage.coq_category,
                func.coalesce(func.sum(CostRegistration.amount), Decimal("0")).label(
                    "cost"
                ),
            )
            .join(
                WorkPackage,
                CostRegistration.work_package_id == WorkPackage.work_package_id,
            )
            .where(
                WorkPackage.project_id == project_id,
                WorkPackage.package_type == quality_type,
                WorkPackage.event_date.isnot(None),
                func.upper(WorkPackage.valid_time).is_(None),
                WorkPackage.deleted_at.is_(None),
                CostRegistration.work_package_id.isnot(None),
                func.upper(CostRegistration.valid_time).is_(None),
                CostRegistration.deleted_at.is_(None),
            )
            .group_by(
                bucket_expr,
                WorkPackage.coq_category,
            )
            .order_by(bucket_expr)
        )
        actual_result = await self.session.execute(actual_stmt)
        actual_rows = actual_result.all()

        # --- Planned costs (from cost_impact) ---
        planned_stmt = (
            select(
                bucket_expr.label("bucket"),
                WorkPackage.coq_category,
                func.coalesce(func.sum(WorkPackage.cost_impact), Decimal("0")).label(
                    "cost"
                ),
            )
            .where(
                WorkPackage.project_id == project_id,
                WorkPackage.package_type == quality_type,
                WorkPackage.event_date.isnot(None),
                func.upper(WorkPackage.valid_time).is_(None),
                WorkPackage.deleted_at.is_(None),
            )
            .group_by(
                bucket_expr,
                WorkPackage.coq_category,
            )
            .order_by(bucket_expr)
        )
        planned_result = await self.session.execute(planned_stmt)
        planned_rows = planned_result.all()

        # Assemble into COQTrendPoints grouped by bucket
        from collections import defaultdict

        actual_buckets: dict[datetime, dict[str, Decimal]] = defaultdict(
            lambda: {
                "prevention": Decimal("0"),
                "appraisal": Decimal("0"),
                "internal_failure": Decimal("0"),
                "external_failure": Decimal("0"),
            }
        )
        for row in actual_rows:
            cat = row.coq_category
            if cat and cat in actual_buckets[row.bucket]:
                actual_buckets[row.bucket][cat] = Decimal(str(row.cost))

        planned_buckets: dict[datetime, dict[str, Decimal]] = defaultdict(
            lambda: {
                "prevention": Decimal("0"),
                "appraisal": Decimal("0"),
                "internal_failure": Decimal("0"),
                "external_failure": Decimal("0"),
            }
        )
        for row in planned_rows:
            cat = row.coq_category
            if cat and cat in planned_buckets[row.bucket]:
                planned_buckets[row.bucket][cat] = Decimal(str(row.cost))

        all_dates = sorted(set(actual_buckets.keys()) | set(planned_buckets.keys()))

        points: list[COQTrendPoint] = []
        for bucket_date in all_dates:
            ac = actual_buckets[bucket_date]
            pc = planned_buckets[bucket_date]
            total_coq = sum(ac.values())
            total_planned = sum(pc.values())
            cpq = ac["internal_failure"] + ac["external_failure"]
            points.append(
                COQTrendPoint(
                    date=bucket_date,
                    planned_prevention=pc["prevention"],
                    planned_appraisal=pc["appraisal"],
                    planned_internal_failure=pc["internal_failure"],
                    planned_external_failure=pc["external_failure"],
                    total_planned=total_planned,
                    prevention=ac["prevention"],
                    appraisal=ac["appraisal"],
                    internal_failure=ac["internal_failure"],
                    external_failure=ac["external_failure"],
                    total_coq=total_coq,
                    cpq=cpq,
                )
            )

        return COQTrendResponse(
            granularity=granularity,
            points=points,
            start_date=start_date,
            end_date=end_date,
            total_points=len(points),
        )

    @staticmethod
    def _compute_qpi(cpq_percentage: Decimal) -> Decimal:
        """Compute Quality Performance Index using Nassar (2009) normalization.

        Uses linear interpolation within bands for smooth QPI values.

        Args:
            cpq_percentage: CPQ as a percentage of total actual cost.

        Returns:
            QPI value between 0.75 and 1.15.
        """
        # Define bands: (upper_bound_pct, qpi_at_upper, qpi_at_lower)
        # Bands from low CPQ% (good) to high CPQ% (bad)
        bands: list[tuple[Decimal, Decimal, Decimal]] = [
            (Decimal("0.5"), Decimal("1.15"), Decimal("1.15")),
            (Decimal("1.0"), Decimal("1.05"), Decimal("1.15")),
            (Decimal("2.0"), Decimal("0.95"), Decimal("1.05")),
            (Decimal("4.0"), Decimal("0.85"), Decimal("0.95")),
        ]

        if cpq_percentage <= Decimal("0.5"):
            return Decimal("1.15")

        prev_upper = Decimal("0.5")
        for upper, qpi_at_upper, qpi_at_lower in bands:
            if cpq_percentage <= upper:
                # Linear interpolation within this band
                fraction = (cpq_percentage - prev_upper) / (upper - prev_upper)
                return (
                    qpi_at_lower + fraction * (qpi_at_upper - qpi_at_lower)
                ).quantize(Decimal("0.01"))
            prev_upper = upper

        # Above 4.0%: linear extrapolation from the last band
        # At 4.0% QPI=0.85, slope from 2.0-4.0% band
        excess = cpq_percentage - Decimal("4.0")
        return (Decimal("0.85") - excess * Decimal("0.05")).quantize(Decimal("0.01"))

    @staticmethod
    def _qpi_rating(qpi: Decimal) -> str:
        """Map QPI value to human-readable rating.

        Args:
            qpi: Quality Performance Index value.

        Returns:
            Rating string.
        """
        if qpi > Decimal("1.05"):
            return "Outstanding"
        if qpi >= Decimal("0.95"):
            return "Within Target"
        if qpi >= Decimal("0.85"):
            return "Below Target"
        return "Poor Performance"

    # --- Allocation operations ---

    async def get_allocations(
        self,
        work_package_id: UUID,
    ) -> list[QualityCostAllocationRead]:
        """Get all cost allocation entries for a work package.

        Queries CostRegistration entries linked to the work package,
        joining with CostElement and WBE for display names.

        Args:
            work_package_id: Root ID of the parent work package.

        Returns:
            List of QualityCostAllocationRead entries.
        """
        stmt = (
            select(
                CostRegistration.cost_registration_id,
                CostRegistration.cost_element_id,
                CostRegistration.amount,
                CostRegistration.description,
                CostElement.name.label("cost_element_name"),
                WBE.code.label("wbe_code"),
            )
            .join(
                CostElement,
                CostRegistration.cost_element_id == CostElement.cost_element_id,
            )
            .join(WBE, CostElement.wbe_id == WBE.wbe_id)
            .where(
                CostRegistration.work_package_id == work_package_id,
                func.upper(CostRegistration.valid_time).is_(None),
                CostRegistration.deleted_at.is_(None),
                CostElement.branch == "main",
                func.upper(CostElement.valid_time).is_(None),
                CostElement.deleted_at.is_(None),
                WBE.branch == "main",
                func.upper(WBE.valid_time).is_(None),
                WBE.deleted_at.is_(None),
            )
            .order_by(CostRegistration.registration_date)
        )
        result = await self.session.execute(stmt)
        rows = result.all()

        return [
            QualityCostAllocationRead(
                cost_registration_id=row.cost_registration_id,
                cost_element_id=row.cost_element_id,
                amount=row.amount,
                description=row.description,
                cost_element_name=row.cost_element_name,
                wbe_code=row.wbe_code,
            )
            for row in rows
        ]

    async def upsert_allocations(
        self,
        work_package_id: UUID,
        allocations_data: list[QualityCostAllocation],
        actor_id: UUID,
    ) -> list[QualityCostAllocationRead]:
        """Replace all cost allocations for a work package.

        Deletes existing CostRegistration entries linked to the work package
        and creates new ones.

        Args:
            work_package_id: Root ID of the parent work package.
            allocations_data: New allocation entries to create.
            actor_id: The user performing the upsert.

        Returns:
            List of newly created allocation entries.
        """
        # Fetch WP for external_event_id (used in description)
        wp = await self.get_by_id(work_package_id)
        external_event_id = wp.external_event_id if wp else "unknown"

        return await self._replace_cost_allocations(
            work_package_id=work_package_id,
            external_event_id=external_event_id or "unknown",
            allocations_data=allocations_data,
            actor_id=actor_id,
        )

    async def compute_actual_cost(self, work_package_id: UUID) -> Decimal | None:
        """Compute actual cost from linked CostRegistration entries.

        Args:
            work_package_id: Root ID of the work package.

        Returns:
            Sum of all linked CostRegistration amounts, or None if no CRs exist.
        """
        stmt = select(func.sum(CostRegistration.amount)).where(
            CostRegistration.work_package_id == work_package_id,
            func.upper(CostRegistration.valid_time).is_(None),
            CostRegistration.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        value = result.scalar_one_or_none()
        if value is None:
            return None
        return Decimal(str(value))

    # --- Internal helpers ---

    @staticmethod
    def _validate_package_type(package_type: str) -> None:
        """Validate package_type against the closed enum.

        Args:
            package_type: The package type value to validate.

        Raises:
            ValueError: If the package_type is not a valid enum member.
        """
        valid_types = {t.value for t in WorkPackageType}
        if package_type not in valid_types:
            raise ValueError(
                f"Invalid package_type '{package_type}'. "
                f"Must be one of: {', '.join(sorted(valid_types))}"
            )

    @staticmethod
    def _validate_status(status: str) -> None:
        """Validate status against the closed enum.

        Args:
            status: The status value to validate.

        Raises:
            ValueError: If the status is not a valid enum member.
        """
        valid_statuses = {s.value for s in WorkPackageStatus}
        if status not in valid_statuses:
            raise ValueError(
                f"Invalid status '{status}'. "
                f"Must be one of: {', '.join(sorted(valid_statuses))}"
            )

    @staticmethod
    def _validate_coq_category(coq_category: str) -> None:
        """Validate coq_category against the COQCategory enum.

        Args:
            coq_category: The COQ category value to validate.

        Raises:
            ValueError: If the coq_category is not a valid enum member.
        """
        valid_categories = {c.value for c in COQCategory}
        if coq_category not in valid_categories:
            raise ValueError(
                f"Invalid coq_category '{coq_category}'. "
                f"Must be one of: {', '.join(sorted(valid_categories))}"
            )

    async def _validate_project_exists(self, project_id: UUID) -> None:
        """Validate that a project exists (current version on main branch).

        Args:
            project_id: Root ID of the project.

        Raises:
            ValueError: If the project does not exist.
        """
        from app.models.domain.project import Project

        stmt = (
            select(Project.id)
            .where(
                Project.project_id == project_id,
                func.upper(Project.valid_time).is_(None),
                Project.deleted_at.is_(None),
            )
            .limit(1)
        )
        result = await self.session.execute(stmt)
        if result.scalar_one_or_none() is None:
            raise ValueError(f"Project {project_id} not found")

    async def _create_cost_allocations(
        self,
        work_package_id: UUID,
        external_event_id: str,
        allocations_data: list[QualityCostAllocation],
        actor_id: UUID,
    ) -> list[CostRegistration]:
        """Create CostRegistration entries for a work package's allocations.

        Each allocation becomes a CostRegistration with work_package_id set.

        Args:
            work_package_id: Root ID of the parent work package.
            external_event_id: External event ID for traceability in description.
            allocations_data: Allocation data to create.
            actor_id: The user creating the allocations.

        Returns:
            List of created CostRegistration entities.
        """
        created: list[CostRegistration] = []
        for alloc in allocations_data:
            root_id = uuid4()
            cmd = CreateVersionCommand(
                entity_class=CostRegistration,  # type: ignore[type-var,unused-ignore]
                root_id=root_id,
                actor_id=actor_id,
                cost_registration_id=root_id,
                cost_element_id=alloc.cost_element_id,
                amount=alloc.amount,
                work_package_id=work_package_id,
                description=alloc.description
                or f"Quality cost allocation for {external_event_id}",
            )
            cr = await cmd.execute(self.session)
            created.append(cr)
        return created

    async def _replace_cost_allocations(
        self,
        work_package_id: UUID,
        external_event_id: str,
        allocations_data: list[QualityCostAllocation],
        actor_id: UUID,
    ) -> list[QualityCostAllocationRead]:
        """Delete existing allocations and create new ones.

        Uses soft-delete on existing CRs linked to the work package,
        then creates new CostRegistration entries.

        Args:
            work_package_id: Root ID of the parent work package.
            external_event_id: External event ID for traceability in description.
            allocations_data: New allocation data.
            actor_id: The user performing the replacement.

        Returns:
            List of newly created QualityCostAllocationRead entries.
        """
        # Soft-delete existing CRs linked to this work package
        from app.core.versioning.commands import SoftDeleteCommand

        existing_stmt = select(CostRegistration).where(
            CostRegistration.work_package_id == work_package_id,
            CostRegistration.deleted_at.is_(None),
        )
        existing_result = await self.session.execute(existing_stmt)
        existing_crs = existing_result.scalars().all()

        for cr in existing_crs:

            class CRSoftDeleteCommand(SoftDeleteCommand[CostRegistration]):  # type: ignore[type-var,unused-ignore]
                def _root_field_name(self) -> str:
                    return "cost_registration_id"

            cmd = CRSoftDeleteCommand(
                entity_class=CostRegistration,  # type: ignore[type-var,unused-ignore]
                root_id=cr.cost_registration_id,
                actor_id=actor_id,
            )
            await cmd.execute(self.session)

        # Create new allocations
        await self._create_cost_allocations(
            work_package_id=work_package_id,
            external_event_id=external_event_id,
            allocations_data=allocations_data,
            actor_id=actor_id,
        )

        # Return newly created allocations as read models
        return await self.get_allocations(work_package_id)

    async def _compute_coq_ratio(
        self, project_id: UUID, total_coq_cost: Decimal
    ) -> Decimal | None:
        """Compute COQ ratio as total COQ cost / project budget.

        Project budget = sum of cost_element.budget_amount for all cost
        elements in the project on the main branch.

        Args:
            project_id: Project root ID.
            total_coq_cost: Total COQ cost.

        Returns:
            Ratio as a percentage (e.g., 12.5), or None if no budget.
        """
        budget_stmt = (
            select(func.coalesce(func.sum(CostElement.budget_amount), Decimal("0")))
            .join(WBE, CostElement.wbe_id == WBE.wbe_id)
            .where(
                WBE.project_id == project_id,
                WBE.branch == "main",
                func.upper(cast(Any, WBE).valid_time).is_(None),
                cast(Any, WBE).deleted_at.is_(None),
                CostElement.branch == "main",
                func.upper(cast(Any, CostElement).valid_time).is_(None),
                cast(Any, CostElement).deleted_at.is_(None),
            )
        )
        budget_result = await self.session.execute(budget_stmt)
        project_budget = Decimal(str(budget_result.scalar_one()))

        if project_budget <= 0:
            return None

        return (total_coq_cost / project_budget * Decimal("100")).quantize(
            Decimal("0.01")
        )
