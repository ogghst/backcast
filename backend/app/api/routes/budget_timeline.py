"""Budget Timeline API routes."""
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from sqlmodel import select

from app.api.deps import CurrentUser, SessionDep
from app.models import (
    WBE,
    CostElement,
    CostElementSchedule,
    Project,
)
from app.models.budget_timeline import CostElementWithSchedulePublic
from app.models.cost_element import CostElementPublic
from app.models.cost_element_schedule import CostElementSchedulePublic

router = APIRouter(prefix="/projects", tags=["budget-timeline"])


@router.get(
    "/{project_id}/cost-elements-with-schedules",
    response_model=list[CostElementWithSchedulePublic],
)
def get_cost_elements_with_schedules(
    session: SessionDep,
    _current_user: CurrentUser,
    project_id: uuid.UUID,
    wbe_ids: list[uuid.UUID] | None = Query(
        default=None, description="Filter by WBE IDs"
    ),
    cost_element_ids: list[uuid.UUID] | None = Query(
        default=None, description="Filter by cost element IDs"
    ),
    cost_element_type_ids: list[uuid.UUID] | None = Query(
        default=None, description="Filter by cost element type IDs"
    ),
) -> Any:
    """
    Get cost elements with their schedules for a project.

    Supports filtering by WBE IDs, cost element IDs, and cost element type IDs.
    All filters are applied with AND logic (all specified filters must match).
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
        return []

    # Build base query for cost elements in project WBEs
    statement = select(CostElement).where(CostElement.wbe_id.in_(wbe_ids_from_project))

    # Apply filters
    if wbe_ids:
        # Validate that filtered WBEs belong to the project
        filtered_wbe_ids = [
            wbe_id for wbe_id in wbe_ids if wbe_id in wbe_ids_from_project
        ]
        if not filtered_wbe_ids:
            return []
        statement = statement.where(CostElement.wbe_id.in_(filtered_wbe_ids))

    if cost_element_ids:
        statement = statement.where(CostElement.cost_element_id.in_(cost_element_ids))

    if cost_element_type_ids:
        statement = statement.where(
            CostElement.cost_element_type_id.in_(cost_element_type_ids)
        )

    # Execute query
    cost_elements = session.exec(statement).all()

    # Build response with schedules
    result = []
    for ce in cost_elements:
        # Get schedule for this cost element
        schedule_statement = select(CostElementSchedule).where(
            CostElementSchedule.cost_element_id == ce.cost_element_id
        )
        schedule = session.exec(schedule_statement).first()

        # Build response object
        ce_data = CostElementPublic.model_validate(ce)
        schedule_data = None
        if schedule:
            schedule_data = CostElementSchedulePublic.model_validate(schedule)

        result_item = CostElementWithSchedulePublic(
            **ce_data.model_dump(),
            schedule=schedule_data,
        )
        result.append(result_item)

    return result
