"""Baseline Log API routes."""

import uuid
from datetime import date
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func
from sqlmodel import Session, select

from app.api.deps import CurrentUser, SessionDep
from app.models import (
    WBE,
    BaselineCostElement,
    BaselineCostElementCreate,
    BaselineCostElementPublic,
    BaselineCostElementsByWBEPublic,
    BaselineCostElementsPublic,
    BaselineCostElementWithCostElementPublic,
    BaselineLog,
    BaselineLogBase,
    BaselineLogPublic,
    BaselineLogUpdate,
    BaselineSnapshotSummaryPublic,
    CostElement,
    CostElementSchedule,
    CostRegistration,
    EarnedValueEntriesPublic,
    EarnedValueEntry,
    Forecast,
    Project,
    WBEWithBaselineCostElementsPublic,
)
from app.services.planned_value import calculate_cost_element_planned_value
from app.services.time_machine import (
    TimeMachineEventType,
    apply_time_machine_filters,
)

router = APIRouter(prefix="/projects", tags=["baseline-logs"])


def _select_schedule_for_baseline(
    session: Session, cost_element_id: uuid.UUID, reference_date: date
) -> CostElementSchedule | None:
    base_statement = (
        select(CostElementSchedule)
        .where(CostElementSchedule.cost_element_id == cost_element_id)
        .where(CostElementSchedule.baseline_id.is_(None))
    )

    prioritized = apply_time_machine_filters(
        base_statement, TimeMachineEventType.SCHEDULE, reference_date
    ).order_by(
        CostElementSchedule.registration_date.desc(),
        CostElementSchedule.created_at.desc(),
    )
    return session.exec(prioritized).first()


