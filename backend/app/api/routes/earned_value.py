"""API endpoints for earned value calculations."""

import uuid
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select

from app.api.deps import (
    CurrentUser,
    SessionDep,
    get_time_machine_control_date,
)
from app.models import (
    WBE,
    CostElement,
    EarnedValueCostElementPublic,
    EarnedValueEntry,
    EarnedValueProjectPublic,
    EarnedValueWBEPublic,
    Project,
)
from app.services.earned_value import (
    aggregate_earned_value,
    calculate_cost_element_earned_value,
)
from app.services.time_machine import (
    TimeMachineEventType,
    apply_time_machine_filters,
    end_of_day,
)

router = APIRouter(prefix="/projects", tags=["earned-value"])


def _ensure_project_exists(session: SessionDep, project_id: uuid.UUID) -> Project:
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _select_entry_for_cost_element(
    session: SessionDep, cost_element_id: uuid.UUID, control_date: date
) -> EarnedValueEntry | None:
    """Select the most recent earned value entry where completion_date <= control_date.

    Args:
        session: Database session
        cost_element_id: Cost element ID to query entries for
        control_date: Control date for selection

    Returns:
        Most recent EarnedValueEntry where completion_date <= control_date, or None if no such entry exists.
        Tie-breaking: If multiple entries have the same completion_date, selects the one with latest created_at.
    """
    statement = select(EarnedValueEntry).where(
        EarnedValueEntry.cost_element_id == cost_element_id,
    )
    statement = apply_time_machine_filters(
        statement, TimeMachineEventType.EARNED_VALUE, control_date
    ).order_by(
        EarnedValueEntry.completion_date.desc(),
        EarnedValueEntry.created_at.desc(),
    )
    return session.exec(statement).first()


def _get_entry_map(
    session: SessionDep, cost_element_ids: list[uuid.UUID], control_date: date
) -> dict[uuid.UUID, EarnedValueEntry | None]:
    """Get a map of cost_element_id -> most recent entry for multiple cost elements.

    Args:
        session: Database session
        cost_element_ids: List of cost element IDs to query entries for
        control_date: Control date for selection

    Returns:
        Dictionary mapping cost_element_id -> EarnedValueEntry | None.
        Returns empty dict if cost_element_ids is empty.
        For each cost element, selects the most recent entry where completion_date <= control_date.
    """
    if not cost_element_ids:
        return {}

    # Query all entries for the cost elements where completion_date <= control_date
    # We'll need to use a window function or subquery to get the latest per cost element
    # For simplicity, we'll query all and filter in Python (acceptable for reasonable number of entries)
    statement = select(EarnedValueEntry).where(
        EarnedValueEntry.cost_element_id.in_(cost_element_ids),
    )
    statement = apply_time_machine_filters(
        statement, TimeMachineEventType.EARNED_VALUE, control_date
    ).order_by(
        EarnedValueEntry.cost_element_id,
        EarnedValueEntry.completion_date.desc(),
        EarnedValueEntry.created_at.desc(),
    )
    entries = session.exec(statement).all()

    # Build map, keeping only the first (most recent) entry for each cost element
    entry_map: dict[uuid.UUID, EarnedValueEntry | None] = {}
    for entry in entries:
        if entry.cost_element_id not in entry_map:
            entry_map[entry.cost_element_id] = entry

    # Ensure all cost_element_ids are in the map (with None if no entry)
    for cost_element_id in cost_element_ids:
        if cost_element_id not in entry_map:
            entry_map[cost_element_id] = None

    return entry_map


def _quantize_decimal(value: Decimal) -> Decimal:
    """Helper to ensure Decimal values have two decimal places."""
    return value.quantize(Decimal("0.00"), rounding=ROUND_HALF_UP)


