"""Cost Timeline API routes."""
import uuid
from collections import defaultdict
from datetime import date
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from sqlmodel import select

from app.api.deps import CurrentUser, SessionDep
from app.models import (
    WBE,
    CostElement,
    CostRegistration,
    Project,
)
from app.models.cost_timeline import (
    CostTimelinePointPublic,
    CostTimelinePublic,
)

router = APIRouter(prefix="/projects", tags=["cost-timeline"])


@router.get("/{project_id}/cost-timeline/", response_model=CostTimelinePublic)
def get_project_cost_timeline(
    session: SessionDep,
    _current_user: CurrentUser,
    project_id: uuid.UUID,
    wbe_ids: list[uuid.UUID] | None = Query(
        default=None, description="Filter by WBE IDs"
    ),
    cost_element_ids: list[uuid.UUID] | None = Query(
        default=None, description="Filter by cost element IDs"
    ),
    start_date: date | None = Query(
        default=None, description="Start date for time series"
    ),
    end_date: date | None = Query(default=None, description="End date for time series"),
) -> Any:
    """
    Get cost timeline (time-phased cost aggregation) for a project.

    Returns cumulative costs by date, aggregated from cost registrations.
    Supports filtering by WBE IDs, cost element IDs, and date range.

    Args:
        project_id: ID of the project
        wbe_ids: Optional list of WBE IDs to filter by
        cost_element_ids: Optional list of cost element IDs to filter by
        start_date: Optional start date for time series
        end_date: Optional end date for time series

    Returns:
        CostTimelinePublic with time series points and total cost
    """
    # Validate project exists
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get all WBEs for this project
    wbes_statement = select(WBE).where(WBE.project_id == project_id)
    wbes = session.exec(wbes_statement).all()
    wbe_ids_from_project = [wbe.wbe_id for wbe in wbes]

    if not wbe_ids_from_project:
        # No WBEs, return empty timeline
        return CostTimelinePublic(data=[], total_cost=Decimal("0.00"))

    # Build query for cost elements
    cost_elements_statement = select(CostElement).where(
        CostElement.wbe_id.in_(wbe_ids_from_project)
    )

    # Apply WBE filter if provided
    if wbe_ids:
        filtered_wbe_ids = [
            wbe_id for wbe_id in wbe_ids if wbe_id in wbe_ids_from_project
        ]
        if not filtered_wbe_ids:
            return CostTimelinePublic(data=[], total_cost=Decimal("0.00"))
        cost_elements_statement = cost_elements_statement.where(
            CostElement.wbe_id.in_(filtered_wbe_ids)
        )

    # Apply cost element filter if provided
    if cost_element_ids:
        cost_elements_statement = cost_elements_statement.where(
            CostElement.cost_element_id.in_(cost_element_ids)
        )

    # Get cost elements
    cost_elements = session.exec(cost_elements_statement).all()
    cost_element_ids_filtered = [ce.cost_element_id for ce in cost_elements]

    if not cost_element_ids_filtered:
        # No cost elements, return empty timeline
        return CostTimelinePublic(data=[], total_cost=Decimal("0.00"))

    # Get all cost registrations for these cost elements
    registrations_statement = select(CostRegistration).where(
        CostRegistration.cost_element_id.in_(cost_element_ids_filtered)
    )

    # Apply date range filter if provided
    if start_date:
        registrations_statement = registrations_statement.where(
            CostRegistration.registration_date >= start_date
        )
    if end_date:
        registrations_statement = registrations_statement.where(
            CostRegistration.registration_date <= end_date
        )

    cost_registrations = session.exec(registrations_statement).all()

    if not cost_registrations:
        # No cost registrations, return empty timeline
        return CostTimelinePublic(data=[], total_cost=Decimal("0.00"))

    # Group registrations by date and sum amounts
    costs_by_date: dict[date, Decimal] = defaultdict(lambda: Decimal("0.00"))
    for cr in cost_registrations:
        costs_by_date[cr.registration_date] += cr.amount

    # Calculate total cost
    total_cost = sum(cr.amount for cr in cost_registrations)

    # Sort dates and calculate cumulative costs
    sorted_dates = sorted(costs_by_date.keys())
    timeline_points = []
    cumulative_cost = Decimal("0.00")

    for point_date in sorted_dates:
        period_cost = costs_by_date[point_date]
        cumulative_cost += period_cost
        timeline_points.append(
            CostTimelinePointPublic(
                point_date=point_date,
                cumulative_cost=cumulative_cost,
                period_cost=period_cost,
            )
        )

    return CostTimelinePublic(data=timeline_points, total_cost=total_cost)
