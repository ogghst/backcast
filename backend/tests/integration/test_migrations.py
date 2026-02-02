"""Integration tests for database migrations.

These tests verify that migrations execute correctly and create
the expected database schema, indexes, and constraints.

This helps catch migration issues early (e.g., missing extensions,
failed index creation, missing tables).
"""

import pytest
from sqlalchemy import text


@pytest.mark.asyncio
@pytest.mark.migration
async def test_progress_entries_table_exists(db_session):
    """Verify progress_entries table was created by migration.

    This test ensures the migration executed successfully and
    created the progress_entries table.

    Related to: CHECK phase Issue #5.1 - Critical Blocker
    """
    result = await db_session.execute(
        text(
            "SELECT EXISTS (SELECT FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = 'progress_entries')"
        )
    )
    exists = result.scalar_one()
    assert exists is True, "progress_entries table was not created by migration!"


@pytest.mark.asyncio
@pytest.mark.migration
async def test_progress_entries_columns_correct(db_session):
    """Verify progress_entries table has all required columns.

    This test ensures the migration created the correct schema
    with all expected columns.
    """
    result = await db_session.execute(
        text(
            """
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'progress_entries'
            ORDER BY ordinal_position
            """
        )
    )
    columns = {row[0]: {"type": row[1], "nullable": row[2]} for row in result.all()}

    # Verify critical columns exist
    required_columns = {
        "id": {"type": "uuid", "nullable": "NO"},
        "progress_entry_id": {"type": "uuid", "nullable": "NO"},
        "cost_element_id": {"type": "uuid", "nullable": "NO"},
        "progress_percentage": {"type": "numeric", "nullable": "NO"},
        "notes": {"type": "text", "nullable": "YES"},
        "valid_time": {"type": "tstzrange", "nullable": "NO"},
        "transaction_time": {"type": "tstzrange", "nullable": "NO"},
        "deleted_at": {"type": "timestamp with time zone", "nullable": "YES"},
        "created_by": {"type": "uuid", "nullable": "NO"},
        "deleted_by": {"type": "uuid", "nullable": "YES"},
        "created_at": {"type": "timestamp with time zone", "nullable": "NO"},
        "updated_at": {"type": "timestamp with time zone", "nullable": "NO"},
    }

    for col_name, expected in required_columns.items():
        assert col_name in columns, f"Column '{col_name}' not found in progress_entries table"
        actual = columns[col_name]
        assert (
            actual["type"] == expected["type"]
        ), f"Column '{col_name}' has wrong type: {actual['type']} != {expected['type']}"
        assert (
            actual["nullable"] == expected["nullable"]
        ), f"Column '{col_name}' has wrong nullable: {actual['nullable']} != {expected['nullable']}"


@pytest.mark.asyncio
@pytest.mark.migration
async def test_progress_entries_indexes_exist(db_session):
    """Verify all required indexes exist on progress_entries table.

    This test ensures the migration created the expected indexes
    for query performance and bitemporal versioning.
    """
    result = await db_session.execute(
        text(
            """
            SELECT indexname
            FROM pg_indexes
            WHERE tablename = 'progress_entries'
            ORDER BY indexname
            """
        )
    )
    actual_indexes = {row[0] for row in result.all()}

    # Verify all required indexes exist
    required_indexes = {
        "ix_progress_entries_progress_entry_id",
        "ix_progress_entries_cost_element_id",
        "ix_progress_entries_valid_time",
        "ix_progress_entries_transaction_time",
        "ix_progress_entries_current_versions",
    }

    missing_indexes = required_indexes - actual_indexes
    assert (
        not missing_indexes
    ), f"Missing indexes on progress_entries table: {missing_indexes}"


@pytest.mark.asyncio
@pytest.mark.migration
async def test_progress_entries_gist_indexes_use_btree_gist(db_session):
    """Verify GIST indexes exist (requires btree_gist extension).

    This test ensures the btree_gist extension was created and
    the GIST indexes on TSTZRANGE columns were created successfully.

    Related to: ACT Phase Option A - Fix Migration Execution
    """
    result = await db_session.execute(
        text(
            """
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE tablename = 'progress_entries'
            AND indexdef LIKE '%USING gist%'
            """
        )
    )
    gist_indexes = {row[0]: row[1] for row in result.all()}

    # Verify GIST indexes on temporal columns
    assert "ix_progress_entries_valid_time" in gist_indexes, (
        "GIST index on valid_time not found. "
        "btree_gist extension may not be enabled."
    )
    assert "USING gist (valid_time)" in gist_indexes["ix_progress_entries_valid_time"]

    assert "ix_progress_entries_transaction_time" in gist_indexes, (
        "GIST index on transaction_time not found. "
        "btree_gist extension may not be enabled."
    )
    assert "USING gist (transaction_time)" in gist_indexes["ix_progress_entries_transaction_time"]


