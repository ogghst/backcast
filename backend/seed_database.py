#!/usr/bin/env python3
"""ANSI-748 compliant database seeder for Backcast.

Loads seed data from JSON files in dependency order:
1. organizational_units (OBS hierarchy)
2. cost_element_types (reference data, depends on org units)
3. cost_event_types (reference data, standalone)
4. demo_project.json (project, WBS elements, control accounts,
   work packages, cost elements, schedule baselines, forecasts,
   progress entries, cost events, cost registrations)

Usage:
    cd backend
    source .venv/bin/activate
    python seed_database.py              # seed all
    python seed_database.py --clean      # truncate ANSI-748 tables first
"""

import argparse
import asyncio
import json
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# ---------------------------------------------------------------------------
# Bootstrap: add backend/ to sys.path so we can import app modules
# ---------------------------------------------------------------------------
BACKEND_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import settings  # noqa: E402

SEED_DIR = BACKEND_DIR / "seed"

SEED_USER = "00000000-0000-0000-0000-000000000001"

# Tables that hold ANSI-748 seed data (truncated with --clean).
# Order matters: children before parents to respect FK-like relationships.
CLEANUP_ORDER = [
    "cost_registrations",
    "cost_events",
    "progress_entries",
    "forecasts",
    "schedule_baselines",
    "cost_elements",
    "work_packages",
    "control_accounts",
    "wbs_elements",
    "projects",
    "cost_event_types",
    "cost_element_types",
    "organizational_units",
]


def load_json(filename: str) -> list[dict] | dict:
    """Load a JSON file from the seed directory."""
    path = SEED_DIR / filename
    with open(path) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Table → column mappings (derived from actual DB schema inspection)
# ---------------------------------------------------------------------------
# Each entry: {table_name: [columns in insertion order]}
# The seeder reads the matching keys from the JSON dicts.

TABLE_COLUMNS: dict[str, list[str]] = {
    "organizational_units": [
        "organizational_unit_id",
        "code",
        "name",
        "parent_unit_id",
        "manager_id",
        "is_active",
        "description",
        "created_by",
    ],
    "cost_element_types": [
        "cost_element_type_id",
        "organizational_unit_id",
        "code",
        "name",
        "description",
        "created_by",
    ],
    "cost_event_types": [
        "cost_event_type_id",
        "code",
        "name",
        "color",
        "is_quality",
        "description",
        "created_by",
    ],
    "projects": [
        "id",
        "project_id",
        "name",
        "code",
        "description",
        "contract_value",
        "currency",
        "status",
        "start_date",
        "end_date",
        "created_by",
        "branch",
        "parent_id",
        "merge_from_branch",
        "deleted_at",
        "deleted_by",
    ],
    "wbs_elements": [
        "id",
        "wbs_element_id",
        "project_id",
        "parent_wbs_element_id",
        "code",
        "name",
        "level",
        "revenue_allocation",
        "description",
        "created_by",
        "branch",
        "parent_id",
        "merge_from_branch",
        "deleted_at",
        "deleted_by",
    ],
    "control_accounts": [
        "id",
        "control_account_id",
        "wbs_element_id",
        "organizational_unit_id",
        "name",
        "code",
        "description",
        "created_by",
        "branch",
        "parent_id",
        "merge_from_branch",
        "deleted_at",
        "deleted_by",
    ],
    "work_packages": [
        "id",
        "work_package_id",
        "control_account_id",
        "name",
        "code",
        "budget_amount",
        "description",
        "status",
        "schedule_baseline_id",
        "forecast_id",
        "created_by",
        "branch",
        "parent_id",
        "merge_from_branch",
        "deleted_at",
        "deleted_by",
    ],
    "cost_elements": [
        "id",
        "cost_element_id",
        "work_package_id",
        "cost_element_type_id",
        "amount",
        "description",
        "created_by",
        "deleted_at",
        "deleted_by",
    ],
    "schedule_baselines": [
        "id",
        "schedule_baseline_id",
        "name",
        "start_date",
        "end_date",
        "progression_type",
        "description",
        "created_by",
        "branch",
        "parent_id",
        "merge_from_branch",
        "deleted_at",
        "deleted_by",
    ],
    "forecasts": [
        "id",
        "forecast_id",
        "eac_amount",
        "basis_of_estimate",
        "approved_date",
        "approved_by",
        "created_by",
        "branch",
        "parent_id",
        "merge_from_branch",
        "deleted_at",
        "deleted_by",
    ],
    "progress_entries": [
        "id",
        "progress_entry_id",
        "work_package_id",
        "progress_percentage",
        "notes",
        "created_by",
        "deleted_at",
        "deleted_by",
    ],
    "cost_events": [
        "id",
        "cost_event_id",
        "project_id",
        "wbs_element_id",
        "cost_event_type_id",
        "name",
        "description",
        "status",
        "external_event_id",
        "event_date",
        "coq_category",
        "estimated_impact",
        "schedule_impact_days",
        "created_by",
        "deleted_at",
        "deleted_by",
    ],
    "cost_registrations": [
        "id",
        "cost_registration_id",
        "cost_element_id",
        "cost_event_id",
        "amount",
        "quantity",
        "unit_of_measure",
        "registration_date",
        "description",
        "invoice_number",
        "vendor_reference",
        "created_by",
        "deleted_at",
        "deleted_by",
    ],
}

