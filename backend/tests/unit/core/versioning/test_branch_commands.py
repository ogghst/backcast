from datetime import UTC, datetime
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
            project_id=root_id,
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
            Project.project_id == root_id,
            Project.branch == "main",
            Project.deleted_at.is_(None),
            func.upper(Project.valid_time).is_(None),
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
            entity_class=Project,
            root_id=root_id,
            actor_id=actor_id,
            updates={"name": "V2"},
            branch="main",
        )
        v2 = await update_cmd.execute(db_session)
        v2_id = v2.id

        # 2. Revert v2 -> v1 (implicit parent)
        revert_cmd = RevertCommand(
            entity_class=Project, root_id=root_id, actor_id=actor_id, branch="main"
        )
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
            entity_class=Project,
            root_id=root_id,
            actor_id=actor_id,
            updates={"name": "V2"},
            branch="main",
        )
        await update_cmd.execute(db_session)

        update_cmd_2 = UpdateCommand(
            entity_class=Project,
            root_id=root_id,
            actor_id=actor_id,
            updates={"name": "V3"},
            branch="main",
        )
        v3 = await update_cmd_2.execute(db_session)
        v3_id = v3.id

        # Revert V3 -> V1 explicitly
        revert_cmd = RevertCommand(
            entity_class=Project,
            root_id=root_id,
            actor_id=actor_id,
            branch="main",
            to_version_id=v1_id,
        )
        reverted = await revert_cmd.execute(db_session)

        assert reverted.name == "V1"
        assert reverted.parent_id == v3_id  # History continues from V3
        assert reverted.branch == "main"

    @pytest.mark.asyncio
    async def test_update_command_with_control_date_no_duplicates(
        self, db_session: AsyncSession
    ):
        """Test that update with control_date does NOT create duplicate rows.

        Regression test for bug where UpdateCommand would create a remainder row
        via clone() and also close the current row, resulting in duplicate
        rows with identical data.

        EVCS Pattern: When control_date > current_lower, the current row should
        be modified in-place to become the remainder, not cloned.
        """
        root_id = uuid4()
        actor_id = uuid4()

        # 1. Create initial version at T0
        t0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
        create_cmd = CreateVersionCommand(
            entity_class=Project,
            root_id=root_id,
            actor_id=actor_id,
            control_date=t0,
            project_id=root_id,
            code="PROJ-DUP-TEST",
            name="Initial Version",
            branch="main",
        )
        v1 = await create_cmd.execute(db_session)
        v1_id = v1.id
        await db_session.commit()

        # 2. Update with control_date > T0 (should create remainder)
        # Set control_date to 2 weeks after initial version
        t1 = datetime(2026, 1, 15, 12, 0, 0, tzinfo=UTC)
        update_cmd = UpdateCommand(
            entity_class=Project,
            root_id=root_id,
            actor_id=actor_id,
            updates={"name": "Updated Version"},
            branch="main",
            control_date=t1,
        )
        v2 = await update_cmd.execute(db_session)
        v2_id = v2.id
        await db_session.commit()

        # 3. Fetch ALL versions for this root_id to verify no duplicates
        stmt_all = (
            select(Project)
            .where(
                Project.project_id == root_id,
                Project.branch == "main",
                Project.deleted_at.is_(None),
            )
            .order_by(Project.transaction_time.asc())
        )
        result = await db_session.execute(stmt_all)
        all_versions = list(result.scalars().all())

        # CRITICAL ASSERTION: Should have exactly 2 versions, not 3
        # - v1 modified in-place as remainder [T0, T1)
        # - v2 as new version [T1, infinity)
        assert len(all_versions) == 2, (
            f"Expected exactly 2 versions after update with control_date, "
            f"but found {len(all_versions)}. This indicates duplicate row creation bug. "
            f"Version IDs: {[v.id for v in all_versions]}"
        )

        # 4. Verify remainder (v1 modified in-place)
        remainder = all_versions[0]
        assert remainder.id == v1_id, (
            "Remainder should be the original v1 modified in-place"
        )
        assert remainder.name == "Initial Version", (
            "Remainder should keep original data"
        )
        assert remainder.valid_time.lower == t0, (
            "Remainder valid_time should start at T0"
        )
        assert remainder.valid_time.upper == t1, "Remainder valid_time should end at T1"
        assert remainder.transaction_time.upper is not None, (
            "Remainder transaction_time should be closed"
        )

        # 5. Verify new version (v2)
        new_version = all_versions[1]
        assert new_version.id == v2_id, "New version should be v2"
        assert new_version.name == "Updated Version", (
            "New version should have updated data"
        )
        assert new_version.valid_time.lower == t1, (
            "New version valid_time should start at T1"
        )
        assert new_version.valid_time.upper is None, (
            "New version valid_time should be open-ended"
        )
        assert new_version.parent_id == v1_id, "New version should parent to remainder"

        # 6. Verify temporal ranges don't overlap (EVCS requirement)
        for i in range(len(all_versions) - 1):
            v_current = all_versions[i]
            v_next = all_versions[i + 1]
            assert v_current.valid_time.upper == v_next.valid_time.lower, (
                f"Version {i} valid_time.upper should equal version {i + 1} valid_time.lower"
            )

        # 7. Verify no duplicate valid_time ranges
        valid_ranges = [(v.valid_time.lower, v.valid_time.upper) for v in all_versions]
        assert len(valid_ranges) == len(set(valid_ranges)), (
            "All versions should have unique valid_time ranges. "
            "Duplicate ranges indicate the bug where clone() creates duplicates."
        )

        # 8. Verify no duplicate transaction_time ranges
        tx_ranges = [
            (v.transaction_time.lower, v.transaction_time.upper) for v in all_versions
        ]
        assert len(tx_ranges) == len(set(tx_ranges)), (
            "All versions should have unique transaction_time ranges. "
            "Duplicate ranges indicate incorrect closure handling."
        )

    @pytest.mark.asyncio
    async def test_update_command_with_control_date_at_boundary(
        self, db_session: AsyncSession
    ):
        """Test update with control_date == current_lower (no remainder needed).

        When control_date equals the current version's valid_time lower bound,
        the update should completely replace the current version without
        creating a remainder.

        The closed version becomes an empty range which is the correct EVCS
        behavior for Time Machine mode updates.
        """
        root_id = uuid4()
        actor_id = uuid4()

        # 1. Create initial version
        t0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
        create_cmd = CreateVersionCommand(
            entity_class=Project,
            root_id=root_id,
            actor_id=actor_id,
            control_date=t0,
            project_id=root_id,
            code="PROJ-BOUNDARY",
            name="Time Machine Update",
            branch="main",
        )
        v1 = await create_cmd.execute(db_session)
        v1_id = v1.id
        await db_session.commit()

        # 2. Update with control_date == T0 (Time Machine mode)
        # This should replace the version starting from the same time
        update_cmd = UpdateCommand(
            entity_class=Project,
            root_id=root_id,
            actor_id=actor_id,
            updates={"name": "Replaced from T0"},
            branch="main",
            control_date=t0,  # Same as original lower bound
        )
        await update_cmd.execute(db_session)
        await db_session.commit()

        # 3. Verify exactly 2 versions exist
        stmt_all = (
            select(Project)
            .where(
                Project.project_id == root_id,
                Project.branch == "main",
                Project.deleted_at.is_(None),
            )
            .order_by(Project.transaction_time.asc())
        )
        result = await db_session.execute(stmt_all)
        all_versions = list(result.scalars().all())

        assert len(all_versions) == 2, (
            f"Expected exactly 2 versions for boundary update, found {len(all_versions)}"
        )

        # 4. Verify the old version exists but is closed
        # When closed at same time as lower bound, it becomes an empty range
        # In PostgreSQL TSTZRANGE, empty ranges have None for both bounds
        closed_version = all_versions[0]
        assert closed_version.id == v1_id, "First version should be the original v1"
        assert closed_version.transaction_time.upper is not None, (
            "Original v1 transaction_time should be closed"
        )
        # Empty range - both bounds are None in PostgreSQL
        # The Range object has an `empty` attribute
        assert closed_version.valid_time.empty, (
            "Closed version should have empty valid_time range"
        )

        # 5. Verify v2 starts from T0 (same boundary)
        new_v2 = all_versions[1]
        assert new_v2.valid_time.lower == t0, "New version should start at T0"
        assert new_v2.name == "Replaced from T0"
        assert new_v2.parent_id == v1_id

    @pytest.mark.asyncio
    async def test_update_command_normal_no_control_date(
        self, db_session: AsyncSession
    ):
        """Test normal update without control_date (current timestamp).

        Verifies that updates without an explicit control_date work correctly
        and don't create duplicate rows.
        """
        root_id = uuid4()
        actor_id = uuid4()

        # 1. Create initial version
        create_cmd = CreateVersionCommand(
            entity_class=Project,
            root_id=root_id,
            actor_id=actor_id,
            project_id=root_id,
            code="PROJ-NORMAL",
            name="Normal Update",
            branch="main",
        )
        v1 = await create_cmd.execute(db_session)
        v1_id = v1.id
        await db_session.commit()

        # 2. Normal update without control_date
        update_cmd = UpdateCommand(
            entity_class=Project,
            root_id=root_id,
            actor_id=actor_id,
            updates={"name": "Updated Normally"},
            branch="main",
        )
        await update_cmd.execute(db_session)
        await db_session.commit()

        # 3. Verify exactly 2 versions exist
        stmt_all = (
            select(Project)
            .where(
                Project.project_id == root_id,
                Project.branch == "main",
                Project.deleted_at.is_(None),
            )
            .order_by(Project.transaction_time.asc())
        )
        result = await db_session.execute(stmt_all)
        all_versions = list(result.scalars().all())

        assert len(all_versions) == 2, (
            f"Expected exactly 2 versions for normal update, found {len(all_versions)}"
        )

        # 4. Verify v1 was closed
        closed_v1 = all_versions[0]
        assert closed_v1.id == v1_id
        assert closed_v1.valid_time.upper is not None, "v1 should be closed"
        assert closed_v1.transaction_time.upper is not None, (
            "v1 transaction_time should be closed"
        )

        # 5. Verify v2 is the new version
        new_v2 = all_versions[1]
        assert new_v2.name == "Updated Normally"
        assert new_v2.parent_id == v1_id
