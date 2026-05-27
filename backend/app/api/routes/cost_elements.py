"""Cost Element (EOC) API routes - standalone endpoints.

Cost Elements are the leaf level of the budget hierarchy (Element of Cost).
Versionable but NOT branchable (financial facts are global).
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import RoleChecker, UserIdentity, get_current_user
from app.db.session import get_db
from app.models.domain.cost_element import CostElement
from app.models.schemas.cost_element import (
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
    response_model=None,
    operation_id="get_cost_elements",
    dependencies=[Depends(RoleChecker(required_permission="cost-element-read"))],
)
async def read_cost_elements(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    per_page: int = Query(20, ge=1, description="Items per page"),
    work_package_id: UUID | None = Query(
        None, description="Filter by Work Package root ID"
    ),
    cost_element_type_id: UUID | None = Query(
        None, description="Filter by Cost Element Type ID"
    ),
    search: str | None = Query(None, description="Search term"),
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
    """Retrieve cost elements (EOCs) with server-side search, filtering, and sorting.

    Cost Elements are versionable but NOT branchable.
    """
    from app.models.schemas.common import PaginatedResponse
    from app.models.schemas.cost_element import CostElementRead

    if as_of is None:
        as_of = datetime.now(tz=UTC)

    legacy_filters: dict[str, Any] = {}
    if work_package_id:
        legacy_filters["work_package_id"] = work_package_id
    if cost_element_type_id:
        legacy_filters["cost_element_type_id"] = cost_element_type_id

    skip = (page - 1) * per_page

    items, total = await service.get_cost_elements(
        work_package_id=work_package_id,
        cost_element_type_id=cost_element_type_id,
        skip=skip,
        limit=per_page,
        as_of=as_of,
    )

    items_out = [CostElementRead.model_validate(i) for i in items]

    response = PaginatedResponse[CostElementRead](
        items=items_out,
        total=total,
        page=page,
        per_page=per_page,
    )

    return response.model_dump()


@router.get(
    "/{cost_element_id}",
    response_model=CostElementRead,
    operation_id="get_cost_element",
    dependencies=[Depends(RoleChecker(required_permission="cost-element-read"))],
)
async def read_cost_element(
    cost_element_id: UUID,
    as_of: datetime | None = Query(
        None,
        description="Time travel: get cost element state as of this timestamp (ISO 8601)",
    ),
    service: CostElementService = Depends(get_cost_element_service),
) -> CostElement:
    """Get a specific cost element by root ID. Requires read permission.

    Supports time-travel queries via the as_of parameter.
    """
    if as_of is None:
        as_of = datetime.now(tz=UTC)

    item = await service.get_as_of(entity_id=cost_element_id, as_of=as_of)

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cost Element not found" + (f" as of {as_of}" if as_of else ""),
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
    current_user: UserIdentity = Depends(get_current_user),
    service: CostElementService = Depends(get_cost_element_service),
) -> CostElement:
    """Update a cost element. Creates a new version. Requires update permission."""
    try:
        return await service.update_cost_element(
            cost_element_id=cost_element_id,
            element_in=element_in,
            actor_id=current_user.user_id,
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
    control_date: datetime | None = Query(
        None, description="Optional control date for deletion"
    ),
    current_user: UserIdentity = Depends(get_current_user),
    service: CostElementService = Depends(get_cost_element_service),
) -> None:
    """Soft delete a cost element. Requires delete permission."""
    try:
        item = await service.get_by_id(cost_element_id)
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cost Element not found",
            )

        await service.soft_delete_cost_element(
            cost_element_id=cost_element_id,
            actor_id=current_user.user_id,
            control_date=control_date,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
