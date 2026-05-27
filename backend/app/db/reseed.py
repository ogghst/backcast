"""Database reseed CLI script.

Truncates all data tables and re-seeds from JSON seed files.

Usage:
    python -m app.db.reseed          # With confirmation prompt
    python -m app.db.reseed --yes    # Skip confirmation
"""

import argparse
import asyncio
import json
import logging
from collections.abc import Callable, Coroutine
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.seed_context import seed_operation
from app.db.session import async_session_maker, engine

logger = logging.getLogger(__name__)

SEED_DIR = Path(__file__).resolve().parent.parent.parent / "seed"

# Tables to truncate in reverse dependency order (dependents first).
# CASCADE handles FK constraints; RESTART IDENTITY resets sequences.
# alembic_version is intentionally excluded.
TABLES_TO_TRUNCATE: list[str] = [
    # AI execution history
    "ai_agent_executions",
    "ai_conversation_attachments",
    "ai_conversation_messages",
    "ai_conversation_sessions",
    # Notifications and quality
    "notifications",
    # Project data (leaf tables first)
    "cost_registrations",
    "progress_entries",
    "cost_elements",
    "forecasts",
    "schedule_baselines",
    "work_packages",
    "control_accounts",
    "cost_events",
    "wbs_elements",
    # Change orders
    "change_order_audit_log",
    "change_orders",
    # Branches
    "branches",
    # Projects
    "projects",
    "project_budget_settings",
    # User-related and AI config
    "user_role_assignments",
    "ai_assistant_configs",
    "ai_models",
    "ai_provider_configs",
    "ai_providers",
    # Reference data
    "cost_element_types",
    "cost_event_types",
    "organizational_units",
    # App config
    "dashboard_layouts",
    "mcp_servers",
    # Change order config
    "co_workflow_config",
    "co_config_audit_log",
    "co_approval_rule_config",
    "co_impact_level_config",
    "co_sla_rule_config",
    # Auth
    "refresh_tokens",
    "users",
    # RBAC (last, referenced by user_role_assignments)
    "rbac_role_permissions",
    "rbac_roles",
]


async def truncate_all_tables() -> None:
    """Truncate all data tables with CASCADE and RESTART IDENTITY."""
    table_list = ", ".join(TABLES_TO_TRUNCATE)
    stmt = text(f"TRUNCATE TABLE {table_list} RESTART IDENTITY CASCADE")
    async with engine.begin() as conn:
        await conn.execute(stmt)
    logger.info("Truncated %d tables", len(TABLES_TO_TRUNCATE))


def _load_json(filename: str) -> Any:
    """Load a JSON file from the seed directory."""
    path = SEED_DIR / filename
    with open(path) as f:
        return json.load(f)


def _parse_datetimes(data: dict[str, Any], fields: list[str]) -> dict[str, Any]:
    """Convert string datetime fields to actual datetime objects in place."""
    for field in fields:
        if field in data and isinstance(data[field], str):
            data[field] = datetime.fromisoformat(data[field])
    return data


async def _seed_organizational_units(session: AsyncSession) -> None:
    """Seed organizational units from JSON."""
    from app.services.organizational_unit_service import OrganizationalUnitService

    data = _load_json("organizational_units.json")
    service = OrganizationalUnitService(session)

    for unit_data in data:
        actor_id = UUID(
            unit_data.pop("created_by", "00000000-0000-0000-0000-000000000001")
        )
        root_id = UUID(unit_data.pop("organizational_unit_id"))
        # Convert parent_unit_id string to UUID or None
        parent_unit_id = unit_data.pop("parent_unit_id", None)
        if parent_unit_id is not None:
            unit_data["parent_unit_id"] = UUID(parent_unit_id)
        # Convert manager_id string to UUID or None
        manager_id = unit_data.pop("manager_id", None)
        if manager_id is not None:
            unit_data["manager_id"] = UUID(manager_id)

        await service.create_root(
            root_id=root_id,
            actor_id=actor_id,
            branch="main",
            **unit_data,
        )
    logger.info("Seeded %d organizational units", len(data))


