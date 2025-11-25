"""Change Order Line Items API routes."""

import uuid
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app.api.deps import CurrentUser, SessionDep
from app.models import WBE, ChangeOrder, CostElement
from app.services.branch_filtering import apply_branch_filters, apply_status_filters

router = APIRouter(
    prefix="/projects/{project_id}/change-orders/{change_order_id}/line-items",
    tags=["change-order-line-items"],
)


class ChangeOrderLineItemPublic(BaseModel):
    """Public schema for change order line item."""

    operation_type: str  # "create", "update", "delete"
    target_type: str  # "wbe", "cost_element"
    branch_target_id: uuid.UUID | None = None  # Entity ID in branch
    main_target_id: uuid.UUID | None = None  # Entity ID in main (for update/delete)
    budget_change: Decimal | None = None
    revenue_change: Decimal | None = None
    description: str | None = None


def _compare_branch_with_main(
    session: Session, branch: str, project_id: uuid.UUID
) -> list[ChangeOrderLineItemPublic]:
    """
    Compare branch with main to generate line items.

    Returns list of line items representing differences between branch and main.
    """
    line_items: list[ChangeOrderLineItemPublic] = []

    # Get all active WBEs in branch
    branch_wbes = session.exec(
        apply_branch_filters(
            select(WBE).where(WBE.project_id == project_id),
            WBE,
            branch=branch,
            include_deleted=False,
        )
    ).all()

    # Get all active WBEs in main
    main_wbes = session.exec(
        apply_branch_filters(
            select(WBE).where(WBE.project_id == project_id),
            WBE,
            branch="main",
            include_deleted=False,
        )
    ).all()

    # Create map of entity_id -> main WBE
    main_wbe_map = {wbe.entity_id: wbe for wbe in main_wbes}

    # Compare branch WBEs with main
    for branch_wbe in branch_wbes:
        main_wbe = main_wbe_map.get(branch_wbe.entity_id)

        if main_wbe is None:
            # CREATE operation - new WBE in branch
            line_items.append(
                ChangeOrderLineItemPublic(
                    operation_type="create",
                    target_type="wbe",
                    branch_target_id=branch_wbe.entity_id,
                    main_target_id=None,
                    budget_change=None,  # WBE doesn't have budget_bac
                    revenue_change=Decimal(str(branch_wbe.revenue_allocation or 0)),
                    description=f"Create WBE: {branch_wbe.machine_type}",
                )
            )
        else:
            # UPDATE operation - WBE exists in both, check for changes
            revenue_change = Decimal(str(branch_wbe.revenue_allocation or 0)) - Decimal(
                str(main_wbe.revenue_allocation or 0)
            )
            if revenue_change != 0 or branch_wbe.machine_type != main_wbe.machine_type:
                line_items.append(
                    ChangeOrderLineItemPublic(
                        operation_type="update",
                        target_type="wbe",
                        branch_target_id=branch_wbe.entity_id,
                        main_target_id=main_wbe.entity_id,
                        budget_change=None,
                        revenue_change=revenue_change,
                        description=f"Update WBE: {branch_wbe.machine_type}",
                    )
                )

    # Check for DELETED WBEs (exist in main but not in branch)
    branch_wbe_entity_ids = {wbe.entity_id for wbe in branch_wbes}
    for main_wbe in main_wbes:
        if main_wbe.entity_id not in branch_wbe_entity_ids:
            # Check if there's a deleted version in branch
            deleted_branch_wbe = session.exec(
                select(WBE)
                .where(WBE.entity_id == main_wbe.entity_id)
                .where(WBE.branch == branch)
                .where(WBE.status == "deleted")
            ).first()

            if deleted_branch_wbe:
                line_items.append(
                    ChangeOrderLineItemPublic(
                        operation_type="delete",
                        target_type="wbe",
                        branch_target_id=main_wbe.entity_id,
                        main_target_id=main_wbe.entity_id,
                        budget_change=None,
                        revenue_change=-Decimal(str(main_wbe.revenue_allocation or 0)),
                        description=f"Delete WBE: {main_wbe.machine_type}",
                    )
                )

    # Get all active CostElements in branch
    # Join with WBE to filter by WBE entity_id (not wbe_id, since WBEs can have multiple versions)
    branch_wbe_entity_ids = {wbe.entity_id for wbe in branch_wbes}
    branch_cost_elements_query = (
        select(CostElement)
        .join(WBE, CostElement.wbe_id == WBE.wbe_id)
        .where(WBE.entity_id.in_(list(branch_wbe_entity_ids)))  # type: ignore[attr-defined]
        .where(WBE.project_id == project_id)
        .where(WBE.branch == branch)  # Ensure WBE is from the correct branch
    )
    branch_cost_elements_query = apply_branch_filters(
        branch_cost_elements_query, CostElement, branch=branch, include_deleted=False
    )
    branch_cost_elements = session.exec(branch_cost_elements_query).all()

    # Get all active CostElements in main
    main_wbe_entity_ids = {wbe.entity_id for wbe in main_wbes}
    main_cost_elements_query = (
        select(CostElement)
        .join(WBE, CostElement.wbe_id == WBE.wbe_id)
        .where(WBE.entity_id.in_(list(main_wbe_entity_ids)))  # type: ignore[attr-defined]
        .where(WBE.project_id == project_id)
        .where(WBE.branch == "main")  # Ensure WBE is from main branch
    )
    main_cost_elements_query = apply_branch_filters(
        main_cost_elements_query, CostElement, branch="main", include_deleted=False
    )
    main_cost_elements = session.exec(main_cost_elements_query).all()

    # Create map of entity_id -> main CostElement
    main_ce_map = {ce.entity_id: ce for ce in main_cost_elements}

    # Compare branch CostElements with main
    for branch_ce in branch_cost_elements:
        main_ce = main_ce_map.get(branch_ce.entity_id)

        if main_ce is None:
            # CREATE operation - new CostElement in branch
            line_items.append(
                ChangeOrderLineItemPublic(
                    operation_type="create",
                    target_type="cost_element",
                    branch_target_id=branch_ce.entity_id,
                    main_target_id=None,
                    budget_change=Decimal(str(branch_ce.budget_bac or 0)),
                    revenue_change=Decimal(str(branch_ce.revenue_plan or 0)),
                    description=f"Create CostElement: {branch_ce.department_name}",
                )
            )
        else:
            # UPDATE operation - CostElement exists in both, check for changes
            budget_change = Decimal(str(branch_ce.budget_bac or 0)) - Decimal(
                str(main_ce.budget_bac or 0)
            )
            revenue_change = Decimal(str(branch_ce.revenue_plan or 0)) - Decimal(
                str(main_ce.revenue_plan or 0)
            )
            if budget_change != 0 or revenue_change != 0:
                line_items.append(
                    ChangeOrderLineItemPublic(
                        operation_type="update",
                        target_type="cost_element",
                        branch_target_id=branch_ce.entity_id,
                        main_target_id=main_ce.entity_id,
                        budget_change=budget_change,
                        revenue_change=revenue_change,
                        description=f"Update CostElement: {branch_ce.department_name}",
                    )
                )

    # Check for DELETED CostElements (exist in main but not in branch)
    branch_ce_entity_ids = {ce.entity_id for ce in branch_cost_elements}
    for main_ce in main_cost_elements:
        if main_ce.entity_id not in branch_ce_entity_ids:
            # Check if there's a deleted version in branch
            deleted_branch_ce = session.exec(
                select(CostElement)
                .where(CostElement.entity_id == main_ce.entity_id)
                .where(CostElement.branch == branch)
                .where(CostElement.status == "deleted")
            ).first()

            if deleted_branch_ce:
                line_items.append(
                    ChangeOrderLineItemPublic(
                        operation_type="delete",
                        target_type="cost_element",
                        branch_target_id=main_ce.entity_id,
                        main_target_id=main_ce.entity_id,
                        budget_change=-Decimal(str(main_ce.budget_bac or 0)),
                        revenue_change=-Decimal(str(main_ce.revenue_plan or 0)),
                        description=f"Delete CostElement: {main_ce.department_name}",
                    )
                )

    return line_items


@router.get("/", response_model=list[ChangeOrderLineItemPublic])
def list_change_order_line_items(
    *,
    session: SessionDep,
    _current_user: CurrentUser,
    project_id: uuid.UUID,
    change_order_id: uuid.UUID,
) -> Any:
    """
    List all line items for a change order.

    Line items are auto-generated from comparing the change order's branch
    with the main branch. This endpoint dynamically generates line items
    based on the current state of the branch.
    """
    # Get change order
    statement = (
        select(ChangeOrder)
        .where(ChangeOrder.change_order_id == change_order_id)
        .where(ChangeOrder.project_id == project_id)
    )
    statement = apply_status_filters(statement, ChangeOrder, status="active")
    change_order = session.exec(statement).first()
    if not change_order:
        raise HTTPException(status_code=404, detail="Change order not found")

    if not change_order.branch:
        # No branch means no line items
        return []

    # Generate line items from branch comparison
    line_items = _compare_branch_with_main(
        session=session, branch=change_order.branch, project_id=project_id
    )

    return line_items