def create_baseline_cost_elements_for_baseline_log(
    session: Session,
    baseline_log: BaselineLog,
    created_by_id: uuid.UUID,  # noqa: ARG001
    department: str | None = None,
    is_pmb: bool | None = None,
) -> None:
    """
    Create baseline cost elements for a baseline log and set department/is_pmb on BaselineLog.

    This function:
    1. Sets department and is_pmb on BaselineLog (if provided)
    2. Gets all cost elements for the project (via WBEs)
    3. For each cost element, creates a BaselineCostElement record with:
       - budget_bac and revenue_plan from CostElement
       - actual_ac aggregated from CostRegistration records
       - forecast_eac from Forecast (is_current=True) if exists
       - earned_ev from EarnedValueEntry (latest by completion_date) if exists

    Args:
        session: Database session
        baseline_log: The BaselineLog entry to snapshot for
        created_by_id: User ID creating the snapshot (unused, kept for compatibility)
        department: Optional department name to set on BaselineLog
        is_pmb: Optional flag to set is_pmb on BaselineLog (None = don't update)

    Returns:
        None
    """
    # Set department and is_pmb on BaselineLog if provided
    if department is not None:
        baseline_log.department = department
    if is_pmb is not None:
        baseline_log.is_pmb = is_pmb
    session.add(baseline_log)
    session.flush()  # Flush to ensure BaselineLog changes are saved

    # Get all cost elements for the project via WBEs
    wbes = session.exec(
        select(WBE).where(WBE.project_id == baseline_log.project_id)
    ).all()

    existing_baseline_schedules = session.exec(
        select(CostElementSchedule).where(
            CostElementSchedule.baseline_id == baseline_log.baseline_id
        )
    ).all()
    for baseline_schedule in existing_baseline_schedules:
        session.delete(baseline_schedule)
    session.flush()

    cost_elements: list[CostElement] = []
    if wbes:
        wbe_ids = [wbe.wbe_id for wbe in wbes]
        cost_elements = session.exec(
            select(CostElement).where(CostElement.wbe_id.in_(wbe_ids))
        ).all()

    # For each cost element, create BaselineCostElement record
    for cost_element in cost_elements:
        # Get budget_bac and revenue_plan from CostElement
        budget_bac = cost_element.budget_bac
        revenue_plan = cost_element.revenue_plan

        # Aggregate actual_ac from CostRegistration records
        cost_registrations = session.exec(
            select(CostRegistration).where(
                CostRegistration.cost_element_id == cost_element.cost_element_id
            )
        ).all()
        actual_ac = (
            sum(cr.amount for cr in cost_registrations)
            if cost_registrations
            else Decimal("0.00")
        )

        # Get forecast_eac from Forecast (is_current=True) if exists
        forecast = session.exec(
            select(Forecast)
            .where(Forecast.cost_element_id == cost_element.cost_element_id)
            .where(Forecast.is_current.is_(True))
            .order_by(Forecast.forecast_date.desc())
        ).first()
        forecast_eac = forecast.estimate_at_completion if forecast else None

        # Get earned_ev from EarnedValueEntry (latest by completion_date) if exists
        earned_value_entry = session.exec(
            select(EarnedValueEntry)
            .where(EarnedValueEntry.cost_element_id == cost_element.cost_element_id)
            .order_by(EarnedValueEntry.completion_date.desc())
        ).first()
        earned_ev = earned_value_entry.earned_value if earned_value_entry else None
        percent_complete = (
            earned_value_entry.percent_complete if earned_value_entry else None
        )

        # Calculate planned value using schedule baseline (if available)
        planned_value = Decimal("0.00")
        schedule = _select_schedule_for_baseline(
            session, cost_element.cost_element_id, baseline_log.baseline_date
        )
        if schedule:
            planned_value, _ = calculate_cost_element_planned_value(
                cost_element=cost_element,
                schedule=schedule,
                control_date=baseline_log.baseline_date,
            )
            baseline_schedule = CostElementSchedule(
                cost_element_id=schedule.cost_element_id,
                baseline_id=baseline_log.baseline_id,
                start_date=schedule.start_date,
                end_date=schedule.end_date,
                progression_type=schedule.progression_type,
                registration_date=schedule.registration_date,
                description=schedule.description,
                notes=schedule.notes,
                created_by_id=schedule.created_by_id,
            )
            session.add(baseline_schedule)

        # Create BaselineCostElement record
        baseline_cost_element_in = BaselineCostElementCreate(
            baseline_id=baseline_log.baseline_id,
            cost_element_id=cost_element.cost_element_id,
            budget_bac=budget_bac,
            revenue_plan=revenue_plan,
            actual_ac=actual_ac,
            forecast_eac=forecast_eac,
            earned_ev=earned_ev,
            percent_complete=percent_complete,
            planned_value=planned_value,
        )
        baseline_cost_element = BaselineCostElement.model_validate(
            baseline_cost_element_in
        )
        session.add(baseline_cost_element)

    session.commit()


@router.get("/{project_id}/baseline-logs/", response_model=list[BaselineLogPublic])
def list_baseline_logs(
    session: SessionDep,
    _current_user: CurrentUser,
    project_id: uuid.UUID,
    exclude_cancelled: bool = Query(
        default=False, description="Exclude cancelled baselines"
    ),
) -> Any:
    """
    List all baseline logs for a project.

    Args:
        project_id: ID of the project
        exclude_cancelled: If True, filter out cancelled baselines

    Returns:
        List of BaselineLogPublic
    """
    # Validate project exists
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Build query
    statement = select(BaselineLog).where(BaselineLog.project_id == project_id)

    # Apply cancelled filter if requested
    if exclude_cancelled:
        statement = statement.where(BaselineLog.is_cancelled.is_(False))

    # Order by baseline_date descending (most recent first)
    statement = statement.order_by(BaselineLog.baseline_date.desc())

    baselines = session.exec(statement).all()
    return baselines


@router.get(
    "/{project_id}/baseline-logs/{baseline_id}", response_model=BaselineLogPublic
)
def read_baseline_log(
    session: SessionDep,
    _current_user: CurrentUser,
    project_id: uuid.UUID,
    baseline_id: uuid.UUID,
) -> Any:
    """
    Get a single baseline log by ID.

    Args:
        project_id: ID of the project
        baseline_id: ID of the baseline log

    Returns:
        BaselineLogPublic
    """
    # Validate project exists
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get baseline and verify it belongs to the project
    baseline = session.get(BaselineLog, baseline_id)
    if not baseline:
        raise HTTPException(status_code=404, detail="Baseline log not found")

    if baseline.project_id != project_id:
        raise HTTPException(status_code=404, detail="Baseline log not found")

    return baseline


