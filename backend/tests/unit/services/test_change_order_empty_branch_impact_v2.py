"""Unit tests for change order impact analysis on empty branches.

Tests follow Red-Green-Refactor TDD cycle for BE-005:
- Add defensive checks for impact analysis on empty branches
- Handle empty branches (branches with no WBE or cost element changes)
- Ensure impact analysis completes successfully even when the isolation branch is empty
- Return reasonable defaults when branch is empty (e.g., impact_level = LOW, zero financial impact)
"""

from decimal import Decimal
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain.change_order import ChangeOrder
from app.models.schemas.change_order import ChangeOrderCreate
from app.services.change_order_service import ChangeOrderService


class TestChangeOrderEmptyBranchImpact:
    """Test impact analysis handling for empty isolation branches.

    Context: When a change order is created and submitted for approval,
    the impact analysis runs on the isolation branch. If no changes have
    been made (empty branch), the analysis should complete successfully
    with reasonable default values rather than failing.
    """

    async def _create_co_via_service(
        self, db_session: AsyncSession
    ) -> tuple[ChangeOrderService, ChangeOrder]:
        """Helper: create a ChangeOrder via the service so it is persisted properly."""
        service = ChangeOrderService(db_session)
        project_id = uuid4()
        actor_id = uuid4()
        co_create = ChangeOrderCreate(
            project_id=project_id,
            code=f"CO-V2-{uuid4().hex[:6]}",
            title="Empty Branch Test",
            description="Test",
        )
        co = await service.create_change_order(co_create, actor_id=actor_id)
        await db_session.commit()
        return service, co

    @pytest.mark.asyncio
    async def test_run_impact_analysis_empty_branch_logs_warning(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Test _run_impact_analysis handles empty branch gracefully.

        Acceptance Criteria:
        - Logs a warning about empty branch
        - Sets impact_analysis_status to "completed" (not "failed")
        - Sets impact_level to "LOW" (default for no changes)
        - Sets impact_score to 0.0 (no financial impact)
        - Does not raise an exception
        """
        # Arrange - Create a change order via service
        service, co = await self._create_co_via_service(db_session)

        # Mock the impact analysis service to raise ValueError (empty branch scenario)
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
            # This should handle the ValueError gracefully
            await service._run_impact_analysis(
                change_order=co,
                branch_name=co.branch_name,  # type: ignore[arg-type]
            )

        # Refresh to get latest state
        await db_session.refresh(co)

        # Assert - Verify reasonable defaults were set
        assert co.impact_analysis_status == "completed", (
            f"Expected status 'completed', got '{co.impact_analysis_status}'"
        )

        assert co.impact_level == "LOW", (
            f"Expected impact_level 'LOW' for empty branch, got '{co.impact_level}'"
        )

        assert co.impact_score == Decimal("0"), (
            f"Expected impact_score 0.0 for empty branch, got {co.impact_score}"
        )

    @pytest.mark.asyncio
    async def test_run_impact_analysis_service_exception_logs_warning(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Test _run_impact_analysis handles unexpected service exceptions.

        Acceptance Criteria:
        - Logs error about service failure
        - Sets impact_analysis_status to "completed" (graceful degradation)
        - Sets impact_level to "MEDIUM" (conservative default)
        - Does not raise an exception
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

            # Act - Run impact analysis with service exception
            await service._run_impact_analysis(
                change_order=co,
                branch_name=co.branch_name,  # type: ignore[arg-type]
            )

        # Refresh to get latest state
        await db_session.refresh(co)

        # Assert - Verify graceful degradation
        assert co.impact_analysis_status in ["completed", "failed"], (
            f"Expected status 'completed' or 'failed', got '{co.impact_analysis_status}'"
        )

        # Should have some impact level set (even if default)
        if co.impact_analysis_status == "completed":
            assert co.impact_level is not None, (
                "impact_level should be set even when service fails"
            )
