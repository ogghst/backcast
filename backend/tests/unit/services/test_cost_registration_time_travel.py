"""Unit tests for Cost Registration Time-Travel Queries.

Tests historical cost analysis using as_of parameter for time-travel queries.
"""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

# Import sample_cost_element_with_budget separately to avoid F811
import tests.unit.fixtures.cost_element_fixtures as _fixtures
from app.models.schemas.cost_registration import CostRegistrationCreate
from app.services.cost_registration_service import CostRegistrationService

# Import fixtures
from tests.unit.fixtures.cost_element_fixtures import (  # noqa: F401
    sample_cost_element_type,
    sample_department,
    sample_wbe,
)

# Type alias for fixture
sample_cost_element_with_budget = _fixtures.sample_cost_element_with_budget  # noqa: F401


class TestTimeTravelQueries:
    """Test time-travel query functionality for cost analysis."""

    @pytest.mark.asyncio
    async def test_get_total_for_cost_element_with_as_of_past_returns_historical_sum(
        self, db_session: AsyncSession, sample_cost_element_with_budget
    ) -> None:
        """Test time-travel query for historical cost totals.

        Acceptance Criteria:
        - as_of parameter queries cost state as of that date (by valid_time)
        - Costs created after as_of are excluded
        - Costs deleted after as_of are included

        Expected Behavior:
        - Querying as_of 2026-01-10 includes only costs with valid_time containing that date
        - Costs created after 2026-01-10 are excluded
        """
        # Arrange
        service = CostRegistrationService(db_session)
        cost_element = sample_cost_element_with_budget
        # Capture ID before entity might be expired
        cost_element_id = cost_element.cost_element_id
        actor_id = uuid4()

        # Create cost with valid_time starting Jan 1
        await service.create(
            CostRegistrationCreate(
                cost_element_id=cost_element_id,
                amount=Decimal("100.00"),
                registration_date=datetime(2026, 1, 1, tzinfo=UTC),
            ),
            actor_id=actor_id,
            control_date=datetime(2026, 1, 1, tzinfo=UTC),  # Sets valid_time start
        )

        # Create cost with valid_time starting Jan 15 (should be excluded)
        await service.create(
            CostRegistrationCreate(
                cost_element_id=cost_element_id,
                amount=Decimal("200.00"),
                registration_date=datetime(2026, 1, 15, tzinfo=UTC),
            ),
            actor_id=actor_id,
            control_date=datetime(2026, 1, 15, tzinfo=UTC),  # Sets valid_time start
        )

        # Act - Query as of Jan 10 (between Jan 1 and Jan 15)
        total = await service.get_total_for_cost_element(
            cost_element_id=cost_element_id,
            as_of=datetime(2026, 1, 10, 12, 0, 0, tzinfo=UTC),
        )

        # Assert - Only Jan 1 cost included (Jan 15 cost not yet valid)
        assert total == Decimal("100.00")

    @pytest.mark.asyncio
    async def test_get_total_for_cost_element_with_as_of_future_returns_current_sum(
        self, db_session: AsyncSession, sample_cost_element_with_budget
    ) -> None:
        """Test time-travel query with future date returns current sum.

        Acceptance Criteria:
        - Future as_of date treated as "now"
        - Returns all current costs (no future costs exist yet)
        - Same result as omitting as_of parameter

        Expected Behavior:
        - Querying as_of 2099-12-31 returns all current costs
        - Result matches query without as_of parameter
        """
        # Arrange
        service = CostRegistrationService(db_session)
        cost_element = sample_cost_element_with_budget
        actor_id = uuid4()

        # Create two costs
        await service.create(
            CostRegistrationCreate(
                cost_element_id=cost_element.cost_element_id,
                amount=Decimal("100.00"),
                registration_date=datetime(2026, 1, 1, tzinfo=UTC),
            ),
            actor_id=actor_id,
        )
        await service.create(
            CostRegistrationCreate(
                cost_element_id=cost_element.cost_element_id,
                amount=Decimal("250.00"),
                registration_date=datetime(2026, 1, 15, tzinfo=UTC),
            ),
            actor_id=actor_id,
        )

        # Act - Query with future date
        future_total = await service.get_total_for_cost_element(
            cost_element_id=cost_element.cost_element_id,
            as_of=datetime(2099, 12, 31, 23, 59, 59, tzinfo=UTC),
        )

        # Act - Query without as_of (current)
        current_total = await service.get_total_for_cost_element(
            cost_element_id=cost_element.cost_element_id,
        )

        # Assert - Both should return same total
        assert future_total == Decimal("350.00")
        assert current_total == Decimal("350.00")
        assert future_total == current_total

    @pytest.mark.asyncio
    async def test_get_total_for_cost_element_includes_costs_soft_deleted_after_as_of(
        self, db_session: AsyncSession, sample_cost_element_with_budget
    ) -> None:
        """Test that costs deleted after as_of date are included in historical total.

        Acceptance Criteria:
        - Costs soft-deleted AFTER as_of are INCLUDED
        - Soft-deleted costs have deleted_at > as_of timestamp
        - Demonstrates time-travel correctness

        Expected Behavior:
        - Cost created with valid_time starting Jan 1
        - Soft deleted on Jan 20 (sets deleted_at)
        - Query as_of Jan 10 includes the cost (not yet deleted)
        """
        # Arrange
        service = CostRegistrationService(db_session)
        cost_element = sample_cost_element_with_budget
        # Capture IDs before entities might be expired
        cost_element_id = cost_element.cost_element_id
        actor_id = uuid4()

        # Create cost with valid_time starting Jan 1
        registration = await service.create(
            CostRegistrationCreate(
                cost_element_id=cost_element_id,
                amount=Decimal("100.00"),
                registration_date=datetime(2026, 1, 1, tzinfo=UTC),
            ),
            actor_id=actor_id,
            control_date=datetime(2026, 1, 1, tzinfo=UTC),  # Sets valid_time start
        )
        # Capture registration ID before entity might be expired
        registration_id = registration.cost_registration_id

        # Soft delete on Jan 20 (sets deleted_at)
        await service.soft_delete(
            registration_id,
            actor_id=actor_id,
            control_date=datetime(2026, 1, 20, tzinfo=UTC),
        )

        # Act - Query as of Jan 10 (before deletion)
        total = await service.get_total_for_cost_element(
            cost_element_id=cost_element_id,
            as_of=datetime(2026, 1, 10, 12, 0, 0, tzinfo=UTC),
        )

        # Assert - Cost should be included (not yet deleted as of Jan 10)
        assert total == Decimal("100.00")

    @pytest.mark.asyncio
    async def test_get_total_for_cost_element_excludes_costs_soft_deleted_before_as_of(
        self, db_session: AsyncSession, sample_cost_element_with_budget
    ) -> None:
        """Test that costs deleted before as_of date are excluded from historical total.

        Acceptance Criteria:
        - Costs soft-deleted BEFORE as_of are EXCLUDED
        - Demonstrates temporal query accuracy

        Expected Behavior:
        - Cost created Jan 1, deleted Jan 5
        - Query as_of Jan 10 excludes the cost (already deleted)
        """
        # Arrange
        service = CostRegistrationService(db_session)
        cost_element = sample_cost_element_with_budget
        actor_id = uuid4()

        # Create and soft delete cost
        registration = await service.create(
            CostRegistrationCreate(
                cost_element_id=cost_element.cost_element_id,
                amount=Decimal("100.00"),
                registration_date=datetime(2026, 1, 1, tzinfo=UTC),
            ),
            actor_id=actor_id,
        )
        await service.soft_delete(
            registration.cost_registration_id,
            actor_id=actor_id,
            control_date=datetime(2026, 1, 5, tzinfo=UTC),
        )

        # Act - Query as of Jan 10 (after deletion)
        total = await service.get_total_for_cost_element(
            cost_element_id=cost_element.cost_element_id,
            as_of=datetime(2026, 1, 10, 12, 0, 0, tzinfo=UTC),
        )

        # Assert - Cost should be excluded (already deleted as of Jan 10)
        assert total == 0

    @pytest.mark.asyncio
    async def test_get_cost_registration_as_of_returns_historical_version(
        self, db_session: AsyncSession, sample_cost_element_with_budget
    ) -> None:
        """Test getting a cost registration as it was at a specific timestamp.

        Acceptance Criteria:
        - Returns version that was valid at as_of timestamp (by valid_time)
        - Handles versions created after as_of correctly
        - Demonstrates System Time Travel semantics (valid_time filtering)

        Expected Behavior:
        - Create v1 with valid_time starting Jan 1, amount=100
        - Update to v2 with valid_time starting Jan 15, amount=150
        - Query as_of Jan 10 returns v1 (amount=100) because v1's valid_time contains Jan 10
        """
        # Arrange
        service = CostRegistrationService(db_session)
        cost_element = sample_cost_element_with_budget
        # Capture ID before entity might be expired
        cost_element_id = cost_element.cost_element_id
        actor_id = uuid4()

        # Create v1 with valid_time starting Jan 1
        v1 = await service.create(
            CostRegistrationCreate(
                cost_element_id=cost_element_id,
                amount=Decimal("100.00"),
                registration_date=datetime(2026, 1, 1, tzinfo=UTC),
            ),
            actor_id=actor_id,
            control_date=datetime(2026, 1, 1, tzinfo=UTC),  # Sets valid_time start
        )
        # Capture v1 ID before entity might be expired
        v1_id = v1.cost_registration_id

        # Update to v2 with valid_time starting Jan 15
        from app.models.schemas.cost_registration import CostRegistrationUpdate

        _ = await service.update(
            v1_id,
            CostRegistrationUpdate(amount=Decimal("150.00")),
            actor_id=uuid4(),
            control_date=datetime(2026, 1, 15, tzinfo=UTC),
        )

        # Act - Query as of Jan 10 (before v2's valid_time starts)
        historical = await service.get_cost_registration_as_of(
            cost_registration_id=v1_id,
            as_of=datetime(2026, 1, 10, 12, 0, 0, tzinfo=UTC),
        )

        # Assert - Should return v1 (amount=100)
        assert historical is not None
        assert historical.amount == Decimal("100.00")

        # Verify current version is v2
        current = await service.get_by_id(v1_id)
        assert current is not None
        assert current.amount == Decimal("150.00")