# Valid baseline types
VALID_BASELINE_TYPES = {
    "schedule",
    "earned_value",
    "budget",
    "forecast",
    "combined",
}

# Valid milestone types
VALID_MILESTONE_TYPES = {
    "kickoff",
    "bom_release",
    "engineering_complete",
    "procurement_complete",
    "manufacturing_start",
    "shipment",
    "site_arrival",
    "commissioning_start",
    "commissioning_complete",
    "closeout",
}


def validate_baseline_type(baseline_type: str) -> None:
    """Validate baseline_type enum."""
    if baseline_type not in VALID_BASELINE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid baseline_type: {baseline_type}. Must be one of: {', '.join(sorted(VALID_BASELINE_TYPES))}",
        )


def validate_milestone_type(milestone_type: str) -> None:
    """Validate milestone_type enum."""
    if milestone_type not in VALID_MILESTONE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid milestone_type: {milestone_type}. Must be one of: {', '.join(sorted(VALID_MILESTONE_TYPES))}",
        )


@router.post("/{project_id}/baseline-logs/", response_model=BaselineLogPublic)
def create_baseline_log(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    project_id: uuid.UUID,
    baseline_in: BaselineLogBase,
) -> Any:
    """
    Create a new baseline log for a project.

    This endpoint automatically creates a baseline snapshot with all cost elements
    for the project when the baseline is created.

    Args:
        project_id: ID of the project
        baseline_in: Baseline log creation data (baseline_type, baseline_date, milestone_type, description, is_cancelled)

    Returns:
        BaselineLogPublic
    """
    # Validate project exists
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Validate baseline_type
    validate_baseline_type(baseline_in.baseline_type)

    # Validate milestone_type
    validate_milestone_type(baseline_in.milestone_type)

    # Create BaselineLog record
    baseline_data = baseline_in.model_dump()
    baseline_data["project_id"] = project_id
    baseline_data["created_by_id"] = current_user.id
    baseline = BaselineLog.model_validate(baseline_data)
    session.add(baseline)
    session.flush()  # Flush to get baseline_id before snapshotting

    # Automatically create baseline cost elements (NO BaselineSnapshot)
    create_baseline_cost_elements_for_baseline_log(
        session=session,
        baseline_log=baseline,
        created_by_id=current_user.id,
        department=baseline_in.department,
        is_pmb=baseline_in.is_pmb,
    )

    session.commit()
    session.refresh(baseline)
    return baseline


@router.put(
    "/{project_id}/baseline-logs/{baseline_id}", response_model=BaselineLogPublic
)
def update_baseline_log(
    *,
    session: SessionDep,
    _current_user: CurrentUser,
    project_id: uuid.UUID,
    baseline_id: uuid.UUID,
    baseline_in: BaselineLogUpdate,
) -> Any:
    """
    Update a baseline log.

    Args:
        project_id: ID of the project
        baseline_id: ID of the baseline log
        baseline_in: Baseline log update data

    Returns:
        BaselineLogPublic
    """
    # Validate project exists
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get baseline and verify it belongs to the project
    baseline = session.get(BaselineLog, baseline_id)
    if not baseline:
        raise HTTPException(status_code=404, detail="Baseline log not found")

    if baseline.project_id != project_id:
        raise HTTPException(status_code=404, detail="Baseline log not found")

    # Get update dict (exclude_unset=True to only update provided fields)
    update_dict = baseline_in.model_dump(exclude_unset=True)

    # Validate baseline_type if being updated
    if "baseline_type" in update_dict:
        validate_baseline_type(update_dict["baseline_type"])

    # Validate milestone_type if being updated
    if "milestone_type" in update_dict:
        validate_milestone_type(update_dict["milestone_type"])

    # Update baseline
    baseline.sqlmodel_update(update_dict)
    session.add(baseline)
    session.commit()
    session.refresh(baseline)
    return baseline


