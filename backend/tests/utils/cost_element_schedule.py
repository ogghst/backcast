import uuid
from datetime import date

from sqlmodel import Session

from app import crud
from app.models import (
    CostElementSchedule,
    CostElementScheduleCreate,
    UserCreate,
)


def create_schedule_for_cost_element(
    db: Session,
    cost_element_id: uuid.UUID,
    start_date: date | None = None,
    end_date: date | None = None,
    progression_type: str = "linear",
    created_by_id: uuid.UUID | None = None,
) -> CostElementSchedule:
    """Create a schedule for a cost element."""
    if created_by_id is None:
        # Create a test user for created_by_id
        email = f"test_user_{uuid.uuid4().hex[:8]}@example.com"
        password = "testpassword123"
        user_in = UserCreate(email=email, password=password)
        user = crud.create_user(session=db, user_create=user_in)
        created_by_id = user.id

    if start_date is None:
        start_date = date.today()
    if end_date is None:
        end_date = date(2025, 12, 31)  # Default end date for tests

    schedule_in = CostElementScheduleCreate(
        cost_element_id=cost_element_id,
        start_date=start_date,
        end_date=end_date,
        progression_type=progression_type,
        created_by_id=created_by_id,
    )
    schedule = CostElementSchedule.model_validate(schedule_in)
    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    return schedule
