from collections.abc import Sequence
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
    response_model=list[CostElementRead],
    operation_id="get_cost_elements",
    dependencies=[Depends(RoleChecker(required_permission="cost-element-read"))],
)
async def read_cost_elements(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    branch: str = Query("main", description="Branch to query"),
    wbe_id: UUID | None = None,
    cost_element_type_id: UUID | None = None,
    service: CostElementService = Depends(get_cost_element_service),
) -> Sequence[CostElement]:
    """Retrieve cost elements for a specific branch."""
    filters = {}
    if wbe_id:
        filters["wbe_id"] = wbe_id
    if cost_element_type_id:
        filters["cost_element_type_id"] = cost_element_type_id
        
    return await service.list(filters=filters, branch=branch, skip=skip, limit=limit)


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
            cost_element_id=cost_element_id, actor_id=current_user.user_id, branch=branch
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