@router.get(
    "/{project_id}/earned-value/cost-elements/{cost_element_id}",
    response_model=EarnedValueCostElementPublic,
)
def get_cost_element_earned_value(
    *,
    session: SessionDep,
    _current_user: CurrentUser,
    project_id: uuid.UUID,
    cost_element_id: uuid.UUID,
    control_date: Annotated[date, Depends(get_time_machine_control_date)],
) -> EarnedValueCostElementPublic:
    project = _ensure_project_exists(session, project_id)

    cost_element = session.get(CostElement, cost_element_id)
    if not cost_element:
        raise HTTPException(status_code=404, detail="Cost element not found")
    cutoff = end_of_day(control_date)
    if cost_element.created_at > cutoff:
        raise HTTPException(status_code=404, detail="Cost element not found")

    wbe = session.get(WBE, cost_element.wbe_id)
    if not wbe or wbe.project_id != project.project_id:
        raise HTTPException(status_code=404, detail="Cost element not found")
    if wbe.created_at > cutoff:
        raise HTTPException(status_code=404, detail="Cost element not found")

    entry = _select_entry_for_cost_element(
        session, cost_element.cost_element_id, control_date
    )

    earned_value, percent = calculate_cost_element_earned_value(
        cost_element=cost_element, entry=entry, control_date=control_date
    )

    return EarnedValueCostElementPublic(
        level="cost-element",
        control_date=control_date,
        earned_value=earned_value,
        percent_complete=percent,
        budget_bac=_quantize_decimal(cost_element.budget_bac or Decimal("0.00")),
        cost_element_id=cost_element.cost_element_id,
    )


@router.get(
    "/{project_id}/earned-value/wbes/{wbe_id}",
    response_model=EarnedValueWBEPublic,
)
def get_wbe_earned_value(
    *,
    session: SessionDep,
    _current_user: CurrentUser,
    project_id: uuid.UUID,
    wbe_id: uuid.UUID,
    control_date: Annotated[date, Depends(get_time_machine_control_date)],
) -> EarnedValueWBEPublic:
    project = _ensure_project_exists(session, project_id)

    wbe = session.get(WBE, wbe_id)
    if not wbe or wbe.project_id != project.project_id:
        raise HTTPException(status_code=404, detail="WBE not found")
    cutoff = end_of_day(control_date)
    if wbe.created_at > cutoff:
        raise HTTPException(status_code=404, detail="WBE not found")

    cost_elements = session.exec(
        select(CostElement).where(
            CostElement.wbe_id == wbe.wbe_id,
            CostElement.created_at <= cutoff,
        )
    ).all()

    entry_map = _get_entry_map(
        session, [ce.cost_element_id for ce in cost_elements], control_date
    )

    tuples: list[tuple[Decimal, Decimal]] = []
    for cost_element in cost_elements:
        entry = entry_map.get(cost_element.cost_element_id)
        if entry is None:
            continue
        earned_value, _percent = calculate_cost_element_earned_value(
            cost_element=cost_element,
            entry=entry,
            control_date=control_date,
        )
        tuples.append((earned_value, cost_element.budget_bac or Decimal("0.00")))

    aggregates = aggregate_earned_value(tuples)

    return EarnedValueWBEPublic(
        level="wbe",
        control_date=control_date,
        earned_value=aggregates.earned_value,
        percent_complete=aggregates.percent_complete,
        budget_bac=aggregates.budget_bac,
        wbe_id=wbe.wbe_id,
    )


@router.get(
    "/{project_id}/earned-value",
    response_model=EarnedValueProjectPublic,
)
def get_project_earned_value(
    *,
    session: SessionDep,
    _current_user: CurrentUser,
    project_id: uuid.UUID,
    control_date: Annotated[date, Depends(get_time_machine_control_date)],
) -> EarnedValueProjectPublic:
    project = _ensure_project_exists(session, project_id)

    cutoff = end_of_day(control_date)
    wbes = session.exec(
        select(WBE).where(
            WBE.project_id == project.project_id,
            WBE.created_at <= cutoff,
        )
    ).all()
    wbe_ids = [wbe.wbe_id for wbe in wbes]
    if wbe_ids:
        cost_elements = session.exec(
            select(CostElement).where(
                CostElement.wbe_id.in_(wbe_ids),
                CostElement.created_at <= cutoff,
            )
        ).all()
    else:
        cost_elements = []

    entry_map = _get_entry_map(
        session, [ce.cost_element_id for ce in cost_elements], control_date
    )

    tuples: list[tuple[Decimal, Decimal]] = []
    for cost_element in cost_elements:
        entry = entry_map.get(cost_element.cost_element_id)
        if entry is None:
            continue
        earned_value, _percent = calculate_cost_element_earned_value(
            cost_element=cost_element,
            entry=entry,
            control_date=control_date,
        )
        tuples.append((earned_value, cost_element.budget_bac or Decimal("0.00")))

    aggregates = aggregate_earned_value(tuples)

    return EarnedValueProjectPublic(
        level="project",
        control_date=control_date,
        earned_value=aggregates.earned_value,
        percent_complete=aggregates.percent_complete,
        budget_bac=aggregates.budget_bac,
        project_id=project.project_id,
    )
