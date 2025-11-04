import uuid
from datetime import date
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from sqlmodel import Session, func, select

from app.api.deps import CurrentUser, SessionDep
from app.models import (
    WBE,
    BudgetAllocation,
    BudgetAllocationCreate,
    CostElement,
    CostElementCreate,
    CostElementPublic,
    CostElementsPublic,
    CostElementType,
    CostElementUpdate,
    Message,
)

router = APIRouter(prefix="/cost-elements", tags=["cost-elements"])


def create_budget_allocation_for_cost_element(
    session: Session,
    cost_element: CostElement,
    allocation_type: str,
    created_by_id: uuid.UUID,
) -> BudgetAllocation:
    """
    Create a BudgetAllocation record for a CostElement.

    Args:
        session: Database session
        cost_element: The CostElement to create allocation for
        allocation_type: Type of allocation ("initial" or "update")
        created_by_id: ID of user creating the allocation

    Returns:
        Created BudgetAllocation record
    """
    budget_allocation_in = BudgetAllocationCreate(
        cost_element_id=cost_element.cost_element_id,
        allocation_date=date.today(),
        budget_amount=cost_element.budget_bac,
        revenue_amount=cost_element.revenue_plan,
        allocation_type=allocation_type,
        description=f"{allocation_type.capitalize()} budget allocation",
        created_by_id=created_by_id,
    )
    budget_allocation = BudgetAllocation.model_validate(budget_allocation_in)
    session.add(budget_allocation)
    return budget_allocation


def validate_revenue_plan_against_wbe_limit(
    session: Session,
    wbe_id: uuid.UUID,
    new_revenue_plan: Decimal,
    exclude_cost_element_id: uuid.UUID | None = None,
) -> None:
    """
    Validate that sum of cost element revenue_plan does not exceed WBE revenue_allocation.
    Raises HTTPException(400) if validation fails.

    Args:
        session: Database session
        wbe_id: ID of the WBE to validate against
        new_revenue_plan: The new revenue_plan value being set
        exclude_cost_element_id: Cost element ID to exclude from the sum (for updates)
    """
    # Get WBE and its revenue_allocation
    wbe = session.get(WBE, wbe_id)
    if not wbe:
        raise HTTPException(status_code=400, detail="WBE not found")

    # Query all cost elements for this WBE (excluding the one being updated if specified)
    statement = select(CostElement).where(CostElement.wbe_id == wbe_id)
    if exclude_cost_element_id:
        statement = statement.where(
            CostElement.cost_element_id != exclude_cost_element_id
        )

    cost_elements = session.exec(statement).all()

    # Sum existing revenue_plan values
    total_revenue_plan = sum(ce.revenue_plan for ce in cost_elements)

    # Add new_revenue_plan
    new_total = total_revenue_plan + new_revenue_plan

    # Compare against wbe.revenue_allocation
    if new_total > wbe.revenue_allocation:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Total revenue plan for cost elements (€{new_total:,.2f}) "
                f"exceeds WBE revenue allocation (€{wbe.revenue_allocation:,.2f})"
            ),
        )


@router.get("/", response_model=CostElementsPublic)
def read_cost_elements(
    session: SessionDep,
    _current_user: CurrentUser,
    skip: int = 0,
    limit: int = 100,
    wbe_id: uuid.UUID | None = Query(default=None, description="Filter by WBE ID"),
) -> Any:
    """
    Retrieve cost elements.
    """
    if wbe_id:
        # Filter by WBE
        count_statement = (
            select(func.count())
            .select_from(CostElement)
            .where(CostElement.wbe_id == wbe_id)
        )
        count = session.exec(count_statement).one()
        statement = (
            select(CostElement)
            .where(CostElement.wbe_id == wbe_id)
            .offset(skip)
            .limit(limit)
        )
    else:
        # Get all
        count_statement = select(func.count()).select_from(CostElement)
        count = session.exec(count_statement).one()
        statement = select(CostElement).offset(skip).limit(limit)

    cost_elements = session.exec(statement).all()
    return CostElementsPublic(data=cost_elements, count=count)


