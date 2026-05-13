"""Unit tests for change order impact analysis on empty branches.

Tests follow Red-Green-Refactor TDD cycle for BE-005:
- Add defensive checks for impact analysis on empty branches
- Handle empty branches (branches with no WBE or cost element changes)
- Ensure impact analysis completes successfully even when the isolation branch is empty
- Return reasonable defaults when branch is empty (e.g., impact_level = LOW, zero financial impact)
"""

from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import ChangeOrderStatus
from app.models.domain.project import Project
from app.models.domain.wbe import WBE
from app.services.change_order_service import ChangeOrderService


class TestChangeOrderEmptyBranchImpact:
    """Test impact analysis handling for empty isolation branches.

    Context: When a change order is created and submitted for approval,
    the impact analysis runs on the isolation branch. If no changes have
    been made (empty branch), the analysis should complete successfully
    with reasonable default values rather than failing.
    """

    @pytest.mark.asyncio
    async def test_impact_analysis_empty_branch(
        self,
        db_session: AsyncSession,
        test_project: Project,
        test_user_id: uuid4,
    ) -> None:
        """Test impact analysis completes successfully on empty isolation branch.

        Acceptance Criteria:
        - Impact analysis status changes to "completed"
        - Impact level is set to "LOW" (no changes = low impact)
        - Impact score is 0.0 (no financial impact)
        - Zero budget delta
        - Zero revenue delta
        - No errors raised

        This is the RED phase test - it will fail until we implement the fix.
        """
        # Arrange - Create a change order
        service = ChangeOrderService(db_session)
        from app.models.schemas.change_order import ChangeOrderCreate

        co_code = "CO-2026-001"
        change_order_in = ChangeOrderCreate(
            code=co_code,
            project_id=test_project.project_id,
            title="Test Change Order",
            description="Test change order with empty branch",
            status=ChangeOrderStatus.DRAFT,
            justification="Testing empty branch handling",
        )

        # Create the change order (this creates the isolation branch)
        change_order = await service.create_change_order(
            change_order_in=change_order_in,
            actor_id=test_user_id,
        )

        # Verify the isolation branch exists but is empty
        assert change_order.branch_name == f"BR-{co_code}"
        isolation_branch = change_order.branch_name

        # Verify no WBEs or cost elements exist on the isolation branch
        from typing import Any, cast

        from sqlalchemy import func, select

        # Check for WBEs on isolation branch
        wbe_stmt = select(WBE).where(
            WBE.project_id == test_project.project_id,
            WBE.branch == isolation_branch,
            func.upper(cast(Any, WBE).valid_time).is_(None),
            cast(Any, WBE).deleted_at.is_(None),
        )
        wbe_result = await db_session.execute(wbe_stmt)
        wbes = wbe_result.scalars().all()
        assert len(wbes) == 0, "Isolation branch should have no WBEs"

        # Act - Run impact analysis on the empty branch
        # This should NOT raise an error
        try:
            await service._run_impact_analysis(change_order, isolation_branch)
            await db_session.commit()
            await db_session.refresh(change_order)
        except Exception as e:
            # If this fails, we're in RED phase
            pytest.fail(f"Impact analysis failed on empty branch: {e}")

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

        # Verify impact analysis results contain expected structure
        assert change_order.impact_analysis_results is not None, (
            "impact_analysis_results should be populated"
        )

        # Check for zero financial impact in results
        results = change_order.impact_analysis_results
        if "kpi_scorecard" in results:
            kpi = results["kpi_scorecard"]
            if "budget_delta" in kpi:
                # Budget delta should be 0 for empty branch
                assert kpi["budget_delta"]["delta"] == 0, (
                    f"Expected zero budget delta for empty branch, got {kpi['budget_delta']['delta']}"
                )
            if "revenue_delta" in kpi:
                # Revenue delta should be 0 for empty branch
                assert kpi["revenue_delta"]["delta"] == 0, (
                    f"Expected zero revenue delta for empty branch, got {kpi['revenue_delta']['delta']}"
                )

    @pytest.mark.asyncio
    async def test_submit_for_approval_with_empty_branch(
        self,
        db_session: AsyncSession,
        test_project: Project,
        test_user_id: uuid4,
    ) -> None:
        """Test submit_for_approval works correctly with empty isolation branch.

        Acceptance Criteria:
        - Status changes to "submitted_for_approval"
        - Impact analysis completes successfully
        - Impact level is set to "LOW"
        - Approver is assigned based on LOW impact level
        - No errors raised during submission

        This tests the full workflow through submit_for_approval.
        """
        # Arrange - Create a draft change order
        service = ChangeOrderService(db_session)
        from app.models.schemas.change_order import ChangeOrderCreate

        co_code = "CO-2026-002"
        change_order_in = ChangeOrderCreate(
            code=co_code,
            project_id=test_project.project_id,
            title="Test Change Order",
            description="Test change order with empty branch",
            status=ChangeOrderStatus.DRAFT,
            justification="Testing empty branch handling",
        )

        change_order = await service.create_change_order(
            change_order_in=change_order_in,
            actor_id=test_user_id,
        )

        # Act - Submit for approval (triggers impact analysis)
        try:
            updated_co = await service.submit_for_approval(
                change_order_id=change_order.change_order_id,
                actor_id=test_user_id,
                comment="Submitting change order with empty branch",
            )
        except Exception as e:
            # If this fails, we're in RED phase
            pytest.fail(f"submit_for_approval failed on empty branch: {e}")

        # Assert - Verify successful submission
        assert updated_co.status == "submitted_for_approval", (
            f"Expected status 'submitted_for_approval', got '{updated_co.status}'"
        )

        assert updated_co.impact_analysis_status == "completed", (
            f"Expected impact_analysis_status 'completed', got '{updated_co.impact_analysis_status}'"
        )

        assert updated_co.impact_level == "LOW", (
            f"Expected impact_level 'LOW' for empty branch, got '{updated_co.impact_level}'"
        )

        # Verify SLA tracking was set
        assert updated_co.sla_assigned_at is not None, (
            "sla_assigned_at should be set after submission"
        )
        assert updated_co.sla_due_date is not None, (
            "sla_due_date should be set after submission"
        )
        assert updated_co.sla_status == "pending", (
            f"Expected sla_status 'pending', got '{updated_co.sla_status}'"
        )
