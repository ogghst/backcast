"""Tests for EVMService.

Covers metric calculations at the work package level, aggregation
through the hierarchy (CA -> WBS -> Project), variance/indices,
time-series generation, and edge cases.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.versioning.enums import BranchMode
from app.models.schemas.evm import (
    EntityType,
    EVMTimeSeriesGranularity,
)
from app.services.evm_service import EVMService
from app.services.forecast_service import ForecastService
from app.services.schedule_baseline_service import ScheduleBaselineService
from tests.factories import (
    create_full_hierarchy,
    create_test_cost_registration,
    create_test_progress_entry,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _setup_wp_with_data(
    db,
    actor_id,
    budget: Decimal = Decimal("100000.00"),
    eac: Decimal | None = None,
    progress_pct: Decimal = Decimal("0.00"),
    cost_amounts: list[Decimal] | None = None,
) -> dict:
    """Create a full hierarchy and optionally attach baseline, forecast, cost, progress."""
    hierarchy = await create_full_hierarchy(db, actor_id, budget_amount=budget)
    wp = hierarchy["wp"]

    # Schedule baseline: 90-day span starting 45 days ago
    sb_service = ScheduleBaselineService(db)
    now = datetime.now(UTC)
    await sb_service.create_for_work_package(
        work_package_id=wp.work_package_id,
        actor_id=actor_id,
        name="Test Baseline",
        start_date=now - timedelta(days=45),
        end_date=now + timedelta(days=45),
        progression_type="LINEAR",
    )

    # Forecast (EAC)
    if eac is not None:
        f_service = ForecastService(db)
        await f_service.create_for_work_package(
            work_package_id=wp.work_package_id,
            actor_id=actor_id,
            eac_amount=eac,
            basis_of_estimate="Test EAC",
        )

    # Cost registrations (AC)
    if cost_amounts:
        ce = hierarchy["ce"]
        for amt in cost_amounts:
            await create_test_cost_registration(
                db, actor_id, ce.cost_element_id, amount=amt
            )

    # Progress entry (EV)
    if progress_pct > 0:
        await create_test_progress_entry(
            db, actor_id, wp.work_package_id, progress_percentage=progress_pct
        )

    return hierarchy


# ---------------------------------------------------------------------------
# Work Package level EVM metrics
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_calculate_evm_metrics_basic(db: AsyncSession, actor_id: UUID) -> None:
    """calculate_evm_metrics should return correct BAC, PV, AC, EV, CPI, SPI."""
    hierarchy = await _setup_wp_with_data(
        db,
        actor_id,
        budget=Decimal("100000"),
        eac=Decimal("110000"),
        progress_pct=Decimal("50.00"),
        cost_amounts=[Decimal("40000"), Decimal("10000")],
    )
    wp = hierarchy["wp"]
    service = EVMService(db)

    metrics = await service.calculate_evm_metrics(
        work_package_id=wp.work_package_id,
        control_date=datetime.now(UTC),
    )

    # BAC = 100000
    assert metrics.bac == pytest.approx(100000, abs=1)

    # AC = 40000 + 10000 = 50000
    assert metrics.ac == pytest.approx(50000, abs=1)

    # EV = BAC * progress% = 100000 * 50/100 = 50000
    assert metrics.ev == pytest.approx(50000, abs=1)

    # PV: linear baseline starting 45d ago, ending 45d from now => ~50%
    # PV = 100000 * ~0.5 = ~50000
    assert metrics.pv == pytest.approx(50000, abs=2000)

    # EAC from forecast
    assert metrics.eac == pytest.approx(110000, abs=1)

    # CV = EV - AC = 50000 - 50000 = 0
    assert metrics.cv == pytest.approx(0, abs=1)

    # CPI = EV / AC = 1.0
    assert metrics.cpi == pytest.approx(1.0, abs=0.01)


@pytest.mark.asyncio
async def test_calculate_evm_metrics_no_progress_warns(
    db: AsyncSession, actor_id: UUID
) -> None:
    """Without progress entries, EV should be 0 and a warning should be set."""
    hierarchy = await _setup_wp_with_data(
        db,
        actor_id,
        budget=Decimal("50000"),
        cost_amounts=[Decimal("10000")],
    )
    wp = hierarchy["wp"]
    service = EVMService(db)

    metrics = await service.calculate_evm_metrics(
        work_package_id=wp.work_package_id,
        control_date=datetime.now(UTC),
    )

    assert metrics.ev == 0
    assert metrics.warning is not None
    assert "No progress" in metrics.warning


@pytest.mark.asyncio
async def test_calculate_evm_metrics_raises_for_missing_wp(
    db: AsyncSession, actor_id: UUID
) -> None:
    """calculate_evm_metrics should raise ValueError for nonexistent work package."""
    service = EVMService(db)

    with pytest.raises(ValueError, match="not found"):
        await service.calculate_evm_metrics(
            work_package_id=uuid4(),
            control_date=datetime.now(UTC),
        )


@pytest.mark.asyncio
async def test_calculate_evm_metrics_no_baseline_pv_is_zero(
    db: AsyncSession, actor_id: UUID
) -> None:
    """Without a schedule baseline, PV should be 0."""
    hierarchy = await create_full_hierarchy(db, actor_id)
    wp = hierarchy["wp"]
    service = EVMService(db)

    # No baseline, no cost, no progress
    metrics = await service.calculate_evm_metrics(
        work_package_id=wp.work_package_id,
        control_date=datetime.now(UTC),
    )

    assert metrics.pv == 0
    assert metrics.ac == 0


@pytest.mark.asyncio
async def test_spi_less_than_one_when_behind_schedule(
    db: AsyncSession, actor_id: UUID
) -> None:
    """SPI < 1.0 when EV < PV (behind schedule)."""
    hierarchy = await _setup_wp_with_data(
        db,
        actor_id,
        budget=Decimal("100000"),
        progress_pct=Decimal("20.00"),  # EV = 20000
    )
    wp = hierarchy["wp"]
    service = EVMService(db)

    # At midpoint of 90-day baseline, PV ~ 50000, but EV is only 20000
    metrics = await service.calculate_evm_metrics(
        work_package_id=wp.work_package_id,
        control_date=datetime.now(UTC),
    )

    assert metrics.ev < metrics.pv
    assert metrics.spi is not None
    assert metrics.spi < 1.0


@pytest.mark.asyncio
async def test_cpi_less_than_one_when_over_budget(
    db: AsyncSession, actor_id: UUID
) -> None:
    """CPI < 1.0 when EV < AC (over budget)."""
    hierarchy = await _setup_wp_with_data(
        db,
        actor_id,
        budget=Decimal("100000"),
        progress_pct=Decimal("30.00"),  # EV = 30000
        cost_amounts=[Decimal("50000")],  # AC = 50000 > EV
    )
    wp = hierarchy["wp"]
    service = EVMService(db)

    metrics = await service.calculate_evm_metrics(
        work_package_id=wp.work_package_id,
        control_date=datetime.now(UTC),
    )

    assert metrics.ac > metrics.ev
    assert metrics.cpi is not None
    assert metrics.cpi < 1.0


@pytest.mark.asyncio
async def test_vac_and_etc_calculated_from_eac(
    db: AsyncSession, actor_id: UUID
) -> None:
    """VAC = BAC - EAC, ETC = EAC - AC should be calculated correctly."""
    hierarchy = await _setup_wp_with_data(
        db,
        actor_id,
        budget=Decimal("100000"),
        eac=Decimal("120000"),  # over budget
        progress_pct=Decimal("50.00"),
        cost_amounts=[Decimal("60000")],
    )
    wp = hierarchy["wp"]
    service = EVMService(db)

    metrics = await service.calculate_evm_metrics(
        work_package_id=wp.work_package_id,
        control_date=datetime.now(UTC),
    )

    # VAC = BAC - EAC = 100000 - 120000 = -20000
    assert metrics.vac == pytest.approx(-20000, abs=1)

    # ETC = EAC - AC = 120000 - 60000 = 60000
    assert metrics.etc == pytest.approx(60000, abs=1)


@pytest.mark.asyncio
async def test_vac_and_etc_none_without_forecast(
    db: AsyncSession, actor_id: UUID
) -> None:
    """Without a forecast (EAC), VAC and ETC should be None."""
    hierarchy = await _setup_wp_with_data(
        db,
        actor_id,
        budget=Decimal("50000"),
        progress_pct=Decimal("25.00"),
    )
    wp = hierarchy["wp"]
    service = EVMService(db)

    metrics = await service.calculate_evm_metrics(
        work_package_id=wp.work_package_id,
        control_date=datetime.now(UTC),
    )

    assert metrics.eac is None
    assert metrics.vac is None
    assert metrics.etc is None


# ---------------------------------------------------------------------------
# Aggregate metrics (batch)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_aggregate_evm_metrics_sums_amounts() -> None:
    """aggregate_evm_metrics should sum BAC, PV, AC, EV across multiple metrics."""
    from app.models.schemas.evm import EVMMetricsResponse

    service = EVMService.__new__(EVMService)

    metrics = [
        EVMMetricsResponse(
            entity_type=EntityType.WORK_PACKAGE,
            entity_id=uuid4(),
            bac=100000,
            pv=50000,
            ac=30000,
            ev=40000,
            cv=10000,
            sv=-10000,
            cpi=1.33,
            spi=0.8,
            eac=80000,
            vac=20000,
            etc=50000,
            control_date=datetime.now(UTC),
            branch="main",
            branch_mode=BranchMode.MERGED,
        ),
        EVMMetricsResponse(
            entity_type=EntityType.WORK_PACKAGE,
            entity_id=uuid4(),
            bac=200000,
            pv=100000,
            ac=80000,
            ev=60000,
            cv=-20000,
            sv=-40000,
            cpi=0.75,
            spi=0.6,
            eac=250000,
            vac=-50000,
            etc=170000,
            control_date=datetime.now(UTC),
            branch="main",
            branch_mode=BranchMode.MERGED,
        ),
    ]

    aggregated = service.aggregate_evm_metrics(metrics)

    assert aggregated.bac == 300000
    assert aggregated.pv == 150000
    assert aggregated.ac == 110000
    assert aggregated.ev == 100000

    # CV = EV - AC = 100000 - 110000 = -10000
    assert aggregated.cv == -10000

    # SV = EV - PV = 100000 - 150000 = -50000
    assert aggregated.sv == -50000

    # CPI = EV / AC = 100000 / 110000
    assert aggregated.cpi == pytest.approx(100000 / 110000, abs=0.01)

    # EAC sum = 80000 + 250000 = 330000
    assert aggregated.eac == 330000


@pytest.mark.asyncio
async def test_aggregate_evm_metrics_raises_on_empty() -> None:
    """aggregate_evm_metrics should raise ValueError for an empty list."""
    service = EVMService.__new__(EVMService)

    with pytest.raises(ValueError, match="Cannot aggregate empty"):
        service.aggregate_evm_metrics([])


@pytest.mark.asyncio
async def test_aggregate_evm_metrics_mixed_none_forecasts() -> None:
    """When some metrics have EAC and some don't, aggregated EAC should be None."""
    from app.models.schemas.evm import EVMMetricsResponse

    service = EVMService.__new__(EVMService)

    metrics = [
        EVMMetricsResponse(
            entity_type=EntityType.WORK_PACKAGE,
            entity_id=uuid4(),
            bac=100000,
            pv=50000,
            ac=30000,
            ev=40000,
            cv=10000,
            sv=-10000,
            cpi=1.33,
            spi=0.8,
            eac=80000,
            vac=20000,
            etc=50000,
            control_date=datetime.now(UTC),
            branch="main",
            branch_mode=BranchMode.MERGED,
        ),
        EVMMetricsResponse(
            entity_type=EntityType.WORK_PACKAGE,
            entity_id=uuid4(),
            bac=200000,
            pv=100000,
            ac=80000,
            ev=60000,
            cv=-20000,
            sv=-40000,
            cpi=0.75,
            spi=0.6,
            eac=None,
            vac=None,
            etc=None,
            control_date=datetime.now(UTC),
            branch="main",
            branch_mode=BranchMode.MERGED,
        ),
    ]

    aggregated = service.aggregate_evm_metrics(metrics)

    # Mixed EAC presence => None
    assert aggregated.eac is None
    assert aggregated.vac is None
    assert aggregated.etc is None

    # BAC still summed
    assert aggregated.bac == 300000


