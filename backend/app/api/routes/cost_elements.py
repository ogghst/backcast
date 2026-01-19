from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import RoleChecker, get_current_active_user
from app.core.versioning.enums import BranchMode
from app.db.session import get_db
from app.models.domain.cost_element import CostElement
from app.models.domain.user import User
from app.models.schemas.cost_element import (
    CostElementCreate,
    CostElementRead,
    CostElementUpdate,
)
from app.services.cost_element_service import CostElementService
from app.services.evm_service import EVMService
from app.services.forecast_service import ForecastService

router = APIRouter()


def get_cost_element_service(
    session: AsyncSession = Depends(get_db),
) -> CostElementService:
    return CostElementService(session)


def get_forecast_service(
    session: AsyncSession = Depends(get_db),
) -> ForecastService:
    return ForecastService(session)


@router.get(
    "",
    response_model=None,  # Will be PaginatedResponse[CostElementRead]
    operation_id="get_cost_elements",
    dependencies=[Depends(RoleChecker(required_permission="cost-element-read"))],
)
async def read_cost_elements(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    per_page: int = Query(20, ge=1, description="Items per page"),
    branch: str = Query("main", description="Branch to query"),
    mode: str = Query(
        "merged",
        pattern="^(merged|isolated)$",
        description="Branch mode: merged (combine with main) or isolated (current branch only)",
    ),
    wbe_id: UUID | None = Query(None, description="Filter by WBE ID"),
    cost_element_type_id: UUID | None = Query(
        None, description="Filter by Cost Element Type ID"
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
        description="Time travel: get Cost Elements as of this timestamp (ISO 8601)",
    ),
    service: CostElementService = Depends(get_cost_element_service),
) -> dict[str, Any]:
    """Retrieve cost elements with server-side search, filtering, and sorting."""
    from app.core.versioning.enums import BranchMode
    from app.models.schemas.common import PaginatedResponse
    from app.models.schemas.cost_element import CostElementRead

    # Parse mode string to BranchMode enum
    branch_mode = BranchMode.MERGE if mode == "merged" else BranchMode.STRICT

    # Legacy filters support
    legacy_filters = {}
    if wbe_id:
        legacy_filters["wbe_id"] = wbe_id
    if cost_element_type_id:
        legacy_filters["cost_element_type_id"] = cost_element_type_id

    skip = (page - 1) * per_page

    items, total = await service.get_cost_elements(
        filters=legacy_filters,
        branch=branch,
        branch_mode=branch_mode,
        skip=skip,
        limit=per_page,
        search=search,
        filter_string=filters,
        sort_field=sort_field,
        sort_order=sort_order,
        as_of=as_of,
    )

    # Convert to Pydantic models
    items_out = [CostElementRead.model_validate(i) for i in items]

    # Return paginated response
    response = PaginatedResponse[CostElementRead](
        items=items_out,
        total=total,
        page=page,
        per_page=per_page,
    )

    return response.model_dump()


@router.post(
    "",
    response_model=CostElementRead,
    status_code=status.HTTP_201_CREATED,
    operation_id="create_cost_element",
    dependencies=[Depends(RoleChecker(required_permission="cost-element-create"))],
)
async def create_cost_element(
    element_in: CostElementCreate,
    current_user: User = Depends(get_current_active_user),
    service: CostElementService = Depends(get_cost_element_service),
) -> CostElement:
    """Create a new cost element in specified branch."""
    try:
        return await service.create(
            element_in=element_in,
            actor_id=current_user.user_id,
            branch=element_in.branch,
            control_date=element_in.control_date,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.get(
    "/{cost_element_id}",
    response_model=CostElementRead,
    operation_id="get_cost_element",
    dependencies=[Depends(RoleChecker(required_permission="cost-element-read"))],
)
async def read_cost_element(
    cost_element_id: UUID,
    branch: str = Query("main", description="Branch to query"),
    as_of: datetime | None = Query(
        None,
        description="Time travel: get cost element state as of this timestamp (ISO 8601)",
    ),
    service: CostElementService = Depends(get_cost_element_service),
) -> CostElement:
    """Get a specific cost element by id and branch.

    Supports time-travel queries via the as_of parameter to view
    the cost element's state at any historical point in time.
    """
    if as_of:
        # Time travel query
        item = await service.get_cost_element_as_of(cost_element_id, as_of)
    else:
        # Current version
        item = await service.get_by_id(cost_element_id, branch=branch)

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cost Element not found in branch {branch}"
            + (f" as of {as_of}" if as_of else ""),
        )
    return item


