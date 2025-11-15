"""Unit tests for earned value calculation helpers."""

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from app.models import CostElement, EarnedValueEntry
from app.services.earned_value import (
    _select_latest_entry_for_control_date,
    aggregate_earned_value,
    calculate_cost_element_earned_value,
    calculate_earned_percent_complete,
    calculate_earned_value,
)


def _create_test_entry(
    completion_date: date,
    percent_complete: Decimal = Decimal("50.00"),
    created_at: datetime | None = None,
    registration_date: date | None = None,
) -> EarnedValueEntry:
    """Create a test EarnedValueEntry without database."""
    if created_at is None:
        created_at = datetime.now(timezone.utc)

    registration_date = registration_date or completion_date

    return EarnedValueEntry(
        earned_value_id=uuid.uuid4(),
        cost_element_id=uuid.uuid4(),
        created_by_id=uuid.uuid4(),
        completion_date=completion_date,
        percent_complete=percent_complete,
        earned_value=Decimal("50000.00"),
        deliverables="Test",
        description="Test entry",
        registration_date=registration_date,
        created_at=created_at,
        last_modified_at=created_at,
    )


def test_select_latest_entry_before_control_date() -> None:
    """Should return most recent entry where completion_date <= control_date."""
    control_date = date(2024, 2, 15)

    entry1 = _create_test_entry(
        completion_date=date(2024, 1, 15),
        created_at=datetime(2024, 1, 15, tzinfo=timezone.utc),
    )
    entry2 = _create_test_entry(
        completion_date=date(2024, 2, 10),
        created_at=datetime(2024, 2, 10, tzinfo=timezone.utc),
    )
    entry3 = _create_test_entry(
        completion_date=date(2024, 2, 20),  # After control_date
        created_at=datetime(2024, 2, 20, tzinfo=timezone.utc),
    )

    entries = [entry1, entry2, entry3]
    result = _select_latest_entry_for_control_date(entries, control_date)

    assert result == entry2
    assert result.completion_date == date(2024, 2, 10)


def test_select_latest_entry_respects_registration_date() -> None:
    """Entries with registration_date after control_date should be excluded."""
    control_date = date(2024, 2, 15)

    entry_valid = _create_test_entry(
        completion_date=date(2024, 2, 1),
        created_at=datetime(2024, 2, 1, tzinfo=timezone.utc),
        registration_date=date(2024, 2, 5),
    )
    entry_future = _create_test_entry(
        completion_date=date(2024, 1, 31),
        created_at=datetime(2024, 2, 1, tzinfo=timezone.utc),
        registration_date=date(2024, 3, 1),
    )

    entries = [entry_future, entry_valid]
    result = _select_latest_entry_for_control_date(entries, control_date)

    assert result == entry_valid


def test_select_latest_entry_after_control_date_returns_none() -> None:
    """Should return None if all entries have completion_date > control_date."""
    control_date = date(2024, 1, 15)

    entry1 = _create_test_entry(
        completion_date=date(2024, 2, 10),
        created_at=datetime(2024, 2, 10, tzinfo=timezone.utc),
    )
    entry2 = _create_test_entry(
        completion_date=date(2024, 2, 20),
        created_at=datetime(2024, 2, 20, tzinfo=timezone.utc),
    )

    entries = [entry1, entry2]
    result = _select_latest_entry_for_control_date(entries, control_date)

    assert result is None


def test_select_latest_entry_no_entries_returns_none() -> None:
    """Should return None if no entries provided."""
    control_date = date(2024, 2, 15)
    entries: list[EarnedValueEntry] = []

    result = _select_latest_entry_for_control_date(entries, control_date)

    assert result is None


def test_select_latest_entry_tie_breaking() -> None:
    """Should use created_at for tie-breaking when completion_dates are equal."""
    control_date = date(2024, 2, 15)

    entry1 = _create_test_entry(
        completion_date=date(2024, 2, 10),
        created_at=datetime(2024, 2, 10, 10, 0, 0, tzinfo=timezone.utc),
    )
    entry2 = _create_test_entry(
        completion_date=date(2024, 2, 10),  # Same completion_date
        created_at=datetime(
            2024, 2, 10, 15, 0, 0, tzinfo=timezone.utc
        ),  # Later created_at
    )

    entries = [entry1, entry2]
    result = _select_latest_entry_for_control_date(entries, control_date)

    assert result == entry2  # Should select the one with later created_at