@router.put(
    "/{project_id}/baseline-logs/{baseline_id}/cancel", response_model=BaselineLogPublic
)
def cancel_baseline_log(
    *,
    session: SessionDep,
    _current_user: CurrentUser,
    project_id: uuid.UUID,
    baseline_id: uuid.UUID,
) -> Any:
    """
    Cancel (soft delete) a baseline log by setting is_cancelled=True.

    Args:
        project_id: ID of the project
        baseline_id: ID of the baseline log

    Returns:
        BaselineLogPublic
    """
    # Validate project exists
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get baseline and verify it belongs to the project
    baseline = session.get(BaselineLog, baseline_id)
    if not baseline:
        raise HTTPException(status_code=404, detail="Baseline log not found")

    if baseline.project_id != project_id:
        raise HTTPException(status_code=404, detail="Baseline log not found")

    # Set is_cancelled=True
    baseline.is_cancelled = True
    session.add(baseline)
    session.commit()
    session.refresh(baseline)
    return baseline


@router.get(
    "/{project_id}/baseline-logs/{baseline_id}/snapshot",
    response_model=BaselineSnapshotSummaryPublic,
)
def get_baseline_snapshot_summary(
    *,
    session: SessionDep,
    _current_user: CurrentUser,
    project_id: uuid.UUID,
    baseline_id: uuid.UUID,
) -> Any:
    """
    Get baseline snapshot summary with aggregated project values.

    Returns snapshot metadata and aggregated totals from all BaselineCostElement
    records for this baseline:
    - total_budget_bac: Sum of all budget_bac values
    - total_revenue_plan: Sum of all revenue_plan values
    - total_planned_value: Sum of all planned_value values
    - total_actual_ac: Sum of all actual_ac values (handles NULLs)
    - total_forecast_eac: Sum of all forecast_eac values (handles NULLs)
    - total_earned_ev: Sum of all earned_ev values (handles NULLs)
    - cost_element_count: Count of BaselineCostElement records

    Args:
        project_id: ID of the project
        baseline_id: ID of the baseline log

    Returns:
        BaselineSnapshotSummaryPublic
    """
    # Validate project exists
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get baseline and verify it belongs to the project
    baseline = session.get(BaselineLog, baseline_id)
    if not baseline:
        raise HTTPException(status_code=404, detail="Baseline log not found")

    if baseline.project_id != project_id:
        raise HTTPException(status_code=404, detail="Baseline log not found")

    # Get all BaselineCostElement records for this baseline
    baseline_cost_elements = session.exec(
        select(BaselineCostElement).where(
            BaselineCostElement.baseline_id == baseline_id
        )
    ).all()

    # Aggregate values
    total_budget_bac = sum(bce.budget_bac for bce in baseline_cost_elements) or Decimal(
        "0.00"
    )
    total_revenue_plan = sum(
        bce.revenue_plan for bce in baseline_cost_elements
    ) or Decimal("0.00")
    total_planned_value = sum(
        bce.planned_value for bce in baseline_cost_elements
    ) or Decimal("0.00")

    # Handle NULL values for optional fields
    actual_ac_values = [
        bce.actual_ac for bce in baseline_cost_elements if bce.actual_ac is not None
    ]
    total_actual_ac = sum(actual_ac_values) if actual_ac_values else None

    forecast_eac_values = [
        bce.forecast_eac
        for bce in baseline_cost_elements
        if bce.forecast_eac is not None
    ]
    total_forecast_eac = sum(forecast_eac_values) if forecast_eac_values else None

    earned_ev_values = [
        bce.earned_ev for bce in baseline_cost_elements if bce.earned_ev is not None
    ]
    total_earned_ev = sum(earned_ev_values) if earned_ev_values else None

    cost_element_count = len(baseline_cost_elements)

    # Create summary response using BaselineLog data (not BaselineSnapshot)
    # Use baseline_id as snapshot_id for backward compatibility
    summary = BaselineSnapshotSummaryPublic(
        snapshot_id=baseline.baseline_id,  # Use baseline_id instead of snapshot_id
        baseline_id=baseline.baseline_id,
        baseline_date=baseline.baseline_date,
        milestone_type=baseline.milestone_type,
        description=baseline.description,
        total_budget_bac=total_budget_bac,
        total_revenue_plan=total_revenue_plan,
        total_planned_value=total_planned_value,
        total_actual_ac=total_actual_ac,
        total_forecast_eac=total_forecast_eac,
        total_earned_ev=total_earned_ev,
        cost_element_count=cost_element_count,
    )

    return summary


