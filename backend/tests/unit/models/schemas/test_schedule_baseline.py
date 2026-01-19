"""Unit tests for ScheduleBaseline Pydantic schemas.

Tests schema validation, field defaults, and type safety for Create/Update operations.
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.models.schemas.schedule_baseline import (
    ScheduleBaselineCreate,
    ScheduleBaselineUpdate,
)


class TestScheduleBaselineCreate:
    """Test ScheduleBaselineCreate schema validation."""

    def test_schedule_baseline_create_with_default_branch_is_main(self):
        """Test that ScheduleBaselineCreate defaults branch to 'main' when not provided.

        Acceptance Criteria:
        - ScheduleBaselineCreate schema validates with default branch="main"
        - Field is not configurable by API consumer (hardcoded default)
        """
        # Arrange
        start_date = datetime(2026, 1, 1, tzinfo=UTC)
        end_date = datetime(2026, 12, 31, tzinfo=UTC)

        # Act - Create without branch field
        baseline = ScheduleBaselineCreate(
            name="Q1 2026 Baseline",
            start_date=start_date,
            end_date=end_date,
            progression_type="LINEAR",
        )

        # Assert - Branch should default to "main"
        assert baseline.branch == "main"
        assert baseline.control_date is None

    def test_schedule_baseline_create_with_explicit_control_date_validates(self):
        """Test that ScheduleBaselineCreate accepts explicit control_date.

        Acceptance Criteria:
        - Schema validates with control_date="2026-01-19T00:00:00Z"
        - control_date is optional and defaults to None
        """
        # Arrange
        start_date = datetime(2026, 1, 1, tzinfo=UTC)
        end_date = datetime(2026, 12, 31, tzinfo=UTC)
        control_date = datetime(2026, 1, 19, tzinfo=UTC)

        # Act - Create with control_date
        baseline = ScheduleBaselineCreate(
            name="Q1 2026 Baseline",
            start_date=start_date,
            end_date=end_date,
            progression_type="LINEAR",
            control_date=control_date,
        )

        # Assert
        assert baseline.control_date == control_date
        assert baseline.branch == "main"

    def test_schedule_baseline_create_with_invalid_branch_type_raises_validation_error(
        self,
    ):
        """Test that ScheduleBaselineCreate rejects invalid branch type.

        Acceptance Criteria:
        - Schema with branch=123 raises Pydantic ValidationError
        - Type validation is enforced
        """
        # Arrange
        start_date = datetime(2026, 1, 1, tzinfo=UTC)
        end_date = datetime(2026, 12, 31, tzinfo=UTC)

        # Act & Assert - Invalid branch type should raise ValidationError
        with pytest.raises(ValidationError) as exc_info:
            ScheduleBaselineCreate(
                name="Q1 2026 Baseline",
                start_date=start_date,
                end_date=end_date,
                progression_type="LINEAR",
                branch=123,  # Invalid: should be string
            )

        # Assert error details
        errors = exc_info.value.errors()
        assert any(error["loc"] == ("branch",) for error in errors)

    def test_schedule_baseline_create_with_all_fields_validates(self):
        """Test that ScheduleBaselineCreate validates with all fields provided.

        Acceptance Criteria:
        - All optional fields can be provided
        - Schema enforces field constraints
        """
        # Arrange
        start_date = datetime(2026, 1, 1, tzinfo=UTC)
        end_date = datetime(2026, 12, 31, tzinfo=UTC)
        control_date = datetime(2026, 1, 19, tzinfo=UTC)
        schedule_baseline_id = uuid4()

        # Act - Create with all fields
        baseline = ScheduleBaselineCreate(
            name="Q1 2026 Baseline",
            start_date=start_date,
            end_date=end_date,
            progression_type="GAUSSIAN",
            description="Initial baseline for Q1",
            control_date=control_date,
            schedule_baseline_id=schedule_baseline_id,
        )

        # Assert
        assert baseline.name == "Q1 2026 Baseline"
        assert baseline.start_date == start_date
        assert baseline.end_date == end_date
        assert baseline.progression_type == "GAUSSIAN"
        assert baseline.description == "Initial baseline for Q1"
        assert baseline.control_date == control_date
        assert baseline.schedule_baseline_id == schedule_baseline_id
        assert baseline.branch == "main"  # Always defaults to main


class TestScheduleBaselineUpdate:
    """Test ScheduleBaselineUpdate schema validation."""

    def test_schedule_baseline_update_with_all_fields_validates(self):
        """Test that ScheduleBaselineUpdate accepts all optional fields.

        Acceptance Criteria:
        - All fields are optional
        - Schema validates with partial data
        """
        # Arrange
        start_date = datetime(2026, 2, 1, tzinfo=UTC)
        end_date = datetime(2026, 12, 31, tzinfo=UTC)
        control_date = datetime(2026, 1, 19, tzinfo=UTC)

        # Act - Update with all fields
        update = ScheduleBaselineUpdate(
            name="Updated Baseline",
            start_date=start_date,
            end_date=end_date,
            progression_type="LOGARITHMIC",
            description="Updated description",
            branch="main",
            control_date=control_date,
        )

        # Assert
        assert update.name == "Updated Baseline"
        assert update.start_date == start_date
        assert update.end_date == end_date
        assert update.progression_type == "LOGARITHMIC"
        assert update.description == "Updated description"
        assert update.branch == "main"
        assert update.control_date == control_date

    def test_schedule_baseline_update_with_partial_fields_validates(self):
        """Test that ScheduleBaselineUpdate validates with partial fields.

        Acceptance Criteria:
        - Schema validates with only some fields provided
        - Unprovided fields default to None
        """
        # Arrange
        start_date = datetime(2026, 2, 1, tzinfo=UTC)

        # Act - Update with only name and start_date
        update = ScheduleBaselineUpdate(
            name="Updated Name",
            start_date=start_date,
        )

        # Assert
        assert update.name == "Updated Name"
        assert update.start_date == start_date
        assert update.end_date is None
        assert update.progression_type is None
        assert update.description is None
        assert update.branch is None
        assert update.control_date is None

    def test_schedule_baseline_update_with_invalid_type_raises_validation_error(self):
        """Test that ScheduleBaselineUpdate rejects invalid types.

        Acceptance Criteria:
        - Schema with invalid field type raises ValidationError
        - Type validation is enforced
        """
        # Act & Assert - Invalid progression_type type
        with pytest.raises(ValidationError) as exc_info:
            ScheduleBaselineUpdate(progression_type=123)

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("progression_type",) for error in errors)

    def test_schedule_baseline_update_with_branch_and_control_date_validates(self):
        """Test that ScheduleBaselineUpdate accepts branch and control_date.

        Acceptance Criteria:
        - Schema validates with branch="main" and control_date provided
        - Both fields are optional
        """
        # Arrange
        control_date = datetime(2026, 1, 19, tzinfo=UTC)

        # Act - Update with only branch and control_date
        update = ScheduleBaselineUpdate(
            branch="main",
            control_date=control_date,
        )

        # Assert
        assert update.branch == "main"
        assert update.control_date == control_date
        assert update.name is None
        assert update.start_date is None