@router.put(
    "/{cost_element_id}",
    response_model=CostElementRead,
    operation_id="update_cost_element",
    dependencies=[Depends(RoleChecker(required_permission="cost-element-update"))],
)
async def update_cost_element(
    cost_element_id: UUID,
    element_in: CostElementUpdate,
    current_user: User = Depends(get_current_active_user),
    service: CostElementService = Depends(get_cost_element_service),
) -> CostElement:
    """Update a cost element. Creates new version or forks."""
    try:
        # Use branch from schema if provided, otherwise default to main
        branch = element_in.branch or "main"

        return await service.update(
            cost_element_id=cost_element_id,
            element_in=element_in,
            actor_id=current_user.user_id,
            branch=branch,
            control_date=element_in.control_date,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.delete(
    "/{cost_element_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="delete_cost_element",
    dependencies=[Depends(RoleChecker(required_permission="cost-element-delete"))],
)
async def delete_cost_element(
    cost_element_id: UUID,
    branch: str = Query("main", description="Branch to delete from"),
    control_date: datetime | None = Query(
        None, description="Optional control date for deletion"
    ),
    current_user: User = Depends(get_current_active_user),
    service: CostElementService = Depends(get_cost_element_service),
) -> None:
    """Soft delete a cost element in a branch."""
    try:
        item = await service.get_by_id(cost_element_id, branch=branch)
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Cost Element not found in branch {branch}",
            )

        await service.soft_delete(
            cost_element_id=cost_element_id,
            actor_id=current_user.user_id,
            branch=branch,
            control_date=control_date,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get(
    "/{cost_element_id}/history",
    response_model=list[CostElementRead],
    operation_id="get_cost_element_history",
    dependencies=[Depends(RoleChecker(required_permission="cost-element-read"))],
)
async def get_cost_element_history(
    cost_element_id: UUID,
    service: CostElementService = Depends(get_cost_element_service),
) -> Sequence[CostElement]:
    """Get full version history for a cost element across all branches."""
    # TODO: History might need branch filtering too?
    # TemporalService.get_history gets ALL versions by root_id.
    # This is correct for "history view".
    return await service.get_history(cost_element_id)


@router.get(
    "/{cost_element_id}/breadcrumb",
    operation_id="get_cost_element_breadcrumb",
    dependencies=[Depends(RoleChecker(required_permission="cost-element-read"))],
)
async def get_cost_element_breadcrumb(
    cost_element_id: UUID,
    service: CostElementService = Depends(get_cost_element_service),
) -> dict[str, Any]:
    """Get breadcrumb trail for a Cost Element (project + WBE + cost element)."""
    try:
        return await service.get_breadcrumb(cost_element_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


# Schedule Baseline nested endpoints (1:1 relationship)


def get_schedule_baseline_service(
    session: AsyncSession = Depends(get_db),
) -> Any:
    from app.services.schedule_baseline_service import ScheduleBaselineService

    return ScheduleBaselineService(session)


@router.get(
    "/{cost_element_id}/schedule-baseline",
    response_model=dict,  # ScheduleBaselineRead with cost element details
    operation_id="get_cost_element_schedule_baseline",
    dependencies=[Depends(RoleChecker(required_permission="schedule-baseline-read"))],
)
async def get_cost_element_schedule_baseline(
    cost_element_id: UUID,
    branch: str = Query("main", description="Branch to query"),
    baseline_service: Any = Depends(get_schedule_baseline_service),
) -> dict[str, Any]:
    """Get the schedule baseline for a specific cost element.

    Returns the single schedule baseline associated with this cost element
    in the specified branch. Returns 404 if no baseline exists.
    """
    baseline = await baseline_service.get_for_cost_element(
        cost_element_id=cost_element_id,
        branch=branch,
    )

    if not baseline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule baseline not found for cost element {cost_element_id} "
            f"in branch '{branch}'",
        )

    # Convert to dict with cost element details
    from app.models.schemas.schedule_baseline import ScheduleBaselineRead

    baseline_dict = ScheduleBaselineRead.model_validate(baseline).model_dump()

    # Add cost element details if available

    from app.models.domain.cost_element import CostElement

    ce_stmt = select(
        CostElement.code,
        CostElement.name,
    ).where(
        CostElement.cost_element_id == cost_element_id,
        CostElement.branch == branch,
        # "Current" filter - get current version only
        func.upper(CostElement.valid_time).is_(None),
        CostElement.deleted_at.is_(None),
    )
    ce_result = await baseline_service.session.execute(ce_stmt)
    ce_row = ce_result.first()

    if ce_row:
        baseline_dict["cost_element_code"] = ce_row.code
        baseline_dict["cost_element_name"] = ce_row.name

    return baseline_dict


@router.post(
    "/{cost_element_id}/schedule-baseline",
    response_model=dict,  # ScheduleBaselineRead
    status_code=status.HTTP_201_CREATED,
    operation_id="create_cost_element_schedule_baseline",
    dependencies=[Depends(RoleChecker(required_permission="schedule-baseline-create"))],
)
async def create_cost_element_schedule_baseline(
    cost_element_id: UUID,
    baseline_in: dict[str, Any],  # ScheduleBaselineBase without cost_element_id
    current_user: User = Depends(get_current_active_user),
    branch: str = Query("main", description="Branch to create in"),
    baseline_service: Any = Depends(get_schedule_baseline_service),
) -> dict[str, Any]:
    """Create a schedule baseline for a cost element.

    Creates a new schedule baseline and associates it with the cost element.
    Each cost element can have only one schedule baseline per branch.

    Raises 400 if a baseline already exists for this cost element.
    """
    from datetime import datetime

    from app.services.schedule_baseline_service import BaselineAlreadyExistsError

    try:
        baseline = await baseline_service.create_for_cost_element(
            cost_element_id=cost_element_id,
            actor_id=current_user.user_id,
            name=baseline_in.get("name", "Default Schedule"),
            start_date=datetime.fromisoformat(baseline_in["start_date"])
            if isinstance(baseline_in.get("start_date"), str)
            else baseline_in["start_date"],
            end_date=datetime.fromisoformat(baseline_in["end_date"])
            if isinstance(baseline_in.get("end_date"), str)
            else baseline_in["end_date"],
            progression_type=baseline_in.get("progression_type", "LINEAR"),
            description=baseline_in.get("description"),
            branch=branch,
            control_date=None,
        )

        # Convert to dict
        from app.models.schemas.schedule_baseline import ScheduleBaselineRead

        return ScheduleBaselineRead.model_validate(baseline).model_dump()

    except BaselineAlreadyExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.put(
    "/{cost_element_id}/schedule-baseline/{baseline_id}",
    response_model=dict,  # ScheduleBaselineRead
    operation_id="update_cost_element_schedule_baseline",
    dependencies=[Depends(RoleChecker(required_permission="schedule-baseline-update"))],
)
async def update_cost_element_schedule_baseline(
    cost_element_id: UUID,
    baseline_id: UUID,
    baseline_in: dict[str, Any],  # ScheduleBaselineUpdate
    current_user: User = Depends(get_current_active_user),
    branch: str = Query("main", description="Branch to update in"),
    baseline_service: Any = Depends(get_schedule_baseline_service),
) -> dict[str, Any]:
    """Update the schedule baseline for a cost element.

    Updates the specified baseline. Creates a new version with the changes.
    Only the fields provided in the request body are updated.
    """
    from datetime import datetime

    # Verify baseline exists and belongs to this cost element
    baseline = await baseline_service.get_by_id(baseline_id, branch=branch)
    if not baseline or baseline.cost_element_id != cost_element_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule baseline {baseline_id} not found for cost element "
            f"{cost_element_id} in branch '{branch}'",
        )

    # Build update data - only include fields that were actually provided
    update_data = {}
    if "name" in baseline_in and baseline_in["name"] is not None:
        update_data["name"] = baseline_in["name"]
    if "start_date" in baseline_in and baseline_in["start_date"] is not None:
        # Handle both string and datetime objects (database uses TIMESTAMPTZ)
        start_date = baseline_in["start_date"]
        if isinstance(start_date, str):
            start_date = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
        update_data["start_date"] = start_date
    if "end_date" in baseline_in and baseline_in["end_date"] is not None:
        # Handle both string and datetime objects (database uses TIMESTAMPTZ)
        end_date = baseline_in["end_date"]
        if isinstance(end_date, str):
            end_date = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
        update_data["end_date"] = end_date
    if "progression_type" in baseline_in and baseline_in["progression_type"] is not None:
        update_data["progression_type"] = baseline_in["progression_type"]
    if "description" in baseline_in:
        update_data["description"] = baseline_in["description"]

    # Update baseline
    updated_baseline = await baseline_service.update(
        root_id=baseline_id,
        actor_id=current_user.user_id,
        branch=branch,
        control_date=None,
        **update_data,
    )

    # Convert to dict
    from app.models.schemas.schedule_baseline import ScheduleBaselineRead

    return ScheduleBaselineRead.model_validate(updated_baseline).model_dump()


