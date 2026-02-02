"""Integration tests for full Change Order merge workflow.

Tests the end-to-end merge of Change Orders with all associated
branchable entities (WBEs, CostElements).

Follows RED-GREEN-REFACTOR TDD methodology.
"""


from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain.wbe import WBE
from app.services.change_order_service import ChangeOrderService
from app.services.cost_element_service import CostElementService
from app.services.wbe import WBEService


@pytest.mark.usefixtures("db_session")
class TestChangeOrderFullMerge:
    """Integration test suite for full Change Order merge workflow."""

    @pytest.mark.asyncio
    async def test_merge_happy_path(
        self, db_session: AsyncSession
    ) -> None:
        """Test successful merge of CO with WBEs and CostElements.

        Expected: All entities merged from co-{code} branch to main branch.
        """
        # Arrange
        actor_id = uuid4()
        project_id = uuid4()
        co_id = uuid4()
        co_code = "123"

        co_service = ChangeOrderService(db_session)
        wbe_service = WBEService(db_session)
        ce_service = CostElementService(db_session)

        # Create CO on main branch
        await co_service.create_root(
            root_id=co_id,
            actor_id=actor_id,
            branch="main",
            code=co_code,
            title="Test CO",
            description="Test Change Order",
            project_id=project_id,
            status="Approved",
        )

        # Create WBEs on main branch first
        wbe1_id = uuid4()
        await wbe_service.create_root(
            root_id=wbe1_id,
            actor_id=actor_id,
            branch="main",
            project_id=project_id,
            code="1.1",
            name="Main WBE 1",
            level=1,
        )

        wbe2_id = uuid4()
        await wbe_service.create_root(
            root_id=wbe2_id,
            actor_id=actor_id,
            branch="main",
            project_id=project_id,
            code="1.2",
            name="Main WBE 2",
            level=1,
        )

        # Create CO version on source branch
        source_branch = f"co-{co_code}"
        await co_service.create_root(
            root_id=co_id,
            actor_id=actor_id,
            branch=source_branch,
            code=co_code,
            title="Test CO",
            description="Test Change Order",
            project_id=project_id,
            status="Approved",
        )

        # Create new versions of WBEs on source branch
        await wbe_service.create_root(
            root_id=wbe1_id,
            actor_id=actor_id,
            branch=source_branch,
            project_id=project_id,
            code="1.1",
            name="Source WBE 1",
            level=1,
        )

        await wbe_service.create_root(
            root_id=wbe2_id,
            actor_id=actor_id,
            branch=source_branch,
            project_id=project_id,
            code="1.2",
            name="Source WBE 2",
            level=1,
        )

        # Create CostElement on main branch first
        ce_type_id = uuid4()
        ce1_id = uuid4()
        await ce_service.create_root(
            root_id=ce1_id,
            actor_id=actor_id,
            branch="main",
            wbe_id=wbe1_id,
            cost_element_type_id=ce_type_id,
            code="CE-001",
            name="Main CE 1",
        )

        # Create new version of CostElement on source branch
        await ce_service.create_root(
            root_id=ce1_id,
            actor_id=actor_id,
            branch=source_branch,
            wbe_id=wbe1_id,
            cost_element_type_id=ce_type_id,
            code="CE-001",
            name="Source CE 1",
        )

        # Act
        result = await co_service.merge_change_order(
            change_order_id=co_id,
            actor_id=actor_id,
            target_branch="main",
        )

        # Assert
        assert result.status == "Implemented"

        # Verify WBEs are on main branch
        wbes_main = await wbe_service.get_wbes(branch="main")
        assert len(wbes_main[0]) >= 2

    @pytest.mark.asyncio
    async def test_merge_creates_new_entities(
        self, db_session: AsyncSession
    ) -> None:
        """Test that source branch versions overwrite target branch versions.

        Expected: WBEs from source branch overwrite versions on main.
        """
        # Arrange
        actor_id = uuid4()
        project_id = uuid4()
        co_id = uuid4()
        co_code = "456"

        co_service = ChangeOrderService(db_session)
        wbe_service = WBEService(db_session)

        # Create CO on main branch
        await co_service.create_root(
            root_id=co_id,
            actor_id=actor_id,
            branch="main",
            code=co_code,
            title="Test CO",
            description="Test Change Order",
            project_id=project_id,
            status="Approved",
        )

        # Create WBE on main branch first
        wbe_id = uuid4()
        await wbe_service.create_root(
            root_id=wbe_id,
            actor_id=actor_id,
            branch="main",
            project_id=project_id,
            code="2.1",
            name="Original WBE",
            level=1,
        )

        # Get WBE before merge
        wbe_before = await wbe_service.get_by_root_id(wbe_id, branch="main")
        assert wbe_before.name == "Original WBE"

        # Create CO version on source branch
        source_branch = f"co-{co_code}"
        await co_service.create_root(
            root_id=co_id,
            actor_id=actor_id,
            branch=source_branch,
            code=co_code,
            title="Test CO",
            description="Test Change Order",
            project_id=project_id,
            status="Approved",
        )

        # Create new version of WBE on source branch
        await wbe_service.create_root(
            root_id=wbe_id,
            actor_id=actor_id,
            branch=source_branch,
            project_id=project_id,
            code="2.1",
            name="Modified WBE",
            level=1,
        )

        # Act
        await co_service.merge_change_order(
            change_order_id=co_id,
            actor_id=actor_id,
            target_branch="main",
        )

        # Assert
        wbe_after = await wbe_service.get_by_root_id(wbe_id, branch="main")
        assert wbe_after is not None
        assert wbe_after.name == "Modified WBE"

    @pytest.mark.asyncio
    async def test_merge_with_empty_branch(
        self, db_session: AsyncSession
    ) -> None:
        """Test merge when source branch has no WBEs or CostElements.

        Expected: Merge succeeds, only CO entity is merged.
        """
        # Arrange
        actor_id = uuid4()
        project_id = uuid4()
        co_id = uuid4()
        co_code = "789"

        co_service = ChangeOrderService(db_session)

        # Create CO on main branch
        await co_service.create_root(
            root_id=co_id,
            actor_id=actor_id,
            branch="main",
            code=co_code,
            title="Test CO",
            description="Test Change Order",
            project_id=project_id,
            status="Approved",
        )

        # Create CO version on empty source branch
        source_branch = f"co-{co_code}"
        await co_service.create_root(
            root_id=co_id,
            actor_id=actor_id,
            branch=source_branch,
            code=co_code,
            title="Test CO",
            description="Test Change Order",
            project_id=project_id,
            status="Approved",
        )

        # Act - merge empty branch
        result = await co_service.merge_change_order(
            change_order_id=co_id,
            actor_id=actor_id,
            target_branch="main",
        )

        # Assert
        assert result.status == "Implemented"

    @pytest.mark.asyncio
    async def test_merge_soft_deletes_entities(
        self, db_session: AsyncSession
    ) -> None:
        """Test that soft-deleted entities propagate correctly during merge.

        Expected: Entity soft-deleted on source branch is also soft-deleted on main after merge.
        """
        # Arrange
        actor_id = uuid4()
        project_id = uuid4()
        co_id = uuid4()
        co_code = "999"

        co_service = ChangeOrderService(db_session)
        wbe_service = WBEService(db_session)

        # Create CO on main branch
        await co_service.create_root(
            root_id=co_id,
            actor_id=actor_id,
            branch="main",
            code=co_code,
            title="Test CO",
            description="Test Change Order",
            project_id=project_id,
            status="Approved",
        )

        # Create WBE on main branch first
        wbe_id = uuid4()
        await wbe_service.create_root(
            root_id=wbe_id,
            actor_id=actor_id,
            branch="main",
            project_id=project_id,
            code="9.1",
            name="Main WBE",
            level=1,
        )

        # Verify WBE exists and is not deleted on main
        wbe_before = await wbe_service.get_by_root_id(wbe_id, branch="main")
        assert wbe_before is not None
        assert wbe_before.deleted_at is None

        # Create CO version on source branch
        source_branch = f"co-{co_code}"
        await co_service.create_root(
            root_id=co_id,
            actor_id=actor_id,
            branch=source_branch,
            code=co_code,
            title="Test CO",
            description="Test Change Order",
            project_id=project_id,
            status="Approved",
        )

        # Create WBE version on source branch
        await wbe_service.create_root(
            root_id=wbe_id,
            actor_id=actor_id,
            branch=source_branch,
            project_id=project_id,
            code="9.1",
            name="Source WBE",
            level=1,
        )

        # Soft-delete WBE on source branch
        deleted_wbe = await wbe_service.soft_delete(
            root_id=wbe_id,
            actor_id=actor_id,
            branch=source_branch,
        )
        assert deleted_wbe.deleted_at is not None

        # Act - merge the soft-delete
        await co_service.merge_change_order(
            change_order_id=co_id,
            actor_id=actor_id,
            target_branch="main",
        )

        # Assert - WBE should be soft-deleted on main branch
        # Use direct SQL query to check for soft-deleted entity
        from typing import Any, cast

        from sqlalchemy import func, select

        stmt = select(WBE).where(
            WBE.wbe_id == wbe_id,
            WBE.branch == "main",
            func.upper(cast(Any, WBE).valid_time).is_(None),
        )
        result = await db_session.execute(stmt)
        wbe_after = result.scalar_one_or_none()

        assert wbe_after is not None, "WBE should exist on main after merge"
        assert wbe_after.deleted_at is not None, "WBE should be soft-deleted on main after merge"
