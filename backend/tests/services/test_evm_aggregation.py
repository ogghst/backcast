"""Unit tests for unified EVM aggregation service."""

from datetime import date
from decimal import Decimal

from app.models import (
    CostElement,
    CostElementSchedule,
    CostRegistration,
    EarnedValueEntry,
)
from app.services.evm_aggregation import (
    aggregate_cost_element_metrics,
    get_cost_element_evm_metrics,
)


def _create_test_cost_element(
    budget_bac: Decimal = Decimal("100000.00"),
) -> CostElement:
    """Create a test CostElement without database."""
    import uuid

    return CostElement(
        cost_element_id=uuid.uuid4(),
        wbe_id=uuid.uuid4(),
        cost_element_type_id=uuid.uuid4(),
        department_code="ENG",
        department_name="Engineering",
        budget_bac=budget_bac,
        revenue_plan=Decimal("120000.00"),
        status="active",
    )


def _create_test_schedule(
    start_date: date = date(2024, 1, 1),
    end_date: date = date(2024, 12, 31),
    progression_type: str = "linear",
) -> CostElementSchedule:
    """Create a test CostElementSchedule without database."""
    import uuid

    return CostElementSchedule(
        schedule_id=uuid.uuid4(),
        cost_element_id=uuid.uuid4(),
        start_date=start_date,
        end_date=end_date,
        progression_type=progression_type,
        registration_date=start_date,
        created_by_id=uuid.uuid4(),
    )


def _create_test_entry(
    completion_date: date = date(2024, 6, 15),
    percent_complete: Decimal = Decimal("50.00"),
) -> EarnedValueEntry:
    """Create a test EarnedValueEntry without database."""
    import uuid

    return EarnedValueEntry(
        entry_id=uuid.uuid4(),
        cost_element_id=uuid.uuid4(),
        completion_date=completion_date,
        registration_date=completion_date,
        percent_complete=percent_complete,
        notes="Test entry",
        created_by_id=uuid.uuid4(),
    )


def _create_test_cost_registrations(
    amounts: list[Decimal],
) -> list[CostRegistration]:
    """Create test CostRegistration objects without database."""
    import uuid

    registrations = []
    for amount in amounts:
        registrations.append(
            CostRegistration(
                registration_id=uuid.uuid4(),
                cost_element_id=uuid.uuid4(),
                registration_date=date(2024, 6, 1),
                amount=amount,
                cost_category="labor",
                is_quality_cost=False,
                created_by_id=uuid.uuid4(),
            )
        )
    return registrations


def test_get_cost_element_evm_metrics_normal_case() -> None:
    """Should calculate all EVM metrics correctly for normal case."""
    cost_element = _create_test_cost_element(budget_bac=Decimal("100000.00"))
    schedule = _create_test_schedule(
        start_date=date(2024, 1, 1),
        end_date=date(2024, 12, 31),
        progression_type="linear",
    )
    entry = _create_test_entry(
        completion_date=date(2024, 6, 15),
        percent_complete=Decimal("50.00"),
    )
    cost_registrations = _create_test_cost_registrations(
        [Decimal("40000.00"), Decimal("10000.00")]
    )  # Total AC = 50000.00
    control_date = date(2024, 6, 15)

    # Expected values:
    # PV = 100000 * (165 days / 365 days) = ~45205.48 (linear progression at midpoint)
    # EV = 100000 * 0.50 = 50000.00
    # AC = 50000.00
    # BAC = 100000.00
    # CPI = EV/AC = 50000/50000 = 1.0000
    # SPI = EV/PV = 50000/45205.48 ≈ 1.1060
    # TCPI = (BAC-EV)/(BAC-AC) = (100000-50000)/(100000-50000) = 1.0000
    # CV = EV - AC = 50000 - 50000 = 0.00
    # SV = EV - PV = 50000 - 45205.48 ≈ 4794.52

    result = get_cost_element_evm_metrics(
        cost_element=cost_element,
        schedule=schedule,
        entry=entry,
        cost_registrations=cost_registrations,
        control_date=control_date,
    )

    assert result.planned_value > Decimal("45000.00")  # Approximate PV
    assert result.planned_value < Decimal("46000.00")
    assert result.earned_value == Decimal("50000.00")
    assert result.actual_cost == Decimal("50000.00")
    assert result.budget_bac == Decimal("100000.00")
    assert result.cpi == Decimal("1.0000")
    assert result.spi is not None
    assert result.spi > Decimal("1.09")  # Approximate SPI (actual: 1.0994)
    assert result.spi < Decimal("1.11")
    assert result.tcpi == Decimal("1.0000")
    assert result.cost_variance == Decimal("0.00")
    assert result.schedule_variance > Decimal(
        "4500.00"
    )  # Approximate SV (actual: 4520.00)
    assert result.schedule_variance < Decimal("4600.00")


