"""WBE API routes with RBAC."""

from collections.abc import Sequence
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import RoleChecker, get_current_active_user
from app.db.session import get_db
from app.models.domain.user import User
from app.models.domain.wbe import WBE
from app.models.schemas.wbe import (
    WBEBreadcrumb,
    WBECreate,
    WBEPublic,
    WBEUpdate,
)
from app.services.wbe import WBEService

router = APIRouter()


def get_wbe_service(
    session: AsyncSession = Depends(get_db),
) -> WBEService:
    return WBEService(session)


@router.get(
    "",
    response_model=None,  # Will be PaginatedResponse[WBEPublic]
    operation_id="get_wbes",
    dependencies=[Depends(RoleChecker(required_permission="wbe-read"))],
)
async def read_wbes(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    project_id: UUID | None = Query(None, description="Filter by project ID"),
    parent_wbe_id: str | None = Query(None, description="Filter by parent WBE ID (use 'null' string for root WBEs)"),
    branch: str = Query("main", description="Branch name"),
    search: str | None = Query(None, description="Search term (code, name)"),
    filters: str | None = Query(
        None,
        description="Filters in format 'column:value;column:value1,value2'",
        example="level:1,2;code:1.1",
    ),
    sort_field: str | None = Query(None, description="Field to sort by"),
    sort_order: str = Query(
        "asc",
        regex="^(asc|desc)$",
        description="Sort order (asc or desc)",
    ),
    service: WBEService = Depends(get_wbe_service),
) -> dict | Sequence[WBE]:
    """Retrieve WBEs with server-side search, filtering, and sorting.
    
    Supports two modes:
    1. **Hierarchical filtering** (project_id/parent_wbe_id): Returns list without pagination
    2. **General listing** (no hierarchical filters): Returns paginated response with search/filter/sort
    
    Hierarchical Filtering:
    - project_id only: All WBEs in project
    - project_id + parent_wbe_id: Child WBEs of specified parent
    - parent_wbe_id='null': Root WBEs (parent_wbe_id IS NULL)
    
    General Listing (when no hierarchical filters):
    - **Search**: Case-insensitive search across code and name
    - **Filters**: Filter by level, code, name (format: "column:value;column:value1,value2")
    - **Sorting**: Sort by any field (asc/desc)
    - **Pagination**: Returns total count for proper pagination UI
    
    Requires read permission.
    """
    from app.models.schemas.common import PaginatedResponse
    from app.models.schemas.wbe import WBEPublic

    # Parse parent_wbe_id
    parsed_parent_id: UUID | None = None
    is_root_query = False

    if parent_wbe_id:
        if parent_wbe_id.lower() == "null":
            is_root_query = True
            parsed_parent_id = None
        else:
            try:
                parsed_parent_id = UUID(parent_wbe_id)
            except ValueError as e:
                raise HTTPException(status_code=422, detail="Invalid parent_wbe_id format") from e

    # Handle hierarchical filtering (returns list, not paginated)
    # Case 1: Specific parent (parsed_parent_id is set)
    # Case 2: Root query (is_root_query is True)
    if parsed_parent_id or is_root_query:
        return await service.get_by_parent(
            project_id=project_id,
            parent_wbe_id=parsed_parent_id,
            branch=branch,
        )

    # Project filtering only (returns list, not paginated)
    if project_id:
        return await service.get_by_project(project_id=project_id, branch=branch)

    # No hierarchical filters - use paginated general listing with search/filter/sort
    skip = (page - 1) * per_page

    try:
        wbes, total = await service.get_wbes(
            skip=skip,
            limit=per_page,
            branch=branch,
            search=search,
            filters=filters,
            sort_field=sort_field,
            sort_order=sort_order,
        )

        # Convert to Pydantic models
        items = [WBEPublic.model_validate(w) for w in wbes]

        # Return paginated response
        response = PaginatedResponse[WBEPublic](
            items=items,
            total=total,
            page=page,
            per_page=per_page,
        )

        return response.model_dump()

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.post(
    "",
    response_model=WBEPublic,
    status_code=status.HTTP_201_CREATED,
    operation_id="create_wbe",
    dependencies=[Depends(RoleChecker(required_permission="wbe-create"))],
)
async def create_wbe(
    wbe_in: WBECreate,
    current_user: User = Depends(get_current_active_user),
    service: WBEService = Depends(get_wbe_service),
) -> WBE:
    """Create a new WBE. Requires create permission."""
    try:
        # Check if WBE code already exists in the project
        existing = await service.get_by_code(
            code=wbe_in.code, project_id=wbe_in.project_id
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"WBE with code '{wbe_in.code}' already exists in this project",
            )

        wbe = await service.create_wbe(wbe_in=wbe_in, actor_id=current_user.user_id)
        return wbe
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.get(
    "/{wbe_id}",
    response_model=WBEPublic,
    operation_id="get_wbe",
    dependencies=[Depends(RoleChecker(required_permission="wbe-read"))],
)
async def read_wbe(
    wbe_id: UUID,
    service: WBEService = Depends(get_wbe_service),
) -> WBE:
    """Get a specific WBE by id. Requires read permission."""
    wbe = await service.get_by_root_id(wbe_id)
    if not wbe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="WBE not found",
        )
    return wbe


@router.put(
    "/{wbe_id}",
    response_model=WBEPublic,
    operation_id="update_wbe",
    dependencies=[Depends(RoleChecker(required_permission="wbe-update"))],
)
async def update_wbe(
    wbe_id: UUID,
    wbe_in: WBEUpdate,
    current_user: User = Depends(get_current_active_user),
    service: WBEService = Depends(get_wbe_service),
) -> WBE:
    """Update a WBE. Requires update permission."""
    try:
        updated_wbe = await service.update_wbe(
            wbe_id=wbe_id,
            wbe_in=wbe_in,
            actor_id=current_user.user_id,
        )
        return updated_wbe
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.delete(
    "/{wbe_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="delete_wbe",
    dependencies=[Depends(RoleChecker(required_permission="wbe-delete"))],
)
async def delete_wbe(
    wbe_id: UUID,
    current_user: User = Depends(get_current_active_user),
    service: WBEService = Depends(get_wbe_service),
) -> None:
    """Soft delete a WBE. Requires delete permission."""
    try:
        await service.delete_wbe(wbe_id=wbe_id, actor_id=current_user.user_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get(
    "/{wbe_id}/breadcrumb",
    response_model=WBEBreadcrumb,
    operation_id="get_wbe_breadcrumb",
    dependencies=[Depends(RoleChecker(required_permission="wbe-read"))],
)
async def read_wbe_breadcrumb(
    wbe_id: UUID,
    service: WBEService = Depends(get_wbe_service),
) -> dict:
    """Get breadcrumb trail for a WBE (project + ancestor path). Requires read permission."""
    try:
        return await service.get_breadcrumb(wbe_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


@router.get(
    "/{wbe_id}/history",
    response_model=list[WBEPublic],
    operation_id="get_wbe_history",
    dependencies=[Depends(RoleChecker(required_permission="wbe-read"))],
)
async def read_wbe_history(
    wbe_id: UUID,
    service: WBEService = Depends(get_wbe_service),
) -> Sequence[WBE]:
    """Get version history for a WBE. Requires read permission."""
    history = await service.get_wbe_history(wbe_id)
    if not history:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No history found for this WBE",
        )
    return history