# ---------------------------------------------------------------------------
# Batch metrics at entity levels
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_calculate_evm_metrics_batch_at_wp_level(
    db: AsyncSession, actor_id: UUID
) -> None:
    """calculate_evm_metrics_batch should compute metrics for work packages."""
    hierarchy = await _setup_wp_with_data(
        db,
        actor_id,
        budget=Decimal("80000"),
        progress_pct=Decimal("50.00"),
        cost_amounts=[Decimal("30000")],
    )
    wp = hierarchy["wp"]
    service = EVMService(db)

    result = await service.calculate_evm_metrics_batch(
        entity_type=EntityType.WORK_PACKAGE,
        entity_ids=[wp.work_package_id],
        control_date=datetime.now(UTC),
    )

    assert result.bac == pytest.approx(80000, abs=1)
    assert result.ev == pytest.approx(40000, abs=1)
    assert result.ac == pytest.approx(30000, abs=1)


@pytest.mark.asyncio
async def test_calculate_evm_metrics_batch_at_ca_level(
    db: AsyncSession, actor_id: UUID
) -> None:
    """calculate_evm_metrics_batch should aggregate metrics for control accounts."""
    hierarchy = await _setup_wp_with_data(
        db,
        actor_id,
        budget=Decimal("60000"),
        progress_pct=Decimal("40.00"),
        cost_amounts=[Decimal("15000")],
    )
    ca = hierarchy["ca"]
    service = EVMService(db)

    result = await service.calculate_evm_metrics_batch(
        entity_type=EntityType.CONTROL_ACCOUNT,
        entity_ids=[ca.control_account_id],
        control_date=datetime.now(UTC),
    )

    assert result.entity_type == EntityType.CONTROL_ACCOUNT
    assert result.bac == pytest.approx(60000, abs=1)
    assert result.ev == pytest.approx(24000, abs=1)


