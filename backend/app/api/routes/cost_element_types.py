from collections.abc import Sequence
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import RoleChecker, get_current_active_user
from app.db.session import get_db
from app.models.domain.cost_element_type import CostElementType
from app.models.domain.user import User
from app.models.schemas.cost_element_type import (
    CostElementTypeCreate,
    CostElementTypeRead,
    CostElementTypeUpdate,
)
from app.services.cost_element_type_service import CostElementTypeService

router = APIRouter()


def get_cost_element_type_service(
    session: AsyncSession = Depends(get_db),
) -> CostElementTypeService:
    return CostElementTypeService(session)


@router.get(
    "",
    response_model=list[CostElementTypeRead],
    operation_id="get_cost_element_types",
    dependencies=[Depends(RoleChecker(required_permission="cost-element-type-read"))],
)
async def read_cost_element_types(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    department_id: UUID | None = None,
    service: CostElementTypeService = Depends(get_cost_element_type_service),
) -> Sequence[CostElementType]:
    """Retrieve cost element types."""
    filters = {}
    if department_id:
        filters["department_id"] = department_id
        
    return await service.list(filters=filters, skip=skip, limit=limit)


@router.post(
    "",
    response_model=CostElementTypeRead,
    status_code=status.HTTP_201_CREATED,
    operation_id="create_cost_element_type",
    dependencies=[Depends(RoleChecker(required_permission="cost-element-type-create"))],
)
async def create_cost_element_type(
    type_in: CostElementTypeCreate,
    current_user: User = Depends(get_current_active_user),
    service: CostElementTypeService = Depends(get_cost_element_type_service),
) -> CostElementType:
    """Create a new cost element type."""
    try:
        return await service.create(
            type_in=type_in, actor_id=current_user.user_id
        )
    except Exception as e:
        # Catch generic errors for now, ideally specific expected exceptions
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.get(
    "/{cost_element_type_id}",
    response_model=CostElementTypeRead,
    operation_id="get_cost_element_type",
    dependencies=[Depends(RoleChecker(required_permission="cost-element-type-read"))],
)
async def read_cost_element_type(
    cost_element_type_id: UUID,
    service: CostElementTypeService = Depends(get_cost_element_type_service),
) -> CostElementType:
    """Get a specific cost element type by id."""
    item = await service.get_by_id(cost_element_type_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cost Element Type not found",
        )
    return item


@router.put(
    "/{cost_element_type_id}",
    response_model=CostElementTypeRead,
    operation_id="update_cost_element_type",
    dependencies=[Depends(RoleChecker(required_permission="cost-element-type-update"))],
)
async def update_cost_element_type(
    cost_element_type_id: UUID,
    type_in: CostElementTypeUpdate,
    current_user: User = Depends(get_current_active_user),
    service: CostElementTypeService = Depends(get_cost_element_type_service),
) -> CostElementType:
    """Update a cost element type."""
    try:
        item = await service.get_by_id(cost_element_type_id)
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cost Element Type not found",
            )
            
        return await service.update(
            cost_element_type_id=cost_element_type_id,
            type_in=type_in,
            actor_id=current_user.user_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.delete(
    "/{cost_element_type_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="delete_cost_element_type",
    dependencies=[Depends(RoleChecker(required_permission="cost-element-type-delete"))],
)
async def delete_cost_element_type(
    cost_element_type_id: UUID,
    current_user: User = Depends(get_current_active_user),
    service: CostElementTypeService = Depends(get_cost_element_type_service),
) -> None:
    """Soft delete a cost element type."""
    try:
        item = await service.get_by_id(cost_element_type_id)
        if not item:
            # Idempotent or Error? Standard idempotent is usually preferred but API often 404s.
            # Mirroring department service behavior.
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cost Element Type not found",
            )
            
        await service.soft_delete(
            cost_element_type_id=cost_element_type_id, actor_id=current_user.user_id
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get(
    "/{cost_element_type_id}/history",
    response_model=list[CostElementTypeRead],
    operation_id="get_cost_element_type_history",
    dependencies=[Depends(RoleChecker(required_permission="cost-element-type-read"))],
)
async def get_cost_element_type_history(
    cost_element_type_id: UUID,
    service: CostElementTypeService = Depends(get_cost_element_type_service),
) -> Sequence[CostElementType]:
    """Get version history for a cost element type."""
    return await service.get_history(cost_element_type_id)
