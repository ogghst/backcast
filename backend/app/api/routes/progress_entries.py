"""Progress Entry API routes - CRUD for work completion tracking."""

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import RoleChecker, get_current_active_user
from app.db.session import get_db
from app.models.domain.progress_entry import ProgressEntry
from app.models.domain.user import User
from app.models.schemas.common import PaginatedResponse
from app.models.schemas.progress_entry import (
    ProgressEntryCreate,
    ProgressEntryRead,
    ProgressEntryUpdate,
)
from app.services.progress_entry_service import ProgressEntryService

router = APIRouter()


def get_progress_entry_service(
    session: AsyncSession = Depends(get_db),
) -> ProgressEntryService:
    """Dependency to get ProgressEntryService instance."""
    return ProgressEntryService(session)


@router.get(
    "",
    response_model=None,  # PaginatedResponse[ProgressEntryRead]
    operation_id="get_progress_entries",
    dependencies=[Depends(RoleChecker(required_permission="progress-entry-read"))],
)
async def read_progress_entries(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    per_page: int = Query(20, ge=1, description="Items per page"),
    cost_element_id: UUID | None = Query(None, description="Filter by Cost Element ID"),
    as_of: datetime | None = Query(
        None,
        description="Time travel: get Progress Entries as of this timestamp (ISO 8601)",
    ),
    service: ProgressEntryService = Depends(get_progress_entry_service),
) -> dict[str, Any]:
    """Retrieve progress entries with filtering and pagination.

    Progress entries track work completion percentage for cost elements.
    They are versionable but NOT branchable (progress is global facts).
    """
    # Build filters dict
    query_filters: dict[str, Any] = {}
    if cost_element_id:
        query_filters["cost_element_id"] = cost_element_id

    skip = (page - 1) * per_page

    # Default to current time if as_of is not provided
    if as_of is None:
        from datetime import UTC
        as_of = datetime.now(tz=UTC)

    items, total = await service.get_progress_history(
        cost_element_id=cost_element_id if cost_element_id else UUID("00000000-0000-0000-0000-000000000000"),  # Dummy ID for list all
        skip=skip,
        limit=per_page,
        as_of=as_of,
    )

    # Convert to Pydantic models
    items_out = [ProgressEntryRead.model_validate(i) for i in items]

    # Return paginated response
    response = PaginatedResponse[ProgressEntryRead](
        items=items_out,
        total=total,
        page=page,
        per_page=per_page,
    )

    return response.model_dump()


@router.post(
    "",
    response_model=ProgressEntryRead,
    status_code=status.HTTP_201_CREATED,
    operation_id="create_progress_entry",
    dependencies=[Depends(RoleChecker(required_permission="progress-entry-create"))],
)
async def create_progress_entry(
    progress_in: ProgressEntryCreate,
    current_user: User = Depends(get_current_active_user),
    service: ProgressEntryService = Depends(get_progress_entry_service),
) -> ProgressEntry:
    """Create a new progress entry.

    Progress entries track work completion percentage (0-100%) for cost elements.
    This enables Earned Value Management (EVM) calculations.

    Validation:
    - progress_percentage must be between 0 and 100
    - cost_element_id must reference an existing cost element
    - control_date determines when the progress was measured (defaults to now)
    """
    try:
        progress = await service.create(
            progress_in=progress_in,
            actor_id=current_user.user_id,
        )
        return progress
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.get(
    "/{progress_entry_id}",
    response_model=ProgressEntryRead,
    operation_id="get_progress_entry",
    dependencies=[Depends(RoleChecker(required_permission="progress-entry-read"))],
)
async def read_progress_entry(
    progress_entry_id: UUID,
    as_of: datetime | None = Query(
        None,
        description="Time travel: get Progress Entry as of this timestamp (ISO 8601)",
    ),
    service: ProgressEntryService = Depends(get_progress_entry_service),
) -> ProgressEntry:
    """Retrieve a specific progress entry by ID.

    Supports time-travel queries via the as_of parameter.
    """
    # Default to current time if as_of is not provided
    if as_of is None:
        from datetime import UTC
        as_of = datetime.now(tz=UTC)

    if as_of:
        # Time-travel query
        progress = await service.get_progress_entry_as_of(
            progress_entry_id=progress_entry_id,
            as_of=as_of,
        )

    if progress is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Progress entry {progress_entry_id} not found",
        )

    return progress


