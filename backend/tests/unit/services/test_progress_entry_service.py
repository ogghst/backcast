"""Unit tests for ProgressEntryService."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

import tests.unit.fixtures.cost_element_fixtures as _fixtures
from app.models.schemas.progress_entry import (
    ProgressEntryCreate,
    ProgressEntryUpdate,
)
from app.services.progress_entry_service import ProgressEntryService
from tests.unit.fixtures.cost_element_fixtures import (  # noqa: F401
    sample_cost_element_type,
    sample_department,
    sample_wbe,
)

sample_cost_element_with_budget = _fixtures.sample_cost_element_with_budget  # noqa: F401


class TestProgressEntryServiceCreate:
    """Test ProgressEntryService.create() method."""

    @pytest.mark.asyncio
    async def test_create_progress_entry_success(
        self, db_session: AsyncSession, sample_cost_element_with_budget
    ) -> None:
        """Test successfully creating a progress entry.

        Acceptance Criteria:
        - Progress entry is created with provided percentage and date
        - progress_entry_id is set (root ID)
        - Transaction time starts now
        - created_by tracks the actor_id

        Test ID: T-001, T-002
        """
        # Arrange
        service = ProgressEntryService(db_session)
        cost_element_id = sample_cost_element_with_budget.cost_element_id
        uuid4()
        progress_in = ProgressEntryCreate(
            cost_element_id=cost_element_id,
            progress_percentage=Decimal("50.00"),
            notes="Foundation complete",
        )
        actor_id = uuid4()

        # Act
        created_progress = await service.create(actor_id, progress_in=progress_in)

        # Assert
        assert created_progress is not None
        assert created_progress.cost_element_id == cost_element_id
        assert created_progress.progress_percentage == Decimal("50.00")
        assert created_progress.notes == "Foundation complete"
        assert created_progress.progress_entry_id is not None
        assert created_progress.created_by == actor_id

    @pytest.mark.asyncio
    async def test_create_progress_entry_with_zero_percentage(
        self, db_session: AsyncSession, sample_cost_element_with_budget
    ) -> None:
        """Test creating progress entry with 0% progress.

        Test ID: T-001
        """
        # Arrange
        service = ProgressEntryService(db_session)
        cost_element_id = sample_cost_element_with_budget.cost_element_id
        progress_in = ProgressEntryCreate(
            cost_element_id=cost_element_id,
            progress_percentage=Decimal("0.00"),
        )
        actor_id = uuid4()

        # Act
        created_progress = await service.create(actor_id, progress_in=progress_in)

        # Assert
        assert created_progress.progress_percentage == Decimal("0.00")

    @pytest.mark.asyncio
    async def test_create_progress_entry_with_hundred_percentage(
        self, db_session: AsyncSession, sample_cost_element_with_budget
    ) -> None:
        """Test creating progress entry with 100% progress.

        Test ID: T-002
        """
        # Arrange
        service = ProgressEntryService(db_session)
        cost_element_id = sample_cost_element_with_budget.cost_element_id
        progress_in = ProgressEntryCreate(
            cost_element_id=cost_element_id,
            progress_percentage=Decimal("100.00"),
        )
        actor_id = uuid4()

        # Act
        created_progress = await service.create(actor_id, progress_in=progress_in)

        # Assert
        assert created_progress.progress_percentage == Decimal("100.00")

    @pytest.mark.asyncio
    async def test_create_progress_entry_with_negative_percentage_raises_error(
        self, db_session: AsyncSession, sample_cost_element_with_budget
    ) -> None:
        """Test creating progress entry with negative percentage raises ValidationError.

        Test ID: T-003
        """
        # Arrange
        ProgressEntryService(db_session)
        cost_element_id = sample_cost_element_with_budget.cost_element_id
        uuid4()

        # Act & Assert - Pydantic validates before service is called
        from pydantic import ValidationError as PydanticValidationError

        with pytest.raises(PydanticValidationError, match="greater_than_equal"):
            ProgressEntryCreate(
                cost_element_id=cost_element_id,
                progress_percentage=Decimal("-1.00"),
            )

    @pytest.mark.asyncio
    async def test_create_progress_entry_with_over_hundred_percentage_raises_error(
        self, db_session: AsyncSession, sample_cost_element_with_budget
    ) -> None:
        """Test creating progress entry with >100% raises ValidationError.

        Test ID: T-004
        """
        # Arrange
        ProgressEntryService(db_session)
        cost_element_id = sample_cost_element_with_budget.cost_element_id

        # Act & Assert - Pydantic validates before service is called
        from pydantic import ValidationError as PydanticValidationError

        with pytest.raises(PydanticValidationError, match="less_than_equal"):
            ProgressEntryCreate(
                cost_element_id=cost_element_id,
                progress_percentage=Decimal("101.00"),
            )


class TestProgressEntryServiceUpdate:
    """Test ProgressEntryService.update() method."""

    @pytest.mark.asyncio
    async def test_update_progress_entry_increase(
        self, db_session: AsyncSession, sample_cost_element_with_budget
    ) -> None:
        """Test updating progress entry to increase percentage.

        Test ID: T-005
        """
        # Arrange - create initial progress entry
        service = ProgressEntryService(db_session)
        cost_element_id = sample_cost_element_with_budget.cost_element_id
        progress_in = ProgressEntryCreate(
            cost_element_id=cost_element_id,
            progress_percentage=Decimal("50.00"),
        )
        actor_id = uuid4()
        created_progress = await service.create(actor_id, progress_in=progress_in)

        # Act - update to higher percentage
        progress_update = ProgressEntryUpdate(
            progress_percentage=Decimal("75.00"),
        )
        updated_progress = await service.update(
            entity_id=created_progress.progress_entry_id,
            progress_in=progress_update,
            actor_id=actor_id,
        )

        # Assert
        assert updated_progress.progress_percentage == Decimal("75.00")

    @pytest.mark.asyncio
    async def test_update_progress_entry_decrease(
        self, db_session: AsyncSession, sample_cost_element_with_budget
    ) -> None:
        """Test updating progress entry to decrease percentage.

        Test ID: T-006
        """
        # Arrange - create initial progress entry
        service = ProgressEntryService(db_session)
        cost_element_id = sample_cost_element_with_budget.cost_element_id
        progress_in = ProgressEntryCreate(
            cost_element_id=cost_element_id,
            progress_percentage=Decimal("75.00"),
        )
        actor_id = uuid4()
        created_progress = await service.create(actor_id, progress_in=progress_in)

        # Act - update to lower percentage with justification
        progress_update = ProgressEntryUpdate(
            progress_percentage=Decimal("50.00"),
            notes="Work undone - inspection failed",
        )
        updated_progress = await service.update(
            entity_id=created_progress.progress_entry_id,
            progress_in=progress_update,
            actor_id=actor_id,
        )

        # Assert
        assert updated_progress.progress_percentage == Decimal("50.00")
        assert updated_progress.notes == "Work undone - inspection failed"


class TestProgressEntryServiceGetLatest:
    """Test ProgressEntryService.get_latest_progress() method."""

    @pytest.mark.asyncio
    async def test_get_latest_progress_returns_most_recent(
        self, db_session: AsyncSession, sample_cost_element_with_budget
    ) -> None:
        """Test that get_latest_progress returns the most recent entry.

        Test ID: T-008
        """
        # Arrange
        service = ProgressEntryService(db_session)
        cost_element_id = sample_cost_element_with_budget.cost_element_id
        uuid4()
        actor_id = uuid4()

        # Create multiple progress entries
        await service.create(
            actor_id,
            progress_in=ProgressEntryCreate(
                cost_element_id=cost_element_id,
                progress_percentage=Decimal("25.00"),
            ),
        )
        await service.create(
            actor_id,
            progress_in=ProgressEntryCreate(
                cost_element_id=cost_element_id,
                progress_percentage=Decimal("50.00"),
            ),
        )
        await service.create(
            actor_id,
            progress_in=ProgressEntryCreate(
                cost_element_id=cost_element_id,
                progress_percentage=Decimal("75.00"),
            ),
        )

        # Act
        latest = await service.get_latest_progress(cost_element_id=cost_element_id)

        # Assert - should return the most recent (75.00)
        assert latest is not None
        assert latest.progress_percentage == Decimal("75.00")

    @pytest.mark.asyncio
    async def test_get_latest_progress_with_as_of(
        self, db_session: AsyncSession, sample_cost_element_with_budget
    ) -> None:
        """Test get_latest_progress with time-travel (as_of parameter).

        Test ID: T-009
        """
        # Arrange
        service = ProgressEntryService(db_session)
        cost_element_id = sample_cost_element_with_budget.cost_element_id
        uuid4()
        actor_id = uuid4()

        # Create progress entries on different dates
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
                control_date=datetime(2026, 1, 15, 12, 0, tzinfo=UTC),
            ),
        )

        # Act - query as of Jan 12 (should get 25%)
        latest = await service.get_latest_progress(
            cost_element_id=cost_element_id,
            as_of=datetime(2026, 1, 12, tzinfo=UTC),
        )

        # Assert
        assert latest is not None
        assert latest.progress_percentage == Decimal("25.00")

    @pytest.mark.asyncio
    async def test_get_latest_progress_returns_none_when_no_entries(
        self, db_session: AsyncSession, sample_cost_element_with_budget
    ) -> None:
        """Test that get_latest_progress returns None when no entries exist.

        Test ID: T-010
        """
        # Arrange
        service = ProgressEntryService(db_session)
        cost_element_id = sample_cost_element_with_budget.cost_element_id

        # Act
        latest = await service.get_latest_progress(cost_element_id=cost_element_id)

        # Assert
        assert latest is None


class TestProgressEntryServiceGetHistory:
    """Test ProgressEntryService.get_progress_history() method."""

    @pytest.mark.asyncio
    async def test_get_progress_history_ordered_by_date(
        self, db_session: AsyncSession, sample_cost_element_with_budget
    ) -> None:
        """Test that get_progress_history returns entries ordered by reported_date DESC.

        Test ID: T-008
        """
        # Arrange
        service = ProgressEntryService(db_session)
        cost_element_id = sample_cost_element_with_budget.cost_element_id
        uuid4()
        actor_id = uuid4()

        # Create progress entries
        await service.create(
            actor_id,
            progress_in=ProgressEntryCreate(
                cost_element_id=cost_element_id,
                progress_percentage=Decimal("25.00"),
            ),
        )
        await service.create(
            actor_id,
            progress_in=ProgressEntryCreate(
                cost_element_id=cost_element_id,
                progress_percentage=Decimal("50.00"),
            ),
        )
        await service.create(
            actor_id,
            progress_in=ProgressEntryCreate(
                cost_element_id=cost_element_id,
                progress_percentage=Decimal("75.00"),
            ),
        )

        # Act
        history, total = await service.get_progress_history(
            cost_element_id=cost_element_id
        )

        # Assert
        assert total == 3
        assert len(history) == 3
        # Should be ordered by reported_date DESC (most recent first)
        assert history[0].progress_percentage == Decimal("75.00")
        assert history[1].progress_percentage == Decimal("50.00")
        assert history[2].progress_percentage == Decimal("25.00")

    @pytest.mark.asyncio
    async def test_get_progress_history_with_pagination(
        self, db_session: AsyncSession, sample_cost_element_with_budget
    ) -> None:
        """Test get_progress_history with pagination.

        Test ID: T-008
        """
        # Arrange
        service = ProgressEntryService(db_session)
        cost_element_id = sample_cost_element_with_budget.cost_element_id
        uuid4()
        actor_id = uuid4()

        # Create 5 progress entries
        for i in range(5):
            await service.create(
                actor_id,
                progress_in=ProgressEntryCreate(
                    cost_element_id=cost_element_id,
                    progress_percentage=Decimal(str(i * 20)),
                ),
            )

        # Act - get page 1 with 2 items per page
        history, total = await service.get_progress_history(
            cost_element_id=cost_element_id, skip=0, limit=2
        )

        # Assert
        assert total == 5
        assert len(history) == 2

    @pytest.mark.asyncio
    async def test_multiple_times_per_day_allowed(
        self, db_session: AsyncSession, sample_cost_element_with_budget
    ) -> None:
        """Test that multiple progress entries can be created on the same day.

        Test ID: T-007
        """
        # Arrange
        service = ProgressEntryService(db_session)
        cost_element_id = sample_cost_element_with_budget.cost_element_id
        uuid4()
        actor_id = uuid4()

        # Act - create multiple entries on the same day
        await service.create(
            actor_id,
            progress_in=ProgressEntryCreate(
                cost_element_id=cost_element_id,
                progress_percentage=Decimal("25.00"),
                notes="Morning update",
            ),
        )
        await service.create(
            actor_id,
            progress_in=ProgressEntryCreate(
                cost_element_id=cost_element_id,
                progress_percentage=Decimal("30.00"),
                notes="Afternoon update",
            ),
        )

        # Assert - both should exist
        history, total = await service.get_progress_history(
            cost_element_id=cost_element_id
        )
        assert total == 2
        assert len(history) == 2


class TestProgressEntryServiceAggregation:
    """Test ProgressEntryService.get_progress_history() with WBE/project filtering."""

    @pytest.mark.asyncio
    async def test_filter_by_wbe_id(
        self, db_session: AsyncSession, sample_cost_element_with_budget
    ) -> None:
        """Test filtering progress entries by WBE ID.

        When wbe_id is provided, should return progress entries for all
        cost elements under that WBE.
        """
        # Arrange
        service = ProgressEntryService(db_session)
        cost_element_id = sample_cost_element_with_budget.cost_element_id
        wbe_id = sample_cost_element_with_budget.wbe_id
        actor_id = uuid4()

        # Create progress entries on the cost element
        await service.create(
            actor_id,
            progress_in=ProgressEntryCreate(
                cost_element_id=cost_element_id,
                progress_percentage=Decimal("50.00"),
            ),
        )

        # Act - filter by WBE ID
        history, total = await service.get_progress_history(wbe_id=wbe_id)

        # Assert - should find the entry through the WBE -> cost_element join
        assert total >= 1
        assert any(
            entry.cost_element_id == cost_element_id for entry in history
        )

    @pytest.mark.asyncio
    async def test_filter_by_project_id(
        self, db_session: AsyncSession, sample_cost_element_with_budget
    ) -> None:
        """Test filtering progress entries by project ID.

        When project_id is provided, should return progress entries for all
        cost elements under all WBEs of that project.
        """
        # Arrange
        service = ProgressEntryService(db_session)
        cost_element_id = sample_cost_element_with_budget.cost_element_id
        actor_id = uuid4()

        # Get project_id through the WBE
        from sqlalchemy import select

        from app.models.domain.wbe import WBE

        wbe_stmt = select(WBE.project_id).where(
            WBE.wbe_id == sample_cost_element_with_budget.wbe_id,
            WBE.deleted_at.is_(None),
        )
        wbe_result = await db_session.execute(wbe_stmt)
        project_id = wbe_result.scalar_one()

        # Create progress entries on the cost element
        await service.create(
            actor_id,
            progress_in=ProgressEntryCreate(
                cost_element_id=cost_element_id,
                progress_percentage=Decimal("75.00"),
            ),
        )

        # Act - filter by project ID
        history, total = await service.get_progress_history(project_id=project_id)

        # Assert - should find the entry through project -> wbe -> cost_element join
        assert total >= 1
        assert any(
            entry.cost_element_id == cost_element_id for entry in history
        )

    @pytest.mark.asyncio
    async def test_filter_by_wbe_id_excludes_other_wbes(
        self, db_session: AsyncSession, sample_wbe, sample_department  # noqa: F811
    ) -> None:
        """Test that WBE filtering excludes cost elements from other WBEs.

        Creates two WBEs with separate cost elements and verifies that
        filtering by one WBE only returns its own entries.
        """
        from app.models.domain.cost_element import CostElement
        from app.models.domain.cost_element_type import CostElementType
        from app.models.domain.wbe import WBE

        service = ProgressEntryService(db_session)
        actor_id = uuid4()

        # Create a second WBE under the same project
        wbe2 = WBE(
            wbe_id=uuid4(),
            project_id=sample_wbe.project_id,
            code="1.2",
            name="Second WBE",
            level=1,
            created_by=uuid4(),
        )
        db_session.add(wbe2)
        await db_session.flush()

        # Create cost element type
        cet = CostElementType(
            cost_element_type_id=uuid4(),
            department_id=sample_department.department_id,
            code="TEST",
            name="Test Type",
            created_by=uuid4(),
        )
        db_session.add(cet)
        await db_session.flush()

        # Create cost elements on each WBE
        ce1 = CostElement(
            cost_element_id=uuid4(),
            wbe_id=sample_wbe.wbe_id,
            cost_element_type_id=cet.cost_element_type_id,
            code="CE-1",
            name="Cost Element 1",
            budget_amount=Decimal("1000.00"),
            created_by=uuid4(),
        )
        ce2 = CostElement(
            cost_element_id=uuid4(),
            wbe_id=wbe2.wbe_id,
            cost_element_type_id=cet.cost_element_type_id,
            code="CE-2",
            name="Cost Element 2",
            budget_amount=Decimal("2000.00"),
            created_by=uuid4(),
        )
        db_session.add_all([ce1, ce2])
        await db_session.flush()

        # Create progress entries on both cost elements
        await service.create(
            actor_id,
            progress_in=ProgressEntryCreate(
                cost_element_id=ce1.cost_element_id,
                progress_percentage=Decimal("30.00"),
            ),
        )
        await service.create(
            actor_id,
            progress_in=ProgressEntryCreate(
                cost_element_id=ce2.cost_element_id,
                progress_percentage=Decimal("60.00"),
            ),
        )

        # Act - filter by first WBE only
        history, total = await service.get_progress_history(
            wbe_id=sample_wbe.wbe_id
        )

        # Assert - should only get entries from ce1
        assert total == 1
        assert history[0].cost_element_id == ce1.cost_element_id

    @pytest.mark.asyncio
    async def test_priority_cost_element_over_wbe(
        self, db_session: AsyncSession, sample_cost_element_with_budget
    ) -> None:
        """Test that cost_element_id takes priority over wbe_id."""
        # Arrange
        service = ProgressEntryService(db_session)
        cost_element_id = sample_cost_element_with_budget.cost_element_id
        wbe_id = sample_cost_element_with_budget.wbe_id
        actor_id = uuid4()

        await service.create(
            actor_id,
            progress_in=ProgressEntryCreate(
                cost_element_id=cost_element_id,
                progress_percentage=Decimal("40.00"),
            ),
        )

        # Act - pass both cost_element_id and wbe_id
        history, total = await service.get_progress_history(
            cost_element_id=cost_element_id,
            wbe_id=wbe_id,
        )

        # Assert - cost_element_id filter is used (wbe_id is ignored in service)
        assert total == 1
        assert history[0].cost_element_id == cost_element_id

    @pytest.mark.asyncio
    async def test_no_filters_returns_all(
        self, db_session: AsyncSession, sample_cost_element_with_budget
    ) -> None:
        """Test that calling with no filters returns entries without scope."""
        # Arrange
        service = ProgressEntryService(db_session)
        cost_element_id = sample_cost_element_with_budget.cost_element_id
        actor_id = uuid4()

        await service.create(
            actor_id,
            progress_in=ProgressEntryCreate(
                cost_element_id=cost_element_id,
                progress_percentage=Decimal("20.00"),
            ),
        )

        # Act - no filters
        history, total = await service.get_progress_history()

        # Assert - should return at least the entry we created
        assert total >= 1
