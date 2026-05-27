"""Cost Event API routes - quality and cost event tracking.

Cost Events replace the old Work Package concept for quality/cost tracking.
Versionable but NOT branchable (events are global facts).
"""

from collections.abc import Sequence
from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import RoleChecker, UserIdentity, get_current_user
from app.db.session import get_db
from app.models.domain.cost_event import CostEvent
from app.models.schemas.cost_event import (
    COQMetrics,
    COQTrendGranularity,
    COQTrendResponse,
    CostEventCreate,
    CostEventRead,
    CostEventSummary,
    CostEventUpdate,
    QualityCostAllocation,
    QualityCostAllocationRead,
)
from app.services.cost_event_service import CostEventService

router = APIRouter()


def get_cost_event_service(
    session: AsyncSession = Depends(get_db),
) -> CostEventService:
    return CostEventService(session)


# ---------------------------------------------------------------------------
# CRUD endpoints
# ---------------------------------------------------------------------------


@router.get(
    "",
    response_model=None,
    operation_id="get_cost_events",
    dependencies=[Depends(RoleChecker(required_permission="cost-event-read"))],
)
async def read_cost_events(
    project_id: UUID | None = Query(None, description="Filter by project ID"),
    wbs_element_id: UUID | None = Query(
        None, description="Filter by WBS Element root ID"
    ),
    coq_category: str | None = Query(
        None,
        pattern="^(prevention|appraisal|internal_failure|external_failure)$",
        description="Filter by COQ category",
    ),
    cost_event_type_id: UUID | None = Query(
        None, description="Filter by Cost Event Type ID"
    ),
    status_filter: str | None = Query(
        None,
        alias="status",
        pattern="^(open|closed)$",
        description="Filter by status",
    ),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    per_page: int = Query(20, ge=1, description="Items per page"),
    as_of: datetime | None = Query(
        None,
        description="Time travel: get events as of this timestamp (ISO 8601)",
    ),
    service: CostEventService = Depends(get_cost_event_service),
) -> dict[str, Any]:
    """Retrieve cost events with filtering and pagination.

    Cost Events are versionable but NOT branchable (global facts).
    """
    from app.models.schemas.common import PaginatedResponse
    from app.models.schemas.cost_event import CostEventRead

    if as_of is None:
        from datetime import UTC

        as_of = datetime.now(tz=UTC)

    skip = (page - 1) * per_page

    try:
        items, total = await service.get_cost_events(
            project_id=project_id,
            wbs_element_id=wbs_element_id,
            coq_category=coq_category,
            status=status_filter,
            skip=skip,
            limit=per_page,
            as_of=as_of,
        )

        items_out = []
        for i in items:
            read = CostEventRead.model_validate(i)
            items_out.append(read)

        response = PaginatedResponse[CostEventRead](
            items=items_out,
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
    response_model=CostEventRead,
    status_code=status.HTTP_201_CREATED,
    operation_id="create_cost_event",
    dependencies=[Depends(RoleChecker(required_permission="cost-event-create"))],
)
async def create_cost_event(
    event_in: CostEventCreate,
    current_user: UserIdentity = Depends(get_current_user),
    service: CostEventService = Depends(get_cost_event_service),
) -> CostEvent:
    """Create a new cost event. Requires create permission."""
    try:
        return await service.create_cost_event(
            data=event_in, actor_id=current_user.user_id
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


# Specific routes BEFORE generic /{cost_event_id} routes


@router.get(
    "/project/{project_id}/summary",
    response_model=CostEventSummary,
    operation_id="get_cost_event_summary",
    dependencies=[Depends(RoleChecker(required_permission="cost-event-read"))],
)
async def get_cost_event_summary(
    project_id: UUID,
    as_of: datetime | None = Query(
        None,
        description="Time travel: get summary as of this timestamp (ISO 8601)",
    ),
    service: CostEventService = Depends(get_cost_event_service),
) -> CostEventSummary:
    """Get aggregated COQ summary for a project.

    Returns total cost, conformance/nonconformance breakdown,
    total schedule impact days, and COQ ratio against project budget.
    """
    try:
        return await service.get_summary(project_id=project_id, as_of=as_of)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


@router.get(
    "/project/{project_id}/coq-metrics",
    response_model=COQMetrics,
    operation_id="get_coq_metrics",
    dependencies=[Depends(RoleChecker(required_permission="cost-event-read"))],
)
async def get_coq_metrics(
    project_id: UUID,
    as_of: datetime | None = Query(None, description="Time travel query"),
    service: CostEventService = Depends(get_cost_event_service),
) -> COQMetrics:
    """Get COQ metrics for a project.

    Returns Cost of Quality metrics including CPQ, CPIq, QPI, and COQ ratio.
    """
    return await service.get_coq_metrics(project_id=project_id, as_of=as_of)


@router.get(
    "/project/{project_id}/coq-trend",
    response_model=COQTrendResponse,
    operation_id="get_coq_trend",
    summary="Get COQ trend time-series",
    dependencies=[Depends(RoleChecker(required_permission="cost-event-read"))],
)
async def get_coq_trend(
    project_id: UUID,
    granularity: COQTrendGranularity = Query(
        COQTrendGranularity.MONTH, description="Time granularity"
    ),
    as_of: datetime | None = Query(
        None, description="Point-in-time for historical query"
    ),
    service: CostEventService = Depends(get_cost_event_service),
) -> COQTrendResponse:
    """Get COQ trend time-series for a project.

    Returns Cost of Quality costs aggregated into time buckets (week or month),
    broken down by the four COQ categories.
    """
    return await service.get_coq_trend(project_id, granularity, as_of)


# Generic routes with path parameters


@router.get(
    "/{cost_event_id}",
    response_model=CostEventRead,
    operation_id="get_cost_event",
    dependencies=[Depends(RoleChecker(required_permission="cost-event-read"))],
)
async def read_cost_event(
    cost_event_id: UUID,
    as_of: datetime | None = Query(
        None,
        description="Time travel: get event state as of this timestamp (ISO 8601)",
    ),
    service: CostEventService = Depends(get_cost_event_service),
) -> CostEvent:
    """Get a specific cost event by root ID. Requires read permission.

    Supports time-travel queries via the as_of parameter.
    """
    if as_of is not None:
        item = await service.get_as_of(
            entity_id=cost_event_id,
            as_of=as_of,
        )
    else:
        item = await service.get_by_id(cost_event_id)

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cost Event not found",
        )
    return item


