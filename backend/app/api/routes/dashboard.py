"""Dashboard API routes with authentication."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_active_user
from app.db.session import get_db
from app.models.domain.user import User
from app.models.schemas.dashboard import DashboardData
from app.services.dashboard_service import DashboardService

router = APIRouter()


def get_dashboard_service(
    session: AsyncSession = Depends(get_db),
) -> DashboardService:
    """Get dashboard service instance.

    Args:
        session: Database session

    Returns:
        DashboardService instance
    """
    return DashboardService(session)


@router.get(
    "/recent-activity",
    response_model=DashboardData,
    operation_id="get_dashboard_recent_activity",
)
async def get_dashboard_recent_activity(
    activity_limit: Annotated[
        int,
        Query(
            ge=1,
            le=50,
            description="Maximum number of activities per entity type (1-50)",
        ),
    ] = 10,
    service: DashboardService = Depends(get_dashboard_service),
    current_user: User = Depends(get_current_active_user),
) -> DashboardData:
    """Get dashboard data with recent activity and project spotlight.

    Returns aggregated dashboard data including:
    - Last edited project with metrics (budget, WBEs, cost elements, change orders)
    - Recent activity across Projects, WBEs, Cost Elements, and Change Orders

    The activity_limit parameter controls how many recent items to return per
    entity type (default: 10, max: 50).

    Requires authentication.
    """
    return await service.get_dashboard_data(
        user_id=current_user.user_id,
        activity_limit=activity_limit,
    )
