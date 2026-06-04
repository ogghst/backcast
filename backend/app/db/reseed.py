"""Database reseed CLI script.

Truncates all data tables and re-seeds from split seed files
(seed_system_config.json + seed_projects.json).

Usage:
    python -m app.db.reseed          # With confirmation prompt
    python -m app.db.reseed --yes    # Skip confirmation
"""

import argparse
import asyncio
import json
import logging
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
SEED_SYSTEM_CONFIG_FILE = SEED_DIR / "seed_system_config.json"
SEED_PROJECTS_FILE = SEED_DIR / "seed_projects.json"

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
    "document_entity_links",
    "document_versions",
    "documents",
    "document_folders",
    "cost_registrations",
    "progress_entries",
    "cost_elements",
    "forecasts",
    "schedule_dependencies",
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


def _load_system_config() -> dict[str, Any]:
    """Load the system config seed file."""
    with open(SEED_SYSTEM_CONFIG_FILE) as f:
        return json.load(f)


def _load_projects() -> dict[str, Any]:
    """Load the projects seed file."""
    with open(SEED_PROJECTS_FILE) as f:
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

    config_data = workflow_data.get("config", {})
    if not config_data:
        logger.info("No change order workflow config to seed, skipping")
        return

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


async def _seed_project_budget_settings(
    session: AsyncSession, data: list[dict[str, Any]]
) -> None:
    """Seed project budget settings from data list."""
    from app.models.domain.project_budget_settings import ProjectBudgetSettings

    with seed_operation():
        count = 0
        for item in data:
            item_copy = dict(item)
            root_id = UUID(item_copy.pop("project_budget_settings_id"))
            item_copy.pop("id", None)
            created_by = UUID(item_copy.pop("created_by"))
            item_copy.pop("deleted_at", None)
            item_copy.pop("deleted_by", None)

            settings = ProjectBudgetSettings(
                id=root_id,
                project_budget_settings_id=root_id,
                project_id=UUID(item_copy.pop("project_id")),
                created_by=created_by,
                **{k: _coerce_value(k, v) for k, v in item_copy.items()},
            )
            session.add(settings)
            count += 1
        await session.flush()
    logger.info("Seeded %d project budget settings", count)


async def _seed_branches(session: AsyncSession, data: list[dict[str, Any]]) -> None:
    """Seed branches from data list."""
    from app.models.domain.branch import Branch

    with seed_operation():
        count = 0
        for item in data:
            item_copy = dict(item)
            item_copy.pop("id", None)
            created_by = UUID(item_copy.pop("created_by"))
            item_copy.pop("parent_id", None)
            item_copy.pop("merge_from_branch", None)
            item_copy.pop("deleted_at", None)
            item_copy.pop("deleted_by", None)
            # DB column is branch_metadata_info, but ORM attribute is branch_metadata
            if "branch_metadata_info" in item_copy:
                item_copy["branch_metadata"] = item_copy.pop("branch_metadata_info")

            branch = Branch(
                created_by=created_by,
                **{k: _coerce_value(k, v) for k, v in item_copy.items()},
            )
            session.add(branch)
            count += 1
        await session.flush()
    logger.info("Seeded %d branches", count)


async def _seed_schedule_dependencies(
    session: AsyncSession, data: list[dict[str, Any]]
) -> None:
    """Seed schedule dependencies from data list."""
    from app.models.domain.schedule_dependency import ScheduleDependency

    with seed_operation():
        count = 0
        for item in data:
            item_copy = dict(item)
            item_copy.pop("id", None)

            dep = ScheduleDependency(
                schedule_dependency_id=UUID(item_copy.pop("schedule_dependency_id")),
                predecessor_id=UUID(item_copy.pop("predecessor_id")),
                successor_id=UUID(item_copy.pop("successor_id")),
                dependency_type=item_copy.pop("dependency_type", "FS"),
                lag_days=item_copy.pop("lag_days", 0),
                branch=item_copy.pop("branch", "main"),
                project_id=UUID(item_copy.pop("project_id")),
            )
            session.add(dep)
            count += 1
        await session.flush()
    logger.info("Seeded %d schedule dependencies", count)


# ---------------------------------------------------------------------------
# Flat project seeding helpers (new top-level array format)
# ---------------------------------------------------------------------------


