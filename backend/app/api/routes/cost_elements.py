from collections.abc import Sequence
from datetime import datetime
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
    as_of: datetime | None = Query(
        None,
        description="Time travel: get Cost Elements as of this timestamp (ISO 8601)",
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
        as_of=as_of,
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
    current_user: User = Depends(get_current_active_user),
    service: CostElementService = Depends(get_cost_element_service),
) -> CostElement:
    """Create a new cost element in specified branch."""
    try:
        return await service.create(
            element_in=element_in,
            actor_id=current_user.user_id,
            branch=element_in.branch,
            control_date=element_in.control_date,
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
    as_of: datetime | None = Query(
        None,
        description="Time travel: get cost element state as of this timestamp (ISO 8601)",
    ),
    service: CostElementService = Depends(get_cost_element_service),
) -> CostElement:
    """Get a specific cost element by id and branch.

    Supports time-travel queries via the as_of parameter to view
    the cost element's state at any historical point in time.
    """
    if as_of:
        # Time travel query
        item = await service.get_cost_element_as_of(cost_element_id, as_of)
    else:
        # Current version
        item = await service.get_by_id(cost_element_id, branch=branch)

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cost Element not found in branch {branch}"
            + (f" as of {as_of}" if as_of else ""),
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
    current_user: User = Depends(get_current_active_user),
    service: CostElementService = Depends(get_cost_element_service),
) -> CostElement:
    """Update a cost element. Creates new version or forks."""
    try:
        # Use branch from schema if provided, otherwise default to main
        branch = element_in.branch or "main"

        return await service.update(
            cost_element_id=cost_element_id,
            element_in=element_in,
            actor_id=current_user.user_id,
            branch=branch,
            control_date=element_in.control_date,
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
    control_date: datetime | None = Query(
        None, description="Optional control date for deletion"
    ),
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
            control_date=control_date,
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


@router.get(
    "/{cost_element_id}/breadcrumb",
    operation_id="get_cost_element_breadcrumb",
    dependencies=[Depends(RoleChecker(required_permission="cost-element-read"))],
)
async def get_cost_element_breadcrumb(
    cost_element_id: UUID,
    service: CostElementService = Depends(get_cost_element_service),
) -> dict[str, Any]:
    """Get breadcrumb trail for a Cost Element (project + WBE + cost element)."""
    try:
        return await service.get_breadcrumb(cost_element_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