@router.delete(
    "/{cost_element_id}/schedule-baseline/{baseline_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="delete_cost_element_schedule_baseline",
    dependencies=[Depends(RoleChecker(required_permission="schedule-baseline-delete"))],
)
async def delete_cost_element_schedule_baseline(
    cost_element_id: UUID,
    baseline_id: UUID,
    current_user: User = Depends(get_current_active_user),
    branch: str = Query("main", description="Branch to delete from"),
    baseline_service: Any = Depends(get_schedule_baseline_service),
) -> None:
    """Soft delete the schedule baseline for a cost element.

    Soft deletes the specified baseline. The baseline is marked as deleted
    but remains in the database for audit purposes.
    """
    # Verify baseline exists and belongs to this cost element
    baseline = await baseline_service.get_by_id(baseline_id, branch=branch)
    if not baseline or baseline.cost_element_id != cost_element_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule baseline {baseline_id} not found for cost element "
            f"{cost_element_id} in branch '{branch}'",
        )

    # Soft delete baseline
    await baseline_service.soft_delete(
        root_id=baseline_id,
        actor_id=current_user.user_id,
        branch=branch,
        control_date=None,
    )


def get_evm_service(
    session: AsyncSession = Depends(get_db),
) -> EVMService:
    """Dependency to get EVMService instance."""
    return EVMService(session)