@router.get(
    "/{project_id}/baseline-logs/{baseline_id}/cost-elements-by-wbe",
    response_model=BaselineCostElementsByWBEPublic,
)
def get_baseline_cost_elements_by_wbe(
    *,
    session: SessionDep,
    _current_user: CurrentUser,
    project_id: uuid.UUID,
    baseline_id: uuid.UUID,
) -> Any:
    """
    Get baseline cost elements grouped by WBE.

    Returns all WBEs for the project with their associated BaselineCostElement records
    for the specified baseline, including aggregated totals per WBE.

    Args:
        project_id: ID of the project
        baseline_id: ID of the baseline log

    Returns:
        BaselineCostElementsByWBEPublic
    """
    # Validate project exists
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get baseline and verify it belongs to the project
    baseline = session.get(BaselineLog, baseline_id)
    if not baseline:
        raise HTTPException(status_code=404, detail="Baseline log not found")

    if baseline.project_id != project_id:
        raise HTTPException(status_code=404, detail="Baseline log not found")

    # Get all WBEs for the project
    wbes = session.exec(select(WBE).where(WBE.project_id == project_id)).all()

    baseline_schedule_map = {
        schedule.cost_element_id: schedule
        for schedule in session.exec(
            select(CostElementSchedule).where(
                CostElementSchedule.baseline_id == baseline_id
            )
        ).all()
    }

    # Build response: for each WBE, get baseline cost elements and aggregate
    wbes_with_cost_elements = []
    for wbe in wbes:
        # Get all BaselineCostElement records for this baseline + WBE (via CostElement join)
        baseline_cost_elements = session.exec(
            select(BaselineCostElement, CostElement)
            .join(
                CostElement,
                BaselineCostElement.cost_element_id == CostElement.cost_element_id,
            )
            .where(
                BaselineCostElement.baseline_id == baseline_id,
                CostElement.wbe_id == wbe.wbe_id,
            )
        ).all()

        # Build list of cost elements with CostElement and WBE fields
        cost_elements_list = []
        for bce, ce in baseline_cost_elements:
            baseline_schedule = baseline_schedule_map.get(bce.cost_element_id)
            cost_element_data = BaselineCostElementWithCostElementPublic(
                baseline_cost_element_id=bce.baseline_cost_element_id,
                baseline_id=bce.baseline_id,
                cost_element_id=bce.cost_element_id,
                budget_bac=bce.budget_bac,
                revenue_plan=bce.revenue_plan,
                planned_value=bce.planned_value,
                actual_ac=bce.actual_ac,
                forecast_eac=bce.forecast_eac,
                earned_ev=bce.earned_ev,
                created_at=bce.created_at,
                department_code=ce.department_code,
                department_name=ce.department_name,
                cost_element_type_id=ce.cost_element_type_id,
                wbe_id=wbe.wbe_id,
                wbe_machine_type=wbe.machine_type,
                schedule_start_date=baseline_schedule.start_date
                if baseline_schedule
                else None,
                schedule_end_date=baseline_schedule.end_date
                if baseline_schedule
                else None,
                schedule_progression_type=baseline_schedule.progression_type
                if baseline_schedule
                else None,
                schedule_registration_date=baseline_schedule.registration_date
                if baseline_schedule
                else None,
                schedule_description=baseline_schedule.description
                if baseline_schedule
                else None,
                schedule_notes=baseline_schedule.notes if baseline_schedule else None,
            )
            cost_elements_list.append(cost_element_data)

        # Aggregate WBE totals
        wbe_total_budget_bac = sum(
            ce.budget_bac for ce in cost_elements_list
        ) or Decimal("0.00")
        wbe_total_revenue_plan = sum(
            ce.revenue_plan for ce in cost_elements_list
        ) or Decimal("0.00")
        wbe_total_planned_value = sum(
            ce.planned_value for ce in cost_elements_list
        ) or Decimal("0.00")

        # Handle NULL values for optional fields
        actual_ac_values = [
            ce.actual_ac for ce in cost_elements_list if ce.actual_ac is not None
        ]
        wbe_total_actual_ac = sum(actual_ac_values) if actual_ac_values else None

        forecast_eac_values = [
            ce.forecast_eac for ce in cost_elements_list if ce.forecast_eac is not None
        ]
        wbe_total_forecast_eac = (
            sum(forecast_eac_values) if forecast_eac_values else None
        )

        earned_ev_values = [
            ce.earned_ev for ce in cost_elements_list if ce.earned_ev is not None
        ]
        wbe_total_earned_ev = sum(earned_ev_values) if earned_ev_values else None

        # Create WBE with cost elements
        wbe_with_cost_elements = WBEWithBaselineCostElementsPublic(
            wbe_id=wbe.wbe_id,
            machine_type=wbe.machine_type,
            serial_number=wbe.serial_number,
            cost_elements=cost_elements_list,
            wbe_total_budget_bac=wbe_total_budget_bac,
            wbe_total_revenue_plan=wbe_total_revenue_plan,
            wbe_total_planned_value=wbe_total_planned_value,
            wbe_total_actual_ac=wbe_total_actual_ac,
            wbe_total_forecast_eac=wbe_total_forecast_eac,
            wbe_total_earned_ev=wbe_total_earned_ev,
        )
        wbes_with_cost_elements.append(wbe_with_cost_elements)

    # Return response
    return BaselineCostElementsByWBEPublic(
        baseline_id=baseline_id,
        wbes=wbes_with_cost_elements,
    )


