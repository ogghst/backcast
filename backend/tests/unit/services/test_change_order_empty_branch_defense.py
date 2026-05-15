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
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schemas.change_order import ChangeOrderCreate
from app.services.change_order_service import ChangeOrderService


class TestChangeOrderImpactAnalysisDefense:
    """Test impact analysis defensive error handling.

    Context: BE-005 requires defensive checks for impact analysis on empty branches.
    When the isolation branch has no changes, the impact analysis service may raise
    ValueError. The change order service should handle this gracefully with reasonable
    defaults (LOW impact, zero score) to allow the approval workflow to continue.
    """

    async def _create_co_via_service(
        self, db_session: AsyncSession
    ) -> tuple[ChangeOrderService, object]:
        """Helper: create a ChangeOrder via the service so it is persisted properly."""
        service = ChangeOrderService(db_session)
        project_id = uuid4()
        actor_id = uuid4()
        co_create = ChangeOrderCreate(
            project_id=project_id,
            code=f"CO-DEF-{uuid4().hex[:6]}",
            title="Empty Branch Test",
            description="Test",
        )
        co = await service.create_change_order(co_create, actor_id=actor_id)
        await db_session.commit()
        return service, co

    @pytest.mark.asyncio
    async def test_empty_branch_sets_low_impact_defaults(
        self, db_session: AsyncSession
    ) -> None:
        """Test _run_impact_analysis sets LOW impact defaults for empty branch.

        Acceptance Criteria:
        - Status changes to "completed" (not "skipped" or "failed")
        - impact_level set to "LOW"
        - impact_score set to 0.0
        - Logs warning about empty branch
        """
        # Arrange - Create a change order via service
        service, co = await self._create_co_via_service(db_session)

        # Mock the impact analysis service to raise ValueError (empty branch)
        with patch(
            "app.services.impact_analysis_service.ImpactAnalysisService"
        ) as mock_impact_service_class:
            mock_impact_service = AsyncMock()
            mock_impact_service.analyze_impact = AsyncMock(
                side_effect=ValueError(
                    "No project data available for analysis: "
                    f"No WBEs or cost elements found on branch {co.branch_name}"
                )
            )
            mock_impact_service_class.return_value = mock_impact_service

            # Act - Run impact analysis on empty branch
            await service._run_impact_analysis(
                change_order=co,
                branch_name=co.branch_name,  # type: ignore[arg-type]
            )

        # Fetch the updated change order
        result = await db_session.execute(select(type(co)).where(type(co).id == co.id))
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
        service, co = await self._create_co_via_service(db_session)

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
                change_order=co,
                branch_name=co.branch_name,  # type: ignore[arg-type]
            )

        # Fetch the updated change order
        from app.models.domain.change_order import ChangeOrder

        result = await db_session.execute(
            select(ChangeOrder).where(ChangeOrder.id == co.id)
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
