"""Unified EVM aggregation API endpoints."""

import uuid
from datetime import date
from decimal import Decimal
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select

from app.api.deps import (
    CurrentUser,
    SessionDep,
    get_time_machine_control_date,
)
from app.api.routes.earned_value import _get_entry_map
from app.api.routes.planned_value import _get_schedule_map
from app.models import (
    WBE,
    CostElement,
    CostRegistration,
    EVMIndicesCostElementPublic,
    EVMIndicesProjectPublic,
    EVMIndicesWBEPublic,
    Project,
)
from app.services.evm_aggregation import (
    aggregate_cost_element_metrics,
    get_cost_element_evm_metrics,
)
from app.services.time_machine import (
    TimeMachineEventType,
    apply_time_machine_filters,
    end_of_day,
)

router = APIRouter(prefix="/projects", tags=["evm-metrics"])


def _ensure_project_exists(session: SessionDep, project_id: uuid.UUID) -> Project:
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _ensure_wbe_exists(
    session: SessionDep, project_id: uuid.UUID, wbe_id: uuid.UUID, control_date: date
) -> WBE:
    project = _ensure_project_exists(session, project_id)
    wbe = session.get(WBE, wbe_id)
    if not wbe or wbe.project_id != project.project_id:
        raise HTTPException(status_code=404, detail="WBE not found")
    cutoff = end_of_day(control_date)
    if wbe.created_at > cutoff:
        raise HTTPException(status_code=404, detail="WBE not found")
    return wbe


@router.get(
    "/{project_id}/evm-metrics/cost-elements/{cost_element_id}",
    response_model=EVMIndicesCostElementPublic,
)
def get_cost_element_evm_metrics_endpoint(
    *,
    session: SessionDep,
    _current_user: CurrentUser,
    project_id: uuid.UUID,
    cost_element_id: uuid.UUID,
    control_date: Annotated[date, Depends(get_time_machine_control_date)],
) -> Any:
    """Get all EVM metrics for a cost element.

    Returns:
        EVMIndicesCostElementPublic with PV, EV, AC, BAC, CPI, SPI, TCPI, CV, SV.
    """
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

    # Get schedule
    schedule_map = _get_schedule_map(session, [cost_element_id], control_date)
    schedule = schedule_map.get(cost_element_id)

    # Get earned value entry
    entry_map = _get_entry_map(session, [cost_element_id], control_date)
    entry = entry_map.get(cost_element_id)

    # Get cost registrations
    statement = select(CostRegistration).where(
        CostRegistration.cost_element_id == cost_element_id,
    )
    statement = apply_time_machine_filters(
        statement, TimeMachineEventType.COST_REGISTRATION, control_date
    )
    cost_registrations = session.exec(statement).all()

    # Calculate metrics using unified service
    metrics = get_cost_element_evm_metrics(
        cost_element=cost_element,
        schedule=schedule,
        entry=entry,
        cost_registrations=cost_registrations,
        control_date=control_date,
    )

    return EVMIndicesCostElementPublic(
        level="cost-element",
        control_date=control_date,
        cost_element_id=cost_element.cost_element_id,
        planned_value=metrics.planned_value,
        earned_value=metrics.earned_value,
        actual_cost=metrics.actual_cost,
        budget_bac=metrics.budget_bac,
        cpi=metrics.cpi,
        spi=metrics.spi,
        tcpi=metrics.tcpi,
        cost_variance=metrics.cost_variance,
        schedule_variance=metrics.schedule_variance,
    )


@router.get(
    "/{project_id}/evm-metrics/wbes/{wbe_id}",
    response_model=EVMIndicesWBEPublic,
)
def get_wbe_evm_metrics_endpoint(
    *,
    session: SessionDep,
    _current_user: CurrentUser,
    project_id: uuid.UUID,
    wbe_id: uuid.UUID,
    control_date: Annotated[date, Depends(get_time_machine_control_date)],
) -> Any:
    """Get all EVM metrics for a WBE (aggregated from cost elements).

    Returns:
        EVMIndicesWBEPublic with PV, EV, AC, BAC, CPI, SPI, TCPI, CV, SV.
    """
    wbe = _ensure_wbe_exists(session, project_id, wbe_id, control_date)

    # Get cost elements for WBE
    cutoff = end_of_day(control_date)
    cost_elements = session.exec(
        select(CostElement).where(
            CostElement.wbe_id == wbe_id,
            CostElement.created_at <= cutoff,
        )
    ).all()

    if not cost_elements:
        # Return zeros for empty WBE
        return EVMIndicesWBEPublic(
            level="wbe",
            control_date=control_date,
            wbe_id=wbe.wbe_id,
            planned_value=Decimal("0.00"),
            earned_value=Decimal("0.00"),
            actual_cost=Decimal("0.00"),
            budget_bac=Decimal("0.00"),
            cpi=None,
            spi=None,
            tcpi=None,
            cost_variance=Decimal("0.00"),
            schedule_variance=Decimal("0.00"),
        )

    cost_element_ids = [ce.cost_element_id for ce in cost_elements]

    # Get schedules
    schedule_map = _get_schedule_map(session, cost_element_ids, control_date)

    # Get entries
    entry_map = _get_entry_map(session, cost_element_ids, control_date)

    # Get cost registrations
    statement = select(CostRegistration).where(
        CostRegistration.cost_element_id.in_(cost_element_ids),
    )
    statement = apply_time_machine_filters(
        statement, TimeMachineEventType.COST_REGISTRATION, control_date
    )
    all_cost_registrations = session.exec(statement).all()

    # Group cost registrations by cost element
    cost_registrations_by_ce: dict[uuid.UUID, list[CostRegistration]] = {}
    for cr in all_cost_registrations:
        if cr.cost_element_id not in cost_registrations_by_ce:
            cost_registrations_by_ce[cr.cost_element_id] = []
        cost_registrations_by_ce[cr.cost_element_id].append(cr)

    # Calculate metrics for each cost element
    cost_element_metrics = []
    for cost_element in cost_elements:
        metrics = get_cost_element_evm_metrics(
            cost_element=cost_element,
            schedule=schedule_map.get(cost_element.cost_element_id),
            entry=entry_map.get(cost_element.cost_element_id),
            cost_registrations=cost_registrations_by_ce.get(
                cost_element.cost_element_id, []
            ),
            control_date=control_date,
        )
        cost_element_metrics.append(metrics)

    # Aggregate metrics
    aggregated = aggregate_cost_element_metrics(cost_element_metrics)

    return EVMIndicesWBEPublic(
        level="wbe",
        control_date=control_date,
        wbe_id=wbe.wbe_id,
        planned_value=aggregated.planned_value,
        earned_value=aggregated.earned_value,
        actual_cost=aggregated.actual_cost,
        budget_bac=aggregated.budget_bac,
        cpi=aggregated.cpi,
        spi=aggregated.spi,
        tcpi=aggregated.tcpi,
        cost_variance=aggregated.cost_variance,
        schedule_variance=aggregated.schedule_variance,
    )