async def _seed_projects(session: AsyncSession, data: list[dict[str, Any]]) -> None:
    """Seed projects from flat array data."""
    from app.models.schemas.project import ProjectCreate
    from app.services.project import ProjectService

    service = ProjectService(session)
    count = 0
    for item in data:
        item_copy = dict(item)
        item_copy.pop("id", None)
        item_copy.pop("parent_id", None)
        item_copy.pop("merge_from_branch", None)
        item_copy.pop("deleted_at", None)
        item_copy.pop("deleted_by", None)
        created_by = UUID(item_copy.pop("created_by"))
        schema = ProjectCreate(**item_copy)
        await service.create_project(schema, actor_id=created_by)
        count += 1
    logger.info("Seeded %d projects", count)


async def _seed_wbs_elements_flat(
    session: AsyncSession, data: list[dict[str, Any]]
) -> None:
    """Seed WBS elements from flat array data."""
    from app.services.wbs_element_service import WBSElementService

    service = WBSElementService(session)
    count = 0
    for item in data:
        item_copy = dict(item)
        root_id = UUID(item_copy.pop("wbs_element_id"))
        item_copy.pop("id", None)
        created_by = UUID(item_copy.pop("created_by"))
        item_copy.pop("parent_id", None)
        item_copy.pop("merge_from_branch", None)
        item_copy.pop("deleted_at", None)
        item_copy.pop("deleted_by", None)
        branch = item_copy.pop("branch", "main")
        await service.create_root(
            root_id=root_id,
            actor_id=created_by,
            branch=branch,
            **item_copy,
        )
        count += 1
    logger.info("Seeded %d WBS elements", count)


async def _seed_control_accounts_flat(
    session: AsyncSession, data: list[dict[str, Any]]
) -> None:
    """Seed control accounts from flat array data."""
    from app.services.control_account_service import ControlAccountService

    service = ControlAccountService(session)
    count = 0
    for item in data:
        item_copy = dict(item)
        root_id = UUID(item_copy.pop("control_account_id"))
        item_copy.pop("id", None)
        created_by = UUID(item_copy.pop("created_by"))
        item_copy.pop("parent_id", None)
        item_copy.pop("merge_from_branch", None)
        item_copy.pop("deleted_at", None)
        item_copy.pop("deleted_by", None)
        branch = item_copy.pop("branch", "main")
        await service.create_root(
            root_id=root_id,
            actor_id=created_by,
            branch=branch,
            **item_copy,
        )
        count += 1
    await session.flush()
    logger.info("Seeded %d control accounts", count)


async def _seed_work_packages_flat(
    session: AsyncSession, data: list[dict[str, Any]]
) -> None:
    """Seed work packages from flat array data."""
    from app.services.work_package_service import WorkPackageService

    service = WorkPackageService(session)
    count = 0
    for item in data:
        item_copy = dict(item)
        root_id = UUID(item_copy.pop("work_package_id"))
        item_copy.pop("id", None)
        created_by = UUID(item_copy.pop("created_by"))
        item_copy.pop("parent_id", None)
        item_copy.pop("merge_from_branch", None)
        item_copy.pop("deleted_at", None)
        item_copy.pop("deleted_by", None)
        item_copy.pop("schedule_baseline_id", None)
        item_copy.pop("forecast_id", None)
        branch = item_copy.pop("branch", "main")
        await service.create_root(
            root_id=root_id,
            actor_id=created_by,
            branch=branch,
            **item_copy,
        )
        count += 1
    await session.flush()
    logger.info("Seeded %d work packages", count)


async def _seed_cost_elements_flat(
    session: AsyncSession, data: list[dict[str, Any]]
) -> None:
    """Seed cost elements from flat array data."""
    from app.core.versioning.commands import CreateVersionCommand
    from app.models.domain.cost_element import CostElement

    count = 0
    for item in data:
        item_copy = dict(item)
        root_id = UUID(item_copy.pop("cost_element_id"))
        item_copy.pop("id", None)
        created_by = UUID(item_copy.pop("created_by"))
        item_copy.pop("deleted_at", None)
        item_copy.pop("deleted_by", None)
        item_copy.pop("parent_id", None)
        item_copy.pop("merge_from_branch", None)
        branch = item_copy.pop("branch", "main")
        cmd = CreateVersionCommand(
            entity_class=CostElement,
            root_id=root_id,
            actor_id=created_by,
            branch=branch,
            **item_copy,
        )
        await cmd.execute(session)
        count += 1
    await session.flush()
    logger.info("Seeded %d cost elements", count)


