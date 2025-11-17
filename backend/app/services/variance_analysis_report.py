"""Variance Analysis Report service."""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from decimal import Decimal

from sqlmodel import Session, select

from app.models import (
    WBE,
    CostElement,
    CostElementType,
    CostRegistration,
    Project,
    VarianceThresholdConfig,
)
from app.models.evm_indices import EVMIndicesProjectPublic
from app.models.variance_analysis_report import (
    VarianceAnalysisReportPublic,
    VarianceAnalysisReportRowPublic,
    VarianceTrendPointPublic,
    VarianceTrendPublic,
)
from app.services.evm_aggregation import get_cost_element_evm_metrics
from app.services.time_machine import (
    TimeMachineEventType,
    apply_time_machine_filters,
    end_of_day,
)


def get_active_variance_thresholds(session: Session) -> dict[str, Decimal]:
    """Get active variance threshold configurations from database.

    Returns:
        Dictionary mapping threshold_type to threshold_percentage.
        Keys: 'critical_cv', 'warning_cv', 'critical_sv', 'warning_sv'
        Returns None for missing threshold types.
    """
    statement = select(VarianceThresholdConfig).where(
        VarianceThresholdConfig.is_active == True  # noqa: E712
    )
    configs = session.exec(statement).all()

    # Build dictionary mapping threshold_type to threshold_percentage
    thresholds: dict[str, Decimal] = {}
    for config in configs:
        thresholds[config.threshold_type.value] = config.threshold_percentage

    return thresholds


def calculate_variance_severity(
    cv_percentage: Decimal | None,
    sv_percentage: Decimal | None,
    thresholds: dict[str, Decimal],
) -> str | None:
    """Calculate variance severity based on thresholds.

    Args:
        cv_percentage: Cost variance percentage (CV/BAC * 100), None if BAC = 0
        sv_percentage: Schedule variance percentage (SV/BAC * 100), None if BAC = 0
        thresholds: Dictionary mapping threshold_type to threshold_percentage

    Returns:
        'critical', 'warning', 'normal', or None if both percentages are undefined.
        Overall severity is the maximum severity of CV and SV.
    """

    # Helper function to determine severity for a single variance
    def _get_severity(
        percentage: Decimal | None, critical_key: str, warning_key: str
    ) -> str | None:
        if percentage is None:
            return None

        critical_threshold = thresholds.get(critical_key)
        warning_threshold = thresholds.get(warning_key)

        if critical_threshold is None or warning_threshold is None:
            # Missing thresholds, default to 'normal'
            return "normal"

        if percentage < critical_threshold:
            return "critical"
        elif percentage < warning_threshold:
            return "warning"
        else:
            return "normal"

    # Calculate severity for CV and SV
    cv_severity = _get_severity(cv_percentage, "critical_cv", "warning_cv")
    sv_severity = _get_severity(sv_percentage, "critical_sv", "warning_sv")

    # Overall severity is the maximum severity
    if cv_severity is None and sv_severity is None:
        return None

    # Severity order: critical > warning > normal
    severity_order = {"critical": 3, "warning": 2, "normal": 1}

    severities = [s for s in [cv_severity, sv_severity] if s is not None]
    if not severities:
        return None

    # Return the highest severity
    return max(severities, key=lambda s: severity_order[s])


def _get_schedule_map(
    session: Session, cost_element_ids: list, control_date: date
) -> dict:
    """Get schedule map for cost elements (reused from evm_aggregation)."""
    from app.api.routes.evm_aggregation import _get_schedule_map as get_schedule_map

    return get_schedule_map(session, cost_element_ids, control_date)


def _get_entry_map(
    session: Session, cost_element_ids: list, control_date: date
) -> dict:
    """Get earned value entry map for cost elements (reused from evm_aggregation)."""
    from app.api.routes.evm_aggregation import _get_entry_map as get_entry_map

    return get_entry_map(session, cost_element_ids, control_date)


def _calculate_variance_percentage(variance: Decimal, bac: Decimal) -> Decimal | None:
    """Calculate variance percentage (variance / BAC * 100). Returns None if BAC = 0."""
    if bac == 0:
        return None
    return (variance / bac) * Decimal("100")


