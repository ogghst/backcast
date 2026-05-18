"""Database reseed CLI script.

Truncates all data tables and re-seeds from JSON seed files.

Usage:
    python -m app.db.reseed          # With confirmation prompt
    python -m app.db.reseed --yes    # Skip confirmation
"""

import argparse
import asyncio
import logging
import sys

from sqlalchemy import text

from app.core.config import settings
from app.db.seed_context import seed_operation
from app.db.seeder import DataSeeder
from app.db.session import async_session_maker, engine

logger = logging.getLogger(__name__)

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
    "quality_events",
    # Project data (leaf tables first)
    "cost_registrations",
    "progress_entries",
    "cost_elements",
    "forecasts",
    "schedule_baselines",
    "wbes",
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
    "departments",
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
    seeder = DataSeeder()
    async with async_session_maker() as session:
        with seed_operation():
            await seeder.seed_all(session)

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