@pytest.mark.asyncio
async def test_calculate_evm_metrics_batch_at_wbs_level(
    db: AsyncSession, actor_id: UUID
) -> None:
    """calculate_evm_metrics_batch should aggregate metrics for WBS elements."""
    hierarchy = await _setup_wp_with_data(
        db,
        actor_id,
        budget=Decimal("70000"),
        progress_pct=Decimal("30.00"),
    )
    wbs = hierarchy["wbs"]
    service = EVMService(db)

    result = await service.calculate_evm_metrics_batch(
        entity_type=EntityType.WBS_ELEMENT,
        entity_ids=[wbs.wbs_element_id],
        control_date=datetime.now(UTC),
    )

    assert result.entity_type == EntityType.WBS_ELEMENT
    assert result.bac == pytest.approx(70000, abs=1)


@pytest.mark.asyncio
async def test_calculate_evm_metrics_batch_at_project_level(
    db: AsyncSession, actor_id: UUID
) -> None:
    """calculate_evm_metrics_batch should aggregate metrics for projects."""
    hierarchy = await _setup_wp_with_data(
        db,
        actor_id,
        budget=Decimal("90000"),
        progress_pct=Decimal("60.00"),
        cost_amounts=[Decimal("20000")],
    )
    project = hierarchy["project"]
    service = EVMService(db)

    result = await service.calculate_evm_metrics_batch(
        entity_type=EntityType.PROJECT,
        entity_ids=[project.project_id],
        control_date=datetime.now(UTC),
    )

    assert result.entity_type == EntityType.PROJECT
    assert result.bac == pytest.approx(90000, abs=1)
    assert result.ev == pytest.approx(54000, abs=1)
    assert result.ac == pytest.approx(20000, abs=1)