# Ordered list of tables for insertion (matches dependency order).
INSERTION_ORDER = [
    "organizational_units",
    "cost_element_types",
    "cost_event_types",
    "projects",
    "wbs_elements",
    "control_accounts",
    "work_packages",
    "cost_elements",
    "schedule_baselines",
    "forecasts",
    "progress_entries",
    "cost_events",
    "cost_registrations",
]

# Column type classifications for asyncpg type coercion.
_DATETIME_COLS: set[str] = {
    "start_date",
    "end_date",
    "event_date",
    "registration_date",
    "approved_date",
    "deleted_at",
}

_DECIMAL_COLS: set[str] = {
    "contract_value",
    "revenue_allocation",
    "budget_amount",
    "amount",
    "eac_amount",
    "estimated_impact",
    "progress_percentage",
    "quantity",
}

_BOOL_COLS: set[str] = {
    "is_active",
    "is_quality",
}

_INT_COLS: set[str] = {
    "level",
    "schedule_impact_days",
}

# UUID columns are left as strings; asyncpg handles UUID string coercion natively.
_UUID_COLS: set[str] = {
    "id",
    "project_id",
    "organizational_unit_id",
    "parent_unit_id",
    "manager_id",
    "cost_element_type_id",
    "cost_event_type_id",
    "wbs_element_id",
    "parent_wbs_element_id",
    "control_account_id",
    "work_package_id",
    "cost_element_id",
    "schedule_baseline_id",
    "forecast_id",
    "progress_entry_id",
    "cost_event_id",
    "cost_registration_id",
    "created_by",
    "deleted_by",
    "approved_by",
    "parent_id",
}


async def insert_rows(
    session: AsyncSession,
    table: str,
    rows: list[dict],
) -> int:
    """Insert rows into a table, only including columns present in TABLE_COLUMNS."""
    columns = TABLE_COLUMNS[table]
    col_list = ", ".join(columns)
    placeholders = ", ".join(f":{c}" for c in columns)

    stmt = text(f"INSERT INTO {table} ({col_list}) VALUES ({placeholders})")

    # Build parameter dicts with only the columns we expect
    params = []
    for row in rows:
        p = {}
        for col in columns:
            val = row.get(col)
            # Convert string 'null' to actual None
            if val == "null":
                val = None
            # Coerce string values to native Python types for asyncpg
            if isinstance(val, str):
                # Datetime columns
                if col in _DATETIME_COLS:
                    val = datetime.fromisoformat(val)
                # Decimal columns
                elif col in _DECIMAL_COLS:
                    val = Decimal(val)
                # UUID columns
                elif col in _UUID_COLS:
                    pass  # asyncpg accepts UUID strings
                # Boolean columns
                elif col in _BOOL_COLS:
                    val = val.lower() in ("true", "1", "yes")
                # Integer columns
                elif col in _INT_COLS:
                    val = int(val)
            p[col] = val
        params.append(p)

    await session.execute(stmt, params)
    return len(params)


async def seed(session: AsyncSession, clean: bool = False) -> None:
    """Load and insert all seed data."""

    if clean:
        print("Cleaning existing data...")
        for table in CLEANUP_ORDER:
            await session.execute(text(f"TRUNCATE TABLE {table} CASCADE"))
        print(f"  Truncated {len(CLEANUP_ORDER)} tables.")
        await session.commit()

    # ------------------------------------------------------------------
    # 1. Reference data from individual files
    # ------------------------------------------------------------------
    ref_data: dict[str, list[dict]] = {
        "organizational_units": load_json("organizational_units.json"),
        "cost_element_types": load_json("cost_element_types.json"),
        "cost_event_types": load_json("cost_event_types.json"),
    }

    # ------------------------------------------------------------------
    # 2. Demo project (single file, multiple sections)
    # ------------------------------------------------------------------
    demo = load_json("demo_project.json")

    # Inject created_by into reference data rows
    for rows in ref_data.values():
        for row in rows:
            if "created_by" not in row:
                row["created_by"] = SEED_USER

    # Map demo_project.json keys to table names
    demo_key_to_table = {
        "project": "projects",
        "wbs_elements": "wbs_elements",
        "control_accounts": "control_accounts",
        "work_packages": "work_packages",
        "cost_elements": "cost_elements",
        "schedule_baselines": "schedule_baselines",
        "forecasts": "forecasts",
        "progress_entries": "progress_entries",
        "cost_events": "cost_events",
        "cost_registrations": "cost_registrations",
    }

    # Merge all data in insertion order
    for table in INSERTION_ORDER:
        rows: list[dict] = []

        # Check reference data files first
        if table in ref_data:
            rows.extend(ref_data[table])

        # Then check demo project sections
        for key, tbl in demo_key_to_table.items():
            if tbl == table:
                section = demo.get(key, [])
                if isinstance(section, dict):
                    rows.append(section)
                else:
                    rows.extend(section)

        if not rows:
            continue

        count = await insert_rows(session, table, rows)
        print(f"  {table}: {count} rows inserted")

    await session.commit()
    print("\nSeeding complete.")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Seed the Backcast database with ANSI-748 demo data")
    parser.add_argument("--clean", action="store_true", help="Truncate ANSI-748 tables before seeding")
    args = parser.parse_args()

    engine = create_async_engine(str(settings.ASYNC_DATABASE_URI), echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    print("Connecting to database...")
    async with session_factory() as session:
        await seed(session, clean=args.clean)

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
