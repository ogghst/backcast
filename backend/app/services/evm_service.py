"""EVM (Earned Value Management) Service - orchestrates EVM metrics calculation."""

import logging
import time
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta
from decimal import Decimal
from functools import wraps
from typing import Any, TypeVar
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.versioning.enums import BranchMode
from app.models.schemas.evm import (
    EntityType,
    EVMMetricsRead,
    EVMMetricsResponse,
    EVMTimeSeriesGranularity,
    EVMTimeSeriesPoint,
    EVMTimeSeriesResponse,
)
from app.services.cost_element_service import CostElementService
from app.services.cost_registration_service import CostRegistrationService
from app.services.forecast_service import ForecastService
from app.services.progress_entry_service import ProgressEntryService
from app.services.project import ProjectService
from app.services.schedule_baseline_service import ScheduleBaselineService
from app.services.wbe import WBEService

logger = logging.getLogger(__name__)

T = TypeVar("T")


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
                # Log warnings for slow operations
                if (
                    "timeseries" in operation_name.lower()
                    and duration_ms > 1000
                ):
                    logger.warning(
                        f"EVM Performance: {operation_name} exceeded 1s budget: "
                        f"{duration_ms:.2f}ms"
                    )
                elif (
                    "metrics" in operation_name.lower()
                    and duration_ms > 500
                ):
                    logger.warning(
                        f"EVM Performance: {operation_name} exceeded 500ms budget: "
                        f"{duration_ms:.2f}ms"
                    )

        return wrapper

    return decorator




