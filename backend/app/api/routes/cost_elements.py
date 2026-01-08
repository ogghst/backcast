from collections.abc import Sequence
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import RoleChecker, get_current_active_user
from app.db.session import get_db
from app.models.domain.cost_element import CostElement
from app.models.domain.user import User
from app.models.schemas.cost_element import (
    CostElementCreate,
    CostElementRead,
    CostElementUpdate,
)
from app.services.cost_element_service import CostElementService

router = APIRouter()


def get_cost_element_service(
    session: AsyncSession = Depends(get_db),
) -> CostElementService:
    return CostElementService(session)


@router.get(
    "",
    response_model=None,  # Will be PaginatedResponse[CostElementRead]
    operation_id="get_cost_elements",
    dependencies=[Depends(RoleChecker(required_permission="cost-element-read"))],
)
async def read_cost_elements(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    per_page: int = Query(20, ge=1, description="Items per page"),
    branch: str = Query("main", description="Branch to query"),
    wbe_id: UUID | None = Query(None, description="Filter by WBE ID"),
    cost_element_type_id: UUID | None = Query(
        None, description="Filter by Cost Element Type ID"
    ),
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
    service: CostElementService = Depends(get_cost_element_service),
) -> dict[str, Any]:
    """Retrieve cost elements with server-side search, filtering, and sorting."""
    from app.models.schemas.common import PaginatedResponse
    from app.models.schemas.cost_element import CostElementRead

    # Legacy filters support
    legacy_filters = {}
    if wbe_id:
        legacy_filters["wbe_id"] = wbe_id
    if cost_element_type_id:
        legacy_filters["cost_element_type_id"] = cost_element_type_id

    skip = (page - 1) * per_page

    items, total = await service.get_cost_elements(
        filters=legacy_filters,
        branch=branch,
        skip=skip,
        limit=per_page,
        search=search,
        filter_string=filters,
        sort_field=sort_field,
        sort_order=sort_order,
    )

    # Convert to Pydantic models
    items_out = [CostElementRead.model_validate(i) for i in items]

    # Return paginated response
    response = PaginatedResponse[CostElementRead](
        items=items_out,
        total=total,
        page=page,
        per_page=per_page,
    )

    return response.model_dump()


@router.post(
    "",
    response_model=CostElementRead,
    status_code=status.HTTP_201_CREATED,
    operation_id="create_cost_element",
    dependencies=[Depends(RoleChecker(required_permission="cost-element-create"))],
)
async def create_cost_element(
    element_in: CostElementCreate,
    branch: str = Query("main", description="Target branch for creation"),
    current_user: User = Depends(get_current_active_user),
    service: CostElementService = Depends(get_cost_element_service),
) -> CostElement:
    """Create a new cost element in specified branch."""
    try:
        return await service.create(
            element_in=element_in, actor_id=current_user.user_id, branch=branch
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.get(
    "/{cost_element_id}",
    response_model=CostElementRead,
    operation_id="get_cost_element",
    dependencies=[Depends(RoleChecker(required_permission="cost-element-read"))],
)
async def read_cost_element(
    cost_element_id: UUID,
    branch: str = Query("main", description="Branch to query"),
    service: CostElementService = Depends(get_cost_element_service),
) -> CostElement:
    """Get a specific cost element by id and branch."""
    item = await service.get_by_id(cost_element_id, branch=branch)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cost Element not found in branch {branch}",
        )
    return item


@router.put(
    "/{cost_element_id}",
    response_model=CostElementRead,
    operation_id="update_cost_element",
    dependencies=[Depends(RoleChecker(required_permission="cost-element-update"))],
)
async def update_cost_element(
    cost_element_id: UUID,
    element_in: CostElementUpdate,
    branch: str = Query("main", description="Target branch for update"),
    current_user: User = Depends(get_current_active_user),
    service: CostElementService = Depends(get_cost_element_service),
) -> CostElement:
    """Update a cost element. Creates new version or forks."""
    try:
        # Check existence first? Service handles existence logic (especially fork).
        # But we might want to 404 if it doesn't exist in source either.
        # Service update logic: "If version not found in target branch -> Fork from main".
        # If not in main -> ValueError.

        return await service.update(
            cost_element_id=cost_element_id,
            element_in=element_in,
            actor_id=current_user.user_id,
            branch=branch,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.delete(
    "/{cost_element_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="delete_cost_element",
    dependencies=[Depends(RoleChecker(required_permission="cost-element-delete"))],
)
async def delete_cost_element(
    cost_element_id: UUID,
    branch: str = Query("main", description="Branch to delete from"),
    current_user: User = Depends(get_current_active_user),
    service: CostElementService = Depends(get_cost_element_service),
) -> None:
    """Soft delete a cost element in a branch."""
    try:
        item = await service.get_by_id(cost_element_id, branch=branch)
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Cost Element not found in branch {branch}",
            )

        await service.soft_delete(
            cost_element_id=cost_element_id,
            actor_id=current_user.user_id,
            branch=branch,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get(
    "/{cost_element_id}/history",
    response_model=list[CostElementRead],
    operation_id="get_cost_element_history",
    dependencies=[Depends(RoleChecker(required_permission="cost-element-read"))],
)
async def get_cost_element_history(
    cost_element_id: UUID,
    service: CostElementService = Depends(get_cost_element_service),
) -> Sequence[CostElement]:
    """Get full version history for a cost element across all branches."""
    # TODO: History might need branch filtering too?
    # TemporalService.get_history gets ALL versions by root_id.
    # This is correct for "history view".
    return await service.get_history(cost_element_id)
