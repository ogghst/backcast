"""Cost Event Service - quality and cost event tracking.

Extends TemporalService (NOT BranchableService) for Cost Event operations.
Cost Events are versionable but NOT branchable -- events are global facts.

Provides COQ (Cost of Quality) metrics, trend analysis, and cost allocation
management. Preserves the COQ formulas from the old WorkPackageService:
- Total COQ = sum of CostRegistration.amount where cost_event_id IS NOT NULL and event type is_quality
- CPQ = sum of CostRegistration.amount where coq_category in (internal_failure, external_failure)
- CPIq = CPQ / Total AC
- QPI via Nassar (2009) linear interpolation
- COQ ratio = Total COQ / Project budget
"""

from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from typing import Any, cast
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.versioning.commands import (
    CreateVersionCommand,
    SoftDeleteCommand,
    UpdateVersionCommand,
)
from app.core.versioning.service import TemporalService
from app.models.domain.control_account import ControlAccount
from app.models.domain.cost_element import CostElement
from app.models.domain.cost_event import CostEvent
from app.models.domain.cost_event_type import CostEventType
from app.models.domain.cost_registration import CostRegistration
from app.models.domain.wbs_element import WBSElement
from app.models.domain.work_package import WorkPackage
from app.models.schemas.cost_event import (
    COQMetrics,
    COQTrendGranularity,
    COQTrendPoint,
    COQTrendResponse,
    CostEventCreate,
    CostEventSummary,
    CostEventUpdate,
    QualityCostAllocation,
    QualityCostAllocationRead,
)


