from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.branching.commands import (
    CreateBranchCommand,
    MergeBranchCommand,
    RevertCommand,
    UpdateCommand,
)
from app.core.versioning.commands import CreateVersionCommand
from app.models.domain.project import Project


class TestBranchCommands:
    """Test suite for Branchable Entity Commands."""

    @pytest.mark.asyncio
    async def test_create_branch_command(self, db_session: AsyncSession):
        """Test creating a new branch from main."""
        root_id = uuid4()
        actor_id = uuid4()

        # 1. Create initial version on main
        create_cmd = CreateVersionCommand(
            entity_class=Project,
            root_id=root_id,
            actor_id=actor_id,
            project_id=str(root_id),
            code="PROJ-001",
            name="Main Project",
            branch="main",
        )
        v1 = await create_cmd.execute(db_session)
        assert v1.branch == "main"

        # 2. Create new branch 'feature/redesign' from 'main'
        branch_cmd = CreateBranchCommand(
            entity_class=Project,
            root_id=root_id,
            actor_id=actor_id,
            new_branch="feature/redesign",
            from_branch="main",
        )
        v2 = await branch_cmd.execute(db_session)

        assert v2.branch == "feature/redesign"
        assert v2.project_id == root_id
        assert v2.parent_id == v1.id
        assert v2.name == "Main Project"  # Should be cloned

        # 3. Verify main still exists and is separate
        stmt = select(Project).where(
            Project.project_id == str(root_id),
            Project.branch == "main",
            Project.deleted_at.is_(None),
            func.upper(Project.valid_time).is_(None),  # type: ignore
        )
        main_current = (await db_session.execute(stmt)).scalar_one()
        assert main_current.id == v1.id

    @pytest.mark.asyncio
    async def test_update_command_on_branch(self, db_session: AsyncSession):
        """Test updating an entity on a specific branch."""
        root_id = uuid4()
        actor_id = uuid4()

        # 1. Create v1 on feature branch
        create_cmd = CreateVersionCommand(
            entity_class=Project,
            root_id=root_id,
            actor_id=actor_id,
            project_id=root_id,
            code="PROJ-002",
            name="Initial",
            branch="feature/x",
        )
        v1 = await create_cmd.execute(db_session)

        # 2. Update on feature branch
        v1_id = v1.id  # Capture ID before it expires
        update_cmd = UpdateCommand(
            entity_class=Project,
            root_id=root_id,
            actor_id=actor_id,
            updates={"name": "Updated"},
            branch="feature/x",
        )
        v2 = await update_cmd.execute(db_session)

        # Assertions
        assert v2.id != v1_id
        assert v2.name == "Updated"
        assert v2.branch == "feature/x"
        assert v2.parent_id == v1_id

        # Verify v1 is closed on this branch
        # Note: v1 itself isn't modified in object, but DB state is.
        # We'd need to fetch history to verify closing, covered by integration tests.

    @pytest.mark.asyncio
    async def test_merge_branch_command(self, db_session: AsyncSession):
        """Test merging feature branch into main."""
        root_id = uuid4()
        actor_id = uuid4()

        # 1. Setup: Main v1 -> Feature v2 (Updated)
        # Main v1
        create_cmd = CreateVersionCommand(
            entity_class=Project,
            root_id=root_id,
            actor_id=actor_id,
            project_id=root_id,
            code="PROJ-003",
            name="Main V1",
            branch="main",
        )
        v1 = await create_cmd.execute(db_session)
        v1_id = v1.id

        # Feature Branch from Main
        branch_cmd = CreateBranchCommand(
            entity_class=Project,
            root_id=root_id,
            actor_id=actor_id,
            new_branch="feature/merge",
            from_branch="main",
        )
        await branch_cmd.execute(db_session)

        # Update Feature (v3)
        update_cmd = UpdateCommand(
            entity_class=Project,
            root_id=root_id,
            actor_id=actor_id,
            updates={"name": "Feature Updated"},
            branch="feature/merge",
        )
        v3 = await update_cmd.execute(db_session)
        v3_id = v3.id

        # 2. Merge Feature -> Main
        # Main is still at v1.
        merge_cmd = MergeBranchCommand(
            entity_class=Project,
            root_id=root_id,
            actor_id=actor_id,
            source_branch="feature/merge",
            target_branch="main",
        )
        merged = await merge_cmd.execute(db_session)

        # Assertions
        assert merged.branch == "main"
        assert merged.name == "Feature Updated"  # Content from source
        assert merged.parent_id == v1_id  # Linked to Main's previous tip
        assert merged.merge_from_branch == "feature/merge"  # Audit trail
        assert merged.id != v3_id  # New version created

    @pytest.mark.asyncio
    async def test_revert_command(self, db_session: AsyncSession):
        """Test reverting changes."""
        root_id = uuid4()
        actor_id = uuid4()

        # 1. Setup: v1 -> v2 -> v3 (on main)
        create_cmd = CreateVersionCommand(
            entity_class=Project,
            root_id=root_id,
            actor_id=actor_id,
            project_id=root_id,
            code="PROJ-004",
            name="V1",
            branch="main",
        )
        v1 = await create_cmd.execute(db_session)
        v1_id = v1.id

        update_cmd = UpdateCommand(
            entity_class=Project, root_id=root_id, actor_id=actor_id, updates={"name": "V2"}, branch="main"
        )
        v2 = await update_cmd.execute(db_session)
        v2_id = v2.id

        # 2. Revert v2 -> v1 (implicit parent)
        revert_cmd = RevertCommand(entity_class=Project, root_id=root_id, actor_id=actor_id, branch="main")
        reverted = await revert_cmd.execute(db_session)

        assert reverted.name == "V1"
        assert reverted.parent_id == v2_id  # Linear history
        assert reverted.id != v1_id  # New version

    @pytest.mark.asyncio
    async def test_revert_to_specific_version(self, db_session: AsyncSession):
        """Test reverting to a specific historic version."""
        root_id = uuid4()
        actor_id = uuid4()

        # v1 -> v2 -> v3
        create_cmd = CreateVersionCommand(
            entity_class=Project,
            root_id=root_id,
            actor_id=actor_id,
            project_id=root_id,
            code="PROJ-005",
            name="V1",
            branch="main",
        )
        v1 = await create_cmd.execute(db_session)
        v1_id = v1.id

        update_cmd = UpdateCommand(
            entity_class=Project, root_id=root_id, actor_id=actor_id, updates={"name": "V2"}, branch="main"
        )
        await update_cmd.execute(db_session)

        update_cmd_2 = UpdateCommand(
            entity_class=Project, root_id=root_id, actor_id=actor_id, updates={"name": "V3"}, branch="main"
        )
        v3 = await update_cmd_2.execute(db_session)
        v3_id = v3.id

        # Revert V3 -> V1 explicitly
        revert_cmd = RevertCommand(
            entity_class=Project, root_id=root_id, actor_id=actor_id, branch="main", to_version_id=v1_id
        )
        reverted = await revert_cmd.execute(db_session)

        assert reverted.name == "V1"
        assert reverted.parent_id == v3_id  # History continues from V3
        assert reverted.branch == "main"
