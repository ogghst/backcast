"""EAC calculation helpers with forecast/BAC fallback."""

from __future__ import annotations

from collections.abc import Iterable
from decimal import ROUND_HALF_UP, Decimal

TWO_PLACES = Decimal("0.01")
FOUR_PLACES = Decimal("0.0001")
ZERO = Decimal("0.0")


def _quantize(value: Decimal, exp: Decimal) -> Decimal:
    """Quantize Decimal value to specified precision."""
    return value.quantize(exp, rounding=ROUND_HALF_UP)


def calculate_cost_element_eac(
    forecast_eac: Decimal | None, budget_bac: Decimal
) -> Decimal:
    """Calculate EAC for a cost element using forecast or BAC fallback.

    Args:
        forecast_eac: Forecast EAC value, or None if no forecast exists
        budget_bac: Budget at Completion (BAC) for fallback

    Returns:
        EAC value: forecast_eac if available, otherwise budget_bac.
        Returns Decimal("0.00") if both are None/zero.
    """
    if forecast_eac is not None:
        return _quantize(forecast_eac, TWO_PLACES)

    if budget_bac is not None and budget_bac > ZERO:
        return _quantize(budget_bac, TWO_PLACES)

    return Decimal("0.00")


def calculate_forecasted_quality(
    forecast_eac: Decimal | None, calculated_eac: Decimal
) -> Decimal:
    """Calculate forecasted quality percentage for a cost element.

    Args:
        forecast_eac: Forecast EAC value, or None if no forecast exists
        calculated_eac: The calculated EAC value (from forecast or BAC)

    Returns:
        Decimal between 0.0000 and 1.0000:
        - 1.0000 (100%) if EAC comes from forecast
        - 0.0000 (0%) if EAC comes from BAC fallback
        - 0.0000 if calculated_eac is zero
    """
    if calculated_eac == ZERO:
        return Decimal("0.0000")

    if forecast_eac is not None:
        return Decimal("1.0000")

    return Decimal("0.0000")


def aggregate_eac(eac_values: Iterable[Decimal]) -> Decimal:
    """Aggregate EAC values from multiple cost elements.

    Args:
        eac_values: Iterable of EAC values to sum

    Returns:
        Sum of all EAC values, quantized to 2 decimal places.
        Returns Decimal("0.00") if empty.
    """
    total = sum(eac_values, start=Decimal("0.00"))
    return _quantize(total, TWO_PLACES)


def aggregate_forecasted_quality(
    forecast_eac_sum: Decimal, total_eac: Decimal
) -> Decimal:
    """Calculate aggregate forecasted quality percentage.

    Args:
        forecast_eac_sum: Sum of EAC values that come from forecasts
        total_eac: Total EAC (sum of all EACs, including BAC fallbacks)

    Returns:
        Decimal between 0.0000 and 1.0000 representing the percentage of
        total EAC that comes from forecasts.
        Returns Decimal("0.0000") if total_eac is zero.
    """
    if total_eac == ZERO:
        return Decimal("0.0000")

    quality = forecast_eac_sum / total_eac
    return _quantize(quality, FOUR_PLACES)
