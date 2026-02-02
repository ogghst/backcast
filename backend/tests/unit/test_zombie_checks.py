"""Zombie check tests for temporal entities.

Verifies that soft-deleted entities correctly respect time travel boundaries:
- Deleted entities are NOT visible when querying after their deleted_at timestamp

Note: These tests use System Time Travel semantics (get_as_of), which require
query timestamps to be after the transaction_time lower bound. The simplified
tests verify the core zombie behavior: entities disappear after deletion.

Reference: docs/02-architecture/cross-cutting/temporal-query-reference.md
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.core.versioning.enums import BranchMode
from app.services.project import ProjectService
from app.services.wbe import WBEService

UTC = UTC


# ============================================================================
# Project Zombie Check (TemporalService)
# ============================================================================


@pytest.mark.asyncio
async def test_project_zombie_check_deleted_not_visible(db_session):
    """Verify deleted Projects are NOT visible after deletion.

    Core zombie behavior: Entity disappears after deleted_at timestamp.
    """
    service = ProjectService(db_session)
    actor_id = uuid4()
    project_id = uuid4()

    # 1. Create entity
    project = await service.create(
        root_id=project_id,
        actor_id=actor_id,
        code="P001",
        name="Test Project",
    )
    await db_session.commit()

    # Verify entity exists before deletion
    result_before = await service.get_as_of(
        entity_id=project_id, as_of=datetime.now(UTC), branch="main"
    )
    assert result_before is not None, "Entity should be visible before deletion"

    # 2. Delete entity
    await service.soft_delete(entity_id=project_id, actor_id=actor_id)
    await db_session.commit()

    # Verify deletion was recorded
    current = await service.get_by_id(project.id)
    assert current.deleted_at is not None

    # 3. Query after deletion - should NOT return entity
    result_after = await service.get_as_of(
        entity_id=project_id,
        as_of=datetime.now(UTC) + timedelta(seconds=1),
        branch="main",
    )
    assert result_after is None, "Deleted entity should NOT be visible after deletion"


# ============================================================================
# WBE Zombie Check (BranchableService)
# ============================================================================


@pytest.mark.asyncio
async def test_wbe_zombie_check_deleted_not_visible(db_session):
    """Verify deleted WBEs are NOT visible after deletion.

    Note: WBE requires a parent project.
    """
    actor_id = uuid4()
    project_id = uuid4()
    wbe_id = uuid4()

    # First create a parent project
    project_service = ProjectService(db_session)
    await project_service.create(
        root_id=project_id,
        actor_id=actor_id,
        code="PROJ-001",
        name="Parent Project",
    )
    await db_session.commit()

    # 1. Create WBE
    wbe_service = WBEService(db_session)
    await wbe_service.create_root(
        root_id=wbe_id,
        actor_id=actor_id,
        project_id=project_id,
        code="WBE-001",
        name="Test WBE",
    )
    await db_session.commit()

    # Verify entity exists before deletion
    result_before = await wbe_service.get_as_of(
        entity_id=wbe_id, as_of=datetime.now(UTC), branch="main"
    )
    assert result_before is not None

    # 2. Delete WBE
    deleted = await wbe_service.soft_delete(root_id=wbe_id, actor_id=actor_id)
    await db_session.commit()

    assert deleted.deleted_at is not None

    # 3. Query after deletion - should NOT return entity
    result_after = await wbe_service.get_as_of(
        entity_id=wbe_id, as_of=datetime.now(UTC) + timedelta(seconds=1), branch="main"
    )
    assert result_after is None


# ============================================================================
# Branch Mode Zombie Check
# ============================================================================


@pytest.mark.asyncio
async def test_wbe_zombie_check_merge_mode_no_fallback(db_session):
    """Verify zombie check works correctly with MERGE branch mode.

    Tests that deleted entities on a branch don't fall back to main.
    """
    actor_id = uuid4()
    project_id = uuid4()
    wbe_id = uuid4()

    # Create parent project
    project_service = ProjectService(db_session)
    await project_service.create(
        root_id=project_id, actor_id=actor_id, code="PROJ-001", name="Parent Project"
    )
    await db_session.commit()

    # Create WBE on main branch
    wbe_service = WBEService(db_session)
    await wbe_service.create_root(
        root_id=wbe_id,
        actor_id=actor_id,
        project_id=project_id,
        code="WBE-001",
        name="Test WBE",
    )
    await db_session.commit()

    # Create a change order branch
    await wbe_service.create_branch(
        root_id=wbe_id,
        actor_id=actor_id,
        new_branch="co-123",
        from_branch="main",
    )
    await db_session.commit()

    # Delete WBE on the change order branch
    await wbe_service.soft_delete(root_id=wbe_id, actor_id=actor_id, branch="co-123")
    await db_session.commit()

    # Query with MERGE mode after deletion
    # Should NOT fall back to main because entity was deleted on co-123
    result = await wbe_service.get_as_of(
        entity_id=wbe_id,
        as_of=datetime.now(UTC) + timedelta(seconds=1),
        branch="co-123",
        branch_mode=BranchMode.MERGE,
    )
    # Note: This test may fail if MERGE mode fallback logic doesn't properly
    # detect that the entity was deleted on the requested branch.
    # The expected behavior is that deleted entities on a branch should NOT
    # fall back to main during MERGE mode queries.
    assert result is None, "Deleted entity on branch should NOT fall back to main"

    # But querying main directly should still work
    result_main = await wbe_service.get_as_of(
        entity_id=wbe_id, as_of=datetime.now(UTC) + timedelta(seconds=1), branch="main"
    )
    assert result_main is not None, "Entity on main branch should still be visible"


# ============================================================================
# Note: Progress Entry and Cost Registration Zombie Check Tests
# ============================================================================
#
# Zombie check tests for progress entries and cost registrations already exist
# in their respective time-travel test files:
#
# - tests/integration/test_progress_time_travel.py::TestProgressTimeTravel::test_time_travel_with_deleted_entry
# - tests/unit/services/test_cost_registration_time_travel.py::TestTimeTravelQueries::test_get_total_for_cost_element_includes_costs_soft_deleted_after_as_of
# - tests/unit/services/test_cost_registration_time_travel.py::TestTimeTravelQueries::test_get_total_for_cost_element_excludes_costs_soft_deleted_before_as_of
#
# These tests verify the Zombie Check TDD pattern:
# - Create → Delete → Query Past
# - Deleted entities are NOT visible when querying after their deleted_at timestamp
# - Deleted entities ARE visible when querying before their deleted_at timestamp
#
# Reference: docs/02-architecture/cross-cutting/temporal-query-reference.md
# ============================================================================

