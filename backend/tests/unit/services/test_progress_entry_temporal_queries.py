"""Test temporal queries for progress entries."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

import tests.unit.fixtures.cost_element_fixtures as _fixtures
from app.models.schemas.progress_entry import ProgressEntryCreate
from app.services.progress_entry_service import ProgressEntryService
from tests.unit.fixtures.cost_element_fixtures import (  # noqa: F401
    sample_cost_element_type,
    sample_department,
    sample_project,
    sample_wbe,
)

sample_cost_element_with_budget = _fixtures.sample_cost_element_with_budget  # noqa: F401


@pytest.mark.asyncio
async def test_get_progress_history_with_as_of(
    db_session: AsyncSession, sample_cost_element_with_budget
) -> None:
    """Test that get_progress_history correctly filters by as_of timestamp."""
    # Arrange
    service = ProgressEntryService(db_session)
    cost_element_id = sample_cost_element_with_budget.cost_element_id
    actor_id = uuid4()

    # Create progress entries with different control dates
    await service.create(
        actor_id,
        progress_in=ProgressEntryCreate(
            cost_element_id=cost_element_id,
            progress_percentage=Decimal("25.00"),
            control_date=datetime(2026, 1, 10, 12, 0, tzinfo=UTC),
        ),
    )
    await service.create(
        actor_id,
        progress_in=ProgressEntryCreate(
            cost_element_id=cost_element_id,
            progress_percentage=Decimal("50.00"),
            control_date=datetime(2026, 1, 20, 12, 0, tzinfo=UTC),
        ),
    )
    await service.create(
        actor_id,
        progress_in=ProgressEntryCreate(
            cost_element_id=cost_element_id,
            progress_percentage=Decimal("75.00"),
            control_date=datetime(2026, 1, 30, 12, 0, tzinfo=UTC),
        ),
    )

    # Act - query as of Jan 15 (should get only the first entry)
    history, total = await service.get_progress_history(
        cost_element_id=cost_element_id,
        as_of=datetime(2026, 1, 15, tzinfo=UTC),
    )

    # Assert
    assert total == 1
    assert len(history) == 1
    assert history[0].progress_percentage == Decimal("25.00")

    # Act - query as of Jan 25 (should get first two entries)
    history, total = await service.get_progress_history(
        cost_element_id=cost_element_id,
        as_of=datetime(2026, 1, 25, tzinfo=UTC),
    )

    # Assert
    assert total == 2
    assert len(history) == 2
    assert history[0].progress_percentage == Decimal("50.00")  # Most recent first
    assert history[1].progress_percentage == Decimal("25.00")

    # Act - query without as_of (should get all entries)
    history, total = await service.get_progress_history(
        cost_element_id=cost_element_id,
    )

    # Assert
    assert total == 3
    assert len(history) == 3
