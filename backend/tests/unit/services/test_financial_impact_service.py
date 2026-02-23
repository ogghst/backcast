"""Unit tests for FinancialImpactService.

Following TDD RED-GREEN-REFACTOR cycle.

Tests financial impact level calculation for change orders based on
budget deltas between main branch and change order branches.
Implements User Story E06-U09.
"""

from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain.change_order import ChangeOrder, ImpactLevel
from app.models.domain.wbe import WBE
from app.services.financial_impact_service import FinancialImpactService


class TestClassifyImpactLevel:
    """Test _classify_impact_level method with boundary conditions."""

    @pytest.mark.asyncio
    async def test_zero_delta_returns_low(self, db_session: AsyncSession) -> None:
        """RED: Zero budget delta should return LOW impact."""
        # Arrange
        service = FinancialImpactService(db_session)

        # Act
        impact = service._classify_impact_level(Decimal("0"))

        # Assert
        assert impact == ImpactLevel.LOW

    @pytest.mark.asyncio
    async def test_low_boundary_below_threshold(self, db_session: AsyncSession) -> None:
        """RED: 9999.99 EUR should return LOW impact."""
        # Arrange
        service = FinancialImpactService(db_session)

        # Act
        impact = service._classify_impact_level(Decimal("9999.99"))

        # Assert
        assert impact == ImpactLevel.LOW

    @pytest.mark.asyncio
    async def test_low_boundary_at_threshold(self, db_session: AsyncSession) -> None:
        """RED: Exactly 10000 EUR should return MEDIUM impact."""
        # Arrange
        service = FinancialImpactService(db_session)

        # Act
        impact = service._classify_impact_level(Decimal("10000"))

        # Assert
        assert impact == ImpactLevel.MEDIUM

    @pytest.mark.asyncio
    async def test_medium_range_middle(self, db_session: AsyncSession) -> None:
        """RED: 30000 EUR should return MEDIUM impact."""
        # Arrange
        service = FinancialImpactService(db_session)

        # Act
        impact = service._classify_impact_level(Decimal("30000"))

        # Assert
        assert impact == ImpactLevel.MEDIUM

    @pytest.mark.asyncio
    async def test_medium_boundary_at_threshold(self, db_session: AsyncSession) -> None:
        """RED: Exactly 50000 EUR should return HIGH impact."""
        # Arrange
        service = FinancialImpactService(db_session)

        # Act
        impact = service._classify_impact_level(Decimal("50000"))

        # Assert
        assert impact == ImpactLevel.HIGH

    @pytest.mark.asyncio
    async def test_high_range_middle(self, db_session: AsyncSession) -> None:
        """RED: 75000 EUR should return HIGH impact."""
        # Arrange
        service = FinancialImpactService(db_session)

        # Act
        impact = service._classify_impact_level(Decimal("75000"))

        # Assert
        assert impact == ImpactLevel.HIGH

    @pytest.mark.asyncio
    async def test_high_boundary_at_threshold(self, db_session: AsyncSession) -> None:
        """RED: Exactly 100000 EUR should return CRITICAL impact."""
        # Arrange
        service = FinancialImpactService(db_session)

        # Act
        impact = service._classify_impact_level(Decimal("100000"))

        # Assert
        assert impact == ImpactLevel.CRITICAL

    @pytest.mark.asyncio
    async def test_critical_range_lower(self, db_session: AsyncSession) -> None:
        """RED: 150000 EUR should return CRITICAL impact."""
        # Arrange
        service = FinancialImpactService(db_session)

        # Act
        impact = service._classify_impact_level(Decimal("150000"))

        # Assert
        assert impact == ImpactLevel.CRITICAL

    @pytest.mark.asyncio
    async def test_critical_range_upper(self, db_session: AsyncSession) -> None:
        """RED: 1000000 EUR should return CRITICAL impact."""
        # Arrange
        service = FinancialImpactService(db_session)

        # Act
        impact = service._classify_impact_level(Decimal("1000000"))

        # Assert
        assert impact == ImpactLevel.CRITICAL


