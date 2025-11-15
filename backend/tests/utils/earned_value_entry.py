import uuid
from datetime import date, datetime, timezone
from decimal import ROUND_HALF_UP, Decimal

from sqlmodel import Session

from app import crud
from app.models import (
    CostElement,
    EarnedValueEntry,
    EarnedValueEntryCreate,
    UserCreate,
)


def _calculate_earned_value(budget_bac: Decimal, percent_complete: Decimal) -> Decimal:
    """Calculate earned value rounded to 2 decimal places."""
    earned_value = budget_bac * (percent_complete / Decimal("100"))
    return earned_value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def create_earned_value_entry(
    db: Session,
    *,
    cost_element_id: uuid.UUID,
    completion_date: date,
    percent_complete: Decimal = Decimal("50.00"),
    deliverables: str = "Test deliverable",
    description: str = "Test earned value entry",
    registration_date: date | None = None,
    created_at: datetime | None = None,
    created_by_id: uuid.UUID | None = None,
) -> EarnedValueEntry:
    """Create an earned value entry for tests."""
    if created_by_id is None:
        email = f"earned_value_user_{uuid.uuid4().hex[:8]}@example.com"
        password = "testpassword123"
        user_in = UserCreate(email=email, password=password)
        user = crud.create_user(session=db, user_create=user_in)
        created_by_id = user.id

    cost_element = db.get(CostElement, cost_element_id)
    if not cost_element:
        raise ValueError("Cost element must exist before creating earned value entry")

    budget_bac = Decimal(str(cost_element.budget_bac or 0))
    earned_value = _calculate_earned_value(budget_bac, percent_complete)

    registration_date = registration_date or completion_date

    ev_in = EarnedValueEntryCreate(
        cost_element_id=cost_element_id,
        completion_date=completion_date,
        percent_complete=percent_complete,
        earned_value=earned_value,
        deliverables=deliverables,
        description=description,
        registration_date=registration_date,
    )

    ev_data = ev_in.model_dump()
    ev_data["created_by_id"] = created_by_id

    earned_value_entry = EarnedValueEntry.model_validate(ev_data)
    if created_at is None:
        created_at = datetime.combine(
            registration_date, datetime.min.time(), tzinfo=timezone.utc
        )
    earned_value_entry.created_at = created_at
    earned_value_entry.last_modified_at = created_at
    db.add(earned_value_entry)
    db.commit()
    db.refresh(earned_value_entry)
    return earned_value_entry
