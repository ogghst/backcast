"""Unified EVM aggregation service that reuses existing calculation services."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Literal

from app.models import (
    CostElement,
    CostElementSchedule,
    CostRegistration,
    EarnedValueEntry,
)
from app.services.eac_calculation import (
    aggregate_eac,
    aggregate_forecasted_quality,
    calculate_cost_element_eac,
    calculate_forecasted_quality,
)
from app.services.earned_value import calculate_cost_element_earned_value
from app.services.evm_indices import (
    calculate_cost_variance,
    calculate_cpi,
    calculate_schedule_variance,
    calculate_spi,
    calculate_tcpi,
)
from app.services.planned_value import calculate_cost_element_planned_value


@dataclass(slots=True)
class WBEEVMMetrics:
    """EVM metrics for a WBE (aggregated from cost elements)."""

    planned_value: Decimal
    earned_value: Decimal
    actual_cost: Decimal
    budget_bac: Decimal
    eac: Decimal
    forecasted_quality: Decimal
    cpi: Decimal | None
    spi: Decimal | None
    tcpi: Decimal | Literal["overrun"] | None
    cost_variance: Decimal
    schedule_variance: Decimal


@dataclass(slots=True)
class ProjectEVMMetrics:
    """EVM metrics for a project (aggregated from WBEs)."""

    planned_value: Decimal
    earned_value: Decimal
    actual_cost: Decimal
    budget_bac: Decimal
    eac: Decimal
    forecasted_quality: Decimal
    cpi: Decimal | None
    spi: Decimal | None
    tcpi: Decimal | Literal["overrun"] | None
    cost_variance: Decimal
    schedule_variance: Decimal


@dataclass(slots=True)
class CostElementEVMMetrics:
    """EVM metrics for a single cost element."""

    planned_value: Decimal
    earned_value: Decimal
    actual_cost: Decimal
    budget_bac: Decimal
    eac: Decimal
    forecasted_quality: Decimal
    cpi: Decimal | None
    spi: Decimal | None
    tcpi: Decimal | Literal["overrun"] | None
    cost_variance: Decimal
    schedule_variance: Decimal


def get_cost_element_evm_metrics(
    *,
    cost_element: CostElement,
    schedule: CostElementSchedule | None,
    entry: EarnedValueEntry | None,
    cost_registrations: list[CostRegistration],
    control_date: date,
    forecast_eac: Decimal | None = None,
) -> CostElementEVMMetrics:
    """Get all EVM metrics for a single cost element by reusing existing services.

    Args:
        cost_element: Cost element to calculate metrics for
        schedule: Cost element schedule (None if no schedule exists)
        entry: Most recent earned value entry (None if no entry exists)
        cost_registrations: List of cost registrations for this cost element
        control_date: Control date for calculations
        forecast_eac: Forecast EAC value, or None if no forecast exists

    Returns:
        CostElementEVMMetrics with all EVM metrics (PV, EV, AC, BAC, EAC, Forecasted Quality, CPI, SPI, TCPI, CV, SV)
    """
    # Calculate PV using existing service
    pv, _ = calculate_cost_element_planned_value(
        cost_element=cost_element,
        schedule=schedule,
        control_date=control_date,
    )

    # Calculate EV using existing service
    ev, _ = calculate_cost_element_earned_value(
        cost_element=cost_element,
        entry=entry,
        control_date=control_date,
    )

    # Calculate AC from cost registrations
    ac = sum(cr.amount for cr in cost_registrations)

    # Get BAC from cost element
    bac = cost_element.budget_bac or Decimal("0.00")

    # Calculate EAC using forecast or BAC fallback
    eac = calculate_cost_element_eac(forecast_eac=forecast_eac, budget_bac=bac)

    # Calculate forecasted quality
    forecasted_quality = calculate_forecasted_quality(
        forecast_eac=forecast_eac, calculated_eac=eac
    )

    # Calculate indices using existing service functions
    cpi = calculate_cpi(ev, ac)
    spi = calculate_spi(ev, pv)
    tcpi = calculate_tcpi(bac, ev, ac)

    # Calculate variances using existing service functions
    cv = calculate_cost_variance(ev, ac)
    sv = calculate_schedule_variance(ev, pv)

    return CostElementEVMMetrics(
        planned_value=pv,
        earned_value=ev,
        actual_cost=ac,
        budget_bac=bac,
        eac=eac,
        forecasted_quality=forecasted_quality,
        cpi=cpi,
        spi=spi,
        tcpi=tcpi,
        cost_variance=cv,
        schedule_variance=sv,
    )


def aggregate_cost_element_metrics(
    metrics: list[CostElementEVMMetrics],
) -> WBEEVMMetrics | ProjectEVMMetrics:
    """Aggregate EVM metrics from multiple cost elements.

    Args:
        metrics: List of CostElementEVMMetrics to aggregate

    Returns:
        Aggregated metrics (WBEEVMMetrics or ProjectEVMMetrics) with summed PV, EV, AC, BAC
        and calculated indices from aggregated values.
    """
    if not metrics:
        return WBEEVMMetrics(
            planned_value=Decimal("0.00"),
            earned_value=Decimal("0.00"),
            actual_cost=Decimal("0.00"),
            budget_bac=Decimal("0.00"),
            eac=Decimal("0.00"),
            forecasted_quality=Decimal("0.0000"),
            cpi=None,
            spi=None,
            tcpi=None,
            cost_variance=Decimal("0.00"),
            schedule_variance=Decimal("0.00"),
        )

    # Aggregate PV, EV, AC, BAC
    total_pv = sum(m.planned_value for m in metrics)
    total_ev = sum(m.earned_value for m in metrics)
    total_ac = sum(m.actual_cost for m in metrics)
    total_bac = sum(m.budget_bac for m in metrics)

    # Aggregate EAC
    eac_values = [m.eac for m in metrics]
    total_eac = aggregate_eac(eac_values)

    # Calculate forecasted quality
    # Sum of EACs that come from forecasts (where forecasted_quality = 1.0000)
    forecast_eac_sum = sum(
        m.eac for m in metrics if m.forecasted_quality == Decimal("1.0000")
    )
    forecasted_quality = aggregate_forecasted_quality(
        forecast_eac_sum=forecast_eac_sum, total_eac=total_eac
    )

    # Calculate indices from aggregated values
    cpi = calculate_cpi(total_ev, total_ac)
    spi = calculate_spi(total_ev, total_pv)
    tcpi = calculate_tcpi(total_bac, total_ev, total_ac)

    # Calculate variances from aggregated values
    cv = calculate_cost_variance(total_ev, total_ac)
    sv = calculate_schedule_variance(total_ev, total_pv)

    return WBEEVMMetrics(
        planned_value=total_pv,
        earned_value=total_ev,
        actual_cost=total_ac,
        budget_bac=total_bac,
        eac=total_eac,
        forecasted_quality=forecasted_quality,
        cpi=cpi,
        spi=spi,
        tcpi=tcpi,
        cost_variance=cv,
        schedule_variance=sv,
    )
