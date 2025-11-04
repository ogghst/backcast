"""Cost Element Types API routes."""
from typing import Any

from fastapi import APIRouter

from app.api.deps import CurrentUser, SessionDep
from app.models import CostElementType, CostElementTypePublic, CostElementTypesPublic

router = APIRouter(prefix="/cost-element-types", tags=["cost-element-types"])


@router.get("/", response_model=CostElementTypesPublic)
def read_cost_element_types(
    session: SessionDep,
    _current_user: CurrentUser,
) -> Any:
    """
    Retrieve active cost element types.
    """
    from sqlalchemy.orm import selectinload
    from sqlmodel import func, select

    # Get only active cost element types, ordered by display_order
    count_statement = (
        select(func.count())
        .select_from(CostElementType)
        .where(CostElementType.is_active.is_(True))
    )
    count = session.exec(count_statement).one()

    statement = (
        select(CostElementType)
        .options(selectinload(CostElementType.department))
        .where(CostElementType.is_active.is_(True))
        .order_by(CostElementType.display_order)
    )
    cost_element_types = session.exec(statement).all()

    # Build response with department info
    public_types = []
    for cet in cost_element_types:
        public_type = CostElementTypePublic(
            cost_element_type_id=cet.cost_element_type_id,
            type_code=cet.type_code,
            type_name=cet.type_name,
            category_type=cet.category_type,
            tracks_hours=cet.tracks_hours,
            description=cet.description,
            display_order=cet.display_order,
            is_active=cet.is_active,
            department_id=cet.department_id,
            department_code=cet.department.department_code if cet.department else None,
            department_name=cet.department.department_name if cet.department else None,
            created_at=cet.created_at,
            updated_at=cet.updated_at,
        )
        public_types.append(public_type)

    return CostElementTypesPublic(data=public_types, count=count)
