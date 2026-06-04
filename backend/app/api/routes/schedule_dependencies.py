"""API routes for Schedule Dependency management."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import RoleChecker, UserIdentity, get_current_user
from app.db.session import get_db
from app.models.schemas.schedule_dependency import (
    ScheduleDependencyCreate,
    ScheduleDependencyRead,
    ScheduleDependencyUpdate,
)
from app.services.schedule_dependency_service import (
    CircularDependencyError,
    DuplicateDependencyError,
    ScheduleDependencyService,
    ScheduleNotFoundError,
    SelfReferenceError,
)

router = APIRouter()


def get_schedule_dependency_service(
    session: AsyncSession = Depends(get_db),
) -> ScheduleDependencyService:
    return ScheduleDependencyService(session)


def _map_dependency_errors(exc: Exception) -> HTTPException:
    """Convert service exceptions to HTTP responses."""
    if isinstance(exc, SelfReferenceError):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    if isinstance(exc, ScheduleNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, DuplicateDependencyError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    if isinstance(exc, CircularDependencyError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
    )


@router.get(
    "",
    response_model=list[ScheduleDependencyRead],
    operation_id="list_schedule_dependencies",
    dependencies=[Depends(RoleChecker(required_permission="schedule-dependency-read"))],
)
async def list_schedule_dependencies(
    project_id: UUID = Query(..., description="Project root ID"),
    branch: str = Query("main", description="Branch name"),
    schedule_baseline_id: UUID | None = Query(
        None, description="Filter by schedule baseline ID"
    ),
    service: ScheduleDependencyService = Depends(get_schedule_dependency_service),
) -> list[ScheduleDependencyRead]:
    """List schedule dependencies for a project or a specific schedule baseline."""
    if schedule_baseline_id is not None:
        items = await service.list_for_schedule(schedule_baseline_id, branch=branch)
    else:
        items = await service.list_for_project(project_id, branch=branch)
    return [ScheduleDependencyRead.model_validate(item) for item in items]


@router.post(
    "",
    response_model=ScheduleDependencyRead,
    status_code=status.HTTP_201_CREATED,
    operation_id="create_schedule_dependency",
    dependencies=[
        Depends(RoleChecker(required_permission="schedule-dependency-create"))
    ],
)
async def create_schedule_dependency(
    dependency_in: ScheduleDependencyCreate,
    current_user: UserIdentity = Depends(get_current_user),
    service: ScheduleDependencyService = Depends(get_schedule_dependency_service),
) -> ScheduleDependencyRead:
    """Create a new schedule dependency between two schedule baselines."""
    try:
        dependency = await service.create(dependency_in, actor_id=current_user.user_id)
        return ScheduleDependencyRead.model_validate(dependency)
    except (
        SelfReferenceError,
        ScheduleNotFoundError,
        DuplicateDependencyError,
        CircularDependencyError,
    ) as exc:
        raise _map_dependency_errors(exc) from exc


@router.get(
    "/{schedule_dependency_id}",
    response_model=ScheduleDependencyRead,
    operation_id="get_schedule_dependency",
    dependencies=[Depends(RoleChecker(required_permission="schedule-dependency-read"))],
)
async def get_schedule_dependency(
    schedule_dependency_id: UUID,
    service: ScheduleDependencyService = Depends(get_schedule_dependency_service),
) -> ScheduleDependencyRead:
    """Get a single schedule dependency by its root ID."""
    item = await service.get_by_id(schedule_dependency_id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule Dependency {schedule_dependency_id} not found",
        )
    return ScheduleDependencyRead.model_validate(item)


@router.put(
    "/{schedule_dependency_id}",
    response_model=ScheduleDependencyRead,
    operation_id="update_schedule_dependency",
    dependencies=[
        Depends(RoleChecker(required_permission="schedule-dependency-update"))
    ],
)
async def update_schedule_dependency(
    schedule_dependency_id: UUID,
    dependency_in: ScheduleDependencyUpdate,
    service: ScheduleDependencyService = Depends(get_schedule_dependency_service),
) -> ScheduleDependencyRead:
    """Update mutable fields of a schedule dependency."""
    try:
        item = await service.update(schedule_dependency_id, dependency_in)
        if item is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Schedule Dependency {schedule_dependency_id} not found",
            )
        return ScheduleDependencyRead.model_validate(item)
    except (DuplicateDependencyError, CircularDependencyError) as exc:
        raise _map_dependency_errors(exc) from exc


@router.delete(
    "/{schedule_dependency_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="delete_schedule_dependency",
    dependencies=[
        Depends(RoleChecker(required_permission="schedule-dependency-delete"))
    ],
)
async def delete_schedule_dependency(
    schedule_dependency_id: UUID,
    service: ScheduleDependencyService = Depends(get_schedule_dependency_service),
) -> None:
    """Delete a schedule dependency."""
    deleted = await service.delete(schedule_dependency_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule Dependency {schedule_dependency_id} not found",
        )
