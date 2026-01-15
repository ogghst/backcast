"""Unit tests for Branch model."""

import pytest
from uuid import uuid4
from sqlalchemy.exc import IntegrityError

from app.models.domain.branch import Branch
from app.models.domain.project import Project


@pytest.mark.asyncio
async def test_branch_creation_with_composite_key(db_session):
    """Test that Branch can be created with composite PK (name, project_id)."""
    # Arrange: Create a project with required fields
    user_id = uuid4()
    project = Project(
        project_id=uuid4(),
        code="TEST-PROJ-001",
        name="Test Project",
        branch="main",
        created_by=user_id
    )
    db_session.add(project)
    await db_session.flush()

    # Act: Create a branch
    branch = Branch(
        name="co-CO-2026-001",
        project_id=project.project_id,
        type="change_order",
        locked=False,
        created_by=user_id
    )
    db_session.add(branch)
    await db_session.flush()

    # Assert: Branch was created with expected values
    assert branch.name == "co-CO-2026-001"
    assert branch.project_id == project.project_id
    assert branch.type == "change_order"
    assert branch.locked is False
    assert branch.created_at is not None
    assert branch.deleted_at is None


@pytest.mark.asyncio
async def test_branch_default_values(db_session):
    """Test that Branch fields have appropriate defaults."""
    # Arrange: Create a project with required fields
    user_id = uuid4()
    project = Project(
        project_id=uuid4(),
        code="TEST-PROJ-002",
        name="Test Project 2",
        branch="main",
        created_by=user_id
    )
    db_session.add(project)
    await db_session.flush()

    # Act: Create a branch with minimal fields
    branch = Branch(
        name="main",
        project_id=project.project_id,
        created_by=user_id
    )
    db_session.add(branch)
    await db_session.flush()

    # Assert: Default values are set correctly
    assert branch.type == "main"
    assert branch.locked is False
    assert branch.deleted_at is None
    assert branch.branch_metadata is None


@pytest.mark.asyncio
async def test_branch_locked_can_be_toggled(db_session):
    """Test that branch locked status can be toggled."""
    # Arrange: Create a project and unlocked branch
    user_id = uuid4()
    project = Project(
        project_id=uuid4(),
        code="TEST-PROJ-003",
        name="Test Project 3",
        branch="main",
        created_by=user_id
    )
    db_session.add(project)
    await db_session.flush()

    branch = Branch(
        name="co-CO-2026-003",
        project_id=project.project_id,
        type="change_order",
        locked=False,
        created_by=user_id
    )
    db_session.add(branch)
    await db_session.flush()

    # Act: Lock the branch
    branch.locked = True
    await db_session.flush()

    # Assert: Branch is now locked
    assert branch.locked is True

    # Act: Unlock the branch
    branch.locked = False
    await db_session.flush()

    # Assert: Branch is now unlocked
    assert branch.locked is False


@pytest.mark.asyncio
async def test_branch_soft_delete(db_session):
    """Test that branches can be soft deleted via deleted_at."""
    # Arrange: Create a project and branch
    user_id = uuid4()
    project = Project(
        project_id=uuid4(),
        code="TEST-PROJ-004",
        name="Test Project 4",
        branch="main",
        created_by=user_id
    )
    db_session.add(project)
    await db_session.flush()

    branch = Branch(
        name="co-CO-2026-004",
        project_id=project.project_id,
        type="change_order",
        locked=False,
        created_by=user_id
    )
    db_session.add(branch)
    await db_session.flush()

    # Act: Soft delete the branch
    from datetime import datetime, timezone
    branch.deleted_at = datetime.now(timezone.utc)
    await db_session.flush()

    # Assert: Branch has deleted_at timestamp
    assert branch.deleted_at is not None

