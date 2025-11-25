"""Change Order API routes."""

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlmodel import select

from app.api.deps import CurrentUser, SessionDep
from app.models import (
    BaselineLog,
    ChangeOrder,
    ChangeOrderCreate,
    ChangeOrderPublic,
    ChangeOrderUpdate,
)
from app.services.branch_filtering import apply_status_filters
from app.services.branch_service import BranchService
from app.services.entity_versioning import (
    create_entity_with_version,
    soft_delete_entity,
    update_entity_with_version,
)


class ChangeOrderTransitionRequest(BaseModel):
    """Request schema for change order status transition."""

    workflow_status: str
    approved_by_id: uuid.UUID | None = None
    implemented_by_id: uuid.UUID | None = None


router = APIRouter(
    prefix="/projects/{project_id}/change-orders", tags=["change-orders"]
)


@router.post("/", response_model=ChangeOrderPublic)
def create_change_order(
    *,
    session: SessionDep,
    _current_user: CurrentUser,
    project_id: uuid.UUID,
    change_order_in: ChangeOrderCreate,
) -> Any:
    """
    Create a new change order and automatically create a branch for it.
    """
    # Validate project_id matches
    if change_order_in.project_id != project_id:
        raise HTTPException(
            status_code=400, detail="Project ID in path does not match request body"
        )

    # Auto-generate change order number if not provided
    if not change_order_in.change_order_number:
        # Generate short project ID
        project_short_id = str(project_id).replace("-", "")[:6].upper()

        # Get next progressive number for this project
        existing_cos = session.exec(
            select(ChangeOrder).where(ChangeOrder.project_id == project_id)
        ).all()
        next_number = len(existing_cos) + 1

        # Format: CO-{PROJECT_SHORT_ID}-{PROGRESSIVE_NUMBER}
        change_order_in.change_order_number = f"CO-{project_short_id}-{next_number:03d}"

    # Create change order
    change_order = ChangeOrder.model_validate(change_order_in)

    # Create entity with version first (saves to DB)
    change_order = create_entity_with_version(
        session=session,
        entity=change_order,
        entity_type="changeorder",
        entity_id=str(change_order.change_order_id),
    )

    # Flush to ensure change order is in database
    session.flush()

    # Create branch for this change order (now it exists in DB)
    branch_name = BranchService.create_branch(
        session=session, change_order_id=change_order.change_order_id
    )
    change_order.branch = branch_name
    session.add(change_order)

    session.commit()
    session.refresh(change_order)
    return change_order


