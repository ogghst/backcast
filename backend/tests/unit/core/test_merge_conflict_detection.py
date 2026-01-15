"""Tests for merge conflict detection in BranchableService.

Test module for detecting merge conflicts when source and target branches
have diverged with incompatible changes.
"""
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.branching.exceptions import MergeConflictError
from app.core.branching.service import BranchableService
from app.core.branching.commands import (
    CreateBranchCommand,
    UpdateCommand,
)
from app.core.versioning.commands import CreateVersionCommand
from app.models.domain.project import Project


class TestMergeConflictDetection:
    """Test suite for merge conflict detection."""

    @pytest.mark.asyncio
    async def test_detect_merge_conflicts_when_both_branches_modified(self, db_session: AsyncSession):
        """Test conflict detection when both source and target modified since divergence."""
        root_id = uuid4()
        actor_id = uuid4()

        # 1. Create initial version on main
        create_cmd = CreateVersionCommand(
            entity_class=Project,
            root_id=root_id,
            actor_id=actor_id,
            project_id=root_id,
            code="PROJ-001",
            name="Original Name",
            branch="main",
        )
        v1_main = await create_cmd.execute(db_session)

        # 2. Create feature branch from main
        branch_cmd = CreateBranchCommand(
            entity_class=Project,
            root_id=root_id,
            actor_id=actor_id,
            new_branch="co-123",
            from_branch="main",
        )
        await branch_cmd.execute(db_session)

        # 3. Modify main branch (creating divergence)
        update_main_cmd = UpdateCommand(
            entity_class=Project,
            root_id=root_id,
            actor_id=actor_id,
            updates={"name": "Main Modified"},
            branch="main",
        )
        v2_main = await update_main_cmd.execute(db_session)

        # 4. Modify feature branch (creating conflict)
        update_feature_cmd = UpdateCommand(
            entity_class=Project,
            root_id=root_id,
            actor_id=actor_id,
            updates={"name": "Feature Modified"},
            branch="co-123",
        )
        v2_feature = await update_feature_cmd.execute(db_session)

        # 5. Detect conflicts using BranchableService
        service = BranchableService(Project, db_session)
        conflicts = await service._detect_merge_conflicts(
            root_id=root_id,
            source_branch="co-123",
            target_branch="main",
        )

        # Assertions: Should detect conflict on 'name' field
        assert len(conflicts) > 0
        assert conflicts[0]["entity_type"] == "Project"
        assert conflicts[0]["entity_id"] == str(root_id)
        assert conflicts[0]["field"] == "name"
        assert conflicts[0]["source_branch"] == "co-123"
        assert conflicts[0]["target_branch"] == "main"
        assert conflicts[0]["source_value"] == "Feature Modified"
        assert conflicts[0]["target_value"] == "Main Modified"

    @pytest.mark.asyncio
    async def test_no_conflicts_when_only_source_modified(self, db_session: AsyncSession):
        """Test no conflicts when only source branch has changes."""
        root_id = uuid4()
        actor_id = uuid4()

        # 1. Create initial version on main
        create_cmd = CreateVersionCommand(
            entity_class=Project,
            root_id=root_id,
            actor_id=actor_id,
            project_id=root_id,
            code="PROJ-001",
            name="Original",
            branch="main",
        )
        await create_cmd.execute(db_session)

        # 2. Create feature branch
        branch_cmd = CreateBranchCommand(
            entity_class=Project,
            root_id=root_id,
            actor_id=actor_id,
            new_branch="co-456",
            from_branch="main",
        )
        await branch_cmd.execute(db_session)

        # 3. Modify ONLY feature branch (no conflict)
        update_cmd = UpdateCommand(
            entity_class=Project,
            root_id=root_id,
            actor_id=actor_id,
            updates={"name": "Feature Update"},
            branch="co-456",
        )
        await update_cmd.execute(db_session)

        # 4. Detect conflicts
        service = BranchableService(Project, db_session)
        conflicts = await service._detect_merge_conflicts(
            root_id=root_id,
            source_branch="co-456",
            target_branch="main",
        )

        # Assertions: No conflicts since target hasn't changed
        assert len(conflicts) == 0

    @pytest.mark.asyncio
    async def test_no_conflicts_when_different_fields_modified(self, db_session: AsyncSession):
        """Test no conflicts when branches modified different fields."""
        root_id = uuid4()
        actor_id = uuid4()

        # 1. Create initial version
        create_cmd = CreateVersionCommand(
            entity_class=Project,
            root_id=root_id,
            actor_id=actor_id,
            project_id=root_id,
            code="PROJ-001",
            name="Original",
            description="Original Description",
            branch="main",
        )
        await create_cmd.execute(db_session)

        # 2. Create feature branch
        branch_cmd = CreateBranchCommand(
            entity_class=Project,
            root_id=root_id,
            actor_id=actor_id,
            new_branch="co-789",
            from_branch="main",
        )
        await branch_cmd.execute(db_session)

        # 3. Modify main: change name
        update_main = UpdateCommand(
            entity_class=Project,
            root_id=root_id,
            actor_id=actor_id,
            updates={"name": "Main Name Change"},
            branch="main",
        )
        await update_main.execute(db_session)

        # 4. Modify feature: change description (different field)
        update_feature = UpdateCommand(
            entity_class=Project,
            root_id=root_id,
            actor_id=actor_id,
            updates={"description": "Feature Description Change"},
            branch="co-789",
        )
        await update_feature.execute(db_session)

        # 5. Detect conflicts
        service = BranchableService(Project, db_session)
        conflicts = await service._detect_merge_conflicts(
            root_id=root_id,
            source_branch="co-789",
            target_branch="main",
        )

        # Assertions: No conflicts since different fields were modified
        # (This is the "no-conflict merge" case)
        assert len(conflicts) == 0

    @pytest.mark.asyncio
    async def test_no_conflicts_for_new_branch(self, db_session: AsyncSession):
        """Test no conflicts when merging a newly created branch with no changes."""
        root_id = uuid4()
        actor_id = uuid4()

        # 1. Create on main
        create_cmd = CreateVersionCommand(
            entity_class=Project,
            root_id=root_id,
            actor_id=actor_id,
            project_id=root_id,
            code="PROJ-001",
            name="Main Project",
            branch="main",
        )
        await create_cmd.execute(db_session)

        # 2. Create feature branch but DON'T modify it
        branch_cmd = CreateBranchCommand(
            entity_class=Project,
            root_id=root_id,
            actor_id=actor_id,
            new_branch="co-new",
            from_branch="main",
        )
        await branch_cmd.execute(db_session)

        # 3. Detect conflicts (no changes on feature branch)
        service = BranchableService(Project, db_session)
        conflicts = await service._detect_merge_conflicts(
            root_id=root_id,
            source_branch="co-new",
            target_branch="main",
        )

        # Assertions: No conflicts since feature branch hasn't diverged
        assert len(conflicts) == 0
