"""API routes for Forecast management."""

from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import RoleChecker, get_current_active_user
from app.db.session import get_db
from app.models.domain.forecast import Forecast
from app.models.domain.user import User
from app.models.schemas.forecast import (
    ForecastComparison,
    ForecastCreate,
    ForecastRead,
    ForecastUpdate,
)
from app.services.forecast_service import ForecastService

router = APIRouter()


def get_forecast_service(
    session: AsyncSession = Depends(get_db),
) -> ForecastService:
    return ForecastService(session)


@router.get(
    "",
    response_model=None,  # Will be PaginatedResponse[ForecastRead]
    operation_id="get_forecasts",
    dependencies=[Depends(RoleChecker(required_permission="forecast-read"))],
)
async def read_forecasts(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    per_page: int = Query(20, ge=1, description="Items per page"),
    branch: str = Query("main", description="Branch to query"),
    cost_element_id: UUID | None = Query(None, description="Filter by Cost Element ID"),
    service: ForecastService = Depends(get_forecast_service),
) -> dict[str, Any]:
    """Retrieve forecasts with pagination."""
    from app.models.schemas.common import PaginatedResponse

    skip = (page - 1) * per_page

    # Build filters
    filters = {}
    if cost_element_id:
        filters["cost_element_id"] = cost_element_id

    # Get all forecasts with filters (using BranchableService base methods)
    items = await service.list(
        filters=filters,
        branch=branch,
        skip=skip,
        limit=per_page,
    )

    # For now, total count requires a separate query
    # TODO: Add get_forecasts() method with count return to ForecastService
    total = len(items)

    # Convert to Pydantic models
    items_out = [ForecastRead.model_validate(i) for i in items]

    # Return paginated response
    response = PaginatedResponse[ForecastRead](
        items=items_out,
        total=total,
        page=page,
        per_page=per_page,
    )

    return response.model_dump()


@router.post(
    "",
    response_model=ForecastRead,
    status_code=status.HTTP_201_CREATED,
    operation_id="create_forecast",
    dependencies=[Depends(RoleChecker(required_permission="forecast-create"))],
)
async def create_forecast(
    forecast_in: ForecastCreate,
    current_user: User = Depends(get_current_active_user),
    service: ForecastService = Depends(get_forecast_service),
) -> Forecast:
    """Create a new forecast in specified branch."""
    try:
        return await service.create(
            forecast_in=forecast_in,
            actor_id=current_user.user_id,
            branch=forecast_in.branch,
            control_date=forecast_in.control_date,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.get(
    "/{forecast_id}",
    response_model=ForecastRead,
    operation_id="get_forecast",
    dependencies=[Depends(RoleChecker(required_permission="forecast-read"))],
)
async def read_forecast(
    forecast_id: UUID,
    branch: str = Query("main", description="Branch to query"),
    as_of: datetime | None = Query(
        None,
        description="Time travel: get forecast state as of this timestamp (ISO 8601)",
    ),
    service: ForecastService = Depends(get_forecast_service),
) -> Forecast:
    """Get a specific forecast by id and branch.

    Supports time-travel queries via the as_of parameter to view
    the forecast's state at any historical point in time.
    """
    if as_of:
        # Time travel query
        item = await service.get_as_of(
            entity_id=forecast_id,
            as_of=as_of,
            branch=branch,
        )
    else:
        # Current version
        item = await service.get_by_id(forecast_id, branch=branch)

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Forecast not found in branch {branch}"
            + (f" as of {as_of}" if as_of else ""),
        )
    return item


