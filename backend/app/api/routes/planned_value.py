"""API endpoints for planned value calculations."""

import uuid
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from fastapi import APIRouter, HTTPException, Query
from sqlmodel import select

from app.api.deps import CurrentUser, SessionDep
from app.models import (
    WBE,
    CostElement,
    CostElementSchedule,
    PlannedValueCostElementPublic,
    PlannedValueProjectPublic,
    PlannedValueWBEPublic,
    Project,
)
from app.services.planned_value import (
    aggregate_planned_value,
    calculate_cost_element_planned_value,
)
from app.services.time_machine import (
    TimeMachineEventType,
    apply_time_machine_filters,
)

router = APIRouter(prefix="/projects", tags=["planned-value"])


def _ensure_project_exists(session: SessionDep, project_id: uuid.UUID) -> Project:
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _select_schedule_for_cost_element(
    session: SessionDep, cost_element_id: uuid.UUID, control_date: date
) -> CostElementSchedule | None:
    base_statement = (
        select(CostElementSchedule)
        .where(CostElementSchedule.cost_element_id == cost_element_id)
        .where(CostElementSchedule.baseline_id.is_(None))
    )

    prioritized = apply_time_machine_filters(
        base_statement, TimeMachineEventType.SCHEDULE, control_date
    ).order_by(
        CostElementSchedule.registration_date.desc(),
        CostElementSchedule.created_at.desc(),
    )
    return session.exec(prioritized).first()


def _get_schedule_map(
    session: SessionDep, cost_element_ids: list[uuid.UUID], control_date: date
) -> dict[uuid.UUID, CostElementSchedule]:
    schedule_map: dict[uuid.UUID, CostElementSchedule] = {}
    for cost_element_id in cost_element_ids:
        schedule = _select_schedule_for_cost_element(
            session, cost_element_id, control_date
        )
        if schedule:
            schedule_map[cost_element_id] = schedule
    return schedule_map


@router.get(
    "/{project_id}/planned-value/cost-elements/{cost_element_id}",
    response_model=PlannedValueCostElementPublic,
)
def get_cost_element_planned_value(
    *,
    session: SessionDep,
    _current_user: CurrentUser,
    project_id: uuid.UUID,
    cost_element_id: uuid.UUID,
    control_date: date = Query(..., description="Control date for planned value"),
) -> PlannedValueCostElementPublic:
    project = _ensure_project_exists(session, project_id)

    cost_element = session.get(CostElement, cost_element_id)
    if not cost_element:
        raise HTTPException(status_code=404, detail="Cost element not found")

    wbe = session.get(WBE, cost_element.wbe_id)
    if not wbe or wbe.project_id != project.project_id:
        raise HTTPException(status_code=404, detail="Cost element not found")

    schedule = _select_schedule_for_cost_element(
        session, cost_element.cost_element_id, control_date
    )

    planned_value, percent = calculate_cost_element_planned_value(
        cost_element=cost_element, schedule=schedule, control_date=control_date
    )

    return PlannedValueCostElementPublic(
        level="cost-element",
        control_date=control_date,
        planned_value=planned_value,
        percent_complete=percent,
        budget_bac=_quantize_decimal(cost_element.budget_bac or Decimal("0.00")),
        cost_element_id=cost_element.cost_element_id,
    )


@router.get(
    "/{project_id}/planned-value/wbes/{wbe_id}",
    response_model=PlannedValueWBEPublic,
)
def get_wbe_planned_value(
    *,
    session: SessionDep,
    _current_user: CurrentUser,
    project_id: uuid.UUID,
    wbe_id: uuid.UUID,
    control_date: date = Query(..., description="Control date for planned value"),
) -> PlannedValueWBEPublic:
    project = _ensure_project_exists(session, project_id)

    wbe = session.get(WBE, wbe_id)
    if not wbe or wbe.project_id != project.project_id:
        raise HTTPException(status_code=404, detail="WBE not found")

    cost_elements = session.exec(
        select(CostElement).where(CostElement.wbe_id == wbe.wbe_id)
    ).all()

    schedule_map = _get_schedule_map(
        session, [ce.cost_element_id for ce in cost_elements], control_date
    )

    tuples: list[tuple[Decimal, Decimal]] = []
    for cost_element in cost_elements:
        planned_value, _percent = calculate_cost_element_planned_value(
            cost_element=cost_element,
            schedule=schedule_map.get(cost_element.cost_element_id),
            control_date=control_date,
        )
        tuples.append((planned_value, cost_element.budget_bac or Decimal("0.00")))

    aggregates = aggregate_planned_value(tuples)

    return PlannedValueWBEPublic(
        level="wbe",
        control_date=control_date,
        planned_value=aggregates.planned_value,
        percent_complete=aggregates.percent_complete,
        budget_bac=aggregates.budget_bac,
        wbe_id=wbe.wbe_id,
    )


@router.get(
    "/{project_id}/planned-value",
    response_model=PlannedValueProjectPublic,
)
def get_project_planned_value(
    *,
    session: SessionDep,
    _current_user: CurrentUser,
    project_id: uuid.UUID,
    control_date: date = Query(..., description="Control date for planned value"),
) -> PlannedValueProjectPublic:
    project = _ensure_project_exists(session, project_id)

    wbes = session.exec(select(WBE).where(WBE.project_id == project.project_id)).all()
    wbe_ids = [wbe.wbe_id for wbe in wbes]
    if wbe_ids:
        cost_elements = session.exec(
            select(CostElement).where(CostElement.wbe_id.in_(wbe_ids))
        ).all()
    else:
        cost_elements = []

    schedule_map = _get_schedule_map(
        session, [ce.cost_element_id for ce in cost_elements], control_date
    )

    tuples: list[tuple[Decimal, Decimal]] = []
    for cost_element in cost_elements:
        planned_value, _percent = calculate_cost_element_planned_value(
            cost_element=cost_element,
            schedule=schedule_map.get(cost_element.cost_element_id),
            control_date=control_date,
        )
        tuples.append((planned_value, cost_element.budget_bac or Decimal("0.00")))

    aggregates = aggregate_planned_value(tuples)

    return PlannedValueProjectPublic(
        level="project",
        control_date=control_date,
        planned_value=aggregates.planned_value,
        percent_complete=aggregates.percent_complete,
        budget_bac=aggregates.budget_bac,
        project_id=project.project_id,
    )


def _quantize_decimal(value: Decimal) -> Decimal:
    """Helper to ensure Decimal values have two decimal places."""
    return value.quantize(Decimal("0.00"), rounding=ROUND_HALF_UP)
