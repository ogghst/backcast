"""Tests for branch lock enforcement in BranchableService."""

from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.branching.exceptions import BranchLockedException
from app.core.branching.service import BranchableService
from app.models.domain.branch import Branch
from app.models.domain.project import Project
from app.models.domain.wbe import WBE
from app.services.branch_service import BranchService


@pytest.mark.asyncio
class TestBranchLockEnforcement:
    """Test that branch locks are enforced for all branchable entities."""

    async def test_update_locked_branch_raises_exception(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Test that updating an entity on a locked branch raises BranchLockedException."""
        # Arrange: Create a project and WBE on main branch
        test_user_id = uuid4()

        # Create project
        project = Project(
            project_id=uuid4(),
            code="TEST-PROJ",
            name="Test Project",
            created_by=test_user_id,
        )
        db_session.add(project)
        await db_session.commit()
        await db_session.refresh(project)
        project_id = project.project_id

        wbe_service = BranchableService(WBE, db_session)
        branch_service = BranchService(db_session)

        # Create initial WBE on main branch
        wbe_root_id = uuid4()
        await wbe_service.create_root(
            root_id=wbe_root_id,
            actor_id=test_user_id,
            branch="main",
            project_id=project_id,
            code="WBE-001",
            name="Test WBE",
        )

        # Create a change order branch
        co_branch = "co-001"
        await wbe_service.create_branch(
            root_id=wbe_root_id,
            actor_id=test_user_id,
            new_branch=co_branch,
            from_branch="main",
        )

        # Create branch entry in branches table
        new_branch = Branch(
            name=co_branch,
            project_id=project_id,
            created_by=test_user_id,
        )
        db_session.add(new_branch)
        await db_session.commit()

        # Lock the branch
        await branch_service.lock(co_branch, project_id)

        # Act & Assert: Try to update WBE on locked branch
        with pytest.raises(BranchLockedException) as exc_info:
            await wbe_service.update(
                root_id=wbe_root_id,
                actor_id=test_user_id,
                branch=co_branch,
                name="Updated WBE",  # This should fail
            )

        # Verify exception details
        assert exc_info.value.branch == co_branch
        assert exc_info.value.entity_type == "WBE"
        assert "locked" in str(exc_info.value).lower()

    async def test_delete_locked_branch_raises_exception(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Test that deleting an entity on a locked branch raises BranchLockedException."""
        # Arrange: Create a project and WBE on main branch
        test_user_id = uuid4()

        # Create project
        project = Project(
            project_id=uuid4(),
            code="TEST-PROJ",
            name="Test Project",
            created_by=test_user_id,
        )
        db_session.add(project)
        await db_session.commit()
        await db_session.refresh(project)
        project_id = project.project_id

        wbe_service = BranchableService(WBE, db_session)
        branch_service = BranchService(db_session)

        # Create initial WBE on main branch
        wbe_root_id = uuid4()
        await wbe_service.create_root(
            root_id=wbe_root_id,
            actor_id=test_user_id,
            branch="main",
            project_id=project_id,
            code="WBE-002",
            name="Test WBE",
        )

        # Create a change order branch
        co_branch = "co-002"
        await wbe_service.create_branch(
            root_id=wbe_root_id,
            actor_id=test_user_id,
            new_branch=co_branch,
            from_branch="main",
        )

        # Create branch entry in branches table
        new_branch = Branch(
            name=co_branch,
            project_id=project_id,
            created_by=test_user_id,
        )
        db_session.add(new_branch)
        await db_session.commit()

        # Lock the branch
        await branch_service.lock(co_branch, project_id)

        # Act & Assert: Try to delete WBE on locked branch
        with pytest.raises(BranchLockedException) as exc_info:
            await wbe_service.soft_delete(
                root_id=wbe_root_id,
                actor_id=test_user_id,
                branch=co_branch,
            )

        # Verify exception details
        assert exc_info.value.branch == co_branch
        assert "locked" in str(exc_info.value).lower()

    async def test_create_on_locked_branch_raises_exception(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Test that creating an entity on a locked branch raises BranchLockedException."""
        # Arrange: Create a project and lock a branch
        test_user_id = uuid4()

        # Create project
        project = Project(
            project_id=uuid4(),
            code="TEST-PROJ",
            name="Test Project",
            created_by=test_user_id,
        )
        db_session.add(project)
        await db_session.commit()
        await db_session.refresh(project)
        project_id = project.project_id

        wbe_service = BranchableService(WBE, db_session)
        branch_service = BranchService(db_session)

        # Create a branch for the project
        co_branch = "co-003"
        new_branch = Branch(
            name=co_branch,
            project_id=project_id,
            created_by=test_user_id,
        )
        db_session.add(new_branch)
        await db_session.commit()

        # Lock the branch
        await branch_service.lock(co_branch, project_id)

        # Act & Assert: Try to create WBE on locked branch
        wbe_root_id = uuid4()
        with pytest.raises(BranchLockedException) as exc_info:
            await wbe_service.create_root(
                root_id=wbe_root_id,
                actor_id=test_user_id,
                branch=co_branch,
                project_id=project_id,
                code="WBE-003",
                name="Test WBE",
            )

        # Verify exception details
        assert exc_info.value.branch == co_branch
        assert "locked" in str(exc_info.value).lower()

    async def test_main_branch_never_locked(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Test that operations on main branch always succeed regardless of lock status."""
        # Arrange: Create a WBE on main branch
        test_user_id = uuid4()

        # Create project
        project = Project(
            project_id=uuid4(),
            code="TEST-PROJ",
            name="Test Project",
            created_by=test_user_id,
        )
        db_session.add(project)
        await db_session.commit()
        await db_session.refresh(project)
        project_id = project.project_id

        wbe_service = BranchableService(WBE, db_session)

        wbe_root_id = uuid4()
        await wbe_service.create_root(
            root_id=wbe_root_id,
            actor_id=test_user_id,
            branch="main",
            project_id=project_id,
            code="WBE-004",
            name="Test WBE",
        )

        # Even if main branch is somehow marked as locked (shouldn't happen),
        # operations should still succeed
        # Act: Update WBE on main branch
        updated_wbe = await wbe_service.update(
            root_id=wbe_root_id,
            actor_id=test_user_id,
            branch="main",
            name="Updated WBE",
        )

        # Assert: Should succeed
        assert updated_wbe.name == "Updated WBE"

    async def test_operations_succeed_on_unlocked_branch(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Test that operations succeed when branch is not locked."""
        # Arrange: Create a WBE on an unlocked branch
        test_user_id = uuid4()

        # Create project
        project = Project(
            project_id=uuid4(),
            code="TEST-PROJ",
            name="Test Project",
            created_by=test_user_id,
        )
        db_session.add(project)
        await db_session.commit()
        await db_session.refresh(project)
        project_id = project.project_id

        wbe_service = BranchableService(WBE, db_session)
        branch_service = BranchService(db_session)

        wbe_root_id = uuid4()
        await wbe_service.create_root(
            root_id=wbe_root_id,
            actor_id=test_user_id,
            branch="main",
            project_id=project_id,
            code="WBE-005",
            name="Test WBE",
        )

        # Create an unlocked branch
        co_branch = "co-004"
        await wbe_service.create_branch(
            root_id=wbe_root_id,
            actor_id=test_user_id,
            new_branch=co_branch,
            from_branch="main",
        )

        # Create branch entry in branches table
        new_branch = Branch(
            name=co_branch,
            project_id=project_id,
            created_by=test_user_id,
        )
        db_session.add(new_branch)
        await db_session.commit()

        # Ensure branch is unlocked
        branch = await branch_service.get_by_name_and_project(co_branch, project_id)
        if branch.locked:
            await branch_service.unlock(co_branch, project_id)

        # Act: Update WBE on unlocked branch
        updated_wbe = await wbe_service.update(
            root_id=wbe_root_id,
            actor_id=test_user_id,
            branch=co_branch,
            name="Updated WBE",
        )

        # Assert: Should succeed
        assert updated_wbe.name == "Updated WBE"
