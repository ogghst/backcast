import uuid

from sqlmodel import Session

from app.models import CostElement, CostElementCreate
from tests.utils.cost_element_type import create_random_cost_element_type
from tests.utils.wbe import create_random_wbe


def create_random_cost_element(
    db: Session,
    wbe_id: uuid.UUID | None = None,
    cost_element_type_id: uuid.UUID | None = None,
) -> CostElement:
    """Create a random cost element."""
    if cost_element_type_id is None:
        cost_element_type = create_random_cost_element_type(db)
        cost_element_type_id = cost_element_type.cost_element_type_id

    if wbe_id is None:
        wbe = create_random_wbe(db)
        wbe_id = wbe.wbe_id

    ce_in = CostElementCreate(
        wbe_id=wbe_id,
        cost_element_type_id=cost_element_type_id,
        department_code=f"DEPT{uuid.uuid4().hex[:4]}",
        department_name=f"Test Department {uuid.uuid4().hex[:8]}",
        budget_bac=10000.00,
        revenue_plan=12000.00,
        status="active",
    )

    ce = CostElement.model_validate(ce_in)
    db.add(ce)
    db.commit()
    db.refresh(ce)
    return ce
