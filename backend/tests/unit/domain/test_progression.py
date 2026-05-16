"""Unit tests for Schedule Progression Functions.

Tests the pure mathematical progression functions used for calculating
Planned Value (PV) in Earned Value Management (EVM).

Following TDD: These tests are written FIRST, before implementation.
"""

from datetime import UTC, datetime, timedelta

import pytest

from app.services.progression.base import ProgressionStrategy
from app.services.progression.gaussian import GaussianProgression
from app.services.progression.linear import LinearProgression
from app.services.progression.logarithmic import LogarithmicProgression


class TestLinearProgression:
    """Test suite for Linear progression strategy.

    Linear progression represents uniform progress over time.
    At 50% of duration, progress should be exactly 50%.
    """

    def test_linear_progression_start_point(self):
        """At start (current = start_date), progress should be 0.0."""
        # Arrange
        start_date = datetime(2026, 1, 1, tzinfo=UTC)
        end_date = datetime(2026, 1, 11, tzinfo=UTC)  # 10 days
        strategy = LinearProgression()

        # Act
        progress = strategy.calculate_progress(start_date, start_date, end_date)

        # Assert
        assert progress == 0.0, "Progress at start should be exactly 0.0"

    def test_linear_progression_end_point(self):
        """At end (current = end_date), progress should be 1.0."""
        # Arrange
        start_date = datetime(2026, 1, 1, tzinfo=UTC)
        end_date = datetime(2026, 1, 11, tzinfo=UTC)  # 10 days
        strategy = LinearProgression()

        # Act
        progress = strategy.calculate_progress(end_date, start_date, end_date)

        # Assert
        assert progress == 1.0, "Progress at end should be exactly 1.0"

    def test_linear_progression_midpoint(self):
        """At midpoint (50% of duration), progress should be 0.5."""
        # Arrange
        start_date = datetime(2026, 1, 1, tzinfo=UTC)
        end_date = datetime(2026, 1, 11, tzinfo=UTC)  # 10 days
        mid_date = datetime(2026, 1, 6, tzinfo=UTC)  # Day 5
        strategy = LinearProgression()

        # Act
        progress = strategy.calculate_progress(mid_date, start_date, end_date)

        # Assert
        assert progress == pytest.approx(0.5, abs=1e-6), (
            "Progress at midpoint should be exactly 0.5"
        )

    def test_linear_progression_quarter_point(self):
        """At 25% of duration, progress should be 0.25."""
        # Arrange
        start_date = datetime(2026, 1, 1, tzinfo=UTC)
        end_date = datetime(2026, 1, 11, tzinfo=UTC)  # 10 days
        quarter_date = start_date + timedelta(days=2.5)  # 25% of 10 days
        strategy = LinearProgression()

        # Act
        progress = strategy.calculate_progress(quarter_date, start_date, end_date)

        # Assert
        assert progress == pytest.approx(0.25, abs=1e-5), (
            "Progress at 25% should be 0.25"
        )

    def test_linear_progression_three_quarter_point(self):
        """At 75% of duration, progress should be 0.75."""
        # Arrange
        start_date = datetime(2026, 1, 1, tzinfo=UTC)
        end_date = datetime(2026, 1, 11, tzinfo=UTC)  # 10 days
        three_quarter_date = start_date + timedelta(days=7.5)  # 75% of 10 days
        strategy = LinearProgression()

        # Act
        progress = strategy.calculate_progress(three_quarter_date, start_date, end_date)

        # Assert
        assert progress == pytest.approx(0.75, abs=1e-5), (
            "Progress at 75% should be 0.75"
        )

    def test_linear_progression_before_start(self):
        """Before start date, progress should be clamped to 0.0."""
        # Arrange
        start_date = datetime(2026, 1, 5, tzinfo=UTC)
        end_date = datetime(2026, 1, 15, tzinfo=UTC)
        before_date = datetime(2026, 1, 1, tzinfo=UTC)
        strategy = LinearProgression()

        # Act
        progress = strategy.calculate_progress(before_date, start_date, end_date)

        # Assert
        assert progress == 0.0, "Progress before start should be clamped to 0.0"

    def test_linear_progression_after_end(self):
        """After end date, progress should be clamped to 1.0."""
        # Arrange
        start_date = datetime(2026, 1, 5, tzinfo=UTC)
        end_date = datetime(2026, 1, 15, tzinfo=UTC)
        after_date = datetime(2026, 1, 20, tzinfo=UTC)
        strategy = LinearProgression()

        # Act
        progress = strategy.calculate_progress(after_date, start_date, end_date)

        # Assert
        assert progress == 1.0, "Progress after end should be clamped to 1.0"