@pytest.mark.asyncio
async def test_calculate_evm_metrics_batch_empty_entity_ids(
    db: AsyncSession, actor_id: UUID
) -> None:
    """calculate_evm_metrics_batch with empty entity_ids should return zero metrics."""
    service = EVMService(db)

    result = await service.calculate_evm_metrics_batch(
        entity_type=EntityType.WORK_PACKAGE,
        entity_ids=[],
        control_date=datetime.now(UTC),
    )

    assert result.bac == 0
    assert result.warning is not None


# ---------------------------------------------------------------------------
# Variance and index calculations (pure methods)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_calculate_variances() -> None:
    """_calculate_variances should compute CV = EV - AC, SV = EV - PV."""
    service = EVMService.__new__(EVMService)

    cv, sv = service._calculate_variances(
        ev=Decimal("50000"), ac=Decimal("60000"), pv=Decimal("55000")
    )

    assert cv == Decimal("-10000")  # over budget
    assert sv == Decimal("-5000")  # behind schedule


@pytest.mark.asyncio
async def test_calculate_indices_zero_division() -> None:
    """_calculate_indices should return None for zero denominators."""
    service = EVMService.__new__(EVMService)

    cpi, spi = service._calculate_indices(
        ev=Decimal("50000"), ac=Decimal("0"), pv=Decimal("0")
    )

    assert cpi is None
    assert spi is None


