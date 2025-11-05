"""Cost Registrations API routes."""
import uuid
from datetime import date
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlmodel import Session, func, select

from app.api.deps import CurrentUser, SessionDep
from app.models import (
    CostElement,
    CostElementSchedule,
    CostRegistration,
    CostRegistrationCreate,
    CostRegistrationPublic,
    CostRegistrationsPublic,
    CostRegistrationUpdate,
    Message,
)

router = APIRouter(prefix="/cost-registrations", tags=["cost-registrations"])

# Valid cost categories (from cost categories endpoint)
VALID_COST_CATEGORIES = ["labor", "materials", "subcontractors"]


def validate_cost_element_exists(
    session: Session,
    cost_element_id: uuid.UUID,
) -> CostElement:
    """
    Validate that cost element exists.
    Raises HTTPException(400) if cost element not found.

    Args:
        session: Database session
        cost_element_id: ID of the cost element to validate

    Returns:
        CostElement if found
    """
    cost_element = session.get(CostElement, cost_element_id)
    if not cost_element:
        raise HTTPException(status_code=400, detail="Cost element not found")
    return cost_element


def validate_cost_category(cost_category: str) -> None:
    """
    Validate that cost category is valid.
    Raises HTTPException(400) if category is invalid.

    Args:
        cost_category: Cost category to validate
    """
    if cost_category not in VALID_COST_CATEGORIES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid cost category. Must be one of: {', '.join(VALID_COST_CATEGORIES)}",
        )


def validate_amount(amount: Decimal) -> None:
    """
    Validate that amount is positive.
    Raises HTTPException(400) if amount is invalid.

    Args:
        amount: Amount to validate
    """
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be greater than zero")


def get_cost_element_schedule(
    session: Session,
    cost_element_id: uuid.UUID,
) -> CostElementSchedule | None:
    """
    Get the latest schedule for a cost element.
    Returns None if no schedule exists.

    Args:
        session: Database session
        cost_element_id: ID of the cost element

    Returns:
        CostElementSchedule or None
    """
    statement = select(CostElementSchedule).where(
        CostElementSchedule.cost_element_id == cost_element_id
    )
    return session.exec(statement).first()


def validate_registration_date(
    session: Session,
    cost_element_id: uuid.UUID,
    registration_date: date,
) -> dict[str, str] | None:
    """
    Validate registration date against cost element schedule.

    Validation rules:
    - If schedule exists and registration_date < start_date: raises HTTPException(400)
    - If schedule exists and registration_date > end_date: returns warning dict
    - If schedule exists and date is within bounds: returns None (valid)
    - If no schedule exists: returns None (allow registration)

    Args:
        session: Database session
        cost_element_id: ID of the cost element
        registration_date: Date to validate

    Returns:
        dict with warning message if date after end_date, None otherwise
        Raises HTTPException(400) if date before start_date

    Raises:
        HTTPException: If registration_date is before schedule start_date
    """
    schedule = get_cost_element_schedule(session, cost_element_id)

    # If no schedule exists, allow registration (no validation)
    if schedule is None:
        return None

    # Check if date is before start_date (hard block)
    if registration_date < schedule.start_date:
        raise HTTPException(
            status_code=400,
            detail=f"Registration date ({registration_date.isoformat()}) cannot be before schedule start date ({schedule.start_date.isoformat()})",
        )

    # Check if date is after end_date (warning but allow)
    if registration_date > schedule.end_date:
        return {
            "warning": f"Registration date ({registration_date.isoformat()}) is after schedule end date ({schedule.end_date.isoformat()})",
        }

    # Date is within bounds (valid)
    return None


@router.get("/", response_model=CostRegistrationsPublic)
def read_cost_registrations(
    session: SessionDep,
    _current_user: CurrentUser,
    cost_element_id: uuid.UUID | None = Query(
        default=None, description="Filter by cost element ID"
    ),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
) -> Any:
    """
    Retrieve cost registrations.
    Optionally filter by cost_element_id.
    """
    statement = select(CostRegistration)
    count_statement = select(func.count()).select_from(CostRegistration)

    if cost_element_id:
        statement = statement.where(CostRegistration.cost_element_id == cost_element_id)
        count_statement = count_statement.where(
            CostRegistration.cost_element_id == cost_element_id
        )

    # Get count
    count = session.exec(count_statement).one()

    # Apply pagination
    statement = statement.offset(skip).limit(limit)
    cost_registrations = session.exec(statement).all()

    return CostRegistrationsPublic(
        data=[CostRegistrationPublic.model_validate(cr) for cr in cost_registrations],
        count=count,
    )


