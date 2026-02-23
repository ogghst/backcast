"""Test for WBE breadcrumb duplicate bug fix.

This test specifically checks that the breadcrumb doesn't contain duplicate entries
when WBEs exist on multiple branches.
"""
import pytest
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.wbe import WBEService
from app.services.project import ProjectService
from app.core.versioning.enums import BranchMode
from app.models.schemas.wbe import WBEUpdate


class TestWBEBreadcrumbDuplicates:
    @pytest.mark.asyncio
    async def test_breadcrumb_no_duplicates_with_multiple_branch_versions(
        self, db_session: AsyncSession
    ):
        """Test that breadcrumb doesn't contain duplicates when parent WBE exists on multiple branches.

        Structure:
        Project (main)
          -> L1 WBE (exists on both main and BR-FEAT - same wbe_id, different id)
             -> L2 WBE (BR-FEAT)

        Expected: Breadcrumb should have exactly 2 entries (L1, L2) with NO duplicates.
        Bug: Before fix, would get 3+ entries due to duplicate L1 from both branches.
        """
        wbe_service = WBEService(db_session)
        project_service = ProjectService(db_session)
        actor_id = uuid4()

        # 1. Create Project
        project = await project_service.create_root(
            root_id=uuid4(),
            actor_id=actor_id,
            branch="main",
            name="Test Project",
            code="PRJ-001",
        )

        # 2. Create L1 WBE on main
        l1_id = uuid4()
        await wbe_service.create_root(
            root_id=l1_id,
            actor_id=actor_id,
            branch="main",
            project_id=project.project_id,
            code="L1",
            name="Level 1",
            level=1,
        )

        # 3. Create L2 WBE on BR-FEAT (child of L1)
        l2_id = uuid4()
        await wbe_service.create_root(
            root_id=l2_id,
            actor_id=actor_id,
            branch="BR-FEAT",
            project_id=project.project_id,
            code="L2",
            name="Level 2",
            level=2,
            parent_wbe_id=l1_id,
        )

        # 4. Create ANOTHER version of L1 on BR-FEAT (same wbe_id, different version)
        # This simulates the scenario where a parent WBE is modified on a change order branch
        await wbe_service.update_wbe(
            wbe_id=l1_id,
            wbe_in=WBEUpdate(name="Level 1 (Modified on BR-FEAT)", branch="BR-FEAT"),
            actor_id=actor_id,
        )

        # 5. Fetch breadcrumb for L2 in MERGE mode
        breadcrumb = await wbe_service.get_breadcrumb(
            l2_id, branch="BR-FEAT", branch_mode=BranchMode.MERGE
        )

        # Assertions
        assert breadcrumb["project"]["code"] == "PRJ-001"

        # Path should contain both L1 and L2, with NO duplicates
        path = breadcrumb["wbe_path"]
        assert len(path) == 2, f"Expected 2 items in breadcrumb path, got {len(path)}: {[p['code'] for p in path]}"

        # Check no duplicate wbe_ids (this is the key test for the bug fix)
        wbe_ids = [p["wbe_id"] for p in path]
        assert len(wbe_ids) == len(set(wbe_ids)), f"Found duplicate wbe_ids in breadcrumb: {wbe_ids}"

        # Check no duplicate codes
        codes = [p["code"] for p in path]
        assert len(codes) == len(set(codes)), f"Found duplicate codes in breadcrumb: {codes}"

        # Verify expected order: L1 first, then L2
        assert path[0]["code"] == "L1"
        assert path[1]["code"] == "L2"
        assert path[1]["wbe_id"] == l2_id

    @pytest.mark.asyncio
    async def test_breadcrumb_three_level_hierarchy_no_duplicates(
        self, db_session: AsyncSession
    ):
        """Test breadcrumb with 3-level hierarchy where middle level exists on multiple branches.

        Structure:
        Project (main)
          -> L1 WBE (main)
             -> L2 WBE (exists on both main and BR-FEAT)
                -> L3 WBE (BR-FEAT)

        Expected: Breadcrumb should have exactly 3 entries (L1, L2, L3) with NO duplicates.
        """
        wbe_service = WBEService(db_session)
        project_service = ProjectService(db_session)
        actor_id = uuid4()

        # 1. Create Project
        project = await project_service.create_root(
            root_id=uuid4(),
            actor_id=actor_id,
            branch="main",
            name="Test Project",
            code="PRJ-002",
        )

        # 2. Create L1 WBE on main
        l1_id = uuid4()
        await wbe_service.create_root(
            root_id=l1_id,
            actor_id=actor_id,
            branch="main",
            project_id=project.project_id,
            code="L1",
            name="Level 1",
            level=1,
        )

        # 3. Create L2 WBE on main
        l2_id = uuid4()
        await wbe_service.create_root(
            root_id=l2_id,
            actor_id=actor_id,
            branch="main",
            project_id=project.project_id,
            code="L2",
            name="Level 2",
            level=2,
            parent_wbe_id=l1_id,
        )

        # 4. Create L3 WBE on BR-FEAT (child of L2)
        l3_id = uuid4()
        await wbe_service.create_root(
            root_id=l3_id,
            actor_id=actor_id,
            branch="BR-FEAT",
            project_id=project.project_id,
            code="L3",
            name="Level 3",
            level=3,
            parent_wbe_id=l2_id,
        )

        # 5. Modify L2 on BR-FEAT to create multiple versions
        await wbe_service.update_wbe(
            wbe_id=l2_id,
            wbe_in=WBEUpdate(name="Level 2 (Modified on BR-FEAT)", branch="BR-FEAT"),
            actor_id=actor_id,
        )

        # 6. Fetch breadcrumb for L3 in MERGE mode
        breadcrumb = await wbe_service.get_breadcrumb(
            l3_id, branch="BR-FEAT", branch_mode=BranchMode.MERGE
        )

        # Assertions
        path = breadcrumb["wbe_path"]
        assert len(path) == 3, f"Expected 3 items in breadcrumb path, got {len(path)}: {[p['code'] for p in path]}"

        # Check no duplicate wbe_ids
        wbe_ids = [p["wbe_id"] for p in path]
        assert len(wbe_ids) == len(set(wbe_ids)), f"Found duplicate wbe_ids in breadcrumb: {wbe_ids}"

        # Verify expected order: L1, L2, L3
        assert path[0]["code"] == "L1"
        assert path[1]["code"] == "L2"
        assert path[2]["code"] == "L3"
        assert path[2]["wbe_id"] == l3_id
