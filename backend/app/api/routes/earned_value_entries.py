"""Earned Value Entries API routes."""
import uuid
from datetime import date, datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlmodel import Session, func, select

from app.api.deps import CurrentUser, SessionDep
from app.models import (
    CostElement,
    CostElementSchedule,
    EarnedValueEntriesPublic,
    EarnedValueEntry,
    EarnedValueEntryCreate,
    EarnedValueEntryPublic,
    EarnedValueEntryUpdate,
    Message,
)

router = APIRouter(prefix="/earned-value-entries", tags=["earned-value-entries"])


def validate_cost_element_exists(
    session: Session, cost_element_id: uuid.UUID
) -> CostElement:
    """
    Ensure the referenced cost element exists.
    """

    cost_element = session.get(CostElement, cost_element_id)
    if not cost_element:
        raise HTTPException(status_code=400, detail="Cost element not found")
    return cost_element


def validate_deliverables(deliverables: str | None) -> None:
    """
    Ensure deliverables description is populated.
    """

    if deliverables is None or not deliverables.strip():
        raise HTTPException(
            status_code=400, detail="Deliverables description is required"
        )


def validate_percent_complete(percent_complete: Decimal) -> None:
    """
    Ensure percent_complete is within 0-100 inclusive.
    """

    if percent_complete < Decimal("0") or percent_complete > Decimal("100"):
        raise HTTPException(
            status_code=400,
            detail="percent_complete must be between 0 and 100",
        )


def ensure_unique_completion_date(
    session: Session,
    cost_element_id: uuid.UUID,
    completion_date: date,
    exclude_id: uuid.UUID | None = None,
) -> None:
    """
    Ensure only one entry per cost element per completion date exists.
    """

    statement = select(EarnedValueEntry).where(
        EarnedValueEntry.cost_element_id == cost_element_id,
        EarnedValueEntry.completion_date == completion_date,
    )
    if exclude_id:
        statement = statement.where(EarnedValueEntry.earned_value_id != exclude_id)

    existing_entry = session.exec(statement).first()
    if existing_entry:
        raise HTTPException(
            status_code=400,
            detail="An earned value entry for this date already exists for the cost element",
        )


def get_cost_element_schedule(
    session: Session, cost_element_id: uuid.UUID
) -> CostElementSchedule | None:
    """
    Retrieve the schedule for a cost element if one exists.
    """

    statement = select(CostElementSchedule).where(
        CostElementSchedule.cost_element_id == cost_element_id
    )
    return session.exec(statement).first()


def validate_completion_date_against_schedule(
    session: Session,
    cost_element_id: uuid.UUID,
    completion_date: date,
) -> dict[str, str] | None:
    """
    Validate completion date relative to the cost element schedule.
    """

    schedule = get_cost_element_schedule(session, cost_element_id)
    if schedule is None:
        return None

    if completion_date < schedule.start_date:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Completion date ({completion_date.isoformat()}) cannot be before "
                f"schedule start date ({schedule.start_date.isoformat()})"
            ),
        )

    if completion_date > schedule.end_date:
        return {
            "warning": (
                f"Completion date ({completion_date.isoformat()}) is after schedule end "
                f"date ({schedule.end_date.isoformat()})"
            )
        }

    return None


def calculate_earned_value(
    budget_bac: Decimal | None, percent_complete: Decimal
) -> Decimal:
    """
    Derive earned value using BAC × percent complete.
    """

    bac = Decimal(str(budget_bac or 0))
    earned_value = bac * (percent_complete / Decimal("100"))
    return earned_value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


@router.get("/", response_model=EarnedValueEntriesPublic)
def read_earned_value_entries(
    session: SessionDep,
    _current_user: CurrentUser,
    cost_element_id: uuid.UUID | None = Query(
        default=None, description="Filter by cost element ID"
    ),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
) -> Any:
    """
    Retrieve earned value entries with optional filtering and pagination.
    """

    statement = select(EarnedValueEntry)
    count_statement = select(func.count()).select_from(EarnedValueEntry)

    if cost_element_id:
        statement = statement.where(EarnedValueEntry.cost_element_id == cost_element_id)
        count_statement = count_statement.where(
            EarnedValueEntry.cost_element_id == cost_element_id
        )

    count = session.exec(count_statement).one()
    entries = session.exec(statement.offset(skip).limit(limit)).all()

    return EarnedValueEntriesPublic(
        data=[EarnedValueEntryPublic.model_validate(entry) for entry in entries],
        count=count,
    )


