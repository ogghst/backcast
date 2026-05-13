"""Unit tests for change order impact analysis defensive checks (BE-005).

Tests that impact analysis handles empty branches gracefully:
- Empty branches (no WBE or cost element changes)
- ValueError from impact analysis service
- Generic exceptions from impact analysis service
- Sets reasonable defaults and allows workflow to continue
"""

from decimal import Decimal
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import ChangeOrderStatus
from app.models.domain.change_order import ChangeOrder
from app.models.schemas.change_order import ChangeOrderCreate
from app.services.change_order_service import ChangeOrderService


class TestChangeOrderImpactAnalysisDefense:
    """Test impact analysis defensive error handling.

    Context: BE-005 requires defensive checks for impact analysis on empty branches.
    When the isolation branch has no changes, the impact analysis service may raise
    ValueError. The change order service should handle this gracefully with reasonable
    defaults (LOW impact, zero score) to allow the approval workflow to continue.
    """

    @pytest.mark.asyncio
    async def test_empty_branch_sets_low_impact_defaults(
        self, db_session: AsyncSession
    ) -> None:
        """Test _run_impact_analysis sets LOW impact defaults for empty branch.

        Acceptance Criteria:
        - Status changes to "completed" (not "skipped" or "failed")
        - impact_level set to "LOW"
        - impact_score set to 0.0
        - assigned_approver_id is attempted (may be None if no approver configured)
        - Logs warning about empty branch
        """
        # Arrange - Create a change order via service
        service = ChangeOrderService(db_session)
        project_id = uuid4()
        actor_id = uuid4()

        change_order_in = ChangeOrderCreate(
            project_id=project_id,
            code="CO-EMPTY-001",
            title="Empty Branch Test",
            description="Testing empty branch handling",
            status=ChangeOrderStatus.DRAFT,
            justification="Test",
        )

        # Create CO directly using update to bypass branch creation
        # This allows us to test the impact analysis logic in isolation
        co_id = uuid4()
        change_order_id = uuid4()

        await db_session.execute(
            update(ChangeOrder)
            .where(ChangeOrder.id == co_id)
            .values(
                change_order_id=change_order_id,
                project_id=project_id,
                code="CO-EMPTY-001",
                title="Empty Branch Test",
                status=ChangeOrderStatus.DRAFT.value,
                branch_name="BR-CO-EMPTY-001",
                branch="main",
                impact_analysis_status="pending",
                impact_level=None,
                impact_score=None,
                created_by=actor_id,
            )
        )

        # Mock the impact analysis service to raise ValueError (empty branch)
        with patch(
            "app.services.impact_analysis_service.ImpactAnalysisService"
        ) as mock_impact_service_class:
            mock_impact_service = AsyncMock()
            mock_impact_service.analyze_impact = AsyncMock(
                side_effect=ValueError(
                    "No project data available for analysis: "
                    "No WBEs or cost elements found on branch BR-CO-EMPTY-001"
                )
            )
            mock_impact_service_class.return_value = mock_impact_service

            # Act - Run impact analysis on empty branch
            await service._run_impact_analysis(
                change_order=ChangeOrder(
                    id=co_id,
                    change_order_id=change_order_id,
                    project_id=project_id,
                    code="CO-EMPTY-001",
                ),
                branch_name="BR-CO-EMPTY-001",
            )

        # Fetch the updated change order
        result = await db_session.execute(
            select(ChangeOrder).where(ChangeOrder.id == co_id)
        )
        change_order = result.scalar_one()

        # Assert - Verify LOW impact defaults were set
        assert change_order.impact_analysis_status == "completed", (
            f"Expected status 'completed', got '{change_order.impact_analysis_status}'"
        )

        assert change_order.impact_level == "LOW", (
            f"Expected impact_level 'LOW' for empty branch, got '{change_order.impact_level}'"
        )

        assert change_order.impact_score == Decimal("0"), (
            f"Expected impact_score 0.0 for empty branch, got {change_order.impact_score}"
        )

        # Verify impact_analysis_results contains the error info
        assert change_order.impact_analysis_results is not None
        assert "error" in change_order.impact_analysis_results
        assert (
            "empty branch"
            in change_order.impact_analysis_results.get("note", "").lower()
        )

    @pytest.mark.asyncio
    async def test_service_exception_sets_medium_impact_defaults(
        self, db_session: AsyncSession
    ) -> None:
        """Test _run_impact_analysis sets MEDIUM impact defaults for service errors.

        Acceptance Criteria:
        - Status changes to "completed" (graceful degradation)
        - impact_level set to "MEDIUM" (conservative default)
        - impact_score set to 50 (moderate impact)
        - Logs error about service failure
        """
        # Arrange
        service = ChangeOrderService(db_session)
        project_id = uuid4()
        actor_id = uuid4()

        co_id = uuid4()
        change_order_id = uuid4()

        await db_session.execute(
            update(ChangeOrder)
            .where(ChangeOrder.id == co_id)
            .values(
                change_order_id=change_order_id,
                project_id=project_id,
                code="CO-ERROR-001",
                title="Service Error Test",
                status=ChangeOrderStatus.DRAFT.value,
                branch_name="BR-CO-ERROR-001",
                branch="main",
                impact_analysis_status="pending",
                impact_level=None,
                impact_score=None,
                created_by=actor_id,
            )
        )

        # Mock the impact analysis service to raise a generic exception
        with patch(
            "app.services.impact_analysis_service.ImpactAnalysisService"
        ) as mock_impact_service_class:
            mock_impact_service = AsyncMock()
            mock_impact_service.analyze_impact = AsyncMock(
                side_effect=RuntimeError("Unexpected service error")
            )
            mock_impact_service_class.return_value = mock_impact_service

            # Act - Run impact analysis with service error
            await service._run_impact_analysis(
                change_order=ChangeOrder(
                    id=co_id,
                    change_order_id=change_order_id,
                    project_id=project_id,
                    code="CO-ERROR-001",
                ),
                branch_name="BR-CO-ERROR-001",
            )

        # Fetch the updated change order
        result = await db_session.execute(
            select(ChangeOrder).where(ChangeOrder.id == co_id)
        )
        change_order = result.scalar_one()

        # Assert - Verify MEDIUM impact defaults were set
        assert change_order.impact_analysis_status == "completed", (
            f"Expected status 'completed', got '{change_order.impact_analysis_status}'"
        )

        assert change_order.impact_level == "MEDIUM", (
            f"Expected impact_level 'MEDIUM' for service error, got '{change_order.impact_level}'"
        )

        assert change_order.impact_score == Decimal("50"), (
            f"Expected impact_score 50 for service error, got {change_order.impact_score}"
        )

        # Verify impact_analysis_results contains error info
        assert change_order.impact_analysis_results is not None
        assert "error" in change_order.impact_analysis_results
        assert change_order.impact_analysis_results["error_type"] == "RuntimeError"