def test_get_cost_element_evm_metrics_no_schedule() -> None:
    """Should handle None schedule correctly (PV = 0)."""
    cost_element = _create_test_cost_element(budget_bac=Decimal("100000.00"))
    entry = _create_test_entry(percent_complete=Decimal("50.00"))
    cost_registrations = _create_test_cost_registrations([Decimal("50000.00")])
    control_date = date(2024, 6, 15)

    result = get_cost_element_evm_metrics(
        cost_element=cost_element,
        schedule=None,
        entry=entry,
        cost_registrations=cost_registrations,
        control_date=control_date,
    )

    assert result.planned_value == Decimal("0.00")
    assert result.earned_value == Decimal("50000.00")
    assert result.actual_cost == Decimal("50000.00")
    assert result.budget_bac == Decimal("100000.00")
    assert result.cpi == Decimal("1.0000")
    assert result.spi is None  # SPI is None when PV = 0
    assert result.tcpi == Decimal("1.0000")
    assert result.cost_variance == Decimal("0.00")
    assert result.schedule_variance == Decimal("50000.00")  # EV - 0


def test_get_cost_element_evm_metrics_no_entry() -> None:
    """Should handle None entry correctly (EV = 0)."""
    cost_element = _create_test_cost_element(budget_bac=Decimal("100000.00"))
    schedule = _create_test_schedule()
    cost_registrations = _create_test_cost_registrations([Decimal("30000.00")])
    control_date = date(2024, 6, 15)

    result = get_cost_element_evm_metrics(
        cost_element=cost_element,
        schedule=schedule,
        entry=None,
        cost_registrations=cost_registrations,
        control_date=control_date,
    )

    assert result.planned_value > Decimal("45000.00")  # PV calculated
    assert result.earned_value == Decimal("0.00")
    assert result.actual_cost == Decimal("30000.00")
    assert result.budget_bac == Decimal("100000.00")
    # CPI = EV/AC = 0/30000 = 0.0000 (CPI is None only when AC = 0)
    assert result.cpi == Decimal("0.0000")
    assert result.spi == Decimal("0.0000")  # EV/PV = 0/PV = 0
    assert result.tcpi == Decimal(
        "1.4286"
    )  # (100000-0)/(100000-30000) = 100000/70000 ≈ 1.4286
    assert result.cost_variance == Decimal("-30000.00")  # 0 - 30000
    assert result.schedule_variance < Decimal("0.00")  # Negative (behind schedule)


def test_get_cost_element_evm_metrics_no_cost_registrations() -> None:
    """Should handle empty cost registrations correctly (AC = 0)."""
    cost_element = _create_test_cost_element(budget_bac=Decimal("100000.00"))
    schedule = _create_test_schedule()
    entry = _create_test_entry(percent_complete=Decimal("50.00"))
    control_date = date(2024, 6, 15)

    result = get_cost_element_evm_metrics(
        cost_element=cost_element,
        schedule=schedule,
        entry=entry,
        cost_registrations=[],
        control_date=control_date,
    )

    assert result.planned_value > Decimal("45000.00")
    assert result.earned_value == Decimal("50000.00")
    assert result.actual_cost == Decimal("0.00")
    assert result.budget_bac == Decimal("100000.00")
    assert result.cpi is None  # CPI is None when AC = 0
    assert result.spi is not None
    assert result.tcpi == Decimal(
        "0.5000"
    )  # (100000-50000)/(100000-0) = 50000/100000 = 0.5
    assert result.cost_variance == Decimal("50000.00")  # 50000 - 0
    assert result.schedule_variance > Decimal(
        "4500.00"
    )  # Approximate SV (actual: 4520.00)
    assert result.schedule_variance < Decimal("4600.00")


def test_get_cost_element_evm_metrics_tcpi_overrun() -> None:
    """Should return 'overrun' for TCPI when BAC ≤ AC."""
    cost_element = _create_test_cost_element(budget_bac=Decimal("100000.00"))
    schedule = _create_test_schedule()
    entry = _create_test_entry(percent_complete=Decimal("50.00"))
    cost_registrations = _create_test_cost_registrations(
        [Decimal("100000.00"), Decimal("10000.00")]
    )  # AC = 110000 > BAC
    control_date = date(2024, 6, 15)

    result = get_cost_element_evm_metrics(
        cost_element=cost_element,
        schedule=schedule,
        entry=entry,
        cost_registrations=cost_registrations,
        control_date=control_date,
    )

    assert result.actual_cost == Decimal("110000.00")
    assert result.budget_bac == Decimal("100000.00")
    assert result.tcpi == "overrun"  # BAC ≤ AC


