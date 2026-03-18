"""Unit tests for Change Order merge orchestration.

Tests the enhanced merge_change_order method that orchestrates
the discovery and merge of all branchable entities (WBEs, CostElements, Projects).

Follows RED-GREEN-REFACTOR TDD methodology.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain.change_order import ChangeOrder
from app.services.change_order_service import ChangeOrderService


class TestChangeOrderMergeOrchestration:
    """Test suite for enhanced merge_change_order orchestration."""

    @pytest.mark.asyncio
    async def test_merge_calls_discovery_service(self, db_session: AsyncSession):
        """Test that merge invokes EntityDiscoveryService for all entity types.

        Expected: discover_wbes and discover_cost_elements are called once
        with the source branch.
        """
        # Arrange
        service = ChangeOrderService(db_session)
        change_order_id = uuid4()
        actor_id = uuid4()
        target_branch = "main"

        # Create a mock ChangeOrder with configure_mock to ensure attributes return values
        project_id = uuid4()
        mock_co = MagicMock()
        mock_co.configure_mock(
            code="123",
            status="Approved",
            change_order_id=change_order_id,
            project_id=project_id
        )

        # Mock the service methods
        service.get_as_of = AsyncMock(return_value=mock_co, side_effect=None)

        # Mock session operations to avoid actual DB operations
        db_session.add = MagicMock()
        db_session.flush = AsyncMock()
        db_session.refresh = AsyncMock()

        with (
            patch(
                "app.services.change_order_service.EntityDiscoveryService"
            ) as MockDiscoveryService,
            patch(
                "app.services.change_order_service.UpdateChangeOrderStatusCommand"
            ) as MockStatusCommand,
            patch("app.services.project.ProjectService") as MockProjectService,
        ):
            mock_discovery = AsyncMock()
            MockDiscoveryService.return_value = mock_discovery

            # Mock command execution
            mock_status_cmd = AsyncMock()
            MockStatusCommand.return_value = mock_status_cmd
            mock_status_cmd.execute = AsyncMock()

            # Mock ProjectService for budget update
            mock_project_service = AsyncMock()
            MockProjectService.return_value = mock_project_service
            mock_project_service.update_project = AsyncMock()

            # Mock session.execute to return a budget sum
            mock_budget_result = MagicMock()
            mock_budget_result.scalar_one.return_value = 100000
            db_session.execute = AsyncMock(return_value=mock_budget_result)

            # Configure discovery to return empty lists
            mock_discovery.discover_all_wbes.return_value = []
            mock_discovery.discover_all_cost_elements.return_value = []

            # Mock merge_branch to return the same mock_co (which will be modified)
            service.merge_branch = AsyncMock(return_value=mock_co)

            # Mock _detect_all_merge_conflicts to return empty list (no conflicts)
            service._detect_all_merge_conflicts = AsyncMock(return_value=[])

            # Act
            await service.merge_change_order(
                change_order_id=change_order_id,
                actor_id=actor_id,
                target_branch=target_branch,
            )

            # Assert
            # discover_all_wbes is called once
            mock_discovery.discover_all_wbes.assert_called_once_with("BR-123")
            mock_discovery.discover_all_cost_elements.assert_called_once_with("BR-123")

    @pytest.mark.asyncio
    async def test_merge_iterates_wbes(self, db_session: AsyncSession):
        """Test that merge calls BranchableService.merge_branch for each discovered WBE.

        Expected: merge_branch called once for each WBE in source branch.
        """
        # Arrange
        service = ChangeOrderService(db_session)
        change_order_id = uuid4()
        actor_id = uuid4()
        target_branch = "main"

        # Create a mock ChangeOrder with configure_mock
        project_id = uuid4()
        mock_co = MagicMock()
        mock_co.configure_mock(
            code="456",
            status="Approved",
            change_order_id=change_order_id,
            project_id=project_id
        )

        # Create mock WBEs (not deleted)
        mock_wbe1 = MagicMock()
        mock_wbe1.wbe_id = uuid4()
        mock_wbe1.deleted_at = None

        mock_wbe2 = MagicMock()
        mock_wbe2.wbe_id = uuid4()
        mock_wbe2.deleted_at = None

        service.get_as_of = AsyncMock(return_value=mock_co, side_effect=None)

        # Mock session operations to avoid actual DB operations
        db_session.add = MagicMock()
        db_session.flush = AsyncMock()
        db_session.refresh = AsyncMock()

        with (
            patch(
                "app.services.change_order_service.EntityDiscoveryService"
            ) as MockDiscoveryService,
            patch("app.services.change_order_service.WBEService") as MockWBEService,
            patch(
                "app.services.change_order_service.UpdateChangeOrderStatusCommand"
            ) as MockStatusCommand,
            patch("app.services.project.ProjectService") as MockProjectService,
        ):
            mock_discovery = AsyncMock()
            MockDiscoveryService.return_value = mock_discovery

            # Mock command execution
            mock_status_cmd = AsyncMock()
            MockStatusCommand.return_value = mock_status_cmd
            mock_status_cmd.execute = AsyncMock()

            # Mock ProjectService for budget update
            mock_project_service = AsyncMock()
            MockProjectService.return_value = mock_project_service
            mock_project_service.update_project = AsyncMock()

            # Mock session.execute to return a budget sum
            mock_budget_result = MagicMock()
            mock_budget_result.scalar_one.return_value = 100000
            db_session.execute = AsyncMock(return_value=mock_budget_result)

            # Configure discovery to return 2 WBEs
            mock_discovery.discover_all_wbes.return_value = [mock_wbe1, mock_wbe2]
            mock_discovery.discover_all_cost_elements.return_value = []

            # Mock WBE service merge_branch and soft_delete
            mock_wbe_service = AsyncMock()
            MockWBEService.return_value = mock_wbe_service
            mock_wbe_service.merge_branch = AsyncMock()
            mock_wbe_service.soft_delete = AsyncMock()

            # Mock the main CO merge
            service.merge_branch = AsyncMock(return_value=mock_co)

            # Mock _detect_all_merge_conflicts to return empty list (no conflicts)
            service._detect_all_merge_conflicts = AsyncMock(return_value=[])

            # Act
            await service.merge_change_order(
                change_order_id=change_order_id,
                actor_id=actor_id,
                target_branch=target_branch,
            )

            # Assert
            assert mock_wbe_service.merge_branch.call_count == 2
            mock_wbe_service.merge_branch.assert_any_call(
                root_id=mock_wbe1.wbe_id,
                actor_id=actor_id,
                source_branch="BR-456",
                target_branch=target_branch,
                control_date=None,
            )
            mock_wbe_service.merge_branch.assert_any_call(
                root_id=mock_wbe2.wbe_id,
                actor_id=actor_id,
                source_branch="BR-456",
                target_branch=target_branch,
                control_date=None,
            )

    @pytest.mark.asyncio
    async def test_merge_updates_status_to_implemented(self, db_session: AsyncSession):
        """Test that merge updates CO status to "Implemented" after successful merge.

        Expected: UpdateChangeOrderStatusCommand is called with "Implemented".
        """
        # Arrange
        service = ChangeOrderService(db_session)
        change_order_id = uuid4()
        actor_id = uuid4()
        target_branch = "main"

        # Create a mock ChangeOrder
        mock_co = MagicMock(spec=ChangeOrder)
        mock_co.code = "789"
        mock_co.status = "Approved"
        mock_co.change_order_id = change_order_id
        mock_co.project_id = uuid4()  # Add project_id for budget recalculation

        service.get_as_of = AsyncMock(return_value=mock_co, side_effect=None)

        # Mock session operations to avoid actual DB operations
        db_session.add = MagicMock()
        db_session.flush = AsyncMock()
        db_session.refresh = AsyncMock()

        with (
            patch(
                "app.services.change_order_service.EntityDiscoveryService"
            ) as MockDiscoveryService,
            patch(
                "app.services.change_order_service.UpdateChangeOrderStatusCommand"
            ) as MockStatusCommand,
            patch("app.services.project.ProjectService") as MockProjectService,
        ):
            mock_discovery = AsyncMock()
            MockDiscoveryService.return_value = mock_discovery

            # Mock command execution - execute returns the updated change order
            mock_status_cmd = AsyncMock()
            MockStatusCommand.return_value = mock_status_cmd
            mock_updated_co = MagicMock(spec=ChangeOrder)
            mock_status_cmd.execute = AsyncMock(return_value=mock_updated_co)

            # Mock ProjectService for budget update
            mock_project_service = AsyncMock()
            MockProjectService.return_value = mock_project_service
            mock_project_service.update_project = AsyncMock()

            # Mock session.execute to return a budget sum
            mock_budget_result = MagicMock()
            mock_budget_result.scalar_one.return_value = 100000
            db_session.execute = AsyncMock(return_value=mock_budget_result)

            # Configure discovery to return empty lists
            mock_discovery.discover_all_wbes.return_value = []
            mock_discovery.discover_all_cost_elements.return_value = []

            # Mock merge_branch to return the mock_co
            service.merge_branch = AsyncMock(return_value=mock_co)

            # Mock _detect_all_merge_conflicts to return empty list (no conflicts)
            service._detect_all_merge_conflicts = AsyncMock(return_value=[])

            # Act
            await service.merge_change_order(
                change_order_id=change_order_id,
                actor_id=actor_id,
                target_branch=target_branch,
            )

            # Assert - Command should be called with "Implemented"
            MockStatusCommand.assert_called_once_with(
                change_order_id=change_order_id,
                new_status="Implemented",
                actor_id=actor_id,
                branch=target_branch,
                control_date=None,
            )
            mock_status_cmd.execute.assert_called_once_with(db_session)

            # Verify refresh was called on the returned updated CO
            db_session.refresh.assert_called_with(mock_updated_co)

    @pytest.mark.asyncio
    async def test_merge_rolls_back_on_failure(self, db_session: AsyncSession):
        """Test that merge rolls back transaction when WBE merge fails.

        Expected: Exception is raised when merge_branch fails.
        """
        # Arrange
        service = ChangeOrderService(db_session)
        change_order_id = uuid4()
        actor_id = uuid4()
        target_branch = "main"

        # Create a mock ChangeOrder
        mock_co = MagicMock()
        mock_co.configure_mock(
            code="999",
            status="Approved",
            change_order_id=change_order_id,
            project_id=uuid4()
        )

        # Create mock WBE (not deleted, so merge will be attempted)
        mock_wbe = MagicMock()
        mock_wbe.wbe_id = uuid4()
        mock_wbe.deleted_at = None

        service.get_as_of = AsyncMock(return_value=mock_co, side_effect=None)

        # Mock session operations to avoid actual DB operations
        db_session.add = MagicMock()
        db_session.flush = AsyncMock()
        db_session.refresh = AsyncMock()

        with (
            patch(
                "app.services.change_order_service.EntityDiscoveryService"
            ) as MockDiscoveryService,
            patch("app.services.change_order_service.WBEService") as MockWBEService,
        ):
            mock_discovery = AsyncMock()
            MockDiscoveryService.return_value = mock_discovery

            # Configure discovery to return 1 WBE
            mock_discovery.discover_all_wbes.return_value = [mock_wbe]
            mock_discovery.discover_all_cost_elements.return_value = []

            # Mock WBE service merge_branch to raise exception
            mock_wbe_service = AsyncMock()
            MockWBEService.return_value = mock_wbe_service
            mock_wbe_service.merge_branch = AsyncMock(
                side_effect=Exception("Merge conflict")
            )

            # Mock the main CO merge
            service.merge_branch = AsyncMock(return_value=mock_co)

            # Mock _detect_all_merge_conflicts to return empty list (no conflicts)
            service._detect_all_merge_conflicts = AsyncMock(return_value=[])

            # Act & Assert
            with pytest.raises(Exception, match="Merge conflict"):
                await service.merge_change_order(
                    change_order_id=change_order_id,
                    actor_id=actor_id,
                    target_branch=target_branch,
                )

    @pytest.mark.asyncio
    async def test_merge_raises_on_conflicts(self, db_session: AsyncSession):
        """Test that merge raises MergeConflictError when conflicts are detected.

        Expected: MergeConflictError raised with conflict details.
        """
        # Arrange
        service = ChangeOrderService(db_session)
        change_order_id = uuid4()
        actor_id = uuid4()
        target_branch = "main"

        # Create a mock ChangeOrder
        mock_co = MagicMock()
        mock_co.configure_mock(
            code="888",
            status="Approved",
            change_order_id=change_order_id,
            project_id=uuid4()
        )

        service.get_as_of = AsyncMock(return_value=mock_co, side_effect=None)

        # Mock the _detect_all_merge_conflicts method to return conflicts
        conflicts = [
            {
                "entity_type": "WBE",
                "entity_id": str(uuid4()),
                "field": "name",
                "source_branch": "BR-888",
                "target_branch": "main",
                "source_value": "Updated Name",
                "target_value": "Original Name",
            }
        ]
        service._detect_all_merge_conflicts = AsyncMock(return_value=conflicts)

        # Act & Assert
        from app.core.branching.exceptions import MergeConflictError

        with pytest.raises(MergeConflictError) as exc_info:
            await service.merge_change_order(
                change_order_id=change_order_id,
                actor_id=actor_id,
                target_branch=target_branch,
            )

        # Verify the error contains the conflicts
        assert exc_info.value.conflicts == conflicts
        service._detect_all_merge_conflicts.assert_called_once_with("BR-888", "main")