def get_variance_analysis_report(
    session: Session,
    project_id: uuid.UUID,
    control_date: date,
    show_only_problems: bool = True,
    sort_by: str = "cv",
) -> VarianceAnalysisReportPublic:
    """Get variance analysis report for a project.

    Args:
        session: Database session
        project_id: Project ID
        control_date: Control date for time-machine filtering
        show_only_problems: If True, filter to rows with negative CV or SV (default: True)
        sort_by: Sort field ('cv' or 'sv'), defaults to 'cv' (most negative first)

    Returns:
        VarianceAnalysisReportPublic with filtered/sorted rows and project summary
    """
    # Get project
    project = session.get(Project, project_id)
    if not project:
        raise ValueError(f"Project {project_id} not found")

    # Get active variance thresholds
    thresholds = get_active_variance_thresholds(session)

    # Get all WBEs for project (respecting control date)
    cutoff = end_of_day(control_date)
    wbes = session.exec(
        select(WBE).where(
            WBE.project_id == project_id,
            WBE.created_at <= cutoff,
        )
    ).all()

    # Get all cost elements for project (respecting control date)
    cost_elements = session.exec(
        select(CostElement)
        .join(WBE)
        .where(
            WBE.project_id == project_id,
            CostElement.created_at <= cutoff,
        )
    ).all()

    if not cost_elements:
        # Return empty report with zero summary
        summary = EVMIndicesProjectPublic(
            level="project",
            control_date=control_date,
            project_id=project.project_id,
            planned_value=Decimal("0.00"),
            earned_value=Decimal("0.00"),
            actual_cost=Decimal("0.00"),
            budget_bac=Decimal("0.00"),
            cpi=None,
            spi=None,
            tcpi=None,
            cost_variance=Decimal("0.00"),
            schedule_variance=Decimal("0.00"),
        )
        return VarianceAnalysisReportPublic(
            project_id=project.project_id,
            project_name=project.project_name,
            control_date=control_date,
            rows=[],
            summary=summary,
            total_problem_areas=0,
            config_used={k: str(v) for k, v in thresholds.items()},
        )

    # Create WBE lookup map
    wbe_map = {wbe.wbe_id: wbe for wbe in wbes}

    # Get cost element IDs
    cost_element_ids = [ce.cost_element_id for ce in cost_elements]

    # Get schedules
    schedule_map = _get_schedule_map(session, cost_element_ids, control_date)

    # Get earned value entries
    entry_map = _get_entry_map(session, cost_element_ids, control_date)

    # Get cost registrations
    statement = select(CostRegistration).where(
        CostRegistration.cost_element_id.in_(cost_element_ids),
    )
    statement = apply_time_machine_filters(
        statement, TimeMachineEventType.COST_REGISTRATION, control_date
    )
    all_cost_registrations = session.exec(statement).all()

    # Group cost registrations by cost element
    cost_registrations_by_ce: dict = {}
    for cr in all_cost_registrations:
        if cr.cost_element_id not in cost_registrations_by_ce:
            cost_registrations_by_ce[cr.cost_element_id] = []
        cost_registrations_by_ce[cr.cost_element_id].append(cr)

    # Get cost element types for metadata
    cost_element_type_ids = {
        ce.cost_element_type_id
        for ce in cost_elements
        if ce.cost_element_type_id is not None
    }
    cost_element_types = {}
    if cost_element_type_ids:
        cet_list = session.exec(
            select(CostElementType).where(
                CostElementType.cost_element_type_id.in_(cost_element_type_ids)
            )
        ).all()
        cost_element_types = {cet.cost_element_type_id: cet for cet in cet_list}

    # Calculate metrics for each cost element and build rows
    rows = []
    total_pv = Decimal("0.00")
    total_ev = Decimal("0.00")
    total_ac = Decimal("0.00")
    total_bac = Decimal("0.00")
    total_problem_areas = 0

    for cost_element in cost_elements:
        wbe = wbe_map.get(cost_element.wbe_id)
        if not wbe:
            continue  # Skip if WBE not found (shouldn't happen)

        # Get EVM metrics
        metrics = get_cost_element_evm_metrics(
            cost_element=cost_element,
            schedule=schedule_map.get(cost_element.cost_element_id),
            entry=entry_map.get(cost_element.cost_element_id),
            cost_registrations=cost_registrations_by_ce.get(
                cost_element.cost_element_id, []
            ),
            control_date=control_date,
        )

        # Calculate variance percentages
        cv_percentage = _calculate_variance_percentage(
            metrics.cost_variance, metrics.budget_bac
        )
        sv_percentage = _calculate_variance_percentage(
            metrics.schedule_variance, metrics.budget_bac
        )

        # Calculate variance severity
        variance_severity = calculate_variance_severity(
            cv_percentage=cv_percentage,
            sv_percentage=sv_percentage,
            thresholds=thresholds,
        )

        # Check if has issues
        has_cost_variance_issue = metrics.cost_variance < 0
        has_schedule_variance_issue = metrics.schedule_variance < 0

        # Count problem areas
        if has_cost_variance_issue or has_schedule_variance_issue:
            total_problem_areas += 1

        # Get cost element type name
        cost_element_type_name = None
        if cost_element.cost_element_type_id:
            cet = cost_element_types.get(cost_element.cost_element_type_id)
            if cet:
                cost_element_type_name = cet.type_name

        # Create row
        row = VarianceAnalysisReportRowPublic(
            cost_element_id=cost_element.cost_element_id,
            wbe_id=wbe.wbe_id,
            wbe_name=wbe.machine_type,
            wbe_serial_number=wbe.serial_number,
            department_code=cost_element.department_code,
            department_name=cost_element.department_name,
            cost_element_type_id=cost_element.cost_element_type_id,
            cost_element_type_name=cost_element_type_name,
            planned_value=metrics.planned_value,
            earned_value=metrics.earned_value,
            actual_cost=metrics.actual_cost,
            budget_bac=metrics.budget_bac,
            cpi=metrics.cpi,
            spi=metrics.spi,
            tcpi=metrics.tcpi,
            cost_variance=metrics.cost_variance,
            schedule_variance=metrics.schedule_variance,
            cv_percentage=cv_percentage,
            sv_percentage=sv_percentage,
            variance_severity=variance_severity,
            has_cost_variance_issue=has_cost_variance_issue,
            has_schedule_variance_issue=has_schedule_variance_issue,
        )
        rows.append(row)

        # Accumulate totals for summary
        total_pv += metrics.planned_value
        total_ev += metrics.earned_value
        total_ac += metrics.actual_cost
        total_bac += metrics.budget_bac

    # Filter to problem areas if requested
    if show_only_problems:
        rows = [
            row
            for row in rows
            if row.has_cost_variance_issue or row.has_schedule_variance_issue
        ]

    # Sort rows by variance (most negative first)
    if sort_by == "cv":
        rows.sort(key=lambda r: r.cost_variance)
    elif sort_by == "sv":
        rows.sort(key=lambda r: r.schedule_variance)

    # Calculate project summary indices
    from app.services.evm_indices import (
        calculate_cost_variance,
        calculate_cpi,
        calculate_schedule_variance,
        calculate_spi,
        calculate_tcpi,
    )

    summary_cpi = calculate_cpi(total_ev, total_ac)
    summary_spi = calculate_spi(total_ev, total_pv)
    summary_tcpi = calculate_tcpi(total_bac, total_ev, total_ac)
    summary_cv = calculate_cost_variance(total_ev, total_ac)
    summary_sv = calculate_schedule_variance(total_ev, total_pv)

    summary = EVMIndicesProjectPublic(
        level="project",
        control_date=control_date,
        project_id=project.project_id,
        planned_value=total_pv,
        earned_value=total_ev,
        actual_cost=total_ac,
        budget_bac=total_bac,
        cpi=summary_cpi,
        spi=summary_spi,
        tcpi=summary_tcpi,
        cost_variance=summary_cv,
        schedule_variance=summary_sv,
    )

    return VarianceAnalysisReportPublic(
        project_id=project.project_id,
        project_name=project.project_name,
        control_date=control_date,
        rows=rows,
        summary=summary,
        total_problem_areas=total_problem_areas,
        config_used={k: str(v) for k, v in thresholds.items()},
    )