async def _seed_schedule_baselines_flat(
    session: AsyncSession, data: list[dict[str, Any]]
) -> None:
    """Seed schedule baselines from flat array data."""
    from app.services.schedule_baseline_service import ScheduleBaselineService

    service = ScheduleBaselineService(session)
    count = 0
    for item in data:
        item_copy = dict(item)
        root_id = UUID(item_copy.pop("schedule_baseline_id"))
        item_copy.pop("id", None)
        created_by = UUID(item_copy.pop("created_by"))
        item_copy.pop("parent_id", None)
        item_copy.pop("merge_from_branch", None)
        item_copy.pop("deleted_at", None)
        item_copy.pop("deleted_by", None)
        branch = item_copy.pop("branch", "main")
        _parse_datetimes(item_copy, ["start_date", "end_date"])
        await service.create_root(
            root_id=root_id,
            actor_id=created_by,
            branch=branch,
            **item_copy,
        )
        count += 1
    logger.info("Seeded %d schedule baselines", count)


async def _seed_forecasts_flat(
    session: AsyncSession, data: list[dict[str, Any]]
) -> None:
    """Seed forecasts from flat array data."""
    from app.services.forecast_service import ForecastService

    service = ForecastService(session)
    count = 0
    for item in data:
        item_copy = dict(item)
        root_id = UUID(item_copy.pop("forecast_id"))
        item_copy.pop("id", None)
        created_by = UUID(item_copy.pop("created_by"))
        item_copy.pop("parent_id", None)
        item_copy.pop("merge_from_branch", None)
        item_copy.pop("deleted_at", None)
        item_copy.pop("deleted_by", None)
        branch = item_copy.pop("branch", "main")
        await service.create_root(
            root_id=root_id,
            actor_id=created_by,
            branch=branch,
            **item_copy,
        )
        count += 1
    await session.flush()
    logger.info("Seeded %d forecasts", count)


async def _seed_progress_entries_flat(
    session: AsyncSession, data: list[dict[str, Any]]
) -> None:
    """Seed progress entries from flat array data."""
    from decimal import Decimal

    from app.core.versioning.commands import CreateVersionCommand
    from app.models.domain.progress_entry import ProgressEntry

    count = 0
    for item in data:
        item_copy = dict(item)
        root_id = UUID(item_copy.pop("progress_entry_id"))
        item_copy.pop("id", None)
        created_by = UUID(item_copy.pop("created_by"))
        item_copy.pop("deleted_at", None)
        item_copy.pop("deleted_by", None)
        item_copy.pop("parent_id", None)
        item_copy.pop("merge_from_branch", None)
        if "progress_percentage" in item_copy and isinstance(
            item_copy["progress_percentage"], str
        ):
            item_copy["progress_percentage"] = Decimal(item_copy["progress_percentage"])
        branch = item_copy.pop("branch", "main")
        cmd = CreateVersionCommand(
            entity_class=ProgressEntry,
            root_id=root_id,
            actor_id=created_by,
            branch=branch,
            **item_copy,
        )
        await cmd.execute(session)
        count += 1
    await session.flush()
    logger.info("Seeded %d progress entries", count)


async def _seed_cost_events_flat(
    session: AsyncSession, data: list[dict[str, Any]]
) -> None:
    """Seed cost events from flat array data."""
    from app.core.versioning.commands import CreateVersionCommand
    from app.models.domain.cost_event import CostEvent

    count = 0
    for item in data:
        item_copy = dict(item)
        root_id = UUID(item_copy.pop("cost_event_id"))
        item_copy.pop("id", None)
        created_by = UUID(item_copy.pop("created_by"))
        item_copy.pop("deleted_at", None)
        item_copy.pop("deleted_by", None)
        item_copy.pop("parent_id", None)
        item_copy.pop("merge_from_branch", None)
        branch = item_copy.pop("branch", "main")
        cmd = CreateVersionCommand(
            entity_class=CostEvent,
            root_id=root_id,
            actor_id=created_by,
            branch=branch,
            **item_copy,
        )
        await cmd.execute(session)
        count += 1
    await session.flush()
    logger.info("Seeded %d cost events", count)


async def _seed_cost_registrations_flat(
    session: AsyncSession, data: list[dict[str, Any]]
) -> None:
    """Seed cost registrations from flat array data."""
    from app.core.versioning.commands import CreateVersionCommand
    from app.models.domain.cost_registration import CostRegistration

    count = 0
    for item in data:
        item_copy = dict(item)
        root_id = UUID(item_copy.pop("cost_registration_id"))
        item_copy.pop("id", None)
        created_by = UUID(item_copy.pop("created_by"))
        item_copy.pop("deleted_at", None)
        item_copy.pop("deleted_by", None)
        item_copy.pop("parent_id", None)
        item_copy.pop("merge_from_branch", None)
        branch = item_copy.pop("branch", "main")
        cmd = CreateVersionCommand(
            entity_class=CostRegistration,
            root_id=root_id,
            actor_id=created_by,
            branch=branch,
            **item_copy,
        )
        await cmd.execute(session)
        count += 1
    await session.flush()
    logger.info("Seeded %d cost registrations", count)


