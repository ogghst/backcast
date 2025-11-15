import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlmodel import Session

from app.models import (
    CostRegistration,
    CostRegistrationCreate,
)
from tests.utils.cost_element import create_random_cost_element


def create_random_cost_registration(
    db: Session,
    cost_element_id: uuid.UUID | None = None,
    created_by_id: uuid.UUID | None = None,
    registration_date: date | None = None,
    created_at: datetime | None = None,
) -> CostRegistration:
    """Create a random cost registration."""
    if cost_element_id is None:
        cost_element = create_random_cost_element(db)
        cost_element_id = cost_element.cost_element_id

    # Use provided created_by_id or create a user
    if created_by_id is None:
        from app import crud
        from app.models import UserCreate

        email = f"user_{uuid.uuid4().hex[:8]}@example.com"
        password = "testpassword123"
        user_in = UserCreate(email=email, password=password)
        user = crud.create_user(session=db, user_create=user_in)
        created_by_id = user.id

    if registration_date is None:
        registration_date = date(2024, 2, 15)

    cost_in = CostRegistrationCreate(
        cost_element_id=cost_element_id,
        registration_date=registration_date,
        amount=Decimal("1500.00"),
        cost_category="labor",
        description="Test cost registration",
        is_quality_cost=False,
    )

    # Create cost registration with created_by_id
    # Note: created_by_id is not in CostRegistrationCreate schema,
    # so we add it directly when creating the model
    cost_data = cost_in.model_dump()
    cost_data["created_by_id"] = created_by_id
    cost = CostRegistration.model_validate(cost_data)
    if created_at is not None:
        cost.created_at = created_at
        cost.last_modified_at = created_at
    elif registration_date is not None:
        default_created = datetime.combine(
            registration_date, datetime.min.time(), tzinfo=timezone.utc
        )
        cost.created_at = default_created
        cost.last_modified_at = default_created
    db.add(cost)
    db.commit()
    db.refresh(cost)
    return cost
