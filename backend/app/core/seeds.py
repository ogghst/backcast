"""Seed functions for initializing database with reference data."""

import json
import uuid
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from sqlmodel import Session, select

from app.core.config import settings
from app.models import (
    WBE,
    AppConfiguration,
    AppConfigurationCreate,
    BaselineCostElement,
    BudgetAllocation,
    BudgetAllocationCreate,
    CostElement,
    CostElementCreate,
    CostElementSchedule,
    CostElementScheduleCreate,
    CostElementType,
    CostElementTypeCreate,
    CostRegistration,
    CostRegistrationCreate,
    Department,
    DepartmentCreate,
    EarnedValueEntry,
    EarnedValueEntryCreate,
    Forecast,
    Project,
    ProjectCreate,
    QualityEvent,
    User,
    VarianceThresholdConfig,
    VarianceThresholdConfigCreate,
    VarianceThresholdType,
    WBECreate,
)


def _parse_iso_datetime(raw_value: str | None) -> datetime | None:
    """Parse ISO-8601 strings (with optional trailing Z) into aware datetimes."""
    if not raw_value:
        return None
    normalized = (
        raw_value.replace("Z", "+00:00") if raw_value.endswith("Z") else raw_value
    )
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def _apply_timestamps(
    instance: object,
    created_at_str: str | None,
    updated_at_str: str | None,
    updated_field: str = "updated_at",
) -> None:
    """Assign created/updated timestamps to SQLModel instances if provided."""
    created_at_value = _parse_iso_datetime(created_at_str)
    if created_at_value is not None and hasattr(instance, "created_at"):
        instance.created_at = created_at_value

    updated_at_value = _parse_iso_datetime(updated_at_str)
    if updated_at_value is not None and hasattr(instance, updated_field):
        setattr(instance, updated_field, updated_at_value)


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
    """Seed projects from JSON template file if not already present."""
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

    # Handle multiple project entries (can be a single project or list of projects)
    projects_data = template_data
    if "project" in template_data and "wbes" in template_data:
        # Single project format
        projects_data = [
            {
                "project": template_data["project"],
                "wbes": template_data["wbes"],
                "earned_value_entries": template_data.get("earned_value_entries", []),
            }
        ]
    elif isinstance(template_data, list):
        # Multiple projects format
        projects_data = template_data
    else:
        # Direct multiple projects format
        projects_data = [template_data]

    # Process each project entry
    for project_entry in projects_data:
        project_data_raw = project_entry.get("project")
        if not project_data_raw:
            continue

        project_data = project_data_raw.copy()
        project_created_at_str = project_data.pop("created_at", None)
        project_updated_at_str = project_data.pop("updated_at", None)
        project_code = project_data.get("project_code")
        if not project_code:
            continue  # Cannot seed project without project_code

        project_data["project_name"] = project_code

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
            project_data_for_update = project_data.copy()
            project_data_for_update["project_manager_id"] = project_manager_id
            for key, value in project_data_for_update.items():
                if hasattr(existing_project, key):
                    setattr(existing_project, key, value)
            session.add(existing_project)
            session.flush()
            project = existing_project
            _apply_timestamps(
                project,
                created_at_str=project_created_at_str,
                updated_at_str=project_updated_at_str,
            )
        else:
            # Create new project
            project_data["project_manager_id"] = project_manager_id
            project_create = ProjectCreate(**project_data)
            project = Project.model_validate(project_create)
            _apply_timestamps(
                project,
                created_at_str=project_created_at_str,
                updated_at_str=project_updated_at_str,
            )
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
                    # Delete associated baseline cost elements first (to avoid foreign key violation)
                    existing_baseline_cost_elements = session.exec(
                        select(BaselineCostElement).where(
                            BaselineCostElement.cost_element_id == ce.cost_element_id
                        )
                    ).all()
                    for baseline_cost_element in existing_baseline_cost_elements:
                        session.delete(baseline_cost_element)
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
                    # Delete associated earned value entries (to avoid foreign key violation)
                    existing_earned_value_entries = session.exec(
                        select(EarnedValueEntry).where(
                            EarnedValueEntry.cost_element_id == ce.cost_element_id
                        )
                    ).all()
                    for earned_value_entry in existing_earned_value_entries:
                        session.delete(earned_value_entry)
                    # Delete associated forecasts (to avoid foreign key violation)
                    existing_forecasts = session.exec(
                        select(Forecast).where(
                            Forecast.cost_element_id == ce.cost_element_id
                        )
                    ).all()
                    for forecast in existing_forecasts:
                        session.delete(forecast)
                    # Delete associated quality events (to avoid foreign key violation)
                    existing_quality_events = session.exec(
                        select(QualityEvent).where(
                            QualityEvent.cost_element_id == ce.cost_element_id
                        )
                    ).all()
                    for quality_event in existing_quality_events:
                        session.delete(quality_event)
                    session.delete(ce)
                session.delete(wbe)
            session.flush()

        # Process earned value entries that are shared across the project
        earned_value_entries_by_type: dict[str, list[dict]] = {}
        for ev_entry in project_entry.get("earned_value_entries", []):
            cost_element_ref = ev_entry.get("cost_element_ref") or ev_entry.get(
                "cost_element_id"
            )
            if cost_element_ref:
                earned_value_entries_by_type.setdefault(cost_element_ref, []).append(
                    ev_entry
                )

        # Create WBEs and cost elements
        for wbe_item in project_entry.get("wbes", []):
            wbe_data = wbe_item["wbe"].copy()
            wbe_created_at_str = wbe_data.pop("created_at", None)
            wbe_updated_at_str = wbe_data.pop("updated_at", None)
            wbe_data["project_id"] = project.project_id
            wbe_create = WBECreate(**wbe_data)
            wbe = WBE.model_validate(wbe_create)
            _apply_timestamps(
                wbe,
                created_at_str=wbe_created_at_str,
                updated_at_str=wbe_updated_at_str,
            )
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
                ce_created_at_str = ce_data_with_wbe.pop("created_at", None)
                ce_updated_at_str = ce_data_with_wbe.pop("updated_at", None)
                ce_data_with_wbe["wbe_id"] = wbe.wbe_id
                ce_data_with_wbe["cost_element_type_id"] = cost_element_type_id
                ce_create = CostElementCreate(**ce_data_with_wbe)
                ce = CostElement.model_validate(ce_create)
                _apply_timestamps(
                    ce,
                    created_at_str=ce_created_at_str,
                    updated_at_str=ce_updated_at_str,
                )
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
                    created_at=project.start_date,
                )
                budget_allocation = BudgetAllocation.model_validate(
                    budget_allocation_data
                )
                session.add(budget_allocation)

                # Create schedule for this cost element
                # Use schedule data from JSON if available, otherwise use project dates
                schedule_info = ce_data.get("schedule", {}).copy()
                schedule_created_at_str = schedule_info.pop("created_at", None)
                schedule_updated_at_str = schedule_info.pop("updated_at", None)
                if schedule_info:
                    # Schedule data explicitly provided in JSON
                    schedule_start = date.fromisoformat(schedule_info["start_date"])
                    schedule_end = date.fromisoformat(schedule_info["end_date"])
                    schedule_progression = schedule_info.get(
                        "progression_type", "linear"
                    )
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
                _apply_timestamps(
                    schedule,
                    created_at_str=schedule_created_at_str,
                    updated_at_str=schedule_updated_at_str,
                )
                session.add(schedule)

                # Create cost registrations if provided in seed data
                cost_registrations_data = ce_data.get("cost_registrations", [])
                for cr_data in cost_registrations_data:
                    # Convert amount to Decimal if it's a float
                    amount = cr_data.get("amount", 0.0)
                    if isinstance(amount, float):
                        amount = Decimal(str(amount))
                    elif isinstance(amount, int | str):
                        amount = Decimal(str(amount))
                    else:
                        amount = Decimal("0.00")

                    cr_created_at_str = cr_data.get("created_at")
                    cr_last_modified_str = cr_data.get("last_modified_at")

                    cost_registration_data = CostRegistrationCreate(
                        cost_element_id=ce.cost_element_id,
                        registration_date=date.fromisoformat(
                            cr_data["registration_date"]
                        ),
                        amount=amount,
                        cost_category=cr_data["cost_category"],
                        invoice_number=cr_data.get("invoice_number"),
                        description=cr_data["description"],
                        is_quality_cost=cr_data.get("is_quality_cost", False),
                    )
                    # Add created_by_id when creating the model (not in CostRegistrationCreate schema)
                    cr_model_data = cost_registration_data.model_dump()
                    cr_model_data["created_by_id"] = first_superuser.id
                    cost_registration = CostRegistration.model_validate(cr_model_data)
                    _apply_timestamps(
                        cost_registration,
                        created_at_str=cr_created_at_str,
                        updated_at_str=cr_last_modified_str,
                        updated_field="last_modified_at",
                    )
                    session.add(cost_registration)

                # Create earned value entries if provided in seed data
                earned_value_entries_data = ce_data.get("earned_value_entries") or []
                cost_element_type_id_str = ce_data.get("cost_element_type_id")
                if not earned_value_entries_data and cost_element_type_id_str:
                    earned_value_entries_data = earned_value_entries_by_type.get(
                        cost_element_type_id_str, []
                    )

                for ev_data in earned_value_entries_data:
                    ev_created_at_str = ev_data.get("created_at")
                    ev_last_modified_str = ev_data.get("last_modified_at")
                    percent_complete_raw = ev_data.get("percent_complete", 0.0)
                    if isinstance(percent_complete_raw, Decimal):
                        percent_complete = percent_complete_raw
                    elif isinstance(percent_complete_raw, float | int | str):
                        percent_complete = Decimal(str(percent_complete_raw))
                    else:
                        percent_complete = Decimal("0.00")

                    earned_value_raw = ev_data.get("earned_value")
                    if earned_value_raw is None:
                        earned_value_amount = None
                    elif isinstance(earned_value_raw, Decimal):
                        earned_value_amount = earned_value_raw
                    elif isinstance(earned_value_raw, float | int | str):
                        earned_value_amount = Decimal(str(earned_value_raw))
                    else:
                        earned_value_amount = None

                    # Ensure registration_date is a pure date (no time component)
                    reg_date = None
                    if ev_created_at_str:
                        parsed_dt = _parse_iso_datetime(ev_created_at_str)
                        if parsed_dt is not None:
                            reg_date = date(
                                parsed_dt.year, parsed_dt.month, parsed_dt.day
                            )

                    earned_value_entry_data = EarnedValueEntryCreate(
                        cost_element_id=ce.cost_element_id,
                        completion_date=date.fromisoformat(ev_data["completion_date"]),
                        percent_complete=percent_complete,
                        earned_value=earned_value_amount,
                        deliverables=ev_data.get("deliverables"),
                        description=ev_data.get("description"),
                        registration_date=reg_date,
                    )
                    ev_model_data = earned_value_entry_data.model_dump()
                    ev_model_data["created_by_id"] = first_superuser.id
                    earned_value_entry = EarnedValueEntry.model_validate(ev_model_data)
                    _apply_timestamps(
                        earned_value_entry,
                        created_at_str=ev_created_at_str,
                        updated_at_str=ev_last_modified_str,
                        updated_field="last_modified_at",
                    )
                    session.add(earned_value_entry)

    session.commit()


