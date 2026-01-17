"""Unit tests for ScheduleBaseline domain model.

Tests model behavior, mixin composition, and versioning/branching support.
"""

from datetime import UTC, datetime
from enum import Enum
from uuid import uuid4

from app.models.domain.schedule_baseline import ScheduleBaseline


class ProgressionType(str, Enum):
    """Progression type enumeration for schedule baselines."""

    LINEAR = "LINEAR"
    GAUSSIAN = "GAUSSIAN"
    LOGARITHMIC = "LOGARITHMIC"


class TestScheduleBaselineModel:
    """Test ScheduleBaseline model behavior and Mixin composition."""

    def test_schedule_baseline_initialization(self):
        """Test basic initialization and mixin defaults.

        Acceptance Criteria:
        - ScheduleBaseline model can be instantiated with required fields
        - schedule_baseline_id is set (root ID)
        - VersionableMixin provides temporal fields (valid_time, transaction_time, deleted_at)
        - BranchableMixin provides branching fields (branch, parent_id, merge_from_branch)
        - All business fields are correctly set
        """
        # Arrange
        schedule_baseline_id = uuid4()
        cost_element_id = uuid4()
        actor_id = uuid4()
        start_date = datetime(2026, 1, 1, tzinfo=UTC)
        end_date = datetime(2026, 12, 31, tzinfo=UTC)

        # Act
        baseline = ScheduleBaseline(
            schedule_baseline_id=schedule_baseline_id,
            cost_element_id=cost_element_id,
            name="Q1 2026 Baseline",
            start_date=start_date,
            end_date=end_date,
            progression_type=ProgressionType.LINEAR.value,
            description="Initial baseline for Q1",
            created_by=actor_id,
            branch="main",
        )

        # Assert - Root ID
        assert baseline.schedule_baseline_id == schedule_baseline_id

        # Assert - Foreign Keys
        assert baseline.cost_element_id == cost_element_id

        # Assert - Business Fields
        assert baseline.name == "Q1 2026 Baseline"
        assert baseline.start_date == start_date
        assert baseline.end_date == end_date
        assert baseline.progression_type == ProgressionType.LINEAR.value
        assert baseline.description == "Initial baseline for Q1"

        # Assert - VersionableMixin fields (created_by is set explicitly, deleted_at/ deleted_by start as None)
        # Note: valid_time and transaction_time are set by PostgreSQL on insert, not on instantiation
        assert baseline.deleted_at is None
        assert baseline.created_by == actor_id
        assert baseline.deleted_by is None

        # Assert - BranchableMixin fields
        assert baseline.branch == "main"
        assert baseline.parent_id is None
        assert baseline.merge_from_branch is None

    def test_schedule_baseline_all_progression_types(self):
        """Test that all progression types are valid."""
        # Arrange
        schedule_baseline_id = uuid4()
        cost_element_id = uuid4()
        actor_id = uuid4()

        # Act & Assert - Test all progression types
        for prog_type in [
            ProgressionType.LINEAR,
            ProgressionType.GAUSSIAN,
            ProgressionType.LOGARITHMIC,
        ]:
            baseline = ScheduleBaseline(
                schedule_baseline_id=schedule_baseline_id,
                cost_element_id=cost_element_id,
                name=f"Baseline {prog_type.value}",
                start_date=datetime(2026, 1, 1, tzinfo=UTC),
                end_date=datetime(2026, 12, 31, tzinfo=UTC),
                progression_type=prog_type.value,
                created_by=actor_id,
            )
            assert baseline.progression_type == prog_type.value

    def test_schedule_baseline_branching(self):
        """Test that ScheduleBaseline supports branching via BranchableMixin."""
        # Arrange
        parent_id = uuid4()
        schedule_baseline_id = uuid4()
        cost_element_id = uuid4()
        actor_id = uuid4()

        # Act - Create a branch baseline
        branch_baseline = ScheduleBaseline(
            schedule_baseline_id=schedule_baseline_id,
            cost_element_id=cost_element_id,
            name="Change Order Baseline",
            start_date=datetime(2026, 2, 1, tzinfo=UTC),
            end_date=datetime(2026, 12, 31, tzinfo=UTC),
            progression_type=ProgressionType.GAUSSIAN.value,
            created_by=actor_id,
            branch="change-order-001",
            parent_id=parent_id,
        )

        # Assert
        assert branch_baseline.branch == "change-order-001"
        assert branch_baseline.parent_id == parent_id
        assert branch_baseline.merge_from_branch is None

    def test_schedule_baseline_optional_description(self):
        """Test that description is optional."""
        # Arrange
        schedule_baseline_id = uuid4()
        cost_element_id = uuid4()
        actor_id = uuid4()

        # Act - Create without description
        baseline = ScheduleBaseline(
            schedule_baseline_id=schedule_baseline_id,
            cost_element_id=cost_element_id,
            name="Minimal Baseline",
            start_date=datetime(2026, 1, 1, tzinfo=UTC),
            end_date=datetime(2026, 6, 30, tzinfo=UTC),
            progression_type=ProgressionType.LOGARITHMIC.value,
            created_by=actor_id,
        )

        # Assert
        assert baseline.description is None

    def test_schedule_baseline_repr(self):
        """Test the __repr__ method for debugging."""
        # Arrange
        schedule_baseline_id = uuid4()
        cost_element_id = uuid4()

        baseline = ScheduleBaseline(
            schedule_baseline_id=schedule_baseline_id,
            cost_element_id=cost_element_id,
            name="Test Baseline",
            start_date=datetime(2026, 1, 1, tzinfo=UTC),
            end_date=datetime(2026, 12, 31, tzinfo=UTC),
            progression_type=ProgressionType.LINEAR.value,
            created_by=uuid4(),
        )

        # Act & Assert - Check repr contains key info
        repr_str = repr(baseline)
        assert "ScheduleBaseline" in repr_str
        assert str(schedule_baseline_id) in repr_str
        assert "Test Baseline" in repr_str