def read_baseline_log_cost_elements(
    *,
    session: Session,
    cost_element_id: uuid.UUID | None = None,
    skip: int = 0,
    limit: int = 100,
) -> tuple[list[BaselineCostElementPublic], int]:
    # Implementation here
    # Filter by cost_element_id if provided
    query = select(BaselineCostElementPublic)
    if cost_element_id:
        query = query.where(BaselineCostElement.cost_element_id == cost_element_id)

    # Apply pagination
    query = query.offset(skip).limit(limit)
    total_query = select(func.count(BaselineCostElement.baseline_cost_element_id))
    if cost_element_id:
        total_query = total_query.where(
            BaselineCostElement.cost_element_id == cost_element_id
        )

    # Execute queries
    baseline_cost_elements = session.exec(query).all()
    total_count = session.exec(total_query).one()

    return baseline_cost_elements, total_count


@router.get(
    "/{project_id}/baseline-logs/{baseline_id}/cost-elements",
    response_model=BaselineCostElementsPublic,
)
def get_baseline_cost_elements(
    *,
    session: SessionDep,
    _current_user: CurrentUser,
    project_id: uuid.UUID,
    baseline_id: uuid.UUID,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
) -> Any:
    """
    Get baseline cost elements as a flat paginated list.

    Returns all BaselineCostElement records for the specified baseline,
    including related CostElement and WBE information, with pagination support.

    Args:
        project_id: ID of the project
        baseline_id: ID of the baseline log
        skip: Number of records to skip (for pagination)
        limit: Maximum number of records to return (1-100)

    Returns:
        BaselineCostElementsPublic: Paginated list of baseline cost elements
    """
    # Validate project exists
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get baseline and verify it belongs to the project
    baseline = session.get(BaselineLog, baseline_id)
    if not baseline:
        raise HTTPException(status_code=404, detail="Baseline log not found")

    if baseline.project_id != project_id:
        raise HTTPException(status_code=404, detail="Baseline log not found")

    # Count total BaselineCostElement records for this baseline
    count_statement = (
        select(func.count())
        .select_from(BaselineCostElement)
        .where(BaselineCostElement.baseline_id == baseline_id)
    )
    count = session.exec(count_statement).one()

    baseline_schedule_map = {
        schedule.cost_element_id: schedule
        for schedule in session.exec(
            select(CostElementSchedule).where(
                CostElementSchedule.baseline_id == baseline_id
            )
        ).all()
    }

    # Get paginated BaselineCostElement records with joins to CostElement and WBE
    statement = (
        select(BaselineCostElement, CostElement, WBE)
        .join(
            CostElement,
            BaselineCostElement.cost_element_id == CostElement.cost_element_id,
        )
        .join(WBE, CostElement.wbe_id == WBE.wbe_id)
        .where(BaselineCostElement.baseline_id == baseline_id)
        .offset(skip)
        .limit(limit)
    )
    results = session.exec(statement).all()

    # Build response list with all required fields
    cost_elements_list = []
    for bce, ce, wbe in results:
        baseline_schedule = baseline_schedule_map.get(bce.cost_element_id)
        cost_element_data = BaselineCostElementWithCostElementPublic(
            baseline_cost_element_id=bce.baseline_cost_element_id,
            baseline_id=bce.baseline_id,
            cost_element_id=bce.cost_element_id,
            budget_bac=bce.budget_bac,
            revenue_plan=bce.revenue_plan,
            planned_value=bce.planned_value,
            actual_ac=bce.actual_ac,
            forecast_eac=bce.forecast_eac,
            earned_ev=bce.earned_ev,
            percent_complete=bce.percent_complete,
            created_at=bce.created_at,
            department_code=ce.department_code,
            department_name=ce.department_name,
            cost_element_type_id=ce.cost_element_type_id,
            wbe_id=wbe.wbe_id,
            wbe_machine_type=wbe.machine_type,
            schedule_start_date=baseline_schedule.start_date
            if baseline_schedule
            else None,
            schedule_end_date=baseline_schedule.end_date if baseline_schedule else None,
            schedule_progression_type=baseline_schedule.progression_type
            if baseline_schedule
            else None,
            schedule_registration_date=baseline_schedule.registration_date
            if baseline_schedule
            else None,
            schedule_description=baseline_schedule.description
            if baseline_schedule
            else None,
            schedule_notes=baseline_schedule.notes if baseline_schedule else None,
        )
        cost_elements_list.append(cost_element_data)

    return BaselineCostElementsPublic(data=cost_elements_list, count=count)


@router.get(
    "/{project_id}/baseline-logs/{baseline_id}/earned-value-entries",
    response_model=EarnedValueEntriesPublic,
)
def get_baseline_earned_value_entries(
    *,
    session: SessionDep,
    _current_user: CurrentUser,
    project_id: uuid.UUID,
    baseline_id: uuid.UUID,
    cost_element_id: uuid.UUID | None = Query(
        default=None, description="Filter by cost element ID"
    ),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
) -> Any:
    """
    Get earned value entries associated with a specific baseline.

    Args:
        project_id: ID of the project
        baseline_id: ID of the baseline log
        cost_element_id: Optional filter for a specific cost element
        skip: Pagination offset
        limit: Pagination limit

    Returns:
        EarnedValueEntriesPublic
    """
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    baseline = session.get(BaselineLog, baseline_id)
    if not baseline or baseline.project_id != project_id:
        raise HTTPException(status_code=404, detail="Baseline log not found")

    # Earned value entries are no longer linked to baselines directly.
    # Return an empty result set to keep the endpoint backwards compatible.
    # Using the parameters to avoid linting errors
    _ = cost_element_id  # Use the parameter to avoid unused variable warning
    _ = skip
    _ = limit

    return EarnedValueEntriesPublic(data=[], count=0)
