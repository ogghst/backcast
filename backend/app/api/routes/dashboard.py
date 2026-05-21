"""Dashboard API routes with authentication."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import RoleChecker, UserIdentity, get_current_user
from app.core.rbac_unified import rbac_session
from app.db.session import get_db
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
    dependencies=[Depends(RoleChecker(required_permission="project-read"))],
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
    as_of: datetime | None = Query(
        None, alias="asOf", description="Optional timestamp for time-travel queries"
    ),
    branch: str = Query("main", description="Branch name to query"),
    service: DashboardService = Depends(get_dashboard_service),
    current_user: UserIdentity = Depends(get_current_user),
) -> DashboardData:
    """Get dashboard data with recent activity and project spotlight.

    Returns aggregated dashboard data including:
    - Last edited project with metrics (budget, WBEs, cost elements, change orders)
    - Recent activity across Projects, WBEs, Cost Elements, and Change Orders

    The activity_limit parameter controls how many recent items to return per
    entity type (default: 10, max: 50).

    The as_of parameter enables time-travel queries, returning data as it
    appeared at a specific point in time.

    The branch parameter controls which branch to query (default: "main").

    Requires authentication.
    """
    async with rbac_session(service.session):
        return await service.get_dashboard_data(
            user_id=current_user.user_id,
            activity_limit=activity_limit,
            as_of=as_of,
            branch=branch,
        )
