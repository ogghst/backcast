"""Cost Performance Report service."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from sqlmodel import Session, select

from app.models import (
    WBE,
    CostElement,
    CostElementSchedule,
    CostElementType,
    CostRegistration,
    EarnedValueEntry,
    Project,
)
from app.models.cost_performance_report import (
    CostPerformanceReportPublic,
    CostPerformanceReportRowPublic,
)
from app.models.evm_indices import EVMIndicesProjectPublic
from app.services.evm_aggregation import get_cost_element_evm_metrics
from app.services.time_machine import (
    TimeMachineEventType,
    apply_time_machine_filters,
    end_of_day,
)


def _get_schedule_map(
    session: Session, cost_element_ids: list[uuid.UUID], control_date: date
) -> dict[uuid.UUID, CostElementSchedule | None]:
    """Get schedule map for cost elements (reused from evm_aggregation)."""
    from app.api.routes.evm_aggregation import _get_schedule_map as get_schedule_map

    return get_schedule_map(session, cost_element_ids, control_date)


def _get_entry_map(
    session: Session, cost_element_ids: list[uuid.UUID], control_date: date
) -> dict[uuid.UUID, EarnedValueEntry | None]:
    """Get earned value entry map for cost elements (reused from evm_aggregation)."""
    from app.api.routes.evm_aggregation import _get_entry_map as get_entry_map

    return get_entry_map(session, cost_element_ids, control_date)


def get_cost_performance_report(
    session: Session, project_id: uuid.UUID, control_date: date
) -> CostPerformanceReportPublic:
    """Get cost performance report for a project.

    Args:
        session: Database session
        project_id: Project ID
        control_date: Control date for time-machine filtering

    Returns:
        CostPerformanceReportPublic with all cost element rows and project summary
    """
    # Get project
    project = session.get(Project, project_id)
    if not project:
        raise ValueError(f"Project {project_id} not found")

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
        return CostPerformanceReportPublic(
            project_id=project.project_id,
            project_name=project.project_name,
            control_date=control_date,
            rows=[],
            summary=summary,
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
    cost_registrations_by_ce: dict[uuid.UUID, list[CostRegistration]] = {}
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

        # Get cost element type name
        cost_element_type_name = None
        if cost_element.cost_element_type_id:
            cet = cost_element_types.get(cost_element.cost_element_type_id)
            if cet:
                cost_element_type_name = cet.type_name

        # Create row
        row = CostPerformanceReportRowPublic(
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
        )
        rows.append(row)

        # Accumulate totals for summary
        total_pv += metrics.planned_value
        total_ev += metrics.earned_value
        total_ac += metrics.actual_cost
        total_bac += metrics.budget_bac

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

    return CostPerformanceReportPublic(
        project_id=project.project_id,
        project_name=project.project_name,
        control_date=control_date,
        rows=rows,
        summary=summary,
    )
