"""EVM (Earned Value Management) Service - orchestrates EVM metrics calculation.

The primary EVM entity is now the Work Package (PMI budget holder).
- BAC from WorkPackage.budget_amount
- PV from ScheduleBaseline (1:1 on WorkPackage)
- AC from CostRegistration through CostElement -> WorkPackage
- EV from ProgressEntry on WorkPackage

Entity levels: PROJECT, WBS_ELEMENT, CONTROL_ACCOUNT, WORK_PACKAGE
"""

import asyncio
import logging
import time
from bisect import bisect_right
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from functools import wraps
from typing import Any, TypeVar
from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.core.versioning.enums import BranchMode
from app.db.session import DB_CONCURRENCY_SEMAPHORE
from app.models.domain.control_account import ControlAccount
from app.models.domain.cost_element import CostElement
from app.models.domain.forecast import Forecast
from app.models.domain.progress_entry import ProgressEntry
from app.models.domain.project import Project
from app.models.domain.schedule_baseline import ScheduleBaseline
from app.models.domain.wbs_element import WBSElement
from app.models.domain.work_package import WorkPackage
from app.models.schemas.evm import (
    EntityType,
    EVMMetricsRead,
    EVMMetricsResponse,
    EVMTimeSeriesGranularity,
    EVMTimeSeriesPoint,
    EVMTimeSeriesResponse,
    PortfolioEVMResponse,
)
from app.services.control_account_service import ControlAccountService
from app.services.cost_registration_service import CostRegistrationService
from app.services.forecast_service import ForecastService
from app.services.progress_entry_service import ProgressEntryService
from app.services.project import ProjectService
from app.services.schedule_baseline_service import ScheduleBaselineService
from app.services.wbs_element_service import WBSElementService
from app.services.work_package_service import WorkPackageService

logger = logging.getLogger(__name__)

T = TypeVar("T")


def _tcpi_from(bac: Decimal, eac: Decimal | None) -> Decimal:
    """To-Complete Performance Index = BAC / EAC.

    Industry convention: defaults to 1.0 when EAC is missing or zero
    (no forecast means remaining work is budgeted at planned cost).

    Args:
        bac: Budget at Completion (in the rollup/base currency).
        eac: Estimate at Completion (in the rollup/base currency), or None.

    Returns:
        TCPI as a Decimal (1.0 when EAC is absent/zero, else ``bac / eac``).
    """
    if eac is None or eac == 0:
        return Decimal("1.0")
    return bac / eac


def log_performance(
    operation_name: str,
) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """Decorator to log performance of EVM service methods.

    Args:
        operation_name: Name of the operation for logging

    Returns:
        Decorator function
    """

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            start_time = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                end_time = time.perf_counter()
                duration_ms = (end_time - start_time) * 1000
                logger.debug(
                    f"EVM Performance: {operation_name} completed in "
                    f"{duration_ms:.2f}ms"
                )
                if "timeseries" in operation_name.lower() and duration_ms > 1000:
                    logger.warning(
                        f"EVM Performance: {operation_name} exceeded 1s budget: "
                        f"{duration_ms:.2f}ms"
                    )
                elif "metrics" in operation_name.lower() and duration_ms > 500:
                    logger.warning(
                        f"EVM Performance: {operation_name} exceeded 500ms budget: "
                        f"{duration_ms:.2f}ms"
                    )

        return wrapper

    return decorator


