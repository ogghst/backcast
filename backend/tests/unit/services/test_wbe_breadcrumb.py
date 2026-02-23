from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.versioning.enums import BranchMode
from app.services.project import ProjectService
from app.services.wbe import WBEService


class TestWBEBreadcrumb:
    @pytest.mark.asyncio
    async def test_breadcrumb_ancestors_on_mixed_branches(
        self, db_session: AsyncSession
    ):
        """Test that get_breadcrumb correctly traverses ancestors across branches.

        Structure:
        Project (main)
          -> L1 WBE (main)
             -> L2 WBE (BR-FEAT)
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

        # 4. Fetch breadcrumb for L2 in MERGE mode
        breadcrumb = await wbe_service.get_breadcrumb(
            l2_id, branch="BR-FEAT", branch_mode=BranchMode.MERGE
        )

        # Assertions
        assert breadcrumb["project"]["code"] == "PRJ-001"

        # Path should contain both L1 and L2
        path = breadcrumb["wbe_path"]
        assert len(path) == 2
        assert path[0]["code"] == "L1"
        assert path[1]["code"] == "L2"
        assert path[1]["wbe_id"] == l2_id
