"""Unit tests for EntityDiscoveryService.

Tests the discovery of branchable entities (WBEs, CostElements, Projects) in a given branch.
Follows RED-GREEN-REFACTOR TDD methodology.
"""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain.wbe import WBE
from app.models.schemas.project import ProjectCreate
from app.services.cost_element_service import CostElementService
from app.services.entity_discovery_service import EntityDiscoveryService
from app.services.project import ProjectService
from app.services.wbe import WBEService


class TestEntityDiscoveryService:
    """Test suite for EntityDiscoveryService."""

    @pytest.mark.asyncio
    async def test_discover_wbes_in_branch(self, db_session: AsyncSession):
        """Test discovering WBEs in a specific branch.

        Expected: Returns list of WBEs with matching branch, deleted_at IS NULL.
        """
        # Arrange
        discovery_service = EntityDiscoveryService(db_session)
        wbe_service = WBEService(db_session)
        branch_name = "co-test-123"
        actor_id = uuid4()
        project_id = uuid4()
        wbe_id = uuid4()

        # Create a WBE on the branch
        await wbe_service.create_root(
            root_id=wbe_id,
            actor_id=actor_id,
            branch=branch_name,
            project_id=project_id,
            code="1.1",
            name="Test WBE",
            level=1,
        )

        # Act
        result = await discovery_service.discover_wbes(branch_name)

        # Assert
        assert len(result) == 1
        assert result[0].wbe_id == wbe_id
        assert result[0].branch == branch_name
        assert result[0].deleted_at is None

    @pytest.mark.asyncio
    async def test_discover_cost_elements_in_branch(self, db_session: AsyncSession):
        """Test discovering CostElements in a specific branch.

        Expected: Returns list of CostElements with matching branch, deleted_at IS NULL.
        """
        # Arrange
        discovery_service = EntityDiscoveryService(db_session)
        ce_service = CostElementService(db_session)
        branch_name = "co-test-456"
        actor_id = uuid4()
        wbe_id = uuid4()
        ce_id = uuid4()
        ce_type_id = uuid4()

        # Create a CostElement on the branch using create_root
        await ce_service.create_root(
            root_id=ce_id,
            actor_id=actor_id,
            branch=branch_name,
            wbe_id=wbe_id,
            cost_element_type_id=ce_type_id,
            code="CE-001",
            name="Test Cost Element",
        )

        # Act
        result = await discovery_service.discover_cost_elements(branch_name)

        # Assert
        assert len(result) == 1
        assert result[0].cost_element_id == ce_id
        assert result[0].branch == branch_name
        assert result[0].deleted_at is None

    @pytest.mark.asyncio
    async def test_discover_projects_in_branch(self, db_session: AsyncSession):
        """Test discovering Projects in a specific branch.

        Expected: Returns list of Projects with matching branch, deleted_at IS NULL.
        """
        # Arrange
        discovery_service = EntityDiscoveryService(db_session)
        project_service = ProjectService(db_session)
        branch_name = "co-test-789"
        actor_id = uuid4()

        # Create a Project on the branch using ProjectCreate schema
        project_in = ProjectCreate(
            name="Test Project",
            code="PROJ-001",
            budget=Decimal("100000.00"),
        )
        created_project = await project_service.create_project(
            project_in=project_in,
            actor_id=actor_id,
            control_date=datetime.now(UTC),
        )
        # Manually set the branch for testing (since create_project doesn't support branch parameter)
        created_project.branch = branch_name
        await db_session.flush()

        # Act
        result = await discovery_service.discover_projects(branch_name)

        # Assert
        assert len(result) == 1
        assert result[0].project_id == created_project.project_id
        assert result[0].branch == branch_name
        assert result[0].deleted_at is None

    @pytest.mark.asyncio
    async def test_discover_returns_empty_for_nonexistent_branch(
        self, db_session: AsyncSession
    ):
        """Test discovering entities in a branch that doesn't exist.

        Expected: Returns empty list for all entity types.
        """
        # Arrange
        service = EntityDiscoveryService(db_session)
        nonexistent_branch = "co-nonexistent-999"

        # Act
        wbes = await service.discover_wbes(nonexistent_branch)
        cost_elements = await service.discover_cost_elements(nonexistent_branch)
        projects = await service.discover_projects(nonexistent_branch)

        # Assert
        assert wbes == []
        assert cost_elements == []
        assert projects == []

    @pytest.mark.asyncio
    async def test_discover_filters_deleted_entities(self, db_session: AsyncSession):
        """Test that deleted entities are filtered out.

        Expected: Only returns entities where deleted_at IS NULL.
        """
        # Arrange
        discovery_service = EntityDiscoveryService(db_session)
        wbe_service = WBEService(db_session)
        branch_name = "co-test-filter"
        actor_id = uuid4()
        project_id = uuid4()
        active_wbe_id = uuid4()
        deleted_wbe_id = uuid4()

        # Create active WBE
        await wbe_service.create_root(
            root_id=active_wbe_id,
            actor_id=actor_id,
            branch=branch_name,
            project_id=project_id,
            code="1.1",
            name="Active WBE",
            level=1,
        )

        # Create deleted WBE
        await wbe_service.create_root(
            root_id=deleted_wbe_id,
            actor_id=actor_id,
            branch=branch_name,
            project_id=project_id,
            code="1.2",
            name="Deleted WBE",
            level=1,
        )
        # Manually soft delete the second WBE by setting deleted_at
        # (since delete_wbe queries main branch by default)
        stmt = select(WBE).where(WBE.wbe_id == deleted_wbe_id, WBE.branch == branch_name)
        result = await db_session.execute(stmt)
        deleted_wbe = result.scalar_one()
        deleted_wbe.deleted_at = datetime.now(UTC)
        await db_session.flush()

        # Act
        result = await discovery_service.discover_wbes(branch_name)

        # Assert
        assert len(result) == 1
        assert result[0].wbe_id == active_wbe_id
        assert result[0].deleted_at is None

    @pytest.mark.asyncio
    async def test_discover_wbes_excludes_other_branches(self, db_session: AsyncSession):
        """Test that discovery only returns entities from the specified branch.

        Expected: WBEs from other branches are not included.
        """
        # Arrange
        discovery_service = EntityDiscoveryService(db_session)
        wbe_service = WBEService(db_session)
        target_branch = "co-target-123"
        other_branch = "co-other-456"
        actor_id = uuid4()
        project_id = uuid4()
        target_wbe_id = uuid4()
        other_wbe_id = uuid4()

        # Create WBE on target branch
        await wbe_service.create_root(
            root_id=target_wbe_id,
            actor_id=actor_id,
            branch=target_branch,
            project_id=project_id,
            code="1.1",
            name="Target WBE",
            level=1,
        )

        # Create WBE on other branch
        await wbe_service.create_root(
            root_id=other_wbe_id,
            actor_id=actor_id,
            branch=other_branch,
            project_id=project_id,
            code="1.2",
            name="Other WBE",
            level=1,
        )

        # Act
        result = await discovery_service.discover_wbes(target_branch)

        # Assert
        assert len(result) == 1
        assert result[0].wbe_id == target_wbe_id
        assert result[0].branch == target_branch
