import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from sqlmodel import select

from app.api.deps import CurrentUser, SessionDep
from app.models import (
    CostElement,
    CostElementSchedule,
    CostElementScheduleBase,
    CostElementScheduleCreate,
    CostElementSchedulePublic,
    CostElementScheduleUpdate,
    Message,
)

router = APIRouter(prefix="/cost-element-schedules", tags=["cost-element-schedules"])


@router.get("/", response_model=CostElementSchedulePublic)
def read_schedule_by_cost_element(
    session: SessionDep,
    _current_user: CurrentUser,
    cost_element_id: uuid.UUID = Query(..., description="Cost element ID"),
) -> Any:
    """
    Get schedule for a cost element.
    """
    statement = select(CostElementSchedule).where(
        CostElementSchedule.cost_element_id == cost_element_id
    )
    schedule = session.exec(statement).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return schedule


@router.post("/", response_model=CostElementSchedulePublic)
def create_schedule(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    schedule_base: CostElementScheduleBase,
    cost_element_id: uuid.UUID = Query(..., description="Cost element ID"),
) -> Any:
    """
    Create a new schedule for a cost element.
    """
    # Validate that cost element exists
    cost_element = session.get(CostElement, cost_element_id)
    if not cost_element:
        raise HTTPException(status_code=400, detail="Cost element not found")

    # Validate end_date >= start_date
    if schedule_base.end_date < schedule_base.start_date:
        raise HTTPException(
            status_code=400,
            detail="end_date must be greater than or equal to start_date",
        )

    # Check if schedule already exists for this cost element
    existing_statement = select(CostElementSchedule).where(
        CostElementSchedule.cost_element_id == cost_element_id
    )
    existing = session.exec(existing_statement).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Schedule already exists for this cost element",
        )

    # Create schedule with current user as created_by
    schedule_create = CostElementScheduleCreate(
        cost_element_id=cost_element_id,
        start_date=schedule_base.start_date,
        end_date=schedule_base.end_date,
        progression_type=schedule_base.progression_type,
        notes=schedule_base.notes,
        created_by_id=current_user.id,
    )
    schedule = CostElementSchedule.model_validate(schedule_create)
    session.add(schedule)
    session.commit()
    session.refresh(schedule)
    return schedule


@router.put("/{id}", response_model=CostElementSchedulePublic)
def update_schedule(
    *,
    session: SessionDep,
    _current_user: CurrentUser,
    id: uuid.UUID,
    schedule_in: CostElementScheduleUpdate,
) -> Any:
    """
    Update a schedule.
    """
    schedule = session.get(CostElementSchedule, id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    update_dict = schedule_in.model_dump(exclude_unset=True)

    # Validate end_date >= start_date if both are being updated
    new_start_date = update_dict.get("start_date", schedule.start_date)
    new_end_date = update_dict.get("end_date", schedule.end_date)

    if new_end_date < new_start_date:
        raise HTTPException(
            status_code=400,
            detail="end_date must be greater than or equal to start_date",
        )

    schedule.sqlmodel_update(update_dict)
    session.add(schedule)
    session.commit()
    session.refresh(schedule)
    return schedule


@router.delete("/{id}")
def delete_schedule(
    session: SessionDep, _current_user: CurrentUser, id: uuid.UUID
) -> Message:
    """
    Delete a schedule.
    """
    schedule = session.get(CostElementSchedule, id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    session.delete(schedule)
    session.commit()
    return Message(message="Schedule deleted successfully")
