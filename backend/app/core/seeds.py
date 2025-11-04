"""Seed functions for initializing database with reference data."""
import json
import uuid
from datetime import date
from pathlib import Path

from sqlmodel import Session, select

from app.core.config import settings
from app.models import (
    WBE,
    BudgetAllocation,
    BudgetAllocationCreate,
    CostElement,
    CostElementCreate,
    CostElementSchedule,
    CostElementScheduleCreate,
    CostElementType,
    CostElementTypeCreate,
    CostRegistration,
    Department,
    DepartmentCreate,
    Project,
    ProjectCreate,
    User,
    WBECreate,
)


def _seed_cost_element_types(session: Session) -> None:
    """Seed cost element types from JSON file if not already present."""
    # Load seed data from JSON file
    seed_file = Path(__file__).parent / "cost_element_types_seed.json"
    if not seed_file.exists():
        return  # No seed file, skip seeding

    with open(seed_file, encoding="utf-8") as f:
        seed_data = json.load(f)

    # Seed each cost element type if it doesn't already exist
    for item in seed_data:
        # Get cost_element_type_id and department_code from item (not part of CostElementTypeCreate)
        cost_element_type_id_str = item.get("cost_element_type_id")
        department_code = item.get("department_code")

        # Check if exists by cost_element_type_id first (if provided), otherwise by type_code
        existing = None
        if cost_element_type_id_str:
            try:
                cost_element_type_id = uuid.UUID(cost_element_type_id_str)
                existing = session.get(CostElementType, cost_element_type_id)
            except ValueError:
                pass  # Invalid UUID, fall back to type_code check

        if not existing:
            existing = session.exec(
                select(CostElementType).where(
                    CostElementType.type_code == item["type_code"]
                )
            ).first()

        if not existing:
            # Create new cost element type
            cet_data = {
                k: v
                for k, v in item.items()
                if k not in ["department_code", "cost_element_type_id"]
            }
            cet_in = CostElementTypeCreate(**cet_data)
            cet = CostElementType.model_validate(cet_in)

            # Set hardcoded cost_element_type_id if provided
            if cost_element_type_id_str:
                try:
                    cet.cost_element_type_id = uuid.UUID(cost_element_type_id_str)
                except ValueError:
                    pass  # Invalid UUID, use auto-generated one

            # Look up department by code and assign department_id
            if department_code:
                department = session.exec(
                    select(Department).where(
                        Department.department_code == department_code
                    )
                ).first()
                if department:
                    cet.department_id = department.department_id

            session.add(cet)
        elif existing and department_code and not existing.department_id:
            # Update existing cost element type if it doesn't have a department_id
            # Look up department by code and assign department_id
            department = session.exec(
                select(Department).where(Department.department_code == department_code)
            ).first()
            if department:
                existing.department_id = department.department_id
                session.add(existing)

    session.commit()


def _seed_departments(session: Session) -> None:
    """Seed departments from JSON file if not already present."""
    # Load seed data from JSON file
    seed_file = Path(__file__).parent / "departments_seed.json"
    if not seed_file.exists():
        return  # No seed file, skip seeding

    with open(seed_file, encoding="utf-8") as f:
        seed_data = json.load(f)

    # Seed each department if it doesn't already exist
    for item in seed_data:
        existing = session.exec(
            select(Department).where(
                Department.department_code == item["department_code"]
            )
        ).first()
        if not existing:
            dept_in = DepartmentCreate(**item)
            dept = Department.model_validate(dept_in)
            session.add(dept)

    session.commit()