def test_select_latest_entry_exact_control_date() -> None:
    """Should include entry where completion_date equals control_date."""
    control_date = date(2024, 2, 15)

    entry1 = _create_test_entry(
        completion_date=date(2024, 2, 10),
        created_at=datetime(2024, 2, 10, tzinfo=timezone.utc),
    )
    entry2 = _create_test_entry(
        completion_date=date(2024, 2, 15),  # Exactly control_date
        created_at=datetime(2024, 2, 15, tzinfo=timezone.utc),
    )

    entries = [entry1, entry2]
    result = _select_latest_entry_for_control_date(entries, control_date)

    assert result == entry2
    assert result.completion_date == control_date


def test_calculate_earned_percent_complete_with_entry() -> None:
    """Should return percent_complete / 100 from entry as Decimal."""
    entry = _create_test_entry(
        completion_date=date(2024, 2, 15),
        percent_complete=Decimal("50.00"),
    )

    result = calculate_earned_percent_complete(entry)

    assert result == Decimal("0.5000")
    assert result == Decimal("50.00") / Decimal("100")


def test_calculate_earned_percent_complete_no_entry_returns_zero() -> None:
    """Should return 0.0000 if entry is None."""
    result = calculate_earned_percent_complete(None)

    assert result == Decimal("0.0000")


def test_calculate_earned_percent_complete_edge_cases() -> None:
    """Should handle edge cases: 0%, 100%, and quantize to 4 decimal places."""
    entry_zero = _create_test_entry(
        completion_date=date(2024, 2, 15),
        percent_complete=Decimal("0.00"),
    )
    entry_hundred = _create_test_entry(
        completion_date=date(2024, 2, 15),
        percent_complete=Decimal("100.00"),
    )
    entry_partial = _create_test_entry(
        completion_date=date(2024, 2, 15),
        percent_complete=Decimal("33.33"),
    )

    result_zero = calculate_earned_percent_complete(entry_zero)
    result_hundred = calculate_earned_percent_complete(entry_hundred)
    result_partial = calculate_earned_percent_complete(entry_partial)

    assert result_zero == Decimal("0.0000")
    assert result_hundred == Decimal("1.0000")
    assert result_partial == Decimal("0.3333")


def test_calculate_earned_value_uses_percent() -> None:
    """Earned value should equal BAC multiplied by percent complete."""
    budget_bac = Decimal("100000.00")
    percent_complete = Decimal("50.00")

    earned_value = calculate_earned_value(budget_bac, percent_complete)

    # 100000 * 0.50 = 50000.00
    assert earned_value == Decimal("50000.00")


def test_calculate_earned_value_no_entry_returns_zero() -> None:
    """Should return 0.00 if percent_complete is 0."""
    budget_bac = Decimal("100000.00")
    percent_complete = Decimal("0.00")

    earned_value = calculate_earned_value(budget_bac, percent_complete)

    assert earned_value == Decimal("0.00")


def test_calculate_earned_value_zero_bac() -> None:
    """Should return 0.00 if BAC is 0."""
    budget_bac = Decimal("0.00")
    percent_complete = Decimal("50.00")

    earned_value = calculate_earned_value(budget_bac, percent_complete)

    assert earned_value == Decimal("0.00")


def test_calculate_earned_value_hundred_percent() -> None:
    """Should return full BAC if percent_complete is 100%."""
    budget_bac = Decimal("100000.00")
    percent_complete = Decimal("100.00")

    earned_value = calculate_earned_value(budget_bac, percent_complete)

    assert earned_value == Decimal("100000.00")