async def _seed_cost_element_types(session: AsyncSession) -> None:
    """Seed cost element types from JSON."""
    from app.models.schemas.cost_element_type import CostElementTypeCreate
    from app.services.cost_element_type_service import CostElementTypeService

    data = _load_json("cost_element_types.json")
    service = CostElementTypeService(session)

    for type_data in data:
        actor_id = UUID("00000000-0000-0000-0000-000000000001")
        create_schema = CostElementTypeCreate(**type_data)
        await service.create(type_in=create_schema, actor_id=actor_id)
    logger.info("Seeded %d cost element types", len(data))


async def _seed_cost_event_types(session: AsyncSession) -> None:
    """Seed cost event types from JSON."""
    from app.models.schemas.cost_event_type import CostEventTypeCreate
    from app.services.cost_event_type_service import CostEventTypeService

    data = _load_json("cost_event_types.json")
    service = CostEventTypeService(session)

    for type_data in data:
        actor_id = UUID("00000000-0000-0000-0000-000000000001")
        create_schema = CostEventTypeCreate(**type_data)
        await service.create(type_in=create_schema, actor_id=actor_id)
    logger.info("Seeded %d cost event types", len(data))


async def _seed_demo_project(session: AsyncSession) -> None:
    """Seed the full demo project from JSON, respecting dependency order."""
    from app.models.schemas.cost_element import CostElementCreate
    from app.models.schemas.cost_event import CostEventCreate
    from app.models.schemas.cost_registration import CostRegistrationCreate
    from app.models.schemas.forecast import ForecastCreate
    from app.models.schemas.project import ProjectCreate
    from app.models.schemas.work_package import WorkPackageCreate
    from app.services.control_account_service import ControlAccountService
    from app.services.cost_element_service import CostElementService
    from app.services.cost_event_service import CostEventService
    from app.services.cost_registration_service import CostRegistrationService
    from app.services.forecast_service import ForecastService
    from app.services.progress_entry_service import ProgressEntryService
    from app.services.project import ProjectService
    from app.services.schedule_baseline_service import ScheduleBaselineService
    from app.services.wbs_element_service import WBSElementService
    from app.services.work_package_service import WorkPackageService

    demo = _load_json("demo_project.json")
    actor_id = UUID(demo["_created_by"])
    dependency_order = demo["_dependency_order"]

    # Pre-extract WP-to-SB and WP-to-FC mappings before dicts get mutated.
    # Work packages have schedule_baseline_id and forecast_id that are set
    # via UpdateCommand after creation (not through the Create schema).
    wp_sb_map: dict[str, str | None] = {}
    wp_fc_map: dict[str, str | None] = {}
    wp_branch_map: dict[str, str] = {}
    for wp in demo["work_packages"]:
        wp_id = wp["work_package_id"]
        wp_sb_map[wp_id] = wp.get("schedule_baseline_id")
        wp_fc_map[wp_id] = wp.get("forecast_id")
        wp_branch_map[wp_id] = wp.get("branch", "main")

    # Map entity type keys to their seed functions
    seed_map: dict[str, Callable[[], Coroutine[Any, Any, None]]] = {}

    async def seed_project() -> None:
        project_data = demo["project"]
        # Remove fields not in ProjectCreate schema
        project_data.pop("id", None)
        project_data.pop("parent_id", None)
        project_data.pop("merge_from_branch", None)
        project_data.pop("deleted_at", None)
        project_data.pop("deleted_by", None)
        created_by = project_data.pop("created_by")
        service = ProjectService(session)
        schema = ProjectCreate(**project_data)
        await service.create_project(schema, actor_id=UUID(created_by))
        logger.info("Seeded project: %s", project_data.get("name"))

    async def seed_wbs_elements() -> None:
        items = demo["wbs_elements"]
        service = WBSElementService(session)
        count = 0
        for item in items:
            root_id = UUID(item.pop("wbs_element_id"))
            item.pop("id", None)
            created_by = item.pop("created_by")
            item.pop("parent_id", None)
            item.pop("merge_from_branch", None)
            item.pop("deleted_at", None)
            item.pop("deleted_by", None)
            branch = item.pop("branch", "main")
            # Use create_root directly to bypass revenue allocation validation
            # (seed data intentionally has allocations on parent + child WBS)
            await service.create_root(
                root_id=root_id,
                actor_id=UUID(created_by),
                branch=branch,
                **item,
            )
            count += 1
        logger.info("Seeded %d WBS elements", count)

    async def seed_control_accounts() -> None:
        items = demo["control_accounts"]
        service = ControlAccountService(session)
        count = 0
        for item in items:
            root_id = UUID(item.pop("control_account_id"))
            item.pop("id", None)
            created_by = item.pop("created_by")
            item.pop("parent_id", None)
            item.pop("merge_from_branch", None)
            item.pop("deleted_at", None)
            item.pop("deleted_by", None)
            branch = item.pop("branch", "main")
            await service.create_root(
                root_id=root_id,
                actor_id=UUID(created_by),
                branch=branch,
                **item,
            )
            count += 1
        logger.info("Seeded %d control accounts", count)

    async def seed_work_packages() -> None:
        items = demo["work_packages"]
        service = WorkPackageService(session)
        count = 0
        for item in items:
            # Remove fields not in WorkPackageCreate schema
            item.pop("id", None)
            created_by = item.pop("created_by")
            item.pop("parent_id", None)
            item.pop("merge_from_branch", None)
            item.pop("deleted_at", None)
            item.pop("deleted_by", None)
            # schedule_baseline_id and forecast_id are not in WorkPackageCreate;
            # they are linked after creation by schedule_baseline/forecast seeders.
            # Store them in the dict before popping so linkers can find them.
            item.pop("schedule_baseline_id", None)
            item.pop("forecast_id", None)
            schema = WorkPackageCreate(**item)
            await service.create_work_package(schema, actor_id=UUID(created_by))
            count += 1
        logger.info("Seeded %d work packages", count)

    async def seed_cost_elements() -> None:
        items = demo["cost_elements"]
        service = CostElementService(session)
        count = 0
        for item in items:
            item.pop("id", None)
            created_by = item.pop("created_by")
            item.pop("deleted_at", None)
            item.pop("deleted_by", None)
            schema = CostElementCreate(**item)
            await service.create_cost_element(schema, actor_id=UUID(created_by))
            count += 1
        logger.info("Seeded %d cost elements", count)

    async def seed_schedule_baselines() -> None:
        items = demo["schedule_baselines"]
        service = ScheduleBaselineService(session)
        count = 0
        for item in items:
            root_id = UUID(item.pop("schedule_baseline_id"))
            item.pop("id", None)
            created_by = item.pop("created_by")
            item.pop("parent_id", None)
            item.pop("merge_from_branch", None)
            item.pop("deleted_at", None)
            item.pop("deleted_by", None)
            branch = item.pop("branch", "main")
            _parse_datetimes(item, ["start_date", "end_date"])
            await service.create_root(
                root_id=root_id,
                actor_id=UUID(created_by),
                branch=branch,
                **item,
            )
            count += 1
        logger.info("Seeded %d schedule baselines", count)

        # Link work packages to their schedule baselines
        from app.core.branching.commands import UpdateCommand
        from app.models.domain.work_package import WorkPackage

        linked = 0
        for wp_id_str, sb_id_str in wp_sb_map.items():
            if sb_id_str is not None:
                cmd = UpdateCommand(
                    entity_class=WorkPackage,
                    root_id=UUID(wp_id_str),
                    actor_id=actor_id,
                    branch=wp_branch_map[wp_id_str],
                    updates={"schedule_baseline_id": UUID(sb_id_str)},
                )
                await cmd.execute(session)
                linked += 1
        if linked:
            logger.info("Linked %d work packages to schedule baselines", linked)

    async def seed_forecasts() -> None:
        items = demo["forecasts"]
        service = ForecastService(session)
        count = 0
        for item in items:
            item.pop("id", None)
            created_by = item.pop("created_by")
            item.pop("parent_id", None)
            item.pop("merge_from_branch", None)
            item.pop("deleted_at", None)
            item.pop("deleted_by", None)
            schema = ForecastCreate(**item)
            await service.create_forecast(schema, actor_id=UUID(created_by))
            count += 1
        logger.info("Seeded %d forecasts", count)

        # Link work packages to their forecasts
        from app.core.branching.commands import UpdateCommand
        from app.models.domain.work_package import WorkPackage

        linked = 0
        for wp_id_str, fc_id_str in wp_fc_map.items():
            if fc_id_str is not None:
                cmd = UpdateCommand(
                    entity_class=WorkPackage,
                    root_id=UUID(wp_id_str),
                    actor_id=actor_id,
                    branch=wp_branch_map[wp_id_str],
                    updates={"forecast_id": UUID(fc_id_str)},
                )
                await cmd.execute(session)
                linked += 1
        if linked:
            logger.info("Linked %d work packages to forecasts", linked)

    async def seed_progress_entries() -> None:
        from decimal import Decimal

        items = demo["progress_entries"]
        service = ProgressEntryService(session)
        count = 0
        for item in items:
            root_id = UUID(item.pop("progress_entry_id"))
            item.pop("id", None)
            created_by = item.pop("created_by")
            item.pop("deleted_at", None)
            item.pop("deleted_by", None)
            # Convert progress_percentage from string to Decimal
            if "progress_percentage" in item and isinstance(
                item["progress_percentage"], str
            ):
                item["progress_percentage"] = Decimal(item["progress_percentage"])
            await service.create(
                actor_id=UUID(created_by),
                root_id=root_id,
                progress_in=None,
                **item,
            )
            count += 1
        logger.info("Seeded %d progress entries", count)

    async def seed_cost_events() -> None:
        items = demo["cost_events"]
        service = CostEventService(session)
        count = 0
        for item in items:
            item.pop("id", None)
            created_by = item.pop("created_by")
            item.pop("deleted_at", None)
            item.pop("deleted_by", None)
            schema = CostEventCreate(**item)
            await service.create_cost_event(schema, actor_id=UUID(created_by))
            count += 1
        logger.info("Seeded %d cost events", count)

    async def seed_cost_registrations() -> None:
        items = demo["cost_registrations"]
        service = CostRegistrationService(session)
        count = 0
        for item in items:
            item.pop("id", None)
            created_by = item.pop("created_by")
            item.pop("deleted_at", None)
            item.pop("deleted_by", None)
            schema = CostRegistrationCreate(**item)
            await service.create_cost_registration(schema, actor_id=UUID(created_by))
            count += 1
        logger.info("Seeded %d cost registrations", count)

    seed_map = {
        "project": seed_project,
        "wbs_elements": seed_wbs_elements,
        "control_accounts": seed_control_accounts,
        "work_packages": seed_work_packages,
        "cost_elements": seed_cost_elements,
        "schedule_baselines": seed_schedule_baselines,
        "forecasts": seed_forecasts,
        "progress_entries": seed_progress_entries,
        "cost_events": seed_cost_events,
        "cost_registrations": seed_cost_registrations,
    }

    # Seed in dependency order
    for entity_type in dependency_order:
        seed_fn = seed_map.get(entity_type)
        if seed_fn is None:
            logger.warning("Unknown entity type in dependency order: %s", entity_type)
            continue
        print(f"  Seeding {entity_type}...")
        await seed_fn()


