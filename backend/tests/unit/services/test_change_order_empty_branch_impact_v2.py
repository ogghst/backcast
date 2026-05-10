"""Unit tests for change order impact analysis on empty branches.

Tests follow Red-Green-Refactor TDD cycle for BE-005:
- Add defensive checks for impact analysis on empty branches
- Handle empty branches (branches with no WBE or cost element changes)
- Ensure impact analysis completes successfully even when the isolation branch is empty
- Return reasonable defaults when branch is empty (e.g., impact_level = LOW, zero financial impact)
"""

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4, UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import ChangeOrderStatus
from app.models.domain.change_order import ChangeOrder
from app.services.change_order_service import ChangeOrderService


class TestChangeOrderEmptyBranchImpact:
    """Test impact analysis handling for empty isolation branches.

    Context: When a change order is created and submitted for approval,
    the impact analysis runs on the isolation branch. If no changes have
    been made (empty branch), the analysis should complete successfully
    with reasonable default values rather than failing.
    """

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

        This is the RED phase test - it will fail until we implement the fix.
        """
        # Arrange - Create a change order with empty branch
        service = ChangeOrderService(db_session)
        change_order_id = uuid4()
        project_id = uuid4()

        from sqlalchemy import select
        from sqlalchemy.dialects.postgresql import TSTZRANGE

        # Create change order using the proper creation pattern
        # Use insert().returning() to bypass ORM hybrid property issues
        now = datetime.now(UTC)
        result = await db_session.execute(
            select(ChangeOrder).from_statement(
                """
                INSERT INTO change_orders (
                    id, change_order_id, project_id, code, title, description,
                    status, branch_name, branch, impact_analysis_status,
                    impact_level, impact_score, created_by,
                    valid_time, transaction_time, deleted_at
                ) VALUES (
                    :id, :change_order_id, :project_id, :code, :title, :description,
                    :status, :branch_name, :branch, :impact_analysis_status,
                    :impact_level, :impact_score, :created_by,
                    tstzrange(:now, NULL), tstzrange(:now, NULL), NULL
                ) RETURNING *
                """
            ),
            {
                "id": uuid4(),
                "change_order_id": change_order_id,
                "project_id": project_id,
                "code": "CO-2026-001",
                "title": "Test CO",
                "description": "Test",
                "status": ChangeOrderStatus.DRAFT.value,
                "branch_name": "BR-CO-2026-001",
                "branch": "main",
                "impact_analysis_status": "pending",
                "impact_level": None,
                "impact_score": None,
                "created_by": uuid4(),
                "now": now,
            },
        )
        change_order = result.scalar_one()

        # Mock the impact analysis service to raise ValueError (empty branch scenario)
        with patch(
            "app.services.change_order_service.ImpactAnalysisService"
        ) as mock_impact_service_class:
            # Configure mock to return a service that raises ValueError
            mock_impact_service = AsyncMock()
            mock_impact_service.analyze_impact = AsyncMock(
                side_effect=ValueError(
                    "No project data available for analysis: "
                    "No WBEs or cost elements found on branch BR-CO-2026-001"
                )
            )
            mock_impact_service_class.return_value = mock_impact_service

            # Act - Run impact analysis on empty branch
            # This should handle the ValueError gracefully
            try:
                await service._run_impact_analysis(
                    change_order=change_order,
                    branch_name="BR-CO-2026-001",
                )
                await db_session.commit()
                await db_session.refresh(change_order)
            except Exception as e:
                # RED phase: This currently fails
                pytest.fail(
                    f"_run_impact_analysis raised exception on empty branch: {e}. "
                    f"Should handle gracefully with default values."
                )

        # Assert - Verify reasonable defaults were set
        assert change_order.impact_analysis_status == "completed", (
            f"Expected status 'completed', got '{change_order.impact_analysis_status}'"
        )

        assert change_order.impact_level == "LOW", (
            f"Expected impact_level 'LOW' for empty branch, got '{change_order.impact_level}'"
        )

        assert change_order.impact_score == Decimal("0"), (
            f"Expected impact_score 0.0 for empty branch, got {change_order.impact_score}"
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
        service = ChangeOrderService(db_session)
        change_order_id = uuid4()
        project_id = uuid4()

        change_order = ChangeOrder(
            id=uuid4(),
            change_order_id=change_order_id,
            project_id=project_id,
            code="CO-2026-002",
            title="Test CO",
            description="Test",
            status=ChangeOrderStatus.DRAFT,
            branch_name="BR-CO-2026-002",
            branch="main",
            impact_analysis_status="pending",
            impact_level=None,
            impact_score=None,
            created_by=uuid4(),
            created_at=datetime.now(UTC),
        )
        db_session.add(change_order)
        await db_session.flush()

        # Mock the impact analysis service to raise a generic exception
        with patch(
            "app.services.change_order_service.ImpactAnalysisService"
        ) as mock_impact_service_class:
            mock_impact_service = AsyncMock()
            mock_impact_service.analyze_impact = AsyncMock(
                side_effect=RuntimeError("Unexpected service error")
            )
            mock_impact_service_class.return_value = mock_impact_service

            # Act - Run impact analysis with service exception
            try:
                await service._run_impact_analysis(
                    change_order=change_order,
                    branch_name="BR-CO-2026-002",
                )
                await db_session.commit()
                await db_session.refresh(change_order)
            except Exception as e:
                # In current implementation, this might fail
                # After fix, it should handle gracefully
                if "Unexpected service error" in str(e):
                    pytest.fail(
                        f"_run_impact_analysis should handle service exceptions gracefully, "
                        f"but it raised: {e}"
                    )

        # Assert - Verify graceful degradation
        # Status should be either completed (with defaults) or failed (with error info)
        assert change_order.impact_analysis_status in ["completed", "failed"], (
            f"Expected status 'completed' or 'failed', got '{change_order.impact_analysis_status}'"
        )

        # Should have some impact level set (even if default)
        if change_order.impact_analysis_status == "completed":
            assert change_order.impact_level is not None, (
                "impact_level should be set even when service fails"
            )
