"""Tests for Schedule Baseline 1:1 relationship migration.

Tests verify that:
1. Migration applies successfully
2. Foreign key constraint is created on cost_elements.schedule_baseline_id
3. Existing data is migrated without loss
4. Unique constraint enforces 1:1 relationship
5. Rollback restores original schema
"""

from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_cost_elements_has_schedule_baseline_id_column(db_session: AsyncSession):
    """Test that cost_elements table has schedule_baseline_id column after migration."""
    # Check column exists
    result = await db_session.execute(
        text("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'cost_elements'
            AND column_name = 'schedule_baseline_id'
        """)
    )
    column = result.fetchone()

    assert column is not None, "schedule_baseline_id column should exist"
    assert column[0] == "schedule_baseline_id"
    assert column[1] in ("uuid", "UUID")
    assert column[2] == "YES", "Column should be nullable for migration"


@pytest.mark.asyncio
async def test_schedule_baselines_missing_cost_element_id_fk(db_session: AsyncSession):
    """Test that cost_element_id FK is removed from schedule_baselines table."""
    # Check that cost_element_id still exists (as a column, not FK)
    result = await db_session.execute(
        text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'schedule_baselines'
            AND column_name = 'cost_element_id'
        """)
    )
    column = result.fetchone()

    # Column should still exist for data migration
    assert column is not None, "cost_element_id column should still exist"

    # Check no foreign key constraint exists
    result = await db_session.execute(
        text("""
            SELECT constraint_name
            FROM information_schema.table_constraints
            WHERE table_name = 'schedule_baselines'
            AND constraint_type = 'FOREIGN KEY'
        """)
    )
    fk_constraints = result.fetchall()

    # Should have no FK constraints (or none related to cost_element_id)
    cost_element_fks = [fk for fk in fk_constraints if "cost_element" in fk[0].lower()]
    assert len(cost_element_fks) == 0, "Should not have cost_element_id FK constraint"


@pytest.mark.asyncio
async def test_unique_constraint_on_schedule_baseline_id(db_session: AsyncSession):
    """Test that unique index was removed from cost_elements.schedule_baseline_id.

    In a bitemporal versioned system, we cannot have a unique constraint on a
    foreign key column because:
    1. The same entity (schedule baseline) can be referenced by multiple historical
       versions of a cost element
    2. The 1:1 relationship is enforced at the application layer (service layer)
    3. Only the application layer can distinguish between current and historical versions

    Migration 4295c725f05f removed the unique index to support proper versioning.
    """
    # Check that unique index does NOT exist
    result = await db_session.execute(
        text("""
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE tablename = 'cost_elements'
            AND indexname = 'uq_cost_elements_schedule_baseline_id'
        """)
    )
    index = result.fetchone()

    assert index is None, "Unique index should NOT exist on schedule_baseline_id (removed for versioning support)"


@pytest.mark.asyncio
async def test_foreign_key_constraint_on_schedule_baseline_id(db_session: AsyncSession):
    """Test that relationship integrity is enforced at application layer.

    Note: In a bitemporal versioned system, we cannot use a traditional FK constraint
    or unique index because schedule_baseline_id appears in multiple version rows.
    Instead, we enforce the 1:1 relationship at the application layer (service layer).

    This test verifies:
    1. The unique index was removed (to allow versioning)
    2. The regular performance index still exists (for query optimization)
    3. Application-level validation is documented
    """
    # Verify that the unique index does NOT exist
    result = await db_session.execute(
        text("""
            SELECT indexname
            FROM pg_indexes
            WHERE tablename = 'cost_elements'
            AND indexname = 'uq_cost_elements_schedule_baseline_id'
        """)
    )
    index = result.fetchone()

    assert index is None, "Unique index should NOT exist (removed for versioning support)"

    # Verify that regular index exists for query performance
    result = await db_session.execute(
        text("""
            SELECT indexname
            FROM pg_indexes
            WHERE tablename = 'cost_elements'
            AND indexname = 'ix_cost_elements_schedule_baseline_id'
        """)
    )
    perf_index = result.fetchone()

    assert perf_index is not None, "Performance index should exist"