@router.get("/{earned_value_id}", response_model=EarnedValueEntryPublic)
def read_earned_value_entry(
    session: SessionDep,
    _current_user: CurrentUser,
    earned_value_id: uuid.UUID,
) -> Any:
    """
    Retrieve a single earned value entry by ID.
    """

    entry = session.get(EarnedValueEntry, earned_value_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Earned value entry not found")
    return entry


@router.post("/", response_model=EarnedValueEntryPublic)
def create_earned_value_entry(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    earned_value_entry_in: EarnedValueEntryCreate,
) -> Any:
    """
    Create a new earned value entry.
    """

    cost_element = validate_cost_element_exists(
        session, earned_value_entry_in.cost_element_id
    )
    validate_deliverables(earned_value_entry_in.deliverables)
    validate_percent_complete(earned_value_entry_in.percent_complete)
    ensure_unique_completion_date(
        session,
        earned_value_entry_in.cost_element_id,
        earned_value_entry_in.completion_date,
    )

    warning = validate_completion_date_against_schedule(
        session,
        earned_value_entry_in.cost_element_id,
        earned_value_entry_in.completion_date,
    )

    earned_value = calculate_earned_value(
        Decimal(str(cost_element.budget_bac or 0)),
        earned_value_entry_in.percent_complete,
    )

    ev_data = earned_value_entry_in.model_dump()
    ev_data["earned_value"] = earned_value
    ev_data["created_by_id"] = current_user.id

    earned_value_entry = EarnedValueEntry.model_validate(ev_data)
    session.add(earned_value_entry)
    session.commit()
    session.refresh(earned_value_entry)

    result = EarnedValueEntryPublic.model_validate(earned_value_entry)
    if warning:
        result_dict = result.model_dump(mode="json")
        result_dict["warning"] = warning["warning"]
        return JSONResponse(content=result_dict)

    return result


@router.put("/{earned_value_id}", response_model=EarnedValueEntryPublic)
def update_earned_value_entry(
    *,
    session: SessionDep,
    _current_user: CurrentUser,
    earned_value_id: uuid.UUID,
    earned_value_entry_in: EarnedValueEntryUpdate,
) -> Any:
    """
    Update an existing earned value entry.
    """

    earned_value_entry = session.get(EarnedValueEntry, earned_value_id)
    if not earned_value_entry:
        raise HTTPException(status_code=404, detail="Earned value entry not found")

    update_data = earned_value_entry_in.model_dump(exclude_unset=True)

    if "deliverables" in update_data:
        validate_deliverables(update_data["deliverables"])

    percent_complete = update_data.get(
        "percent_complete", earned_value_entry.percent_complete
    )
    validate_percent_complete(percent_complete)

    completion_date = update_data.get(
        "completion_date", earned_value_entry.completion_date
    )

    ensure_unique_completion_date(
        session,
        earned_value_entry.cost_element_id,
        completion_date,
        exclude_id=earned_value_id,
    )

    warning = validate_completion_date_against_schedule(
        session,
        earned_value_entry.cost_element_id,
        completion_date,
    )

    cost_element = validate_cost_element_exists(
        session, earned_value_entry.cost_element_id
    )

    earned_value_entry.sqlmodel_update(update_data)
    earned_value_entry.completion_date = completion_date
    earned_value_entry.percent_complete = percent_complete
    earned_value_entry.earned_value = calculate_earned_value(
        Decimal(str(cost_element.budget_bac or 0)),
        percent_complete,
    )
    earned_value_entry.last_modified_at = datetime.now(timezone.utc)

    session.add(earned_value_entry)
    session.commit()
    session.refresh(earned_value_entry)

    result = EarnedValueEntryPublic.model_validate(earned_value_entry)
    if warning:
        result_dict = result.model_dump(mode="json")
        result_dict["warning"] = warning["warning"]
        return JSONResponse(content=result_dict)

    return result


@router.delete("/{earned_value_id}")
def delete_earned_value_entry(
    session: SessionDep,
    _current_user: CurrentUser,
    earned_value_id: uuid.UUID,
) -> Message:
    """
    Delete an earned value entry.
    """

    earned_value_entry = session.get(EarnedValueEntry, earned_value_id)
    if not earned_value_entry:
        raise HTTPException(status_code=404, detail="Earned value entry not found")

    session.delete(earned_value_entry)
    session.commit()

    return Message(message="Earned value entry deleted successfully")