async def _seed_change_orders_flat(
    session: AsyncSession, data: list[dict[str, Any]]
) -> None:
    """Seed change orders from flat array data."""
    if not data:
        return
    from app.models.domain.change_order import ChangeOrder

    count = 0
    for item in data:
        item_copy = dict(item)
        item_copy.pop("id", None)
        co_id = item_copy["change_order_id"]
        co = ChangeOrder(
            id=UUID(co_id),
            **{k: _coerce_value(k, v) for k, v in item_copy.items()},
        )
        session.add(co)
        count += 1
    await session.flush()
    logger.info("Seeded %d change orders", count)


async def _seed_change_order_audit_logs_flat(
    session: AsyncSession, data: list[dict[str, Any]]
) -> None:
    """Seed change order audit logs from flat array data."""
    if not data:
        return
    from app.models.domain.change_order_audit_log import ChangeOrderAuditLog

    count = 0
    for item in data:
        item_copy = dict(item)
        alog = ChangeOrderAuditLog(
            id=UUID(item_copy.pop("id")),
            **{k: _coerce_value(k, v) for k, v in item_copy.items()},
        )
        session.add(alog)
        count += 1
    await session.flush()
    logger.info("Seeded %d change order audit logs", count)


async def _seed_document_folders(
    session: AsyncSession, data: list[dict[str, Any]]
) -> None:
    """Seed document folders from flat array data."""
    if not data:
        return
    from app.models.domain.document_folder import DocumentFolder

    count = 0
    for item in data:
        item_copy = dict(item)
        folder = DocumentFolder(
            id=UUID(item_copy.pop("id")),
            **{k: _coerce_value(k, v) for k, v in item_copy.items()},
        )
        session.add(folder)
        count += 1
    await session.flush()
    logger.info("Seeded %d document folders", count)


async def _seed_documents(session: AsyncSession, data: list[dict[str, Any]]) -> None:
    """Seed documents from flat array data."""
    if not data:
        return
    from app.models.domain.document import Document

    count = 0
    for item in data:
        item_copy = dict(item)
        doc = Document(
            id=UUID(item_copy.pop("id")),
            **{k: _coerce_value(k, v) for k, v in item_copy.items()},
        )
        session.add(doc)
        count += 1
    await session.flush()
    logger.info("Seeded %d documents", count)


async def _seed_document_versions(
    session: AsyncSession, data: list[dict[str, Any]]
) -> None:
    """Seed document versions from flat array data."""
    if not data:
        return
    from app.models.domain.document_version import DocumentVersion

    count = 0
    for item in data:
        item_copy = dict(item)
        ver = DocumentVersion(
            id=UUID(item_copy.pop("id")),
            **{k: _coerce_value(k, v) for k, v in item_copy.items()},
        )
        session.add(ver)
        count += 1
    await session.flush()
    logger.info("Seeded %d document versions", count)


async def _seed_document_entity_links(
    session: AsyncSession, data: list[dict[str, Any]]
) -> None:
    """Seed document entity links from flat array data."""
    if not data:
        return
    from app.models.domain.document_entity_link import DocumentEntityLink

    count = 0
    for item in data:
        item_copy = dict(item)
        link = DocumentEntityLink(
            id=UUID(item_copy.pop("id")),
            **{k: _coerce_value(k, v) for k, v in item_copy.items()},
        )
        session.add(link)
        count += 1
    await session.flush()
    logger.info("Seeded %d document entity links", count)


# ---------------------------------------------------------------------------
# Core reseed function (accepts data dict, used by both CLI and API)
# ---------------------------------------------------------------------------