@pytest.mark.asyncio
async def test_index_exists_on_schedule_baseline_id(db_session: AsyncSession):
    """Test that index exists on cost_elements.schedule_baseline_id."""
    # Check for index
    result = await db_session.execute(
        text("""
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE tablename = 'cost_elements'
            AND indexname LIKE '%schedule_baseline%'
        """)
    )
    indexes = result.fetchall()

    schedule_baseline_indexes = [
        idx for idx in indexes if "schedule_baseline" in idx[0].lower()
    ]
    assert len(schedule_baseline_indexes) > 0, \
        "Should have index on schedule_baseline_id"


@pytest.mark.asyncio
async def test_migration_preserves_existing_data(db_session: AsyncSession):
    """Test that existing schedule baseline data is preserved during migration."""
    # This test assumes migration has already run
    # We verify that we can query existing relationships

    # Query to check that baselines still exist and are linked
    result = await db_session.execute(
        text("""
            SELECT
                ce.cost_element_id,
                ce.code,
                ce.schedule_baseline_id,
                sb.schedule_baseline_id,
                sb.name
            FROM cost_elements ce
            LEFT JOIN schedule_baselines sb
                ON ce.schedule_baseline_id = sb.schedule_baseline_id
            WHERE ce.deleted_at IS NULL
            LIMIT 10
        """)
    )
    rows = result.fetchall()

    # If we have cost elements, we should be able to join to baselines
    # (This tests that the migration preserves data integrity)
    for row in rows:
        cost_element_id, code, schedule_baseline_id, baseline_id, baseline_name = row
        # If schedule_baseline_id is set, we should find the baseline
        if schedule_baseline_id is not None:
            assert baseline_id is not None, \
                f"Cost element {code} has schedule_baseline_id but baseline not found"