@router.get(
    "/{project_id}/evm-metrics",
    response_model=EVMIndicesProjectPublic,
)
def get_project_evm_metrics_endpoint(
    *,
    session: SessionDep,
    _current_user: CurrentUser,
    project_id: uuid.UUID,
    control_date: Annotated[date, Depends(get_time_machine_control_date)],
) -> Any:
    """Get all EVM metrics for a project (aggregated from WBEs).

    Returns:
        EVMIndicesProjectPublic with PV, EV, AC, BAC, CPI, SPI, TCPI, CV, SV.
    """
    project = _ensure_project_exists(session, project_id)

    # Get WBEs for project
    cutoff = end_of_day(control_date)
    wbes = session.exec(
        select(WBE).where(
            WBE.project_id == project_id,
            WBE.created_at <= cutoff,
        )
    ).all()

    if not wbes:
        # Return zeros for empty project
        return EVMIndicesProjectPublic(
            level="project",
            control_date=control_date,
            project_id=project.project_id,
            planned_value=Decimal("0.00"),
            earned_value=Decimal("0.00"),
            actual_cost=Decimal("0.00"),
            budget_bac=Decimal("0.00"),
            cpi=None,
            spi=None,
            tcpi=None,
            cost_variance=Decimal("0.00"),
            schedule_variance=Decimal("0.00"),
        )

    wbe_ids = [wbe.wbe_id for wbe in wbes]

    # Get all cost elements for all WBEs
    cost_elements = session.exec(
        select(CostElement).where(
            CostElement.wbe_id.in_(wbe_ids),
            CostElement.created_at <= cutoff,
        )
    ).all()

    if not cost_elements:
        # Return zeros for project with no cost elements
        return EVMIndicesProjectPublic(
            level="project",
            control_date=control_date,
            project_id=project.project_id,
            planned_value=Decimal("0.00"),
            earned_value=Decimal("0.00"),
            actual_cost=Decimal("0.00"),
            budget_bac=Decimal("0.00"),
            cpi=None,
            spi=None,
            tcpi=None,
            cost_variance=Decimal("0.00"),
            schedule_variance=Decimal("0.00"),
        )

    cost_element_ids = [ce.cost_element_id for ce in cost_elements]

    # Get schedules
    schedule_map = _get_schedule_map(session, cost_element_ids, control_date)

    # Get entries
    entry_map = _get_entry_map(session, cost_element_ids, control_date)

    # Get cost registrations
    statement = select(CostRegistration).where(
        CostRegistration.cost_element_id.in_(cost_element_ids),
    )
    statement = apply_time_machine_filters(
        statement, TimeMachineEventType.COST_REGISTRATION, control_date
    )
    all_cost_registrations = session.exec(statement).all()

    # Group cost registrations by cost element
    cost_registrations_by_ce: dict[uuid.UUID, list[CostRegistration]] = {}
    for cr in all_cost_registrations:
        if cr.cost_element_id not in cost_registrations_by_ce:
            cost_registrations_by_ce[cr.cost_element_id] = []
        cost_registrations_by_ce[cr.cost_element_id].append(cr)

    # Calculate metrics for each cost element
    cost_element_metrics = []
    for cost_element in cost_elements:
        metrics = get_cost_element_evm_metrics(
            cost_element=cost_element,
            schedule=schedule_map.get(cost_element.cost_element_id),
            entry=entry_map.get(cost_element.cost_element_id),
            cost_registrations=cost_registrations_by_ce.get(
                cost_element.cost_element_id, []
            ),
            control_date=control_date,
        )
        cost_element_metrics.append(metrics)

    # Aggregate metrics
    aggregated = aggregate_cost_element_metrics(cost_element_metrics)

    return EVMIndicesProjectPublic(
        level="project",
        control_date=control_date,
        project_id=project.project_id,
        planned_value=aggregated.planned_value,
        earned_value=aggregated.earned_value,
        actual_cost=aggregated.actual_cost,
        budget_bac=aggregated.budget_bac,
        cpi=aggregated.cpi,
        spi=aggregated.spi,
        tcpi=aggregated.tcpi,
        cost_variance=aggregated.cost_variance,
        schedule_variance=aggregated.schedule_variance,
    )
