"""Dashboard Layout API routes with authentication."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import RoleChecker, get_current_active_user
from app.db.session import get_db
from app.models.domain.user import User
from app.models.schemas.dashboard_layout import (
    CloneTemplateRequest,
    DashboardLayoutCreate,
    DashboardLayoutRead,
    DashboardLayoutUpdate,
)
from app.services.dashboard_layout_service import DashboardLayoutService

router = APIRouter()


def get_dashboard_layout_service(
    session: AsyncSession = Depends(get_db),
) -> DashboardLayoutService:
    """Get DashboardLayoutService instance.

    Args:
        session: Database session

    Returns:
        DashboardLayoutService instance
    """
    return DashboardLayoutService(session)


@router.get(
    "",
    response_model=list[DashboardLayoutRead],
    operation_id="list_dashboard_layouts",
    dependencies=[Depends(RoleChecker(required_permission="project-read"))],
)
async def list_dashboard_layouts(
    project_id: UUID | None = Query(None),
    current_user: User = Depends(get_current_active_user),
    service: DashboardLayoutService = Depends(get_dashboard_layout_service),
) -> list[DashboardLayoutRead]:
    """List dashboard layouts for the current user, optionally filtered by project."""
    layouts = await service.get_for_user_project(current_user.user_id, project_id)
    return [DashboardLayoutRead.model_validate(layout) for layout in layouts]


@router.get(
    "/templates",
    response_model=list[DashboardLayoutRead],
    operation_id="list_dashboard_layout_templates",
    dependencies=[Depends(RoleChecker(required_permission="project-read"))],
)
async def list_dashboard_layout_templates(
    current_user: User = Depends(get_current_active_user),
    service: DashboardLayoutService = Depends(get_dashboard_layout_service),
) -> list[DashboardLayoutRead]:
    """List all template dashboard layouts."""
    layouts = await service.get_templates()
    return [DashboardLayoutRead.model_validate(layout) for layout in layouts]


@router.get(
    "/{layout_id}",
    response_model=DashboardLayoutRead,
    operation_id="get_dashboard_layout",
    dependencies=[Depends(RoleChecker(required_permission="project-read"))],
)
async def get_dashboard_layout(
    layout_id: UUID,
    current_user: User = Depends(get_current_active_user),
    service: DashboardLayoutService = Depends(get_dashboard_layout_service),
) -> DashboardLayoutRead:
    """Get a specific dashboard layout by ID."""
    layout = await service.get(layout_id)
    if layout is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dashboard layout not found",
        )
    if layout.user_id != current_user.user_id and not layout.is_template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dashboard layout not found",
        )
    return DashboardLayoutRead.model_validate(layout)


@router.post(
    "",
    response_model=DashboardLayoutRead,
    status_code=status.HTTP_201_CREATED,
    operation_id="create_dashboard_layout",
    dependencies=[Depends(RoleChecker(required_permission="project-read"))],
)
async def create_dashboard_layout(
    layout_in: DashboardLayoutCreate,
    current_user: User = Depends(get_current_active_user),
    service: DashboardLayoutService = Depends(get_dashboard_layout_service),
) -> DashboardLayoutRead:
    """Create a new dashboard layout."""
    layout = await service.create(
        user_id=current_user.user_id, **layout_in.model_dump()
    )
    return DashboardLayoutRead.model_validate(layout)


@router.put(
    "/{layout_id}",
    response_model=DashboardLayoutRead,
    operation_id="update_dashboard_layout",
)
async def update_dashboard_layout(
    layout_id: UUID,
    layout_update: DashboardLayoutUpdate,
    current_user: User = Depends(get_current_active_user),
    service: DashboardLayoutService = Depends(get_dashboard_layout_service),
) -> DashboardLayoutRead:
    """Update an existing dashboard layout."""
    try:
        layout = await service.update(
            layout_id,
            user_id=current_user.user_id,
            **layout_update.model_dump(exclude_unset=True),
        )
    except ValueError as e:
        msg = str(e)
        if "not found" in msg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=msg
            ) from e
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=msg) from e
    return DashboardLayoutRead.model_validate(layout)


@router.delete(
    "/{layout_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="delete_dashboard_layout",
    dependencies=[Depends(RoleChecker(required_permission="project-read"))],
)
async def delete_dashboard_layout(
    layout_id: UUID,
    current_user: User = Depends(get_current_active_user),
    service: DashboardLayoutService = Depends(get_dashboard_layout_service),
) -> None:
    """Delete a dashboard layout."""
    try:
        deleted = await service.delete(layout_id, user_id=current_user.user_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dashboard layout not found",
        )


@router.post(
    "/{layout_id}/clone",
    response_model=DashboardLayoutRead,
    status_code=status.HTTP_201_CREATED,
    operation_id="clone_dashboard_layout_template",
    dependencies=[Depends(RoleChecker(required_permission="project-read"))],
)
async def clone_dashboard_layout_template(
    layout_id: UUID,
    clone_in: CloneTemplateRequest,
    current_user: User = Depends(get_current_active_user),
    service: DashboardLayoutService = Depends(get_dashboard_layout_service),
) -> DashboardLayoutRead:
    """Clone a template dashboard layout for the current user."""
    try:
        layout = await service.clone_template(
            layout_id, current_user.user_id, clone_in.project_id
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e
    return DashboardLayoutRead.model_validate(layout)


@router.put(
    "/templates/{layout_id}",
    response_model=DashboardLayoutRead,
    operation_id="update_dashboard_layout_template",
    dependencies=[
        Depends(RoleChecker(required_permission="dashboard-template-update"))
    ],
)
async def update_dashboard_layout_template(
    layout_id: UUID,
    layout_update: DashboardLayoutUpdate,
    current_user: User = Depends(get_current_active_user),
    service: DashboardLayoutService = Depends(get_dashboard_layout_service),
) -> DashboardLayoutRead:
    """Update a template dashboard layout (admin only).

    Allows administrators to modify template layouts. Non-admin users
    receive a 403 response from the RoleChecker dependency.
    """
    try:
        layout = await service.update_template(
            layout_id,
            **layout_update.model_dump(exclude_unset=True),
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    return DashboardLayoutRead.model_validate(layout)
