"""Project API routes with RBAC."""

from collections.abc import Sequence
from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import (
    ProjectRoleChecker,
    RoleChecker,
    get_current_active_user,
)
from app.core.rbac import RBACServiceABC, get_rbac_service
from app.db.session import get_db
from app.models.domain.project import Project
from app.models.domain.user import User
from app.models.schemas.branch import BranchPublic
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
    per_page: int = Query(20, ge=1, description="Items per page"),
    branch: str = Query("main", description="Branch name"),
    mode: str = Query(
        "merged",
        pattern="^(merged|isolated)$",
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
        description="Time travel: get Projects as of this timestamp (ISO 8601)",
    ),
    current_user: User = Depends(get_current_active_user),
    rbac_service: RBACServiceABC = Depends(get_rbac_service),
    service: ProjectService = Depends(get_project_service),
) -> dict[str, Any]:
    """Retrieve projects with server-side search, filtering, and sorting.

    Supports:
    - **Search**: Case-insensitive search across code and name
    - **Filters**: Filter by status, code, name (format: "column:value;column:value1,value2")
    - **Sorting**: Sort by any field (asc/desc)
    - **Pagination**: Returns total count for proper pagination UI
    - **Mode**: Branch mode - "merged" (combine with main) or "isolated" (current branch only)

    Requires read permission. Non-admin users only see projects they are members of.
    """
    from app.core.versioning.enums import BranchMode
    from app.models.schemas.common import PaginatedResponse

    # Parse mode string to BranchMode enum
    branch_mode = BranchMode.MERGE if mode == "merged" else BranchMode.STRICT

    # Calculate skip from page number
    skip = (page - 1) * per_page

    # Default to current time if as_of is not provided
    if as_of is None:
        from datetime import UTC

        as_of = datetime.now(tz=UTC)

    try:
        # Get projects with filters
        projects, total = await service.get_projects(
            skip=skip,
            limit=per_page,
            branch=branch,
            branch_mode=branch_mode,
            search=search,
            filters=filters,
            sort_field=sort_field,
            sort_order=sort_order,
            as_of=as_of,
        )

        # Filter projects by user's access for non-admin users
        if current_user.role != "admin":
            accessible_project_ids = await rbac_service.get_user_projects(
                user_id=current_user.user_id,
                user_role=current_user.role,
            )
            # Filter projects to only those the user can access
            projects = [p for p in projects if p.project_id in accessible_project_ids]
            total = len(projects)

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
            project_in=project_in,
            actor_id=current_user.user_id,
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
)
async def read_project(
    project_id: UUID,
    branch: str = Query("main", description="Branch name"),
    as_of: datetime | None = Query(
        None,
        description="Time travel: get project state as of this timestamp (ISO 8601)",
    ),
    current_user: User = Depends(
        ProjectRoleChecker(required_permission="project-read")
    ),
    service: ProjectService = Depends(get_project_service),
) -> Project:
    """Get a specific project by id. Requires read permission.

    Supports time-travel queries via the as_of parameter to view
    the project's state at any historical point in time.
    """
    # Default to current time if as_of is not provided
    if as_of is None:
        from datetime import UTC

        as_of = datetime.now(tz=UTC)

    if as_of:
        # Time travel query
        project = await service.get_project_as_of(project_id, as_of, branch=branch)
    else:
        project = await service.get_as_of(project_id, branch=branch)

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project not found in branch '{branch}'"
            + (f" as of {as_of}" if as_of else ""),
        )
    return project


@router.put(
    "/{project_id}",
    response_model=ProjectPublic,
    operation_id="update_project",
)
async def update_project(
    project_id: UUID,
    project_in: ProjectUpdate,
    current_user: User = Depends(
        ProjectRoleChecker(required_permission="project-update")
    ),
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
    except IntegrityError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database integrity error during project update",
        ) from e


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="delete_project",
)
async def delete_project(
    project_id: UUID,
    control_date: datetime | None = Query(
        None, description="Optional control date for deletion"
    ),
    current_user: User = Depends(
        ProjectRoleChecker(required_permission="project-delete")
    ),
    service: ProjectService = Depends(get_project_service),
) -> None:
    """Soft delete a project. Requires delete permission."""
    try:
        await service.delete_project(
            project_id=project_id,
            actor_id=current_user.user_id,
            control_date=control_date,
        )
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


@router.get(
    "/{project_id}/branches",
    response_model=list[BranchPublic],
    operation_id="get_project_branches",
    dependencies=[Depends(RoleChecker(required_permission="project-read"))],
)
async def read_project_branches(
    project_id: UUID,
    as_of: datetime | None = Query(
        None,
        description="Time travel: get branches as of this timestamp (ISO 8601)",
    ),
    service: ProjectService = Depends(get_project_service),
) -> list[BranchPublic]:
    """Get all branches for a project.

    Returns the main branch plus any change order branches (BR-{code})
    that exist for this project.

    Requires read permission.
    """
    # Default to current time if as_of is not provided
    if as_of is None:
        from datetime import UTC

        as_of = datetime.now(tz=UTC)

    return await service.get_project_branches(project_id, as_of=as_of)
