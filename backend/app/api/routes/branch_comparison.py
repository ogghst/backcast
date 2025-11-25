"""Branch comparison endpoints for comparing branches."""

import uuid
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from sqlmodel import select

from app.api.deps import CurrentUser, SessionDep
from app.models import WBE, CostElement
from app.services.branch_filtering import apply_branch_filters

router = APIRouter(prefix="/branch-comparison", tags=["branch-comparison"])


@router.get("/{project_id}/compare")
def compare_branches(
    *,
    session: SessionDep,
    _current_user: CurrentUser,
    project_id: uuid.UUID,
    branch: str = Query(..., description="Branch name to compare"),
    base_branch: str = Query(
        default="main", description="Base branch to compare against"
    ),
) -> dict[str, Any]:
    """
    Compare a branch with the base branch (default: main).

    Returns detailed comparison including:
    - Creates: New entities in branch
    - Updates: Modified entities
    - Deletes: Entities deleted in branch
    - Financial impact summary
    """
    if branch == base_branch:
        raise HTTPException(status_code=400, detail="Cannot compare branch with itself")

    # Get all active WBEs in branch
    branch_wbes = session.exec(
        apply_branch_filters(
            select(WBE).where(WBE.project_id == project_id),
            WBE,
            branch=branch,
            include_deleted=False,
        )
    ).all()

    # Get all active WBEs in base branch
    main_wbes = session.exec(
        apply_branch_filters(
            select(WBE).where(WBE.project_id == project_id),
            WBE,
            branch=base_branch,
            include_deleted=False,
        )
    ).all()

    # Create maps
    main_wbe_map = {wbe.entity_id: wbe for wbe in main_wbes}
    branch_wbe_map = {wbe.entity_id: wbe for wbe in branch_wbes}

    # Track changes
    creates: list[dict[str, Any]] = []
    updates: list[dict[str, Any]] = []
    deletes: list[dict[str, Any]] = []

    total_revenue_change = Decimal("0")
    total_budget_change = Decimal("0")

    # Find creates and updates
    for branch_wbe in branch_wbes:
        main_wbe = main_wbe_map.get(branch_wbe.entity_id)

        if main_wbe is None:
            # CREATE operation
            creates.append(
                {
                    "type": "wbe",
                    "entity_id": str(branch_wbe.entity_id),
                    "description": f"Create WBE: {branch_wbe.machine_type}",
                    "revenue_change": float(branch_wbe.revenue_allocation or 0),
                }
            )
            total_revenue_change += Decimal(str(branch_wbe.revenue_allocation or 0))
        else:
            # Check if updated
            if (
                branch_wbe.machine_type != main_wbe.machine_type
                or branch_wbe.revenue_allocation != main_wbe.revenue_allocation
            ):
                updates.append(
                    {
                        "type": "wbe",
                        "entity_id": str(branch_wbe.entity_id),
                        "description": f"Update WBE: {branch_wbe.machine_type}",
                        "revenue_change": float(
                            (branch_wbe.revenue_allocation or 0)
                            - (main_wbe.revenue_allocation or 0)
                        ),
                    }
                )
                total_revenue_change += Decimal(
                    str(
                        (branch_wbe.revenue_allocation or 0)
                        - (main_wbe.revenue_allocation or 0)
                    )
                )

    # Find deletes
    for main_wbe in main_wbes:
        if main_wbe.entity_id not in branch_wbe_map:
            # Check if deleted in branch
            deleted_branch_wbe = session.exec(
                select(WBE)
                .where(WBE.entity_id == main_wbe.entity_id)
                .where(WBE.branch == branch)
                .where(WBE.status == "deleted")
            ).first()

            if deleted_branch_wbe:
                deletes.append(
                    {
                        "type": "wbe",
                        "entity_id": str(main_wbe.entity_id),
                        "description": f"Delete WBE: {main_wbe.machine_type}",
                        "revenue_change": -float(main_wbe.revenue_allocation or 0),
                    }
                )
                total_revenue_change -= Decimal(str(main_wbe.revenue_allocation or 0))

    # Similar logic for CostElements
    branch_wbe_entity_ids = {wbe.entity_id for wbe in branch_wbes}
    branch_cost_elements_query = (
        select(CostElement)
        .join(WBE, CostElement.wbe_id == WBE.wbe_id)
        .where(WBE.entity_id.in_(list(branch_wbe_entity_ids)))  # type: ignore[attr-defined]
        .where(WBE.project_id == project_id)
        .where(WBE.branch == branch)
    )
    branch_cost_elements_query = apply_branch_filters(
        branch_cost_elements_query, CostElement, branch=branch, include_deleted=False
    )
    branch_cost_elements = session.exec(branch_cost_elements_query).all()

    main_wbe_entity_ids = {wbe.entity_id for wbe in main_wbes}
    main_cost_elements_query = (
        select(CostElement)
        .join(WBE, CostElement.wbe_id == WBE.wbe_id)
        .where(WBE.entity_id.in_(list(main_wbe_entity_ids)))  # type: ignore[attr-defined]
        .where(WBE.project_id == project_id)
        .where(WBE.branch == base_branch)
    )
    main_cost_elements_query = apply_branch_filters(
        main_cost_elements_query, CostElement, branch=base_branch, include_deleted=False
    )
    main_cost_elements = session.exec(main_cost_elements_query).all()

    main_ce_map = {ce.entity_id: ce for ce in main_cost_elements}
    branch_ce_map = {ce.entity_id: ce for ce in branch_cost_elements}

    for branch_ce in branch_cost_elements:
        main_ce = main_ce_map.get(branch_ce.entity_id)

        if main_ce is None:
            creates.append(
                {
                    "type": "cost_element",
                    "entity_id": str(branch_ce.entity_id),
                    "description": f"Create Cost Element: {branch_ce.department_name}",
                    "budget_change": float(branch_ce.budget_bac or 0),
                    "revenue_change": float(branch_ce.revenue_plan or 0),
                }
            )
            total_budget_change += Decimal(str(branch_ce.budget_bac or 0))
            total_revenue_change += Decimal(str(branch_ce.revenue_plan or 0))
        else:
            if (
                branch_ce.budget_bac != main_ce.budget_bac
                or branch_ce.revenue_plan != main_ce.revenue_plan
            ):
                updates.append(
                    {
                        "type": "cost_element",
                        "entity_id": str(branch_ce.entity_id),
                        "description": f"Update Cost Element: {branch_ce.department_name}",
                        "budget_change": float(
                            (branch_ce.budget_bac or 0) - (main_ce.budget_bac or 0)
                        ),
                        "revenue_change": float(
                            (branch_ce.revenue_plan or 0) - (main_ce.revenue_plan or 0)
                        ),
                    }
                )
                total_budget_change += Decimal(
                    str((branch_ce.budget_bac or 0) - (main_ce.budget_bac or 0))
                )
                total_revenue_change += Decimal(
                    str((branch_ce.revenue_plan or 0) - (main_ce.revenue_plan or 0))
                )

    for main_ce in main_cost_elements:
        if main_ce.entity_id not in branch_ce_map:
            deleted_branch_ce = session.exec(
                select(CostElement)
                .where(CostElement.entity_id == main_ce.entity_id)
                .where(CostElement.branch == branch)
                .where(CostElement.status == "deleted")
            ).first()

            if deleted_branch_ce:
                deletes.append(
                    {
                        "type": "cost_element",
                        "entity_id": str(main_ce.entity_id),
                        "description": f"Delete Cost Element: {main_ce.department_name}",
                        "budget_change": -float(main_ce.budget_bac or 0),
                        "revenue_change": -float(main_ce.revenue_plan or 0),
                    }
                )
                total_budget_change -= Decimal(str(main_ce.budget_bac or 0))
                total_revenue_change -= Decimal(str(main_ce.revenue_plan or 0))

    return {
        "project_id": str(project_id),
        "branch": branch,
        "base_branch": base_branch,
        "summary": {
            "creates_count": len(creates),
            "updates_count": len(updates),
            "deletes_count": len(deletes),
            "total_budget_change": float(total_budget_change),
            "total_revenue_change": float(total_revenue_change),
        },
        "creates": creates,
        "updates": updates,
        "deletes": deletes,
    }
