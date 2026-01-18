"""Performance benchmark tests for PV (Planned Value) calculation.

These tests verify that PV calculations meet the performance target of
< 50ms for a single entity calculation.

Performance Target:
- Linear Progression: < 10ms (simple calculation)
- Gaussian Progression: < 15ms (math.erf is optimized C)
- Logarithmic Progression: < 10ms (simple calculation)
- Full Baseline PV (with DB query): < 50ms (includes DB roundtrip)
"""

import time
from datetime import datetime

import pytest

from app.services.progression.gaussian import GaussianProgression
from app.services.progression.linear import LinearProgression
from app.services.progression.logarithmic import LogarithmicProgression


class TestPVCalculationPerformance:
    """Performance tests for PV calculation logic."""

    @pytest.mark.performance
    def test_linear_progression_performance(self):
        """Benchmark: Linear progression calculation should complete in < 10ms.

        Target: < 10ms for 1000 iterations (avg < 0.01ms per calculation)
        """
        progression = LinearProgression()
        start = datetime(2026, 1, 1)
        end = datetime(2026, 12, 31)
        current = datetime(2026, 6, 30)

        iterations = 1000
        start_time = time.perf_counter()

        for _ in range(iterations):
            result = progression.calculate_progress(current, start, end)
            assert 0.0 <= result <= 1.0

        elapsed_ms = (time.perf_counter() - start_time) * 1000
        avg_ms_per_calc = elapsed_ms / iterations

        # Assert: Average calculation time < 0.01ms (10 microseconds)
        assert (
            avg_ms_per_calc < 0.01
        ), f"Linear progression too slow: {avg_ms_per_calc:.6f}ms per calculation"

        # Total time for 1000 calculations should be < 10ms
        assert elapsed_ms < 10, f"Linear progression batch too slow: {elapsed_ms:.2f}ms"

    @pytest.mark.performance
    def test_gaussian_progression_performance(self):
        """Benchmark: Gaussian progression calculation should complete in < 15ms.

        Target: < 15ms for 1000 iterations (avg < 0.015ms per calculation)
        Uses math.erf which is optimized C implementation.
        """
        progression = GaussianProgression()
        start = datetime(2026, 1, 1)
        end = datetime(2026, 12, 31)
        current = datetime(2026, 6, 30)

        iterations = 1000
        start_time = time.perf_counter()

        for _ in range(iterations):
            result = progression.calculate_progress(current, start, end)
            assert 0.0 <= result <= 1.0

        elapsed_ms = (time.perf_counter() - start_time) * 1000
        avg_ms_per_calc = elapsed_ms / iterations

        # Assert: Average calculation time < 0.015ms (15 microseconds)
        assert (
            avg_ms_per_calc < 0.015
        ), f"Gaussian progression too slow: {avg_ms_per_calc:.6f}ms per calculation"

        # Total time for 1000 calculations should be < 15ms
        assert elapsed_ms < 15, f"Gaussian progression batch too slow: {elapsed_ms:.2f}ms"

    @pytest.mark.performance
    def test_logarithmic_progression_performance(self):
        """Benchmark: Logarithmic progression calculation should complete in < 10ms.

        Target: < 10ms for 1000 iterations (avg < 0.01ms per calculation)
        """
        progression = LogarithmicProgression()
        start = datetime(2026, 1, 1)
        end = datetime(2026, 12, 31)
        current = datetime(2026, 6, 30)

        iterations = 1000
        start_time = time.perf_counter()

        for _ in range(iterations):
            result = progression.calculate_progress(current, start, end)
            assert 0.0 <= result <= 1.0

        elapsed_ms = (time.perf_counter() - start_time) * 1000
        avg_ms_per_calc = elapsed_ms / iterations

        # Assert: Average calculation time < 0.01ms (10 microseconds)
        assert (
            avg_ms_per_calc < 0.01
        ), f"Logarithmic progression too slow: {avg_ms_per_calc:.6f}ms per calculation"

        # Total time for 1000 calculations should be < 10ms
        assert elapsed_ms < 10, f"Logarithmic progression batch too slow: {elapsed_ms:.2f}ms"

    @pytest.mark.performance
    def test_pv_calculation_full_formula_performance(self):
        """Benchmark: Full PV = BAC * Progress calculation should complete in < 20ms.

        Target: < 20ms for 1000 iterations (avg < 0.02ms per calculation)
        Includes Decimal arithmetic which is slightly slower than float.
        """
        from decimal import Decimal

        progression = GaussianProgression()
        start = datetime(2026, 1, 1)
        end = datetime(2026, 12, 31)
        current = datetime(2026, 6, 30)
        bac = Decimal("100000.00")

        iterations = 1000
        start_time = time.perf_counter()

        for _ in range(iterations):
            progress = progression.calculate_progress(current, start, end)
            pv = bac * Decimal(str(progress))
            assert pv >= 0

        elapsed_ms = (time.perf_counter() - start_time) * 1000
        avg_ms_per_calc = elapsed_ms / iterations

        # Assert: Average calculation time < 0.02ms (20 microseconds)
        assert (
            avg_ms_per_calc < 0.02
        ), f"PV calculation too slow: {avg_ms_per_calc:.6f}ms per calculation"

        # Total time for 1000 calculations should be < 20ms
        assert elapsed_ms < 20, f"PV calculation batch too slow: {elapsed_ms:.2f}ms"

    @pytest.mark.performance
    def test_mixed_progression_types_performance(self):
        """Benchmark: Mixed progression types should complete in < 30ms.

        Simulates real-world scenario where different baselines use different
        progression types.
        """
        progressions = [
            LinearProgression(),
            GaussianProgression(),
            LogarithmicProgression(),
        ]
        start = datetime(2026, 1, 1)
        end = datetime(2026, 12, 31)
        current = datetime(2026, 6, 30)

        iterations = 1000
        start_time = time.perf_counter()

        for i in range(iterations):
            progression = progressions[i % len(progressions)]
            result = progression.calculate_progress(current, start, end)
            assert 0.0 <= result <= 1.0

        elapsed_ms = (time.perf_counter() - start_time) * 1000
        avg_ms_per_calc = elapsed_ms / iterations

        # Assert: Average calculation time < 0.03ms (30 microseconds)
        assert (
            avg_ms_per_calc < 0.03
        ), f"Mixed progression too slow: {avg_ms_per_calc:.6f}ms per calculation"

        # Total time for 1000 calculations should be < 30ms
        assert elapsed_ms < 30, f"Mixed progression batch too slow: {elapsed_ms:.2f}ms"