def _seed_project_from_template(session: Session) -> None:
    """Seed project from JSON template file if not already present."""
    # Load seed data from JSON file
    seed_file = Path(__file__).parent / "project_template_seed.json"
    if not seed_file.exists():
        return  # No seed file, skip seeding

    with open(seed_file, encoding="utf-8") as f:
        template_data = json.load(f)

    # Get first superuser for project_manager_id
    first_superuser = session.exec(
        select(User).where(User.email == settings.FIRST_SUPERUSER)
    ).first()
    if not first_superuser:
        return  # Cannot seed project without first superuser

    project_data = template_data["project"]
    project_code = project_data.get("project_code")

    if not project_code:
        return  # Cannot seed project without project_code

    # Check if project already exists
    existing_project = session.exec(
        select(Project).where(Project.project_code == project_code)
    ).first()

    # Resolve project_manager_id placeholder
    project_manager_id_str = project_data.get("project_manager_id", "")
    if (
        project_manager_id_str == "REPLACE_WITH_VALID_USER_UUID"
        or not project_manager_id_str
    ):
        project_manager_id = first_superuser.id
    else:
        try:
            project_manager_id = uuid.UUID(project_manager_id_str)
        except ValueError:
            project_manager_id = first_superuser.id

    if existing_project:
        # Update existing project
        project_data_for_update = dict(project_data.items())
        project_data_for_update["project_manager_id"] = project_manager_id
        for key, value in project_data_for_update.items():
            if hasattr(existing_project, key):
                setattr(existing_project, key, value)
        session.add(existing_project)
        session.flush()
        project = existing_project
    else:
        # Create new project
        project_data["project_manager_id"] = project_manager_id
        project_create = ProjectCreate(**project_data)
        project = Project.model_validate(project_create)
        session.add(project)
        session.flush()  # Get project_id without committing

    # Clear existing WBEs if updating (user requested update behavior)
    if existing_project:
        existing_wbes = session.exec(
            select(WBE).where(WBE.project_id == project.project_id)
        ).all()
        for wbe in existing_wbes:
            # Delete associated cost elements first
            existing_cost_elements = session.exec(
                select(CostElement).where(CostElement.wbe_id == wbe.wbe_id)
            ).all()
            for ce in existing_cost_elements:
                # Delete associated budget allocations first (to avoid foreign key violation)
                existing_budget_allocations = session.exec(
                    select(BudgetAllocation).where(
                        BudgetAllocation.cost_element_id == ce.cost_element_id
                    )
                ).all()
                for budget_allocation in existing_budget_allocations:
                    session.delete(budget_allocation)
                # Delete associated cost element schedules (to avoid foreign key violation)
                existing_schedules = session.exec(
                    select(CostElementSchedule).where(
                        CostElementSchedule.cost_element_id == ce.cost_element_id
                    )
                ).all()
                for schedule in existing_schedules:
                    session.delete(schedule)
                # Delete associated cost registrations (to avoid foreign key violation)
                existing_cost_registrations = session.exec(
                    select(CostRegistration).where(
                        CostRegistration.cost_element_id == ce.cost_element_id
                    )
                ).all()
                for cost_registration in existing_cost_registrations:
                    session.delete(cost_registration)
                session.delete(ce)
            session.delete(wbe)
        session.flush()

    # Create WBEs and cost elements
    for wbe_item in template_data.get("wbes", []):
        wbe_data = wbe_item["wbe"].copy()
        wbe_data["project_id"] = project.project_id
        wbe_create = WBECreate(**wbe_data)
        wbe = WBE.model_validate(wbe_create)
        session.add(wbe)
        session.flush()  # Get wbe_id without committing

        # Create cost elements for this WBE
        for ce_data in wbe_item.get("cost_elements", []):
            # Validate cost_element_type_id exists
            cost_element_type_id_str = ce_data.get("cost_element_type_id")
            if not cost_element_type_id_str:
                continue  # Skip if no cost_element_type_id

            try:
                cost_element_type_id = uuid.UUID(cost_element_type_id_str)
            except ValueError:
                continue  # Skip if invalid UUID

            # Verify cost element type exists
            cost_element_type = session.get(CostElementType, cost_element_type_id)
            if not cost_element_type:
                continue  # Skip if cost element type doesn't exist

            ce_data_with_wbe = ce_data.copy()
            ce_data_with_wbe["wbe_id"] = wbe.wbe_id
            ce_data_with_wbe["cost_element_type_id"] = cost_element_type_id
            ce_create = CostElementCreate(**ce_data_with_wbe)
            ce = CostElement.model_validate(ce_create)
            session.add(ce)
            session.flush()  # Get cost_element_id without committing

            # Create initial budget allocation for this cost element
            budget_allocation_data = BudgetAllocationCreate(
                cost_element_id=ce.cost_element_id,
                allocation_date=project.start_date,
                budget_amount=ce.budget_bac,
                revenue_amount=ce.revenue_plan,
                allocation_type="initial",
                description="Initial budget allocation from seed data",
                created_by_id=first_superuser.id,
            )
            budget_allocation = BudgetAllocation.model_validate(budget_allocation_data)
            session.add(budget_allocation)

            # Create schedule for this cost element
            # Use schedule data from JSON if available, otherwise use project dates
            schedule_info = ce_data.get("schedule")
            if schedule_info:
                # Schedule data explicitly provided in JSON
                schedule_start = date.fromisoformat(schedule_info["start_date"])
                schedule_end = date.fromisoformat(schedule_info["end_date"])
                schedule_progression = schedule_info.get("progression_type", "linear")
                schedule_notes = schedule_info.get("notes")
            else:
                # Fallback to project dates (backward compatibility)
                schedule_start = project.start_date
                schedule_end = project.planned_completion_date
                schedule_progression = "linear"
                schedule_notes = "Initial schedule baseline from seed data"

            schedule_data = CostElementScheduleCreate(
                cost_element_id=ce.cost_element_id,
                start_date=schedule_start,
                end_date=schedule_end,
                progression_type=schedule_progression,
                notes=schedule_notes,
                created_by_id=first_superuser.id,
            )
            schedule = CostElementSchedule.model_validate(schedule_data)
            session.add(schedule)

    session.commit()