async def reseed_from_data(session: AsyncSession, data: dict[str, Any]) -> None:
    """Reseed database from a seed data dict.

    This is the core function called by both the CLI entry point and the API.
    Assumes tables have already been truncated before calling.

    Expects flat top-level arrays for all project entities
    (``projects``, ``project_budget_settings``, ``branches``, etc.).
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

        print("  Seeding projects...")
        await _seed_projects(session, data.get("projects", []))

        print("  Seeding project budget settings...")
        await _seed_project_budget_settings(
            session, data.get("project_budget_settings", [])
        )

        print("  Seeding branches...")
        await _seed_branches(session, data.get("branches", []))

        print("  Seeding WBS elements...")
        await _seed_wbs_elements_flat(session, data.get("wbs_elements", []))

        print("  Seeding control accounts...")
        await _seed_control_accounts_flat(session, data.get("control_accounts", []))

        print("  Seeding work packages...")
        await _seed_work_packages_flat(session, data.get("work_packages", []))

        print("  Seeding cost elements...")
        await _seed_cost_elements_flat(session, data.get("cost_elements", []))

        print("  Seeding schedule baselines...")
        await _seed_schedule_baselines_flat(session, data.get("schedule_baselines", []))

        print("  Seeding schedule dependencies...")
        await _seed_schedule_dependencies(
            session, data.get("schedule_dependencies", [])
        )

        print("  Seeding forecasts...")
        await _seed_forecasts_flat(session, data.get("forecasts", []))

        print("  Seeding progress entries...")
        await _seed_progress_entries_flat(session, data.get("progress_entries", []))

        print("  Seeding cost events...")
        await _seed_cost_events_flat(session, data.get("cost_events", []))

        print("  Seeding cost registrations...")
        await _seed_cost_registrations_flat(session, data.get("cost_registrations", []))

        print("  Seeding document folders...")
        await _seed_document_folders(session, data.get("document_folders", []))

        print("  Seeding documents...")
        await _seed_documents(session, data.get("documents", []))

        print("  Seeding document versions...")
        await _seed_document_versions(session, data.get("document_versions", []))

        print("  Seeding document entity links...")
        await _seed_document_entity_links(
            session, data.get("document_entity_links", [])
        )

        print("  Seeding change orders...")
        await _seed_change_orders_flat(session, data.get("change_orders", []))

        print("  Seeding change order audit logs...")
        await _seed_change_order_audit_logs_flat(
            session, data.get("change_order_audit_logs", [])
        )

        await session.commit()


async def reseed_from_split_files(session: AsyncSession) -> None:
    """Load both split seed files and reseed from the merged result.

    Loads ``seed_system_config.json`` and ``seed_projects.json``, merges them
    into a single dict compatible with :func:`reseed_from_data`, then
    executes the reseed.
    """
    system_config = _load_system_config()
    projects = _load_projects()

    # Merge both files into a single dict for reseed_from_data
    merged: dict[str, Any] = {
        "_version": system_config.get("_version", 1),
        "_comment": "Merged from split seed files",
        # System config sections
        "rbac_roles": system_config.get("rbac_roles", {}),
        "users": system_config.get("users", []),
        "user_role_assignments": system_config.get("user_role_assignments", {}),
        "ai_providers": system_config.get("ai_providers", []),
        "ai_assistant_configs": system_config.get("ai_assistant_configs", []),
        "ai_specialist_configs": system_config.get("ai_specialist_configs", []),
        "mcp_servers": system_config.get("mcp_servers", []),
        "change_order_workflow": system_config.get("change_order_workflow", {}),
        # Project sections (flat top-level arrays)
        "organizational_units": projects.get("organizational_units", []),
        "cost_element_types": projects.get("cost_element_types", []),
        "cost_event_types": projects.get("cost_event_types", []),
        "projects": projects.get("projects", []),
        "project_budget_settings": projects.get("project_budget_settings", []),
        "branches": projects.get("branches", []),
        "wbs_elements": projects.get("wbs_elements", []),
        "control_accounts": projects.get("control_accounts", []),
        "work_packages": projects.get("work_packages", []),
        "cost_elements": projects.get("cost_elements", []),
        "schedule_baselines": projects.get("schedule_baselines", []),
        "schedule_dependencies": projects.get("schedule_dependencies", []),
        "forecasts": projects.get("forecasts", []),
        "progress_entries": projects.get("progress_entries", []),
        "cost_events": projects.get("cost_events", []),
        "cost_registrations": projects.get("cost_registrations", []),
        "document_folders": projects.get("document_folders", []),
        "documents": projects.get("documents", []),
        "document_versions": projects.get("document_versions", []),
        "document_entity_links": projects.get("document_entity_links", []),
        "change_orders": projects.get("change_orders", []),
        "change_order_audit_logs": projects.get("change_order_audit_logs", []),
    }

    await reseed_from_data(session, merged)


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

    print("Seeding database from split seed files...")
    async with async_session_maker() as session:
        await reseed_from_split_files(session)

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
