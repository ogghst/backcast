import uuid
from datetime import date
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

    cost_in = CostRegistrationCreate(
        cost_element_id=cost_element_id,
        registration_date=date(2024, 2, 15),
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
    db.add(cost)
    db.commit()
    db.refresh(cost)
    return cost
