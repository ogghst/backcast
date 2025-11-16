"""Shared helpers for time-machine aware filtering."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime, time, timezone
from enum import Enum

from sqlalchemy.sql.elements import ColumnElement
from sqlalchemy.sql.selectable import Select

from app.models import CostElementSchedule, CostRegistration, EarnedValueEntry

FilterFactory = Callable[[date], tuple[ColumnElement[bool], ...]]


class TimeMachineEventType(str, Enum):
    """Enumerates event types supported by the time-machine helper."""

    SCHEDULE = "schedule"
    EARNED_VALUE = "earned_value"
    COST_REGISTRATION = "cost_registration"


def end_of_day(control_date: date) -> datetime:
    """Return timezone-aware datetime representing the end of the provided date."""
    return datetime.combine(control_date, time.max, tzinfo=timezone.utc)


def _schedule_filters(control_date: date) -> tuple[ColumnElement[bool], ...]:
    cutoff = end_of_day(control_date)
    return (
        CostElementSchedule.registration_date <= control_date,
        CostElementSchedule.created_at <= cutoff,
    )


def _earned_value_filters(control_date: date) -> tuple[ColumnElement[bool], ...]:
    cutoff = end_of_day(control_date)
    return (
        EarnedValueEntry.completion_date <= control_date,
        EarnedValueEntry.registration_date <= control_date,
        EarnedValueEntry.created_at <= cutoff,
    )


def _cost_registration_filters(control_date: date) -> tuple[ColumnElement[bool], ...]:
    cutoff = end_of_day(control_date)
    return (
        CostRegistration.registration_date <= control_date,
        CostRegistration.created_at <= cutoff,
    )


_VISIBILITY_FILTERS: dict[TimeMachineEventType, FilterFactory] = {
    TimeMachineEventType.SCHEDULE: _schedule_filters,
    TimeMachineEventType.EARNED_VALUE: _earned_value_filters,
    TimeMachineEventType.COST_REGISTRATION: _cost_registration_filters,
}


def register_time_machine_filters(
    event_type: TimeMachineEventType, factory: FilterFactory
) -> None:
    """Allow future event types to register custom visibility logic."""
    _VISIBILITY_FILTERS[event_type] = factory


def get_visibility_filters(
    event_type: TimeMachineEventType, control_date: date
) -> tuple[ColumnElement[bool], ...]:
    """Retrieve the configured filters for an event type."""
    if event_type not in _VISIBILITY_FILTERS:
        msg = f"No time-machine filters registered for {event_type}"
        raise ValueError(msg)
    return _VISIBILITY_FILTERS[event_type](control_date)


def apply_time_machine_filters(
    statement: Select, event_type: TimeMachineEventType, control_date: date
) -> Select:
    """Apply the event-specific time-machine filters to a SQLAlchemy statement."""
    filters = get_visibility_filters(event_type, control_date)
    if not filters:
        return statement
    return statement.where(*filters)


def schedule_visibility_filters(control_date: date) -> tuple[ColumnElement[bool], ...]:
    """Backward-compatible wrapper for schedule filters."""
    return get_visibility_filters(TimeMachineEventType.SCHEDULE, control_date)


def earned_value_visibility_filters(
    control_date: date,
) -> tuple[ColumnElement[bool], ...]:
    """Backward-compatible wrapper for earned value filters."""
    return get_visibility_filters(TimeMachineEventType.EARNED_VALUE, control_date)
