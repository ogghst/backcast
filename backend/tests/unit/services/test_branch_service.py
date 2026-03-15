"""Unit tests for BranchService."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.exc import NoResultFound

from app.models.domain.branch import Branch
from app.models.domain.project import Project
from app.services.branch_service import BranchService


@pytest.mark.asyncio
async def test_lock_branch_sets_locked_true(db_session):
    """Test that locking a branch sets locked field to True."""
    # Arrange: Create a project and unlocked branch
    user_id = uuid4()
    project = Project(
        project_id=uuid4(),
        code="TEST-PROJ-001",
        name="Test Project",
        branch="main",
        created_by=user_id,
    )
    db_session.add(project)
    await db_session.flush()

    branch = Branch(
        name="BR-CO-2026-001",
        project_id=project.project_id,
        type="change_order",
        locked=False,
        created_by=user_id,
    )
    db_session.add(branch)
    await db_session.commit()

    # Act: Lock the branch
    service = BranchService(db_session)
    locked_branch = await service.lock(
        name="BR-CO-2026-001", project_id=project.project_id, actor_id=user_id
    )

    # Assert: Branch is locked
    assert locked_branch.locked is True

    # Verify in database using service method which filters for current versions
    db_branch = await service.get_by_name_and_project(
        name="BR-CO-2026-001", project_id=project.project_id
    )
    assert db_branch.locked is True


@pytest.mark.asyncio
async def test_unlock_branch_sets_locked_false(db_session):
    """Test that unlocking a branch sets locked field to False."""
    # Arrange: Create a project and locked branch
    user_id = uuid4()
    project = Project(
        project_id=uuid4(),
        code="TEST-PROJ-002",
        name="Test Project 2",
        branch="main",
        created_by=user_id,
    )
    db_session.add(project)
    await db_session.flush()

    branch = Branch(
        name="BR-CO-2026-002",
        project_id=project.project_id,
        type="change_order",
        locked=True,
        created_by=user_id,
    )
    db_session.add(branch)
    await db_session.commit()

    # Act: Unlock the branch
    service = BranchService(db_session)
    unlocked_branch = await service.unlock(
        name="BR-CO-2026-002", project_id=project.project_id, actor_id=user_id
    )

    # Assert: Branch is unlocked
    assert unlocked_branch.locked is False


@pytest.mark.asyncio
async def test_get_branch_by_name_and_project(db_session):
    """Test retrieving a branch by composite key."""
    # Arrange: Create a project and branch
    user_id = uuid4()
    project = Project(
        project_id=uuid4(),
        code="TEST-PROJ-003",
        name="Test Project 3",
        branch="main",
        created_by=user_id,
    )
    db_session.add(project)
    await db_session.flush()

    branch = Branch(
        name="main",
        project_id=project.project_id,
        type="main",
        locked=False,
        created_by=user_id,
    )
    db_session.add(branch)
    await db_session.commit()

    # Act: Get branch by name and project_id
    service = BranchService(db_session)
    retrieved_branch = await service.get_by_name_and_project(
        name="main", project_id=project.project_id
    )

    # Assert: Branch is retrieved correctly
    assert retrieved_branch is not None
    assert retrieved_branch.name == "main"
    assert retrieved_branch.project_id == project.project_id
    assert retrieved_branch.type == "main"


@pytest.mark.asyncio
async def test_get_branch_excludes_soft_deleted(db_session):
    """Test that get_by_name_and_project excludes soft-deleted branches."""
    # Arrange: Create a project and two branches (one soft-deleted)
    user_id = uuid4()
    project = Project(
        project_id=uuid4(),
        code="TEST-PROJ-004",
        name="Test Project 4",
        branch="main",
        created_by=user_id,
    )
    db_session.add(project)
    await db_session.flush()

    # Active branch
    active_branch = Branch(
        name="BR-CO-2026-004a",
        project_id=project.project_id,
        type="change_order",
        locked=False,
        created_by=user_id,
    )
    db_session.add(active_branch)

    # Soft-deleted branch
    deleted_branch = Branch(
        name="BR-CO-2026-004b",
        project_id=project.project_id,
        type="change_order",
        locked=False,
        created_by=user_id,
        deleted_at=datetime.now(UTC),
    )
    db_session.add(deleted_branch)
    await db_session.commit()

    # Act: Try to get the soft-deleted branch
    service = BranchService(db_session)

    # Assert: Should raise NoResultFound for soft-deleted branch
    with pytest.raises(NoResultFound):
        await service.get_by_name_and_project(
            name="BR-CO-2026-004b", project_id=project.project_id
        )

    # But active branch should be found
    retrieved = await service.get_by_name_and_project(
        name="BR-CO-2026-004a", project_id=project.project_id
    )
    assert retrieved.name == "BR-CO-2026-004a"