class CostEventService(TemporalService[CostEvent]):  # type: ignore[type-var,unused-ignore]
    """Service for Cost Event entity operations.

    Cost Events track quality events and cost impacts for projects.
    Versionable but NOT branchable (events are global facts).
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(CostEvent, session)

    # --- CRUD ---

    async def create_cost_event(
        self,
        data: CostEventCreate,
        actor_id: UUID,
    ) -> CostEvent:
        """Create new cost event with optional cost allocations.

        Args:
            data: Cost event creation data.
            actor_id: User creating the event.

        Returns:
            Created CostEvent entity.
        """
        control_date = getattr(data, "control_date", None)
        event_data = data.model_dump(
            exclude_unset=True,
            exclude={"control_date", "cost_allocations"},
        )

        root_id = data.cost_event_id or uuid4()
        event_data["cost_event_id"] = root_id

        # Validate CostEventType existence
        type_exists = await self.session.execute(
            select(CostEventType.id)
            .where(
                CostEventType.cost_event_type_id == data.cost_event_type_id,
                func.upper(cast(Any, CostEventType).valid_time).is_(None),
                cast(Any, CostEventType).deleted_at.is_(None),
            )
            .limit(1)
        )
        if not type_exists.scalar_one_or_none():
            raise ValueError(f"Cost Event Type {data.cost_event_type_id} not found")

        cmd = CreateVersionCommand(  # type: ignore[type-var]
            entity_class=CostEvent,
            root_id=root_id,
            actor_id=actor_id,
            control_date=control_date,
            **event_data,
        )
        event = await cmd.execute(self.session)

        # Create cost allocations if provided
        if data.cost_allocations:
            await self._create_cost_allocations(
                cost_event_id=root_id,
                allocations_data=data.cost_allocations,
                actor_id=actor_id,
            )

        return event

    async def update_cost_event(
        self,
        cost_event_id: UUID,
        data: CostEventUpdate,
        actor_id: UUID,
    ) -> CostEvent:
        """Update cost event (creates new version).

        Args:
            cost_event_id: Root ID to update.
            data: Update data.
            actor_id: User making the update.

        Returns:
            Updated CostEvent entity.
        """
        control_date = data.control_date
        update_data = data.model_dump(
            exclude_unset=True,
            exclude={"control_date", "cost_allocations"},
        )

        # Validate CostEventType if changed
        if data.cost_event_type_id is not None:
            type_exists = await self.session.execute(
                select(CostEventType.id)
                .where(
                    CostEventType.cost_event_type_id == data.cost_event_type_id,
                    func.upper(cast(Any, CostEventType).valid_time).is_(None),
                    cast(Any, CostEventType).deleted_at.is_(None),
                )
                .limit(1)
            )
            if not type_exists.scalar_one_or_none():
                raise ValueError(f"Cost Event Type {data.cost_event_type_id} not found")

        class CostEventUpdateCommand(UpdateVersionCommand[CostEvent]):  # type: ignore[type-var,unused-ignore]
            def _root_field_name(self) -> str:
                return "cost_event_id"

        cmd = CostEventUpdateCommand(
            entity_class=CostEvent,
            root_id=cost_event_id,
            actor_id=actor_id,
            control_date=control_date,
            **update_data,
        )
        event = await cmd.execute(self.session)

        # Replace cost allocations if provided
        if data.cost_allocations is not None:
            await self._replace_cost_allocations(
                cost_event_id=cost_event_id,
                allocations_data=data.cost_allocations,
                actor_id=actor_id,
            )

        return event

    async def soft_delete_cost_event(
        self,
        cost_event_id: UUID,
        actor_id: UUID,
        control_date: datetime | None = None,
    ) -> None:
        """Soft delete cost event.

        Args:
            cost_event_id: Root ID to delete.
            actor_id: User performing deletion.
            control_date: Optional control date.
        """

        class CostEventSoftDeleteCommand(SoftDeleteCommand[CostEvent]):  # type: ignore[type-var,unused-ignore]
            def _root_field_name(self) -> str:
                return "cost_event_id"

        cmd = CostEventSoftDeleteCommand(
            entity_class=CostEvent,
            root_id=cost_event_id,
            actor_id=actor_id,
            control_date=control_date,
        )
        await cmd.execute(self.session)

    # --- Queries ---

    async def get_by_id(self, cost_event_id: UUID) -> CostEvent | None:
        """Get current cost event by root ID."""
        stmt = (
            select(CostEvent)
            .where(
                CostEvent.cost_event_id == cost_event_id,
                func.upper(CostEvent.valid_time).is_(None),
                CostEvent.deleted_at.is_(None),
            )
            .order_by(CostEvent.valid_time.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_cost_events(
        self,
        project_id: UUID | None = None,
        wbs_element_id: UUID | None = None,
        coq_category: str | None = None,
        status: str | None = None,
        skip: int = 0,
        limit: int = 100,
        as_of: datetime | None = None,
    ) -> tuple[list[CostEvent], int]:
        """Get cost events with optional filtering and pagination.

        Args:
            project_id: Optional project filter.
            wbs_element_id: Optional WBS Element filter.
            coq_category: Optional COQ category filter.
            status: Optional status filter.
            skip: Records to skip.
            limit: Maximum records.
            as_of: Optional timestamp for time-travel.

        Returns:
            Tuple of (list of cost events, total count).
        """
        stmt = select(CostEvent)

        if as_of is not None:
            stmt = self._apply_bitemporal_filter(stmt, as_of)
        else:
            stmt = stmt.where(
                func.upper(CostEvent.valid_time).is_(None),
                CostEvent.deleted_at.is_(None),
            )

        if project_id is not None:
            stmt = stmt.where(CostEvent.project_id == project_id)

        if wbs_element_id is not None:
            stmt = stmt.where(CostEvent.wbs_element_id == wbs_element_id)

        if coq_category is not None:
            stmt = stmt.where(CostEvent.coq_category == coq_category)

        if status is not None:
            stmt = stmt.where(CostEvent.status == status)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar_one()

        stmt = stmt.order_by(CostEvent.event_date.desc().nullslast())
        stmt = stmt.offset(skip).limit(limit)

        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    # --- COQ Metrics ---

    async def _get_quality_event_type_ids(self) -> list[UUID]:
        """Get root IDs of all CostEventTypes flagged as quality-relevant."""
        stmt = select(CostEventType.cost_event_type_id).where(
            func.upper(cast(Any, CostEventType).valid_time).is_(None),
            cast(Any, CostEventType).deleted_at.is_(None),
            CostEventType.is_quality == True,  # noqa: E712
        )
        result = await self.session.execute(stmt)
        ids = [row[0] for row in result.all()]
        return ids if ids else [UUID("00000000-0000-0000-0000-000000000000")]

    async def get_coq_metrics(
        self,
        project_id: UUID,
        as_of: datetime | None = None,
    ) -> COQMetrics:
        """Get COQ metrics for a project.

        Computes Cost of Quality metrics including:
        - Total COQ: sum of CR amounts linked to quality events
        - CPQ: Cost of Poor Quality (nonconformance)
        - CPIq: CPQ / Total AC
        - QPI: Quality Performance Index (Nassar 2009)
        - COQ ratio: Total COQ / Project budget

        Args:
            project_id: Project root ID.
            as_of: Optional timestamp for time-travel.

        Returns:
            COQMetrics with all computed indicators.
        """
        quality_ids = await self._get_quality_event_type_ids()

        # Apply as_of time-travel when requested. CostEvent is filtered via this
        # service's bitemporal helper (bound to CostEvent); CostRegistration is a
        # different entity, so we reuse CostRegistrationService's helper (bound to
        # CostRegistration) -- exactly how EVMService computes AC. When as_of is
        # None we keep the original current-version filter. See get_summary /
        # cr_service.get_total_for_work_package for the canonical pattern.
        if as_of is not None:
            from app.services.cost_registration_service import CostRegistrationService

            cr_service = CostRegistrationService(self.session)

            def _apply_cr(stmt: Any) -> Any:
                return cr_service._apply_bitemporal_filter(stmt, as_of)  # noqa: SLF001

            def _apply_event(stmt: Any) -> Any:
                return self._apply_bitemporal_filter(stmt, as_of)

        else:
            cr_filters_current = [
                func.upper(CostRegistration.valid_time).is_(None),
                CostRegistration.deleted_at.is_(None),
            ]

            def _apply_cr(stmt: Any) -> Any:
                return stmt.where(*cr_filters_current)

            # Original behavior: as_of=None never applied a bitemporal filter to
            # CostEvent (only CostRegistration). Keep it a no-op here.
            def _apply_event(stmt: Any) -> Any:
                return stmt

        # 1. Total COQ: sum of CR.amount where cost_event_id IS NOT NULL and event type is quality
        total_coq_stmt = (
            select(func.coalesce(func.sum(CostRegistration.amount), Decimal("0")))
            .join(
                CostEvent,
                CostRegistration.cost_event_id == CostEvent.cost_event_id,
            )
            .where(
                CostEvent.project_id == project_id,
                CostEvent.cost_event_type_id.in_(quality_ids),
                CostRegistration.cost_event_id.isnot(None),
            )
        )
        total_coq_stmt = _apply_cr(total_coq_stmt)
        total_coq_stmt = _apply_event(total_coq_stmt)
        total_coq_result = await self.session.execute(total_coq_stmt)
        total_coq = Decimal(str(total_coq_result.scalar_one()))

        # 2. CPQ: same but filtered by nonconformance categories
        cpq_stmt = (
            select(func.coalesce(func.sum(CostRegistration.amount), Decimal("0")))
            .join(
                CostEvent,
                CostRegistration.cost_event_id == CostEvent.cost_event_id,
            )
            .where(
                CostEvent.project_id == project_id,
                CostEvent.cost_event_type_id.in_(quality_ids),
                CostEvent.coq_category.in_(["internal_failure", "external_failure"]),
                CostRegistration.cost_event_id.isnot(None),
            )
        )
        cpq_stmt = _apply_cr(cpq_stmt)
        cpq_stmt = _apply_event(cpq_stmt)
        cpq_result = await self.session.execute(cpq_stmt)
        cpq = Decimal(str(cpq_result.scalar_one()))

        # 3. Total AC: sum of ALL CostRegistration amounts in the project
        # through CostElement -> WorkPackage -> ControlAccount -> WBSElement -> Project
        total_ac_stmt = (
            select(func.coalesce(func.sum(CostRegistration.amount), Decimal("0")))
            .join(
                CostElement,
                CostRegistration.cost_element_id == CostElement.cost_element_id,
            )
            .join(
                WorkPackage, CostElement.work_package_id == WorkPackage.work_package_id
            )
            .join(
                ControlAccount,
                WorkPackage.control_account_id == ControlAccount.control_account_id,
            )
            .join(
                WBSElement,
                ControlAccount.wbs_element_id == WBSElement.wbs_element_id,
            )
            .where(
                WBSElement.project_id == project_id,
            )
        )
        total_ac_stmt = _apply_cr(total_ac_stmt)
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

    async def get_coq_trend(
        self,
        project_id: UUID,
        granularity: COQTrendGranularity = COQTrendGranularity.MONTH,
        as_of: datetime | None = None,
    ) -> COQTrendResponse:
        """Get COQ cost trend over time bucketed by granularity.

        Args:
            project_id: Project root ID.
            granularity: Time bucket size (week or month).
            as_of: Optional timestamp cap.

        Returns:
            COQTrendResponse with time-series data points.
        """
        quality_ids = await self._get_quality_event_type_ids()
        trunc = "week" if granularity == COQTrendGranularity.WEEK else "month"

        # Determine date range
        event_range = select(
            func.min(CostEvent.event_date),
            func.max(CostEvent.event_date),
        ).where(
            CostEvent.project_id == project_id,
            CostEvent.cost_event_type_id.in_(quality_ids),
            CostEvent.event_date.isnot(None),
            func.upper(CostEvent.valid_time).is_(None),
            CostEvent.deleted_at.is_(None),
        )
        event_result = await self.session.execute(event_range)
        ev_min, ev_max = event_result.one()

        cr_range = (
            select(
                func.min(CostRegistration.registration_date),
                func.max(CostRegistration.registration_date),
            )
            .join(
                CostEvent,
                CostRegistration.cost_event_id == CostEvent.cost_event_id,
            )
            .where(
                CostEvent.project_id == project_id,
                CostEvent.cost_event_type_id.in_(quality_ids),
                CostRegistration.registration_date.isnot(None),
                CostRegistration.cost_event_id.isnot(None),
                func.upper(CostRegistration.valid_time).is_(None),
                CostRegistration.deleted_at.is_(None),
                func.upper(CostEvent.valid_time).is_(None),
                CostEvent.deleted_at.is_(None),
            )
        )
        cr_result = await self.session.execute(cr_range)
        cr_min, cr_max = cr_result.one()

        all_dates = [d for d in (ev_min, ev_max, cr_min, cr_max) if d is not None]
        if all_dates:
            start_date = min(all_dates)
            end_date = max(all_dates)
        else:
            start_date = datetime.now()
            end_date = datetime.now()
        if as_of is not None and as_of < end_date:
            end_date = as_of

        # Actual costs (from CostRegistration)
        actual_bucket_expr = func.date_trunc(trunc, CostRegistration.registration_date)
        actual_stmt = (
            select(
                actual_bucket_expr.label("bucket"),
                CostEvent.coq_category,
                func.coalesce(func.sum(CostRegistration.amount), Decimal("0")).label(
                    "cost"
                ),
            )
            .join(
                CostEvent,
                CostRegistration.cost_event_id == CostEvent.cost_event_id,
            )
            .where(
                CostEvent.project_id == project_id,
                CostEvent.cost_event_type_id.in_(quality_ids),
                CostRegistration.registration_date.isnot(None),
                CostRegistration.cost_event_id.isnot(None),
                func.upper(CostEvent.valid_time).is_(None),
                CostEvent.deleted_at.is_(None),
                func.upper(CostRegistration.valid_time).is_(None),
                CostRegistration.deleted_at.is_(None),
            )
            .group_by(actual_bucket_expr, CostEvent.coq_category)
            .order_by(actual_bucket_expr)
        )
        actual_result = await self.session.execute(actual_stmt)
        actual_rows = actual_result.all()

        # Planned costs (from estimated_impact)
        planned_bucket_expr = func.date_trunc(trunc, CostEvent.event_date)
        planned_stmt = (
            select(
                planned_bucket_expr.label("bucket"),
                CostEvent.coq_category,
                func.coalesce(func.sum(CostEvent.estimated_impact), Decimal("0")).label(
                    "cost"
                ),
            )
            .where(
                CostEvent.project_id == project_id,
                CostEvent.cost_event_type_id.in_(quality_ids),
                CostEvent.event_date.isnot(None),
                func.upper(CostEvent.valid_time).is_(None),
                CostEvent.deleted_at.is_(None),
            )
            .group_by(planned_bucket_expr, CostEvent.coq_category)
            .order_by(planned_bucket_expr)
        )
        planned_result = await self.session.execute(planned_stmt)
        planned_rows = planned_result.all()

        # Assemble into trend points
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

        all_bucket_dates = sorted(
            set(actual_buckets.keys()) | set(planned_buckets.keys())
        )

        points: list[COQTrendPoint] = []
        for bucket_date in all_bucket_dates:
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

    async def get_summary(
        self,
        project_id: UUID,
        as_of: datetime | None = None,
    ) -> CostEventSummary:
        """Get aggregated COQ summary for a project.

        Only includes events of types flagged as quality-relevant.

        Args:
            project_id: Project root ID.
            as_of: Optional timestamp for time-travel.

        Returns:
            CostEventSummary with cost breakdown and COQ ratio.
        """
        quality_ids = await self._get_quality_event_type_ids()

        if as_of is not None:
            inner_stmt = select(CostEvent).where(
                CostEvent.project_id == project_id,
                CostEvent.cost_event_type_id.in_(quality_ids),
            )
            inner_stmt = self._apply_bitemporal_filter(inner_stmt, as_of)
            inner_subq = inner_stmt.subquery()

            total_stmt = select(
                func.coalesce(
                    func.sum(inner_subq.c.estimated_impact), Decimal("0")
                ).label("total_cost"),
                func.count().label("impact_count"),
                func.coalesce(func.sum(inner_subq.c.schedule_impact_days), 0).label(
                    "total_schedule_days"
                ),
            )
            total_result = await self.session.execute(total_stmt)
            total_row = total_result.one()

            cat_stmt = select(
                inner_subq.c.coq_category,
                func.coalesce(
                    func.sum(inner_subq.c.estimated_impact), Decimal("0")
                ).label("category_cost"),
            ).group_by(inner_subq.c.coq_category)
            cat_result = await self.session.execute(cat_stmt)
            cat_costs = {
                row.coq_category: row.category_cost for row in cat_result.all()
            }
        else:
            current_filter = (
                func.upper(CostEvent.valid_time).is_(None),
                CostEvent.deleted_at.is_(None),
            )
            total_stmt = select(
                func.coalesce(func.sum(CostEvent.estimated_impact), Decimal("0")).label(
                    "total_cost"
                ),
                func.count().label("impact_count"),
                func.coalesce(func.sum(CostEvent.schedule_impact_days), 0).label(
                    "total_schedule_days"
                ),
            ).where(
                CostEvent.project_id == project_id,
                CostEvent.cost_event_type_id.in_(quality_ids),
                *current_filter,
            )
            total_result = await self.session.execute(total_stmt)
            total_row = total_result.one()

            cat_stmt = (
                select(
                    CostEvent.coq_category,
                    func.coalesce(
                        func.sum(CostEvent.estimated_impact), Decimal("0")
                    ).label("category_cost"),
                )
                .where(
                    CostEvent.project_id == project_id,
                    CostEvent.cost_event_type_id.in_(quality_ids),
                    *current_filter,
                )
                .group_by(CostEvent.coq_category)
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

        coq_ratio = await self._compute_coq_ratio(project_id, total_cost)

        return CostEventSummary(
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

    # --- Allocations ---

    async def get_allocations(
        self,
        cost_event_id: UUID,
    ) -> list[QualityCostAllocationRead]:
        """Get all cost allocation entries for a cost event.

        Queries CostRegistration entries linked to the cost event.

        Args:
            cost_event_id: Root ID of the parent cost event.

        Returns:
            List of QualityCostAllocationRead entries.
        """
        stmt = (
            select(
                CostRegistration.cost_registration_id,
                CostRegistration.cost_element_id,
                CostRegistration.amount,
                CostRegistration.description,
            )
            .outerjoin(
                CostElement,
                CostRegistration.cost_element_id == CostElement.cost_element_id,
            )
            .where(
                CostRegistration.cost_event_id == cost_event_id,
                func.upper(CostRegistration.valid_time).is_(None),
                CostRegistration.deleted_at.is_(None),
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
            )
            for row in rows
        ]

    async def upsert_allocations(
        self,
        cost_event_id: UUID,
        allocations_data: list[QualityCostAllocation],
        actor_id: UUID,
    ) -> list[QualityCostAllocationRead]:
        """Replace all cost allocations for a cost event.

        Deletes existing CostRegistration entries linked to the cost event
        and creates new ones.

        Args:
            cost_event_id: Root ID of the parent cost event.
            allocations_data: New allocation entries.
            actor_id: User performing the upsert.

        Returns:
            List of newly created allocation entries.
        """
        return await self._replace_cost_allocations(
            cost_event_id=cost_event_id,
            allocations_data=allocations_data,
            actor_id=actor_id,
        )

    # --- Internal helpers ---

    @staticmethod
    def _compute_qpi(cpq_percentage: Decimal) -> Decimal:
        """Compute QPI using Nassar (2009) normalization."""
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
                fraction = (cpq_percentage - prev_upper) / (upper - prev_upper)
                return (
                    qpi_at_lower + fraction * (qpi_at_upper - qpi_at_lower)
                ).quantize(Decimal("0.01"))
            prev_upper = upper

        excess = cpq_percentage - Decimal("4.0")
        return (Decimal("0.85") - excess * Decimal("0.05")).quantize(Decimal("0.01"))

    @staticmethod
    def _qpi_rating(qpi: Decimal) -> str:
        """Map QPI value to human-readable rating."""
        if qpi > Decimal("1.05"):
            return "Outstanding"
        if qpi >= Decimal("0.95"):
            return "Within Target"
        if qpi >= Decimal("0.85"):
            return "Below Target"
        return "Poor Performance"

    async def _create_cost_allocations(
        self,
        cost_event_id: UUID,
        allocations_data: list[QualityCostAllocation],
        actor_id: UUID,
    ) -> list[CostRegistration]:
        """Create CostRegistration entries for a cost event's allocations."""
        created: list[CostRegistration] = []
        for alloc in allocations_data:
            root_id = uuid4()
            cmd = CreateVersionCommand(  # type: ignore[type-var]
                entity_class=CostRegistration,
                root_id=root_id,
                actor_id=actor_id,
                cost_registration_id=root_id,
                cost_element_id=alloc.cost_element_id,
                cost_event_id=cost_event_id,
                amount=alloc.amount,
                description=alloc.description
                or f"Quality cost allocation for event {cost_event_id}",
            )
            cr = await cmd.execute(self.session)
            created.append(cr)
        return created

    async def _replace_cost_allocations(
        self,
        cost_event_id: UUID,
        allocations_data: list[QualityCostAllocation],
        actor_id: UUID,
    ) -> list[QualityCostAllocationRead]:
        """Delete existing allocations and create new ones."""
        # Soft-delete existing CRs linked to this cost event
        existing_stmt = select(CostRegistration).where(
            CostRegistration.cost_event_id == cost_event_id,
            CostRegistration.deleted_at.is_(None),
        )
        existing_result = await self.session.execute(existing_stmt)
        existing_crs = existing_result.scalars().all()

        for cr in existing_crs:

            class CRSoftDeleteCommand(SoftDeleteCommand[CostRegistration]):  # type: ignore[type-var,unused-ignore]
                def _root_field_name(self) -> str:
                    return "cost_registration_id"

            cmd = CRSoftDeleteCommand(
                entity_class=CostRegistration,
                root_id=cr.cost_registration_id,
                actor_id=actor_id,
            )
            await cmd.execute(self.session)

        # Create new allocations
        await self._create_cost_allocations(
            cost_event_id=cost_event_id,
            allocations_data=allocations_data,
            actor_id=actor_id,
        )

        return await self.get_allocations(cost_event_id)

    async def _compute_coq_ratio(
        self, project_id: UUID, total_coq_cost: Decimal
    ) -> Decimal | None:
        """Compute COQ ratio as total COQ cost / project budget.

        Project budget = sum of WorkPackage.budget_amount for all work packages
        in the project through ControlAccount -> WBSElement.

        Args:
            project_id: Project root ID.
            total_coq_cost: Total COQ cost.

        Returns:
            Ratio as percentage, or None if no budget.
        """
        budget_stmt = (
            select(func.coalesce(func.sum(WorkPackage.budget_amount), Decimal("0")))
            .join(
                ControlAccount,
                WorkPackage.control_account_id == ControlAccount.control_account_id,
            )
            .join(
                WBSElement,
                ControlAccount.wbs_element_id == WBSElement.wbs_element_id,
            )
            .where(
                WBSElement.project_id == project_id,
                func.upper(cast(Any, WBSElement).valid_time).is_(None),
                cast(Any, WBSElement).deleted_at.is_(None),
                func.upper(cast(Any, ControlAccount).valid_time).is_(None),
                cast(Any, ControlAccount).deleted_at.is_(None),
                func.upper(cast(Any, WorkPackage).valid_time).is_(None),
                cast(Any, WorkPackage).deleted_at.is_(None),
            )
        )
        budget_result = await self.session.execute(budget_stmt)
        project_budget = Decimal(str(budget_result.scalar_one()))

        if project_budget <= 0:
            return None

        return (total_coq_cost / project_budget * Decimal("100")).quantize(
            Decimal("0.01")
        )
