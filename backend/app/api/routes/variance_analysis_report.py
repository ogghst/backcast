"""Variance Analysis Report API endpoints."""

import uuid
from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import (
    CurrentUser,
    SessionDep,
    get_time_machine_control_date,
)
from app.models import WBE, CostElement, Project
from app.models.variance_analysis_report import (
    VarianceAnalysisReportPublic,
    VarianceTrendPublic,
)
from app.services.time_machine import end_of_day
from app.services.variance_analysis_report import (
    get_variance_analysis_report,
    get_variance_trend,
)

router = APIRouter(prefix="/projects", tags=["reports"])


def _ensure_project_exists(session: SessionDep, project_id: uuid.UUID) -> Project:
    """Ensure project exists and return it."""
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.get(
    "/{project_id}/reports/variance-analysis",
    response_model=VarianceAnalysisReportPublic,
)
def get_project_variance_analysis_report_endpoint(
    *,
    session: SessionDep,
    _current_user: CurrentUser,
    project_id: uuid.UUID,
    control_date: Annotated[date, Depends(get_time_machine_control_date)],
    show_only_problems: bool = Query(
        default=True,
        description="Filter to show only problem areas (negative CV or SV)",
    ),
    sort_by: str = Query(
        default="cv",
        description="Sort field: 'cv' (cost variance) or 'sv' (schedule variance)",
    ),
) -> Any:
    """Get variance analysis report for a project.

    Returns:
        VarianceAnalysisReportPublic with filtered/sorted rows and project summary.
        Rows emphasize variance metrics (CV, SV, CV%, SV%) and include severity indicators.
        Default: shows only problem areas (negative variances), sorted by most negative CV.
    """
    # Validate sort_by parameter
    if sort_by not in ("cv", "sv"):
        raise HTTPException(
            status_code=400,
            detail="sort_by must be 'cv' or 'sv'",
        )

    # Ensure project exists and respect time-machine
    project = _ensure_project_exists(session, project_id)
    cutoff = end_of_day(control_date)
    if project.created_at > cutoff:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get report using service function
    try:
        report = get_variance_analysis_report(
            session=session,
            project_id=project_id,
            control_date=control_date,
            show_only_problems=show_only_problems,
            sort_by=sort_by,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return report


@router.get(
    "/{project_id}/reports/variance-analysis/trend",
    response_model=VarianceTrendPublic,
)
def get_variance_trend_endpoint(
    *,
    session: SessionDep,
    _current_user: CurrentUser,
    project_id: uuid.UUID,
    control_date: Annotated[date, Depends(get_time_machine_control_date)],
    wbe_id: uuid.UUID | None = Query(
        default=None,
        description="Optional WBE ID for WBE-level trend",
    ),
    cost_element_id: uuid.UUID | None = Query(
        default=None,
        description="Optional cost element ID for cost element-level trend (cannot be used with wbe_id)",
    ),
) -> Any:
    """Get variance trend analysis showing monthly variance evolution over time.

    Returns:
        VarianceTrendPublic with monthly variance trend points from project start to control date.
        Each point contains CV, SV, CV%, SV% as of that month's end.
        Supports project level (default), WBE level (wbe_id), or cost element level (cost_element_id).
    """
    # Validate that cost_element_id and wbe_id are not both provided
    if cost_element_id is not None and wbe_id is not None:
        raise HTTPException(
            status_code=400,
            detail="Cannot provide both wbe_id and cost_element_id",
        )

    # Ensure project exists and respect time-machine
    project = _ensure_project_exists(session, project_id)
    cutoff = end_of_day(control_date)
    if project.created_at > cutoff:
        raise HTTPException(status_code=404, detail="Project not found")

    # Validate wbe_id if provided
    if wbe_id is not None:
        wbe = session.get(WBE, wbe_id)
        if not wbe or wbe.project_id != project_id:
            raise HTTPException(status_code=404, detail="WBE not found")

    # Validate cost_element_id if provided
    if cost_element_id is not None:
        cost_element = session.get(CostElement, cost_element_id)
        if not cost_element:
            raise HTTPException(status_code=404, detail="Cost element not found")
        # Verify cost element belongs to project via WBE
        wbe = session.get(WBE, cost_element.wbe_id)
        if not wbe or wbe.project_id != project_id:
            raise HTTPException(
                status_code=404, detail="Cost element not found in project"
            )

    # Get trend using service function
    try:
        trend = get_variance_trend(
            session=session,
            project_id=project_id,
            control_date=control_date,
            cost_element_id=cost_element_id,
            wbe_id=wbe_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return trend
