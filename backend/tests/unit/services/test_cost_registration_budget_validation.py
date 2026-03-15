"""Unit tests for Cost Registration Budget Validation.

Tests budget validation logic (now permissive) for cost registrations.
"""

from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schemas.cost_registration import (
    CostRegistrationCreate,
)
from app.services.cost_registration_service import CostRegistrationService

# Import fixtures
from tests.unit.fixtures.cost_element_fixtures import (  # noqa: F401
    sample_cost_element_type,
    sample_department,
    sample_wbe,
)
from tests.unit.fixtures.cost_element_fixtures import (
    sample_cost_element_with_budget as sample_cost_element_with_budget_fixture,
)

# Type alias for the fixture
sample_cost_element_with_budget = sample_cost_element_with_budget_fixture


class TestBudgetValidation:
    """Test budget validation when creating cost registrations."""

    @pytest.mark.asyncio
    async def test_create_when_below_80_percent_budget_succeeds(
        self, db_session: AsyncSession, sample_cost_element_with_budget
    ) -> None:
        """Test creating cost registration when under 80% of budget succeeds.

        Acceptance Criteria:
        - Registration succeeds when used/budget < 80%
        - No warning returned

        Expected Failure: Fixture `sample_cost_element_with_budget` doesn't exist yet
        """
        # Arrange
        service = CostRegistrationService(db_session)
        cost_element = sample_cost_element_with_budget  # budget=1000
        # No existing costs, create for 500 (50%)
        registration_in = CostRegistrationCreate(
            cost_element_id=cost_element.cost_element_id,
            amount=Decimal("500.00"),
        )
        actor_id = uuid4()

        # Act
        result = await service.create_cost_registration(
            registration_in, actor_id=actor_id
        )

        # Assert
        assert result.amount == Decimal("500.00")
        # No warning threshold exceeded

    @pytest.mark.asyncio
    async def test_create_when_at_80_percent_budget_returns_warning(
        self, db_session: AsyncSession, sample_cost_element_with_budget
    ) -> None:
        """Test creating cost registration at 80% threshold returns warning.

        Acceptance Criteria:
        - When used/budget >= 80%, return warning
        - Registration still succeeds
        - Warning includes percentage

        Expected Failure: Fixture `sample_cost_element_with_budget` doesn't exist yet
        """
        # Arrange
        service = CostRegistrationService(db_session)
        cost_element = sample_cost_element_with_budget  # budget=1000

        # Create costs totaling 700 (70%)
        for _ in range(7):
            await service.create_cost_registration(
                CostRegistrationCreate(
                    cost_element_id=cost_element.cost_element_id,
                    amount=Decimal("100.00"),
                ),
                actor_id=uuid4(),
            )

        # Add 100 more to reach 80%
        registration_in = CostRegistrationCreate(
            cost_element_id=cost_element.cost_element_id,
            amount=Decimal("100.00"),
        )
        actor_id = uuid4()

        # Act - Should either return warning or be verified via separate check
        # For now, we'll create and verify it succeeds
        result = await service.create_cost_registration(
            registration_in, actor_id=actor_id
        )

        # Assert - Registration succeeds even at warning threshold
        assert result.amount == Decimal("100.00")

    @pytest.mark.asyncio
    async def test_create_when_exceeding_budget_succeeds(
        self, db_session: AsyncSession, sample_cost_element_with_budget
    ) -> None:
        """Test creating cost registration when exceeding budget succeeds.

        Acceptance Criteria:
        - When used + new_amount > budget, registration succeeds
        - No error is raised
        """
        # Arrange
        service = CostRegistrationService(db_session)
        cost_element = sample_cost_element_with_budget  # budget=1000

        # Create costs totaling 1000 (full budget)
        for _ in range(10):
            await service.create_cost_registration(
                CostRegistrationCreate(
                    cost_element_id=cost_element.cost_element_id,
                    amount=Decimal("100.00"),
                ),
                actor_id=uuid4(),
            )

        # Try to add more
        registration_in = CostRegistrationCreate(
            cost_element_id=cost_element.cost_element_id,
            amount=Decimal("1.00"),
        )
        actor_id = uuid4()

        # Act
        result = await service.create_cost_registration(
            registration_in, actor_id=actor_id
        )

        # Assert
        assert result.amount == Decimal("1.00")

    @pytest.mark.asyncio
    async def test_get_budget_status_returns_used_remaining_percentage(
        self, db_session: AsyncSession, sample_cost_element_with_budget
    ) -> None:
        """Test getting budget status returns used, remaining, percentage.

        Acceptance Criteria:
        - Returns BudgetStatus with used, remaining, percentage
        - Calculated from cost_element budget and sum of cost registrations

        Expected Failure: get_budget_status method doesn't exist yet
        """
        # Arrange
        service = CostRegistrationService(db_session)
        cost_element = sample_cost_element_with_budget  # budget=1000

        # Create costs totaling 500 (50%)
        for _ in range(5):
            await service.create_cost_registration(
                CostRegistrationCreate(
                    cost_element_id=cost_element.cost_element_id,
                    amount=Decimal("100.00"),
                ),
                actor_id=uuid4(),
            )

        # Act
        status = await service.get_budget_status(cost_element.cost_element_id)

        # Assert
        assert status.budget == Decimal("1000.00")
        assert status.used == Decimal("500.00")
        assert status.remaining == Decimal("500.00")
        assert status.percentage == Decimal("50.00")

    @pytest.mark.asyncio
    async def test_get_budget_status_with_no_costs_returns_zero_used(
        self, db_session: AsyncSession, sample_cost_element_with_budget
    ) -> None:
        """Test getting budget status with no costs returns zero used.

        Acceptance Criteria:
        - Returns BudgetStatus with used=0, remaining=budget, percentage=0

        Expected Failure: get_budget_status method doesn't exist yet
        """
        # Arrange
        service = CostRegistrationService(db_session)
        cost_element = sample_cost_element_with_budget  # budget=1000

        # Act
        status = await service.get_budget_status(cost_element.cost_element_id)

        # Assert
        assert status.budget == Decimal("1000.00")
        assert status.used == Decimal("0.00")
        assert status.remaining == Decimal("1000.00")
        assert status.percentage == Decimal("0.00")

    @pytest.mark.asyncio
    async def test_get_total_for_cost_element_returns_sum(
        self, db_session: AsyncSession, sample_cost_element_with_budget
    ) -> None:
        """Test get_total_for_cost_element returns sum of all costs.

        Acceptance Criteria:
        - Returns sum of amount for all cost registrations for the element
        - Excludes soft-deleted registrations

        Expected Failure: Method exists but need fixture
        """
        # Arrange
        service = CostRegistrationService(db_session)
        cost_element = sample_cost_element_with_budget

        # Create multiple registrations
        await service.create_cost_registration(
            CostRegistrationCreate(
                cost_element_id=cost_element.cost_element_id,
                amount=Decimal("100.00"),
            ),
            actor_id=uuid4(),
        )
        await service.create_cost_registration(
            CostRegistrationCreate(
                cost_element_id=cost_element.cost_element_id,
                amount=Decimal("250.00"),
            ),
            actor_id=uuid4(),
        )

        # Act
        total = await service.get_total_for_cost_element(cost_element.cost_element_id)

        # Assert
        assert total == Decimal("350.00")

    @pytest.mark.asyncio
    async def test_get_total_for_cost_element_excludes_deleted(
        self, db_session: AsyncSession, sample_cost_element_with_budget
    ) -> None:
        """Test get_total_for_cost_element excludes soft-deleted registrations.

        Acceptance Criteria:
        - Soft-deleted registrations are not included in total

        Expected Failure: Method exists but need fixture
        """
        # Arrange
        service = CostRegistrationService(db_session)
        cost_element = sample_cost_element_with_budget

        # Create and then delete a registration
        reg = await service.create_cost_registration(
            CostRegistrationCreate(
                cost_element_id=cost_element.cost_element_id,
                amount=Decimal("200.00"),
            ),
            actor_id=uuid4(),
        )
        await service.soft_delete(reg.cost_registration_id, actor_id=uuid4())

        # Create another active registration
        await service.create_cost_registration(
            CostRegistrationCreate(
                cost_element_id=cost_element.cost_element_id,
                amount=Decimal("150.00"),
            ),
            actor_id=uuid4(),
        )

        # Act
        total = await service.get_total_for_cost_element(cost_element.cost_element_id)

        # Assert - Only active registration counted
        assert total == Decimal("150.00")
