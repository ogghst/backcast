"""API routes for Schedule Baseline management."""

from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import RoleChecker, get_current_active_user
from app.db.session import get_db
from app.models.domain.schedule_baseline import ScheduleBaseline
from app.models.domain.user import User
from app.models.schemas.schedule_baseline import (
    ScheduleBaselineCreate,
    ScheduleBaselineRead,
    ScheduleBaselineUpdate,
)
from app.services.schedule_baseline_service import ScheduleBaselineService

router = APIRouter()


def get_schedule_baseline_service(
    session: AsyncSession = Depends(get_db),
) -> ScheduleBaselineService:
    return ScheduleBaselineService(session)


@router.get(
    "",
    response_model=None,  # Will be PaginatedResponse[ScheduleBaselineRead]
    operation_id="get_schedule_baselines",
    dependencies=[Depends(RoleChecker(required_permission="schedule-baseline-read"))],
)
async def read_schedule_baselines(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    per_page: int = Query(20, ge=1, description="Items per page"),
    branch: str = Query("main", description="Branch to query"),
    cost_element_id: UUID | None = Query(None, description="Filter by Cost Element ID"),
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Retrieve schedule baselines with pagination."""
    from typing import cast

    from sqlalchemy import func, select

    from app.models.schemas.common import PaginatedResponse

    skip = (page - 1) * per_page

    # Build query
    stmt = select(ScheduleBaseline).where(
        ScheduleBaseline.branch == branch,
        func.upper(cast(Any, ScheduleBaseline).valid_time).is_(None),
        cast(Any, ScheduleBaseline).deleted_at.is_(None),
    )

    # Apply optional filters
    if cost_element_id:
        stmt = stmt.where(ScheduleBaseline.cost_element_id == cost_element_id)

    # Get total count
    from sqlalchemy import func as sql_func

    count_stmt = select(sql_func.count()).select_from(stmt.subquery())
    result = await session.execute(count_stmt)
    total = result.scalar() or 0

    # Apply pagination
    stmt = stmt.offset(skip).limit(per_page)

    # Execute query
    result = await session.execute(stmt)
    items = result.scalars().all()

    # Convert to Pydantic models
    items_out = [ScheduleBaselineRead.model_validate(i) for i in items]

    # Return paginated response
    response = PaginatedResponse[ScheduleBaselineRead](
        items=items_out,
        total=total,
        page=page,
        per_page=per_page,
    )

    return response.model_dump()


@router.post(
    "",
    response_model=ScheduleBaselineRead,
    status_code=status.HTTP_201_CREATED,
    operation_id="create_schedule_baseline",
    dependencies=[Depends(RoleChecker(required_permission="schedule-baseline-create"))],
)
async def create_schedule_baseline(
    baseline_in: ScheduleBaselineCreate,
    current_user: User = Depends(get_current_active_user),
    service: ScheduleBaselineService = Depends(get_schedule_baseline_service),
) -> ScheduleBaseline:
    """Create a new schedule baseline in specified branch."""
    try:
        # Extract branch and control_date from request body
        # Note: Schema defaults branch to "main", but we enforce it here per "create on main first" policy
        branch = "main"  # Always create on main first
        control_date = baseline_in.control_date

        return await service.create(
            create_schema=baseline_in,
            actor_id=current_user.user_id,
            branch=branch,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.get(
    "/{schedule_baseline_id}",
    response_model=ScheduleBaselineRead,
    operation_id="get_schedule_baseline",
    dependencies=[Depends(RoleChecker(required_permission="schedule-baseline-read"))],
)
async def read_schedule_baseline(
    schedule_baseline_id: UUID,
    branch: str = Query("main", description="Branch to query"),
    as_of: datetime | None = Query(
        None,
        description="Time travel: get baseline state as of this timestamp (ISO 8601)",
    ),
    service: ScheduleBaselineService = Depends(get_schedule_baseline_service),
) -> ScheduleBaseline:
    """Get a specific schedule baseline by id and branch.

    Supports time-travel queries via the as_of parameter to view
    the baseline's state at any historical point in time.
    """
    # Default to current time if as_of is not provided
    if as_of is None:
        from datetime import UTC
        as_of = datetime.now(tz=UTC)

    if as_of:
        # Time travel query
        item = await service.get_as_of(
            entity_id=schedule_baseline_id,
            as_of=as_of,
            branch=branch,
        )
    else:
        # Current version
        item = await service.get_by_id(schedule_baseline_id, branch=branch)

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule Baseline not found in branch {branch}"
            + (f" as of {as_of}" if as_of else ""),
        )
    return item


@router.put(
    "/{schedule_baseline_id}",
    response_model=ScheduleBaselineRead,
    operation_id="update_schedule_baseline",
    dependencies=[Depends(RoleChecker(required_permission="schedule-baseline-update"))],
)
async def update_schedule_baseline(
    schedule_baseline_id: UUID,
    baseline_in: ScheduleBaselineUpdate,
    current_user: User = Depends(get_current_active_user),
    service: ScheduleBaselineService = Depends(get_schedule_baseline_service),
) -> ScheduleBaseline:
    """Update a schedule baseline. Creates new version or forks."""
    try:
        # Extract branch and control_date from request body
        branch = baseline_in.branch or "main"
        control_date = baseline_in.control_date

        # Get current version to check if it exists
        current = await service.get_by_id(schedule_baseline_id, branch=branch)
        if not current:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Schedule Baseline not found",
            )

        # Convert ScheduleBaselineUpdate to dict for update, excluding branch and control_date
        update_data = baseline_in.model_dump(exclude_unset=True, exclude={"branch", "control_date"})

        return await service.update(
            root_id=schedule_baseline_id,
            baseline_in=baseline_in,
            actor_id=current_user.user_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.delete(
    "/{schedule_baseline_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="delete_schedule_baseline",
    dependencies=[Depends(RoleChecker(required_permission="schedule-baseline-delete"))],
)
async def delete_schedule_baseline(
    schedule_baseline_id: UUID,
    branch: str = Query("main", description="Branch to delete from"),
    control_date: datetime | None = Query(
        None, description="Optional control date for deletion"
    ),
    current_user: User = Depends(get_current_active_user),
    service: ScheduleBaselineService = Depends(get_schedule_baseline_service),
) -> None:
    """Soft delete a schedule baseline in a branch."""
    try:
        item = await service.get_by_id(schedule_baseline_id, branch=branch)
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Schedule Baseline not found in branch {branch}",
            )

        await service.soft_delete(
            root_id=schedule_baseline_id,
            actor_id=current_user.user_id,
            branch=branch,
            control_date=control_date,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get(
    "/{schedule_baseline_id}/history",
    response_model=list[ScheduleBaselineRead],
    operation_id="get_schedule_baseline_history",
    dependencies=[Depends(RoleChecker(required_permission="schedule-baseline-read"))],
)
async def get_schedule_baseline_history(
    schedule_baseline_id: UUID,
    service: ScheduleBaselineService = Depends(get_schedule_baseline_service),
) -> Sequence[ScheduleBaseline]:
    """Get full version history for a schedule baseline across all branches."""
    return await service.get_history(schedule_baseline_id)


@router.get(
    "/{schedule_baseline_id}/pv",
    operation_id="calculate_planned_value",
    dependencies=[Depends(RoleChecker(required_permission="schedule-baseline-read"))],
)
async def calculate_planned_value(
    schedule_baseline_id: UUID,
    current_date: datetime = Query(
        ..., description="Date to calculate PV for (ISO 8601)"
    ),
    bac: Decimal = Query(..., description="Budget at Completion (BAC) amount"),
    branch: str = Query("main", description="Branch to query"),
    service: ScheduleBaselineService = Depends(get_schedule_baseline_service),
) -> dict[str, Any]:
    """Calculate Planned Value (PV) for a schedule baseline.

    PV = BAC × Progress

    Where Progress is calculated based on the baseline's progression type
    (LINEAR, GAUSSIAN, or LOGARITHMIC) and the current date relative to
    the baseline's start and end dates.

    Args:
        schedule_baseline_id: The baseline to calculate PV for
        current_date: The date to calculate progress for
        bac: Budget at Completion (total planned budget)
        branch: Branch to query (default: "main")

    Returns:
        Dictionary with:
        - schedule_baseline_id: The baseline ID
        - current_date: The date used for calculation
        - bac: Budget at Completion
        - progress: Progress value (0.0 to 1.0)
        - pv: Planned Value (BAC × Progress)
        - progression_type: Type of progression used
    """
    # Get the baseline
    baseline = await service.get_by_id(schedule_baseline_id, branch=branch)
    if not baseline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule Baseline not found in branch {branch}",
        )

    # Import progression strategies
    from app.services.progression.gaussian import GaussianProgression
    from app.services.progression.linear import LinearProgression
    from app.services.progression.logarithmic import LogarithmicProgression

    # Select progression strategy based on baseline type
    progression_map = {
        "LINEAR": LinearProgression(),
        "GAUSSIAN": GaussianProgression(),
        "LOGARITHMIC": LogarithmicProgression(),
    }

    strategy = progression_map.get(baseline.progression_type)
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown progression type: {baseline.progression_type}",
        )

    # Calculate progress
    progress = strategy.calculate_progress(
        current_date, baseline.start_date, baseline.end_date
    )

    # Calculate PV = BAC × Progress
    pv = bac * Decimal(str(progress))

    return {
        "schedule_baseline_id": schedule_baseline_id,
        "current_date": current_date,
        "bac": str(bac),
        "progress": progress,
        "pv": str(pv),
        "progression_type": baseline.progression_type,
    }
