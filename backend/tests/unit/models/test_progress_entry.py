"""Unit tests for ProgressEntry model."""

from decimal import Decimal
from uuid import uuid4

import pytest

from app.models.domain.progress_entry import ProgressEntry


class TestProgressEntryModel:
    """Test ProgressEntry model attributes and constraints."""

    @pytest.mark.asyncio
    async def test_progress_entry_instantiation(self, db_session):
        """Test creating a ProgressEntry instance.

        Acceptance Criteria:
        - ProgressEntry can be instantiated with all required fields
        - progress_percentage accepts 0.00 to 100.00
        - All fields are properly set

        Test ID: T-001, T-002
        """
        # Arrange
        progress_entry_id = uuid4()
        cost_element_id = uuid4()
        created_by_user_id = uuid4()

        # Act
        progress_entry = ProgressEntry(
            id=uuid4(),
            progress_entry_id=progress_entry_id,
            cost_element_id=cost_element_id,
            progress_percentage=Decimal("50.00"),
            notes="Foundation complete",
            created_by=created_by_user_id,
            deleted_at=None,
            deleted_by=None,
        )

        # Assert
        assert progress_entry.progress_entry_id == progress_entry_id
        assert progress_entry.cost_element_id == cost_element_id
        assert progress_entry.progress_percentage == Decimal("50.00")
        assert progress_entry.notes == "Foundation complete"

    @pytest.mark.asyncio
    async def test_progress_entry_accepts_zero_percentage(self, db_session):
        """Test that progress_percentage accepts 0.00.

        Test ID: T-001
        """
        # Arrange
        progress_entry = ProgressEntry(
            id=uuid4(),
            progress_entry_id=uuid4(),
            cost_element_id=uuid4(),
            progress_percentage=Decimal("0.00"),
            created_by=uuid4(),
        )

        # Assert
        assert progress_entry.progress_percentage == Decimal("0.00")

    @pytest.mark.asyncio
    async def test_progress_entry_accepts_hundred_percentage(self, db_session):
        """Test that progress_percentage accepts 100.00.

        Test ID: T-002
        """
        # Arrange
        progress_entry = ProgressEntry(
            id=uuid4(),
            progress_entry_id=uuid4(),
            cost_element_id=uuid4(),
            progress_percentage=Decimal("100.00"),
            created_by=uuid4(),
        )

        # Assert
        assert progress_entry.progress_percentage == Decimal("100.00")

    @pytest.mark.asyncio
    async def test_progress_entry_repr(self, db_session):
        """Test ProgressEntry __repr__ method.

        Acceptance Criteria:
        - __repr__ includes key fields for debugging
        """
        # Arrange
        progress_entry_id = uuid4()
        progress_entry = ProgressEntry(
            id=uuid4(),
            progress_entry_id=progress_entry_id,
            cost_element_id=uuid4(),
            progress_percentage=Decimal("75.50"),
            created_by=uuid4(),
        )

        # Act
        repr_str = repr(progress_entry)

        # Assert
        assert "ProgressEntry" in repr_str
        assert str(progress_entry_id) in repr_str
        assert "75.50" in repr_str

    @pytest.mark.asyncio
    async def test_progress_entry_optional_notes(self, db_session):
        """Test that notes field is optional.

        Acceptance Criteria:
        - ProgressEntry can be created without notes
        """
        # Arrange
        progress_entry = ProgressEntry(
            id=uuid4(),
            progress_entry_id=uuid4(),
            cost_element_id=uuid4(),
            progress_percentage=Decimal("25.00"),
            notes=None,
            created_by=uuid4(),
        )

        # Assert
        assert progress_entry.notes is None

    @pytest.mark.asyncio
    async def test_progress_entry_two_decimal_precision(self, db_session):
        """Test that progress_percentage supports 2 decimal places.

        Acceptance Criteria:
        - Precision of 5,2 allows values like 99.99
        """
        # Arrange
        progress_entry = ProgressEntry(
            id=uuid4(),
            progress_entry_id=uuid4(),
            cost_element_id=uuid4(),
            progress_percentage=Decimal("99.99"),
            created_by=uuid4(),
        )

        # Assert
        assert progress_entry.progress_percentage == Decimal("99.99")
