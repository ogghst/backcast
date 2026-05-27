"""WBS Element API routes with RBAC and EVCS support."""

from collections.abc import Sequence
from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import RoleChecker, UserIdentity, get_current_user
from app.core.versioning.enums import BranchMode
from app.db.session import get_db
from app.models.domain.wbs_element import WBSElement
from app.models.schemas.wbs_element import (
    WBSElementCreate,
    WBSElementPublic,
    WBSElementUpdate,
)
from app.services.wbs_element_service import WBSElementService

router = APIRouter()


def get_wbs_element_service(
    session: AsyncSession = Depends(get_db),
) -> WBSElementService:
    return WBSElementService(session)


@router.get(
    "",
    response_model=None,
    operation_id="get_wbs_elements",
    dependencies=[Depends(RoleChecker(required_permission="wbs-element-read"))],
)
async def read_wbs_elements(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    per_page: int = Query(20, ge=1, description="Items per page"),
    project_id: UUID | None = Query(None, description="Filter by project ID"),
    parent_id: UUID | None = Query(
        None, description="Filter by parent WBS Element ID (use 'null' for root)"
    ),
    branch: str = Query("main", description="Branch name"),
    branch_mode: BranchMode = Query(
        BranchMode.MERGED,
        description="Branch mode: merged (combine with main) or isolated (current branch only)",
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
        description="Time travel: get WBS Elements as of this timestamp (ISO 8601)",
    ),
    service: WBSElementService = Depends(get_wbs_element_service),
) -> dict[str, Any] | list[WBSElementPublic]:
    """Retrieve WBS Elements with server-side search, filtering, and sorting.

    Supports two modes:
    1. **Hierarchical filtering** (project_id/parent_id): Returns list without pagination
    2. **General listing** (no hierarchical filters): Returns paginated response

    Requires read permission.
    """
    from app.models.schemas.common import PaginatedResponse
    from app.models.schemas.wbs_element import WBSElementPublic

    if as_of is None:
        from datetime import UTC

        as_of = datetime.now(tz=UTC)

    # Hierarchical mode: filter by parent_id
    if parent_id is not None:
        wbs_elements = await service.get_by_parent(
            project_id=project_id,
            parent_wbe_id=parent_id,
            branch=branch,
            branch_mode=branch_mode,
            as_of=as_of,
        )
        return [WBSElementPublic.model_validate(w) for w in wbs_elements]

    # General listing (Paginated)
    skip = (page - 1) * per_page

    try:
        items, total = await service.get_wbs_elements(
            skip=skip,
            limit=per_page,
            branch=branch,
            branch_mode=branch_mode,
            search=search,
            filters=filters,
            sort_field=sort_field,
            sort_order=sort_order,
            project_id=project_id,
            as_of=as_of,
        )

        result_items = [WBSElementPublic.model_validate(i) for i in items]

        response = PaginatedResponse[WBSElementPublic](
            items=result_items,
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
    response_model=WBSElementPublic,
    status_code=status.HTTP_201_CREATED,
    operation_id="create_wbs_element",
    dependencies=[Depends(RoleChecker(required_permission="wbs-element-create"))],
)
async def create_wbs_element(
    wbs_in: WBSElementCreate,
    current_user: UserIdentity = Depends(get_current_user),
    service: WBSElementService = Depends(get_wbs_element_service),
) -> WBSElement:
    """Create a new WBS Element. Requires create permission."""
    try:
        existing = await service.get_by_code(
            code=wbs_in.code, project_id=wbs_in.project_id
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"WBS Element with code '{wbs_in.code}' already exists in this project",
            )

        return await service.create_wbe(wbe_in=wbs_in, actor_id=current_user.user_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.get(
    "/project/{project_id}/tree",
    response_model=list[WBSElementPublic],
    operation_id="get_wbs_tree",
    dependencies=[Depends(RoleChecker(required_permission="wbs-element-read"))],
)
async def read_wbs_tree(
    project_id: UUID,
    branch: str = Query("main", description="Branch name"),
    branch_mode: BranchMode = Query(
        BranchMode.MERGED,
        description="Branch mode: merged or isolated",
    ),
    as_of: datetime | None = Query(
        None,
        description="Time travel: get tree as of this timestamp (ISO 8601)",
    ),
    service: WBSElementService = Depends(get_wbs_element_service),
) -> list[WBSElement]:
    """Get full WBS tree for a project.

    Returns all WBS Elements for the project as a flat list with parent references.
    Requires read permission.
    """
    if as_of is None:
        from datetime import UTC

        as_of = datetime.now(tz=UTC)

    try:
        items, _total = await service.get_wbs_elements(
            project_id=project_id,
            branch=branch,
            branch_mode=branch_mode,
            as_of=as_of,
        )
        return items
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


@router.get(
    "/{wbs_element_id}",
    response_model=WBSElementPublic,
    operation_id="get_wbs_element",
    dependencies=[Depends(RoleChecker(required_permission="wbs-element-read"))],
)
async def read_wbs_element(
    wbs_element_id: UUID,
    branch: str = Query("main", description="Branch name"),
    as_of: datetime | None = Query(
        None,
        description="Time travel: get WBS Element state as of this timestamp (ISO 8601)",
    ),
    service: WBSElementService = Depends(get_wbs_element_service),
) -> WBSElement:
    """Get a specific WBS Element by root ID. Requires read permission.

    Supports time-travel queries via the as_of parameter.
    """
    if as_of is None:
        from datetime import UTC

        as_of = datetime.now(tz=UTC)

    wbs_element = await service.get_as_of(
        entity_id=wbs_element_id, as_of=as_of, branch=branch
    )

    if not wbs_element:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"WBS Element not found in branch '{branch}'"
            + (f" as of {as_of}" if as_of else ""),
        )
    return wbs_element