class EVMService:
    """Service for calculating EVM metrics with time-travel support.

    Orchestrates the calculation of all EVM metrics:
    - BAC (Budget at Completion)
    - PV (Planned Value)
    - AC (Actual Cost)
    - EV (Earned Value)
    - EAC (Estimate at Completion) - from forecast
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
        self.ce_service = CostElementService(db)
        self.sb_service = ScheduleBaselineService(db)
        self.cr_service = CostRegistrationService(db)
        self.pe_service = ProgressEntryService(db)
        self.f_service = ForecastService(db)
        self.wbe_service = WBEService(db)
        self.project_service = ProjectService(db)

    @log_performance("calculate_evm_metrics")
    async def calculate_evm_metrics(
        self,
        cost_element_id: UUID,
        control_date: datetime,
        branch: str = "main",
        branch_mode: BranchMode = BranchMode.MERGE,
    ) -> EVMMetricsRead:
        """Calculate all EVM metrics for a cost element as of control_date.

        All calculations respect time-travel (control_date) and branch mode:
        - ISOLATED: Only use data from the specified branch
        - MERGE: Use data from specified branch, falling back to parent branches

        Args:
            cost_element_id: The cost element to calculate metrics for
            control_date: The control date for time-travel query (fetches entities at correct valid_time)
            branch: Branch name (default: "main")
            branch_mode: Branch isolation mode (default: MERGE)

        Returns:
            EVMMetricsRead with all calculated metrics

        Raises:
            ValueError: If cost element not found
        """
        warning = None

        # Get BAC (Budget at Completion) with time-travel and branch mode
        bac = await self._get_bac_as_of(cost_element_id, control_date, branch, branch_mode)
        if bac is None:
            raise ValueError(f"Cost element {cost_element_id} not found")

        # Get PV (Planned Value) from schedule baseline with time-travel and branch mode
        pv = await self._get_pv_as_of(cost_element_id, control_date, branch, branch_mode)

        # Get AC (Actual Cost) from cost registrations (global facts, not branchable)
        ac = await self._get_ac_as_of(cost_element_id, control_date)

        # Get EV (Earned Value) from progress entries (global facts, not branchable)
        ev, progress_percentage, ev_warning = await self._get_ev_as_of(
            cost_element_id, control_date, bac
        )
        if ev_warning:
            warning = ev_warning

        # Calculate variances
        cv, sv = self._calculate_variances(ev, ac, pv)

        # Calculate performance indices
        cpi, spi = self._calculate_indices(ev, ac, pv)

        # Get EAC (Estimate at Completion) from forecast with time-travel and branch mode
        eac = await self._get_eac_as_of(cost_element_id, control_date, branch, branch_mode)

        # Calculate VAC (Variance at Completion) and ETC (Estimate to Complete)
        # VAC = BAC - EAC (negative = over budget, positive = under budget)
        # ETC = EAC - AC (remaining work cost)
        vac = None
        etc = None
        cpi_forecast = None

        if eac is not None:
            vac = bac - eac
            etc = eac - ac

            # Forecast-based efficiency (BAC / EAC)
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
            cost_element_id=cost_element_id,
            control_date=control_date,
            branch=branch,
            branch_mode=branch_mode,
            progress_percentage=progress_percentage,
            warning=warning,
            cpi_forecast=cpi_forecast
        )

    async def _get_bac_as_of(
        self, cost_element_id: UUID, as_of: datetime, branch: str, branch_mode: BranchMode
    ) -> Decimal | None:
        """Get Budget at Completion (BAC) as of specified date with branch mode.

        Args:
            cost_element_id: The cost element to get BAC for
            as_of: Time-travel query date (fetches entity at correct valid_time)
            branch: Branch name
            branch_mode: Branch isolation mode (ISOLATED or MERGE)

        Returns:
            BAC value or None if cost element not found
        """
        cost_element = await self.ce_service.get_as_of(
            entity_id=cost_element_id, as_of=as_of, branch=branch, branch_mode=branch_mode
        )
        if cost_element is None:
            return None
        return cost_element.budget_amount

    async def _get_pv_as_of(
        self, cost_element_id: UUID, as_of: datetime, branch: str, branch_mode: BranchMode
    ) -> Decimal:
        """Get Planned Value (PV) as of specified date with branch mode.

        PV = BAC × Progress (from schedule baseline progression strategy)

        Uses time-travel to fetch the schedule baseline that was active at the control_date.

        Args:
            cost_element_id: The cost element to get PV for
            as_of: Time-travel query date (fetches baseline at correct valid_time)
            branch: Branch name
            branch_mode: Branch isolation mode (ISOLATED or MERGE)

        Returns:
            PV value (0 if no baseline or error)
        """
        try:
            # First, get the cost element to find its schedule_baseline_id
            cost_element = await self.ce_service.get_as_of(
                entity_id=cost_element_id, as_of=as_of, branch=branch, branch_mode=branch_mode
            )

            if cost_element is None or cost_element.schedule_baseline_id is None:
                # No cost element or no baseline means no planned value
                return Decimal("0")

            # Get the schedule baseline as of the control date (time-travel)
            schedule_baseline = await self.sb_service.get_as_of(
                entity_id=cost_element.schedule_baseline_id,
                as_of=as_of,
                branch=branch,
                branch_mode=branch_mode,
            )

            if schedule_baseline is None:
                # No baseline found at this control_date
                return Decimal("0")

            # Get BAC from cost element (already fetched above)
            bac = cost_element.budget_amount
            if bac is None:
                return Decimal("0")

            # Calculate progress percentage using progression strategy
            from app.services.progression import get_progression_strategy

            strategy = get_progression_strategy(schedule_baseline.progression_type)

            progress = strategy.calculate_progress(
                current_date=as_of,
                start_date=schedule_baseline.start_date,
                end_date=schedule_baseline.end_date,
            )

            # PV = BAC × Progress
            # progress is a float between 0.0 and 1.0 (e.g., 0.5 for 50%)
            pv = bac * Decimal(str(progress))

            return pv
        except Exception:
            # If any error occurs, return 0
            return Decimal("0")

    async def _get_ac_as_of(self, cost_element_id: UUID, as_of: datetime) -> Decimal:
        """Get Actual Cost (AC) as of specified date.

        AC = sum of all cost registrations for the cost element

        Args:
            cost_element_id: The cost element to get AC for
            as_of: Time-travel query date

        Returns:
            AC value (0 if no costs)
        """
        total = await self.cr_service.get_total_for_cost_element(
            cost_element_id=cost_element_id, as_of=as_of
        )
        return Decimal(str(total)) if total else Decimal("0")

    async def _get_ev_as_of(
        self, cost_element_id: UUID, as_of: datetime, bac: Decimal
    ) -> tuple[Decimal, Decimal | None, str | None]:
        """Get Earned Value (EV) as of specified date.

        EV = BAC × Progress Percentage (from progress entries)

        Args:
            cost_element_id: The cost element to get EV for
            as_of: Time-travel query date
            bac: Budget at Completion

        Returns:
            Tuple of (EV, progress_percentage, warning)
        """
        # Get latest progress entry
        progress_entry = await self.pe_service.get_latest_progress(
            cost_element_id=cost_element_id, as_of=as_of
        )

        if progress_entry is None:
            # No progress reported: EV = 0 with warning
            return Decimal("0"), None, "No progress reported for this cost element"

        progress_percentage = progress_entry.progress_percentage
        # EV = BAC × Progress Percentage / 100
        ev = bac * progress_percentage / Decimal("100")

        return ev, progress_percentage, None

    async def _get_eac_as_of(
        self, cost_element_id: UUID, as_of: datetime, branch: str, branch_mode: BranchMode
    ) -> Decimal | None:
        """Get Estimate at Completion (EAC) from forecast.

        Fetches the forecast associated with the cost element using time-travel.
        The forecast provides the EAC (Estimate at Completion) value.

        Uses Valid Time Travel semantics:
        - Only checks valid_time (when the forecast was valid in the real world)
        - Does NOT check transaction_time (when recorded in database)

        Args:
            cost_element_id: The cost element to get EAC for
            as_of: Time-travel query date (fetches forecast at correct valid_time)
            branch: Branch name
            branch_mode: Branch isolation mode (STRICT or MERGE)

        Returns:
            EAC value or None if forecast not found
        """
        # First, get the cost element to find its forecast_id
        cost_element = await self.ce_service.get_as_of(
            entity_id=cost_element_id, as_of=as_of, branch=branch, branch_mode=branch_mode
        )

        if cost_element is None or cost_element.forecast_id is None:
            # No cost element or no forecast associated
            return None

        # Get the forecast as of the control date (time-travel)
        # This uses Valid Time Travel semantics via BranchableService.get_as_of()
        forecast = await self.f_service.get_as_of(
            entity_id=cost_element.forecast_id,
            as_of=as_of,
            branch=branch,
            branch_mode=branch_mode,
        )

        if forecast is None:
            # No forecast found at this control_date
            return None

        return forecast.eac_amount

    def _calculate_variances(
        self, ev: Decimal, ac: Decimal, pv: Decimal
    ) -> tuple[Decimal, Decimal]:
        """Calculate cost and schedule variances.

        Args:
            ev: Earned Value
            ac: Actual Cost
            pv: Planned Value

        Returns:
            Tuple of (CV, SV)
            - CV = EV - AC (negative = over budget)
            - SV = EV - PV (negative = behind schedule)
        """
        cv = ev - ac
        sv = ev - pv
        return cv, sv

    def _calculate_indices(
        self, ev: Decimal, ac: Decimal, pv: Decimal
    ) -> tuple[Decimal | None, Decimal | None]:
        """Calculate cost and schedule performance indices.

        Args:
            ev: Earned Value
            ac: Actual Cost
            pv: Planned Value

        Returns:
            Tuple of (CPI, SPI)
            - CPI = EV / AC (< 1.0 = over budget, None if AC = 0)
            - SPI = EV / PV (< 1.0 = behind schedule, None if PV = 0)
        """
        # CPI = EV / AC (handle division by zero)
        if ac == 0:
            cpi = None
        else:
            cpi = ev / ac

        # SPI = EV / PV (handle division by zero)
        if pv == 0:
            spi = None
        else:
            spi = ev / pv

        return cpi, spi

    @log_performance("calculate_evm_metrics_batch")
    async def calculate_evm_metrics_batch(
        self,
        entity_type: EntityType,
        entity_ids: list[UUID],
        control_date: datetime,
        branch: str = "main",
        branch_mode: BranchMode = BranchMode.MERGE,
    ) -> EVMMetricsResponse:
        """Calculate EVM metrics for multiple entities and aggregate them.

        This method calculates EVM metrics for each entity individually,
        then aggregates them using sum for amounts and weighted average for indices.

        For WBE entities, this method aggregates all child cost elements.

        Args:
            entity_type: Type of entities (cost_element, wbe, project)
            entity_ids: List of entity IDs to calculate metrics for
            control_date: Control date for time-travel query
            branch: Branch name (default: "main")
            branch_mode: Branch isolation mode (default: MERGE)

        Returns:
            EVMMetricsResponse with aggregated metrics

        Raises:
            ValueError: If entity_type is not supported or no entities found
        """
        if not entity_ids:
            # Return zero metrics for empty list
            return EVMMetricsResponse(
                entity_type=entity_type,
                entity_id=UUID("00000000-0000-0000-0000-000000000000"),  # Placeholder
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
                control_date=control_date,
                branch=branch,
                branch_mode=branch_mode,
                progress_percentage=None,
                warning="No entities provided",
            )

        # Handle WBE entity type
        if entity_type == EntityType.WBE:
            return await self._calculate_wbe_evm_metrics(
                wbe_ids=entity_ids,
                control_date=control_date,
                branch=branch,
                branch_mode=branch_mode,
            )

        # Handle PROJECT entity type
        if entity_type == EntityType.PROJECT:
            return await self._calculate_project_evm_metrics(
                project_ids=entity_ids,
                control_date=control_date,
                branch=branch,
                branch_mode=branch_mode,
            )

        # For now, only support cost_element, wbe, and project entity types
        if entity_type != EntityType.COST_ELEMENT:
            raise ValueError(
                f"Entity type {entity_type} not yet supported. "
                "Currently only cost_element, wbe, and project are supported."
            )

        # Calculate metrics for each cost element
        individual_metrics: list[EVMMetricsRead] = []
        for entity_id in entity_ids:
            try:
                metrics = await self.calculate_evm_metrics(
                    cost_element_id=entity_id,
                    control_date=control_date,
                    branch=branch,
                    branch_mode=branch_mode,
                )
                individual_metrics.append(metrics)
            except ValueError:
                # Skip entities that don't exist
                continue

        if not individual_metrics:
            raise ValueError(f"No valid entities found for IDs: {entity_ids}")

        # Convert to EVMMetricsResponse and aggregate
        response_metrics = [
            self._convert_to_response(metrics, entity_type)
            for metrics in individual_metrics
        ]

        return self.aggregate_evm_metrics(response_metrics)

    async def _calculate_wbe_evm_metrics(
        self,
        wbe_ids: list[UUID],
        control_date: datetime,
        branch: str,
        branch_mode: BranchMode,
    ) -> EVMMetricsResponse:
        """Calculate EVM metrics for WBEs by aggregating child cost elements.

        Args:
            wbe_ids: List of WBE IDs to calculate metrics for
            control_date: Control date for time-travel query
            branch: Branch name
            branch_mode: Branch isolation mode

        Returns:
            EVMMetricsResponse with aggregated metrics from all child cost elements

        Raises:
            ValueError: If no valid cost elements found
        """
        # Collect all cost element IDs from all WBEs
        all_cost_element_ids: list[UUID] = []

        for wbe_id in wbe_ids:
            # Get all cost elements for this WBE
            # Note: We pass None for as_of to get current versions, then time-travel
            # is handled in calculate_evm_metrics for each cost element
            cost_elements, _ = await self.ce_service.get_cost_elements(
                filters={"wbe_id": wbe_id},
                branch=branch,
                branch_mode=branch_mode,
                as_of=None,  # Get current versions
                skip=0,
                limit=10000,  # Large limit to get all cost elements
            )

            # Extract cost element IDs (using cost_element_id from CostElement model)
            for ce in cost_elements:
                all_cost_element_ids.append(ce.cost_element_id)

        if not all_cost_element_ids:
            # No cost elements found for these WBEs
            return EVMMetricsResponse(
                entity_type=EntityType.WBE,
                entity_id=wbe_ids[0],  # Use first WBE ID
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
                control_date=control_date,
                branch=branch,
                branch_mode=branch_mode,
                progress_percentage=None,
                warning="No cost elements found for WBEs",
            )

        # Calculate metrics for all cost elements
        individual_metrics: list[EVMMetricsRead] = []
        for ce_id in all_cost_element_ids:
            try:
                metrics = await self.calculate_evm_metrics(
                    cost_element_id=ce_id,
                    control_date=control_date,
                    branch=branch,
                    branch_mode=branch_mode,
                )
                individual_metrics.append(metrics)
            except ValueError:
                # Skip cost elements that don't exist or have errors
                continue

        if not individual_metrics:
            raise ValueError(f"No valid cost elements found for WBEs: {wbe_ids}")

        # Convert to EVMMetricsResponse and aggregate
        response_metrics = [
            self._convert_to_response(metrics, EntityType.WBE)
            for metrics in individual_metrics
        ]

        aggregated = self.aggregate_evm_metrics(response_metrics)

        # Override entity_id to use the WBE ID instead of first cost element ID
        # When aggregating for a single WBE, use that WBE's ID
        # When aggregating for multiple WBEs, use the first WBE ID
        return EVMMetricsResponse(
            entity_type=EntityType.WBE,
            entity_id=wbe_ids[0],  # Use first WBE ID, not cost element ID
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
        """Calculate EVM metrics for Projects by aggregating child WBEs.

        Args:
            project_ids: List of Project IDs to calculate metrics for
            control_date: Control date for time-travel query
            branch: Branch name
            branch_mode: Branch isolation mode

        Returns:
            EVMMetricsResponse with aggregated metrics from all child WBEs

        Raises:
            ValueError: If no valid WBEs found
        """
        # Collect all WBE IDs from all Projects
        all_wbe_ids: list[UUID] = []

        for project_id in project_ids:
            # Get all WBEs for this project
            wbes, _ = await self.wbe_service.get_wbes(
                project_id=project_id,
                branch=branch,
                branch_mode=branch_mode,
                as_of=None,  # Get current versions
                skip=0,
                limit=10000,  # Large limit to get all WBEs
            )

            # Extract WBE IDs (using wbe_id from WBE model)
            for wbe in wbes:
                all_wbe_ids.append(wbe.wbe_id)

        if not all_wbe_ids:
            # No WBEs found for these projects
            return EVMMetricsResponse(
                entity_type=EntityType.PROJECT,
                entity_id=project_ids[0],  # Use first project ID
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
                control_date=control_date,
                branch=branch,
                branch_mode=branch_mode,
                progress_percentage=None,
                warning="No WBEs found for project",
            )

        # Calculate metrics for all WBEs (which in turn aggregate cost elements)
        wbe_result = await self._calculate_wbe_evm_metrics(
            wbe_ids=all_wbe_ids,
            control_date=control_date,
            branch=branch,
            branch_mode=branch_mode,
        )

        # Override entity_type and entity_id to reflect PROJECT level
        return EVMMetricsResponse(
            entity_type=EntityType.PROJECT,
            entity_id=project_ids[0],  # Use first project ID
            bac=wbe_result.bac,
            pv=wbe_result.pv,
            ac=wbe_result.ac,
            ev=wbe_result.ev,
            cv=wbe_result.cv,
            sv=wbe_result.sv,
            cpi=wbe_result.cpi,
            spi=wbe_result.spi,
            eac=wbe_result.eac,
            vac=wbe_result.vac,
            etc=wbe_result.etc,
            control_date=wbe_result.control_date,
            branch=wbe_result.branch,
            branch_mode=wbe_result.branch_mode,
            progress_percentage=wbe_result.progress_percentage,
            warning=wbe_result.warning,
        )

    def _convert_to_response(
        self, metrics: EVMMetricsRead, entity_type: EntityType
    ) -> EVMMetricsResponse:
        """Convert EVMMetricsRead to EVMMetricsResponse.

        Args:
            metrics: The cost-element-specific metrics
            entity_type: The entity type to assign

        Returns:
            EVMMetricsResponse with generic structure
        """
        return EVMMetricsResponse(
            entity_type=entity_type,
            entity_id=metrics.cost_element_id,
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
        Calculates BAC-weighted average for indices (CPI, SPI).

        Args:
            metrics_list: List of EVMMetricsResponse to aggregate

        Returns:
            Aggregated EVMMetricsResponse

        Raises:
            ValueError: If metrics_list is empty
        """
        if not metrics_list:
            raise ValueError("Cannot aggregate empty metrics list")

        # Use the first metric's metadata
        first = metrics_list[0]
        entity_type = first.entity_type
        control_date = first.control_date
        branch = first.branch
        branch_mode = first.branch_mode

        # Sum amount fields
        bac: Decimal = sum(Decimal(str(m.bac)) for m in metrics_list)
        pv: Decimal = sum(Decimal(str(m.pv)) for m in metrics_list)
        ac: Decimal = sum(Decimal(str(m.ac)) for m in metrics_list)
        ev: Decimal = sum(Decimal(str(m.ev)) for m in metrics_list)

        # Calculate variances from summed values
        cv = ev - ac
        sv = ev - pv

        # BAC-weighted average for indices
        cpi = self._calculate_weighted_index(metrics_list, "cpi", bac)
        spi = self._calculate_weighted_index(metrics_list, "spi", bac)

        # Sum forecast-based fields (if all have values)
        eac_list = [Decimal(str(m.eac)) for m in metrics_list if m.eac is not None]
        eac = sum(eac_list) if len(eac_list) == len(metrics_list) else None

        vac_list = [Decimal(str(m.vac)) for m in metrics_list if m.vac is not None]
        vac = sum(vac_list) if len(vac_list) == len(metrics_list) else None

        etc_list = [Decimal(str(m.etc)) for m in metrics_list if m.etc is not None]
        etc = sum(etc_list) if len(etc_list) == len(metrics_list) else None

        # Aggregate progress percentage (weighted by BAC)
        total_bac = bac
        progress_percentage = None
        if total_bac > 0:
            weighted_progress = sum(
                Decimal(str(m.progress_percentage or 0)) * Decimal(str(m.bac))
                for m in metrics_list
            )
            progress_percentage = weighted_progress / total_bac

        # Collect warnings (concatenate if multiple)
        warnings = [m.warning for m in metrics_list if m.warning]
        warning = "; ".join(warnings) if warnings else None

        # Create placeholder entity_id (use first entity's ID for now)
        entity_id = first.entity_id

        return EVMMetricsResponse(
            entity_type=entity_type,
            entity_id=entity_id,
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
            control_date=control_date,
            branch=branch,
            branch_mode=branch_mode,
            progress_percentage=progress_percentage,
            warning=warning,
        )

    def _calculate_weighted_index(
        self, metrics_list: list[EVMMetricsResponse], index_name: str, total_bac: Decimal
    ) -> Decimal | None:
        """Calculate BAC-weighted average for a performance index.

        Args:
            metrics_list: List of metrics to aggregate
            index_name: Name of the index field ("cpi" or "spi")
            total_bac: Sum of all BAC values

        Returns:
            Weighted average index value, or None if all indices are None
        """
        if total_bac == 0:
            return None

        weighted_sum = Decimal("0")
        valid_count = 0

        for metrics in metrics_list:
            index_value = getattr(metrics, index_name)
            if index_value is not None:
                # Convert float values to Decimal for precise calculation
                index_decimal = Decimal(str(index_value))
                bac_decimal = Decimal(str(metrics.bac))
                weighted_sum += index_decimal * bac_decimal
                valid_count += 1

        if valid_count == 0:
            return None

        return weighted_sum / total_bac

    @log_performance("get_evm_timeseries")
    async def get_evm_timeseries(
        self,
        entity_type: EntityType,
        entity_id: UUID,
        granularity: EVMTimeSeriesGranularity,
        control_date: datetime,
        branch: str = "main",
        branch_mode: BranchMode = BranchMode.MERGE,
    ) -> EVMTimeSeriesResponse:
        """Get historical EVM metrics as time-series data for charts.

        Generates a time-series of EVM metrics (PV, EV, AC) over a date range
        with server-side aggregation at the specified granularity (day, week, month).

        The date range is context-dependent:
        - Cost element: Uses its schedule baseline date range
        - WBE: Aggregates time-series from all child cost elements
        - Project: From project start to max(project end, control_date)

        Args:
            entity_type: Type of entity (cost_element, wbe, project)
            entity_id: ID of the entity
            granularity: Time granularity (day, week, month)
            control_date: Control date for time-travel queries
            branch: Branch name (default: "main")
            branch_mode: Branch isolation mode (default: MERGE)

        Returns:
            EVMTimeSeriesResponse with aggregated time-series data

        Raises:
            ValueError: If entity_type is not supported or entity not found
        """
        # Handle WBE entity type
        if entity_type == EntityType.WBE:
            return await self._get_wbe_evm_timeseries(
                wbe_id=entity_id,
                granularity=granularity,
                control_date=control_date,
                branch=branch,
                branch_mode=branch_mode,
            )

        # Handle PROJECT entity type
        if entity_type == EntityType.PROJECT:
            return await self._get_project_evm_timeseries(
                project_id=entity_id,
                granularity=granularity,
                control_date=control_date,
                branch=branch,
                branch_mode=branch_mode,
            )

        # For now, only support cost_element, wbe, and project entity types
        if entity_type != EntityType.COST_ELEMENT:
            raise ValueError(
                f"Entity type {entity_type} not yet supported for time-series. "
                "Currently only cost_element, wbe, and project are supported."
            )

        # Get the cost element to find its schedule baseline
        cost_element = await self.ce_service.get_as_of(
            entity_id=entity_id, as_of=control_date, branch=branch, branch_mode=branch_mode
        )

        if cost_element is None:
            raise ValueError(f"Cost element {entity_id} not found")

        # Get the schedule baseline for date range
        if cost_element.schedule_baseline_id is None:
            # No baseline means no date range - return empty time-series
            return EVMTimeSeriesResponse(
                granularity=granularity,
                points=[],
                start_date=control_date,
                end_date=control_date,
                total_points=0,
            )

        schedule_baseline = await self.sb_service.get_as_of(
            entity_id=cost_element.schedule_baseline_id,
            as_of=control_date,
            branch=branch,
            branch_mode=branch_mode,
        )

        if schedule_baseline is None:
            # No baseline found - return empty time-series
            return EVMTimeSeriesResponse(
                granularity=granularity,
                points=[],
                start_date=control_date,
                end_date=control_date,
                total_points=0,
            )

        # Determine date range based on entity type
        start_date = schedule_baseline.start_date
        end_date = schedule_baseline.end_date

        # EXTEND TIME SERIES BEYOND BASELINE IF CONTROL_DATE IS LATER
        # This allows viewing projected values (PV) alongside actual data (EV, AC)
        # when the control date extends past the original schedule baseline.
        # Useful for ongoing projects where the schedule baseline hasn't been updated.
        if control_date > end_date:
            end_date = control_date

        # Generate time-series data points
        points = await self._generate_timeseries_points(
            cost_element_id=entity_id,
            start_date=start_date,
            end_date=end_date,
            granularity=granularity,
            control_date=control_date,
            branch=branch,
            branch_mode=branch_mode,
            schedule_baseline_end=schedule_baseline.end_date,  # Pass for distinction
        )

        return EVMTimeSeriesResponse(
            granularity=granularity,
            points=points,
            start_date=start_date,
            end_date=end_date,
            total_points=len(points),
        )

    async def _generate_timeseries_points(
        self,
        cost_element_id: UUID,
        start_date: datetime,
        end_date: datetime,
        granularity: EVMTimeSeriesGranularity,
        control_date: datetime,
        branch: str,
        branch_mode: BranchMode,
        schedule_baseline_end: datetime | None = None,
    ) -> list[EVMTimeSeriesPoint]:
        """Generate time-series data points for EVM metrics.

        OPTIMIZED: Uses batch queries to avoid N+1 query problem.
        Instead of querying for each date individually, fetches all data upfront
        and maps it to dates in memory.

        Args:
            cost_element_id: Cost element ID
            start_date: Start of date range
            end_date: End of date range (may extend beyond baseline end)
            granularity: Time granularity (day, week, month)
            control_date: Control date for time-travel
            branch: Branch name
            branch_mode: Branch isolation mode
            schedule_baseline_end: Original schedule baseline end date for PV projection

        Returns:
            List of EVMTimeSeriesPoint with aggregated metrics
        """
        # Generate date intervals based on granularity
        dates = self._generate_date_intervals(start_date, end_date, granularity)

        # OPTIMIZATION: Batch fetch all data upfront instead of N+1 queries
        # Get BAC once (it doesn't change)
        bac = await self._get_bac_as_of(
            cost_element_id, control_date, branch, branch_mode
        )
        if bac is None:
            return []

        # Fetch cumulative costs for the entire range
        cumulative_costs = await self.cr_service.get_cumulative_costs(
            cost_element_id=cost_element_id,
            start_date=start_date,
            end_date=end_date,
            as_of=control_date,
        )

        # Build a map of date -> cumulative AC for fast lookup
        ac_map: dict[datetime, Decimal] = {}
        for entry in cumulative_costs:
            entry_date = datetime.fromisoformat(
                entry["registration_date"]
            ).replace(hour=0, minute=0, second=0, microsecond=0)
            ac_map[entry_date] = Decimal(str(entry["cumulative_amount"]))

        # Batch fetch all progress entries (EV data) for the cost element
        progress_entries, _ = await self.pe_service.get_progress_history(
            cost_element_id=cost_element_id,
            skip=0,
            limit=10000,  # Large limit to get all history
        )

        # Build a map of date -> progress percentage for fast lookup
        # Sort by reported_date ascending
        min_date = datetime.min
        sorted_entries = sorted(
            progress_entries, key=lambda pe: pe.reported_date or min_date
        )
        ev_map: dict[datetime, tuple[Decimal, Decimal]] = {}

        for entry in sorted_entries:
            if entry.reported_date:
                report_date = entry.reported_date.replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
                ev = bac * entry.progress_percentage / Decimal("100")
                ev_map[report_date] = (entry.progress_percentage, ev)

        # Get schedule baseline for PV calculation (PV is deterministic)
        cost_element = await self.ce_service.get_as_of(
            entity_id=cost_element_id,
            as_of=control_date,
            branch=branch,
            branch_mode=branch_mode,
        )
        if cost_element is None or cost_element.schedule_baseline_id is None:
            return []

        schedule_baseline = await self.sb_service.get_as_of(
            entity_id=cost_element.schedule_baseline_id,
            as_of=control_date,
            branch=branch,
            branch_mode=branch_mode,
        )
        if schedule_baseline is None:
            return []

        # Import progression strategy
        from app.services.progression import get_progression_strategy

        strategy = get_progression_strategy(schedule_baseline.progression_type)

        # Determine the baseline end date for PV projection
        # If schedule_baseline_end is provided, use it; otherwise use baseline's end_date
        baseline_end_for_projection = (
            schedule_baseline_end if schedule_baseline_end else schedule_baseline.end_date
        )

        # Generate points using pre-fetched data (no more queries!)
        points: list[EVMTimeSeriesPoint] = []
        latest_ev = Decimal("0")
        last_calculated_pv = Decimal("0")  # Track last PV for projection beyond baseline

        for date in dates:
            # Calculate PV (deterministic based on date)
            if date > control_date:
                # Future dates: use plan values
                # If date is beyond baseline end, cap progress at 1.0 (100% of BAC)
                if date > baseline_end_for_projection:
                    pv = bac  # PV is capped at BAC (100% progress)
                else:
                    progress = strategy.calculate_progress(
                        current_date=date,
                        start_date=schedule_baseline.start_date,
                        end_date=schedule_baseline.end_date,
                    )
                    pv = bac * Decimal(str(progress))
                    last_calculated_pv = pv  # Remember for projection
                ev = Decimal("0")
                ac = Decimal("0")
            else:
                # Past and current dates: use actual/fetched values
                # If date is beyond baseline end, cap progress at 1.0
                if date > baseline_end_for_projection:
                    pv = bac  # PV is capped at BAC
                else:
                    progress = strategy.calculate_progress(
                        current_date=date,
                        start_date=schedule_baseline.start_date,
                        end_date=schedule_baseline.end_date,
                    )
                    pv = bac * Decimal(str(progress))
                    last_calculated_pv = pv

                # Get EV from progress entries (find latest progress as of date)
                for report_date, (_progress_pct, ev_val) in sorted(
                    ev_map.items()
                ):
                    if report_date <= date:
                        latest_ev = ev_val
                    else:
                        break
                ev = latest_ev

                # Get AC from cost registrations
                latest_ac = Decimal("0")
                for ac_date in sorted(ac_map.keys()):
                    if ac_date <= date:
                        latest_ac = ac_map[ac_date]
                    else:
                        break
                ac = latest_ac

            point = EVMTimeSeriesPoint(
                date=date,
                pv=pv,
                ev=ev,
                ac=ac,
                forecast=pv,  # Forecast equals planned value
                actual=ev,  # Actual equals earned value
            )
            points.append(point)

        return points

    def _generate_date_intervals(
        self,
        start_date: datetime,
        end_date: datetime,
        granularity: EVMTimeSeriesGranularity,
    ) -> list[datetime]:
        """Generate date intervals based on granularity.

        Args:
            start_date: Start of date range
            end_date: End of date range
            granularity: Time granularity (day, week, month)

        Returns:
            List of datetime points at the specified granularity
        """
        dates: list[datetime] = []
        current_date = start_date

        if granularity == EVMTimeSeriesGranularity.DAY:
            # Generate daily points
            while current_date <= end_date:
                dates.append(current_date)
                current_date = current_date + timedelta(days=1)

        elif granularity == EVMTimeSeriesGranularity.WEEK:
            # Generate weekly points (start of each week)
            while current_date <= end_date:
                dates.append(current_date)
                current_date = current_date + timedelta(weeks=1)

        elif granularity == EVMTimeSeriesGranularity.MONTH:
            # Generate monthly points (first day of each month)
            while current_date <= end_date:
                dates.append(current_date)
                # Move to first day of next month
                if current_date.month == 12:
                    current_date = current_date.replace(year=current_date.year + 1, month=1)
                else:
                    current_date = current_date.replace(month=current_date.month + 1)

        return dates

    async def _get_ev_as_of_date(
        self,
        cost_element_id: UUID,
        as_of: datetime,
        branch: str,
        branch_mode: BranchMode,
    ) -> Decimal:
        """Get Earned Value (EV) as of a specific date.

        Args:
            cost_element_id: Cost element ID
            as_of: Date to get EV for
            branch: Branch name
            branch_mode: Branch isolation mode

        Returns:
            EV value (0 if no progress or error)
        """
        # First, get BAC for this cost element
        bac = await self._get_bac_as_of(cost_element_id, as_of, branch, branch_mode)
        if bac is None:
            return Decimal("0")

        # Get progress and calculate EV
        ev, _, _ = await self._get_ev_as_of(cost_element_id, as_of, bac)
        return ev

    @log_performance("_get_wbe_evm_timeseries")
    async def _get_wbe_evm_timeseries(
        self,
        wbe_id: UUID,
        granularity: EVMTimeSeriesGranularity,
        control_date: datetime,
        branch: str,
        branch_mode: BranchMode,
    ) -> EVMTimeSeriesResponse:
        """Get EVM time-series for a WBE by aggregating child cost elements.

        Args:
            wbe_id: WBE ID
            granularity: Time granularity (day, week, month)
            control_date: Control date for time-travel queries
            branch: Branch name
            branch_mode: Branch isolation mode

        Returns:
            EVMTimeSeriesResponse with aggregated time-series data

        Raises:
            ValueError: If WBE not found
        """
        # Get all cost elements for this WBE
        cost_elements, _ = await self.ce_service.get_cost_elements(
            filters={"wbe_id": wbe_id},
            branch=branch,
            branch_mode=branch_mode,
            as_of=None,  # Get current versions
            skip=0,
            limit=10000,
        )

        if not cost_elements:
            # No cost elements found - return empty time-series
            return EVMTimeSeriesResponse(
                granularity=granularity,
                points=[],
                start_date=control_date,
                end_date=control_date,
                total_points=0,
            )

        # Collect all time-series from child cost elements
        all_timeseries: list[EVMTimeSeriesResponse] = []
        overall_start_date = control_date
        overall_end_date = control_date

        for ce in cost_elements:
            try:
                ce_timeseries = await self.get_evm_timeseries(
                    entity_type=EntityType.COST_ELEMENT,
                    entity_id=ce.cost_element_id,
                    granularity=granularity,
                    control_date=control_date,
                    branch=branch,
                    branch_mode=branch_mode,
                )
                all_timeseries.append(ce_timeseries)

                # Update overall date range
                if ce_timeseries.start_date < overall_start_date:
                    overall_start_date = ce_timeseries.start_date
                if ce_timeseries.end_date > overall_end_date:
                    overall_end_date = ce_timeseries.end_date
            except ValueError:
                # Skip cost elements that fail
                continue

        if not all_timeseries:
            # No valid time-series found
            return EVMTimeSeriesResponse(
                granularity=granularity,
                points=[],
                start_date=control_date,
                end_date=control_date,
                total_points=0,
            )

        # Generate date intervals for the aggregated range
        dates = self._generate_date_intervals(
            start_date=overall_start_date,
            end_date=overall_end_date,
            granularity=granularity,
        )

        # Aggregate time-series points by date
        aggregated_points: list[EVMTimeSeriesPoint] = []
        for date in dates:
            # Sum values from all time-series for this date
            total_pv = Decimal("0")
            total_ev = Decimal("0")
            total_ac = Decimal("0")
            total_forecast = Decimal("0")
            total_actual = Decimal("0")

            for ts in all_timeseries:
                # Find point for this date in the time-series
                for point in ts.points:
                    if point.date.date() == date.date():  # Compare dates without time
                        total_pv += point.pv
                        total_ev += point.ev
                        total_ac += point.ac
                        total_forecast += point.forecast
                        total_actual += point.actual
                        break

            aggregated_point = EVMTimeSeriesPoint(
                date=date,
                pv=total_pv,
                ev=total_ev,
                ac=total_ac,
                forecast=total_forecast,
                actual=total_actual,
            )
            aggregated_points.append(aggregated_point)

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
        """Get EVM time-series for a Project by aggregating child WBEs.

        The date range is from project start to max(project end, control_date).

        Args:
            project_id: Project ID
            granularity: Time granularity (day, week, month)
            control_date: Control date for time-travel queries
            branch: Branch name
            branch_mode: Branch isolation mode

        Returns:
            EVMTimeSeriesResponse with aggregated time-series data

        Raises:
            ValueError: If Project not found
        """
        # Get the project to determine date range
        project = await self.project_service.get_as_of(
            entity_id=project_id,
            as_of=control_date,
            branch=branch,
            branch_mode=branch_mode,
        )

        if project is None:
            # Project not found - return empty time-series
            return EVMTimeSeriesResponse(
                granularity=granularity,
                points=[],
                start_date=control_date,
                end_date=control_date,
                total_points=0,
            )

        # Get all WBEs for this project
        wbes, _ = await self.wbe_service.get_wbes(
            project_id=project_id,
            branch=branch,
            branch_mode=branch_mode,
            as_of=None,  # Get current versions
            skip=0,
            limit=10000,
        )

        if not wbes:
            # No WBEs found - return empty time-series
            return EVMTimeSeriesResponse(
                granularity=granularity,
                points=[],
                start_date=control_date,
                end_date=control_date,
                total_points=0,
            )

        # Determine date range: project start to max(project end, control_date)
        start_date = project.start_date or control_date
        end_date = project.end_date or control_date
        if control_date > end_date:
            end_date = control_date

        # Collect all time-series from child WBEs
        all_timeseries: list[EVMTimeSeriesResponse] = []
        overall_start_date = end_date
        overall_end_date = start_date

        for wbe in wbes:
            try:
                wbe_timeseries = await self.get_evm_timeseries(
                    entity_type=EntityType.WBE,
                    entity_id=wbe.wbe_id,
                    granularity=granularity,
                    control_date=control_date,
                    branch=branch,
                    branch_mode=branch_mode,
                )
                all_timeseries.append(wbe_timeseries)

                # Update overall date range
                if wbe_timeseries.start_date < overall_start_date:
                    overall_start_date = wbe_timeseries.start_date
                if wbe_timeseries.end_date > overall_end_date:
                    overall_end_date = wbe_timeseries.end_date
            except ValueError:
                # Skip WBEs that fail
                continue

        if not all_timeseries:
            # No valid time-series found
            return EVMTimeSeriesResponse(
                granularity=granularity,
                points=[],
                start_date=start_date,
                end_date=end_date,
                total_points=0,
            )

        # Use project date range if it's broader
        if start_date < overall_start_date:
            overall_start_date = start_date
        if end_date > overall_end_date:
            overall_end_date = end_date

        # Generate date intervals for the aggregated range
        dates = self._generate_date_intervals(
            start_date=overall_start_date,
            end_date=overall_end_date,
            granularity=granularity,
        )

        # Aggregate time-series points by date
        aggregated_points: list[EVMTimeSeriesPoint] = []
        for date in dates:
            # Sum values from all time-series for this date
            total_pv = Decimal("0")
            total_ev = Decimal("0")
            total_ac = Decimal("0")
            total_forecast = Decimal("0")
            total_actual = Decimal("0")

            for ts in all_timeseries:
                # Find point for this date in the time-series
                for point in ts.points:
                    if point.date.date() == date.date():  # Compare dates without time
                        total_pv += point.pv
                        total_ev += point.ev
                        total_ac += point.ac
                        total_forecast += point.forecast
                        total_actual += point.actual
                        break

            aggregated_point = EVMTimeSeriesPoint(
                date=date,
                pv=total_pv,
                ev=total_ev,
                ac=total_ac,
                forecast=total_forecast,
                actual=total_actual,
            )
            aggregated_points.append(aggregated_point)

        return EVMTimeSeriesResponse(
            granularity=granularity,
            points=aggregated_points,
            start_date=overall_start_date,
            end_date=overall_end_date,
            total_points=len(aggregated_points),
        )
