"""Quality Events API routes - CRUD for quality event tracking."""

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import RoleChecker, get_current_active_user
from app.db.session import get_db
from app.models.domain.quality_event import QualityEvent
from app.models.domain.user import User
from app.models.schemas.common import PaginatedResponse
from app.models.schemas.quality_event import (
    QualityEventCreate,
    QualityEventRead,
    QualityEventUpdate,
)
from app.services.quality_event_service import QualityEventService

router = APIRouter()


def _default_as_of(as_of: datetime | None) -> datetime:
    """Return as_of if provided, otherwise current UTC time."""
    if as_of is not None:
        return as_of
    return datetime.now(tz=UTC)


def get_quality_event_service(
    session: AsyncSession = Depends(get_db),
) -> QualityEventService:
    """Dependency to get QualityEventService instance."""
    return QualityEventService(session)


@router.get(
    "",
    response_model=None,  # PaginatedResponse[QualityEventRead]
    operation_id="get_quality_events",
    dependencies=[Depends(RoleChecker(required_permission="quality-event-read"))],
)
async def read_quality_events(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    per_page: int = Query(20, ge=1, description="Items per page"),
    branch: str = Query("main", description="Branch to query (for context)"),
    mode: str = Query(
        "merged",
        pattern="^(merged|isolated)$",
        description="Branch mode: merged (combine with main) or isolated (current branch only)",
    ),
    cost_element_id: UUID | None = Query(None, description="Filter by Cost Element ID"),
    wbe_id: UUID | None = Query(
        None, description="Filter by WBE ID (returns all events under this WBE)"
    ),
    project_id: UUID | None = Query(
        None,
        description="Filter by Project ID (returns all events under this project)",
    ),
    event_type: str | None = Query(
        None, description="Filter by event type (defect, rework, scrap, warranty, other)"
    ),
    severity: str | None = Query(
        None, description="Filter by severity (low, medium, high, critical)"
    ),
    as_of: datetime | None = Query(
        None,
        description="Time travel: get Quality Events as of this timestamp (ISO 8601)",
    ),
    service: QualityEventService = Depends(get_quality_event_service),
) -> dict[str, Any]:
    """Retrieve quality events with filtering and pagination.

    Quality events track rework costs and quality issues against cost elements.
    They are versionable but NOT branchable (quality events are global facts).
    Branch and mode parameters are provided for API consistency and context,
    though quality events themselves are not branch-specific.

    Filtering hierarchy: cost_element_id > wbe_id > project_id.
    When multiple are provided, all applicable filters are applied (AND).
    """
    # Build filters dict
    query_filters: dict[str, Any] = {}
    if cost_element_id:
        query_filters["cost_element_id"] = cost_element_id
    if event_type:
        query_filters["event_type"] = event_type
    if severity:
        query_filters["severity"] = severity

    skip = (page - 1) * per_page

    # Default to current time if as_of is not provided
    if as_of is None:
        as_of = datetime.now(tz=UTC)

    items, total = await service.get_quality_events(
        filters=query_filters,
        skip=skip,
        limit=per_page,
        as_of=as_of,
        wbe_id=wbe_id,
        project_id=project_id,
    )

    # Convert to Pydantic models
    items_out = [QualityEventRead.model_validate(i) for i in items]

    # Return paginated response
    response = PaginatedResponse[QualityEventRead](
        items=items_out,
        total=total,
        page=page,
        per_page=per_page,
    )

    return response.model_dump()


@router.post(
    "",
    response_model=QualityEventRead,
    status_code=status.HTTP_201_CREATED,
    operation_id="create_quality_event",
    dependencies=[Depends(RoleChecker(required_permission="quality-event-write"))],
)
async def create_quality_event(
    event_in: QualityEventCreate,
    branch: str = Query("main", description="Branch to check cost element against"),
    current_user: User = Depends(get_current_active_user),
    service: QualityEventService = Depends(get_quality_event_service),
) -> QualityEvent:
    """Create a new quality event.

    The control_date parameter allows setting the valid_time start date,
    useful for backdated quality events or testing time-travel scenarios.
    """
    try:
        event = await service.create_quality_event(
            event_in=event_in,
            actor_id=current_user.user_id,
            branch=branch,
        )
        return event
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


# CRITICAL: Specific routes must be defined BEFORE the generic /{quality_event_id} route
# to avoid FastAPI matching "by-period" or "total" as a quality_event_id UUID.