@router.put(
    "/{wbs_element_id}",
    response_model=WBSElementPublic,
    operation_id="update_wbs_element",
    dependencies=[Depends(RoleChecker(required_permission="wbs-element-update"))],
)
async def update_wbs_element(
    wbs_element_id: UUID,
    wbs_in: WBSElementUpdate,
    current_user: UserIdentity = Depends(get_current_user),
    service: WBSElementService = Depends(get_wbs_element_service),
) -> WBSElement:
    """Update a WBS Element. Requires update permission."""
    try:
        return await service.update_wbe(
            wbe_id=wbs_element_id,
            wbe_in=wbs_in,
            actor_id=current_user.user_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.delete(
    "/{wbs_element_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="delete_wbs_element",
    dependencies=[Depends(RoleChecker(required_permission="wbs-element-delete"))],
)
async def delete_wbs_element(
    wbs_element_id: UUID,
    control_date: datetime | None = Query(
        None, description="Optional control date for deletion"
    ),
    current_user: UserIdentity = Depends(get_current_user),
    service: WBSElementService = Depends(get_wbs_element_service),
) -> None:
    """Soft delete a WBS Element. Requires delete permission."""
    try:
        await service.delete_wbe(
            wbe_id=wbs_element_id,
            actor_id=current_user.user_id,
            control_date=control_date,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get(
    "/{wbs_element_id}/history",
    response_model=list[WBSElementPublic],
    operation_id="get_wbs_element_history",
    dependencies=[Depends(RoleChecker(required_permission="wbs-element-read"))],
)
async def read_wbs_element_history(
    wbs_element_id: UUID,
    service: WBSElementService = Depends(get_wbs_element_service),
) -> Sequence[WBSElement]:
    """Get version history for a WBS Element. Requires read permission."""
    history = await service.get_history(wbs_element_id)
    if not history:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No history found for this WBS Element",
        )
    return history


@router.get(
    "/{wbs_element_id}/breadcrumb",
    operation_id="get_wbs_element_breadcrumb",
    dependencies=[Depends(RoleChecker(required_permission="wbs-element-read"))],
)
async def read_wbs_element_breadcrumb(
    wbs_element_id: UUID,
    branch: str = Query("main", description="Branch name"),
    branch_mode: BranchMode = Query(
        BranchMode.MERGED,
        description="Branch mode: merged or isolated",
    ),
    as_of: datetime | None = Query(
        None,
        description="Time travel: get breadcrumb as of this timestamp (ISO 8601)",
    ),
    service: WBSElementService = Depends(get_wbs_element_service),
) -> dict[str, Any]:
    """Get breadcrumb trail for a WBS Element (project + ancestor path).

    Requires read permission.
    """
    if as_of is None:
        from datetime import UTC

        as_of = datetime.now(tz=UTC)

    try:
        return await service.get_breadcrumb(
            wbs_element_id, branch=branch, branch_mode=branch_mode, as_of=as_of
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
