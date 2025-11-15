import uuid
from datetime import date, datetime, time, timezone
from typing import Any

from fastapi import APIRouter, HTTPException
from sqlmodel import select

from app.api.deps import CurrentUser, SessionDep, TimeMachineControlDate
from app.models import WBE, CostElement, Project
from app.models.budget_summary import BudgetSummaryPublic

router = APIRouter(prefix="/budget-summary", tags=["budget-summary"])


def _end_of_day(control_date: date) -> datetime:
    """Return timezone-aware datetime representing the end of the control date."""
    return datetime.combine(control_date, time.max, tzinfo=timezone.utc)


@router.get("/project/{project_id}", response_model=BudgetSummaryPublic)
def get_project_budget_summary(
    session: SessionDep,
    _current_user: CurrentUser,
    project_id: uuid.UUID,
    control_date: TimeMachineControlDate,
) -> Any:
    """
    Get budget summary for a project.

    Aggregates:
    - revenue_limit: project.contract_value
    - total_revenue_allocated: sum of wbe.revenue_allocation
    - total_budget_bac: sum of cost_element.budget_bac across all WBEs
    - total_revenue_plan: sum of cost_element.revenue_plan across all WBEs
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

    # Calculate total revenue allocated (sum of WBE revenue_allocation)
    total_revenue_allocated = sum(wbe.revenue_allocation for wbe in wbes)

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

    # Calculate totals from cost elements
    total_budget_bac = sum(ce.budget_bac for ce in cost_elements)
    total_revenue_plan = sum(ce.revenue_plan for ce in cost_elements)

    # Create summary
    summary = BudgetSummaryPublic(
        level="project",
        revenue_limit=project.contract_value,
        total_revenue_allocated=total_revenue_allocated,
        total_budget_bac=total_budget_bac,
        total_revenue_plan=total_revenue_plan,
        project_id=str(project.project_id),
    )

    return summary


@router.get("/wbe/{wbe_id}", response_model=BudgetSummaryPublic)
def get_wbe_budget_summary(
    session: SessionDep,
    _current_user: CurrentUser,
    wbe_id: uuid.UUID,
    control_date: TimeMachineControlDate,
) -> Any:
    """
    Get budget summary for a WBE.

    Aggregates:
    - revenue_limit: wbe.revenue_allocation
    - total_revenue_allocated: sum of cost_element.revenue_plan
    - total_budget_bac: sum of cost_element.budget_bac
    - total_revenue_plan: sum of cost_element.revenue_plan (same as total_revenue_allocated)
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

    # Calculate totals from cost elements
    total_budget_bac = sum(ce.budget_bac for ce in cost_elements)
    total_revenue_plan = sum(ce.revenue_plan for ce in cost_elements)
    # For WBE level, total_revenue_allocated is the sum of cost element revenue_plan
    total_revenue_allocated = total_revenue_plan

    # Create summary
    summary = BudgetSummaryPublic(
        level="wbe",
        revenue_limit=wbe.revenue_allocation,
        total_revenue_allocated=total_revenue_allocated,
        total_budget_bac=total_budget_bac,
        total_revenue_plan=total_revenue_plan,
        wbe_id=str(wbe.wbe_id),
    )

    return summary
