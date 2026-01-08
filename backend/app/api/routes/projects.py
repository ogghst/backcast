"""Project API routes with RBAC."""

from collections.abc import Sequence
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import RoleChecker, get_current_active_user
from app.db.session import get_db
from app.models.domain.project import Project
from app.models.domain.user import User
from app.models.schemas.project import (
    ProjectCreate,
    ProjectPublic,
    ProjectUpdate,
)
from app.services.project import ProjectService

router = APIRouter()


def get_project_service(
    session: AsyncSession = Depends(get_db),
) -> ProjectService:
    return ProjectService(session)


@router.get(
    "",
    response_model=None,  # Will be PaginatedResponse[ProjectPublic] but FastAPI needs explicit type
    operation_id="get_projects",
    dependencies=[Depends(RoleChecker(required_permission="project-read"))],
)
async def read_projects(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    branch: str = Query("main", description="Branch name"),
    search: str | None = Query(None, description="Search term (code, name)"),
    filters: str | None = Query(
        None,
        description="Filters in format 'column:value;column:value1,value2'",
        example="status:Active;code:PROJ",
    ),
    sort_field: str | None = Query(None, description="Field to sort by"),
    sort_order: str = Query(
        "asc",
        regex="^(asc|desc)$",
        description="Sort order (asc or desc)",
    ),
    service: ProjectService = Depends(get_project_service),
) -> dict:
    """Retrieve projects with server-side search, filtering, and sorting.

    Supports:
    - **Search**: Case-insensitive search across code and name
    - **Filters**: Filter by status, code, name (format: "column:value;column:value1,value2")
    - **Sorting**: Sort by any field (asc/desc)
    - **Pagination**: Returns total count for proper pagination UI

    Requires read permission.
    """
    from app.models.schemas.common import PaginatedResponse

    # Calculate skip from page number
    skip = (page - 1) * per_page

    try:
        # Get projects with filters
        projects, total = await service.get_projects(
            skip=skip,
            limit=per_page,
            branch=branch,
            search=search,
            filters=filters,
            sort_field=sort_field,
            sort_order=sort_order,
        )

        # Convert to Pydantic models
        from app.models.schemas.project import ProjectPublic

        items = [ProjectPublic.model_validate(p) for p in projects]

        # Return paginated response
        response = PaginatedResponse[ProjectPublic](
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
    response_model=ProjectPublic,
    status_code=status.HTTP_201_CREATED,
    operation_id="create_project",
    dependencies=[Depends(RoleChecker(required_permission="project-create"))],
)
async def create_project(
    project_in: ProjectCreate,
    current_user: User = Depends(get_current_active_user),
    service: ProjectService = Depends(get_project_service),
) -> Project:
    """Create a new project. Requires create permission."""
    try:
        # Check if project code already exists
        existing = await service.get_by_code(project_in.code)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Project with code '{project_in.code}' already exists",
            )

        project = await service.create_project(
            project_in=project_in, actor_id=current_user.user_id
        )
        return project
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.get(
    "/{project_id}",
    response_model=ProjectPublic,
    operation_id="get_project",
    dependencies=[Depends(RoleChecker(required_permission="project-read"))],
)
async def read_project(
    project_id: UUID,
    service: ProjectService = Depends(get_project_service),
) -> Project:
    """Get a specific project by id. Requires read permission."""
    project = await service.get_by_root_id(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    return project


@router.put(
    "/{project_id}",
    response_model=ProjectPublic,
    operation_id="update_project",
    dependencies=[Depends(RoleChecker(required_permission="project-update"))],
)
async def update_project(
    project_id: UUID,
    project_in: ProjectUpdate,
    current_user: User = Depends(get_current_active_user),
    service: ProjectService = Depends(get_project_service),
) -> Project:
    """Update a project. Requires update permission."""
    try:
        updated_project = await service.update_project(
            project_id=project_id,
            project_in=project_in,
            actor_id=current_user.user_id,
        )
        return updated_project
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="delete_project",
    dependencies=[Depends(RoleChecker(required_permission="project-delete"))],
)
async def delete_project(
    project_id: UUID,
    current_user: User = Depends(get_current_active_user),
    service: ProjectService = Depends(get_project_service),
) -> None:
    """Soft delete a project. Requires delete permission."""
    try:
        await service.delete_project(project_id=project_id, actor_id=current_user.user_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get(
    "/{project_id}/history",
    response_model=list[ProjectPublic],
    operation_id="get_project_history",
    dependencies=[Depends(RoleChecker(required_permission="project-read"))],
)
async def read_project_history(
    project_id: UUID,
    service: ProjectService = Depends(get_project_service),
) -> Sequence[Project]:
    """Get version history for a project. Requires read permission."""
    history = await service.get_project_history(project_id)
    if not history:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No history found for this project",
        )
    return history