# ---------------------------------------------------------------------------
# Time-series
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_evm_timeseries_work_package(
    db: AsyncSession, actor_id: UUID
) -> None:
    """get_evm_timeseries should return data points for a work package."""
    hierarchy = await _setup_wp_with_data(
        db,
        actor_id,
        budget=Decimal("100000"),
        progress_pct=Decimal("50.00"),
        cost_amounts=[Decimal("25000")],
    )
    wp = hierarchy["wp"]
    service = EVMService(db)

    ts = await service.get_evm_timeseries(
        entity_type=EntityType.WORK_PACKAGE,
        entity_id=wp.work_package_id,
        granularity=EVMTimeSeriesGranularity.WEEK,
        control_date=datetime.now(UTC),
    )

    assert ts.total_points > 0
    assert ts.start_date <= ts.end_date
    # Each point should have non-negative PV, EV, AC
    for point in ts.points:
        assert point.pv >= 0
        assert point.ev >= 0
        assert point.ac >= 0


@pytest.mark.asyncio
async def test_get_evm_timeseries_raises_for_missing_wp(
    db: AsyncSession, actor_id: UUID
) -> None:
    """get_evm_timeseries should raise ValueError for nonexistent work package."""
    service = EVMService(db)

    with pytest.raises(ValueError, match="not found"):
        await service.get_evm_timeseries(
            entity_type=EntityType.WORK_PACKAGE,
            entity_id=uuid4(),
            granularity=EVMTimeSeriesGranularity.MONTH,
            control_date=datetime.now(UTC),
        )


@pytest.mark.asyncio
async def test_generate_date_intervals_granularities() -> None:
    """_generate_date_intervals should produce correct number of dates for each granularity."""
    service = EVMService.__new__(EVMService)

    start = datetime(2026, 1, 1, tzinfo=UTC)
    end = datetime(2026, 2, 1, tzinfo=UTC)

    daily = service._generate_date_intervals(start, end, EVMTimeSeriesGranularity.DAY)
    assert len(daily) == 32  # Jan 1 to Feb 1 inclusive

    weekly = service._generate_date_intervals(start, end, EVMTimeSeriesGranularity.WEEK)
    assert len(weekly) >= 5  # ~4.3 weeks + end_date

    monthly = service._generate_date_intervals(
        start, end, EVMTimeSeriesGranularity.MONTH
    )
    assert len(monthly) >= 2  # Jan 1 + Feb 1
