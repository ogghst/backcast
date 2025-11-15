"""Earned value calculation helpers."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from app.models import CostElement, EarnedValueEntry
from app.services.time_machine import end_of_day

TWO_PLACES = Decimal("0.01")
FOUR_PLACES = Decimal("0.0001")
ONE = Decimal("1.0")
ZERO = Decimal("0.0")


class EarnedValueError(Exception):
    """Raised when attempting to calculate earned value for invalid inputs."""


def _quantize(value: Decimal, exp: Decimal) -> Decimal:
    return value.quantize(exp, rounding=ROUND_HALF_UP)


def _select_latest_entry_for_control_date(
    entries: list[EarnedValueEntry],
    control_date: date,
) -> EarnedValueEntry | None:
    """Select the most recent earned value entry where completion_date <= control_date.

    Args:
        entries: List of earned value entries to search
        control_date: Control date for selection

    Returns:
        Most recent entry where completion_date <= control_date, or None if no such entry exists.
        Tie-breaking: If multiple entries have the same completion_date, selects the one with
        the latest created_at timestamp.
    """
    if not entries:
        return None

    # Filter entries where completion_date <= control_date
    cutoff = end_of_day(control_date)
    valid_entries = [
        entry
        for entry in entries
        if entry.completion_date <= control_date
        and entry.registration_date <= control_date
        and entry.created_at <= cutoff
    ]

    if not valid_entries:
        return None

    # Sort by completion_date DESC, then created_at DESC
    # This ensures we get the most recent entry
    valid_entries.sort(key=lambda e: (e.completion_date, e.created_at), reverse=True)

    return valid_entries[0]


def calculate_earned_percent_complete(
    entry: EarnedValueEntry | None,
) -> Decimal:
    """Calculate the earned percent complete from an earned value entry.

    Args:
        entry: Earned value entry, or None if no entry exists

    Returns:
        Percent complete as Decimal (0.0000 to 1.0000), quantized to 4 decimal places.
        Returns 0.0000 if entry is None.
    """
    if entry is None:
        return _quantize(ZERO, FOUR_PLACES)

    percent_decimal = entry.percent_complete / Decimal("100")
    return _quantize(percent_decimal, FOUR_PLACES)


def calculate_earned_value(
    budget_bac: Decimal,
    percent_complete: Decimal,
) -> Decimal:
    """Calculate earned value as BAC multiplied by percent complete.

    Args:
        budget_bac: Budget at Completion (BAC) for the cost element
        percent_complete: Physical completion percentage (0-100)

    Returns:
        Earned value (EV) as Decimal, quantized to 2 decimal places.
        Formula: EV = BAC × (percent_complete / 100)
    """
    percent_decimal = percent_complete / Decimal("100")
    earned_value = budget_bac * percent_decimal
    return _quantize(earned_value, TWO_PLACES)


def calculate_cost_element_earned_value(
    *,
    cost_element: CostElement,
    entry: EarnedValueEntry | None,
    control_date: date,  # noqa: ARG001
) -> tuple[Decimal, Decimal]:
    """Calculate earned value and percent for a cost element.

    Args:
        cost_element: Cost element to calculate EV for
        entry: Most recent earned value entry for the cost element at control_date, or None
        control_date: Control date for calculation (used for consistency, not in calculation)

    Returns:
        Tuple of (earned_value: Decimal, percent_complete: Decimal).
        Returns (0.00, 0.0000) if entry is None.
    """
    budget_bac = cost_element.budget_bac or Decimal("0.00")
    if entry is None:
        return Decimal("0.00"), Decimal("0.0000")

    percent = calculate_earned_percent_complete(entry)
    earned_value = calculate_earned_value(budget_bac, entry.percent_complete)
    return earned_value, percent


@dataclass(slots=True)
class AggregateResult:
    earned_value: Decimal
    percent_complete: Decimal
    budget_bac: Decimal


def aggregate_earned_value(
    values: Iterable[tuple[Decimal, Decimal]],
) -> AggregateResult:
    """Aggregate earned values over multiple cost elements.

    Args:
        values: Iterable of (earned_value, budget_bac) tuples

    Returns:
        AggregateResult with total earned_value, weighted percent_complete, and total budget_bac.
        If total_bac is 0, returns percent_complete = 0.0000.
    """
    total_bac = Decimal("0.00")
    total_earned_value = Decimal("0.00")

    for earned_value, budget_bac in values:
        total_earned_value += earned_value
        total_bac += budget_bac

    if total_bac == Decimal("0.00"):
        return AggregateResult(
            earned_value=_quantize(total_earned_value, TWO_PLACES),
            percent_complete=Decimal("0.0000"),
            budget_bac=Decimal("0.00"),
        )

    percent_complete = total_earned_value / total_bac
    return AggregateResult(
        earned_value=_quantize(total_earned_value, TWO_PLACES),
        percent_complete=_quantize(percent_complete, FOUR_PLACES),
        budget_bac=_quantize(total_bac, TWO_PLACES),
    )
