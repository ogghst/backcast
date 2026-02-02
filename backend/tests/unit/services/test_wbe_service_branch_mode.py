"""Unit tests for WBEService branch mode filtering.

Tests the DISTINCT ON strategy for MERGE mode vs STRICT (isolated) mode.
"""

from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.versioning.enums import BranchMode
from app.services.wbe import WBEService


class TestWBEServiceBranchMode:
    """Test WBEService branch mode filtering for merged vs isolated views."""

    @pytest.mark.asyncio
    async def test_isolated_mode_returns_only_branch_entities(
        self, db_session: AsyncSession
    ) -> None:
        """Isolated mode returns only entities from the specified branch.

        This is the simplest test - verifies current STRICT behavior works.
        """
        service = WBEService(db_session)
        project_id = uuid4()
        actor_id = uuid4()

        # Arrange: Create 5 WBEs on main branch using create_root
        for i in range(5):
            await service.create_root(
                root_id=uuid4(),
                actor_id=actor_id,
                branch="main",
                project_id=project_id,
                code=f"MAIN-{i}",
                name=f"Main WBE {i}",
                level=1,
            )

        # Arrange: Create 2 WBEs on co-123 branch (different root_ids)
        for i in range(2):
            await service.create_root(
                root_id=uuid4(),
                actor_id=actor_id,
                branch="co-123",
                project_id=project_id,
                code=f"CO-{i}",
                name=f"CO WBE {i}",
                level=1,
            )

        # Act: Query with isolated mode (STRICT)
        wbes, total = await service.get_wbes(
            branch="co-123",
            branch_mode=BranchMode.STRICT,
        )

        # Assert: Should return only the 2 WBEs from co-123 branch
        assert len(wbes) == 2, f"Expected 2 WBEs from co-123, got {len(wbes)}"
        assert total == 2
        for wbe in wbes:
            assert wbe.branch == "co-123", f"Expected co-123, got {wbe.branch}"
            assert wbe.code.startswith("CO-"), f"Expected CO- prefix, got {wbe.code}"

    @pytest.mark.asyncio
    async def test_merged_mode_includes_unmodified_main_entities(
        self, db_session: AsyncSession
    ) -> None:
        """Merged mode includes main branch entities not modified in current branch.

        Tests DISTINCT ON logic:
        - Main has 5 WBEs
        - co-123 has 2 WBEs (different root_ids from main)
        - Merged query should return 7 total (2 from co-123 + 5 from main)
        """
        service = WBEService(db_session)
        project_id = uuid4()
        actor_id = uuid4()

        # Arrange: Create 5 WBEs on main branch
        for i in range(5):
            await service.create_root(
                root_id=uuid4(),
                actor_id=actor_id,
                branch="main",
                project_id=project_id,
                code=f"MAIN-{i}",
                name=f"Main WBE {i}",
                level=1,
            )

        # Arrange: Create 2 WBEs on co-123 branch (different root_ids)
        for i in range(2):
            await service.create_root(
                root_id=uuid4(),
                actor_id=actor_id,
                branch="co-123",
                project_id=project_id,
                code=f"CO-{i}",
                name=f"CO WBE {i}",
                level=1,
            )

        # Act: Query with merged mode
        wbes, total = await service.get_wbes(
            branch="co-123",
            branch_mode=BranchMode.MERGE,
        )

        # Assert: Should return all 7 WBEs (2 from co-123 + 5 from main)
        assert len(wbes) == 7, (
            f"Expected 7 total WBEs (5 main + 2 co-123), got {len(wbes)}"
        )
        assert total == 7

        # Verify branch distribution
        co_wbes = [w for w in wbes if w.branch == "co-123"]
        main_wbes = [w for w in wbes if w.branch == "main"]
        assert len(co_wbes) == 2, f"Expected 2 co-123 WBEs, got {len(co_wbes)}"
        assert len(main_wbes) == 5, f"Expected 5 main WBEs, got {len(main_wbes)}"

    @pytest.mark.asyncio
    async def test_distinct_on_prioritizes_branch_over_main(
        self, db_session: AsyncSession
    ) -> None:
        """Merged mode prioritizes branch version over main when same root_id exists.

        Tests DISTINCT ON with branch precedence:
        - Create WBE with root_id=X on main
        - Create WBE with same root_id=X on co-123 (modified version)
        - Merged query should return only the co-123 version (X appears once)
        """
        service = WBEService(db_session)
        project_id = uuid4()
        actor_id = uuid4()

        # Arrange: Create WBE on main branch
        root_id = uuid4()
        await service.create_root(
            root_id=root_id,
            actor_id=actor_id,
            branch="main",
            project_id=project_id,
            code="W001",
            name="Original WBE",
            level=1,
        )

        # Arrange: Create WBE with same root_id on co-123 branch (modified)
        await service.create_root(
            root_id=root_id,
            actor_id=actor_id,
            branch="co-123",
            project_id=project_id,
            code="W001",  # Same code
            name="Modified WBE",  # Different name
            level=2,  # Different level
        )

        # Act: Query with merged mode
        wbes, total = await service.get_wbes(
            branch="co-123",
            branch_mode=BranchMode.MERGE,
        )

        # Assert: Should return 1 WBE (the co-123 version takes precedence)
        assert len(wbes) == 1, f"Expected 1 WBE (co-123 version), got {len(wbes)}"
        assert total == 1

        result = wbes[0]
        assert result.wbe_id == root_id, "Should have the shared root_id"
        assert result.branch == "co-123", f"Expected co-123 branch, got {result.branch}"
        assert result.name == "Modified WBE", "Should have co-123 version data"
        assert result.level == 2, "Should have co-123 version data"

    @pytest.mark.asyncio
    async def test_deleted_entities_not_merged_from_main(
        self, db_session: AsyncSession
    ) -> None:
        """Entities deleted on branch should NOT fall back to main.

        Tests merge behavior with soft deletes:
        - Create WBE on main
        - Delete WBE on co-123 branch
        - Merged query should NOT return the main version (respect deletion)
        """
        service = WBEService(db_session)
        project_id = uuid4()
        actor_id = uuid4()

        # Arrange: Create WBE on main branch
        root_id = uuid4()
        await service.create_root(
            root_id=root_id,
            actor_id=actor_id,
            branch="main",
            project_id=project_id,
            code="W001",
            name="Main WBE",
            level=1,
        )

        # Arrange: Create and then delete WBE on co-123 branch
        await service.create_root(
            root_id=root_id,
            actor_id=actor_id,
            branch="co-123",
            project_id=project_id,
            code="W001",
            name="CO WBE",
            level=1,
        )

        await service.soft_delete(
            root_id=root_id,
            actor_id=actor_id,
            branch="co-123",
        )

        # Act: Query with merged mode
        wbes, total = await service.get_wbes(
            branch="co-123",
            branch_mode=BranchMode.MERGE,
        )

        # Assert: Should return 0 WBEs (deleted on branch, should not fall back)
        assert len(wbes) == 0, f"Expected 0 WBEs (deleted), got {len(wbes)}"
        assert total == 0