@router.get("/", response_model=list[ChangeOrderPublic])
def list_change_orders(
    *,
    session: SessionDep,
    _current_user: CurrentUser,
    project_id: uuid.UUID,
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """
    List all change orders for a project (active only).
    """
    statement = select(ChangeOrder).where(ChangeOrder.project_id == project_id)
    statement = apply_status_filters(statement, ChangeOrder, status="active")
    statement = statement.offset(skip).limit(limit)
    change_orders = session.exec(statement).all()
    return change_orders


@router.get("/{change_order_id}", response_model=ChangeOrderPublic)
def read_change_order(
    *,
    session: SessionDep,
    _current_user: CurrentUser,
    project_id: uuid.UUID,
    change_order_id: uuid.UUID,
) -> Any:
    """
    Get change order by ID (active only).
    """
    statement = (
        select(ChangeOrder)
        .where(ChangeOrder.change_order_id == change_order_id)
        .where(ChangeOrder.project_id == project_id)
    )
    statement = apply_status_filters(statement, ChangeOrder, status="active")
    change_order = session.exec(statement).first()
    if not change_order:
        raise HTTPException(status_code=404, detail="Change order not found")
    return change_order


@router.put("/{change_order_id}", response_model=ChangeOrderPublic)
def update_change_order(
    *,
    session: SessionDep,
    _current_user: CurrentUser,
    project_id: uuid.UUID,
    change_order_id: uuid.UUID,
    change_order_in: ChangeOrderUpdate,
) -> Any:
    """
    Update a change order. Only allowed when workflow_status is 'design'.
    Creates a new version.
    """
    # Get current change order
    statement = (
        select(ChangeOrder)
        .where(ChangeOrder.change_order_id == change_order_id)
        .where(ChangeOrder.project_id == project_id)
    )
    statement = apply_status_filters(statement, ChangeOrder, status="active")
    current_co = session.exec(statement).first()
    if not current_co:
        raise HTTPException(status_code=404, detail="Change order not found")

    # Check if cancellation is requested (allowed from any status)
    is_cancellation = (
        change_order_in.workflow_status == "cancelled"
        and current_co.workflow_status != "cancelled"
    )

    # Validate that change order is in 'design' status (only editable in design)
    # Exception: cancellation is allowed from any status
    if current_co.workflow_status != "design" and not is_cancellation:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot update change order in '{current_co.workflow_status}' status. Only 'design' status can be edited (or cancelled from any status).",
        )

    # Cancel change order - soft delete the branch BEFORE creating new version
    if is_cancellation and current_co.branch:
        BranchService.delete_branch(session=session, branch=current_co.branch)
        session.flush()  # Ensure branch deletion is applied

    # Update change order
    update_dict = change_order_in.model_dump(exclude_unset=True)
    try:
        change_order = update_entity_with_version(
            session=session,
            entity_class=ChangeOrder,
            entity_id=change_order_id,
            update_data=update_dict,
            entity_type="changeorder",
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Change order not found") from exc

    session.commit()
    session.refresh(change_order)
    return change_order


@router.delete("/{change_order_id}")
def delete_change_order(
    *,
    session: SessionDep,
    _current_user: CurrentUser,
    project_id: uuid.UUID,
    change_order_id: uuid.UUID,
) -> Any:
    """
    Soft delete a change order and its associated branch.
    """
    statement = (
        select(ChangeOrder)
        .where(ChangeOrder.change_order_id == change_order_id)
        .where(ChangeOrder.project_id == project_id)
    )
    statement = apply_status_filters(statement, ChangeOrder, status="active")
    change_order = session.exec(statement).first()
    if not change_order:
        raise HTTPException(status_code=404, detail="Change order not found")

    # Soft delete the branch if it exists
    if change_order.branch:
        BranchService.delete_branch(session=session, branch=change_order.branch)

    # Soft delete the change order
    soft_delete_entity(
        session=session,
        entity_class=ChangeOrder,
        entity_id=change_order_id,
        entity_type="changeorder",
    )

    session.commit()
    return {"message": "Change order deleted"}


@router.post("/{change_order_id}/transition", response_model=ChangeOrderPublic)
def transition_change_order_status(
    *,
    session: SessionDep,
    _current_user: CurrentUser,
    project_id: uuid.UUID,
    change_order_id: uuid.UUID,
    transition_request: ChangeOrderTransitionRequest,
) -> Any:
    """
    Transition change order workflow status.

    Valid transitions:
    - design → approve: Creates 'before' baseline and locks branch
    - approve → execute: Merges branch into main and creates 'after' baseline

    Args:
        transition_request: Transition request with workflow_status and user IDs
    """
    # Get current change order
    statement = (
        select(ChangeOrder)
        .where(ChangeOrder.change_order_id == change_order_id)
        .where(ChangeOrder.project_id == project_id)
    )
    statement = apply_status_filters(statement, ChangeOrder, status="active")
    change_order = session.exec(statement).first()
    if not change_order:
        raise HTTPException(status_code=404, detail="Change order not found")

    current_status = change_order.workflow_status
    workflow_status = transition_request.workflow_status
    approved_by_id = transition_request.approved_by_id
    implemented_by_id = transition_request.implemented_by_id

    # Validate transition
    if workflow_status == "approve":
        if current_status != "design":
            raise HTTPException(
                status_code=400,
                detail=f"Cannot transition to 'approve' from '{current_status}'. Must be in 'design' status.",
            )
        if not approved_by_id:
            raise HTTPException(
                status_code=400, detail="approved_by_id is required for approval"
            )
        change_order.approved_by_id = approved_by_id
        change_order.approved_at = datetime.now(timezone.utc)
        change_order.workflow_status = "approve"

        # Create 'before' baseline snapshot
        from app.api.routes.baseline_logs import (
            create_baseline_cost_elements_for_baseline_log,
        )

        baseline_log = BaselineLog(
            project_id=project_id,
            baseline_type="combined",
            baseline_date=datetime.now(timezone.utc).date(),
            milestone_type="change_order_approval",
            description=f"Before baseline for change order {change_order.change_order_number}",
            is_pmb=False,
            created_by_id=_current_user.id,
        )
        baseline_log = create_entity_with_version(
            session=session,
            entity=baseline_log,
            entity_type="baseline_log",
            entity_id=str(baseline_log.baseline_id),
        )
        session.flush()

        create_baseline_cost_elements_for_baseline_log(
            session=session,
            baseline_log=baseline_log,
            created_by_id=_current_user.id,
        )

    elif workflow_status == "execute":
        if current_status != "approve":
            raise HTTPException(
                status_code=400,
                detail=f"Cannot transition to 'execute' from '{current_status}'. Must be in 'approve' status.",
            )
        if not implemented_by_id:
            raise HTTPException(
                status_code=400, detail="implemented_by_id is required for execution"
            )
        if not change_order.branch:
            raise HTTPException(
                status_code=400, detail="Change order has no associated branch"
            )

        # Merge branch into main
        BranchService.merge_branch(
            session=session,
            branch=change_order.branch,
            change_order_id=change_order_id,
        )

        change_order.implemented_by_id = implemented_by_id
        change_order.implemented_at = datetime.now(timezone.utc)
        change_order.workflow_status = "execute"

        # Create 'after' baseline snapshot (after merge)
        from app.api.routes.baseline_logs import (
            create_baseline_cost_elements_for_baseline_log,
        )

        baseline_log = BaselineLog(
            project_id=project_id,
            baseline_type="combined",
            baseline_date=datetime.now(timezone.utc).date(),
            milestone_type="change_order_execution",
            description=f"After baseline for change order {change_order.change_order_number}",
            is_pmb=False,
            created_by_id=_current_user.id,
        )
        baseline_log = create_entity_with_version(
            session=session,
            entity=baseline_log,
            entity_type="baseline_log",
            entity_id=str(baseline_log.baseline_id),
        )
        session.flush()

        create_baseline_cost_elements_for_baseline_log(
            session=session,
            baseline_log=baseline_log,
            created_by_id=_current_user.id,
        )

    else:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid workflow_status transition: '{workflow_status}'. Valid transitions: design→approve, approve→execute",
        )

    session.add(change_order)
    session.commit()
    session.refresh(change_order)
    return change_order