def _seed_variance_threshold_configs(session: Session) -> None:
    """Seed default variance threshold configurations if they don't exist."""
    default_configs = [
        {
            "threshold_type": VarianceThresholdType.critical_cv,
            "threshold_percentage": Decimal("-10.00"),
            "description": "Critical cost variance threshold",
            "is_active": True,
        },
        {
            "threshold_type": VarianceThresholdType.warning_cv,
            "threshold_percentage": Decimal("-5.00"),
            "description": "Warning cost variance threshold",
            "is_active": True,
        },
        {
            "threshold_type": VarianceThresholdType.critical_sv,
            "threshold_percentage": Decimal("-10.00"),
            "description": "Critical schedule variance threshold",
            "is_active": True,
        },
        {
            "threshold_type": VarianceThresholdType.warning_sv,
            "threshold_percentage": Decimal("-5.00"),
            "description": "Warning schedule variance threshold",
            "is_active": True,
        },
    ]

    for config_data in default_configs:
        # Check if active configuration of this type already exists
        existing = session.exec(
            select(VarianceThresholdConfig).where(
                VarianceThresholdConfig.threshold_type == config_data["threshold_type"],
                VarianceThresholdConfig.is_active == True,  # noqa: E712
            )
        ).first()

        if not existing:
            # Create new configuration
            config_in = VarianceThresholdConfigCreate(**config_data)
            config = VarianceThresholdConfig.model_validate(config_in)
            session.add(config)

    session.commit()