class TestGaussianProgression:
    """Test suite for Gaussian (S-curve) progression strategy.

    Gaussian progression models realistic project progress with slow start,
    rapid middle phase, and tapering end. Creates an S-curve pattern.
    """

    def test_gaussian_progression_start_point(self):
        """At start (current = start_date), progress should be 0.0."""
        # Arrange
        start_date = datetime(2026, 1, 1, tzinfo=UTC)
        end_date = datetime(2026, 1, 11, tzinfo=UTC)
        strategy = GaussianProgression()

        # Act
        progress = strategy.calculate_progress(start_date, start_date, end_date)

        # Assert
        assert progress == pytest.approx(0.0, abs=1e-6), (
            "Progress at start should be 0.0"
        )

    def test_gaussian_progression_end_point(self):
        """At end (current = end_date), progress should be 1.0."""
        # Arrange
        start_date = datetime(2026, 1, 1, tzinfo=UTC)
        end_date = datetime(2026, 1, 11, tzinfo=UTC)
        strategy = GaussianProgression()

        # Act
        progress = strategy.calculate_progress(end_date, start_date, end_date)

        # Assert
        assert progress == pytest.approx(1.0, abs=1e-6), "Progress at end should be 1.0"

    def test_gaussian_progression_midpoint(self):
        """At midpoint, Gaussian S-curve should be at 50% progress."""
        # Arrange
        start_date = datetime(2026, 1, 1, tzinfo=UTC)
        end_date = datetime(2026, 1, 11, tzinfo=UTC)  # 10 days
        mid_date = datetime(2026, 1, 6, tzinfo=UTC)  # Day 5
        strategy = GaussianProgression()

        # Act
        progress = strategy.calculate_progress(mid_date, start_date, end_date)

        # Assert
        assert progress == pytest.approx(0.5, abs=1e-6), (
            "Gaussian midpoint should be exactly 0.5"
        )

    def test_gaussian_progression_s_curve_slow_start(self):
        """At 25% time, progress should be LESS than 25% (slow start)."""
        # Arrange
        start_date = datetime(2026, 1, 1, tzinfo=UTC)
        end_date = datetime(2026, 1, 11, tzinfo=UTC)  # 10 days
        quarter_date = start_date + timedelta(days=2.5)  # 25% of duration
        strategy = GaussianProgression()

        # Act
        progress = strategy.calculate_progress(quarter_date, start_date, end_date)

        # Assert
        assert progress < 0.25, (
            "Gaussian S-curve should have slow start (< 25% at 25% time)"
        )
        assert progress > 0.0, "Progress should still be positive"

    def test_gaussian_progression_s_curve_slow_end(self):
        """At 75% time, progress should be GREATER than 75% due to middle acceleration."""
        # Arrange
        start_date = datetime(2026, 1, 1, tzinfo=UTC)
        end_date = datetime(2026, 1, 11, tzinfo=UTC)  # 10 days
        three_quarter_date = start_date + timedelta(days=7.5)  # 75% of duration
        strategy = GaussianProgression()

        # Act
        progress = strategy.calculate_progress(three_quarter_date, start_date, end_date)

        # Assert
        # S-curve accelerates in middle, so at 75% time we're past 75% progress
        assert progress > 0.75, (
            "Gaussian S-curve accelerates in middle (> 75% at 75% time)"
        )
        assert progress < 1.0, "But not complete yet"

    def test_gaussian_progression_symmetry(self):
        """Gaussian progression should be symmetric around midpoint."""
        # Arrange
        start_date = datetime(2026, 1, 1, tzinfo=UTC)
        end_date = datetime(2026, 1, 11, tzinfo=UTC)
        mid_date = datetime(2026, 1, 6, tzinfo=UTC)
        delta = timedelta(days=2)
        strategy = GaussianProgression()

        # Act
        progress_before = strategy.calculate_progress(
            mid_date - delta, start_date, end_date
        )
        progress_after = strategy.calculate_progress(
            mid_date + delta, start_date, end_date
        )

        # Assert
        expected_after = 1.0 - progress_before
        assert progress_after == pytest.approx(expected_after, abs=1e-6), (
            "Gaussian should be symmetric around midpoint"
        )

    def test_gaussian_progression_before_start(self):
        """Before start date, progress should be clamped to 0.0."""
        # Arrange
        start_date = datetime(2026, 1, 5, tzinfo=UTC)
        end_date = datetime(2026, 1, 15, tzinfo=UTC)
        before_date = datetime(2026, 1, 1, tzinfo=UTC)
        strategy = GaussianProgression()

        # Act
        progress = strategy.calculate_progress(before_date, start_date, end_date)

        # Assert
        assert progress == 0.0

    def test_gaussian_progression_after_end(self):
        """After end date, progress should be clamped to 1.0."""
        # Arrange
        start_date = datetime(2026, 1, 5, tzinfo=UTC)
        end_date = datetime(2026, 1, 15, tzinfo=UTC)
        after_date = datetime(2026, 1, 20, tzinfo=UTC)
        strategy = GaussianProgression()

        # Act
        progress = strategy.calculate_progress(after_date, start_date, end_date)

        # Assert
        assert progress == 1.0