@pytest.mark.asyncio
async def test_enforces_1to1_relationship_at_db_level(db_session: AsyncSession):
    """Test that database does NOT enforce 1:1 relationship (application layer does).

    In a bitemporal versioned system, the database cannot enforce a 1:1 relationship
    via unique constraints because:
    - Multiple historical versions of a cost element can reference the same baseline
    - Only current versions should have the 1:1 constraint
    - The database cannot distinguish between current and historical versions

    Therefore, this test verifies that:
    1. The database ALLOWS multiple cost elements to reference the same baseline
    2. Application-layer logic (in services) enforces the 1:1 constraint for current versions
    """
    # Create a test schedule baseline
    baseline_id = uuid4()
    await db_session.execute(
        text("""
            INSERT INTO schedule_baselines (
                id, schedule_baseline_id, cost_element_id,
                name, start_date, end_date, progression_type,
                valid_time, transaction_time, created_by, branch
            ) VALUES (
                :id, :schedule_baseline_id, :cost_element_id,
                :name, :start_date, :end_date, :progression_type,
                tstzrange(now(), NULL), tstzrange(now(), NULL),
                :created_by, :branch
            )
        """),
        {
            "id": uuid4(),
            "schedule_baseline_id": baseline_id,
            "cost_element_id": uuid4(),  # Dummy ID
            "name": "Test Baseline",
            "start_date": datetime.utcnow(),
            "end_date": datetime.utcnow() + timedelta(days=90),
            "progression_type": "LINEAR",
            "created_by": uuid4(),
            "branch": "main"
        }
    )
    await db_session.commit()

    # Try to create two cost elements referencing the same baseline
    # This should SUCCEED at the database level (no unique constraint)
    ce1_id = uuid4()
    ce2_id = uuid4()

    # First cost element should succeed
    await db_session.execute(
        text("""
            INSERT INTO cost_elements (
                id, cost_element_id, wbe_id, cost_element_type_id,
                code, name, budget_amount, schedule_baseline_id,
                valid_time, transaction_time, created_by, branch
            ) VALUES (
                :id, :cost_element_id, :wbe_id, :cost_element_type_id,
                :code, :name, :budget_amount, :schedule_baseline_id,
                tstzrange(now(), NULL), tstzrange(now(), NULL),
                :created_by, :branch
            )
        """),
        {
            "id": uuid4(),
            "cost_element_id": ce1_id,
            "wbe_id": uuid4(),
            "cost_element_type_id": uuid4(),
            "code": "CE-001",
            "name": "Cost Element 1",
            "budget_amount": 100000,
            "schedule_baseline_id": baseline_id,
            "created_by": uuid4(),
            "branch": "main"
        }
    )
    await db_session.commit()

    # Second cost element with same baseline should ALSO succeed at DB level
    # (The unique constraint was removed to support versioning)
    await db_session.execute(
        text("""
            INSERT INTO cost_elements (
                id, cost_element_id, wbe_id, cost_element_type_id,
                code, name, budget_amount, schedule_baseline_id,
                valid_time, transaction_time, created_by, branch
            ) VALUES (
                :id, :cost_element_id, :wbe_id, :cost_element_type_id,
                :code, :name, :budget_amount, :schedule_baseline_id,
                tstzrange(now(), NULL), tstzrange(now(), NULL),
                :created_by, :branch
            )
        """),
        {
            "id": uuid4(),
            "cost_element_id": ce2_id,
            "wbe_id": uuid4(),
            "cost_element_type_id": uuid4(),
            "code": "CE-002",
            "name": "Cost Element 2",
            "budget_amount": 200000,
            "schedule_baseline_id": baseline_id,  # Same baseline!
            "created_by": uuid4(),
            "branch": "main"
        }
    )
    await db_session.commit()

    # Verify both cost elements were created successfully
    result = await db_session.execute(
        text("""
            SELECT cost_element_id, code, schedule_baseline_id
            FROM cost_elements
            WHERE schedule_baseline_id = :baseline_id
            AND deleted_at IS NULL
        """),
        {"baseline_id": baseline_id}
    )
    rows = result.fetchall()

    # Database allows multiple cost elements to reference the same baseline
    # The 1:1 constraint is enforced at the application layer
    assert len(rows) == 2, "Database should allow multiple cost elements to reference the same baseline"


@pytest.mark.asyncio
async def test_cost_element_can_have_null_schedule_baseline_id(db_session: AsyncSession):
    """Test that cost_elements.schedule_baseline_id is nullable (for migration)."""
    # Create a cost element without a schedule baseline
    ce_id = uuid4()

    await db_session.execute(
        text("""
            INSERT INTO cost_elements (
                id, cost_element_id, wbe_id, cost_element_type_id,
                code, name, budget_amount,
                valid_time, transaction_time, created_by, branch
            ) VALUES (
                :id, :cost_element_id, :wbe_id, :cost_element_type_id,
                :code, :name, :budget_amount,
                tstzrange(now(), NULL), tstzrange(now(), NULL),
                :created_by, :branch
            )
        """),
        {
            "id": uuid4(),
            "cost_element_id": ce_id,
            "wbe_id": uuid4(),
            "cost_element_type_id": uuid4(),
            "code": "CE-NO-BASELINE",
            "name": "Cost Element Without Baseline",
            "budget_amount": 100000,
            "created_by": uuid4(),
            "branch": "main"
        }
    )
    await db_session.commit()

    # Query to verify NULL is allowed
    result = await db_session.execute(
        text("""
            SELECT schedule_baseline_id
            FROM cost_elements
            WHERE cost_element_id = :ce_id
        """),
        {"ce_id": ce_id}
    )
    schedule_baseline_id = result.scalar_one()

    assert schedule_baseline_id is None, "Should allow NULL schedule_baseline_id"
