"""Database reseed CLI script.

Truncates all data tables and re-seeds from the unified seed_data.json file.

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
SEED_FILE = SEED_DIR / "seed_data.json"

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


def _load_seed_data() -> dict[str, Any]:
    """Load the unified seed_data.json file."""
    with open(SEED_FILE) as f:
        return json.load(f)


def _parse_datetimes(data: dict[str, Any], fields: list[str]) -> dict[str, Any]:
    """Convert string datetime fields to actual datetime objects in place."""
    for field in fields:
        if field in data and isinstance(data[field], str):
            data[field] = datetime.fromisoformat(data[field])
    return data


# ---------------------------------------------------------------------------
# CO Workflow config seeding via direct SQL (matching seed_database.py pattern)
# ---------------------------------------------------------------------------

# Column type sets for type coercion during SQL insertion
_DATETIME_COLS: set[str] = {
    "changed_at",
    "control_date",
    "created_at",
    "updated_at",
    "effective_date",
    "event_date",
    "registration_date",
    "sla_assigned_at",
    "sla_due_date",
    "start_date",
    "end_date",
    "approved_date",
}
_DECIMAL_COLS: set[str] = {
    "amount",
    "contract_value",
    "estimated_impact",
    "escalation_trigger_pct",
    "impact_score",
    "progress_percentage",
    "quantity",
    "revenue_allocation",
    "score_threshold_max",
    "score_threshold_min",
    "threshold_amount",
    "budget_amount",
    "eac_amount",
}
_BOOL_COLS: set[str] = {
    "is_active",
    "is_encrypted",
    "is_quality",
}
_INT_COLS: set[str] = {
    "business_days",
    "level_order",
    "max_tokens",
    "recursion_limit",
    "schedule_impact_days",
    "version",
}
_UUID_COLS: set[str] = {
    "approver_role",  # not UUID, but string
}
_JSONB_COLS: set[str] = {
    "impact_weights",
    "score_boundaries",
    "workflow_transitions",
    "custom_fields",
    "custom_field_values",
    "config_snapshot",
    "impact_analysis_results",
    "delegation_config",
}


def _coerce_value(col: str, value: Any) -> Any:
    """Coerce a JSON value to the correct Python type for SQL insertion."""
    if value is None:
        return None
    if col in _DATETIME_COLS and isinstance(value, str):
        return datetime.fromisoformat(value)
    if col in _DECIMAL_COLS and isinstance(value, str):
        from decimal import Decimal

        return Decimal(value)
    if col in _BOOL_COLS and isinstance(value, str):
        return value.lower() in ("true", "1", "yes")
    if col in _INT_COLS and isinstance(value, str):
        return int(value)
    return value


async def _seed_change_order_workflow(
    session: AsyncSession, workflow_data: dict[str, Any]
) -> None:
    """Seed change order workflow config using direct SQL insertion."""
    from app.models.domain.change_order_config import (
        ChangeOrderApprovalRuleConfig,
        ChangeOrderImpactLevelConfig,
        ChangeOrderSLARuleConfig,
        ChangeOrderWorkflowConfig,
    )

    config_data = workflow_data["config"]

    # Seed main config
    config = ChangeOrderWorkflowConfig(
        id=UUID(config_data["id"]),
        config_id=UUID(config_data["config_id"]),
        project_id=UUID(config_data["project_id"])
        if config_data.get("project_id")
        else None,
        is_active=config_data["is_active"],
        version=config_data.get("version", 1),
        created_by=UUID(config_data["created_by"]),
        updated_by=UUID(config_data["updated_by"])
        if config_data.get("updated_by")
        else None,
        impact_weights=config_data["impact_weights"],
        score_boundaries=config_data["score_boundaries"],
        workflow_transitions=config_data.get("workflow_transitions"),
        holiday_country_code=config_data.get("holiday_country_code"),
        custom_fields=config_data.get("custom_fields"),
    )
    session.add(config)

    # Seed impact levels
    for level_data in workflow_data.get("impact_levels", []):
        level = ChangeOrderImpactLevelConfig(
            id=UUID(level_data["id"]),
            config_id=UUID(level_data["config_id"]),
            level_name=level_data["level_name"],
            level_order=level_data["level_order"],
            threshold_amount=level_data["threshold_amount"],
            score_threshold_min=level_data["score_threshold_min"],
            score_threshold_max=level_data["score_threshold_max"],
            is_active=level_data.get("is_active", True),
        )
        session.add(level)

    # Seed approval rules
    for rule_data in workflow_data.get("approval_rules", []):
        rule = ChangeOrderApprovalRuleConfig(
            id=UUID(rule_data["id"]),
            config_id=UUID(rule_data["config_id"]),
            impact_level_name=rule_data["impact_level_name"],
            required_authority_level=rule_data["required_authority_level"],
            approver_role=rule_data["approver_role"],
        )
        session.add(rule)

    # Seed SLA rules
    for sla_data in workflow_data.get("sla_rules", []):
        sla = ChangeOrderSLARuleConfig(
            id=UUID(sla_data["id"]),
            config_id=UUID(sla_data["config_id"]),
            impact_level_name=sla_data["impact_level_name"],
            business_days=sla_data["business_days"],
            escalation_trigger_pct=sla_data.get("escalation_trigger_pct"),
        )
        session.add(sla)

    await session.flush()
    logger.info("Seeded change order workflow config")


# ---------------------------------------------------------------------------
# Individual seed functions (accept data parameter)
# ---------------------------------------------------------------------------


async def _seed_organizational_units(
    session: AsyncSession, data: list[dict[str, Any]]
) -> None:
    """Seed organizational units from data list."""
    from app.services.organizational_unit_service import OrganizationalUnitService

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
        # Remove fields not accepted by create_root
        unit_data.pop("branch", None)
        unit_data.pop("id", None)

        await service.create_root(
            root_id=root_id,
            actor_id=actor_id,
            branch="main",
            **unit_data,
        )
    logger.info("Seeded %d organizational units", len(data))


async def _seed_cost_element_types(
    session: AsyncSession, data: list[dict[str, Any]]
) -> None:
    """Seed cost element types from data list."""
    from app.models.schemas.cost_element_type import CostElementTypeCreate
    from app.services.cost_element_type_service import CostElementTypeService

    service = CostElementTypeService(session)

    for type_data in data:
        actor_id = UUID("00000000-0000-0000-0000-000000000001")
        create_schema = CostElementTypeCreate(**type_data)
        await service.create(type_in=create_schema, actor_id=actor_id)
    logger.info("Seeded %d cost element types", len(data))


async def _seed_cost_event_types(
    session: AsyncSession, data: list[dict[str, Any]]
) -> None:
    """Seed cost event types from data list."""
    from app.models.schemas.cost_event_type import CostEventTypeCreate
    from app.services.cost_event_type_service import CostEventTypeService

    service = CostEventTypeService(session)

    for type_data in data:
        actor_id = UUID("00000000-0000-0000-0000-000000000001")
        create_schema = CostEventTypeCreate(**type_data)
        await service.create(type_in=create_schema, actor_id=actor_id)
    logger.info("Seeded %d cost event types", len(data))


async def _seed_demo_project(session: AsyncSession, demo: dict[str, Any]) -> None:
    """Seed the full demo project from data dict, respecting dependency order."""
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

    actor_id = UUID(demo["_created_by"])
    dependency_order = demo["_dependency_order"]

    # Pre-extract WP-to-SB and WP-to-FC mappings before dicts get mutated.
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
            item.pop("id", None)
            created_by = item.pop("created_by")
            item.pop("parent_id", None)
            item.pop("merge_from_branch", None)
            item.pop("deleted_at", None)
            item.pop("deleted_by", None)
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

    async def seed_change_orders() -> None:
        items = demo.get("change_orders", [])
        if not items:
            return
        from app.models.domain.change_order import ChangeOrder

        count = 0
        for item in items:
            item.pop("id", None)
            co_id = item["change_order_id"]
            co = ChangeOrder(
                id=UUID(co_id),
                **{k: _coerce_value(k, v) for k, v in item.items()},
            )
            session.add(co)
            count += 1
        await session.flush()
        logger.info("Seeded %d change orders", count)

    async def seed_change_order_audit_logs() -> None:
        items = demo.get("change_order_audit_logs", [])
        if not items:
            return
        from app.models.domain.change_order_audit_log import ChangeOrderAuditLog

        count = 0
        for item in items:
            alog = ChangeOrderAuditLog(
                id=UUID(item.pop("id")),
                **{k: _coerce_value(k, v) for k, v in item.items()},
            )
            session.add(alog)
            count += 1
        await session.flush()
        logger.info("Seeded %d change order audit logs", count)

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
        "change_orders": seed_change_orders,
        "change_order_audit_logs": seed_change_order_audit_logs,
    }

    # Seed in dependency order
    for entity_type in dependency_order:
        seed_fn = seed_map.get(entity_type)
        if seed_fn is None:
            logger.warning("Unknown entity type in dependency order: %s", entity_type)
            continue
        print(f"  Seeding {entity_type}...")
        await seed_fn()


async def _seed_ai_providers(session: AsyncSession, data: list[dict[str, Any]]) -> None:
    """Seed AI providers, their configs, and models from data list."""
    from app.models.domain.ai import AIModel, AIProvider, AIProviderConfig

    with seed_operation():
        provider_count = 0
        config_count = 0
        model_count = 0

        for provider_data in data:
            configs = provider_data.pop("configs", [])
            models = provider_data.pop("models", [])

            provider = AIProvider(
                id=UUID(provider_data.pop("id")),
                **provider_data,
            )
            session.add(provider)
            await session.flush()

            for config_data in configs:
                config = AIProviderConfig(
                    id=UUID(config_data.pop("id")),
                    provider_id=str(provider.id),
                    **config_data,
                )
                session.add(config)
                config_count += 1

            for model_data in models:
                model = AIModel(
                    id=UUID(model_data.pop("id")),
                    provider_id=str(provider.id),
                    **model_data,
                )
                session.add(model)
                model_count += 1

            provider_count += 1
            await session.flush()

    logger.info(
        "Seeded %d AI providers, %d configs, %d models",
        provider_count,
        config_count,
        model_count,
    )


async def _seed_ai_assistant_configs(
    session: AsyncSession, data: list[dict[str, Any]]
) -> None:
    """Seed AI assistant configs (main agents) from data list."""
    from app.models.domain.ai import AIAssistantConfig

    with seed_operation():
        for assistant_data in data:
            assistant_data["model_id"] = str(assistant_data["model_id"])
            assistant = AIAssistantConfig(
                id=UUID(assistant_data.pop("id")),
                **assistant_data,
            )
            session.add(assistant)
            await session.flush()

    logger.info("Seeded %d AI assistant configs", len(data))


async def _seed_mcp_servers(session: AsyncSession, data: list[dict[str, Any]]) -> None:
    """Seed MCP server configurations from data list."""
    from app.models.domain.mcp_server import MCPServer
    from app.services.mcp_server_service import MCPServerService

    service = MCPServerService(session)

    with seed_operation():
        for server_data in data:
            encrypted_config = service.encrypt_config(server_data["config"])
            server = MCPServer(
                name=server_data["name"],
                config=encrypted_config,
                is_active=server_data.get("is_active", True),
            )
            session.add(server)
            await session.flush()

    logger.info("Seeded %d MCP servers", len(data))


async def _seed_ai_specialist_configs(
    session: AsyncSession, data: list[dict[str, Any]]
) -> None:
    """Seed AI specialist configs from data list (idempotent by name)."""
    from sqlalchemy import select as sql_select

    from app.models.domain.ai import AIAssistantConfig

    with seed_operation():
        seeded = 0
        for specialist_data in data:
            # Idempotent: skip if already exists
            existing = await session.execute(
                sql_select(AIAssistantConfig).where(
                    AIAssistantConfig.name == specialist_data["name"],
                    AIAssistantConfig.agent_type == "specialist",
                )
            )
            if existing.scalar_one_or_none() is not None:
                continue

            specialist_data["model_id"] = str(specialist_data["model_id"])
            specialist = AIAssistantConfig(**specialist_data)
            session.add(specialist)
            await session.flush()
            seeded += 1

    logger.info(
        "Seeded %d AI specialist configs (skipped %d existing)",
        seeded,
        len(data) - seeded,
    )


# ---------------------------------------------------------------------------
# Core reseed function (accepts data dict, used by both CLI and API)
# ---------------------------------------------------------------------------


async def reseed_from_data(session: AsyncSession, data: dict[str, Any]) -> None:
    """Reseed database from a seed data dict.

    This is the core function called by both the CLI entry point and the API.
    Assumes tables have already been truncated before calling.
    """
    with seed_operation():
        print("  Seeding users and RBAC...")
        from app.db.seed_users_rbac import seed_users_and_rbac_from_data

        await seed_users_and_rbac_from_data(session, data)

        print("  Seeding AI providers...")
        await _seed_ai_providers(session, data["ai_providers"])

        print("  Seeding AI assistant configs...")
        await _seed_ai_assistant_configs(session, data["ai_assistant_configs"])

        print("  Seeding AI specialist configs...")
        await _seed_ai_specialist_configs(session, data["ai_specialist_configs"])

        print("  Seeding MCP servers...")
        await _seed_mcp_servers(session, data["mcp_servers"])

        print("  Seeding organizational units...")
        await _seed_organizational_units(session, data["organizational_units"])

        print("  Seeding cost element types...")
        await _seed_cost_element_types(session, data["cost_element_types"])

        print("  Seeding cost event types...")
        await _seed_cost_event_types(session, data["cost_event_types"])

        print("  Seeding change order workflow...")
        await _seed_change_order_workflow(session, data["change_order_workflow"])

        print("  Seeding demo project...")
        await _seed_demo_project(session, data["demo_project"])

        await session.commit()


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

    print("Seeding database from seed_data.json...")
    data = _load_seed_data()

    async with async_session_maker() as session:
        await reseed_from_data(session, data)

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
