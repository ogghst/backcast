"""Cost Summary API routes."""

import uuid
from datetime import date, datetime, time, timezone
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from sqlmodel import select

from app.api.deps import CurrentUser, SessionDep, TimeMachineControlDate
from app.models import WBE, CostElement, CostRegistration, Project
from app.models.cost_summary import CostSummaryPublic
from app.services.time_machine import TimeMachineEventType, apply_time_machine_filters

router = APIRouter(prefix="/cost-summary", tags=["cost-summary"])


def _end_of_day(control_date: date) -> datetime:
    """Return timezone-aware datetime representing end of control date."""
    return datetime.combine(control_date, time.max, tzinfo=timezone.utc)


@router.get("/cost-element/{cost_element_id}", response_model=CostSummaryPublic)
def get_cost_element_cost_summary(
    session: SessionDep,
    _current_user: CurrentUser,
    cost_element_id: uuid.UUID,
    control_date: TimeMachineControlDate,
    is_quality_cost: bool | None = Query(
        default=None, description="Filter by quality cost"
    ),
) -> Any:
    """
    Get cost summary for a cost element.

    Aggregates:
    - total_cost: sum of cost_registration.amount for this cost element
    - budget_bac: cost_element.budget_bac
    - cost_registration_count: number of cost registrations aggregated
    - cost_percentage_of_budget: (total_cost / budget_bac) * 100

    Optional filter:
    - is_quality_cost: If True, only include quality costs. If False, only regular costs. If None, include all.
    """
    # Get cost element
    cost_element = session.get(CostElement, cost_element_id)
    if not cost_element:
        raise HTTPException(status_code=404, detail="Cost element not found")
    if cost_element.created_at > _end_of_day(control_date):
        raise HTTPException(status_code=404, detail="Cost element not found")

    # Get all cost registrations for this cost element
    statement = select(CostRegistration).where(
        CostRegistration.cost_element_id == cost_element_id,
    )

    # Apply quality cost filter if provided
    if is_quality_cost is not None:
        statement = statement.where(CostRegistration.is_quality_cost == is_quality_cost)

    statement = apply_time_machine_filters(
        statement, TimeMachineEventType.COST_REGISTRATION, control_date
    )
    cost_registrations = session.exec(statement).all()

    # Calculate total cost
    total_cost = sum(cr.amount for cr in cost_registrations)

    # Create summary
    summary = CostSummaryPublic(
        level="cost-element",
        total_cost=total_cost,
        budget_bac=cost_element.budget_bac,
        cost_registration_count=len(cost_registrations),
        cost_element_id=str(cost_element.cost_element_id),
    )

    return summary


@router.get("/wbe/{wbe_id}", response_model=CostSummaryPublic)
def get_wbe_cost_summary(
    session: SessionDep,
    _current_user: CurrentUser,
    wbe_id: uuid.UUID,
    control_date: TimeMachineControlDate,
    is_quality_cost: bool | None = Query(
        default=None, description="Filter by quality cost"
    ),
) -> Any:
    """
    Get cost summary for a WBE.

    Aggregates:
    - total_cost: sum of cost_registration.amount for all cost elements in this WBE
    - budget_bac: sum of cost_element.budget_bac for all cost elements in this WBE
    - cost_registration_count: number of cost registrations aggregated across all cost elements

    Optional filter:
    - is_quality_cost: If True, only include quality costs. If False, only regular costs. If None, include all.
    """
    # Get WBE
    wbe = session.get(WBE, wbe_id)
    if not wbe:
        raise HTTPException(status_code=404, detail="WBE not found")
    if wbe.created_at > _end_of_day(control_date):
        raise HTTPException(status_code=404, detail="WBE not found")

    # Get all cost elements for this WBE
    cost_elements = session.exec(
        select(CostElement).where(
            CostElement.wbe_id == wbe_id,
            CostElement.created_at <= _end_of_day(control_date),
        )
    ).all()

    # Calculate total budget BAC for this WBE
    total_budget_bac = (
        sum(ce.budget_bac for ce in cost_elements) if cost_elements else Decimal("0.00")
    )

    # Get all cost registrations for all cost elements in this WBE
    cost_element_ids = [ce.cost_element_id for ce in cost_elements]
    if cost_element_ids:
        statement = select(CostRegistration).where(
            CostRegistration.cost_element_id.in_(cost_element_ids),
        )

        # Apply quality cost filter if provided
        if is_quality_cost is not None:
            statement = statement.where(
                CostRegistration.is_quality_cost == is_quality_cost
            )

        statement = apply_time_machine_filters(
            statement, TimeMachineEventType.COST_REGISTRATION, control_date
        )
        cost_registrations = session.exec(statement).all()
    else:
        cost_registrations = []

    # Calculate total cost
    total_cost = sum(cr.amount for cr in cost_registrations)

    # Create summary
    summary = CostSummaryPublic(
        level="wbe",
        total_cost=total_cost,
        budget_bac=total_budget_bac,
        cost_registration_count=len(cost_registrations),
        wbe_id=str(wbe.wbe_id),
    )

    return summary


@router.get("/project/{project_id}", response_model=CostSummaryPublic)
def get_project_cost_summary(
    session: SessionDep,
    _current_user: CurrentUser,
    project_id: uuid.UUID,
    control_date: TimeMachineControlDate,
    is_quality_cost: bool | None = Query(
        default=None, description="Filter by quality cost"
    ),
) -> Any:
    """
    Get cost summary for a project.

    Aggregates:
    - total_cost: sum of cost_registration.amount for all cost elements in all WBEs in this project
    - budget_bac: sum of cost_element.budget_bac for all cost elements in all WBEs
    - cost_registration_count: number of cost registrations aggregated across all cost elements

    Optional filter:
    - is_quality_cost: If True, only include quality costs. If False, only regular costs. If None, include all.
    """
    # Get project
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get all WBEs for this project
    wbes = session.exec(
        select(WBE).where(
            WBE.project_id == project_id,
            WBE.created_at <= _end_of_day(control_date),
        )
    ).all()

    # Get all cost elements for all WBEs in this project
    wbe_ids = [wbe.wbe_id for wbe in wbes]
    if wbe_ids:
        cost_elements = session.exec(
            select(CostElement).where(
                CostElement.wbe_id.in_(wbe_ids),
                CostElement.created_at <= _end_of_day(control_date),
            )
        ).all()
    else:
        cost_elements = []

    # Calculate total budget BAC for this project
    total_budget_bac = (
        sum(ce.budget_bac for ce in cost_elements) if cost_elements else Decimal("0.00")
    )

    # Get all cost registrations for all cost elements in this project
    cost_element_ids = [ce.cost_element_id for ce in cost_elements]
    if cost_element_ids:
        statement = select(CostRegistration).where(
            CostRegistration.cost_element_id.in_(cost_element_ids),
        )

        # Apply quality cost filter if provided
        if is_quality_cost is not None:
            statement = statement.where(
                CostRegistration.is_quality_cost == is_quality_cost
            )

        statement = apply_time_machine_filters(
            statement, TimeMachineEventType.COST_REGISTRATION, control_date
        )
        cost_registrations = session.exec(statement).all()
    else:
        cost_registrations = []

    # Calculate total cost
    total_cost = sum(cr.amount for cr in cost_registrations)

    # Create summary
    summary = CostSummaryPublic(
        level="project",
        total_cost=total_cost,
        budget_bac=total_budget_bac,
        cost_registration_count=len(cost_registrations),
        project_id=str(project.project_id),
    )

    return summary
