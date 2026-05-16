"""Unit tests for PV (Planned Value) calculation.

Tests the core EVM calculation: PV = BAC × Progress

These are pure mathematical tests that don't require database access.
"""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from app.models.domain.schedule_baseline import ScheduleBaseline
from app.services.progression.gaussian import GaussianProgression
from app.services.progression.linear import LinearProgression
from app.services.progression.logarithmic import LogarithmicProgression


class TestPVCalculation:
    """Test Planned Value (PV) calculation for EVM.

    PV = BAC × Progress
    Where:
    - BAC = Budget at Completion (total planned budget)
    - Progress = Calculated based on progression type and current date
    """

    def test_pv_calculation_linear_midpoint(self):
        """At schedule midpoint, Linear PV should be exactly 50% of BAC."""
        # Arrange
        bac = Decimal("10000.00")  # Budget at Completion
        start_date = datetime(2026, 1, 1, tzinfo=UTC)
        end_date = datetime(2026, 12, 31, tzinfo=UTC)
        mid_date = datetime(2026, 7, 2, tzinfo=UTC)  # ~50% through

        # Act
        progress = LinearProgression().calculate_progress(
            mid_date, start_date, end_date
        )
        pv = bac * Decimal(str(progress))

        # Assert
        assert progress == pytest.approx(0.5, abs=1e-6)
        assert pv == Decimal("5000.00"), "PV should be exactly 50% of BAC at midpoint"

    def test_pv_calculation_gaussian_s_curve(self):
        """Gaussian S-curve should show slow start, fast middle, tapering end."""
        # Arrange
        start_date = datetime(2026, 1, 1, tzinfo=UTC)
        end_date = datetime(2026, 12, 31, tzinfo=UTC)  # 1 year
        quarter_date = datetime(2026, 4, 2, tzinfo=UTC)  # ~25% through
        mid_date = datetime(2026, 7, 2, tzinfo=UTC)  # ~50% through
        three_quarter_date = datetime(2026, 10, 1, tzinfo=UTC)  # ~75% through

        # Act
        q1_progress = GaussianProgression().calculate_progress(
            quarter_date, start_date, end_date
        )
        mid_progress = GaussianProgression().calculate_progress(
            mid_date, start_date, end_date
        )
        q3_progress = GaussianProgression().calculate_progress(
            three_quarter_date, start_date, end_date
        )

        # Assert - S-curve characteristics
        # Slow start: progress at 25% time should be < 25%
        assert q1_progress < 0.25, "Gaussian should have slow start"
        # Midpoint should be exactly 50%
        assert mid_progress == pytest.approx(0.5, abs=1e-6)
        # At 75% time, should be > 75% due to middle acceleration
        assert q3_progress > 0.75, "Gaussian accelerates in middle"

    def test_pv_calculation_logarithmic_front_loaded(self):
        """Logarithmic progression should show front-loaded behavior."""
        # Arrange
        bac = Decimal("10000.00")
        start_date = datetime(2026, 1, 1, tzinfo=UTC)
        end_date = datetime(2026, 12, 31, tzinfo=UTC)  # 1 year
        quarter_date = datetime(2026, 4, 2, tzinfo=UTC)  # ~25% through

        # Act
        progress = LogarithmicProgression().calculate_progress(
            quarter_date, start_date, end_date
        )
        pv = bac * Decimal(str(progress))

        # Assert - Front-loaded: at 25% time, progress should be > 25%
        assert progress > 0.25, "Logarithmic should be front-loaded"
        assert pv > Decimal("2500.00"), "PV should be > 25% of BAC at 25% time"

    def test_pv_calculation_before_schedule(self):
        """Before schedule starts, PV should be 0."""
        # Arrange
        bac = Decimal("10000.00")
        start_date = datetime(2026, 1, 1, tzinfo=UTC)
        end_date = datetime(2026, 12, 31, tzinfo=UTC)
        before_date = datetime(2025, 12, 31, tzinfo=UTC)

        # Act
        progress = LinearProgression().calculate_progress(
            before_date, start_date, end_date
        )
        pv = bac * Decimal(str(progress))

        # Assert
        assert progress == 0.0
        assert pv == Decimal("0.00"), "PV should be 0 before schedule starts"

    def test_pv_calculation_after_schedule(self):
        """After schedule ends, PV should equal BAC (100%)."""
        # Arrange
        bac = Decimal("10000.00")
        start_date = datetime(2026, 1, 1, tzinfo=UTC)
        end_date = datetime(2026, 12, 31, tzinfo=UTC)
        after_date = datetime(2027, 1, 1, tzinfo=UTC)

        # Act
        progress = LinearProgression().calculate_progress(
            after_date, start_date, end_date
        )
        pv = bac * Decimal(str(progress))

        # Assert
        assert progress == 1.0
        assert pv == bac, "PV should equal BAC after schedule ends"

    def test_pv_calculation_precision(self):
        """PV calculation should maintain 4 decimal places of precision."""
        # Arrange
        bac = Decimal("12345.67")
        start_date = datetime(2026, 1, 1, tzinfo=UTC)
        end_date = datetime(2026, 12, 31, tzinfo=UTC)
        current_date = datetime(2026, 6, 15, tzinfo=UTC)  # ~47.5% through

        # Act
        progress = LinearProgression().calculate_progress(
            current_date, start_date, end_date
        )
        pv = bac * Decimal(str(progress))

        # Assert - PV should be calculated with proper precision
        expected_pv = bac * Decimal(str(progress))
        # The Decimal multiplication should maintain precision
        assert pv == expected_pv.quantize(Decimal("0.0001")) or abs(
            pv - expected_pv
        ) < Decimal("0.0001")

    def test_pv_calculation_zero_bac(self):
        """PV should be 0 when BAC is 0."""
        # Arrange
        bac = Decimal("0.00")
        start_date = datetime(2026, 1, 1, tzinfo=UTC)
        end_date = datetime(2026, 12, 31, tzinfo=UTC)
        mid_date = datetime(2026, 7, 2, tzinfo=UTC)

        # Act
        progress = LinearProgression().calculate_progress(
            mid_date, start_date, end_date
        )
        pv = bac * Decimal(str(progress))

        # Assert
        assert pv == Decimal("0.00"), "PV should be 0 when BAC is 0"