@router.put(
    "/{progress_entry_id}",
    response_model=ProgressEntryRead,
    operation_id="update_progress_entry",
    dependencies=[Depends(RoleChecker(required_permission="progress-entry-update"))],
)
async def update_progress_entry(
    progress_entry_id: UUID,
    progress_in: ProgressEntryUpdate,
    current_user: User = Depends(get_current_active_user),
    service: ProgressEntryService = Depends(get_progress_entry_service),
) -> ProgressEntry:
    """Update a progress entry.

    Creates a new version of the progress entry with the updated values.
    Progress can be increased or decreased (decreases should include justification in notes).

    The system will maintain full version history for audit trails.
    """
    try:
        progress = await service.update(
            progress_entry_id=progress_entry_id,
            progress_in=progress_in,
            actor_id=current_user.user_id,
        )
        return progress
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except HTTPException:
        raise


@router.delete(
    "/{progress_entry_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="delete_progress_entry",
    dependencies=[Depends(RoleChecker(required_permission="progress-entry-delete"))],
)
async def delete_progress_entry(
    progress_entry_id: UUID,
    current_user: User = Depends(get_current_active_user),
    service: ProgressEntryService = Depends(get_progress_entry_service),
) -> None:
    """Soft delete a progress entry.

    Marks the progress entry as deleted but preserves it in the database
    for audit purposes. The entry can be restored if needed.
    """
    await service.soft_delete(
        progress_entry_id=progress_entry_id,
        actor_id=current_user.user_id,
    )


@router.get(
    "/cost-element/{cost_element_id}/latest",
    response_model=ProgressEntryRead | None,
    operation_id="get_latest_progress",
    dependencies=[Depends(RoleChecker(required_permission="progress-entry-read"))],
)
async def read_latest_progress(
    cost_element_id: UUID,
    as_of: datetime | None = Query(
        None,
        description="Time travel: get latest progress as of this timestamp (ISO 8601)",
    ),
    service: ProgressEntryService = Depends(get_progress_entry_service),
) -> ProgressEntry | None:
    """Retrieve the latest progress entry for a cost element.

    Returns the most recent progress entry based on valid_time.
    Supports time-travel queries via the as_of parameter.

    Returns None if no progress has been reported for the cost element.
    """
    # Default to current time if as_of is not provided
    if as_of is None:
        from datetime import UTC
        as_of = datetime.now(tz=UTC)

    progress = await service.get_latest_progress(
        cost_element_id=cost_element_id,
        as_of=as_of,
    )

    return progress


@router.get(
    "/cost-element/{cost_element_id}/history",
    response_model=None,  # PaginatedResponse[ProgressEntryRead]
    operation_id="get_progress_history",
    dependencies=[Depends(RoleChecker(required_permission="progress-entry-read"))],
)
async def read_progress_history(
    cost_element_id: UUID,
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    per_page: int = Query(20, ge=1, description="Items per page"),
    service: ProgressEntryService = Depends(get_progress_entry_service),
) -> dict[str, Any]:
    """Retrieve progress history for a cost element.

    Returns all progress entries for the specified cost element,
    ordered by valid_time descending (most recent first).

    Useful for generating progress charts and historical analysis.
    """
    skip = (page - 1) * per_page

    items, total = await service.get_progress_history(
        cost_element_id=cost_element_id,
        skip=skip,
        limit=per_page,
    )

    # Convert to Pydantic models
    items_out = [ProgressEntryRead.model_validate(i) for i in items]

    # Return paginated response
    response = PaginatedResponse[ProgressEntryRead](
        items=items_out,
        total=total,
        page=page,
        per_page=per_page,
    )

    return response.model_dump()