class TestCalculateImpactLevel:
    """Test calculate_impact_level method with database integration."""

    @pytest.mark.asyncio
    async def test_low_impact_level(self, db_session: AsyncSession) -> None:
        """RED: Small budget delta (5000 EUR) should return LOW impact."""
        # Arrange
        service = FinancialImpactService(db_session)
        project_id = uuid4()
        change_order_id = uuid4()
        code = "CO-001"

        # Create change order
        change_order = ChangeOrder(
            change_order_id=change_order_id,
            code=code,
            project_id=project_id,
            title="Low Impact Change",
            status="Draft",
            impact_level=ImpactLevel.LOW,
            branch="main",
            created_by=uuid4(),
        )
        db_session.add(change_order)
        await db_session.flush()

        # Create WBEs in main branch (total budget: 50000)
        wbe_main_1 = WBE(
            wbe_id=uuid4(),
            project_id=project_id,
            code="1.1",
            name="WBE 1",
            budget_allocation=30000,
            revenue_allocation=35000,
            branch="main",
            created_by=uuid4(),
        )
        wbe_main_2 = WBE(
            wbe_id=uuid4(),
            project_id=project_id,
            code="1.2",
            name="WBE 2",
            budget_allocation=20000,
            revenue_allocation=25000,
            branch="main",
            created_by=uuid4(),
        )
        db_session.add_all([wbe_main_1, wbe_main_2])
        await db_session.flush()

        # Create WBEs in change branch (total budget: 55000, delta: 5000)
        wbe_change_1 = WBE(
            wbe_id=uuid4(),
            project_id=project_id,
            code="1.1",
            name="WBE 1",
            budget_allocation=33000,
            revenue_allocation=38000,
            branch=f"BR-{code}",
            parent_id=wbe_main_1.id,
            created_by=uuid4(),
        )
        wbe_change_2 = WBE(
            wbe_id=uuid4(),
            project_id=project_id,
            code="1.2",
            name="WBE 2",
            budget_allocation=22000,
            revenue_allocation=27000,
            branch=f"BR-{code}",
            parent_id=wbe_main_2.id,
            created_by=uuid4(),
        )
        db_session.add_all([wbe_change_1, wbe_change_2])
        await db_session.flush()

        # Act
        impact = await service.calculate_impact_level(change_order_id)

        # Assert
        assert impact == ImpactLevel.LOW

    @pytest.mark.asyncio
    async def test_medium_impact_level(self, db_session: AsyncSession) -> None:
        """RED: Medium budget delta (25000 EUR) should return MEDIUM impact."""
        # Arrange
        service = FinancialImpactService(db_session)
        project_id = uuid4()
        change_order_id = uuid4()
        code = "CO-002"

        # Create change order
        change_order = ChangeOrder(
            change_order_id=change_order_id,
            code=code,
            project_id=project_id,
            title="Medium Impact Change",
            status="Draft",
            impact_level=ImpactLevel.MEDIUM,
            branch="main",
            created_by=uuid4(),
        )
        db_session.add(change_order)
        await db_session.flush()

        # Create WBEs in main branch (total budget: 50000)
        wbe_main_1 = WBE(
            wbe_id=uuid4(),
            project_id=project_id,
            code="2.1",
            name="WBE 1",
            budget_allocation=30000,
            revenue_allocation=35000,
            branch="main",
            created_by=uuid4(),
        )
        wbe_main_2 = WBE(
            wbe_id=uuid4(),
            project_id=project_id,
            code="2.2",
            name="WBE 2",
            budget_allocation=20000,
            revenue_allocation=25000,
            branch="main",
            created_by=uuid4(),
        )
        db_session.add_all([wbe_main_1, wbe_main_2])
        await db_session.flush()

        # Create WBEs in change branch (total budget: 75000, delta: 25000)
        wbe_change_1 = WBE(
            wbe_id=uuid4(),
            project_id=project_id,
            code="2.1",
            name="WBE 1",
            budget_allocation=45000,
            revenue_allocation=50000,
            branch=f"BR-{code}",
            parent_id=wbe_main_1.id,
            created_by=uuid4(),
        )
        wbe_change_2 = WBE(
            wbe_id=uuid4(),
            project_id=project_id,
            code="2.2",
            name="WBE 2",
            budget_allocation=30000,
            revenue_allocation=35000,
            branch=f"BR-{code}",
            parent_id=wbe_main_2.id,
            created_by=uuid4(),
        )
        db_session.add_all([wbe_change_1, wbe_change_2])
        await db_session.flush()

        # Act
        impact = await service.calculate_impact_level(change_order_id)

        # Assert
        assert impact == ImpactLevel.MEDIUM

    @pytest.mark.asyncio
    async def test_high_impact_level(self, db_session: AsyncSession) -> None:
        """RED: Large budget delta (75000 EUR) should return HIGH impact."""
        # Arrange
        service = FinancialImpactService(db_session)
        project_id = uuid4()
        change_order_id = uuid4()
        code = "CO-003"

        # Create change order
        change_order = ChangeOrder(
            change_order_id=change_order_id,
            code=code,
            project_id=project_id,
            title="High Impact Change",
            status="Draft",
            impact_level=ImpactLevel.HIGH,
            branch="main",
            created_by=uuid4(),
        )
        db_session.add(change_order)
        await db_session.flush()

        # Create WBEs in main branch (total budget: 50000)
        wbe_main_1 = WBE(
            wbe_id=uuid4(),
            project_id=project_id,
            code="3.1",
            name="WBE 1",
            budget_allocation=30000,
            revenue_allocation=35000,
            branch="main",
            created_by=uuid4(),
        )
        wbe_main_2 = WBE(
            wbe_id=uuid4(),
            project_id=project_id,
            code="3.2",
            name="WBE 2",
            budget_allocation=20000,
            revenue_allocation=25000,
            branch="main",
            created_by=uuid4(),
        )
        db_session.add_all([wbe_main_1, wbe_main_2])
        await db_session.flush()

        # Create WBEs in change branch (total budget: 125000, delta: 75000)
        wbe_change_1 = WBE(
            wbe_id=uuid4(),
            project_id=project_id,
            code="3.1",
            name="WBE 1",
            budget_allocation=75000,
            revenue_allocation=80000,
            branch=f"BR-{code}",
            parent_id=wbe_main_1.id,
            created_by=uuid4(),
        )
        wbe_change_2 = WBE(
            wbe_id=uuid4(),
            project_id=project_id,
            code="3.2",
            name="WBE 2",
            budget_allocation=50000,
            revenue_allocation=55000,
            branch=f"BR-{code}",
            parent_id=wbe_main_2.id,
            created_by=uuid4(),
        )
        db_session.add_all([wbe_change_1, wbe_change_2])
        await db_session.flush()

        # Act
        impact = await service.calculate_impact_level(change_order_id)

        # Assert
        assert impact == ImpactLevel.HIGH

    @pytest.mark.asyncio
    async def test_critical_impact_level(self, db_session: AsyncSession) -> None:
        """RED: Very large budget delta (150000 EUR) should return CRITICAL impact."""
        # Arrange
        service = FinancialImpactService(db_session)
        project_id = uuid4()
        change_order_id = uuid4()
        code = "CO-004"

        # Create change order
        change_order = ChangeOrder(
            change_order_id=change_order_id,
            code=code,
            project_id=project_id,
            title="Critical Impact Change",
            status="Draft",
            impact_level=ImpactLevel.CRITICAL,
            branch="main",
            created_by=uuid4(),
        )
        db_session.add(change_order)
        await db_session.flush()

        # Create WBEs in main branch (total budget: 50000)
        wbe_main_1 = WBE(
            wbe_id=uuid4(),
            project_id=project_id,
            code="4.1",
            name="WBE 1",
            budget_allocation=30000,
            revenue_allocation=35000,
            branch="main",
            created_by=uuid4(),
        )
        wbe_main_2 = WBE(
            wbe_id=uuid4(),
            project_id=project_id,
            code="4.2",
            name="WBE 2",
            budget_allocation=20000,
            revenue_allocation=25000,
            branch="main",
            created_by=uuid4(),
        )
        db_session.add_all([wbe_main_1, wbe_main_2])
        await db_session.flush()

        # Create WBEs in change branch (total budget: 200000, delta: 150000)
        wbe_change_1 = WBE(
            wbe_id=uuid4(),
            project_id=project_id,
            code="4.1",
            name="WBE 1",
            budget_allocation=120000,
            revenue_allocation=125000,
            branch=f"BR-{code}",
            parent_id=wbe_main_1.id,
            created_by=uuid4(),
        )
        wbe_change_2 = WBE(
            wbe_id=uuid4(),
            project_id=project_id,
            code="4.2",
            name="WBE 2",
            budget_allocation=80000,
            revenue_allocation=85000,
            branch=f"BR-{code}",
            parent_id=wbe_main_2.id,
            created_by=uuid4(),
        )
        db_session.add_all([wbe_change_1, wbe_change_2])
        await db_session.flush()

        # Act
        impact = await service.calculate_impact_level(change_order_id)

        # Assert
        assert impact == ImpactLevel.CRITICAL

    @pytest.mark.asyncio
    async def test_change_order_not_found_raises_error(
        self, db_session: AsyncSession
    ) -> None:
        """RED: Non-existent change order should raise ValueError."""
        # Arrange
        service = FinancialImpactService(db_session)
        non_existent_id = uuid4()

        # Act & Assert
        with pytest.raises(ValueError, match="Change order .* not found"):
            await service.calculate_impact_level(non_existent_id)

    @pytest.mark.asyncio
    async def test_zero_budget_returns_low(self, db_session: AsyncSession) -> None:
        """RED: Zero budget change should return LOW impact."""
        # Arrange
        service = FinancialImpactService(db_session)
        project_id = uuid4()
        change_order_id = uuid4()
        code = "CO-005"

        # Create change order
        change_order = ChangeOrder(
            change_order_id=change_order_id,
            code=code,
            project_id=project_id,
            title="Zero Budget Change",
            status="Draft",
            impact_level=ImpactLevel.LOW,
            branch="main",
            created_by=uuid4(),
        )
        db_session.add(change_order)
        await db_session.flush()

        # No WBEs created (budget = 0 in both branches)

        # Act
        impact = await service.calculate_impact_level(change_order_id)

        # Assert
        assert impact == ImpactLevel.LOW

    @pytest.mark.asyncio
    async def test_negative_delta_converted_to_absolute(
        self, db_session: AsyncSession
    ) -> None:
        """RED: Budget decrease should use absolute value for impact level."""
        # Arrange
        service = FinancialImpactService(db_session)
        project_id = uuid4()
        change_order_id = uuid4()
        code = "CO-006"

        # Create change order
        change_order = ChangeOrder(
            change_order_id=change_order_id,
            code=code,
            project_id=project_id,
            title="Budget Decrease",
            status="Draft",
            impact_level=ImpactLevel.MEDIUM,
            branch="main",
            created_by=uuid4(),
        )
        db_session.add(change_order)
        await db_session.flush()

        # Create WBEs in main branch (total budget: 75000)
        wbe_main_1 = WBE(
            wbe_id=uuid4(),
            project_id=project_id,
            code="6.1",
            name="WBE 1",
            budget_allocation=45000,
            revenue_allocation=50000,
            branch="main",
            created_by=uuid4(),
        )
        wbe_main_2 = WBE(
            wbe_id=uuid4(),
            project_id=project_id,
            code="6.2",
            name="WBE 2",
            budget_allocation=30000,
            revenue_allocation=35000,
            branch="main",
            created_by=uuid4(),
        )
        db_session.add_all([wbe_main_1, wbe_main_2])
        await db_session.flush()

        # Create WBEs in change branch (total budget: 50000, delta: -25000)
        # Absolute delta is 25000, which is MEDIUM
        wbe_change_1 = WBE(
            wbe_id=uuid4(),
            project_id=project_id,
            code="6.1",
            name="WBE 1",
            budget_allocation=30000,
            revenue_allocation=35000,
            branch=f"BR-{code}",
            parent_id=wbe_main_1.id,
            created_by=uuid4(),
        )
        wbe_change_2 = WBE(
            wbe_id=uuid4(),
            project_id=project_id,
            code="6.2",
            name="WBE 2",
            budget_allocation=20000,
            revenue_allocation=25000,
            branch=f"BR-{code}",
            parent_id=wbe_main_2.id,
            created_by=uuid4(),
        )
        db_session.add_all([wbe_change_1, wbe_change_2])
        await db_session.flush()

        # Act
        impact = await service.calculate_impact_level(change_order_id)

        # Assert - should use absolute delta (25000), so MEDIUM
        assert impact == ImpactLevel.MEDIUM


