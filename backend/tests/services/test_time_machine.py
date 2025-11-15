"""Tests for centralized time-machine helpers."""

from datetime import date

from sqlalchemy import select

from app.models import CostRegistration
from app.services import time_machine


def test_get_visibility_filters_returns_schedule_filters() -> None:
    control_date = date(2024, 2, 15)

    filters = time_machine.get_visibility_filters(
        time_machine.TimeMachineEventType.SCHEDULE, control_date
    )

    assert len(filters) == 2
    registration_filter, created_filter = filters

    assert registration_filter.left.name == "registration_date"
    assert registration_filter.right.value == control_date
    assert created_filter.left.name == "created_at"
    assert created_filter.right.value.day == control_date.day


def test_get_visibility_filters_returns_earned_value_filters() -> None:
    control_date = date(2024, 6, 1)

    filters = time_machine.get_visibility_filters(
        time_machine.TimeMachineEventType.EARNED_VALUE, control_date
    )

    assert len(filters) == 3
    column_names = [f.left.name for f in filters]
    assert column_names == ["completion_date", "registration_date", "created_at"]


def test_apply_time_machine_filters_appends_predicates() -> None:
    control_date = date(2024, 3, 31)
    statement = select(CostRegistration)

    filtered = time_machine.apply_time_machine_filters(
        statement, time_machine.TimeMachineEventType.COST_REGISTRATION, control_date
    )

    assert filtered is not statement
    clause = str(filtered.whereclause)
    assert "registration_date" in clause
    assert "created_at" in clause