@router.get("/{id}", response_model=CostElementPublic)
def read_cost_element(
    session: SessionDep, _current_user: CurrentUser, id: uuid.UUID
) -> Any:
    """
    Get cost element by ID.
    """
    cost_element = session.get(CostElement, id)
    if not cost_element:
        raise HTTPException(status_code=404, detail="Cost element not found")
    return cost_element


@router.post("/", response_model=CostElementPublic)
def create_cost_element(
    *,
    session: SessionDep,
    _current_user: CurrentUser,
    cost_element_in: CostElementCreate,
) -> Any:
    """
    Create new cost element.
    """
    # Validate that WBE exists
    wbe = session.get(WBE, cost_element_in.wbe_id)
    if not wbe:
        raise HTTPException(status_code=400, detail="WBE not found")

    # Validate that cost element type exists
    cost_element_type = session.get(
        CostElementType, cost_element_in.cost_element_type_id
    )
    if not cost_element_type:
        raise HTTPException(status_code=400, detail="Cost element type not found")

    # Validate revenue_plan does not exceed WBE revenue_allocation
    validate_revenue_plan_against_wbe_limit(
        session=session,
        wbe_id=cost_element_in.wbe_id,
        new_revenue_plan=cost_element_in.revenue_plan,
    )

    cost_element = CostElement.model_validate(cost_element_in)
    session.add(cost_element)
    session.flush()  # Flush to get cost_element_id without committing

    # Create initial BudgetAllocation record
    create_budget_allocation_for_cost_element(
        session=session,
        cost_element=cost_element,
        allocation_type="initial",
        created_by_id=_current_user.id,
    )

    session.commit()
    session.refresh(cost_element)
    return cost_element


@router.put("/{id}", response_model=CostElementPublic)
def update_cost_element(
    *,
    session: SessionDep,
    _current_user: CurrentUser,
    id: uuid.UUID,
    cost_element_in: CostElementUpdate,
) -> Any:
    """
    Update a cost element.
    """
    cost_element = session.get(CostElement, id)
    if not cost_element:
        raise HTTPException(status_code=404, detail="Cost element not found")

    update_dict = cost_element_in.model_dump(exclude_unset=True)

    # Validate revenue_plan if it's being updated
    if "revenue_plan" in update_dict:
        new_revenue_plan = update_dict["revenue_plan"]
        validate_revenue_plan_against_wbe_limit(
            session=session,
            wbe_id=cost_element.wbe_id,
            new_revenue_plan=new_revenue_plan,
            exclude_cost_element_id=cost_element.cost_element_id,
        )

    # Check if budget_bac or revenue_plan are being updated
    budget_changed = "budget_bac" in update_dict
    revenue_changed = "revenue_plan" in update_dict

    # Store old values to check if they actually changed
    old_budget_bac = cost_element.budget_bac
    old_revenue_plan = cost_element.revenue_plan

    cost_element.sqlmodel_update(update_dict)
    session.add(cost_element)
    session.flush()  # Flush to get updated values without committing

    # Create new BudgetAllocation if budget_bac or revenue_plan changed
    if budget_changed or revenue_changed:
        # Check if values actually changed (to handle cases where same value is set)
        if (budget_changed and cost_element.budget_bac != old_budget_bac) or (
            revenue_changed and cost_element.revenue_plan != old_revenue_plan
        ):
            create_budget_allocation_for_cost_element(
                session=session,
                cost_element=cost_element,
                allocation_type="update",
                created_by_id=_current_user.id,
            )

    session.commit()
    session.refresh(cost_element)
    return cost_element


@router.delete("/{id}")
def delete_cost_element(
    session: SessionDep, _current_user: CurrentUser, id: uuid.UUID
) -> Message:
    """
    Delete a cost element.
    """
    cost_element = session.get(CostElement, id)
    if not cost_element:
        raise HTTPException(status_code=404, detail="Cost element not found")
    session.delete(cost_element)
    session.commit()
    return Message(message="Cost element deleted successfully")