class TestLogarithmicProgression:
    """Test suite for Logarithmic (front-loaded) progression strategy.

    Logarithmic progression represents front-loaded work where progress
    is rapid initially and tapers off.
    """

    def test_logarithmic_progression_start_point(self):
        """At start (current = start_date), progress should be 0.0."""
        # Arrange
        start_date = datetime(2026, 1, 1, tzinfo=UTC)
        end_date = datetime(2026, 1, 11, tzinfo=UTC)
        strategy = LogarithmicProgression()

        # Act
        progress = strategy.calculate_progress(start_date, start_date, end_date)

        # Assert
        assert progress == pytest.approx(0.0, abs=1e-6), (
            "Progress at start should be 0.0"
        )

    def test_logarithmic_progression_end_point(self):
        """At end (current = end_date), progress should be 1.0."""
        # Arrange
        start_date = datetime(2026, 1, 1, tzinfo=UTC)
        end_date = datetime(2026, 1, 11, tzinfo=UTC)
        strategy = LogarithmicProgression()

        # Act
        progress = strategy.calculate_progress(end_date, start_date, end_date)

        # Assert
        assert progress == pytest.approx(1.0, abs=1e-6), "Progress at end should be 1.0"

    def test_logarithmic_progression_front_loaded(self):
        """At 25% time, progress should be GREATER than 25% (front-loaded)."""
        # Arrange
        start_date = datetime(2026, 1, 1, tzinfo=UTC)
        end_date = datetime(2026, 1, 11, tzinfo=UTC)  # 10 days
        quarter_date = start_date + timedelta(days=2.5)  # 25% of duration
        strategy = LogarithmicProgression()

        # Act
        progress = strategy.calculate_progress(quarter_date, start_date, end_date)

        # Assert
        assert progress > 0.25, "Logarithmic should be front-loaded (> 25% at 25% time)"
        assert progress < 0.5, "But not past midpoint yet"

    def test_logarithmic_progression_slow_finish(self):
        """At 75% time, progress should be significantly advanced but not complete."""
        # Arrange
        start_date = datetime(2026, 1, 1, tzinfo=UTC)
        end_date = datetime(2026, 1, 11, tzinfo=UTC)  # 10 days
        three_quarter_date = start_date + timedelta(days=7.5)  # 75% of duration
        strategy = LogarithmicProgression()

        # Act
        progress = strategy.calculate_progress(three_quarter_date, start_date, end_date)

        # Assert
        assert progress > 0.75, "Should be well past 75% at 75% time"
        assert progress < 1.0, "But not complete"

    def test_logarithmic_progression_before_start(self):
        """Before start date, progress should be clamped to 0.0."""
        # Arrange
        start_date = datetime(2026, 1, 5, tzinfo=UTC)
        end_date = datetime(2026, 1, 15, tzinfo=UTC)
        before_date = datetime(2026, 1, 1, tzinfo=UTC)
        strategy = LogarithmicProgression()

        # Act
        progress = strategy.calculate_progress(before_date, start_date, end_date)

        # Assert
        assert progress == 0.0

    def test_logarithmic_progression_after_end(self):
        """After end date, progress should be clamped to 1.0."""
        # Arrange
        start_date = datetime(2026, 1, 5, tzinfo=UTC)
        end_date = datetime(2026, 1, 15, tzinfo=UTC)
        after_date = datetime(2026, 1, 20, tzinfo=UTC)
        strategy = LogarithmicProgression()

        # Act
        progress = strategy.calculate_progress(after_date, start_date, end_date)

        # Assert
        assert progress == 1.0


class TestProgressionStrategy:
    """Test the base progression strategy interface."""

    def test_progression_strategy_is_abstract(self):
        """ProgressionStrategy should not be instantiable directly."""
        # Arrange & Act & Assert
        with pytest.raises(TypeError):
            ProgressionStrategy()  # type: ignore