@router.put(
    "/{cost_event_id}",
    response_model=CostEventRead,
    operation_id="update_cost_event",
    dependencies=[Depends(RoleChecker(required_permission="cost-event-update"))],
)
async def update_cost_event(
    cost_event_id: UUID,
    event_in: CostEventUpdate,
    current_user: UserIdentity = Depends(get_current_user),
    service: CostEventService = Depends(get_cost_event_service),
) -> CostEvent:
    """Update a cost event. Creates a new version. Requires update permission."""
    try:
        return await service.update_cost_event(
            cost_event_id=cost_event_id,
            data=event_in,
            actor_id=current_user.user_id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.delete(
    "/{cost_event_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="delete_cost_event",
    dependencies=[Depends(RoleChecker(required_permission="cost-event-delete"))],
)
async def delete_cost_event(
    cost_event_id: UUID,
    control_date: datetime | None = Query(
        None, description="Optional control date for deletion"
    ),
    current_user: UserIdentity = Depends(get_current_user),
    service: CostEventService = Depends(get_cost_event_service),
) -> None:
    """Soft delete a cost event. Requires delete permission."""
    try:
        await service.soft_delete_cost_event(
            cost_event_id=cost_event_id,
            actor_id=current_user.user_id,
            control_date=control_date,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get(
    "/{cost_event_id}/history",
    response_model=list[CostEventRead],
    operation_id="get_cost_event_history",
    dependencies=[Depends(RoleChecker(required_permission="cost-event-read"))],
)
async def read_cost_event_history(
    cost_event_id: UUID,
    service: CostEventService = Depends(get_cost_event_service),
) -> Sequence[CostEvent]:
    """Get full version history for a cost event. Requires read permission."""
    history = await service.get_history(cost_event_id)
    if not history:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No history found for this Cost Event",
        )
    return history


# ---------------------------------------------------------------------------
# Allocations
# ---------------------------------------------------------------------------


@router.get(
    "/{cost_event_id}/allocations",
    response_model=list[QualityCostAllocationRead],
    operation_id="get_cost_event_allocations",
    dependencies=[Depends(RoleChecker(required_permission="cost-event-read"))],
)
async def get_cost_event_allocations(
    cost_event_id: UUID,
    service: CostEventService = Depends(get_cost_event_service),
) -> list[QualityCostAllocationRead]:
    """Get cost allocation entries for a cost event.

    Returns CostRegistration entries linked to this cost event.
    """
    return await service.get_allocations(cost_event_id)


@router.put(
    "/{cost_event_id}/allocations",
    response_model=list[QualityCostAllocationRead],
    operation_id="upsert_cost_event_allocations",
    dependencies=[Depends(RoleChecker(required_permission="cost-event-update"))],
)
async def upsert_cost_event_allocations(
    cost_event_id: UUID,
    allocations_in: list[QualityCostAllocation],
    current_user: UserIdentity = Depends(get_current_user),
    service: CostEventService = Depends(get_cost_event_service),
) -> list[QualityCostAllocationRead]:
    """Replace all cost allocations for a cost event.

    Soft-deletes existing linked CostRegistration entries and creates new ones.
    """
    return await service.upsert_allocations(
        cost_event_id=cost_event_id,
        allocations_data=allocations_in,
        actor_id=current_user.user_id,
    )
