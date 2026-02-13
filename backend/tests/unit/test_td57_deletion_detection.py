"""Test to verify TD-057 - MERGE Mode Branch Deletion Detection.

This test verifies the edge case where an entity is deleted on a branch
AFTER the as_of timestamp. In this case, MERGE mode SHOULD fall back to main.
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.core.versioning.enums import BranchMode
from app.services.project import ProjectService
from app.services.wbe import WBEService


@pytest.mark.asyncio
async def test_td57_deleted_after_as_of_should_fallback(db_session):
    """Verify that entities deleted AFTER as_of timestamp DO fall back to main.

    This is the edge case that _is_deleted_on_branch() must handle correctly.
    If an entity is deleted at T=10, but we query at T=5, the entity should
    still be visible (fall back to main if not on branch).

    Current implementation bug: _is_deleted_on_branch() doesn't check temporal aspect.
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
        new_branch="BR-123",
        from_branch="main",
    )
    await db_session.commit()

    # Get timestamps
    before_deletion = datetime.now(UTC)
    await db_session.commit()  # Ensure transaction is committed

    # Delete WBE on the change order branch
    await wbe_service.soft_delete(root_id=wbe_id, actor_id=actor_id, branch="BR-123")
    await db_session.commit()

    after_deletion = datetime.now(UTC) + timedelta(seconds=1)

    # Query BEFORE deletion timestamp - SHOULD fall back to main
    # because entity wasn't deleted yet at that point in time
    result_before = await wbe_service.get_as_of(
        entity_id=wbe_id,
        as_of=before_deletion,
        branch="BR-123",
        branch_mode=BranchMode.MERGE,
    )

    # This should return the main branch version because at T=before_deletion,
    # the entity was NOT deleted on BR-123 yet
    assert result_before is not None, (
        "Entity deleted AFTER as_of should fall back to main "
        "(deletion hadn't happened yet at query time)"
    )

    # Query AFTER deletion timestamp - should NOT fall back to main
    result_after = await wbe_service.get_as_of(
        entity_id=wbe_id,
        as_of=after_deletion,
        branch="BR-123",
        branch_mode=BranchMode.MERGE,
    )

    # This should return None because at T=after_deletion,
    # the entity WAS deleted on BR-123
    assert result_after is None, "Entity deleted BEFORE as_of should NOT fall back to main"


@pytest.mark.asyncio
async def test_td57_deleted_before_as_of_no_fallback(db_session):
    """Verify that entities deleted BEFORE as_of timestamp do NOT fall back to main.

    This is the main zombie check test case.
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
        new_branch="BR-123",
        from_branch="main",
    )
    await db_session.commit()

    # Delete WBE on the change order branch
    await wbe_service.soft_delete(root_id=wbe_id, actor_id=actor_id, branch="BR-123")
    await db_session.commit()

    # Query AFTER deletion timestamp
    as_of = datetime.now(UTC) + timedelta(seconds=1)

    result = await wbe_service.get_as_of(
        entity_id=wbe_id,
        as_of=as_of,
        branch="BR-123",
        branch_mode=BranchMode.MERGE,
    )

    # Should NOT fall back to main because entity was deleted on BR-123
    assert result is None, "Deleted entity on branch should NOT fall back to main"

    # But querying main directly should still work
    result_main = await wbe_service.get_as_of(
        entity_id=wbe_id, as_of=as_of, branch="main"
    )
    assert result_main is not None, "Entity on main branch should still be visible"
