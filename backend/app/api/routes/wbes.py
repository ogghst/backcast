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
    response_model=list[WBEPublic],
    operation_id="get_wbes",
    dependencies=[Depends(RoleChecker(required_permission="wbe-read"))],
)
async def read_wbes(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    project_id: UUID | None = Query(None, description="Filter by project ID"),
    branch: str = Query("main", description="Branch name"),
    service: WBEService = Depends(get_wbe_service),
) -> Sequence[WBE]:
    """Retrieve WBEs. Requires read permission."""
    if project_id:
        return await service.get_by_project(project_id=project_id, branch=branch)
    return await service.get_wbes(skip=skip, limit=limit, branch=branch)


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
    wbe = await service.get_wbe(wbe_id)
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