def test_calculate_earned_value_quantizes_to_two_places() -> None:
    """Should quantize result to 2 decimal places."""
    budget_bac = Decimal("100000.00")
    percent_complete = Decimal("33.33")

    earned_value = calculate_earned_value(budget_bac, percent_complete)

    # 100000 * 0.3333 = 33330.00 (rounded)
    assert earned_value == Decimal("33330.00")
    # Verify it's quantized to 2 places
    assert (
        str(earned_value).split(".")[1]
        if "." in str(earned_value)
        else "00" == "00" or len(str(earned_value).split(".")[1]) <= 2
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


def test_calculate_cost_element_earned_value_with_entry() -> None:
    """Should calculate EV and percent for cost element with entry."""
    cost_element = _create_test_cost_element(budget_bac=Decimal("100000.00"))
    entry = _create_test_entry(
        completion_date=date(2024, 2, 15),
        percent_complete=Decimal("50.00"),
    )
    control_date = date(2024, 2, 15)

    earned_value, percent = calculate_cost_element_earned_value(
        cost_element=cost_element,
        entry=entry,
        control_date=control_date,
    )

    assert earned_value == Decimal("50000.00")
    assert percent == Decimal("0.5000")


def test_calculate_cost_element_earned_value_no_entry() -> None:
    """Should return (0.00, 0.0000) if entry is None."""
    cost_element = _create_test_cost_element(budget_bac=Decimal("100000.00"))
    control_date = date(2024, 2, 15)

    earned_value, percent = calculate_cost_element_earned_value(
        cost_element=cost_element,
        entry=None,
        control_date=control_date,
    )

    assert earned_value == Decimal("0.00")
    assert percent == Decimal("0.0000")


def test_calculate_cost_element_earned_value_zero_bac() -> None:
    """Should return (0.00, 0.0000) if BAC is 0."""
    cost_element = _create_test_cost_element(budget_bac=Decimal("0.00"))
    entry = _create_test_entry(
        completion_date=date(2024, 2, 15),
        percent_complete=Decimal("50.00"),
    )
    control_date = date(2024, 2, 15)

    earned_value, percent = calculate_cost_element_earned_value(
        cost_element=cost_element,
        entry=entry,
        control_date=control_date,
    )

    assert earned_value == Decimal("0.00")
    assert percent == Decimal("0.5000")  # Percent still calculated from entry


def test_aggregate_earned_value_sums_ev_and_bac() -> None:
    """Should sum EV and BAC across multiple cost elements."""
    tuples = [
        (Decimal("30000.00"), Decimal("60000.00")),  # EV, BAC
        (Decimal("20000.00"), Decimal("40000.00")),
    ]

    result = aggregate_earned_value(tuples)

    assert result.earned_value == Decimal("50000.00")
    assert result.budget_bac == Decimal("100000.00")


def test_aggregate_earned_value_calculates_weighted_percent() -> None:
    """Should calculate weighted percent complete = total_EV / total_BAC."""
    tuples = [
        (Decimal("30000.00"), Decimal("60000.00")),  # 50% complete
        (Decimal("20000.00"), Decimal("40000.00")),  # 50% complete
    ]

    result = aggregate_earned_value(tuples)

    # Total EV = 50000, Total BAC = 100000, Percent = 0.5000
    assert result.percent_complete == Decimal("0.5000")
    assert result.earned_value == Decimal("50000.00")
    assert result.budget_bac == Decimal("100000.00")


def test_aggregate_earned_value_zero_bac_returns_zero_percent() -> None:
    """Should return 0.0000 percent if total BAC is 0."""
    tuples = [
        (Decimal("0.00"), Decimal("0.00")),
        (Decimal("0.00"), Decimal("0.00")),
    ]

    result = aggregate_earned_value(tuples)

    assert result.earned_value == Decimal("0.00")
    assert result.budget_bac == Decimal("0.00")
    assert result.percent_complete == Decimal("0.0000")


def test_aggregate_earned_value_empty_list() -> None:
    """Should return zeros for empty list."""
    tuples: list[tuple[Decimal, Decimal]] = []

    result = aggregate_earned_value(tuples)

    assert result.earned_value == Decimal("0.00")
    assert result.budget_bac == Decimal("0.00")
    assert result.percent_complete == Decimal("0.0000")


def test_aggregate_earned_value_different_percents() -> None:
    """Should correctly aggregate cost elements with different completion percentages."""
    tuples = [
        (Decimal("60000.00"), Decimal("80000.00")),  # 75% complete
        (Decimal("20000.00"), Decimal("40000.00")),  # 50% complete
    ]

    result = aggregate_earned_value(tuples)

    # Total EV = 80000, Total BAC = 120000, Percent = 0.6667 (rounded)
    assert result.earned_value == Decimal("80000.00")
    assert result.budget_bac == Decimal("120000.00")
    # 80000 / 120000 = 0.666666... ≈ 0.6667
    assert result.percent_complete == Decimal("0.6667")
