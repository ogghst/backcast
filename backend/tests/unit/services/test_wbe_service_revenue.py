"""Unit tests for WBE revenue allocation validation - Minimal version.

Tests T-001 through T-009 from the plan document.
Following RED-GREEN-REFACTOR TDD methodology.
"""

from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain.project import Project
from app.models.schemas.wbe import WBECreate, WBEUpdate
from app.services.wbe import WBEService


@pytest.mark.asyncio
class TestWBERevenueAllocationValidation:
    """Test suite for revenue allocation validation logic."""

    async def test_validate_revenue_allocation_with_exact_match_passes(
        self,
        db_session: AsyncSession,
    ):
        """T-001: Validation passes when sum of WBE revenues equals project.contract_value.

        Note: With Option 2 (lenient validation), WBEs can be created incrementally
        as long as the total doesn't exceed the contract value. This test creates WBEs
        incrementally and verifies the final state matches the contract value.
        """
        # Arrange
        user_id = uuid4()
        project = Project(
            project_id=uuid4(),
            code="PRJ-001",
            name="Test Project",
            contract_value=Decimal("100000.00"),
            branch="main",
            created_by=user_id,
        )
        db_session.add(project)
        await db_session.commit()

        service = WBEService(db_session)

        # Create WBEs incrementally (allowed by Option 2)
        # WBE 1: 50,000
        wbe1 = await service.create_wbe(
            WBECreate(
                project_id=project.project_id,
                code="1.1",
                name="WBE 1",
                budget_allocation=Decimal("50000.00"),
                revenue_allocation=Decimal("50000.00"),  # 50% of contract
                branch="main",
            ),
            user_id,
        )
        assert wbe1.revenue_allocation == Decimal("50000.00")

        # WBE 2: 50,000 (total = 100,000 = contract)
        wbe2 = await service.create_wbe(
            WBECreate(
                project_id=project.project_id,
                code="1.2",
                name="WBE 2",
                budget_allocation=Decimal("50000.00"),
                revenue_allocation=Decimal("50000.00"),  # 50% of contract
                branch="main",
            ),
            user_id,
        )
        assert wbe2.revenue_allocation == Decimal("50000.00")

        # Verify total matches contract value
        wbes = await service.get_by_project(project.project_id)
        total_revenue = sum(w.revenue_allocation or Decimal("0") for w in wbes)
        assert total_revenue == Decimal("100000.00")

    async def test_validate_revenue_allocation_exceeds_contract_raises_error(
        self,
        db_session: AsyncSession,
    ):
        """T-002: Raises ValueError when total revenue > contract_value."""
        # Arrange
        user_id = uuid4()
        project = Project(
            project_id=uuid4(),
            code="PRJ-002",
            name="Test Project Exceed",
            contract_value=Decimal("100000.00"),
            branch="main",
            created_by=user_id,
        )
        db_session.add(project)
        await db_session.commit()

        service = WBEService(db_session)

        await service.create_wbe(
            WBECreate(
                project_id=project.project_id,
                code="1.1",
                name="WBE 1",
                budget_allocation=Decimal("60000.00"),
                revenue_allocation=Decimal("60000.00"),
                branch="main",
            ),
            user_id,
        )

        # Act & Assert: Should raise ValueError
        with pytest.raises(ValueError) as exc_info:
            await service.create_wbe(
                WBECreate(
                    project_id=project.project_id,
                    code="1.2",
                    name="WBE 2",
                    budget_allocation=Decimal("50000.00"),
                    revenue_allocation=Decimal("50000.00"),
                    branch="main",
                ),
                user_id,
            )

        error_msg = str(exc_info.value)
        assert "110,000" in error_msg
        assert "100,000" in error_msg
        assert "10,000" in error_msg
        assert "exceeds" in error_msg.lower()

    async def test_validate_revenue_allocation_with_none_contract_value_skips(
        self,
        db_session: AsyncSession,
    ):
        """T-004: Validation returns None (no error) when project.contract_value is None."""
        # Arrange
        user_id = uuid4()
        project = Project(
            project_id=uuid4(),
            code="PRJ-004",
            name="Test Project No Contract",
            contract_value=None,
            branch="main",
            created_by=user_id,
        )
        db_session.add(project)
        await db_session.commit()

        service = WBEService(db_session)

        # Act: Should succeed without validation
        wbe = await service.create_wbe(
            WBECreate(
                project_id=project.project_id,
                code="1.1",
                name="WBE 1",
                budget_allocation=Decimal("50000.00"),
                revenue_allocation=Decimal("999999.99"),
                branch="main",
            ),
            user_id,
        )

        assert wbe.revenue_allocation == Decimal("999999.99")

    async def test_validate_revenue_allocation_update_workflow(
        self,
        db_session: AsyncSession,
    ):
        """T-003: Update validation modifies WBE revenue and validates correctly.

        Tests the workflow where a user updates a WBE's revenue allocation.
        The validation should check the new total including the updated value.
        """
        # Arrange
        user_id = uuid4()
        project = Project(
            project_id=uuid4(),
            code="PRJ-003",
            name="Test Project Update",
            contract_value=Decimal("100000.00"),
            branch="main",
            created_by=user_id,
        )
        db_session.add(project)
        await db_session.commit()

        service = WBEService(db_session)

        # Create initial WBE with 40,000
        wbe1 = await service.create_wbe(
            WBECreate(
                project_id=project.project_id,
                code="1.1",
                name="WBE 1",
                budget_allocation=Decimal("50000.00"),
                revenue_allocation=Decimal("40000.00"),
                branch="main",
            ),
            user_id,
        )

        # Create second WBE with 40,000 (total = 80,000, under contract)
        await service.create_wbe(
            WBECreate(
                project_id=project.project_id,
                code="1.2",
                name="WBE 2",
                budget_allocation=Decimal("50000.00"),
                revenue_allocation=Decimal("40000.00"),
                branch="main",
            ),
            user_id,
        )

        # Act: Update WBE 1 to 60,000 (total = 100,000, matches contract)
        wbe1_updated = await service.update_wbe(
            wbe1.wbe_id,
            WBEUpdate(revenue_allocation=Decimal("60000.00")),
            user_id,
        )

        # Assert: Update succeeds
        assert wbe1_updated.revenue_allocation == Decimal("60000.00")

        # Verify total matches contract value
        await db_session.commit()  # Ensure transaction is committed
        wbes = await service.get_by_project(project.project_id)
        total_revenue = sum(w.revenue_allocation or Decimal("0") for w in wbes)
        assert total_revenue == Decimal("100000.00")

    async def test_validate_revenue_allocation_under_contract_allowed(
        self,
        db_session: AsyncSession,
    ):
        """T-005: Validation allows total revenue < contract_value (intermediate state).

        Option 2 (lenient validation) allows partial allocation during workflow.
        Only exceeding the contract value is rejected.
        """
        # Arrange
        user_id = uuid4()
        project = Project(
            project_id=uuid4(),
            code="PRJ-005",
            name="Test Project Under",
            contract_value=Decimal("100000.00"),
            branch="main",
            created_by=user_id,
        )
        db_session.add(project)
        await db_session.commit()

        service = WBEService(db_session)

        # Act: Create WBE with revenue less than contract (partial allocation)
        wbe = await service.create_wbe(
            WBECreate(
                project_id=project.project_id,
                code="1.1",
                name="WBE 1",
                budget_allocation=Decimal("50000.00"),
                revenue_allocation=Decimal("30000.00"),  # Only 30% allocated
                branch="main",
            ),
            user_id,
        )

        # Assert: Creation succeeds (Option 2 allows intermediate states)
        assert wbe.revenue_allocation == Decimal("30000.00")

    async def test_validate_revenue_allocation_branch_isolation(
        self,
        db_session: AsyncSession,
    ):
        """T-006: Validation respects branch isolation.

        Revenue allocations in one branch should not affect validation
        in another branch. Each branch has its own allocation tracking.
        """
        # Arrange
        user_id = uuid4()
        project = Project(
            project_id=uuid4(),
            code="PRJ-006",
            name="Test Project Branch",
            contract_value=Decimal("100000.00"),
            branch="main",
            created_by=user_id,
        )
        db_session.add(project)
        await db_session.commit()

        service = WBEService(db_session)

        # Create WBE in main branch with full allocation
        wbe_main = await service.create_wbe(
            WBECreate(
                project_id=project.project_id,
                code="1.1",
                name="WBE Main",
                budget_allocation=Decimal("100000.00"),
                revenue_allocation=Decimal("100000.00"),
                branch="main",
            ),
            user_id,
        )

        # Act: Create WBE in different branch with same allocation
        # This should succeed because branches are isolated
        wbe_branch = await service.create_wbe(
            WBECreate(
                project_id=project.project_id,
                code="1.1",
                name="WBE Branch",
                budget_allocation=Decimal("100000.00"),
                revenue_allocation=Decimal("100000.00"),
                branch="BR-1",  # Different branch
            ),
            user_id,
        )

        # Assert: Both WBEs created successfully
        assert wbe_main.revenue_allocation == Decimal("100000.00")
        assert wbe_branch.revenue_allocation == Decimal("100000.00")

        # Verify each branch has correct total
        wbes_main = await service.get_by_project(project.project_id, branch="main")
        total_main = sum(w.revenue_allocation or Decimal("0") for w in wbes_main)
        assert total_main == Decimal("100000.00")

        wbes_branch = await service.get_by_project(project.project_id, branch="BR-1")
        total_branch = sum(w.revenue_allocation or Decimal("0") for w in wbes_branch)
        assert total_branch == Decimal("100000.00")

    async def test_validate_revenue_allocation_soft_deleted_excluded(
        self,
        db_session: AsyncSession,
    ):
        """T-007: Soft-deleted WBEs are excluded from revenue allocation validation.

        When a WBE is soft-deleted, its revenue allocation should not be
        counted in the total. This allows re-allocation of that revenue.
        """
        # Arrange
        user_id = uuid4()
        project = Project(
            project_id=uuid4(),
            code="PRJ-007",
            name="Test Project Soft Delete",
            contract_value=Decimal("100000.00"),
            branch="main",
            created_by=user_id,
        )
        db_session.add(project)
        await db_session.commit()

        service = WBEService(db_session)

        # Create WBE 1 with 50,000
        wbe1 = await service.create_wbe(
            WBECreate(
                project_id=project.project_id,
                code="1.1",
                name="WBE 1",
                budget_allocation=Decimal("50000.00"),
                revenue_allocation=Decimal("50000.00"),
                branch="main",
            ),
            user_id,
        )

        # Create WBE 2 with 50,000 (total = 100,000)
        await service.create_wbe(
            WBECreate(
                project_id=project.project_id,
                code="1.2",
                name="WBE 2",
                budget_allocation=Decimal("50000.00"),
                revenue_allocation=Decimal("50000.00"),
                branch="main",
            ),
            user_id,
        )

        # Act: Soft-delete WBE 1
        await service.delete_wbe(wbe1.wbe_id, user_id)

        # Act: Create WBE 3 with 50,000
        # This should succeed because WBE 1 is deleted (total = 50,000 + 50,000 = 100,000)
        wbe3 = await service.create_wbe(
            WBECreate(
                project_id=project.project_id,
                code="1.3",
                name="WBE 3",
                budget_allocation=Decimal("50000.00"),
                revenue_allocation=Decimal("50000.00"),
                branch="main",
            ),
            user_id,
        )

        # Assert: WBE 3 created successfully
        assert wbe3.revenue_allocation == Decimal("50000.00")

        # Verify total (excluding deleted WBE 1)
        wbes = await service.get_by_project(project.project_id)
        total_revenue = sum(w.revenue_allocation or Decimal("0") for w in wbes)
        assert total_revenue == Decimal("100000.00")

    async def test_validate_revenue_allocation_decimal_precision(
        self,
        db_session: AsyncSession,
    ):
        """T-008: Decimal precision handling works correctly.

        Revenue allocations use DECIMAL(15, 2) for currency precision.
        Validation should quantize to 2 decimal places for comparison.
        """
        # Arrange
        user_id = uuid4()
        project = Project(
            project_id=uuid4(),
            code="PRJ-008",
            name="Test Project Precision",
            contract_value=Decimal("100000.00"),
            branch="main",
            created_by=user_id,
        )
        db_session.add(project)
        await db_session.commit()

        service = WBEService(db_session)

        # Act: Create WBE with precise decimal values
        wbe1 = await service.create_wbe(
            WBECreate(
                project_id=project.project_id,
                code="1.1",
                name="WBE 1",
                budget_allocation=Decimal("50000.00"),
                revenue_allocation=Decimal("33333.33"),  # Precise to 2 decimals
                branch="main",
            ),
            user_id,
        )

        wbe2 = await service.create_wbe(
            WBECreate(
                project_id=project.project_id,
                code="1.2",
                name="WBE 2",
                budget_allocation=Decimal("50000.00"),
                revenue_allocation=Decimal("66666.67"),  # Complements to 100,000.00
                branch="main",
            ),
            user_id,
        )

        # Assert: Both created successfully
        assert wbe1.revenue_allocation == Decimal("33333.33")
        assert wbe2.revenue_allocation == Decimal("66666.67")

        # Verify total matches exactly (100,000.00)
        wbes = await service.get_by_project(project.project_id)
        total_revenue = sum(w.revenue_allocation or Decimal("0") for w in wbes)
        assert total_revenue == Decimal("100000.00")

    async def test_validate_revenue_allocation_multiple_wbes_sequential(
        self,
        db_session: AsyncSession,
    ):
        """T-009: Multiple WBEs can be created sequentially with incremental allocation.

        Tests the full workflow of creating multiple WBEs one after another,
        gradually allocating the full contract value.
        """
        # Arrange
        user_id = uuid4()
        project = Project(
            project_id=uuid4(),
            code="PRJ-009",
            name="Test Project Sequential",
            contract_value=Decimal("100000.00"),
            branch="main",
            created_by=user_id,
        )
        db_session.add(project)
        await db_session.commit()

        service = WBEService(db_session)

        # Act: Create 3 WBEs sequentially
        wbe1 = await service.create_wbe(
            WBECreate(
                project_id=project.project_id,
                code="1.1",
                name="WBE 1",
                budget_allocation=Decimal("33333.34"),
                revenue_allocation=Decimal("33333.34"),
                branch="main",
            ),
            user_id,
        )
        assert wbe1.revenue_allocation == Decimal("33333.34")

        wbe2 = await service.create_wbe(
            WBECreate(
                project_id=project.project_id,
                code="1.2",
                name="WBE 2",
                budget_allocation=Decimal("33333.33"),
                revenue_allocation=Decimal("33333.33"),
                branch="main",
            ),
            user_id,
        )
        assert wbe2.revenue_allocation == Decimal("33333.33")

        wbe3 = await service.create_wbe(
            WBECreate(
                project_id=project.project_id,
                code="1.3",
                name="WBE 3",
                budget_allocation=Decimal("33333.33"),
                revenue_allocation=Decimal("33333.33"),
                branch="main",
            ),
            user_id,
        )
        assert wbe3.revenue_allocation == Decimal("33333.33")

        # Assert: Verify total matches contract value
        wbes = await service.get_by_project(project.project_id)
        total_revenue = sum(w.revenue_allocation or Decimal("0") for w in wbes)
        assert total_revenue == Decimal("100000.00")