@router.put(
    "/{forecast_id}",
    response_model=ForecastRead,
    operation_id="update_forecast",
    dependencies=[Depends(RoleChecker(required_permission="forecast-update"))],
)
async def update_forecast(
    forecast_id: UUID,
    forecast_in: ForecastUpdate,
    current_user: User = Depends(get_current_active_user),
    service: ForecastService = Depends(get_forecast_service),
) -> Forecast:
    """Update a forecast. Creates new version or forks."""
    try:
        # Use branch from schema if provided, otherwise default to main
        branch = forecast_in.branch or "main"

        # Convert ForecastUpdate to dict for update
        update_data = forecast_in.model_dump(exclude_unset=True)
        # Remove fields that should be passed as named arguments, not in updates
        update_data.pop("control_date", None)
        update_data.pop("branch", None)

        return await service.update(
            root_id=forecast_id,
            actor_id=current_user.user_id,
            branch=branch,
            control_date=forecast_in.control_date,
            **update_data,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.delete(
    "/{forecast_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="delete_forecast",
    dependencies=[Depends(RoleChecker(required_permission="forecast-delete"))],
)
async def delete_forecast(
    forecast_id: UUID,
    branch: str = Query("main", description="Branch to delete from"),
    control_date: datetime | None = Query(
        None, description="Optional control date for deletion"
    ),
    current_user: User = Depends(get_current_active_user),
    service: ForecastService = Depends(get_forecast_service),
) -> None:
    """Soft delete a forecast in a branch."""
    try:
        item = await service.get_by_id(forecast_id, branch=branch)
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Forecast not found in branch {branch}",
            )

        await service.soft_delete(
            forecast_id=forecast_id,
            actor_id=current_user.user_id,
            branch=branch,
            control_date=control_date,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get(
    "/{forecast_id}/history",
    response_model=list[ForecastRead],
    operation_id="get_forecast_history",
    dependencies=[Depends(RoleChecker(required_permission="forecast-read"))],
)
async def get_forecast_history(
    forecast_id: UUID,
    service: ForecastService = Depends(get_forecast_service),
) -> Sequence[Forecast]:
    """Get full version history for a forecast across all branches."""
    return await service.get_history(forecast_id)


@router.get(
    "/{forecast_id}/comparison",
    response_model=ForecastComparison,
    operation_id="get_forecast_comparison",
    dependencies=[Depends(RoleChecker(required_permission="forecast-read"))],
)
async def get_forecast_comparison(
    forecast_id: UUID,
    branch: str = Query("main", description="Branch to query"),
    service: ForecastService = Depends(get_forecast_service),
) -> dict[str, Any]:
    """Get EVM comparison metrics for a forecast.

    Returns:
        - BAC (Budget at Complete): From CostElement
        - EAC (Estimate at Complete): From Forecast
        - AC (Actual Cost): Sum of CostRegistrations
        - VAC (Variance at Complete): BAC - EAC
        - ETC (Estimate to Complete): EAC - AC
    """
    # Get the forecast
    forecast = await service.get_by_id(forecast_id, branch=branch)
    if not forecast:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Forecast not found in branch {branch}",
        )

    # Get Cost Element for BAC
    from app.services.cost_element_service import CostElementService

    element_service = CostElementService(service.session)
    cost_element = await element_service.get_by_id(
        forecast.cost_element_id, branch=branch
    )
    if not cost_element:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cost Element not found in branch {branch}",
        )

    # Get AC (Actual Cost) from CostRegistrations
    # Note: CostRegistrations are versionable but NOT branchable
    # They are global facts across all branches
    from app.services.cost_registration_service import CostRegistrationService

    reg_service = CostRegistrationService(service.session)

    # Get total actual cost from registrations for this cost element
    # CostRegistrations are versionable but NOT branchable (global facts)
    ac_total = await reg_service.get_total_for_cost_element(forecast.cost_element_id)
    ac_amount = Decimal(str(ac_total)) if ac_total else Decimal("0.00")

    # Calculate EVM metrics
    bac_amount = cost_element.budget_amount
    eac_amount = forecast.eac_amount
    vac_amount = bac_amount - eac_amount  # VAC = BAC - EAC
    etc_amount = eac_amount - ac_amount  # ETC = EAC - AC

    return {
        "forecast_id": forecast_id,
        "cost_element_id": forecast.cost_element_id,
        "bac_amount": bac_amount,
        "eac_amount": eac_amount,
        "ac_amount": ac_amount,
        "vac_amount": vac_amount,
        "etc_amount": etc_amount,
    }
