"""EVM (Earned Value Management) Service - orchestrates EVM metrics calculation."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.versioning.enums import BranchMode
from app.models.schemas.evm import EVMMetricsRead
from app.services.cost_element_service import CostElementService
from app.services.cost_registration_service import CostRegistrationService
from app.services.forecast_service import ForecastService
from app.services.progress_entry_service import ProgressEntryService
from app.services.schedule_baseline_service import ScheduleBaselineService


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
