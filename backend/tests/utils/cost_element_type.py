import uuid

from sqlmodel import Session

from app.models import CostElementType, CostElementTypeCreate


def create_random_cost_element_type(db: Session) -> CostElementType:
    """Create a random cost element type."""
    unique_code = f"test_{uuid.uuid4().hex[:8]}"
    cet_in = CostElementTypeCreate(
        type_code=unique_code,
        type_name=f"Test Type {uuid.uuid4().hex[:8]}",
        category_type="engineering_mechanical",
        display_order=1,
        is_active=True,
    )

    cet = CostElementType.model_validate(cet_in)
    db.add(cet)
    db.commit()
    db.refresh(cet)
    return cet
