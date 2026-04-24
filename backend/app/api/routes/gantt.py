"""Gantt chart API routes."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import ProjectRoleChecker, get_current_active_user
from app.db.session import get_db
from app.models.domain.user import User
from app.models.schemas.gantt import GanttDataResponse
from app.services.gantt_service import GanttService

router = APIRouter()


def get_gantt_service(
    session: AsyncSession = Depends(get_db),
) -> GanttService:
    """Get Gantt service instance."""
    return GanttService(session)


@router.get(
    "/{project_id}/gantt-data",
    response_model=GanttDataResponse,
    operation_id="get_project_gantt_data",
    dependencies=[Depends(ProjectRoleChecker(required_permission="cost-element-read"))],
)
async def get_gantt_data(
    project_id: UUID,
    branch: str = Query("main", description="Branch to query"),
    mode: str = Query(
        "merged",
        pattern="^(merged|isolated)$",
        description="Branch mode: merged or isolated",
    ),
    as_of: datetime | None = Query(
        None,
        description="Time travel: get data as of this timestamp (ISO 8601)",
    ),
    service: GanttService = Depends(get_gantt_service),
    _current_user: User = Depends(get_current_active_user),
) -> GanttDataResponse:
    """Get aggregated Gantt chart data for a project.

    Returns WBE hierarchy with cost elements and their schedule baselines,
    filtered by branch, mode, and optional time-travel timestamp.
    """
    return await service.get_gantt_data(
        project_id=project_id,
        branch=branch,
        mode=mode,
        as_of=as_of,
    )