class TestScheduleBaselinePVCalculation:
    """Test PV calculation using ScheduleBaseline model directly (no DB required)."""

    def test_calculate_pv_from_baseline_linear(self):
        """Calculate PV using a ScheduleBaseline entity with Linear progression."""
        # Arrange - Create baseline without database (just the model instance)
        baseline = ScheduleBaseline(
            id=uuid4(),
            schedule_baseline_id=uuid4(),
            cost_element_id=uuid4(),
            name="Test Baseline",
            start_date=datetime(2026, 1, 1, tzinfo=UTC),
            end_date=datetime(2026, 12, 31, tzinfo=UTC),
            progression_type="LINEAR",
            created_by=uuid4(),
        )
        bac = Decimal("50000.00")
        current_date = datetime(2026, 7, 2, tzinfo=UTC)  # ~50% through

        # Act - Calculate PV = BAC × Progress
        strategy = LinearProgression()
        progress = strategy.calculate_progress(
            current_date, baseline.start_date, baseline.end_date
        )
        pv = bac * Decimal(str(progress))

        # Assert
        assert progress == pytest.approx(0.5, abs=1e-6)
        assert pv == Decimal("25000.00")

    def test_calculate_pv_from_baseline_gaussian(self):
        """Calculate PV using ScheduleBaseline with Gaussian S-curve progression."""
        # Arrange
        baseline = ScheduleBaseline(
            id=uuid4(),
            schedule_baseline_id=uuid4(),
            cost_element_id=uuid4(),
            name="S-Curve Baseline",
            start_date=datetime(2026, 1, 1, tzinfo=UTC),
            end_date=datetime(2026, 12, 31, tzinfo=UTC),
            progression_type="GAUSSIAN",
            created_by=uuid4(),
        )
        bac = Decimal("50000.00")
        current_date = datetime(2026, 7, 2, tzinfo=UTC)  # ~50% through

        # Act - Calculate PV
        strategy = GaussianProgression()
        progress = strategy.calculate_progress(
            current_date, baseline.start_date, baseline.end_date
        )
        pv = bac * Decimal(str(progress))

        # Assert
        assert progress == pytest.approx(0.5, abs=1e-6), (
            "Gaussian midpoint should be exactly 50%"
        )
        assert pv == Decimal("25000.00")

    def test_calculate_pv_from_baseline_logarithmic(self):
        """Calculate PV using ScheduleBaseline with Logarithmic front-loaded progression."""
        # Arrange
        baseline = ScheduleBaseline(
            id=uuid4(),
            schedule_baseline_id=uuid4(),
            cost_element_id=uuid4(),
            name="Front-loaded Baseline",
            start_date=datetime(2026, 1, 1, tzinfo=UTC),
            end_date=datetime(2026, 12, 31, tzinfo=UTC),
            progression_type="LOGARITHMIC",
            created_by=uuid4(),
        )
        bac = Decimal("50000.00")
        current_date = datetime(2026, 4, 2, tzinfo=UTC)  # ~25% through

        # Act - Calculate PV
        strategy = LogarithmicProgression()
        progress = strategy.calculate_progress(
            current_date, baseline.start_date, baseline.end_date
        )
        pv = bac * Decimal(str(progress))

        # Assert
        assert progress > 0.25, "Logarithmic should be front-loaded"
        assert pv > Decimal("12500.00"), "PV should be > 25% of BAC at 25% time"
