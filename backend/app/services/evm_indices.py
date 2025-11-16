"""EVM performance indices calculation helpers."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal

TWO_PLACES = Decimal("0.01")
FOUR_PLACES = Decimal("0.0001")
ONE = Decimal("1.0")
ZERO = Decimal("0.0")


class EVMIndicesError(Exception):
    """Raised when attempting to calculate EVM indices for invalid inputs."""


def _quantize(value: Decimal, exp: Decimal) -> Decimal:
    return value.quantize(exp, rounding=ROUND_HALF_UP)


def calculate_cost_variance(ev: Decimal, ac: Decimal) -> Decimal:
    """Calculate Cost Variance (CV) = EV - AC.

    Args:
        ev: Earned Value
        ac: Actual Cost

    Returns:
        CV as Decimal quantized to 2 decimal places.
        CV is always defined (no None case).
        Negative CV = over-budget, positive CV = under-budget, zero CV = on-budget.

    Business Rules:
        - CV = EV - AC (always defined)
        - CV < 0 indicates over-budget (costs exceed earned value)
        - CV > 0 indicates under-budget (earned value exceeds costs)
        - CV = 0 indicates on-budget (earned value equals costs)
    """
    cv = ev - ac
    return _quantize(cv, TWO_PLACES)


def calculate_schedule_variance(ev: Decimal, pv: Decimal) -> Decimal:
    """Calculate Schedule Variance (SV) = EV - PV.

    Args:
        ev: Earned Value
        pv: Planned Value

    Returns:
        SV as Decimal quantized to 2 decimal places.
        SV is always defined (no None case).
        Negative SV = behind-schedule, positive SV = ahead-of-schedule, zero SV = on-schedule.

    Business Rules:
        - SV = EV - PV (always defined)
        - SV < 0 indicates behind-schedule (earned value less than planned)
        - SV > 0 indicates ahead-of-schedule (earned value greater than planned)
        - SV = 0 indicates on-schedule (earned value equals planned)
    """
    sv = ev - pv
    return _quantize(sv, TWO_PLACES)


def calculate_cpi(ev: Decimal, ac: Decimal) -> Decimal | None:
    """Calculate Cost Performance Index (CPI) = EV / AC.

    Args:
        ev: Earned Value
        ac: Actual Cost

    Returns:
        CPI as Decimal quantized to 4 decimal places, or None if undefined.
        CPI is undefined when AC = 0 (regardless of EV value per business rule).

    Business Rules:
        - CPI = EV / AC when AC > 0
        - CPI = None when AC = 0 (undefined case)
    """
    if ac == ZERO:
        return None

    cpi = ev / ac
    return _quantize(cpi, FOUR_PLACES)


def calculate_spi(ev: Decimal, pv: Decimal) -> Decimal | None:
    """Calculate Schedule Performance Index (SPI) = EV / PV.

    Args:
        ev: Earned Value
        pv: Planned Value

    Returns:
        SPI as Decimal quantized to 4 decimal places, or None if undefined.
        SPI is undefined when PV = 0 (per business rule).

    Business Rules:
        - SPI = EV / PV when PV > 0
        - SPI = None when PV = 0 (null case)
    """
    if pv == ZERO:
        return None

    spi = ev / pv
    return _quantize(spi, FOUR_PLACES)


def calculate_tcpi(
    bac: Decimal, ev: Decimal, ac: Decimal
) -> Decimal | Literal["overrun"] | None:
    """Calculate To-Complete Performance Index (TCPI) = (BAC - EV) / (BAC - AC).

    Args:
        bac: Budget at Completion
        ev: Earned Value
        ac: Actual Cost

    Returns:
        TCPI as Decimal quantized to 4 decimal places, 'overrun' string literal,
        or None if undefined.
        TCPI returns 'overrun' when BAC ≤ AC (per business rule).
        TCPI is undefined when BAC = AC = 0.

    Business Rules:
        - TCPI = (BAC - EV) / (BAC - AC) when BAC > AC
        - TCPI = 'overrun' when BAC ≤ AC (overrun case)
        - TCPI = None when BAC = AC = 0 (undefined case)
    """
    if bac == ZERO and ac == ZERO:
        return None

    if bac <= ac:
        return "overrun"

    numerator = bac - ev
    denominator = bac - ac

    if denominator == ZERO:
        # This shouldn't happen if BAC > AC, but handle it gracefully
        return None

    tcpi = numerator / denominator
    return _quantize(tcpi, FOUR_PLACES)


@dataclass(slots=True)
class AggregateResult:
    """Result of aggregating EVM inputs across multiple cost elements."""

    planned_value: Decimal
    earned_value: Decimal
    actual_cost: Decimal
    budget_bac: Decimal


def aggregate_evm_indices(
    values: Iterable[tuple[Decimal, Decimal, Decimal, Decimal]],
) -> AggregateResult:
    """Aggregate PV, EV, AC, and BAC over multiple cost elements.

    Args:
        values: Iterable of (planned_value, earned_value, actual_cost, budget_bac) tuples

    Returns:
        AggregateResult with total PV, EV, AC, and BAC.
        All values are quantized to 2 decimal places.
    """
    total_pv = Decimal("0.00")
    total_ev = Decimal("0.00")
    total_ac = Decimal("0.00")
    total_bac = Decimal("0.00")

    for pv, ev, ac, bac in values:
        total_pv += pv
        total_ev += ev
        total_ac += ac
        total_bac += bac

    return AggregateResult(
        planned_value=_quantize(total_pv, TWO_PLACES),
        earned_value=_quantize(total_ev, TWO_PLACES),
        actual_cost=_quantize(total_ac, TWO_PLACES),
        budget_bac=_quantize(total_bac, TWO_PLACES),
    )