@router.get(
    "/cost-element/{cost_element_id}/total",
    operation_id="get_quality_event_total",
    dependencies=[Depends(RoleChecker(required_permission="quality-event-read"))],
)
async def get_quality_event_total(
    cost_element_id: UUID,
    as_of: datetime | None = Query(
        None,
        description="Time travel: get total as of this timestamp (ISO 8601)",
    ),
    service: QualityEventService = Depends(get_quality_event_service),
) -> dict[str, Any]:
    """Get total quality event costs for a cost element with time-travel support.

    Returns the sum of all cost_impact values for quality events associated
    with the specified cost element. Useful for displaying total rework costs.

    The as_of parameter allows viewing the total at any historical point in time,
    showing only quality events that were valid as of that timestamp.
    """
    # Default to current time if as_of is not provided
    if as_of is None:
        as_of = datetime.now(tz=UTC)

    try:
        total = await service.get_total_for_cost_element(
            cost_element_id, as_of=as_of
        )
        return {
            "cost_element_id": str(cost_element_id),
            "total_cost_impact": float(total),
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


@router.get(
    "/by-period",
    operation_id="get_quality_events_by_period",
    dependencies=[Depends(RoleChecker(required_permission="quality-event-read"))],
)
async def get_quality_events_by_period(
    cost_element_id: UUID = Query(
        ..., description="Cost Element ID to aggregate quality events for"
    ),
    period: str = Query(
        ...,
        pattern="^(daily|weekly|monthly)$",
        description="Aggregation period (daily, weekly, or monthly)",
    ),
    start_date: datetime = Query(
        ..., description="Start date for aggregation (ISO 8601)"
    ),
    end_date: datetime | None = Query(
        None, description="End date for aggregation (ISO 8601, defaults to now)"
    ),
    as_of: datetime | None = Query(
        None,
        description="Time travel: get quality events as of this timestamp (ISO 8601)",
    ),
    service: QualityEventService = Depends(get_quality_event_service),
) -> list[dict[str, Any]]:
    """Get quality event aggregations by time period.

    Returns quality event costs aggregated by day, week, or month for a cost element.

    Example:
        - period=daily: One row per day with total cost_impact
        - period=weekly: One row per week (starts Monday) with total cost_impact
        - period=monthly: One row per month (starts 1st) with total cost_impact

    All quality events respect time-travel queries via the as_of parameter.
    """
    as_of = _default_as_of(as_of)

    try:
        events = await service.get_quality_events_by_period(
            cost_element_id=cost_element_id,
            period=period,
            start_date=start_date,
            end_date=end_date,
            as_of=as_of,
        )
        return events
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


# Generic routes with path parameters must come AFTER specific routes


@router.get(
    "/{quality_event_id}",
    response_model=QualityEventRead,
    operation_id="get_quality_event",
    dependencies=[Depends(RoleChecker(required_permission="quality-event-read"))],
)
async def read_quality_event(
    quality_event_id: UUID,
    as_of: datetime | None = Query(
        None,
        description="Time travel: get quality event state as of this timestamp (ISO 8601)",
    ),
    service: QualityEventService = Depends(get_quality_event_service),
) -> QualityEvent:
    """Get a specific quality event by id.

    Supports time-travel queries via the as_of parameter to view
    the quality event's state at any historical point in time.
    """
    # Default to current time if as_of is not provided
    if as_of is None:
        as_of = datetime.now(tz=UTC)

    if as_of:
        # Time travel query
        item = await service.get_quality_event_as_of(
            quality_event_id=quality_event_id,
            as_of=as_of,
        )
    else:
        # Current version
        item = await service.get_by_id(quality_event_id)

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quality Event not found" + (f" as of {as_of}" if as_of else ""),
        )
    return item


@router.put(
    "/{quality_event_id}",
    response_model=QualityEventRead,
    operation_id="update_quality_event",
    dependencies=[Depends(RoleChecker(required_permission="quality-event-write"))],
)
async def update_quality_event(
    quality_event_id: UUID,
    event_in: QualityEventUpdate,
    current_user: User = Depends(get_current_active_user),
    service: QualityEventService = Depends(get_quality_event_service),
) -> QualityEvent:
    """Update a quality event.

    Creates a new version of the quality event with the updated values.
    Previous versions are preserved in the history.

    The control_date parameter allows setting the valid_time start date for
    the new version, useful for backdating updates or testing time-travel.
    """
    try:
        return await service.update_quality_event(
            quality_event_id=quality_event_id,
            event_in=event_in,
            actor_id=current_user.user_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.delete(
    "/{quality_event_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="delete_quality_event",
    dependencies=[Depends(RoleChecker(required_permission="quality-event-delete"))],
)
async def delete_quality_event(
    quality_event_id: UUID,
    control_date: datetime | None = Query(
        None, description="Optional control date for deletion"
    ),
    current_user: User = Depends(get_current_active_user),
    service: QualityEventService = Depends(get_quality_event_service),
) -> None:
    """Soft delete a quality event.

    Marks the quality event as deleted but preserves it in the history.
    """
    try:
        item = await service.get_by_id(quality_event_id)
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Quality Event not found",
            )

        await service.soft_delete(
            quality_event_id=quality_event_id,
            actor_id=current_user.user_id,
            control_date=control_date,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get(
    "/{quality_event_id}/history",
    response_model=list[QualityEventRead],
    operation_id="get_quality_event_history",
    dependencies=[Depends(RoleChecker(required_permission="quality-event-read"))],
)
async def get_quality_event_history(
    quality_event_id: UUID,
    service: QualityEventService = Depends(get_quality_event_service),
) -> Sequence[QualityEvent]:
    """Get full version history for a quality event.

    Returns all versions of the quality event, ordered by transaction time.
    Includes both current and historical versions.
    """
    return await service.get_history(quality_event_id)