async def reseed(skip_confirm: bool = False) -> None:
    """Run the full reseed: truncate then seed_all.

    Args:
        skip_confirm: If True, skip the y/N confirmation prompt.
    """
    if not skip_confirm:
        print("This will DELETE ALL DATA and re-seed from JSON files.")
        answer = input("Continue? [y/N] ").strip().lower()
        if answer not in ("y", "yes"):
            print("Aborted.")
            return

    print("Truncating all data tables...")
    await truncate_all_tables()
    print(f"Truncated {len(TABLES_TO_TRUNCATE)} tables.")

    print("Seeding database from JSON files...")
    async with async_session_maker() as session:
        with seed_operation():
            print("  Seeding users and RBAC...")
            from app.db.seed_users_rbac import seed_users_and_rbac

            await seed_users_and_rbac(session)

            print("  Seeding organizational units...")
            await _seed_organizational_units(session)

            print("  Seeding cost element types...")
            await _seed_cost_element_types(session)

            print("  Seeding cost event types...")
            await _seed_cost_event_types(session)

            print("  Seeding demo project...")
            await _seed_demo_project(session)

            await session.commit()

    print("Reseed complete.")
    await engine.dispose()


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Truncate all data tables and re-seed from JSON files."
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip confirmation prompt.",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    asyncio.run(reseed(skip_confirm=args.yes))


if __name__ == "__main__":
    main()