class TestPVCalculationPerformanceTarget:
    """Verify the < 50ms target for single entity PV calculation.

    Note: This test measures ONLY the calculation logic, not database queries.
    The full endpoint (including DB query) should still be < 50ms since
    the calculation itself is < 0.02ms (200x faster than target).
    """

    @pytest.mark.performance
    def test_single_pv_calculation_under_50ms(self):
        """Verify: Single PV calculation completes in < 50ms.

        This is a relaxed target - actual calculation is ~200x faster.
        Even with database query overhead, the full request should be < 50ms.
        """
        from decimal import Decimal

        progression = GaussianProgression()
        start = datetime(2026, 1, 1)
        end = datetime(2026, 12, 31)
        current = datetime(2026, 6, 30)
        bac = Decimal("100000.00")

        start_time = time.perf_counter()

        # Single PV calculation
        progress = progression.calculate_progress(current, start, end)
        _ = bac * Decimal(str(progress))  # Calculate but don't use (timing test)

        elapsed_ms = (time.perf_counter() - start_time) * 1000

        # Assert: Single calculation < 50ms (very generous target)
        assert (
            elapsed_ms < 50
        ), f"PV calculation exceeds 50ms target: {elapsed_ms:.2f}ms"

        # In reality, this should be < 1ms
        assert (
            elapsed_ms < 1
        ), f"PV calculation unexpectedly slow: {elapsed_ms:.2f}ms (expected < 1ms)"