@router.get(
    "/{cost_element_id}/evm",
    response_model=None,  # EVMMetricsRead
    operation_id="get_evm_metrics",
    dependencies=[Depends(RoleChecker(required_permission="cost-element-read"))],
)
async def read_evm_metrics(
    cost_element_id: UUID,
    control_date: datetime | None = Query(
        None,
        description="Control date for time-travel query (ISO 8601, defaults to now). "
        "All entities are fetched as they were at this valid_time.",
    ),
    branch: str = Query("main", description="Branch to query"),
    branch_mode: BranchMode = Query(
        BranchMode.MERGE,
        description="Branch mode: ISOLATED (only this branch) or MERGE (fall back to parent branches)",
    ),
    service: EVMService = Depends(get_evm_service),
) -> dict[str, Any]:
    """Calculate EVM (Earned Value Management) metrics for a cost element.

    Returns comprehensive EVM analysis including:
    - BAC: Budget at Completion (total planned budget)
    - PV: Planned Value (budgeted cost of work scheduled)
    - AC: Actual Cost (cost incurred to date)
    - EV: Earned Value (budgeted cost of work performed)
    - CV: Cost Variance (EV - AC, negative = over budget)
    - SV: Schedule Variance (EV - PV, negative = behind schedule)
    - CPI: Cost Performance Index (EV / AC, < 1.0 = over budget)
    - SPI: Schedule Performance Index (EV / PV, < 1.0 = behind schedule)

    Time-Travel & Branching:
    - All metrics respect time-travel: entities are fetched as they were at control_date
    - Cost elements and schedule baselines are fetched at the correct valid_time
    - Branch mode (ISOLATED/MERGE) controls parent branch fallback behavior
    - Cost registrations and progress entries are global facts (not branchable)

    Warning: Returns EV = 0 with warning message if no progress has been reported.
    """
    if control_date is None:
        control_date = datetime.now(tz=UTC)

    try:
        metrics = await service.calculate_evm_metrics(
            cost_element_id=cost_element_id,
            control_date=control_date,
            branch=branch,
            branch_mode=branch_mode,
        )
        return metrics.model_dump(mode='json')
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


