"""Cost Event Type API routes - configurable cost event categorization.

Cost Event Types are versionable (NOT branchable) reference data.
"""

from collections.abc import Sequence
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import RoleChecker, UserIdentity, get_current_user
from app.db.session import get_db
from app.models.domain.cost_event_type import CostEventType
from app.models.schemas.cost_event_type import (
    CostEventTypeCreate,
    CostEventTypeRead,
    CostEventTypeUpdate,
)
from app.services.cost_event_type_service import CostEventTypeService

router = APIRouter()


def get_cost_event_type_service(
    session: AsyncSession = Depends(get_db),
) -> CostEventTypeService:
    return CostEventTypeService(session)


@router.get(
    "",
    response_model=None,
    operation_id="get_cost_event_types",
    dependencies=[Depends(RoleChecker(required_permission="cost-event-type-read"))],
)
async def read_cost_event_types(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    per_page: int = Query(20, ge=1, description="Items per page"),
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
    service: CostEventTypeService = Depends(get_cost_event_type_service),
) -> dict[str, Any]:
    """Retrieve cost event types with server-side search, filtering, and sorting."""
    from app.models.schemas.common import PaginatedResponse
    from app.models.schemas.cost_event_type import CostEventTypeRead

    skip = (page - 1) * per_page

    items, total = await service.get_cost_event_types(
        skip=skip,
        limit=per_page,
        search=search,
        filter_string=filters,
        sort_field=sort_field,
        sort_order=sort_order,
    )

    items_out = [CostEventTypeRead.model_validate(i) for i in items]

    return PaginatedResponse[CostEventTypeRead](
        items=items_out,
        total=total,
        page=page,
        per_page=per_page,
    ).model_dump()


@router.post(
    "",
    response_model=CostEventTypeRead,
    status_code=status.HTTP_201_CREATED,
    operation_id="create_cost_event_type",
    dependencies=[Depends(RoleChecker(required_permission="cost-event-type-create"))],
)
async def create_cost_event_type(
    type_in: CostEventTypeCreate,
    current_user: UserIdentity = Depends(get_current_user),
    service: CostEventTypeService = Depends(get_cost_event_type_service),
) -> CostEventType:
    """Create a new cost event type."""
    try:
        return await service.create(type_in=type_in, actor_id=current_user.user_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.get(
    "/{cost_event_type_id}",
    response_model=CostEventTypeRead,
    operation_id="get_cost_event_type",
    dependencies=[Depends(RoleChecker(required_permission="cost-event-type-read"))],
)
async def read_cost_event_type(
    cost_event_type_id: UUID,
    service: CostEventTypeService = Depends(get_cost_event_type_service),
) -> CostEventType:
    """Get a specific cost event type by root ID."""
    item = await service.get_by_id(cost_event_type_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cost Event Type not found",
        )
    return item


@router.put(
    "/{cost_event_type_id}",
    response_model=CostEventTypeRead,
    operation_id="update_cost_event_type",
    dependencies=[Depends(RoleChecker(required_permission="cost-event-type-update"))],
)
async def update_cost_event_type(
    cost_event_type_id: UUID,
    type_in: CostEventTypeUpdate,
    current_user: UserIdentity = Depends(get_current_user),
    service: CostEventTypeService = Depends(get_cost_event_type_service),
) -> CostEventType:
    """Update a cost event type."""
    try:
        return await service.update(
            cost_event_type_id=cost_event_type_id,
            type_in=type_in,
            actor_id=current_user.user_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.delete(
    "/{cost_event_type_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="delete_cost_event_type",
    dependencies=[Depends(RoleChecker(required_permission="cost-event-type-delete"))],
)
async def delete_cost_event_type(
    cost_event_type_id: UUID,
    current_user: UserIdentity = Depends(get_current_user),
    service: CostEventTypeService = Depends(get_cost_event_type_service),
) -> None:
    """Soft delete a cost event type."""
    try:
        await service.soft_delete(
            cost_event_type_id=cost_event_type_id,
            actor_id=current_user.user_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get(
    "/{cost_event_type_id}/history",
    response_model=list[CostEventTypeRead],
    operation_id="get_cost_event_type_history",
    dependencies=[Depends(RoleChecker(required_permission="cost-event-type-read"))],
)
async def get_cost_event_type_history(
    cost_event_type_id: UUID,
    service: CostEventTypeService = Depends(get_cost_event_type_service),
) -> Sequence[CostEventType]:
    """Get version history for a cost event type."""
    history = await service.get_history(cost_event_type_id)
    if not history:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No history found for this Cost Event Type",
        )
    return history
