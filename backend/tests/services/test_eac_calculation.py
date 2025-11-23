"""Unit tests for EAC calculation helpers."""

from decimal import Decimal

from app.services.eac_calculation import (
    aggregate_eac,
    aggregate_forecasted_quality,
    calculate_cost_element_eac,
    calculate_forecasted_quality,
)


def test_calculate_cost_element_eac_with_forecast() -> None:
    """Should return forecast EAC when forecast exists."""
    forecast_eac = Decimal("150000.00")
    budget_bac = Decimal("100000.00")

    eac = calculate_cost_element_eac(forecast_eac=forecast_eac, budget_bac=budget_bac)

    assert eac == Decimal("150000.00")


def test_calculate_cost_element_eac_with_bac_fallback() -> None:
    """Should return BAC when no forecast exists."""
    forecast_eac = None
    budget_bac = Decimal("100000.00")

    eac = calculate_cost_element_eac(forecast_eac=forecast_eac, budget_bac=budget_bac)

    assert eac == Decimal("100000.00")


def test_calculate_cost_element_eac_with_no_bac() -> None:
    """Should return 0.00 when no forecast and no BAC."""
    forecast_eac = None
    budget_bac = Decimal("0.00")

    eac = calculate_cost_element_eac(forecast_eac=forecast_eac, budget_bac=budget_bac)

    assert eac == Decimal("0.00")


def test_calculate_cost_element_eac_with_zero_forecast() -> None:
    """Should return 0.00 when forecast EAC is zero."""
    forecast_eac = Decimal("0.00")
    budget_bac = Decimal("100000.00")

    eac = calculate_cost_element_eac(forecast_eac=forecast_eac, budget_bac=budget_bac)

    assert eac == Decimal("0.00")


def test_calculate_forecasted_quality_with_forecast() -> None:
    """Should return 100% (1.0000) when EAC comes from forecast."""
    forecast_eac = Decimal("150000.00")
    calculated_eac = Decimal("150000.00")

    quality = calculate_forecasted_quality(
        forecast_eac=forecast_eac, calculated_eac=calculated_eac
    )

    assert quality == Decimal("1.0000")


def test_calculate_forecasted_quality_with_bac_fallback() -> None:
    """Should return 0% (0.0000) when EAC comes from BAC."""
    forecast_eac = None
    calculated_eac = Decimal("100000.00")

    quality = calculate_forecasted_quality(
        forecast_eac=forecast_eac, calculated_eac=calculated_eac
    )

    assert quality == Decimal("0.0000")


def test_calculate_forecasted_quality_with_zero_eac() -> None:
    """Should return 0.0000 when calculated EAC is zero."""
    forecast_eac = Decimal("150000.00")
    calculated_eac = Decimal("0.00")

    quality = calculate_forecasted_quality(
        forecast_eac=forecast_eac, calculated_eac=calculated_eac
    )

    assert quality == Decimal("0.0000")


def test_calculate_forecasted_quality_with_none_forecast_and_zero_eac() -> None:
    """Should return 0.0000 when no forecast and zero EAC."""
    forecast_eac = None
    calculated_eac = Decimal("0.00")

    quality = calculate_forecasted_quality(
        forecast_eac=forecast_eac, calculated_eac=calculated_eac
    )

    assert quality == Decimal("0.0000")


def test_aggregate_eac_with_multiple_values() -> None:
    """Should sum all EAC values."""
    eac_values = [
        Decimal("100000.00"),
        Decimal("200000.00"),
        Decimal("150000.00"),
    ]

    total_eac = aggregate_eac(eac_values)

    assert total_eac == Decimal("450000.00")


def test_aggregate_eac_with_empty_list() -> None:
    """Should return 0.00 when no EAC values."""
    eac_values: list[Decimal] = []

    total_eac = aggregate_eac(eac_values)

    assert total_eac == Decimal("0.00")


def test_aggregate_eac_with_single_value() -> None:
    """Should return single value when only one EAC."""
    eac_values = [Decimal("100000.00")]

    total_eac = aggregate_eac(eac_values)

    assert total_eac == Decimal("100000.00")


def test_aggregate_forecasted_quality_with_forecasts() -> None:
    """Should calculate percentage of total EAC from forecasts."""
    forecast_eac_sum = Decimal("300000.00")
    total_eac = Decimal("500000.00")

    quality = aggregate_forecasted_quality(
        forecast_eac_sum=forecast_eac_sum, total_eac=total_eac
    )

    # 300000 / 500000 = 0.6000 = 60%
    assert quality == Decimal("0.6000")


def test_aggregate_forecasted_quality_all_from_forecasts() -> None:
    """Should return 100% when all EAC comes from forecasts."""
    forecast_eac_sum = Decimal("500000.00")
    total_eac = Decimal("500000.00")

    quality = aggregate_forecasted_quality(
        forecast_eac_sum=forecast_eac_sum, total_eac=total_eac
    )

    assert quality == Decimal("1.0000")


def test_aggregate_forecasted_quality_all_from_bac() -> None:
    """Should return 0% when no EAC comes from forecasts."""
    forecast_eac_sum = Decimal("0.00")
    total_eac = Decimal("500000.00")

    quality = aggregate_forecasted_quality(
        forecast_eac_sum=forecast_eac_sum, total_eac=total_eac
    )

    assert quality == Decimal("0.0000")


def test_aggregate_forecasted_quality_with_zero_total_eac() -> None:
    """Should return 0.0000 when total EAC is zero."""
    forecast_eac_sum = Decimal("100000.00")
    total_eac = Decimal("0.00")

    quality = aggregate_forecasted_quality(
        forecast_eac_sum=forecast_eac_sum, total_eac=total_eac
    )

    assert quality == Decimal("0.0000")


def test_aggregate_forecasted_quality_partial_forecasts() -> None:
    """Should calculate correct percentage for partial forecasts."""
    # Example: 3 cost elements
    # - CE1: forecast EAC = 100000 (from forecast)
    # - CE2: EAC = 200000 (from BAC, no forecast)
    # - CE3: forecast EAC = 150000 (from forecast)
    # Total forecast EAC = 250000
    # Total EAC = 450000
    # Quality = 250000 / 450000 = 0.5556 = 55.56%
    forecast_eac_sum = Decimal("250000.00")
    total_eac = Decimal("450000.00")

    quality = aggregate_forecasted_quality(
        forecast_eac_sum=forecast_eac_sum, total_eac=total_eac
    )

    assert quality == Decimal("0.5556")