# ============================================================================
# Forecast Endpoints (1:1 Relationship with Cost Elements)
# ============================================================================

@router.get(
    "/{cost_element_id}/forecast",
    response_model=dict,  # ForecastRead with cost element details
    operation_id="get_cost_element_forecast",
    dependencies=[Depends(RoleChecker(required_permission="forecast-read"))],
)
async def get_cost_element_forecast(
    cost_element_id: UUID,
    branch: str = Query("main", description="Branch to query"),
    forecast_service: ForecastService = Depends(get_forecast_service),
) -> dict[str, Any]:
    """Get the forecast for a specific cost element.

    Returns the single forecast associated with this cost element
    in the specified branch. Returns 404 if no forecast exists.

    This endpoint follows the inverted FK pattern, querying via
    cost_element.forecast_id instead of forecast.cost_element_id.
    """
    forecast = await forecast_service.get_for_cost_element(
        cost_element_id=cost_element_id,
        branch=branch,
    )

    if not forecast:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Forecast not found for cost element {cost_element_id} "
            f"in branch '{branch}'",
        )

    # Convert to dict with cost element details
    from app.models.schemas.forecast import ForecastRead

    forecast_dict = ForecastRead.model_validate(forecast).model_dump()

    # Add cost element details if available

    stmt = select(
        CostElement.cost_element_id,
        CostElement.code,
        CostElement.name,
        CostElement.budget_amount,
    ).where(
        CostElement.cost_element_id == cost_element_id,
        CostElement.branch == branch,
        # "Current" filter - get current version only
        func.upper(CostElement.valid_time).is_(None),
        CostElement.deleted_at.is_(None),
    )
    result = await forecast_service.session.execute(stmt)
    ce_row = result.first()

    if ce_row:
        forecast_dict["cost_element_id"] = ce_row.cost_element_id
        forecast_dict["cost_element_code"] = ce_row.code
        forecast_dict["cost_element_name"] = ce_row.name
        forecast_dict["cost_element_budget_amount"] = ce_row.budget_amount

    return forecast_dict


