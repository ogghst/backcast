import uuid
from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query
from sqlmodel import select

from app.api.deps import CurrentUser, SessionDep, TimeMachineControlDate
from app.models import (
    CostElement,
    CostElementSchedule,
    CostElementScheduleBase,
    CostElementScheduleCreate,
    CostElementSchedulePublic,
    CostElementScheduleUpdate,
    Message,
)
from app.services.time_machine import (
    TimeMachineEventType,
    apply_time_machine_filters,
)

router = APIRouter(prefix="/cost-element-schedules", tags=["cost-element-schedules"])


def _select_latest_operational_schedule(
    session: SessionDep,
    cost_element_id: uuid.UUID,
    control_date: date | None = None,
) -> CostElementSchedule | None:
    statement = (
        select(CostElementSchedule)
        .where(CostElementSchedule.cost_element_id == cost_element_id)
        .where(CostElementSchedule.baseline_id.is_(None))
        .order_by(
            CostElementSchedule.registration_date.desc(),
            CostElementSchedule.created_at.desc(),
        )
    )
    if control_date:
        statement = apply_time_machine_filters(
            statement, TimeMachineEventType.SCHEDULE, control_date
        )
    return session.exec(statement).first()


def _select_operational_schedule_history(
    session: SessionDep, cost_element_id: uuid.UUID, control_date: date | None = None
) -> list[CostElementSchedule]:
    statement = (
        select(CostElementSchedule)
        .where(CostElementSchedule.cost_element_id == cost_element_id)
        .where(CostElementSchedule.baseline_id.is_(None))
        .order_by(
            CostElementSchedule.registration_date.desc(),
            CostElementSchedule.created_at.desc(),
        )
    )
    if control_date:
        statement = apply_time_machine_filters(
            statement, TimeMachineEventType.SCHEDULE, control_date
        )
    return list(session.exec(statement).all())


@router.get("/", response_model=CostElementSchedulePublic)
def read_schedule_by_cost_element(
    session: SessionDep,
    _current_user: CurrentUser,
    cost_element_id: Annotated[uuid.UUID, Query(..., description="Cost element ID")],
    control_date: TimeMachineControlDate,
) -> Any:
    """
    Get the latest operational schedule for a cost element.
    """
    schedule = _select_latest_operational_schedule(
        session, cost_element_id, control_date
    )
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return schedule


@router.get("/history", response_model=list[CostElementSchedulePublic])
def read_schedule_history_by_cost_element(
    session: SessionDep,
    _current_user: CurrentUser,
    cost_element_id: Annotated[uuid.UUID, Query(..., description="Cost element ID")],
    control_date: TimeMachineControlDate,
) -> list[CostElementSchedule]:
    """
    Get the full operational schedule history for a cost element.
    """
    return _select_operational_schedule_history(session, cost_element_id, control_date)


@router.post("/", response_model=CostElementSchedulePublic)
def create_schedule(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    schedule_base: CostElementScheduleBase,
    cost_element_id: uuid.UUID = Query(..., description="Cost element ID"),
) -> Any:
    """
    Create a new schedule registration for a cost element.
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

    registration_date = schedule_base.registration_date or date.today()

    # Create schedule with current user as created_by
    schedule_create = CostElementScheduleCreate(
        cost_element_id=cost_element_id,
        start_date=schedule_base.start_date,
        end_date=schedule_base.end_date,
        progression_type=schedule_base.progression_type,
        registration_date=registration_date,
        description=schedule_base.description,
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
    Update a schedule registration.
    """
    schedule = session.get(CostElementSchedule, id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    if schedule.baseline_id is not None:
        raise HTTPException(
            status_code=400, detail="Baseline schedule snapshots cannot be modified"
        )

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
    Delete a schedule registration.
    """
    schedule = session.get(CostElementSchedule, id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    if schedule.baseline_id is not None:
        raise HTTPException(
            status_code=400, detail="Baseline schedule snapshots cannot be deleted"
        )
    session.delete(schedule)
    session.commit()
    return Message(message="Schedule deleted successfully")
