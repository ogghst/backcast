"""Performance tests for Change Order merge operation.

Tests verify that merging a large number of entities (100+)
completes within the defined SLA (5 seconds).

Follows RED-GREEN-REFACTOR TDD methodology.

Requirement: Task BE-007 - "Performance: Merge completes within 5 seconds for 100 entities"
"""

import time
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.change_order_service import ChangeOrderService
from app.services.cost_element_service import CostElementService
from app.services.project import ProjectService
from app.services.wbe import WBEService


@pytest.mark.usefixtures("db_session")
@pytest.mark.performance
class TestMergePerformance:
    """Performance test suite for Change Order merge operation."""

    @pytest.mark.asyncio
    async def test_merge_100_entities_under_5_seconds(
        self, db_session: AsyncSession
    ) -> None:
        """Verify merging 100 entities (50 WBEs + 50 CostElements) completes within 5 seconds.

        This is the SLA requirement from the plan:
        - Task BE-007: "Performance: Merge completes within 5 seconds for 100 entities"

        The test creates 50 WBEs and 50 CostElements on both main and source branches,
        then performs a merge and measures execution time.
        """
        # Arrange
        actor_id = uuid4()
        project_id = uuid4()
        co_id = uuid4()
        co_code = "PERF-123"
        ce_type_id = uuid4()

        co_service = ChangeOrderService(db_session)
        wbe_service = WBEService(db_session)
        ce_service = CostElementService(db_session)
        project_service = ProjectService(db_session)

        # Create project on main branch first
        await project_service.create_root(
            root_id=project_id,
            actor_id=actor_id,
            branch="main",
            code="PROJ-PERF",
            name="Performance Test Project",
        )

        # Create CO on main branch
        await co_service.create_root(
            root_id=co_id,
            actor_id=actor_id,
            branch="main",
            code=co_code,
            title="Performance Test CO",
            description="CO for performance testing",
            project_id=project_id,
            status="Approved",
        )

        # Create 50 WBEs on main branch first
        wbe_ids = []
        for i in range(50):
            wbe_id = uuid4()
            wbe_ids.append(wbe_id)
            await wbe_service.create_root(
                root_id=wbe_id,
                actor_id=actor_id,
                branch="main",
                project_id=project_id,
                code=f"WBE-{i:03d}",
                name=f"Main WBE {i}",
                level=1,
            )

        # Create 50 CostElements on main branch
        ce_ids = []
        for i in range(50):
            ce_id = uuid4()
            ce_ids.append(ce_id)
            await ce_service.create_root(
                root_id=ce_id,
                actor_id=actor_id,
                branch="main",
                wbe_id=wbe_ids[i % 50],  # Distribute across WBEs
                cost_element_type_id=ce_type_id,
                code=f"CE-{i:03d}",
                name=f"Cost Element {i}",
            )

        # Create CO version on source branch
        source_branch = f"BR-{co_code}"
        await co_service.create_root(
            root_id=co_id,
            actor_id=actor_id,
            branch=source_branch,
            code=co_code,
            title="Performance Test CO",
            description="CO for performance testing",
            project_id=project_id,
            status="Approved",
        )

        # Create new versions of WBEs on source branch
        for i, wbe_id in enumerate(wbe_ids):
            await wbe_service.create_root(
                root_id=wbe_id,
                actor_id=actor_id,
                branch=source_branch,
                project_id=project_id,
                code=f"WBE-{i:03d}",
                name=f"Source WBE {i}",
                level=1,
            )

        # Create new versions of CostElements on source branch
        for i, ce_id in enumerate(ce_ids):
            await ce_service.create_root(
                root_id=ce_id,
                actor_id=actor_id,
                branch=source_branch,
                wbe_id=wbe_ids[i % 50],
                cost_element_type_id=ce_type_id,
                code=f"CE-{i:03d}",
                name=f"Source Cost Element {i}",
            )

        # Act: Perform merge and measure time
        start_time = time.time()
        result = await co_service.merge_change_order(
            change_order_id=co_id,
            actor_id=actor_id,
            target_branch="main",
        )
        end_time = time.time()

        total_time_seconds = end_time - start_time

        # Assert: Performance SLA met
        assert result.status == "Implemented", "Merge should complete successfully"
        assert total_time_seconds < 5.0, (
            f"Merge of 100 entities (50 WBEs + 50 CostElements) took "
            f"{total_time_seconds:.2f}s, exceeding 5s SLA requirement"
        )

        # Verify entities are on main branch
        from app.services.entity_discovery_service import EntityDiscoveryService

        discovery = EntityDiscoveryService(db_session)
        main_wbes = await discovery.discover_wbes("main")
        main_ces = await discovery.discover_cost_elements("main")

        # All entities should be on main branch
        assert len(main_wbes) >= 50, (
            f"Expected at least 50 WBEs on main, got {len(main_wbes)}"
        )
        assert len(main_ces) >= 50, (
            f"Expected at least 50 CostElements on main, got {len(main_ces)}"
        )

    @pytest.mark.asyncio
    async def test_merge_100_wbes_under_5_seconds(
        self, db_session: AsyncSession
    ) -> None:
        """Verify merging 100 WBEs completes within 5 seconds.

        Tests the performance boundary with a single entity type.
        """
        # Arrange
        actor_id = uuid4()
        project_id = uuid4()
        co_id = uuid4()
        co_code = "PERF-WBE"

        co_service = ChangeOrderService(db_session)
        wbe_service = WBEService(db_session)
        project_service = ProjectService(db_session)

        # Create project on main branch first
        await project_service.create_root(
            root_id=project_id,
            actor_id=actor_id,
            branch="main",
            code="PROJ-PERF",
            name="Performance Test Project",
        )

        # Create CO on main branch
        await co_service.create_root(
            root_id=co_id,
            actor_id=actor_id,
            branch="main",
            code=co_code,
            title="Performance Test CO - WBEs",
            description="CO for WBE performance testing",
            project_id=project_id,
            status="Approved",
        )

        # Create 100 WBEs on main branch first
        wbe_ids = []
        for i in range(100):
            wbe_id = uuid4()
            wbe_ids.append(wbe_id)
            await wbe_service.create_root(
                root_id=wbe_id,
                actor_id=actor_id,
                branch="main",
                project_id=project_id,
                code=f"WBE-{i:03d}",
                name=f"Main WBE {i}",
                level=1,
            )

        # Create CO version on source branch
        source_branch = f"BR-{co_code}"
        await co_service.create_root(
            root_id=co_id,
            actor_id=actor_id,
            branch=source_branch,
            code=co_code,
            title="Performance Test CO - WBEs",
            description="CO for WBE performance testing",
            project_id=project_id,
            status="Approved",
        )

        # Create new versions of WBEs on source branch
        for i, wbe_id in enumerate(wbe_ids):
            await wbe_service.create_root(
                root_id=wbe_id,
                actor_id=actor_id,
                branch=source_branch,
                project_id=project_id,
                code=f"WBE-{i:03d}",
                name=f"Source WBE {i}",
                level=1,
            )

        # Act: Perform merge and measure time
        start_time = time.time()
        result = await co_service.merge_change_order(
            change_order_id=co_id,
            actor_id=actor_id,
            target_branch="main",
        )
        end_time = time.time()

        total_time_seconds = end_time - start_time

        # Assert: Performance SLA met
        assert result.status == "Implemented", "Merge should complete successfully"
        assert total_time_seconds < 5.0, (
            f"Merge of 100 WBEs took {total_time_seconds:.2f}s, "
            f"exceeding 5s SLA requirement"
        )

        # Verify entities are on main branch
        from app.services.entity_discovery_service import EntityDiscoveryService

        discovery = EntityDiscoveryService(db_session)
        main_wbes = await discovery.discover_wbes("main")

        assert len(main_wbes) >= 100, (
            f"Expected at least 100 WBEs on main, got {len(main_wbes)}"
        )