def test_get_cost_element_evm_metrics_all_none() -> None:
    """Should handle all None/empty inputs correctly."""
    cost_element = _create_test_cost_element(budget_bac=Decimal("100000.00"))
    control_date = date(2024, 6, 15)

    result = get_cost_element_evm_metrics(
        cost_element=cost_element,
        schedule=None,
        entry=None,
        cost_registrations=[],
        control_date=control_date,
    )

    assert result.planned_value == Decimal("0.00")
    assert result.earned_value == Decimal("0.00")
    assert result.actual_cost == Decimal("0.00")
    assert result.budget_bac == Decimal("100000.00")
    assert result.cpi is None
    assert result.spi is None
    # TCPI = (BAC-EV)/(BAC-AC) = (100000-0)/(100000-0) = 100000/100000 = 1.0000
    # TCPI = None only when BAC = 0 and AC = 0
    assert result.tcpi == Decimal("1.0000")
    assert result.cost_variance == Decimal("0.00")
    assert result.schedule_variance == Decimal("0.00")


def test_aggregate_cost_element_metrics_multiple_elements() -> None:
    """Should aggregate metrics from multiple cost elements correctly."""
    # Create metrics for two cost elements
    ce1_metrics = get_cost_element_evm_metrics(
        cost_element=_create_test_cost_element(budget_bac=Decimal("100000.00")),
        schedule=_create_test_schedule(),
        entry=_create_test_entry(percent_complete=Decimal("50.00")),
        cost_registrations=_create_test_cost_registrations([Decimal("50000.00")]),
        control_date=date(2024, 6, 15),
    )

    ce2_metrics = get_cost_element_evm_metrics(
        cost_element=_create_test_cost_element(budget_bac=Decimal("80000.00")),
        schedule=_create_test_schedule(),
        entry=_create_test_entry(percent_complete=Decimal("40.00")),
        cost_registrations=_create_test_cost_registrations([Decimal("35000.00")]),
        control_date=date(2024, 6, 15),
    )

    aggregated = aggregate_cost_element_metrics([ce1_metrics, ce2_metrics])

    # Expected aggregated values:
    # PV = ce1_pv + ce2_pv (both ~40932, so ~81864)
    # EV = 50000 + 32000 = 82000 (50% of 100000 + 40% of 80000)
    # AC = 50000 + 35000 = 85000
    # BAC = 100000 + 80000 = 180000
    # CPI = 82000/85000 ≈ 0.9647
    # SPI = 82000/81864 ≈ 1.0017 (ahead of schedule)
    # TCPI = (180000-82000)/(180000-85000) = 98000/95000 ≈ 1.0316
    # CV = 82000 - 85000 = -3000
    # SV = 82000 - 81864 = 136 (ahead of schedule)

    assert aggregated.planned_value > Decimal("81000.00")
    assert aggregated.planned_value < Decimal("83000.00")
    assert aggregated.earned_value == Decimal("82000.00")
    assert aggregated.actual_cost == Decimal("85000.00")
    assert aggregated.budget_bac == Decimal("180000.00")
    assert aggregated.cpi is not None
    assert aggregated.cpi < Decimal("1.00")  # Under-performing (cost-wise)
    assert aggregated.spi is not None
    assert aggregated.spi > Decimal("1.00")  # Ahead of schedule
    assert aggregated.tcpi is not None
    assert aggregated.cost_variance == Decimal("-3000.00")
    assert aggregated.schedule_variance > Decimal("0.00")  # Ahead of schedule


def test_aggregate_cost_element_metrics_empty() -> None:
    """Should return zeros when aggregating empty list."""
    aggregated = aggregate_cost_element_metrics([])

    assert aggregated.planned_value == Decimal("0.00")
    assert aggregated.earned_value == Decimal("0.00")
    assert aggregated.actual_cost == Decimal("0.00")
    assert aggregated.budget_bac == Decimal("0.00")
    assert aggregated.cpi is None
    assert aggregated.spi is None
    assert aggregated.tcpi is None
    assert aggregated.cost_variance == Decimal("0.00")
    assert aggregated.schedule_variance == Decimal("0.00")


def test_aggregate_cost_element_metrics_single_element() -> None:
    """Should return same values when aggregating single element."""
    ce_metrics = get_cost_element_evm_metrics(
        cost_element=_create_test_cost_element(budget_bac=Decimal("100000.00")),
        schedule=_create_test_schedule(),
        entry=_create_test_entry(percent_complete=Decimal("50.00")),
        cost_registrations=_create_test_cost_registrations([Decimal("50000.00")]),
        control_date=date(2024, 6, 15),
    )

    aggregated = aggregate_cost_element_metrics([ce_metrics])

    assert aggregated.planned_value == ce_metrics.planned_value
    assert aggregated.earned_value == ce_metrics.earned_value
    assert aggregated.actual_cost == ce_metrics.actual_cost
    assert aggregated.budget_bac == ce_metrics.budget_bac
    assert aggregated.cpi == ce_metrics.cpi
    assert aggregated.spi == ce_metrics.spi
    assert aggregated.tcpi == ce_metrics.tcpi
    assert aggregated.cost_variance == ce_metrics.cost_variance
    assert aggregated.schedule_variance == ce_metrics.schedule_variance
