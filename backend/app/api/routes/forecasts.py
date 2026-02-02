"""API routes for Forecast management."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import RoleChecker, get_current_active_user
from app.db.session import get_db
from app.models.domain.user import User
from app.models.schemas.forecast import ForecastCreate, ForecastUpdate
from app.services.forecast_service import ForecastService

router = APIRouter()


def get_forecast_service(
    session: AsyncSession = Depends(get_db),
) -> ForecastService:
    return ForecastService(session)


@router.get(
    "",
    response_model=None,
    operation_id="get_forecasts",
    dependencies=[Depends(RoleChecker(required_permission="forecast-read"))],
)
async def read_forecasts(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    per_page: int = Query(20, ge=1, description="Items per page"),
    branch: str = Query("main", description="Branch to query"),
    cost_element_id: UUID | None = Query(None, description="Filter by Cost Element ID"),
    service: ForecastService = Depends(get_forecast_service),
) -> None:
    """Retrieve forecasts with pagination.

    **DEPRECATED**: This endpoint is deprecated as of 2026-01-18.

    Forecasts now have a 1:1 relationship with Cost Elements.
    Use the cost element endpoints instead:
    - GET /api/v1/cost-elements/{cost_element_id}/forecast
    - PUT /api/v1/cost-elements/{cost_element_id}/forecast
    - DELETE /api/v1/cost-elements/{cost_element_id}/forecast
    """
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail={
            "message": "This endpoint is deprecated. Forecasts now have a 1:1 relationship with Cost Elements.",
            "new_endpoints": {
                "get": "GET /api/v1/cost-elements/{cost_element_id}/forecast",
                "update": "PUT /api/v1/cost-elements/{cost_element_id}/forecast",
                "delete": "DELETE /api/v1/cost-elements/{cost_element_id}/forecast",
            },
            "deprecated_since": "2026-01-18",
        },
    )


@router.post(
    "",
    response_model=None,
    status_code=status.HTTP_410_GONE,
    operation_id="create_forecast",
    dependencies=[Depends(RoleChecker(required_permission="forecast-create"))],
)
async def create_forecast(
    forecast_in: ForecastCreate,
    current_user: User = Depends(get_current_active_user),
    service: ForecastService = Depends(get_forecast_service),
) -> None:
    """Create a new forecast in specified branch.

    **DEPRECATED**: This endpoint is deprecated as of 2026-01-18.

    Forecasts now have a 1:1 relationship with Cost Elements.
    Use: PUT /api/v1/cost-elements/{cost_element_id}/forecast
    """
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail={
            "message": "This endpoint is deprecated. Use the cost element forecast endpoint instead.",
            "new_endpoint": "PUT /api/v1/cost-elements/{cost_element_id}/forecast",
            "deprecated_since": "2026-01-18",
        },
    )


@router.get(
    "/{forecast_id}",
    response_model=None,
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
) -> None:
    """Get a specific forecast by id and branch.

    **DEPRECATED**: This endpoint is deprecated as of 2026-01-18.

    Forecasts now have a 1:1 relationship with Cost Elements.
    Use: GET /api/v1/cost-elements/{cost_element_id}/forecast
    """
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail={
            "message": "This endpoint is deprecated. Use the cost element forecast endpoint instead.",
            "new_endpoint": "GET /api/v1/cost-elements/{cost_element_id}/forecast",
            "deprecated_since": "2026-01-18",
        },
    )


@router.put(
    "/{forecast_id}",
    response_model=None,
    operation_id="update_forecast",
    dependencies=[Depends(RoleChecker(required_permission="forecast-update"))],
)
async def update_forecast(
    forecast_id: UUID,
    forecast_in: ForecastUpdate,
    current_user: User = Depends(get_current_active_user),
    service: ForecastService = Depends(get_forecast_service),
) -> None:
    """Update a forecast. Creates new version or forks.

    **DEPRECATED**: This endpoint is deprecated as of 2026-01-18.

    Forecasts now have a 1:1 relationship with Cost Elements.
    Use: PUT /api/v1/cost-elements/{cost_element_id}/forecast
    """
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail={
            "message": "This endpoint is deprecated. Use the cost element forecast endpoint instead.",
            "new_endpoint": "PUT /api/v1/cost-elements/{cost_element_id}/forecast",
            "deprecated_since": "2026-01-18",
        },
    )


@router.delete(
    "/{forecast_id}",
    status_code=status.HTTP_410_GONE,
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
    """Soft delete a forecast in a branch.

    **DEPRECATED**: This endpoint is deprecated as of 2026-01-18.

    Forecasts now have a 1:1 relationship with Cost Elements.
    Use: DELETE /api/v1/cost-elements/{cost_element_id}/forecast
    """
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail={
            "message": "This endpoint is deprecated. Use the cost element forecast endpoint instead.",
            "new_endpoint": "DELETE /api/v1/cost-elements/{cost_element_id}/forecast",
            "deprecated_since": "2026-01-18",
        },
    )


@router.get(
    "/{forecast_id}/history",
    response_model=None,
    operation_id="get_forecast_history",
    dependencies=[Depends(RoleChecker(required_permission="forecast-read"))],
)
async def get_forecast_history(
    forecast_id: UUID,
    service: ForecastService = Depends(get_forecast_service),
) -> None:
    """Get full version history for a forecast across all branches.

    **DEPRECATED**: This endpoint is deprecated as of 2026-01-18.

    Forecast history is still available via the cost element history endpoint.
    Use: GET /api/v1/cost-elements/{cost_element_id}/history
    """
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail={
            "message": "This endpoint is deprecated. Use the cost element history endpoint instead.",
            "new_endpoint": "GET /api/v1/cost-elements/{cost_element_id}/history",
            "deprecated_since": "2026-01-18",
        },
    )


@router.get(
    "/{forecast_id}/comparison",
    response_model=None,
    operation_id="get_forecast_comparison",
    dependencies=[Depends(RoleChecker(required_permission="forecast-read"))],
)
async def get_forecast_comparison(
    forecast_id: UUID,
    branch: str = Query("main", description="Branch to query"),
    service: ForecastService = Depends(get_forecast_service),
) -> None:
    """Get EVM comparison metrics for a forecast.

    **DEPRECATED**: This endpoint is deprecated as of 2026-01-18.

    EVM metrics are now calculated via the cost element EVM endpoint.
    Use: GET /api/v1/cost-elements/{cost_element_id}/evm-metrics
    """
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail={
            "message": "This endpoint is deprecated. Use the cost element EVM metrics endpoint instead.",
            "new_endpoint": "GET /api/v1/cost-elements/{cost_element_id}/evm-metrics",
            "deprecated_since": "2026-01-18",
        },
    )
