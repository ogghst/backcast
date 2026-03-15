"""Performance tests for PV (Planned Value) calculations with database queries.

These tests verify that PV calculations meet the <100ms performance requirement
as specified in the Schedule Baseline 1:1 Architecture plan (T-009).

Performance Criteria:
- Single PV calculation (with DB query): <100ms (target: <50ms)
- 10 cost elements: <500ms
- 100 cost elements: <2000ms

These tests measure the FULL PV calculation including database queries,
not just the progression calculation logic.
"""

import time
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.versioning.enums import BranchMode
from app.models.domain.cost_element import CostElement
from app.models.domain.schedule_baseline import ScheduleBaseline
from app.services.evm_service import EVMService


@pytest.mark.asyncio
@pytest.mark.performance
class TestPVCalculationPerformance:
    """Performance tests for PV calculation through EVMService.

    These tests measure the end-to-end PV calculation including:
    - Database queries for cost element
    - Database queries for schedule baseline
    - Progression strategy calculation
    - PV = BAC × Progress calculation

    This reflects real-world usage where PV is calculated via API calls.
    """

    async def test_single_pv_calculation_under_100ms(
        self, db_session: AsyncSession
    ) -> None:
        """Verify: Single PV calculation completes in <100ms.

        Target: <100ms (requirement from plan T-009)
        Stretch goal: <50ms for optimal user experience

        This test creates a cost element with schedule baseline and measures
        the time to calculate PV via EVMService._get_pv_as_of().
        """
        # Arrange: Create minimal test data
        creator_id = uuid4()

        # Create schedule baseline
        baseline = ScheduleBaseline(
            schedule_baseline_id=uuid4(),
            name="Performance Test Baseline",
            start_date=datetime(2026, 1, 1, tzinfo=UTC),
            end_date=datetime(2026, 12, 31, tzinfo=UTC),
            progression_type="LINEAR",
            valid_time=None,
            transaction_time=None,
            branch="main",
            created_by=creator_id,
        )
        db_session.add(baseline)

        # Create cost element with baseline
        cost_element = CostElement(
            cost_element_id=uuid4(),
            wbe_id=uuid4(),  # Dummy ID for test
            cost_element_type_id=uuid4(),  # Dummy ID for test
            code="CE-PERF-001",
            name="Performance Test Cost Element",
            budget_amount=Decimal("100000.00"),
            schedule_baseline_id=baseline.schedule_baseline_id,
            valid_time=None,
            transaction_time=None,
            branch="main",
            created_by=creator_id,
        )
        db_session.add(cost_element)

        await db_session.commit()

        # Act: Measure PV calculation time
        evm_service = EVMService(db_session)
        control_date = datetime(2026, 7, 2, tzinfo=UTC)  # ~50% through year

        # Warm-up call (to ensure connection is established)
        await evm_service._get_pv_as_of(
            cost_element_id=cost_element.cost_element_id,
            as_of=control_date,
            branch="main",
            branch_mode=BranchMode.MERGE,
        )

        # Measure actual performance
        iterations = 10
        start_time = time.perf_counter()

        for _ in range(iterations):
            pv = await evm_service._get_pv_as_of(
                cost_element_id=cost_element.cost_element_id,
                as_of=control_date,
                branch="main",
                branch_mode=BranchMode.MERGE,
            )
            # Verify PV is calculated correctly
            assert pv > 0

        elapsed_ms = (time.perf_counter() - start_time) * 1000
        avg_ms_per_calc = elapsed_ms / iterations

        # Assert: Performance requirement met
        # Average time should be <100ms per calculation
        assert avg_ms_per_calc < 100, (
            f"PV calculation exceeds 100ms target: {avg_ms_per_calc:.2f}ms average"
        )

        # Stretch goal: <50ms for good UX
        assert avg_ms_per_calc < 50, (
            f"PV calculation slower than 50ms stretch goal: {avg_ms_per_calc:.2f}ms average"
        )

        # Verify PV is approximately 50% of BAC (midpoint of schedule)
        assert Decimal("49000.00") <= pv <= Decimal("51000.00"), (
            f"PV should be ~50% of BAC at midpoint, got {pv}"
        )

    async def test_10_cost_elements_pv_under_500ms(
        self, db_session: AsyncSession
    ) -> None:
        """Verify: PV calculations for 10 cost elements complete in <500ms.

        Target: <500ms total (avg <50ms per element)

        This test simulates a dashboard view showing PV for multiple cost elements.
        """
        # Arrange: Create 10 cost elements with baselines
        creator_id = uuid4()
        cost_elements = []

        for i in range(10):
            # Create baseline
            baseline = ScheduleBaseline(
                schedule_baseline_id=uuid4(),
                name=f"Baseline {i}",
                start_date=datetime(2026, 1, 1, tzinfo=UTC),
                end_date=datetime(2026, 12, 31, tzinfo=UTC),
                progression_type="LINEAR",
                valid_time=None,
                transaction_time=None,
                branch="main",
                created_by=creator_id,
            )
            db_session.add(baseline)

            # Create cost element
            cost_element = CostElement(
                cost_element_id=uuid4(),
                wbe_id=uuid4(),
                cost_element_type_id=uuid4(),
                code=f"CE-PERF-10-{i:03d}",
                name=f"Cost Element {i}",
                budget_amount=Decimal("100000.00"),
                schedule_baseline_id=baseline.schedule_baseline_id,
                valid_time=None,
                transaction_time=None,
                branch="main",
                created_by=creator_id,
            )
            db_session.add(cost_element)
            cost_elements.append(cost_element)

        await db_session.commit()

        # Act: Measure PV calculation time for all elements
        evm_service = EVMService(db_session)
        control_date = datetime(2026, 6, 30, tzinfo=UTC)

        start_time = time.perf_counter()

        results = []
        for cost_element in cost_elements:
            pv = await evm_service._get_pv_as_of(
                cost_element_id=cost_element.cost_element_id,
                as_of=control_date,
                branch="main",
                branch_mode=BranchMode.MERGE,
            )
            results.append(pv)

        elapsed_ms = (time.perf_counter() - start_time) * 1000
        avg_ms_per_calc = elapsed_ms / 10

        # Assert: Performance requirement met
        assert elapsed_ms < 500, (
            f"PV calculations for 10 elements took {elapsed_ms:.2f}ms, "
            f"exceeding 500ms requirement (avg: {avg_ms_per_calc:.2f}ms per element)"
        )

        # Verify all results are valid
        assert len(results) == 10
        for pv in results:
            assert pv > 0

    async def test_100_cost_elements_pv_under_2000ms(
        self, db_session: AsyncSession
    ) -> None:
        """Verify: PV calculations for 100 cost elements complete in <2000ms.

        Target: <2000ms total (avg <20ms per element)

        This test simulates a large project with many cost elements.
        """
        # Arrange: Create 100 cost elements with baselines
        creator_id = uuid4()
        cost_elements = []

        for i in range(100):
            # Create baseline
            baseline = ScheduleBaseline(
                schedule_baseline_id=uuid4(),
                name=f"Baseline {i}",
                start_date=datetime(2026, 1, 1, tzinfo=UTC),
                end_date=datetime(2026, 12, 31, tzinfo=UTC),
                progression_type="LINEAR",
                valid_time=None,
                transaction_time=None,
                branch="main",
                created_by=creator_id,
            )
            db_session.add(baseline)

            # Create cost element
            cost_element = CostElement(
                cost_element_id=uuid4(),
                wbe_id=uuid4(),
                cost_element_type_id=uuid4(),
                code=f"CE-PERF-100-{i:03d}",
                name=f"Cost Element {i}",
                budget_amount=Decimal("100000.00"),
                schedule_baseline_id=baseline.schedule_baseline_id,
                valid_time=None,
                transaction_time=None,
                branch="main",
                created_by=creator_id,
            )
            db_session.add(cost_element)
            cost_elements.append(cost_element)

        await db_session.commit()

        # Act: Measure PV calculation time for all elements
        evm_service = EVMService(db_session)
        control_date = datetime(2026, 6, 30, tzinfo=UTC)

        start_time = time.perf_counter()

        results = []
        for cost_element in cost_elements:
            pv = await evm_service._get_pv_as_of(
                cost_element_id=cost_element.cost_element_id,
                as_of=control_date,
                branch="main",
                branch_mode=BranchMode.MERGE,
            )
            results.append(pv)

        elapsed_ms = (time.perf_counter() - start_time) * 1000
        avg_ms_per_calc = elapsed_ms / 100

        # Assert: Performance requirement met
        assert elapsed_ms < 2000, (
            f"PV calculations for 100 elements took {elapsed_ms:.2f}ms, "
            f"exceeding 2000ms requirement (avg: {avg_ms_per_calc:.2f}ms per element)"
        )

        # Verify all results are valid
        assert len(results) == 100
        for pv in results:
            assert pv > 0

    async def test_pv_with_different_progression_types(
        self, db_session: AsyncSession
    ) -> None:
        """Verify: PV calculation performance is consistent across progression types.

        This test ensures that GAUSSIAN and LOGARITHMIC progression types
        perform similarly to LINEAR (within 2x).
        """
        # Arrange: Create cost elements with different progression types
        creator_id = uuid4()
        progression_types = ["LINEAR", "GAUSSIAN", "LOGARITHMIC"]
        cost_elements = {}

        for prog_type in progression_types:
            baseline = ScheduleBaseline(
                schedule_baseline_id=uuid4(),
                name=f"Baseline {prog_type}",
                start_date=datetime(2026, 1, 1, tzinfo=UTC),
                end_date=datetime(2026, 12, 31, tzinfo=UTC),
                progression_type=prog_type,
                valid_time=None,
                transaction_time=None,
                branch="main",
                created_by=creator_id,
            )
            db_session.add(baseline)

            cost_element = CostElement(
                cost_element_id=uuid4(),
                wbe_id=uuid4(),
                cost_element_type_id=uuid4(),
                code=f"CE-PROG-{prog_type}",
                name=f"Cost Element {prog_type}",
                budget_amount=Decimal("100000.00"),
                schedule_baseline_id=baseline.schedule_baseline_id,
                valid_time=None,
                transaction_time=None,
                branch="main",
                created_by=creator_id,
            )
            db_session.add(cost_element)
            cost_elements[prog_type] = cost_element

        await db_session.commit()

        # Act: Measure PV calculation time for each progression type
        evm_service = EVMService(db_session)
        control_date = datetime(2026, 6, 30, tzinfo=UTC)

        timings = {}
        for prog_type in progression_types:
            start_time = time.perf_counter()

            # Run 10 iterations to get stable measurement
            for _ in range(10):
                pv = await evm_service._get_pv_as_of(
                    cost_element_id=cost_elements[prog_type].cost_element_id,
                    as_of=control_date,
                    branch="main",
                    branch_mode=BranchMode.MERGE,
                )
                assert pv > 0

            elapsed_ms = (time.perf_counter() - start_time) * 1000
            timings[prog_type] = elapsed_ms / 10  # Average per iteration

        # Assert: All progression types should be <100ms
        for prog_type, avg_time in timings.items():
            assert avg_time < 100, f"{prog_type} progression too slow: {avg_time:.2f}ms"

        # Assert: GAUSSIAN and LOGARITHMIC should be within 2x of LINEAR
        linear_time = timings["LINEAR"]
        for prog_type in ["GAUSSIAN", "LOGARITHMIC"]:
            assert timings[prog_type] < linear_time * 2, (
                f"{prog_type} progression ({timings[prog_type]:.2f}ms) is more than 2x slower than LINEAR ({linear_time:.2f}ms)"
            )

    async def test_pv_without_baseline_returns_zero_quickly(
        self, db_session: AsyncSession
    ) -> None:
        """Verify: PV calculation for cost element without baseline completes quickly.

        Target: <50ms (early return optimization)

        This test verifies the early return path when no baseline exists.
        """
        # Arrange: Create cost element WITHOUT schedule baseline
        creator_id = uuid4()

        cost_element = CostElement(
            cost_element_id=uuid4(),
            wbe_id=uuid4(),
            cost_element_type_id=uuid4(),
            code="CE-NO-BL",
            name="Cost Element No Baseline",
            budget_amount=Decimal("100000.00"),
            schedule_baseline_id=None,  # No baseline
            valid_time=None,
            transaction_time=None,
            branch="main",
            created_by=creator_id,
        )
        db_session.add(cost_element)

        await db_session.commit()

        # Act: Measure PV calculation time
        evm_service = EVMService(db_session)
        control_date = datetime(2026, 6, 30, tzinfo=UTC)

        start_time = time.perf_counter()

        pv = await evm_service._get_pv_as_of(
            cost_element_id=cost_element.cost_element_id,
            as_of=control_date,
            branch="main",
            branch_mode=BranchMode.MERGE,
        )

        elapsed_ms = (time.perf_counter() - start_time) * 1000

        # Assert: Should return 0 quickly
        assert pv == Decimal("0"), "PV should be 0 when no baseline exists"
        assert elapsed_ms < 50, (
            f"PV calculation without baseline took {elapsed_ms:.2f}ms, exceeding 50ms target"
        )