@router.get("/{id}", response_model=CostRegistrationPublic)
def read_cost_registration(
    session: SessionDep, _current_user: CurrentUser, id: uuid.UUID
) -> Any:
    """
    Get a single cost registration by ID.
    """
    cost_registration = session.get(CostRegistration, id)
    if not cost_registration:
        raise HTTPException(status_code=404, detail="Cost registration not found")
    return cost_registration


@router.post("/", response_model=CostRegistrationPublic)
def create_cost_registration(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    cost_registration_in: CostRegistrationCreate,
) -> Any:
    """
    Create a new cost registration.
    """
    # Validate cost element exists
    validate_cost_element_exists(session, cost_registration_in.cost_element_id)

    # Validate cost category
    validate_cost_category(cost_registration_in.cost_category)

    # Validate amount
    validate_amount(cost_registration_in.amount)

    # Validate registration date against schedule
    warning = validate_registration_date(
        session,
        cost_registration_in.cost_element_id,
        cost_registration_in.registration_date,
    )

    # Create cost registration with created_by_id from current user
    cost_registration_data = cost_registration_in.model_dump()
    cost_registration_data["created_by_id"] = current_user.id
    cost_registration = CostRegistration.model_validate(cost_registration_data)
    session.add(cost_registration)
    session.commit()
    session.refresh(cost_registration)

    # Convert to public schema and add warning if present
    result = CostRegistrationPublic.model_validate(cost_registration)
    if warning:
        # Add warning to response by converting to dict and adding warning
        # Use mode='json' to serialize dates properly
        # Return as JSONResponse to bypass response_model validation
        result_dict = result.model_dump(mode="json")
        result_dict["warning"] = warning["warning"]
        return JSONResponse(content=result_dict)

    return result


@router.put("/{id}", response_model=CostRegistrationPublic)
def update_cost_registration(
    *,
    session: SessionDep,
    _current_user: CurrentUser,
    id: uuid.UUID,
    cost_registration_in: CostRegistrationUpdate,
) -> Any:
    """
    Update a cost registration.
    """
    cost_registration = session.get(CostRegistration, id)
    if not cost_registration:
        raise HTTPException(status_code=404, detail="Cost registration not found")

    update_dict = cost_registration_in.model_dump(exclude_unset=True)

    # Validate cost category if being updated
    if "cost_category" in update_dict:
        validate_cost_category(update_dict["cost_category"])

    # Validate amount if being updated
    if "amount" in update_dict:
        validate_amount(update_dict["amount"])

    # Validate cost element if being updated
    if "cost_element_id" in update_dict:
        validate_cost_element_exists(session, update_dict["cost_element_id"])

    # Validate registration date if being updated
    # Use updated date if provided, otherwise use existing date
    registration_date = update_dict.get(
        "registration_date", cost_registration.registration_date
    )
    # Use updated cost_element_id if provided, otherwise use existing cost_element_id
    cost_element_id = update_dict.get(
        "cost_element_id", cost_registration.cost_element_id
    )

    warning = validate_registration_date(
        session,
        cost_element_id,
        registration_date,
    )

    cost_registration.sqlmodel_update(update_dict)
    session.add(cost_registration)
    session.commit()
    session.refresh(cost_registration)

    # Convert to public schema and add warning if present
    result = CostRegistrationPublic.model_validate(cost_registration)
    if warning:
        # Add warning to response by converting to dict and adding warning
        # Use mode='json' to serialize dates properly
        # Return as JSONResponse to bypass response_model validation
        result_dict = result.model_dump(mode="json")
        result_dict["warning"] = warning["warning"]
        return JSONResponse(content=result_dict)

    return result


@router.delete("/{id}")
def delete_cost_registration(
    session: SessionDep, _current_user: CurrentUser, id: uuid.UUID
) -> Message:
    """
    Delete a cost registration.
    """
    cost_registration = session.get(CostRegistration, id)
    if not cost_registration:
        raise HTTPException(status_code=404, detail="Cost registration not found")
    session.delete(cost_registration)
    session.commit()
    return Message(message="Cost registration deleted successfully")