def _generate_monthly_dates(start_date: date, end_date: date) -> list[date]:
    """Generate list of first-of-month dates from start_date to end_date (monthly granularity)."""
    dates = []
    current_date = start_date.replace(day=1)  # First day of start month

    while current_date <= end_date:
        dates.append(current_date)
        # Move to first day of next month
        if current_date.month == 12:
            current_date = current_date.replace(
                year=current_date.year + 1, month=1, day=1
            )
        else:
            current_date = current_date.replace(month=current_date.month + 1, day=1)

    # Ensure end_date month is included if not already
    end_month_start = end_date.replace(day=1)
    if dates and dates[-1] < end_month_start:
        dates.append(end_month_start)

    return dates


def get_variance_trend(
    session: Session,
    project_id: uuid.UUID,
    control_date: date,
    cost_element_id: uuid.UUID | None = None,
    wbe_id: uuid.UUID | None = None,
) -> VarianceTrendPublic:
    """Get variance trend analysis showing monthly variance evolution over time.

    Args:
        session: Database session
        project_id: Project ID
        control_date: Current control date (trend ends at this date)
        cost_element_id: Optional cost element ID for cost element level trend
        wbe_id: Optional WBE ID for WBE level trend (cannot be used with cost_element_id)

    Returns:
        VarianceTrendPublic with monthly variance trend points from project start to control date
    """
    # Get project
    project = session.get(Project, project_id)
    if not project:
        raise ValueError(f"Project {project_id} not found")

    # Validate that cost_element_id and wbe_id are not both provided
    if cost_element_id is not None and wbe_id is not None:
        raise ValueError("Cannot provide both cost_element_id and wbe_id")

    # Generate monthly dates from project start_date to control_date
    monthly_dates = _generate_monthly_dates(project.start_date, control_date)

    if not monthly_dates:
        # No months to analyze
        return VarianceTrendPublic(
            project_id=project.project_id,
            cost_element_id=cost_element_id,
            wbe_id=wbe_id,
            control_date=control_date,
            trend_points=[],
        )

    trend_points = []

    # For each month, calculate CV and SV as of that month's end
    for month_start in monthly_dates:
        # Calculate month end date (last day of the month)
        if month_start.month == 12:
            month_end = month_start.replace(
                year=month_start.year + 1, month=1, day=1
            ) - timedelta(days=1)
        else:
            month_end = month_start.replace(
                month=month_start.month + 1, day=1
            ) - timedelta(days=1)

        # Use month_end as control date, but don't exceed current control_date
        month_control_date = min(month_end, control_date)

        # Calculate EVM metrics as of this month's end
        if cost_element_id is not None:
            # Cost element level: calculate for single cost element
            cost_element = session.get(CostElement, cost_element_id)
            if not cost_element:
                continue

            # Get EVM metrics for this cost element
            schedule_map = _get_schedule_map(
                session, [cost_element_id], month_control_date
            )
            entry_map = _get_entry_map(session, [cost_element_id], month_control_date)

            statement = select(CostRegistration).where(
                CostRegistration.cost_element_id == cost_element_id,
            )
            statement = apply_time_machine_filters(
                statement, TimeMachineEventType.COST_REGISTRATION, month_control_date
            )
            cost_registrations = session.exec(statement).all()

            metrics = get_cost_element_evm_metrics(
                cost_element=cost_element,
                schedule=schedule_map.get(cost_element_id),
                entry=entry_map.get(cost_element_id),
                cost_registrations=list(cost_registrations),
                control_date=month_control_date,
            )

            total_cv = metrics.cost_variance
            total_sv = metrics.schedule_variance
            total_bac = metrics.budget_bac

        elif wbe_id is not None:
            # WBE level: aggregate all cost elements in WBE
            wbe = session.get(WBE, wbe_id)
            if not wbe or wbe.project_id != project_id:
                continue

            cost_elements_in_wbe = session.exec(
                select(CostElement).where(CostElement.wbe_id == wbe_id)
            ).all()

            if not cost_elements_in_wbe:
                continue

            cost_element_ids = [ce.cost_element_id for ce in cost_elements_in_wbe]
            schedule_map = _get_schedule_map(
                session, cost_element_ids, month_control_date
            )
            entry_map = _get_entry_map(session, cost_element_ids, month_control_date)

            statement = select(CostRegistration).where(
                CostRegistration.cost_element_id.in_(cost_element_ids),
            )
            statement = apply_time_machine_filters(
                statement, TimeMachineEventType.COST_REGISTRATION, month_control_date
            )
            all_cost_registrations = session.exec(statement).all()

            cost_registrations_by_ce: dict = {}
            for cr in all_cost_registrations:
                if cr.cost_element_id not in cost_registrations_by_ce:
                    cost_registrations_by_ce[cr.cost_element_id] = []
                cost_registrations_by_ce[cr.cost_element_id].append(cr)

            total_cv = Decimal("0.00")
            total_sv = Decimal("0.00")
            total_bac = Decimal("0.00")

            for cost_element in cost_elements_in_wbe:
                metrics = get_cost_element_evm_metrics(
                    cost_element=cost_element,
                    schedule=schedule_map.get(cost_element.cost_element_id),
                    entry=entry_map.get(cost_element.cost_element_id),
                    cost_registrations=cost_registrations_by_ce.get(
                        cost_element.cost_element_id, []
                    ),
                    control_date=month_control_date,
                )

                total_cv += metrics.cost_variance
                total_sv += metrics.schedule_variance
                total_bac += metrics.budget_bac
        else:
            # Project level: aggregate all cost elements in project
            cutoff = end_of_day(month_control_date)
            cost_elements = session.exec(
                select(CostElement)
                .join(WBE)
                .where(
                    WBE.project_id == project_id,
                    CostElement.created_at <= cutoff,
                )
            ).all()

            if not cost_elements:
                continue

            cost_element_ids = [ce.cost_element_id for ce in cost_elements]
            schedule_map = _get_schedule_map(
                session, cost_element_ids, month_control_date
            )
            entry_map = _get_entry_map(session, cost_element_ids, month_control_date)

            statement = select(CostRegistration).where(
                CostRegistration.cost_element_id.in_(cost_element_ids),
            )
            statement = apply_time_machine_filters(
                statement, TimeMachineEventType.COST_REGISTRATION, month_control_date
            )
            all_cost_registrations = session.exec(statement).all()

            cost_registrations_by_ce: dict = {}
            for cr in all_cost_registrations:
                if cr.cost_element_id not in cost_registrations_by_ce:
                    cost_registrations_by_ce[cr.cost_element_id] = []
                cost_registrations_by_ce[cr.cost_element_id].append(cr)

            total_cv = Decimal("0.00")
            total_sv = Decimal("0.00")
            total_bac = Decimal("0.00")

            for cost_element in cost_elements:
                metrics = get_cost_element_evm_metrics(
                    cost_element=cost_element,
                    schedule=schedule_map.get(cost_element.cost_element_id),
                    entry=entry_map.get(cost_element.cost_element_id),
                    cost_registrations=cost_registrations_by_ce.get(
                        cost_element.cost_element_id, []
                    ),
                    control_date=month_control_date,
                )

                total_cv += metrics.cost_variance
                total_sv += metrics.schedule_variance
                total_bac += metrics.budget_bac

        # Calculate variance percentages
        cv_percentage = _calculate_variance_percentage(total_cv, total_bac)
        sv_percentage = _calculate_variance_percentage(total_sv, total_bac)

        # Create trend point
        trend_point = VarianceTrendPointPublic(
            month=month_start,
            cost_variance=total_cv,
            schedule_variance=total_sv,
            cv_percentage=cv_percentage,
            sv_percentage=sv_percentage,
        )
        trend_points.append(trend_point)

    return VarianceTrendPublic(
        project_id=project.project_id,
        cost_element_id=cost_element_id,
        wbe_id=wbe_id,
        control_date=control_date,
        trend_points=trend_points,
    )
