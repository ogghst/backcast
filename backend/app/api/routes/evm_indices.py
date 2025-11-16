"""API endpoints for EVM performance indices calculations."""

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
from app.api.routes.earned_value import (
    _get_entry_map,
)
from app.api.routes.planned_value import (
    _get_schedule_map,
)
from app.models import (
    WBE,
    CostElement,
    CostRegistration,
    EVMIndicesProjectPublic,
    EVMIndicesWBEPublic,
    Project,
)
from app.services.evm_aggregation import (
    aggregate_cost_element_metrics,
    get_cost_element_evm_metrics,
)
from app.services.evm_indices import (
    calculate_cost_variance,
    calculate_cpi,
    calculate_schedule_variance,
    calculate_spi,
    calculate_tcpi,
)
from app.services.time_machine import (
    TimeMachineEventType,
    apply_time_machine_filters,
    end_of_day,
)

router = APIRouter(prefix="/projects", tags=["evm-indices"])


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


def _get_wbe_evm_inputs(
    session: SessionDep, wbe_id: uuid.UUID, control_date: date
) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    """Get PV, EV, AC, and BAC for a WBE at control date using unified aggregation service.

    Returns:
        Tuple of (planned_value, earned_value, actual_cost, budget_bac)
    """
    # Get cost elements for WBE
    cutoff = end_of_day(control_date)
    cost_elements = session.exec(
        select(CostElement).where(
            CostElement.wbe_id == wbe_id,
            CostElement.created_at <= cutoff,
        )
    ).all()

    if not cost_elements:
        return Decimal("0.00"), Decimal("0.00"), Decimal("0.00"), Decimal("0.00")

    cost_element_ids = [ce.cost_element_id for ce in cost_elements]

    # Get schedules, entries, and cost registrations
    schedule_map = _get_schedule_map(session, cost_element_ids, control_date)
    entry_map = _get_entry_map(session, cost_element_ids, control_date)

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

    # Calculate metrics for each cost element using unified service
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

    return (
        aggregated.planned_value,
        aggregated.earned_value,
        aggregated.actual_cost,
        aggregated.budget_bac,
    )


def _get_project_evm_inputs(
    session: SessionDep, project_id: uuid.UUID, control_date: date
) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    """Get PV, EV, AC, and BAC for a project at control date using unified aggregation service.

    Returns:
        Tuple of (planned_value, earned_value, actual_cost, budget_bac)
    """
    _ensure_project_exists(session, project_id)

    # Get all WBEs for project
    cutoff = end_of_day(control_date)
    wbes = session.exec(
        select(WBE).where(
            WBE.project_id == project_id,
            WBE.created_at <= cutoff,
        )
    ).all()

    if not wbes:
        return Decimal("0.00"), Decimal("0.00"), Decimal("0.00"), Decimal("0.00")

    wbe_ids = [wbe.wbe_id for wbe in wbes]

    # Get all cost elements for all WBEs
    cost_elements = session.exec(
        select(CostElement).where(
            CostElement.wbe_id.in_(wbe_ids),
            CostElement.created_at <= cutoff,
        )
    ).all()

    if not cost_elements:
        return Decimal("0.00"), Decimal("0.00"), Decimal("0.00"), Decimal("0.00")

    cost_element_ids = [ce.cost_element_id for ce in cost_elements]

    # Get schedules, entries, and cost registrations
    schedule_map = _get_schedule_map(session, cost_element_ids, control_date)
    entry_map = _get_entry_map(session, cost_element_ids, control_date)

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

    # Calculate metrics for each cost element using unified service
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

    return (
        aggregated.planned_value,
        aggregated.earned_value,
        aggregated.actual_cost,
        aggregated.budget_bac,
    )


@router.get(
    "/{project_id}/evm-indices/wbes/{wbe_id}",
    response_model=EVMIndicesWBEPublic,
    deprecated=True,
    summary="Get EVM indices for a WBE (DEPRECATED)",
    description="**DEPRECATED:** Use `/projects/{project_id}/evm-metrics/wbes/{wbe_id}` instead. "
    "This endpoint will be removed in a future version. The unified EVM metrics endpoint provides the same functionality "
    "with consistent aggregation logic.",
)
def get_wbe_evm_indices(
    *,
    session: SessionDep,
    _current_user: CurrentUser,
    project_id: uuid.UUID,
    wbe_id: uuid.UUID,
    control_date: Annotated[date, Depends(get_time_machine_control_date)],
) -> Any:
    """Get EVM performance indices (CPI, SPI, TCPI) for a WBE.

    Returns:
        EVMIndicesWBEPublic with CPI, SPI, TCPI, and underlying PV, EV, AC, BAC values.
    """
    wbe = _ensure_wbe_exists(session, project_id, wbe_id, control_date)

    pv, ev, ac, bac = _get_wbe_evm_inputs(session, wbe_id, control_date)

    # Calculate indices
    cpi = calculate_cpi(ev, ac)
    spi = calculate_spi(ev, pv)
    tcpi = calculate_tcpi(bac, ev, ac)

    # Calculate variances
    cost_variance = calculate_cost_variance(ev, ac)
    schedule_variance = calculate_schedule_variance(ev, pv)

    return EVMIndicesWBEPublic(
        level="wbe",
        control_date=control_date,
        cpi=cpi,
        spi=spi,
        tcpi=tcpi,
        planned_value=pv,
        earned_value=ev,
        actual_cost=ac,
        budget_bac=bac,
        cost_variance=cost_variance,
        schedule_variance=schedule_variance,
        wbe_id=wbe.wbe_id,
    )


@router.get(
    "/{project_id}/evm-indices",
    response_model=EVMIndicesProjectPublic,
    deprecated=True,
    summary="Get EVM indices for a project (DEPRECATED)",
    description="**DEPRECATED:** Use `/projects/{project_id}/evm-metrics` instead. "
    "This endpoint will be removed in a future version. The unified EVM metrics endpoint provides the same functionality "
    "with consistent aggregation logic.",
)
def get_project_evm_indices(
    *,
    session: SessionDep,
    _current_user: CurrentUser,
    project_id: uuid.UUID,
    control_date: Annotated[date, Depends(get_time_machine_control_date)],
) -> Any:
    """Get EVM performance indices (CPI, SPI, TCPI) for a project.

    Returns:
        EVMIndicesProjectPublic with CPI, SPI, TCPI, and underlying PV, EV, AC, BAC values.
    """
    project = _ensure_project_exists(session, project_id)

    pv, ev, ac, bac = _get_project_evm_inputs(session, project_id, control_date)

    # Calculate indices
    cpi = calculate_cpi(ev, ac)
    spi = calculate_spi(ev, pv)
    tcpi = calculate_tcpi(bac, ev, ac)

    # Calculate variances
    cost_variance = calculate_cost_variance(ev, ac)
    schedule_variance = calculate_schedule_variance(ev, pv)

    return EVMIndicesProjectPublic(
        level="project",
        control_date=control_date,
        cpi=cpi,
        spi=spi,
        tcpi=tcpi,
        planned_value=pv,
        earned_value=ev,
        actual_cost=ac,
        budget_bac=bac,
        cost_variance=cost_variance,
        schedule_variance=schedule_variance,
        project_id=project.project_id,
    )