@pytest.mark.asyncio
@pytest.mark.migration
async def test_progress_entries_foreign_key_constraints(db_session):
    """Verify foreign key constraints on progress_entries table.

    This test verifies that foreign keys are NOT enforced at database level
    (following the cost_registrations pattern) because business keys don't
    have unique constraints. Referential integrity is enforced at application level.

    Related to: Migration design decision - no FK constraints
    """
    result = await db_session.execute(
        text(
            """
            SELECT
                conname AS constraint_name,
                pg_get_constraintdef(c.oid) AS constraint_definition
            FROM pg_constraint c
            JOIN pg_namespace n ON n.oid = c.connamespace
            JOIN pg_class cl ON cl.oid = c.conrelid
            WHERE cl.relname = 'progress_entries'
            AND contype = 'f'
            ORDER BY conname
            """
        )
    )
    fk_constraints = {row[0]: row[1] for row in result.all()}

    # Verify NO foreign keys exist (by design, matching cost_registrations pattern)
    assert len(fk_constraints) == 0, (
        f"Expected no foreign key constraints (enforced at application level), "
        f"but found {len(fk_constraints)}: {list(fk_constraints.keys())}"
    )


@pytest.mark.asyncio
@pytest.mark.migration
async def test_progress_entries_check_constraint_percentage_range(db_session):
    """Verify check constraint for progress_percentage range (0-100).

    This test ensures data integrity is enforced for progress percentages.
    """
    result = await db_session.execute(
        text(
            """
            SELECT conname, pg_get_constraintdef(c.oid)
            FROM pg_constraint c
            JOIN pg_class cl ON cl.oid = c.conrelid
            WHERE cl.relname = 'progress_entries'
            AND contype = 'c'
            AND conname = 'chk_progress_entries_percentage_range'
            """
        )
    )
    constraint = result.first()

    assert constraint is not None, "Check constraint for percentage range not found"
    assert "progress_percentage >=" in constraint[1], (
        "Check constraint should enforce minimum value"
    )
    assert "progress_percentage <=" in constraint[1], (
        "Check constraint should enforce maximum value"
    )


@pytest.mark.asyncio
@pytest.mark.migration
async def test_progress_entries_exclusion_constraint_overlap(db_session):
    """Verify exclusion constraint prevents overlapping valid_time ranges.

    This test ensures bitemporal versioning integrity is enforced.
    """
    result = await db_session.execute(
        text(
            """
            SELECT conname, pg_get_constraintdef(c.oid)
            FROM pg_constraint c
            JOIN pg_class cl ON cl.oid = c.conrelid
            WHERE cl.relname = 'progress_entries'
            AND contype = 'x'
            AND conname = 'excl_progress_entries_overlap'
            """
        )
    )
    constraint = result.first()

    assert constraint is not None, "Exclusion constraint for overlap prevention not found"
    assert "EXCLUDE USING gist" in constraint[1], (
        "Exclusion constraint should use GIST"
    )
    assert "progress_entry_id WITH =" in constraint[1], (
        "Exclusion constraint should check progress_entry_id equality"
    )
    assert "valid_time WITH &&" in constraint[1], (
        "Exclusion constraint should check valid_time overlap"
    )


@pytest.mark.asyncio
@pytest.mark.migration
async def test_btree_gist_extension_enabled(db_session):
    """Verify btree_gist extension is enabled in the database.

    This test ensures the extension required for GIST indexes on
    TSTZRANGE columns is available.

    Related to: ACT Phase Option A - Fix Migration Execution
    """
    result = await db_session.execute(
        text(
            """
            SELECT extname
            FROM pg_extension
            WHERE extname = 'btree_gist'
            """
        )
    )
    extension = result.first()

    assert extension is not None, (
        "btree_gist extension is not enabled. "
        "This extension is required for GIST indexes on TSTZRANGE columns. "
        "Migration should have created it with: CREATE EXTENSION IF NOT EXISTS btree_gist"
    )