def _seed_ai_default_config(session: Session) -> None:
    """Seed default AI configuration entries if they don't exist."""
    # Get base URL from environment variable or use empty string
    default_base_url = settings.AI_DEFAULT_OPENAI_BASE_URL or ""

    default_configs = [
        {
            "config_key": "ai_default_openai_base_url",
            "config_value": default_base_url,
            "description": "Default OpenAI API base URL (e.g., https://api.openai.com/v1)",
            "is_active": True,
        },
        {
            "config_key": "ai_default_openai_api_key_encrypted",
            "config_value": "",  # Empty by default - users must configure
            "description": "Default OpenAI API key (encrypted). Users must configure this.",
            "is_active": True,
        },
        {
            "config_key": "ai_default_openai_model",
            "config_value": "",  # Empty by default - users must configure
            "description": "Default OpenAI model (e.g., gpt-4o-mini, deepseek-chat). Users must configure this.",
            "is_active": True,
        },
    ]

    for config_data in default_configs:
        # Check if configuration with this key already exists
        existing = session.exec(
            select(AppConfiguration).where(
                AppConfiguration.config_key == config_data["config_key"]
            )
        ).first()

        if not existing:
            # Create new configuration
            config_in = AppConfigurationCreate(**config_data)
            config = AppConfiguration.model_validate(config_in)
            session.add(config)

    session.commit()