class EVMService:
    """Service for calculating EVM metrics with time-travel support.

    Orchestrates the calculation of all EVM metrics at the Work Package level:
    - BAC (Budget at Completion) from WorkPackage.budget_amount
    - PV (Planned Value) from ScheduleBaseline on WorkPackage
    - AC (Actual Cost) from CostRegistration through CostElement -> WorkPackage
    - EV (Earned Value) from ProgressEntry on WorkPackage
    - EAC (Estimate at Completion) from Forecast on WorkPackage
    - VAC (Variance at Completion) - BAC - EAC
    - ETC (Estimate to Complete) - EAC - AC
    - CV, SV (Variances)
    - CPI, SPI (Performance Indices)

    All calculations support time-travel via the control_date parameter.
    """

    def __init__(self, db: AsyncSession):
        """Initialize EVMService with all required services.

        Args:
            db: Async database session
        """
        self.db = db
        self.wp_service = WorkPackageService(db)
        self.sb_service = ScheduleBaselineService(db)
        self.cr_service = CostRegistrationService(db)
        self.pe_service = ProgressEntryService(db)
        self.f_service = ForecastService(db)
        self.wbs_service = WBSElementService(db)
        self.ca_service = ControlAccountService(db)
        self.project_service = ProjectService(db)

    @log_performance("calculate_evm_metrics")
    async def calculate_evm_metrics(
        self,
        work_package_id: UUID,
        control_date: datetime,
        branch: str = "main",
        branch_mode: BranchMode = BranchMode.MERGED,
    ) -> EVMMetricsRead:
        """Calculate all EVM metrics for a work package as of control_date.

        Args:
            work_package_id: The work package to calculate metrics for
            control_date: The control date for time-travel query
            branch: Branch name (default: "main")
            branch_mode: Branch isolation mode (default: MERGED)

        Returns:
            EVMMetricsRead with all calculated metrics

        Raises:
            ValueError: If work package not found
        """
        warning = None

        # Get BAC (Budget at Completion)
        bac = await self._get_bac_as_of(
            work_package_id, control_date, branch, branch_mode
        )
        if bac is None:
            raise ValueError(f"Work Package {work_package_id} not found")

        # Get PV (Planned Value) from schedule baseline
        pv = await self._get_pv_as_of(
            work_package_id, control_date, branch, branch_mode
        )

        # Get AC (Actual Cost) from cost registrations through CostElements
        ac = await self._get_ac_as_of(work_package_id, control_date)

        # Get EV (Earned Value) from progress entries
        ev, progress_percentage, ev_warning = await self._get_ev_as_of(
            work_package_id, control_date, bac
        )
        if ev_warning:
            warning = ev_warning

        # Calculate variances and indices
        cv, sv = self._calculate_variances(ev, ac, pv)
        cpi, spi = self._calculate_indices(ev, ac, pv)

        # Get EAC from forecast
        eac = await self._get_eac_as_of(
            work_package_id, control_date, branch, branch_mode
        )

        vac = None
        etc = None
        cpi_forecast = None

        if eac is not None:
            vac = bac - eac
            etc = eac - ac
            if eac > 0 and bac is not None:
                cpi_forecast = bac / eac

        return EVMMetricsRead(
            bac=bac,
            pv=pv,
            ac=ac,
            ev=ev,
            cv=cv,
            sv=sv,
            cpi=cpi,
            spi=spi,
            eac=eac,
            vac=vac,
            etc=etc,
            work_package_id=work_package_id,
            control_date=control_date,
            branch=branch,
            branch_mode=branch_mode,
            progress_percentage=progress_percentage,
            warning=warning,
            cpi_forecast=cpi_forecast,
        )

    async def _get_bac_as_of(
        self,
        work_package_id: UUID,
        as_of: datetime,
        branch: str,
        branch_mode: BranchMode,
    ) -> Decimal | None:
        """Get Budget at Completion (BAC) as of specified date with branch mode."""
        work_package = await self.wp_service.get_as_of(
            entity_id=work_package_id,
            as_of=as_of,
            branch=branch,
            branch_mode=branch_mode,
        )
        if work_package is None:
            return None
        return work_package.budget_amount

    async def _get_pv_as_of(
        self,
        work_package_id: UUID,
        as_of: datetime,
        branch: str,
        branch_mode: BranchMode,
    ) -> Decimal:
        """Get Planned Value (PV) as of specified date with branch mode.

        PV = BAC * Progress (from schedule baseline progression strategy)
        """
        try:
            work_package = await self.wp_service.get_as_of(
                entity_id=work_package_id,
                as_of=as_of,
                branch=branch,
                branch_mode=branch_mode,
            )

            if work_package is None or work_package.schedule_baseline_id is None:
                return Decimal("0")

            schedule_baseline = await self.sb_service.get_as_of(
                entity_id=work_package.schedule_baseline_id,
                as_of=as_of,
                branch=branch,
                branch_mode=branch_mode,
            )

            if schedule_baseline is None:
                return Decimal("0")

            bac = work_package.budget_amount
            if bac is None:
                return Decimal("0")

            from app.services.progression import get_progression_strategy

            if (
                schedule_baseline.start_date is None
                or schedule_baseline.end_date is None
                or schedule_baseline.start_date >= schedule_baseline.end_date
            ):
                logger.warning(
                    f"Invalid date range for schedule baseline {work_package_id}: "
                    f"start_date={schedule_baseline.start_date}, "
                    f"end_date={schedule_baseline.end_date}"
                )
                return Decimal("0")

            strategy = get_progression_strategy(schedule_baseline.progression_type)
            progress = strategy.calculate_progress(
                current_date=as_of,
                start_date=schedule_baseline.start_date,
                end_date=schedule_baseline.end_date,
            )

            return bac * Decimal(str(progress))
        except Exception:
            return Decimal("0")

    async def _get_ac_as_of(self, work_package_id: UUID, as_of: datetime) -> Decimal:
        """Get Actual Cost (AC) as of specified date.

        AC = sum of all cost registrations through CostElements for this WorkPackage.
        """
        total = await self.cr_service.get_total_for_work_package(
            work_package_id=work_package_id, as_of=as_of
        )
        return Decimal(str(total)) if total else Decimal("0")

    async def _get_ev_as_of(
        self, work_package_id: UUID, as_of: datetime, bac: Decimal
    ) -> tuple[Decimal, Decimal | None, str | None]:
        """Get Earned Value (EV) as of specified date.

        EV = BAC * Progress Percentage (from progress entries on WorkPackage)
        """
        progress_entry = await self.pe_service.get_latest_progress(
            work_package_id=work_package_id, as_of=as_of
        )

        if progress_entry is None:
            return Decimal("0"), None, "No progress reported for this work package"

        progress_percentage = progress_entry.progress_percentage
        ev = bac * progress_percentage / Decimal("100")

        return ev, progress_percentage, None

    async def _get_eac_as_of(
        self,
        work_package_id: UUID,
        as_of: datetime,
        branch: str,
        branch_mode: BranchMode,
    ) -> Decimal | None:
        """Get Estimate at Completion (EAC) from forecast."""
        work_package = await self.wp_service.get_as_of(
            entity_id=work_package_id,
            as_of=as_of,
            branch=branch,
            branch_mode=branch_mode,
        )

        if work_package is None or work_package.forecast_id is None:
            return None

        forecast = await self.f_service.get_as_of(
            entity_id=work_package.forecast_id,
            as_of=as_of,
            branch=branch,
            branch_mode=branch_mode,
        )

        if forecast is None:
            return None

        return forecast.eac_amount

    def _calculate_variances(
        self, ev: Decimal, ac: Decimal, pv: Decimal
    ) -> tuple[Decimal, Decimal]:
        """Calculate cost and schedule variances."""
        return ev - ac, ev - pv

    def _calculate_indices(
        self, ev: Decimal, ac: Decimal, pv: Decimal
    ) -> tuple[Decimal | None, Decimal | None]:
        """Calculate cost and schedule performance indices."""
        cpi = None if ac == 0 else ev / ac
        spi = None if pv == 0 else ev / pv
        return cpi, spi

    def _calculate_evm_metrics_from_data(
        self,
        work_package: WorkPackage,
        schedule_baseline: ScheduleBaseline | None,
        total_ac: Decimal,
        progress_entry: ProgressEntry | None,
        forecast: Forecast | None,
        control_date: datetime,
        branch: str,
        branch_mode: BranchMode,
    ) -> EVMMetricsRead:
        """Calculate EVM metrics using pre-fetched data (in-memory)."""
        warning = None
        work_package_id = work_package.work_package_id

        bac = work_package.budget_amount
        if bac is None:
            bac = Decimal("0")

        # PV
        pv = Decimal("0")
        if schedule_baseline:
            try:
                if (
                    schedule_baseline.start_date is None
                    or schedule_baseline.end_date is None
                    or schedule_baseline.start_date >= schedule_baseline.end_date
                ):
                    pv = Decimal("0")
                else:
                    from app.services.progression import get_progression_strategy

                    strategy = get_progression_strategy(
                        schedule_baseline.progression_type
                    )
                    progress = strategy.calculate_progress(
                        current_date=control_date,
                        start_date=schedule_baseline.start_date,
                        end_date=schedule_baseline.end_date,
                    )
                    pv = bac * Decimal(str(progress))
            except Exception as e:
                logger.error(f"Error calculating PV for {work_package_id}: {e}")
                pv = Decimal("0")

        ac = total_ac

        ev = Decimal("0")
        progress_percentage = None
        if progress_entry:
            progress_percentage = progress_entry.progress_percentage
            ev = bac * progress_percentage / Decimal("100")
        else:
            warning = "No progress reported for this work package"

        cv, sv = self._calculate_variances(ev, ac, pv)
        cpi, spi = self._calculate_indices(ev, ac, pv)

        eac = None
        vac = None
        etc = None
        cpi_forecast = None

        if forecast:
            eac = forecast.eac_amount
            if eac is not None:
                vac = bac - eac
                etc = eac - ac
                if eac > 0 and bac > 0:
                    cpi_forecast = bac / eac

        return EVMMetricsRead(
            bac=bac,
            pv=pv,
            ac=ac,
            ev=ev,
            cv=cv,
            sv=sv,
            cpi=cpi,
            spi=spi,
            eac=eac,
            vac=vac,
            etc=etc,
            work_package_id=work_package_id,
            control_date=control_date,
            branch=branch,
            branch_mode=branch_mode,
            progress_percentage=progress_percentage,
            warning=warning,
            cpi_forecast=cpi_forecast,
        )

    async def _batch_calculate_work_package_metrics(
        self,
        work_package_ids: list[UUID],
        control_date: datetime,
        branch: str,
        branch_mode: BranchMode,
    ) -> list[EVMMetricsRead]:
        """Batch calculate metrics for multiple work packages efficiently."""
        unique_wp_ids = list(dict.fromkeys(work_package_ids))

        # Bulk fetch work packages
        wp_map = await self.wp_service.get_as_of_batch(
            entity_ids=unique_wp_ids,
            as_of=control_date,
            branch=branch,
            branch_mode=branch_mode,
        )

        if not wp_map:
            return []

        valid_ids = list(wp_map.keys())

        # Bulk fetch all related data in parallel
        forecast_branch = "main" if branch_mode == BranchMode.MERGED else branch
        async with DB_CONCURRENCY_SEMAPHORE:
            baselines_map, ac_map, progress_map, forecasts_map = await asyncio.gather(
                self.sb_service.get_baselines_for_work_packages(
                    valid_ids, branch, as_of=control_date
                ),
                self._get_ac_batch(valid_ids, control_date),
                self.pe_service.get_latest_progress_for_work_packages(
                    valid_ids, as_of=control_date
                ),
                self.f_service.get_forecasts_for_work_packages(
                    valid_ids, forecast_branch, as_of=control_date
                ),
            )

        results = []
        for wp_id in valid_ids:
            wp = wp_map.get(wp_id)
            if wp is None:
                continue
            metric = self._calculate_evm_metrics_from_data(
                work_package=wp,
                schedule_baseline=baselines_map.get(wp_id),
                total_ac=ac_map.get(wp_id, Decimal("0")),
                progress_entry=progress_map.get(wp_id),
                forecast=forecasts_map.get(wp_id),
                control_date=control_date,
                branch=branch,
                branch_mode=branch_mode,
            )
            results.append(metric)

        return results

    async def _get_ac_batch(
        self, work_package_ids: list[UUID], as_of: datetime
    ) -> dict[UUID, Decimal]:
        """Get AC for multiple work packages in a single query."""
        if not work_package_ids:
            return {}

        # Get all CostElement IDs for the work packages
        ce_stmt = select(
            CostElement.work_package_id, CostElement.cost_element_id
        ).where(
            CostElement.work_package_id.in_(work_package_ids),
            func.upper(CostElement.valid_time).is_(None),
            CostElement.deleted_at.is_(None),
        )
        ce_result = await self.db.execute(ce_stmt)
        ce_rows = ce_result.all()

        # Group CE IDs by WP
        wp_to_ces: dict[UUID, list[UUID]] = {}
        all_ce_ids: list[UUID] = []
        for row in ce_rows:
            wp_to_ces.setdefault(row.work_package_id, []).append(row.cost_element_id)
            all_ce_ids.append(row.cost_element_id)

        if not all_ce_ids:
            return {wp_id: Decimal("0") for wp_id in work_package_ids}

        # Get totals for all CEs
        ce_totals = await self.cr_service.get_totals_for_cost_elements(
            all_ce_ids, as_of=as_of
        )

        # Aggregate by WP
        result: dict[UUID, Decimal] = {}
        for wp_id in work_package_ids:
            total = Decimal("0")
            for ce_id in wp_to_ces.get(wp_id, []):
                total += ce_totals.get(ce_id, Decimal("0"))
            result[wp_id] = total

        return result

    @log_performance("calculate_evm_metrics_batch")
    async def calculate_evm_metrics_batch(
        self,
        entity_type: EntityType,
        entity_ids: list[UUID],
        control_date: datetime,
        branch: str = "main",
        branch_mode: BranchMode = BranchMode.MERGED,
    ) -> EVMMetricsResponse:
        """Calculate EVM metrics for multiple entities and aggregate them.

        Args:
            entity_type: Type of entities (work_package, wbs_element, control_account, project)
            entity_ids: List of entity IDs to calculate metrics for
            control_date: Control date for time-travel query
            branch: Branch name (default: "main")
            branch_mode: Branch isolation mode (default: MERGED)

        Returns:
            EVMMetricsResponse with aggregated metrics
        """
        if not entity_ids:
            return EVMMetricsResponse(
                entity_type=entity_type,
                entity_id=UUID("00000000-0000-0000-0000-000000000000"),
                bac=Decimal("0"),
                pv=Decimal("0"),
                ac=Decimal("0"),
                ev=Decimal("0"),
                cv=Decimal("0"),
                sv=Decimal("0"),
                cpi=None,
                spi=None,
                eac=None,
                vac=None,
                etc=None,
                tcpi=None,
                control_date=control_date,
                branch=branch,
                branch_mode=branch_mode,
                progress_percentage=None,
                warning="No entities provided",
            )

        if entity_type == EntityType.WBS_ELEMENT:
            return await self._calculate_wbs_element_evm_metrics(
                wbs_element_ids=entity_ids,
                control_date=control_date,
                branch=branch,
                branch_mode=branch_mode,
            )

        if entity_type == EntityType.CONTROL_ACCOUNT:
            return await self._calculate_control_account_evm_metrics(
                control_account_ids=entity_ids,
                control_date=control_date,
                branch=branch,
                branch_mode=branch_mode,
            )

        if entity_type == EntityType.PROJECT:
            return await self._calculate_project_evm_metrics(
                project_ids=entity_ids,
                control_date=control_date,
                branch=branch,
                branch_mode=branch_mode,
            )

        if entity_type != EntityType.WORK_PACKAGE:
            raise ValueError(
                f"Entity type {entity_type} not yet supported. "
                "Currently only work_package, wbs_element, control_account, and project are supported."
            )

        # WORK_PACKAGE: direct calculation
        individual_metrics = await self._batch_calculate_work_package_metrics(
            work_package_ids=entity_ids,
            control_date=control_date,
            branch=branch,
            branch_mode=branch_mode,
        )

        if not individual_metrics:
            raise ValueError(f"No valid entities found for IDs: {entity_ids}")

        response_metrics = [
            self._convert_to_response(metrics, entity_type)
            for metrics in individual_metrics
        ]

        return self.aggregate_evm_metrics(response_metrics)

    async def _resolve_work_package_ids_for_wbs(
        self,
        wbs_element_ids: list[UUID],
        branch: str,
        branch_mode: BranchMode,
    ) -> list[UUID]:
        """Resolve WBS Element IDs to Work Package IDs through Control Accounts."""
        # Include descendants
        expanded_ids = list(wbs_element_ids)
        for wbs_id in wbs_element_ids:
            descendants = await self.wbs_service._get_all_descendants(
                wbs_id, branch, branch_mode
            )
            expanded_ids.extend(d.wbs_element_id for d in descendants)
        expanded_ids = list(dict.fromkeys(expanded_ids))

        # Get Control Accounts for these WBS Elements
        stmt = select(ControlAccount.control_account_id).where(
            ControlAccount.wbs_element_id.in_(expanded_ids),
            ControlAccount.branch == branch,
            func.upper(ControlAccount.valid_time).is_(None),
            ControlAccount.deleted_at.is_(None),
        )
        result = await self.db.execute(stmt)
        ca_ids = [row.control_account_id for row in result.all()]

        if not ca_ids:
            return []

        # Get Work Packages for these Control Accounts
        wp_stmt = select(WorkPackage.work_package_id).where(
            WorkPackage.control_account_id.in_(ca_ids),
            WorkPackage.branch == branch,
            func.upper(WorkPackage.valid_time).is_(None),
            WorkPackage.deleted_at.is_(None),
        )
        wp_result = await self.db.execute(wp_stmt)
        return list(dict.fromkeys(row.work_package_id for row in wp_result.all()))

    async def _resolve_work_package_ids_for_ca(
        self,
        control_account_ids: list[UUID],
        branch: str,
    ) -> list[UUID]:
        """Resolve Control Account IDs to Work Package IDs."""
        stmt = select(WorkPackage.work_package_id).where(
            WorkPackage.control_account_id.in_(control_account_ids),
            WorkPackage.branch == branch,
            func.upper(WorkPackage.valid_time).is_(None),
            WorkPackage.deleted_at.is_(None),
        )
        result = await self.db.execute(stmt)
        return list(dict.fromkeys(row.work_package_id for row in result.all()))

    async def _calculate_wbs_element_evm_metrics(
        self,
        wbs_element_ids: list[UUID],
        control_date: datetime,
        branch: str,
        branch_mode: BranchMode,
    ) -> EVMMetricsResponse:
        """Calculate EVM metrics for WBS Elements by aggregating child Work Packages."""
        wp_ids = await self._resolve_work_package_ids_for_wbs(
            wbs_element_ids, branch, branch_mode
        )

        if not wp_ids:
            return EVMMetricsResponse(
                entity_type=EntityType.WBS_ELEMENT,
                entity_id=wbs_element_ids[0],
                bac=Decimal("0"),
                pv=Decimal("0"),
                ac=Decimal("0"),
                ev=Decimal("0"),
                cv=Decimal("0"),
                sv=Decimal("0"),
                cpi=None,
                spi=None,
                eac=None,
                vac=None,
                etc=None,
                tcpi=None,
                control_date=control_date,
                branch=branch,
                branch_mode=branch_mode,
                progress_percentage=None,
                warning="No work packages found for WBS Elements",
            )

        individual_metrics = await self._batch_calculate_work_package_metrics(
            work_package_ids=wp_ids,
            control_date=control_date,
            branch=branch,
            branch_mode=branch_mode,
        )

        if not individual_metrics:
            raise ValueError(
                f"No valid work packages found for WBS Elements: {wbs_element_ids}"
            )

        response_metrics = [
            self._convert_to_response(metrics, EntityType.WBS_ELEMENT)
            for metrics in individual_metrics
        ]

        aggregated = self.aggregate_evm_metrics(response_metrics)
        return EVMMetricsResponse(
            entity_type=EntityType.WBS_ELEMENT,
            entity_id=wbs_element_ids[0],
            bac=aggregated.bac,
            pv=aggregated.pv,
            ac=aggregated.ac,
            ev=aggregated.ev,
            cv=aggregated.cv,
            sv=aggregated.sv,
            cpi=aggregated.cpi,
            spi=aggregated.spi,
            eac=aggregated.eac,
            vac=aggregated.vac,
            etc=aggregated.etc,
            tcpi=aggregated.tcpi,
            control_date=aggregated.control_date,
            branch=aggregated.branch,
            branch_mode=aggregated.branch_mode,
            progress_percentage=aggregated.progress_percentage,
            warning=aggregated.warning,
        )

    async def _calculate_control_account_evm_metrics(
        self,
        control_account_ids: list[UUID],
        control_date: datetime,
        branch: str,
        branch_mode: BranchMode,
    ) -> EVMMetricsResponse:
        """Calculate EVM metrics for Control Accounts by aggregating child Work Packages."""
        wp_ids = await self._resolve_work_package_ids_for_ca(
            control_account_ids, branch
        )

        if not wp_ids:
            return EVMMetricsResponse(
                entity_type=EntityType.CONTROL_ACCOUNT,
                entity_id=control_account_ids[0],
                bac=Decimal("0"),
                pv=Decimal("0"),
                ac=Decimal("0"),
                ev=Decimal("0"),
                cv=Decimal("0"),
                sv=Decimal("0"),
                cpi=None,
                spi=None,
                eac=None,
                vac=None,
                etc=None,
                tcpi=None,
                control_date=control_date,
                branch=branch,
                branch_mode=branch_mode,
                progress_percentage=None,
                warning="No work packages found for Control Accounts",
            )

        individual_metrics = await self._batch_calculate_work_package_metrics(
            work_package_ids=wp_ids,
            control_date=control_date,
            branch=branch,
            branch_mode=branch_mode,
        )

        if not individual_metrics:
            raise ValueError(
                f"No valid work packages found for Control Accounts: {control_account_ids}"
            )

        response_metrics = [
            self._convert_to_response(metrics, EntityType.CONTROL_ACCOUNT)
            for metrics in individual_metrics
        ]

        aggregated = self.aggregate_evm_metrics(response_metrics)
        return EVMMetricsResponse(
            entity_type=EntityType.CONTROL_ACCOUNT,
            entity_id=control_account_ids[0],
            bac=aggregated.bac,
            pv=aggregated.pv,
            ac=aggregated.ac,
            ev=aggregated.ev,
            cv=aggregated.cv,
            sv=aggregated.sv,
            cpi=aggregated.cpi,
            spi=aggregated.spi,
            eac=aggregated.eac,
            vac=aggregated.vac,
            etc=aggregated.etc,
            tcpi=aggregated.tcpi,
            control_date=aggregated.control_date,
            branch=aggregated.branch,
            branch_mode=aggregated.branch_mode,
            progress_percentage=aggregated.progress_percentage,
            warning=aggregated.warning,
        )

    async def _calculate_project_evm_metrics(
        self,
        project_ids: list[UUID],
        control_date: datetime,
        branch: str,
        branch_mode: BranchMode,
    ) -> EVMMetricsResponse:
        """Calculate EVM metrics for Projects by aggregating child WBS Elements."""
        wbs_elements, _ = await self.wbs_service.get_wbs_elements_for_projects(
            project_ids=project_ids,
            branch=branch,
            branch_mode=branch_mode,
        )
        all_wbs_ids = list(dict.fromkeys(w.wbs_element_id for w in wbs_elements))

        if not all_wbs_ids:
            return EVMMetricsResponse(
                entity_type=EntityType.PROJECT,
                entity_id=project_ids[0],
                bac=Decimal("0"),
                pv=Decimal("0"),
                ac=Decimal("0"),
                ev=Decimal("0"),
                cv=Decimal("0"),
                sv=Decimal("0"),
                cpi=None,
                spi=None,
                eac=None,
                vac=None,
                etc=None,
                tcpi=None,
                control_date=control_date,
                branch=branch,
                branch_mode=branch_mode,
                progress_percentage=None,
                warning="No WBS Elements found for project",
            )

        wbs_result = await self._calculate_wbs_element_evm_metrics(
            wbs_element_ids=all_wbs_ids,
            control_date=control_date,
            branch=branch,
            branch_mode=branch_mode,
        )

        return EVMMetricsResponse(
            entity_type=EntityType.PROJECT,
            entity_id=project_ids[0],
            bac=wbs_result.bac,
            pv=wbs_result.pv,
            ac=wbs_result.ac,
            ev=wbs_result.ev,
            cv=wbs_result.cv,
            sv=wbs_result.sv,
            cpi=wbs_result.cpi,
            spi=wbs_result.spi,
            eac=wbs_result.eac,
            vac=wbs_result.vac,
            etc=wbs_result.etc,
            tcpi=wbs_result.tcpi,
            control_date=wbs_result.control_date,
            branch=wbs_result.branch,
            branch_mode=wbs_result.branch_mode,
            progress_percentage=wbs_result.progress_percentage,
            warning=wbs_result.warning,
        )

    def _convert_to_response(
        self, metrics: EVMMetricsRead, entity_type: EntityType
    ) -> EVMMetricsResponse:
        """Convert EVMMetricsRead to EVMMetricsResponse."""
        # TCPI is derived (BAC/EAC); EVMMetricsRead has no tcpi field. Defaults
        # to 1.0 when EAC is missing or zero (industry convention).
        tcpi = _tcpi_from(
            Decimal(str(metrics.bac)),
            Decimal(str(metrics.eac)) if metrics.eac is not None else None,
        )
        return EVMMetricsResponse(
            entity_type=entity_type,
            entity_id=metrics.work_package_id,
            bac=metrics.bac,
            pv=metrics.pv,
            ac=metrics.ac,
            ev=metrics.ev,
            cv=metrics.cv,
            sv=metrics.sv,
            cpi=metrics.cpi,
            spi=metrics.spi,
            eac=metrics.eac,
            vac=metrics.vac,
            etc=metrics.etc,
            tcpi=tcpi,
            control_date=metrics.control_date,
            branch=metrics.branch,
            branch_mode=metrics.branch_mode,
            progress_percentage=metrics.progress_percentage,
            warning=metrics.warning,
        )

    def aggregate_evm_metrics(
        self, metrics_list: list[EVMMetricsResponse]
    ) -> EVMMetricsResponse:
        """Aggregate multiple EVM metrics responses.

        Sums amount fields (BAC, PV, AC, EV, CV, SV, EAC, VAC, ETC).
        Re-derives indices (CPI, SPI, TCPI) from summed EV/AC/PV/BAC/EAC
        (industry-standard 'roll up, never average').
        """
        if not metrics_list:
            raise ValueError("Cannot aggregate empty metrics list")

        first = metrics_list[0]

        bac: Decimal = sum((Decimal(str(m.bac)) for m in metrics_list), Decimal("0"))
        pv: Decimal = sum((Decimal(str(m.pv)) for m in metrics_list), Decimal("0"))
        ac: Decimal = sum((Decimal(str(m.ac)) for m in metrics_list), Decimal("0"))
        ev: Decimal = sum((Decimal(str(m.ev)) for m in metrics_list), Decimal("0"))

        cv = ev - ac
        sv = ev - pv

        cpi = None if ac == 0 else ev / ac
        spi = None if pv == 0 else ev / pv

        eac_list = [Decimal(str(m.eac)) for m in metrics_list if m.eac is not None]
        eac = (
            sum(eac_list, Decimal("0")) if len(eac_list) == len(metrics_list) else None
        )

        vac_list = [Decimal(str(m.vac)) for m in metrics_list if m.vac is not None]
        vac = (
            sum(vac_list, Decimal("0")) if len(vac_list) == len(metrics_list) else None
        )

        etc_list = [Decimal(str(m.etc)) for m in metrics_list if m.etc is not None]
        etc = (
            sum(etc_list, Decimal("0")) if len(etc_list) == len(metrics_list) else None
        )

        # TCPI = BAC / EAC; defaults to 1.0 when EAC is missing or zero.
        tcpi = _tcpi_from(bac, eac)

        total_bac = bac
        progress_percentage = None
        if total_bac > 0:
            weighted_progress = sum(
                Decimal(str(m.progress_percentage or 0)) * Decimal(str(m.bac))
                for m in metrics_list
            )
            progress_percentage = weighted_progress / total_bac

        warnings = [m.warning for m in metrics_list if m.warning]
        warning = "; ".join(warnings) if warnings else None

        return EVMMetricsResponse(
            entity_type=first.entity_type,
            entity_id=first.entity_id,
            bac=bac,
            pv=pv,
            ac=ac,
            ev=ev,
            cv=cv,
            sv=sv,
            cpi=cpi,
            spi=spi,
            eac=eac,
            vac=vac,
            etc=etc,
            tcpi=tcpi,
            control_date=first.control_date,
            branch=first.branch,
            branch_mode=first.branch_mode,
            progress_percentage=progress_percentage,
            warning=warning,
        )

    async def _gather_timeseries(
        self,
        tasks: list[Awaitable[EVMTimeSeriesResponse]],
        label: str,
    ) -> list[EVMTimeSeriesResponse]:
        """Execute time-series tasks concurrently, filtering out failures."""
        results = await asyncio.gather(*tasks, return_exceptions=True)
        collected: list[EVMTimeSeriesResponse] = []
        for r in results:
            if isinstance(r, BaseException):
                if not isinstance(r, ValueError):
                    logger.warning(
                        f"Unexpected error fetching {label} time-series: {r}"
                    )
                continue
            collected.append(r)
        return collected

    async def _resolve_wps_to_projects_batch(
        self,
        project_ids: list[UUID],
        branch: str,
        branch_mode: BranchMode,
    ) -> tuple[dict[UUID, UUID], dict[UUID, list[UUID]]]:
        """Resolve every accessible project's Work Packages in a constant number
        of queries (independent of the project count).

        Mirrors the per-project resolution path
        (:meth:`_resolve_work_package_ids_for_wbs` over the WBS set returned by
        ``get_wbs_elements_for_projects``) but batches the whole portfolio:

        1. Fetch every top-level WBS Element for the project set.
        2. Expand all descendants of that WBS set in ONE recursive CTE.
        3. Fetch every Control Account hanging off any (top + descendant) WBS.
        4. Fetch every Work Package under those Control Accounts.

        Args:
            project_ids: Accessible project root ids.
            branch: Branch name.
            branch_mode: Branch isolation mode (drives the descendant CTE).

        Returns:
            A tuple ``(wp_to_project, wbs_by_project)`` where ``wp_to_project``
            maps each Work Package root id to its owning Project root id, and
            ``wbs_by_project`` maps each Project to its (top-level) WBS root ids.
        """
        # 1. Top-level WBS Elements for the whole project set (current versions).
        wbs_stmt = (
            select(WBSElement.wbs_element_id, WBSElement.project_id)
            .where(WBSElement.project_id.in_(project_ids))
            .where(WBSElement.branch == branch)
            .where(func.upper(WBSElement.valid_time).is_(None))
            .where(WBSElement.deleted_at.is_(None))
        )
        wbs_rows = (await self.db.execute(wbs_stmt)).all()
        if not wbs_rows:
            return {}, {}

        # wbs_id -> project_id (top-level); plus the seed set for the CTE.
        wbs_to_project: dict[UUID, UUID] = {}
        top_wbs_ids: list[UUID] = []
        wbs_by_project: dict[UUID, list[UUID]] = {}
        for row in wbs_rows:
            wbs_to_project[row.wbs_element_id] = row.project_id
            top_wbs_ids.append(row.wbs_element_id)
            wbs_by_project.setdefault(row.project_id, []).append(row.wbs_element_id)

        # 2. Expand descendants of ALL top-level WBS in ONE recursive CTE.
        #    Generalises _get_descendants_isolated / _get_descendants_merged to
        #    a multi-root seed; the recursion semantics are unchanged.
        all_wbs_ids = await self._expand_wbs_descendants_batch(
            top_wbs_ids, branch, branch_mode
        )

        # 3. Control Accounts under any (top + descendant) WBS.
        ca_stmt = (
            select(
                ControlAccount.control_account_id,
                ControlAccount.wbs_element_id,
            )
            .where(ControlAccount.wbs_element_id.in_(all_wbs_ids))
            .where(ControlAccount.branch == branch)
            .where(func.upper(ControlAccount.valid_time).is_(None))
            .where(ControlAccount.deleted_at.is_(None))
        )
        ca_rows = (await self.db.execute(ca_stmt)).all()

        # Propagate project ownership down the WBS tree: a descendant WBS keeps
        # its ancestor's project (WBS never crosses project boundaries). Any CA
        # whose WBS is a descendant (absent from the top-level map) gets its
        # project resolved via a single fill-in query.
        orphan_ca_wbs = {
            row.wbs_element_id
            for row in ca_rows
            if row.wbs_element_id not in wbs_to_project
        }
        if orphan_ca_wbs:
            fill_stmt = select(WBSElement.wbs_element_id, WBSElement.project_id).where(
                WBSElement.wbs_element_id.in_(orphan_ca_wbs)
            )
            for row in (await self.db.execute(fill_stmt)).all():
                wbs_to_project[row.wbs_element_id] = row.project_id

        ca_to_project: dict[UUID, UUID] = {
            row.control_account_id: wbs_to_project[row.wbs_element_id]
            for row in ca_rows
            if row.wbs_element_id in wbs_to_project
        }

        if not ca_to_project:
            return {}, wbs_by_project

        # 4. Work Packages under those Control Accounts.
        wp_stmt = (
            select(
                WorkPackage.work_package_id,
                WorkPackage.control_account_id,
            )
            .where(WorkPackage.control_account_id.in_(ca_to_project.keys()))
            .where(WorkPackage.branch == branch)
            .where(func.upper(WorkPackage.valid_time).is_(None))
            .where(WorkPackage.deleted_at.is_(None))
        )
        wp_rows = (await self.db.execute(wp_stmt)).all()

        wp_to_project: dict[UUID, UUID] = {
            row.work_package_id: ca_to_project[row.control_account_id]
            for row in wp_rows
            if row.control_account_id in ca_to_project
        }
        return wp_to_project, wbs_by_project

    async def _expand_wbs_descendants_batch(
        self,
        seed_wbs_ids: list[UUID],
        branch: str,
        branch_mode: BranchMode,
    ) -> list[UUID]:
        """Expand ALL descendants of ``seed_wbs_ids`` in ONE recursive query.

        Returns the union of the seed set and every descendant WBS root id.
        Mirrors :meth:`WBSElementService._get_descendants_isolated` and
        ``_get_descendants_merged`` but with a multi-root seed, so the cost is
        O(1) queries regardless of how many WBS Elements are passed in.

        Args:
            seed_wbs_ids: Top-level WBS Element root ids to expand.
            branch: Branch name.
            branch_mode: Branch isolation mode.

        Returns:
            Deduplicated list of WBS root ids (seed + descendants).
        """
        unique_seeds = list(dict.fromkeys(seed_wbs_ids))
        if not unique_seeds:
            return []

        merged = branch_mode == BranchMode.MERGED and branch != "main"

        if not merged:
            wbs_cte = (
                select(WBSElement.wbs_element_id)
                .where(
                    WBSElement.parent_wbs_element_id.in_(unique_seeds),
                    WBSElement.branch == branch,
                    func.upper(WBSElement.valid_time).is_(None),
                    WBSElement.deleted_at.is_(None),
                )
                .cte(name="wbs_descendants_batch", recursive=True)
            )
            child_alias = aliased(WBSElement, name="wbs_child_batch")
            wbs_cte = wbs_cte.union_all(
                select(child_alias.wbs_element_id).where(
                    child_alias.parent_wbs_element_id == wbs_cte.c.wbs_element_id,
                    child_alias.branch == branch,
                    func.upper(child_alias.valid_time).is_(None),
                    child_alias.deleted_at.is_(None),
                )
            )
            stmt = select(wbs_cte.c.wbs_element_id)
            result = await self.db.execute(stmt)
            descendant_ids = [row.wbs_element_id for row in result.all()]
        else:
            # MERGED mode on a non-main branch: same intricate row-selection as
            # _get_descendants_merged (prefer the branch's version over main
            # when both exist, drop main rows shadowed by a branch deletion),
            # generalised to a multi-root seed.
            raw_sql = text("""
                WITH RECURSIVE wbs_descendants AS (
                    SELECT DISTINCT ON (wbs_element_id) wbs_element_id
                    FROM wbs_elements
                    WHERE parent_wbs_element_id = ANY(:seed_ids)
                        AND branch IN (:current_branch, 'main')
                        AND deleted_at IS NULL
                        AND upper(valid_time) IS NULL
                        AND NOT (
                            branch = 'main'
                            AND wbs_element_id IN (
                                SELECT w.wbs_element_id FROM wbs_elements w
                                WHERE w.branch = :current_branch
                                  AND w.deleted_at IS NOT NULL
                            )
                        )
                    ORDER BY wbs_element_id,
                             CASE WHEN branch = :current_branch THEN 0 ELSE 1 END

                    UNION ALL

                    SELECT child.wbs_element_id
                    FROM wbs_descendants wd
                    INNER JOIN LATERAL (
                        SELECT DISTINCT ON (wbs_element_id) wbs_element_id
                        FROM wbs_elements w
                        WHERE w.parent_wbs_element_id = wd.wbs_element_id
                            AND branch IN (:current_branch, 'main')
                            AND w.deleted_at IS NULL
                            AND upper(w.valid_time) IS NULL
                            AND NOT (
                                branch = 'main'
                                AND wbs_element_id IN (
                                    SELECT ww.wbs_element_id FROM wbs_elements ww
                                    WHERE ww.branch = :current_branch
                                      AND ww.deleted_at IS NOT NULL
                                )
                            )
                        ORDER BY wbs_element_id,
                                 CASE WHEN branch = :current_branch THEN 0 ELSE 1 END
                    ) child ON true
                )
                SELECT wbs_element_id FROM wbs_descendants
            """)
            seed_id_strs = [str(s) for s in unique_seeds]
            result = await self.db.execute(
                raw_sql,
                {
                    "seed_ids": seed_id_strs,
                    "current_branch": branch,
                },
            )
            descendant_ids = [row.wbs_element_id for row in result.all()]

        # Union with the seed set and dedupe (preserves order).
        return list(dict.fromkeys(unique_seeds + descendant_ids))

    async def _get_projects_as_of_batch(
        self,
        project_ids: list[UUID],
        as_of: datetime,
        branch: str,
        branch_mode: BranchMode,
    ) -> dict[UUID, Project]:
        """Fetch the current version of every project in ONE time-travel query.

        Batched replacement for the per-project
        ``project_service.get_as_of`` loop in :meth:`calculate_portfolio_evm`.
        Returns only the latest version per project root id at ``as_of``.

        Args:
            project_ids: Project root ids to fetch.
            as_of: Time-travel cutoff.
            branch: Branch name.
            branch_mode: Branch isolation mode.

        Returns:
            Mapping of ``project_id`` -> current ``Project`` version.
        """
        unique_ids = list(dict.fromkeys(project_ids))
        if not unique_ids:
            return {}

        merged = branch_mode == BranchMode.MERGED and branch != "main"
        if merged:
            # MERGED on non-main: prefer the branch's version, fall back to main.
            # Mirrors the BranchableService.get_as_of row-selection contract.
            raw_sql = text("""
                SELECT DISTINCT ON (project_id) *
                FROM projects
                WHERE project_id = ANY(:ids)
                  AND branch IN (:current_branch, 'main')
                  AND deleted_at IS NULL
                  AND lower(valid_time) <= :as_of
                  AND (upper(valid_time) IS NULL OR upper(valid_time) > :as_of)
                ORDER BY project_id,
                         CASE WHEN branch = :current_branch THEN 0 ELSE 1 END,
                         valid_time DESC
            """)
            result = await self.db.execute(
                raw_sql,
                {
                    "ids": [str(i) for i in unique_ids],
                    "current_branch": branch,
                    "as_of": as_of,
                },
            )
            rows = result.all()
            # Map rows back to ORM Project objects for downstream consistency.
            orm_projects: dict[UUID, Project] = {}
            for row in rows:
                # Re-fetch via ORM is avoided; build lightweight read from row.
                # Downstream code only touches: project_id, name, status,
                # currency, contract_value, organizational_unit_id,
                # project_manager_id, customer_id.
                p = Project()
                p.project_id = row.project_id
                p.name = row.name
                p.status = row.status
                p.currency = row.currency
                p.contract_value = row.contract_value
                p.organizational_unit_id = row.organizational_unit_id
                p.project_manager_id = row.project_manager_id
                p.customer_id = row.customer_id
                orm_projects[row.project_id] = p
            return orm_projects

        # ISOLATED mode (or main branch): straightforward ORM query.
        stmt = select(Project).where(Project.project_id.in_(unique_ids))
        stmt = stmt.where(Project.branch == branch)
        stmt = stmt.where(func.upper(Project.valid_time).is_(None))
        stmt = stmt.where(Project.deleted_at.is_(None))
        result = await self.db.execute(stmt)
        return {p.project_id: p for p in result.scalars()}

    async def calculate_portfolio_evm(
        self,
        project_ids: list[UUID],
        control_date: datetime,
        branch: str = "main",
        branch_mode: BranchMode = BranchMode.MERGED,
    ) -> PortfolioEVMResponse:
        """Compute portfolio EVM across the given (already-access-scoped) projects.

        Resolves every accessible project's Work Packages in a SINGLE batched
        pass (one query per layer: WBS → descendants CTE → Control Accounts →
        Work Packages), runs :meth:`_batch_calculate_work_package_metrics` ONCE
        over the full Work Package set, then GROUPS the resulting per-WP metrics
        by project (WP → control_account → wbs_element → project) and aggregates
        each project's EVM. The per-project numbers are therefore identical to
        calling ``calculate_evm_metrics_batch(entity_type=PROJECT, [pid])`` per
        project, but the cost is O(1) queries rather than O(N).

        FX / ΔEAC / RAG semantics are preserved exactly: monetary values are
        converted to the base currency per project via ``convert_to_base``, ΔEAC
        drift is attached from the ForecastService, and ``at_risk = spi < 0.9``.

        Performance: O(1) DB round-trips for the WBS/CA/WP resolution plus one
        batched EVM computation, regardless of the project count.

        Args:
            project_ids: Accessible project root ids (caller already filtered).
            control_date: Time-travel control date for EVM + rate resolution.
            branch: Branch name (default ``"main"``).
            branch_mode: Branch isolation mode (default MERGED).

        Returns:
            :class:`PortfolioEVMResponse` with rolled-up summary, per-project
            breakdown, and the SPI-based at-risk subset.
        """
        from app.models.schemas.evm import PortfolioProjectMetrics
        from app.services.currency_rate_service import convert_to_base
        from app.services.forecast_service import ForecastService

        if not project_ids:
            raise ValueError("Cannot compute portfolio EVM over an empty project set")

        async def _to_base(
            amount: Decimal | float | None, currency: str
        ) -> float | None:
            """Convert an amount to the base currency at the control date."""
            if amount is None:
                return None
            converted = await convert_to_base(
                self.db, Decimal(str(amount)), currency, control_date
            )
            return float(converted)

        forecast_service = ForecastService(self.db)
        delta_eac_by_project = await forecast_service.get_delta_eac_for_projects(
            project_ids, branch=branch
        )

        # --- BATCH RESOLUTION -------------------------------------------------
        # Fetch every project's current version, every relevant WBS / CA / WP in
        # a constant number of queries, then compute EVM for ALL work packages
        # in a single pass.
        projects_map = await self._get_projects_as_of_batch(
            project_ids=project_ids,
            as_of=control_date,
            branch=branch,
            branch_mode=branch_mode,
        )

        # Only projects that actually have a current version contribute.
        # Dedup preserving order: RBAC ``accessible_project_ids`` can repeat a
        # project for users with multiple grants, which would otherwise yield
        # duplicate ``PortfolioProjectMetrics`` rows (mirrors line 1322).
        live_project_ids = list(
            dict.fromkeys(pid for pid in project_ids if pid in projects_map)
        )
        for missing_pid in set(project_ids) - set(live_project_ids):
            logger.warning(
                "Portfolio: project %s not found as_of %s; skipping",
                missing_pid,
                control_date,
            )

        wp_to_project, _ = await self._resolve_wps_to_projects_batch(
            project_ids=live_project_ids,
            branch=branch,
            branch_mode=branch_mode,
        )

        # Per-WP EVM in ONE batched pass over the whole portfolio's work
        # packages. Group the results back to projects via wp_to_project.
        all_wp_ids = list(wp_to_project.keys())
        wp_metrics_by_project: dict[UUID, list[EVMMetricsResponse]] = {
            pid: [] for pid in live_project_ids
        }
        if all_wp_ids:
            wp_metrics = await self._batch_calculate_work_package_metrics(
                work_package_ids=all_wp_ids,
                control_date=control_date,
                branch=branch,
                branch_mode=branch_mode,
            )
            for m in wp_metrics:
                owner_pid = wp_to_project.get(m.work_package_id)
                if owner_pid is not None and owner_pid in wp_metrics_by_project:
                    wp_metrics_by_project[owner_pid].append(
                        self._convert_to_response(m, EntityType.PROJECT)
                    )

        breakdown: list[PortfolioProjectMetrics] = []
        # Build a synthetic EVMMetricsResponse per project (converted to base)
        # so the existing aggregate_evm_metrics rollup can be reused.
        per_project_converted: list[EVMMetricsResponse] = []

        for project_id in live_project_ids:
            project = projects_map[project_id]
            wp_responses = wp_metrics_by_project.get(project_id, [])

            # Aggregate this project's WP metrics — identical to the per-project
            # _calculate_project_evm_metrics → aggregate_evm_metrics path.
            if wp_responses:
                metrics = self.aggregate_evm_metrics(wp_responses)
            else:
                # No WPs for this project: zero-valued EVM (same as the
                # per-project path's "No WBS Elements found" branch).
                metrics = EVMMetricsResponse(
                    entity_type=EntityType.PROJECT,
                    entity_id=project_id,
                    bac=Decimal("0"),
                    pv=Decimal("0"),
                    ac=Decimal("0"),
                    ev=Decimal("0"),
                    cv=Decimal("0"),
                    sv=Decimal("0"),
                    cpi=None,
                    spi=None,
                    eac=None,
                    vac=None,
                    etc=None,
                    tcpi=None,
                    control_date=control_date,
                    branch=branch,
                    branch_mode=branch_mode,
                    progress_percentage=None,
                    warning="No WBS Elements found for project",
                )

            currency = project.currency or "EUR"

            # Convert ALL flow values to the base currency BEFORE pushing into
            # the rollup — otherwise aggregate_evm_metrics sums mixed currencies
            # and CPI/SPI/CV/SV are dimensionally wrong under multi-currency.
            # cv/sv are intentionally NOT carried: aggregate_evm_metrics
            # re-derives them (cv = ev - ac, sv = ev - pv) from the converted
            # flows at rollup time.
            bac_b = await _to_base(metrics.bac, currency)
            eac_b = await _to_base(metrics.eac, currency)
            vac_b = await _to_base(metrics.vac, currency)
            pv_b = await _to_base(metrics.pv, currency)
            ac_b = await _to_base(metrics.ac, currency)
            ev_b = await _to_base(metrics.ev, currency)
            contract_value_b = (
                await _to_base(project.contract_value, currency)
                if project.contract_value is not None
                else None
            )
            delta_eac_raw = delta_eac_by_project.get(project_id)
            delta_eac_b = (
                await _to_base(delta_eac_raw, currency)
                if delta_eac_raw is not None
                else None
            )

            spi = metrics.spi
            at_risk = spi is not None and spi < 0.9

            breakdown.append(
                PortfolioProjectMetrics(
                    project_id=project.project_id,
                    name=project.name,
                    status=project.status,
                    cpi=metrics.cpi,
                    spi=spi,
                    vac=vac_b,
                    contract_value=contract_value_b,
                    bac=bac_b if bac_b is not None else 0.0,
                    eac=eac_b,
                    currency=currency,
                    organizational_unit_id=project.organizational_unit_id,
                    project_manager_id=project.project_manager_id,
                    customer_id=project.customer_id,
                    at_risk=at_risk,
                    delta_eac=delta_eac_b,
                    start_date=project.start_date,
                    end_date=project.end_date,
                )
            )

            # cv/sv omitted on purpose: aggregate_evm_metrics re-derives them
            # from the (now base-converted) pv/ac/ev.
            per_project_converted.append(
                EVMMetricsResponse(
                    entity_type=EntityType.PROJECT,
                    entity_id=project_id,
                    bac=bac_b if bac_b is not None else Decimal("0"),
                    pv=pv_b if pv_b is not None else Decimal("0"),
                    ac=ac_b if ac_b is not None else Decimal("0"),
                    ev=ev_b if ev_b is not None else Decimal("0"),
                    cv=Decimal("0"),
                    sv=Decimal("0"),
                    cpi=metrics.cpi,
                    spi=metrics.spi,
                    eac=eac_b,
                    vac=vac_b,
                    etc=metrics.etc,
                    tcpi=metrics.tcpi,
                    control_date=metrics.control_date,
                    branch=metrics.branch,
                    branch_mode=metrics.branch_mode,
                    progress_percentage=metrics.progress_percentage,
                    warning=metrics.warning,
                )
            )

        if per_project_converted:
            summary = self.aggregate_evm_metrics(per_project_converted)
        else:
            # No project produced metrics — return an empty summary.
            summary = EVMMetricsResponse(
                entity_type=EntityType.PROJECT,
                entity_id=project_ids[0],
                bac=Decimal("0"),
                pv=Decimal("0"),
                ac=Decimal("0"),
                ev=Decimal("0"),
                cv=Decimal("0"),
                sv=Decimal("0"),
                cpi=None,
                spi=None,
                eac=None,
                vac=None,
                etc=None,
                tcpi=None,
                control_date=control_date,
                branch=branch,
                branch_mode=branch_mode,
                progress_percentage=None,
                warning="No accessible projects with EVM data",
            )

        return PortfolioEVMResponse(
            summary=summary,
            projects=breakdown,
            at_risk_projects=[p for p in breakdown if p.at_risk],
            control_date=control_date,
        )

    def _aggregate_timeseries(
        self,
        all_timeseries: list[EVMTimeSeriesResponse],
        dates: list[datetime],
    ) -> list[EVMTimeSeriesPoint]:
        """Aggregate multiple time-series into a single point list."""
        ts_sorted: list[list[tuple[datetime, EVMTimeSeriesPoint]]] = []
        for ts in all_timeseries:
            ts_sorted.append([(p.date, p) for p in ts.points])

        cursors = [0] * len(ts_sorted)
        aggregated: list[EVMTimeSeriesPoint] = []

        for date in dates:
            total_pv = Decimal("0")
            total_ev = Decimal("0")
            total_ac = Decimal("0")
            total_forecast = Decimal("0")
            total_actual = Decimal("0")

            for i, entries in enumerate(ts_sorted):
                while (
                    cursors[i] < len(entries)
                    and entries[cursors[i]][0].date() <= date.date()
                ):
                    cursors[i] += 1
                if cursors[i] > 0:
                    p = entries[cursors[i] - 1][1]
                    total_pv += p.pv
                    total_ev += p.ev
                    total_ac += p.ac
                    total_forecast += p.forecast
                    total_actual += p.actual

            cpi, spi = self._calculate_indices(total_ev, total_ac, total_pv)
            aggregated.append(
                EVMTimeSeriesPoint(
                    date=date,
                    pv=total_pv,
                    ev=total_ev,
                    ac=total_ac,
                    forecast=total_forecast,
                    actual=total_actual,
                    cpi=cpi,
                    spi=spi,
                )
            )

        return aggregated

    @log_performance("get_evm_timeseries")
    async def get_evm_timeseries(
        self,
        entity_type: EntityType,
        entity_id: UUID,
        granularity: EVMTimeSeriesGranularity,
        control_date: datetime,
        branch: str = "main",
        branch_mode: BranchMode = BranchMode.MERGED,
    ) -> EVMTimeSeriesResponse:
        """Get historical EVM metrics as time-series data for charts."""
        if entity_type == EntityType.WBS_ELEMENT:
            return await self._get_wbs_element_evm_timeseries(
                wbs_element_id=entity_id,
                granularity=granularity,
                control_date=control_date,
                branch=branch,
                branch_mode=branch_mode,
            )

        if entity_type == EntityType.CONTROL_ACCOUNT:
            return await self._get_control_account_evm_timeseries(
                control_account_id=entity_id,
                granularity=granularity,
                control_date=control_date,
                branch=branch,
                branch_mode=branch_mode,
            )

        if entity_type == EntityType.PROJECT:
            return await self._get_project_evm_timeseries(
                project_id=entity_id,
                granularity=granularity,
                control_date=control_date,
                branch=branch,
                branch_mode=branch_mode,
            )

        if entity_type != EntityType.WORK_PACKAGE:
            raise ValueError(
                f"Entity type {entity_type} not yet supported for time-series."
            )

        # WORK_PACKAGE level
        work_package = await self.wp_service.get_as_of(
            entity_id=entity_id,
            as_of=control_date,
            branch=branch,
            branch_mode=branch_mode,
        )

        if work_package is None:
            raise ValueError(f"Work Package {entity_id} not found")

        schedule_baseline = None
        if work_package.schedule_baseline_id is not None:
            schedule_baseline = await self.sb_service.get_as_of(
                entity_id=work_package.schedule_baseline_id,
                as_of=control_date,
                branch=branch,
                branch_mode=branch_mode,
            )

        if schedule_baseline:
            start_date = schedule_baseline.start_date
            end_date = schedule_baseline.end_date
        else:
            start_date = control_date
            end_date = control_date

        if control_date > end_date:
            end_date = control_date

        points = await self._generate_timeseries_points(
            work_package_id=entity_id,
            start_date=start_date,
            end_date=end_date,
            granularity=granularity,
            control_date=control_date,
            branch=branch,
            branch_mode=branch_mode,
            schedule_baseline_end=schedule_baseline.end_date
            if schedule_baseline
            else None,
        )

        if points and schedule_baseline is None:
            start_date = points[0].date
            end_date = points[-1].date
        elif not points:
            start_date = control_date
            end_date = control_date

        return EVMTimeSeriesResponse(
            granularity=granularity,
            points=points,
            start_date=start_date,
            end_date=end_date,
            total_points=len(points),
        )

    async def _generate_timeseries_points(
        self,
        work_package_id: UUID,
        start_date: datetime,
        end_date: datetime,
        granularity: EVMTimeSeriesGranularity,
        control_date: datetime,
        branch: str,
        branch_mode: BranchMode,
        schedule_baseline_end: datetime | None = None,
    ) -> list[EVMTimeSeriesPoint]:
        """Generate time-series data points for EVM metrics for a single work package."""
        dates = self._generate_date_intervals(start_date, end_date, granularity)

        bac = await self._get_bac_as_of(
            work_package_id, control_date, branch, branch_mode
        )
        if bac is None:
            return []

        # Get cumulative costs through all CostElements for this WorkPackage
        cumulative_start_date = datetime.min.replace(tzinfo=UTC)

        # Get all CE IDs for this WP
        ce_stmt = select(CostElement.cost_element_id).where(
            CostElement.work_package_id == work_package_id,
            func.upper(CostElement.valid_time).is_(None),
            CostElement.deleted_at.is_(None),
        )
        ce_result = await self.db.execute(ce_stmt)
        ce_ids = [row.cost_element_id for row in ce_result.all()]

        ac_map: dict[datetime, Decimal] = {}
        if ce_ids:
            cumulative_costs = await self.cr_service.get_cumulative_costs_batch(
                cost_element_ids=ce_ids,
                start_date=cumulative_start_date,
                end_date=end_date,
                as_of=control_date,
            )
            for _ce_id, entries in cumulative_costs.items():
                for entry in entries:
                    entry_date = datetime.fromisoformat(
                        entry["registration_date"]
                    ).replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=UTC)
                    ac_map[entry_date] = ac_map.get(entry_date, Decimal("0")) + Decimal(
                        str(entry["cumulative_amount"])
                    )

        # Get progress entries for this WP
        progress_entries, _ = await self.pe_service.get_progress_history(
            work_package_id=work_package_id,
            skip=0,
            limit=10000,
            as_of=control_date,
        )

        ev_map: dict[datetime, tuple[Decimal, Decimal]] = {}
        progress_with_dates = [
            (pe, pe.valid_time.lower if pe.valid_time else None)
            for pe in progress_entries
        ]
        sorted_entries = sorted(
            progress_with_dates,
            key=lambda x: x[1] if x[1] is not None else datetime.min,
        )

        pe: ProgressEntry
        valid_lower: datetime | None
        for pe, valid_lower in sorted_entries:
            if valid_lower is not None:
                report_date = valid_lower.replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
                ev = bac * pe.progress_percentage / Decimal("100")
                ev_map[report_date] = (pe.progress_percentage, ev)

        # Get schedule baseline for PV
        work_package = await self.wp_service.get_as_of(
            entity_id=work_package_id,
            as_of=control_date,
            branch=branch,
            branch_mode=branch_mode,
        )

        schedule_baseline = None
        if work_package is not None and work_package.schedule_baseline_id is not None:
            schedule_baseline = await self.sb_service.get_as_of(
                entity_id=work_package.schedule_baseline_id,
                as_of=control_date,
                branch=branch,
                branch_mode=branch_mode,
            )

        if schedule_baseline is None:
            if not ac_map and not ev_map:
                return []

            earliest_ac = min(ac_map.keys()) if ac_map else control_date
            earliest_ev = min(ev_map.keys()) if ev_map else control_date
            earliest_date = min(earliest_ac, earliest_ev)

            dates = self._generate_date_intervals(
                start_date=earliest_date,
                end_date=control_date,
                granularity=granularity,
            )
            strategy = None
            baseline_end_for_projection = control_date
        else:
            from app.services.progression import get_progression_strategy

            strategy = get_progression_strategy(schedule_baseline.progression_type)
            baseline_end_for_projection = (
                schedule_baseline_end
                if schedule_baseline_end
                else schedule_baseline.end_date
            )

            dates = self._generate_date_intervals(
                start_date=schedule_baseline.start_date,
                end_date=max(schedule_baseline.end_date, control_date),
                granularity=granularity,
            )

        sorted_ac_dates = sorted(ac_map.keys())
        sorted_ev_dates = sorted(ev_map.keys())

        final_ac = Decimal("0")
        ac_idx = bisect_right(sorted_ac_dates, control_date)
        if ac_idx > 0:
            final_ac = ac_map[sorted_ac_dates[ac_idx - 1]]

        final_ev = Decimal("0")
        ev_idx = bisect_right(sorted_ev_dates, control_date)
        if ev_idx > 0:
            final_ev = ev_map[sorted_ev_dates[ev_idx - 1]][1]

        latest_ev = Decimal("0")
        ev_cursor = 0
        points: list[EVMTimeSeriesPoint] = []

        for date in dates:
            # PV
            if schedule_baseline is None or strategy is None:
                pv = Decimal("0")
            elif date > baseline_end_for_projection:
                pv = bac
            else:
                if (
                    schedule_baseline.start_date is None
                    or schedule_baseline.end_date is None
                    or schedule_baseline.start_date >= schedule_baseline.end_date
                ):
                    pv = Decimal("0")
                else:
                    progress = strategy.calculate_progress(
                        current_date=date,
                        start_date=schedule_baseline.start_date,
                        end_date=schedule_baseline.end_date,
                    )
                    pv = bac * Decimal(str(progress))

            # EV and AC
            if date > control_date:
                ev = final_ev
                ac = final_ac
            else:
                while (
                    ev_cursor < len(sorted_ev_dates)
                    and sorted_ev_dates[ev_cursor] <= date
                ):
                    latest_ev = ev_map[sorted_ev_dates[ev_cursor]][1]
                    ev_cursor += 1
                ev = latest_ev

                ac_idx = bisect_right(sorted_ac_dates, date)
                ac = ac_map[sorted_ac_dates[ac_idx - 1]] if ac_idx > 0 else Decimal("0")

            cpi, spi = self._calculate_indices(ev=ev, ac=ac, pv=pv)

            points.append(
                EVMTimeSeriesPoint(
                    date=date,
                    pv=pv,
                    ev=ev,
                    ac=ac,
                    forecast=pv,
                    actual=ac,
                    cpi=float(cpi) if cpi is not None else None,
                    spi=float(spi) if spi is not None else None,
                )
            )

        return points

    async def _generate_timeseries_points_batch(
        self,
        work_package_ids: list[UUID],
        granularity: EVMTimeSeriesGranularity,
        control_date: datetime,
        branch: str,
        branch_mode: BranchMode,
    ) -> dict[UUID, list[EVMTimeSeriesPoint]]:
        """Generate time-series data points for multiple work packages at once."""
        if not work_package_ids:
            return {}

        # Batch fetch work packages
        wp_map = await self.wp_service.get_as_of_batch(
            work_package_ids, control_date, branch, branch_mode
        )

        # Get all CE IDs per WP
        ce_stmt = select(
            CostElement.work_package_id, CostElement.cost_element_id
        ).where(
            CostElement.work_package_id.in_(work_package_ids),
            func.upper(CostElement.valid_time).is_(None),
            CostElement.deleted_at.is_(None),
        )
        ce_result = await self.db.execute(ce_stmt)
        wp_to_ces: dict[UUID, list[UUID]] = {}
        all_ce_ids: list[UUID] = []
        for row in ce_result.all():
            wp_to_ces.setdefault(row.work_package_id, []).append(row.cost_element_id)
            all_ce_ids.append(row.cost_element_id)

        cumulative_start = datetime.min.replace(tzinfo=UTC)
        ac_raw_task = (
            self.cr_service.get_cumulative_costs_batch(
                all_ce_ids, cumulative_start, control_date, control_date
            )
            if all_ce_ids
            else self._empty_ce_cumulative_costs()
        )
        async with DB_CONCURRENCY_SEMAPHORE:
            ac_raw, progress_raw, baseline_map = await asyncio.gather(
                ac_raw_task,
                self.pe_service.get_progress_history_batch(
                    work_package_ids, control_date
                ),
                self.sb_service.get_baselines_for_work_packages(
                    work_package_ids, branch, control_date
                ),
            )

        result: dict[UUID, list[EVMTimeSeriesPoint]] = {}

        for wp_id in work_package_ids:
            wp = wp_map.get(wp_id)
            if wp is None or wp.budget_amount is None:
                continue

            bac = wp.budget_amount
            baseline = baseline_map.get(wp_id)

            # Build AC map (aggregate across all CEs for this WP)
            ac_map: dict[datetime, Decimal] = {}
            for ce_id in wp_to_ces.get(wp_id, []):
                for entry in ac_raw.get(ce_id, []):
                    entry_date = datetime.fromisoformat(
                        entry["registration_date"]
                    ).replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=UTC)
                    ac_map[entry_date] = ac_map.get(entry_date, Decimal("0")) + Decimal(
                        str(entry["cumulative_amount"])
                    )

            # Build EV map
            ev_map: dict[datetime, tuple[Decimal, Decimal]] = {}
            pe_list = progress_raw.get(wp_id, [])
            sorted_entries = sorted(
                [(p, p.valid_time.lower if p.valid_time else None) for p in pe_list],
                key=lambda x: x[1] if x[1] is not None else datetime.min,
            )
            for p_entry, valid_lower in sorted_entries:
                if valid_lower is not None:
                    report_date = valid_lower.replace(
                        hour=0, minute=0, second=0, microsecond=0
                    )
                    ev = bac * p_entry.progress_percentage / Decimal("100")
                    ev_map[report_date] = (p_entry.progress_percentage, ev)

            # Determine date range
            if baseline is None:
                if not ac_map and not ev_map:
                    continue
                earliest_ac = min(ac_map.keys()) if ac_map else control_date
                earliest_ev = min(ev_map.keys()) if ev_map else control_date
                earliest_date = min(earliest_ac, earliest_ev)
                dates = self._generate_date_intervals(
                    earliest_date, control_date, granularity
                )
                strategy = None
                baseline_end = control_date
            else:
                from app.services.progression import get_progression_strategy

                strategy = get_progression_strategy(baseline.progression_type)
                start_date = baseline.start_date
                end_date = max(baseline.end_date, control_date)
                dates = self._generate_date_intervals(start_date, end_date, granularity)
                baseline_end = baseline.end_date

            sorted_ac_dates = sorted(ac_map.keys())
            sorted_ev_dates = sorted(ev_map.keys())

            final_ac = Decimal("0")
            ac_idx = bisect_right(sorted_ac_dates, control_date)
            if ac_idx > 0:
                final_ac = ac_map[sorted_ac_dates[ac_idx - 1]]

            final_ev = Decimal("0")
            ev_idx = bisect_right(sorted_ev_dates, control_date)
            if ev_idx > 0:
                final_ev = ev_map[sorted_ev_dates[ev_idx - 1]][1]

            latest_ev = Decimal("0")
            ev_cursor = 0
            wp_points: list[EVMTimeSeriesPoint] = []

            for date in dates:
                if baseline is None or strategy is None:
                    pv = Decimal("0")
                elif date > baseline_end:
                    pv = bac
                else:
                    if (
                        baseline.start_date is None
                        or baseline.end_date is None
                        or baseline.start_date >= baseline.end_date
                    ):
                        pv = Decimal("0")
                    else:
                        progress = strategy.calculate_progress(
                            date, baseline.start_date, baseline.end_date
                        )
                        pv = bac * Decimal(str(progress))

                if date > control_date:
                    ev = final_ev
                    ac = final_ac
                else:
                    while (
                        ev_cursor < len(sorted_ev_dates)
                        and sorted_ev_dates[ev_cursor] <= date
                    ):
                        latest_ev = ev_map[sorted_ev_dates[ev_cursor]][1]
                        ev_cursor += 1
                    ev = latest_ev
                    ac_idx = bisect_right(sorted_ac_dates, date)
                    ac = (
                        ac_map[sorted_ac_dates[ac_idx - 1]]
                        if ac_idx > 0
                        else Decimal("0")
                    )

                cpi, spi = self._calculate_indices(ev=ev, ac=ac, pv=pv)
                wp_points.append(
                    EVMTimeSeriesPoint(
                        date=date,
                        pv=pv,
                        ev=ev,
                        ac=ac,
                        forecast=pv,
                        actual=ac,
                        cpi=float(cpi) if cpi is not None else None,
                        spi=float(spi) if spi is not None else None,
                    )
                )

            result[wp_id] = wp_points

        return result

    def _generate_date_intervals(
        self,
        start_date: datetime,
        end_date: datetime,
        granularity: EVMTimeSeriesGranularity,
    ) -> list[datetime]:
        """Generate date intervals based on granularity."""
        dates: list[datetime] = []
        current_date = start_date

        if granularity == EVMTimeSeriesGranularity.DAY:
            while current_date <= end_date:
                dates.append(current_date)
                current_date = current_date + timedelta(days=1)
        elif granularity == EVMTimeSeriesGranularity.WEEK:
            while current_date <= end_date:
                dates.append(current_date)
                current_date = current_date + timedelta(weeks=1)
        elif granularity == EVMTimeSeriesGranularity.MONTH:
            while current_date <= end_date:
                dates.append(current_date)
                if current_date.month == 12:
                    current_date = current_date.replace(
                        year=current_date.year + 1, month=1, day=1
                    )
                else:
                    current_date = current_date.replace(
                        month=current_date.month + 1, day=1
                    )

        if dates and dates[-1] != end_date:
            dates.append(end_date)

        return dates

    @log_performance("_get_wbs_element_evm_timeseries")
    async def _get_wbs_element_evm_timeseries(
        self,
        wbs_element_id: UUID,
        granularity: EVMTimeSeriesGranularity,
        control_date: datetime,
        branch: str,
        branch_mode: BranchMode,
    ) -> EVMTimeSeriesResponse:
        """Get EVM time-series for a WBS Element by aggregating child Work Packages."""
        wp_ids = await self._resolve_work_package_ids_for_wbs(
            [wbs_element_id], branch, branch_mode
        )

        if not wp_ids:
            return EVMTimeSeriesResponse(
                granularity=granularity,
                points=[],
                start_date=control_date,
                end_date=control_date,
                total_points=0,
            )

        return await self._aggregate_wp_timeseries(
            wp_ids, granularity, control_date, branch, branch_mode
        )

    @log_performance("_get_control_account_evm_timeseries")
    async def _get_control_account_evm_timeseries(
        self,
        control_account_id: UUID,
        granularity: EVMTimeSeriesGranularity,
        control_date: datetime,
        branch: str,
        branch_mode: BranchMode,
    ) -> EVMTimeSeriesResponse:
        """Get EVM time-series for a Control Account by aggregating child Work Packages."""
        wp_ids = await self._resolve_work_package_ids_for_ca(
            [control_account_id], branch
        )

        if not wp_ids:
            return EVMTimeSeriesResponse(
                granularity=granularity,
                points=[],
                start_date=control_date,
                end_date=control_date,
                total_points=0,
            )

        return await self._aggregate_wp_timeseries(
            wp_ids, granularity, control_date, branch, branch_mode
        )

    async def _aggregate_wp_timeseries(
        self,
        wp_ids: list[UUID],
        granularity: EVMTimeSeriesGranularity,
        control_date: datetime,
        branch: str,
        branch_mode: BranchMode,
    ) -> EVMTimeSeriesResponse:
        """Aggregate time-series for multiple work packages."""
        ce_points_map = await self._generate_timeseries_points_batch(
            wp_ids,
            granularity,
            control_date,
            branch,
            branch_mode,
        )

        all_timeseries: list[EVMTimeSeriesResponse] = []
        for points in ce_points_map.values():
            if not points:
                continue
            all_timeseries.append(
                EVMTimeSeriesResponse(
                    granularity=granularity,
                    points=points,
                    start_date=points[0].date,
                    end_date=points[-1].date,
                    total_points=len(points),
                )
            )

        if not all_timeseries:
            return EVMTimeSeriesResponse(
                granularity=granularity,
                points=[],
                start_date=control_date,
                end_date=control_date,
                total_points=0,
            )

        overall_start_date = control_date
        overall_end_date = control_date
        for ts in all_timeseries:
            if ts.start_date < overall_start_date:
                overall_start_date = ts.start_date
            if ts.end_date > overall_end_date:
                overall_end_date = ts.end_date

        if overall_start_date > overall_end_date:
            overall_start_date = control_date
            overall_end_date = control_date

        dates = self._generate_date_intervals(
            start_date=overall_start_date,
            end_date=overall_end_date,
            granularity=granularity,
        )

        aggregated_points = self._aggregate_timeseries(all_timeseries, dates)

        return EVMTimeSeriesResponse(
            granularity=granularity,
            points=aggregated_points,
            start_date=overall_start_date,
            end_date=overall_end_date,
            total_points=len(aggregated_points),
        )

    @log_performance("_get_project_evm_timeseries")
    async def _get_project_evm_timeseries(
        self,
        project_id: UUID,
        granularity: EVMTimeSeriesGranularity,
        control_date: datetime,
        branch: str,
        branch_mode: BranchMode,
    ) -> EVMTimeSeriesResponse:
        """Get EVM time-series for a Project by aggregating all its Work Packages."""
        project = await self.project_service.get_as_of(
            entity_id=project_id,
            as_of=control_date,
            branch=branch,
            branch_mode=branch_mode,
        )

        if project is None:
            return EVMTimeSeriesResponse(
                granularity=granularity,
                points=[],
                start_date=control_date,
                end_date=control_date,
                total_points=0,
            )

        # Resolve all work packages for the project
        wbs_elements, _ = await self.wbs_service.get_wbs_elements(
            project_id=project_id,
            branch=branch,
            branch_mode=branch_mode,
            as_of=None,
            skip=0,
            limit=10000,
        )

        if not wbs_elements:
            return EVMTimeSeriesResponse(
                granularity=granularity,
                points=[],
                start_date=project.start_date or control_date,
                end_date=project.end_date or control_date,
                total_points=0,
            )

        wbs_ids = [wbs.wbs_element_id for wbs in wbs_elements]
        wp_ids = await self._resolve_work_package_ids_for_wbs(
            wbs_ids, branch, branch_mode
        )

        if not wp_ids:
            return EVMTimeSeriesResponse(
                granularity=granularity,
                points=[],
                start_date=project.start_date or control_date,
                end_date=project.end_date or control_date,
                total_points=0,
            )

        result = await self._aggregate_wp_timeseries(
            wp_ids, granularity, control_date, branch, branch_mode
        )

        # Expand to project date range if broader
        project_start = project.start_date or control_date
        project_end = project.end_date or control_date
        if control_date > project_end:
            project_end = control_date

        return EVMTimeSeriesResponse(
            granularity=result.granularity,
            points=result.points,
            start_date=min(result.start_date, project_start),
            end_date=max(result.end_date, project_end),
            total_points=result.total_points,
        )

    @staticmethod
    async def _empty_ce_cumulative_costs() -> dict[UUID, list[dict[str, Any]]]:
        """Return empty cumulative costs dict for asyncio.gather compatibility."""
        return {}

    async def _get_ev_as_of_date(
        self,
        work_package_id: UUID,
        as_of: datetime,
        branch: str,
        branch_mode: BranchMode,
    ) -> Decimal:
        """Get Earned Value (EV) as of a specific date."""
        bac = await self._get_bac_as_of(work_package_id, as_of, branch, branch_mode)
        if bac is None:
            return Decimal("0")

        ev, _, _ = await self._get_ev_as_of(work_package_id, as_of, bac)
        return ev
