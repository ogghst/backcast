"""Unit tests for ProgressEntryService."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schemas.progress_entry import (
    ProgressEntryCreate,
    ProgressEntryUpdate,
)
from app.services.progress_entry_service import ProgressEntryService


class TestProgressEntryServiceCreate:
    """Test ProgressEntryService.create() method."""

    @pytest.mark.asyncio
    async def test_create_progress_entry_success(self, db_session: AsyncSession) -> None:
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
        cost_element_id = uuid4()
        reported_by_user_id = uuid4()
        progress_in = ProgressEntryCreate(
            cost_element_id=cost_element_id,
            progress_percentage=Decimal("50.00"),
            notes="Foundation complete",
        )
        actor_id = uuid4()

        # Act
        created_progress = await service.create(progress_in, actor_id=actor_id)

        # Assert
        assert created_progress is not None
        assert created_progress.cost_element_id == cost_element_id
        assert created_progress.progress_percentage == Decimal("50.00")
        assert created_progress.notes == "Foundation complete"
        assert created_progress.progress_entry_id is not None
        assert created_progress.created_by == actor_id

    @pytest.mark.asyncio
    async def test_create_progress_entry_with_zero_percentage(
        self, db_session: AsyncSession
    ) -> None:
        """Test creating progress entry with 0% progress.

        Test ID: T-001
        """
        # Arrange
        service = ProgressEntryService(db_session)
        cost_element_id = uuid4()
        progress_in = ProgressEntryCreate(
            cost_element_id=cost_element_id,
            progress_percentage=Decimal("0.00"),
        )
        actor_id = uuid4()

        # Act
        created_progress = await service.create(progress_in, actor_id=actor_id)

        # Assert
        assert created_progress.progress_percentage == Decimal("0.00")

    @pytest.mark.asyncio
    async def test_create_progress_entry_with_hundred_percentage(
        self, db_session: AsyncSession
    ) -> None:
        """Test creating progress entry with 100% progress.

        Test ID: T-002
        """
        # Arrange
        service = ProgressEntryService(db_session)
        cost_element_id = uuid4()
        progress_in = ProgressEntryCreate(
            cost_element_id=cost_element_id,
            progress_percentage=Decimal("100.00"),
        )
        actor_id = uuid4()

        # Act
        created_progress = await service.create(progress_in, actor_id=actor_id)

        # Assert
        assert created_progress.progress_percentage == Decimal("100.00")

    @pytest.mark.asyncio
    async def test_create_progress_entry_with_negative_percentage_raises_error(
        self, db_session: AsyncSession
    ) -> None:
        """Test creating progress entry with negative percentage raises ValidationError.

        Test ID: T-003
        """
        # Arrange
        service = ProgressEntryService(db_session)
        cost_element_id = uuid4()
        actor_id = uuid4()

        # Act & Assert - Pydantic validates before service is called
        from pydantic import ValidationError as PydanticValidationError
        with pytest.raises(PydanticValidationError, match="greater_than_equal"):
            ProgressEntryCreate(
                cost_element_id=cost_element_id,
                progress_percentage=Decimal("-1.00"),
            )

    @pytest.mark.asyncio
    async def test_create_progress_entry_with_over_hundred_percentage_raises_error(
        self, db_session: AsyncSession
    ) -> None:
        """Test creating progress entry with >100% raises ValidationError.

        Test ID: T-004
        """
        # Arrange
        service = ProgressEntryService(db_session)
        cost_element_id = uuid4()

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
    async def test_update_progress_entry_increase(self, db_session: AsyncSession) -> None:
        """Test updating progress entry to increase percentage.

        Test ID: T-005
        """
        # Arrange - create initial progress entry
        service = ProgressEntryService(db_session)
        cost_element_id = uuid4()
        progress_in = ProgressEntryCreate(
            cost_element_id=cost_element_id,
            progress_percentage=Decimal("50.00"),
        )
        actor_id = uuid4()
        created_progress = await service.create(progress_in, actor_id=actor_id)

        # Act - update to higher percentage
        progress_update = ProgressEntryUpdate(
            progress_percentage=Decimal("75.00"),
        )
        updated_progress = await service.update(
            progress_entry_id=created_progress.progress_entry_id,
            progress_in=progress_update,
            actor_id=actor_id,
        )

        # Assert
        assert updated_progress.progress_percentage == Decimal("75.00")

    @pytest.mark.asyncio
    async def test_update_progress_entry_decrease(self, db_session: AsyncSession) -> None:
        """Test updating progress entry to decrease percentage.

        Test ID: T-006
        """
        # Arrange - create initial progress entry
        service = ProgressEntryService(db_session)
        cost_element_id = uuid4()
        progress_in = ProgressEntryCreate(
            cost_element_id=cost_element_id,
            progress_percentage=Decimal("75.00"),
        )
        actor_id = uuid4()
        created_progress = await service.create(progress_in, actor_id=actor_id)

        # Act - update to lower percentage with justification
        progress_update = ProgressEntryUpdate(
            progress_percentage=Decimal("50.00"),
            notes="Work undone - inspection failed",
        )
        updated_progress = await service.update(
            progress_entry_id=created_progress.progress_entry_id,
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
        self, db_session: AsyncSession
    ) -> None:
        """Test that get_latest_progress returns the most recent entry.

        Test ID: T-008
        """
        # Arrange
        service = ProgressEntryService(db_session)
        cost_element_id = uuid4()
        user_id = uuid4()
        actor_id = uuid4()

        # Create multiple progress entries
        await service.create(
            ProgressEntryCreate(
                cost_element_id=cost_element_id,
                progress_percentage=Decimal("25.00"),
            ),
            actor_id=actor_id,
        )
        await service.create(
            ProgressEntryCreate(
                cost_element_id=cost_element_id,
                progress_percentage=Decimal("50.00"),
            ),
            actor_id=actor_id,
        )
        await service.create(
            ProgressEntryCreate(
                cost_element_id=cost_element_id,
                progress_percentage=Decimal("75.00"),
            ),
            actor_id=actor_id,
        )

        # Act
        latest = await service.get_latest_progress(cost_element_id=cost_element_id)

        # Assert - should return the most recent (75.00)
        assert latest is not None
        assert latest.progress_percentage == Decimal("75.00")

    @pytest.mark.asyncio
    async def test_get_latest_progress_with_as_of(self, db_session: AsyncSession) -> None:
        """Test get_latest_progress with time-travel (as_of parameter).

        Test ID: T-009
        """
        # Arrange
        service = ProgressEntryService(db_session)
        cost_element_id = uuid4()
        user_id = uuid4()
        actor_id = uuid4()

        # Create progress entries on different dates
        await service.create(
            ProgressEntryCreate(
                cost_element_id=cost_element_id,
                progress_percentage=Decimal("25.00"),
                control_date=datetime(2026, 1, 10, 12, 0, tzinfo=UTC),
            ),
            actor_id=actor_id,
        )
        await service.create(
            ProgressEntryCreate(
                cost_element_id=cost_element_id,
                progress_percentage=Decimal("50.00"),
                control_date=datetime(2026, 1, 15, 12, 0, tzinfo=UTC),
            ),
            actor_id=actor_id,
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
        self, db_session: AsyncSession
    ) -> None:
        """Test that get_latest_progress returns None when no entries exist.

        Test ID: T-010
        """
        # Arrange
        service = ProgressEntryService(db_session)
        cost_element_id = uuid4()

        # Act
        latest = await service.get_latest_progress(cost_element_id=cost_element_id)

        # Assert
        assert latest is None


class TestProgressEntryServiceGetHistory:
    """Test ProgressEntryService.get_progress_history() method."""

    @pytest.mark.asyncio
    async def test_get_progress_history_ordered_by_date(
        self, db_session: AsyncSession
    ) -> None:
        """Test that get_progress_history returns entries ordered by reported_date DESC.

        Test ID: T-008
        """
        # Arrange
        service = ProgressEntryService(db_session)
        cost_element_id = uuid4()
        user_id = uuid4()
        actor_id = uuid4()

        # Create progress entries
        await service.create(
            ProgressEntryCreate(
                cost_element_id=cost_element_id,
                progress_percentage=Decimal("25.00"),
            ),
            actor_id=actor_id,
        )
        await service.create(
            ProgressEntryCreate(
                cost_element_id=cost_element_id,
                progress_percentage=Decimal("50.00"),
            ),
            actor_id=actor_id,
        )
        await service.create(
            ProgressEntryCreate(
                cost_element_id=cost_element_id,
                progress_percentage=Decimal("75.00"),
            ),
            actor_id=actor_id,
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
        self, db_session: AsyncSession
    ) -> None:
        """Test get_progress_history with pagination.

        Test ID: T-008
        """
        # Arrange
        service = ProgressEntryService(db_session)
        cost_element_id = uuid4()
        user_id = uuid4()
        actor_id = uuid4()

        # Create 5 progress entries
        for i in range(5):
            await service.create(
                ProgressEntryCreate(
                    cost_element_id=cost_element_id,
                    progress_percentage=Decimal(str(i * 20)),
                ),
                actor_id=actor_id,
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
        self, db_session: AsyncSession
    ) -> None:
        """Test that multiple progress entries can be created on the same day.

        Test ID: T-007
        """
        # Arrange
        service = ProgressEntryService(db_session)
        cost_element_id = uuid4()
        user_id = uuid4()
        actor_id = uuid4()

        # Act - create multiple entries on the same day
        await service.create(
            ProgressEntryCreate(
                cost_element_id=cost_element_id,
                progress_percentage=Decimal("25.00"),
                notes="Morning update",
            ),
            actor_id=actor_id,
        )
        await service.create(
            ProgressEntryCreate(
                cost_element_id=cost_element_id,
                progress_percentage=Decimal("30.00"),
                notes="Afternoon update",
            ),
            actor_id=actor_id,
        )

        # Assert - both should exist
        history, total = await service.get_progress_history(
            cost_element_id=cost_element_id
        )
        assert total == 2
        assert len(history) == 2