@router.put(
    "/{cost_element_id}/forecast",
    response_model=dict,  # ForecastRead
    operation_id="update_cost_element_forecast",
    dependencies=[Depends(RoleChecker(required_permission="forecast-update"))],
)
async def update_cost_element_forecast(
    cost_element_id: UUID,
    forecast_in: dict[str, Any],  # ForecastUpdate
    current_user: User = Depends(get_current_active_user),
    branch: str = Query("main", description="Branch to update in"),
    control_date: datetime | None = Query(
        None,
        description="Control date for valid_time (ISO 8601). "
        "Sets when the forecast becomes valid in the real world. "
        "Defaults to current time if not provided.",
    ),
    forecast_service: ForecastService = Depends(get_forecast_service),
) -> dict[str, Any]:
    """Update the forecast for a cost element.

    Updates the existing forecast or creates a new one if none exists.
    Creates a new version with the changes.
    Only the fields provided in the request body are updated.

    Raises 400 if a forecast already exists (when creating new).
    """
    from decimal import Decimal

    from app.models.domain.cost_element import CostElement
    from app.services.forecast_service import ForecastAlreadyExistsError

    # Check if forecast exists
    existing_forecast = await forecast_service.get_for_cost_element(
        cost_element_id=cost_element_id,
        branch=branch,
    )

    if existing_forecast:
        # Update existing forecast
        # Build update data - only include fields that were actually provided
        update_data = {}
        if "eac_amount" in forecast_in and forecast_in["eac_amount"] is not None:
            update_data["eac_amount"] = Decimal(str(forecast_in["eac_amount"]))
        if "basis_of_estimate" in forecast_in:
            update_data["basis_of_estimate"] = forecast_in["basis_of_estimate"]
        if "approved_date" in forecast_in:
            approved_date = forecast_in["approved_date"]
            if isinstance(approved_date, str):
                approved_date = datetime.fromisoformat(approved_date.replace("Z", "+00:00"))
            update_data["approved_date"] = approved_date
        if "approved_by" in forecast_in:
            update_data["approved_by"] = forecast_in["approved_by"]

        # Update forecast using standard update method
        updated_forecast = await forecast_service.update(
            root_id=existing_forecast.forecast_id,
            actor_id=current_user.user_id,
            branch=branch,
            control_date=control_date,
            **update_data,
        )
    else:
        # Create new forecast
        # Build create data
        create_data: dict[str, Any] = {}
        if "eac_amount" in forecast_in and forecast_in["eac_amount"] is not None:
            create_data["eac_amount"] = Decimal(str(forecast_in["eac_amount"]))
        else:
            # Get budget from cost element as default
            from sqlalchemy import func, select

            ce_stmt = select(CostElement.budget_amount).where(
                CostElement.cost_element_id == cost_element_id,
                CostElement.branch == branch,
                # "Current" filter - get current version only
                func.upper(CostElement.valid_time).is_(None),
                CostElement.deleted_at.is_(None),
            )
            ce_result = await forecast_service.session.execute(ce_stmt)
            ce_row = ce_result.first()
            create_data["eac_amount"] = ce_row.budget_amount if ce_row else Decimal("0.00")

        if "basis_of_estimate" in forecast_in:
            create_data["basis_of_estimate"] = forecast_in["basis_of_estimate"]
        else:
            create_data["basis_of_estimate"] = "Initial forecast"

        if "approved_date" in forecast_in:
            approved_date = forecast_in["approved_date"]
            if isinstance(approved_date, str):
                approved_date = datetime.fromisoformat(approved_date.replace("Z", "+00:00"))
            create_data["approved_date"] = approved_date
        if "approved_by" in forecast_in:
            create_data["approved_by"] = forecast_in["approved_by"]

        try:
            updated_forecast = await forecast_service.create_for_cost_element(
                cost_element_id=cost_element_id,
                actor_id=current_user.user_id,
                branch=branch,
                control_date=control_date,
                **create_data,
            )
        except ForecastAlreadyExistsError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            ) from e

    # Convert to dict with cost element details
    from app.models.schemas.forecast import ForecastRead

    forecast_dict = ForecastRead.model_validate(updated_forecast).model_dump()

    # Add cost element details if available
    from sqlalchemy import func, select

    ce_details_stmt = select(
        CostElement.cost_element_id,
        CostElement.code,
        CostElement.name,
        CostElement.budget_amount,
    ).where(
        CostElement.cost_element_id == cost_element_id,
        CostElement.branch == branch,
        # "Current" filter - get current version only
        func.upper(CostElement.valid_time).is_(None),
        CostElement.deleted_at.is_(None),
    )
    ce_details_result = await forecast_service.session.execute(ce_details_stmt)
    ce_details_row = ce_details_result.first()

    if ce_details_row:
        forecast_dict["cost_element_id"] = ce_details_row.cost_element_id
        forecast_dict["cost_element_code"] = ce_details_row.code
        forecast_dict["cost_element_name"] = ce_details_row.name
        forecast_dict["cost_element_budget_amount"] = ce_details_row.budget_amount

    return forecast_dict


@router.delete(
    "/{cost_element_id}/forecast",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="delete_cost_element_forecast",
    dependencies=[Depends(RoleChecker(required_permission="forecast-delete"))],
)
async def delete_cost_element_forecast(
    cost_element_id: UUID,
    current_user: User = Depends(get_current_active_user),
    branch: str = Query("main", description="Branch to delete from"),
    forecast_service: ForecastService = Depends(get_forecast_service),
) -> None:
    """Delete the forecast for a cost element.

    Soft deletes the forecast associated with this cost element.
    The forecast remains in the database for audit/history but is marked as deleted.

    Note: This does NOT cascade to delete the cost element. The cost element
    remains, but without an associated forecast. A new forecast can be created later.
    """
    # Get the forecast first
    forecast = await forecast_service.get_for_cost_element(
        cost_element_id=cost_element_id,
        branch=branch,
    )

    if not forecast:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Forecast not found for cost element {cost_element_id} "
            f"in branch '{branch}'",
        )

    # Soft delete the forecast
    await forecast_service.soft_delete(
        forecast_id=forecast.forecast_id,
        actor_id=current_user.user_id,
        branch=branch,
        control_date=None,
    )
