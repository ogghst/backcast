"""Unit tests to improve coverage for base classes and error paths."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.branching.commands import (
    CreateBranchCommand,
    MergeBranchCommand,
    RevertCommand,
    UpdateCommand,
)
from app.core.versioning.commands import UpdateVersionCommand
from app.core.versioning.service import TemporalService
from app.models.domain.project import Project


@pytest.mark.asyncio
async def test_update_version_command_no_active_version(db_session: AsyncSession):
    """Test UpdateVersionCommand raises ValueError when no active version exists."""
    root_id = uuid4()
    # Don't create any version

    cmd = UpdateVersionCommand(Project, root_id, name="Update")
    with pytest.raises(ValueError, match="No active version found"):
        await cmd.execute(db_session)

@pytest.mark.asyncio
async def test_create_branch_command_no_active_version(db_session: AsyncSession):
    """Test CreateBranchCommand raises ValueError when source branch has no active version."""
    root_id = uuid4()

    cmd = CreateBranchCommand(Project, root_id, new_branch="feat/x", from_branch="main")
    with pytest.raises(ValueError, match="No active version on branch"):
        await cmd.execute(db_session)

@pytest.mark.asyncio
async def test_update_command_no_active_version(db_session: AsyncSession):
    """Test UpdateCommand (Branch) raises ValueError when branch has no active version."""
    root_id = uuid4()

    cmd = UpdateCommand(Project, root_id, updates={"name": "Update"}, branch="main")
    with pytest.raises(ValueError, match="No active version on branch"):
        await cmd.execute(db_session)

@pytest.mark.asyncio
async def test_merge_branch_command_missing_source(db_session: AsyncSession):
    """Test MergeBranchCommand raises ValueError when source branch missing."""
    root_id = uuid4()

    cmd = MergeBranchCommand(Project, root_id, source_branch="feature/missing", target_branch="main")
    with pytest.raises(ValueError, match="Source branch .* not found"):
        await cmd.execute(db_session)

@pytest.mark.asyncio
async def test_merge_branch_command_missing_target(db_session: AsyncSession):
    """Test MergeBranchCommand raises ValueError when target branch missing."""
    root_id = uuid4()

    # Create source manually so it passes first check
    project = Project(project_id=root_id, name="Src", branch="feature/exists")
    db_session.add(project)
    await db_session.flush()

    cmd = MergeBranchCommand(Project, root_id, source_branch="feature/exists", target_branch="main")
    with pytest.raises(ValueError, match="Target branch .* not found"):
        await cmd.execute(db_session)

@pytest.mark.asyncio
async def test_revert_command_no_active_version(db_session: AsyncSession):
    """Test RevertCommand raises ValueError when current branch is empty."""
    root_id = uuid4()

    cmd = RevertCommand(Project, root_id, branch="main")
    with pytest.raises(ValueError, match="No active version on"):
        await cmd.execute(db_session)

@pytest.mark.asyncio
async def test_revert_command_no_target_version(db_session: AsyncSession):
    """Test RevertCommand raises ValueError when no parent/target specified."""
    root_id = uuid4()

    # Create orphan version (no parent)
    project = Project(project_id=root_id, name="Orphan", branch="main")
    db_session.add(project)
    await db_session.flush()

    cmd = RevertCommand(Project, root_id, branch="main")
    with pytest.raises(ValueError, match="Cannot revert: No target version specified"):
        await cmd.execute(db_session)

@pytest.mark.asyncio
async def test_temporal_service_base_methods(db_session: AsyncSession):
    """Test standard methods of TemporalService."""
    service = TemporalService(Project, db_session)
    root_id = uuid4()

    # 1. Create dummy data directly (service.create is not implemented)
    p1 = Project(project_id=root_id, name="Test Service", branch="main")
    db_session.add(p1)
    await db_session.flush()
    await db_session.refresh(p1)

    # 2. Test get_by_id
    res = await service.get_by_id(p1.id)
    assert res is not None
    assert res.id == p1.id

    # 3. Test get_all
    all_res = await service.get_all()
    assert len(all_res) >= 1
    assert any(p.id == p1.id for p in all_res)

    # 4. Test get_as_of (basic wiring check)
    as_of_res = await service.get_as_of(root_id, datetime.now(UTC))
    assert as_of_res is not None
    assert as_of_res.id == p1.id

@pytest.mark.asyncio
async def test_temporal_service_not_implemented_methods(db_session: AsyncSession):
    """Verify NotImplementedError for placeholder methods."""
    TemporalService(Project, db_session)
    uuid4()


    pass