class TestGetFinancialImpactDetails:
    """Test get_financial_impact_details method."""

    @pytest.mark.asyncio
    async def test_returns_all_expected_fields(self, db_session: AsyncSession) -> None:
        """RED: Should return all 7 expected fields."""
        # Arrange
        service = FinancialImpactService(db_session)
        project_id = uuid4()
        change_order_id = uuid4()
        code = "CO-007"

        # Create change order
        change_order = ChangeOrder(
            change_order_id=change_order_id,
            code=code,
            project_id=project_id,
            title="Test Change",
            status="Draft",
            impact_level=ImpactLevel.LOW,
            branch="main",
            created_by=uuid4(),
        )
        db_session.add(change_order)
        await db_session.flush()

        # Create WBEs in main branch
        wbe_main = WBE(
            wbe_id=uuid4(),
            project_id=project_id,
            code="7.1",
            name="WBE 1",
            budget_allocation=50000,
            revenue_allocation=60000,
            branch="main",
            created_by=uuid4(),
        )
        db_session.add(wbe_main)
        await db_session.flush()

        # Create WBEs in change branch
        wbe_change = WBE(
            wbe_id=uuid4(),
            project_id=project_id,
            code="7.1",
            name="WBE 1",
            budget_allocation=55000,
            revenue_allocation=65000,
            branch=f"BR-{code}",
            parent_id=wbe_main.id,
            created_by=uuid4(),
        )
        db_session.add(wbe_change)
        await db_session.flush()

        # Act
        details = await service.get_financial_impact_details(change_order_id)

        # Assert - check all 7 fields exist
        assert "main_budget" in details
        assert "change_budget" in details
        assert "budget_delta" in details
        assert "main_revenue" in details
        assert "change_revenue" in details
        assert "revenue_delta" in details
        assert "impact_level" in details
        assert len(details) == 7

    @pytest.mark.asyncio
    async def test_budget_calculations_accurate(self, db_session: AsyncSession) -> None:
        """RED: Budget calculations should be accurate."""
        # Arrange
        service = FinancialImpactService(db_session)
        project_id = uuid4()
        change_order_id = uuid4()
        code = "CO-008"

        # Create change order
        change_order = ChangeOrder(
            change_order_id=change_order_id,
            code=code,
            project_id=project_id,
            title="Test Change",
            status="Draft",
            impact_level=ImpactLevel.LOW,
            branch="main",
            created_by=uuid4(),
        )
        db_session.add(change_order)
        await db_session.flush()

        # Create WBEs in main branch (total: 50000)
        wbe_main_1 = WBE(
            wbe_id=uuid4(),
            project_id=project_id,
            code="8.1",
            name="WBE 1",
            budget_allocation=30000,
            revenue_allocation=35000,
            branch="main",
            created_by=uuid4(),
        )
        wbe_main_2 = WBE(
            wbe_id=uuid4(),
            project_id=project_id,
            code="8.2",
            name="WBE 2",
            budget_allocation=20000,
            revenue_allocation=25000,
            branch="main",
            created_by=uuid4(),
        )
        db_session.add_all([wbe_main_1, wbe_main_2])
        await db_session.flush()

        # Create WBEs in change branch (total: 75000, delta: 25000)
        wbe_change_1 = WBE(
            wbe_id=uuid4(),
            project_id=project_id,
            code="8.1",
            name="WBE 1",
            budget_allocation=45000,
            revenue_allocation=50000,
            branch=f"BR-{code}",
            parent_id=wbe_main_1.id,
            created_by=uuid4(),
        )
        wbe_change_2 = WBE(
            wbe_id=uuid4(),
            project_id=project_id,
            code="8.2",
            name="WBE 2",
            budget_allocation=30000,
            revenue_allocation=35000,
            branch=f"BR-{code}",
            parent_id=wbe_main_2.id,
            created_by=uuid4(),
        )
        db_session.add_all([wbe_change_1, wbe_change_2])
        await db_session.flush()

        # Act
        details = await service.get_financial_impact_details(change_order_id)

        # Assert
        assert details["main_budget"] == 50000.0
        assert details["change_budget"] == 75000.0
        assert details["budget_delta"] == 25000.0
        assert details["impact_level"] == ImpactLevel.MEDIUM

    @pytest.mark.asyncio
    async def test_revenue_calculations_accurate(
        self, db_session: AsyncSession
    ) -> None:
        """RED: Revenue calculations should be accurate."""
        # Arrange
        service = FinancialImpactService(db_session)
        project_id = uuid4()
        change_order_id = uuid4()
        code = "CO-009"

        # Create change order
        change_order = ChangeOrder(
            change_order_id=change_order_id,
            code=code,
            project_id=project_id,
            title="Test Change",
            status="Draft",
            impact_level=ImpactLevel.LOW,
            branch="main",
            created_by=uuid4(),
        )
        db_session.add(change_order)
        await db_session.flush()

        # Create WBEs in main branch (revenue: 60000)
        wbe_main_1 = WBE(
            wbe_id=uuid4(),
            project_id=project_id,
            code="9.1",
            name="WBE 1",
            budget_allocation=30000,
            revenue_allocation=35000,
            branch="main",
            created_by=uuid4(),
        )
        wbe_main_2 = WBE(
            wbe_id=uuid4(),
            project_id=project_id,
            code="9.2",
            name="WBE 2",
            budget_allocation=20000,
            revenue_allocation=25000,
            branch="main",
            created_by=uuid4(),
        )
        db_session.add_all([wbe_main_1, wbe_main_2])
        await db_session.flush()

        # Create WBEs in change branch (revenue: 85000, delta: 25000)
        wbe_change_1 = WBE(
            wbe_id=uuid4(),
            project_id=project_id,
            code="9.1",
            name="WBE 1",
            budget_allocation=45000,
            revenue_allocation=50000,
            branch=f"BR-{code}",
            parent_id=wbe_main_1.id,
            created_by=uuid4(),
        )
        wbe_change_2 = WBE(
            wbe_id=uuid4(),
            project_id=project_id,
            code="9.2",
            name="WBE 2",
            budget_allocation=30000,
            revenue_allocation=35000,
            branch=f"BR-{code}",
            parent_id=wbe_main_2.id,
            created_by=uuid4(),
        )
        db_session.add_all([wbe_change_1, wbe_change_2])
        await db_session.flush()

        # Act
        details = await service.get_financial_impact_details(change_order_id)

        # Assert
        assert details["main_revenue"] == 60000.0
        assert details["change_revenue"] == 85000.0
        assert details["revenue_delta"] == 25000.0

    @pytest.mark.asyncio
    async def test_change_order_not_found_raises_error_details(
        self, db_session: AsyncSession
    ) -> None:
        """RED: Non-existent change order should raise ValueError for details."""
        # Arrange
        service = FinancialImpactService(db_session)
        non_existent_id = uuid4()

        # Act & Assert
        with pytest.raises(ValueError, match="Change order .* not found"):
            await service.get_financial_impact_details(non_existent_id)

    @pytest.mark.asyncio
    async def test_zero_budget_revenue_details(self, db_session: AsyncSession) -> None:
        """RED: Should handle zero budget and revenue correctly."""
        # Arrange
        service = FinancialImpactService(db_session)
        project_id = uuid4()
        change_order_id = uuid4()
        code = "CO-010"

        # Create change order
        change_order = ChangeOrder(
            change_order_id=change_order_id,
            code=code,
            project_id=project_id,
            title="Empty Change",
            status="Draft",
            impact_level=ImpactLevel.LOW,
            branch="main",
            created_by=uuid4(),
        )
        db_session.add(change_order)
        await db_session.flush()

        # No WBEs created

        # Act
        details = await service.get_financial_impact_details(change_order_id)

        # Assert
        assert details["main_budget"] == 0.0
        assert details["change_budget"] == 0.0
        assert details["budget_delta"] == 0.0
        assert details["main_revenue"] == 0.0
        assert details["change_revenue"] == 0.0
        assert details["revenue_delta"] == 0.0
        assert details["impact_level"] == ImpactLevel.LOW
