from collections.abc import Sequence
from typing import Any
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
    response_model=None,  # Will be PaginatedResponse[CostElementTypeRead]
    operation_id="get_cost_element_types",
    dependencies=[Depends(RoleChecker(required_permission="cost-element-type-read"))],
)
async def read_cost_element_types(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    per_page: int = Query(20, ge=1, description="Items per page"),
    department_id: UUID | None = Query(None, description="Filter by Department ID"),
    search: str | None = Query(None, description="Search term (code, name)"),
    filters: str | None = Query(
        None,
        description="Filters in format 'column:value;column:value1,value2'",
    ),
    sort_field: str | None = Query(None, description="Field to sort by"),
    sort_order: str = Query(
        "asc",
        pattern="^(asc|desc)$",
        description="Sort order (asc or desc)",
    ),
    service: CostElementTypeService = Depends(get_cost_element_type_service),
) -> dict[str, Any]:
    """Retrieve cost element types with server-side features."""
    from app.models.schemas.common import PaginatedResponse
    from app.models.schemas.cost_element_type import CostElementTypeRead

    legacy_filters = {}
    if department_id:
        legacy_filters["department_id"] = department_id

    skip = (page - 1) * per_page
    
    # Assuming the service might need updates too, but let's check it
    # For now, we'll just use what it has or return (items, total) if it supports it
    # Actually, let's check the service.
    items, total = await service.get_cost_element_types(
        filters=legacy_filters,
        skip=skip,
        limit=per_page,
        search=search,
        filter_string=filters,
        sort_field=sort_field,
        sort_order=sort_order,
    )

    items_out = [CostElementTypeRead.model_validate(i) for i in items]

    return PaginatedResponse[CostElementTypeRead](
        items=items_out,
        total=total,
        page=page,
        per_page=per_page,
    ).model_dump()


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
