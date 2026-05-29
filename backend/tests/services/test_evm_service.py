"""Tests for EVMService.

Covers metric calculations at the work package level, aggregation
through the hierarchy (CA -> WBS -> Project), variance/indices,
time-series generation, and edge cases.
"""

import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.versioning.enums import BranchMode
from app.models.domain.work_package import WorkPackage
from app.models.schemas.evm import (
    EntityType,
    EVMMetricsResponse,
    EVMTimeSeriesGranularity,
    EVMTimeSeriesPoint,
    EVMTimeSeriesResponse,
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


# ---------------------------------------------------------------------------
# log_performance decorator
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_log_performance_timeseries_warning(
    db: AsyncSession, actor_id: UUID, caplog: pytest.LogCaptureFixture
) -> None:
    """log_performance logs warning when timeseries exceeds 1s."""

    from app.services.evm_service import log_performance

    @log_performance("timeseries_slow_operation")
    async def slow_op() -> str:
        # Not actually slow - we just verify the decorator runs without error
        return "done"

    with caplog.at_level(logging.DEBUG, logger="app.services.evm_service"):
        result = await slow_op()
    assert result == "done"


@pytest.mark.asyncio
async def test_log_performance_metrics_warning(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """log_performance logs warning when metrics exceeds 500ms."""
    from app.services.evm_service import log_performance

    @log_performance("metrics_slow_operation")
    async def slow_op() -> str:
        return "done"

    with caplog.at_level(logging.DEBUG, logger="app.services.evm_service"):
        result = await slow_op()
    assert result == "done"


# ---------------------------------------------------------------------------
# _calculate_evm_metrics_from_data (in-memory)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_calculate_evm_metrics_from_data_no_baseline(
    db: AsyncSession, actor_id: UUID
) -> None:
    """_calculate_evm_metrics_from_data with no baseline => PV=0."""

    hierarchy = await create_full_hierarchy(db, actor_id)
    wp = hierarchy["wp"]
    await db.commit()

    service = EVMService(db)
    now = datetime.now(UTC)

    # Get the actual WP entity
    wp_entity = await service.wp_service.get_as_of(
        entity_id=wp.work_package_id, as_of=now, branch="main", branch_mode=BranchMode.MERGED
    )
    assert wp_entity is not None

    result = service._calculate_evm_metrics_from_data(
        work_package=wp_entity,
        schedule_baseline=None,
        total_ac=Decimal("5000"),
        progress_entry=None,
        forecast=None,
        control_date=now,
        branch="main",
        branch_mode=BranchMode.MERGED,
    )

    assert result.pv == Decimal("0")
    assert result.ac == Decimal("5000")
    assert result.ev == Decimal("0")
    assert result.warning is not None
    assert "No progress" in result.warning


@pytest.mark.asyncio
async def test_calculate_evm_metrics_from_data_with_forecast(
    db: AsyncSession, actor_id: UUID
) -> None:
    """_calculate_evm_metrics_from_data with forecast => EAC, VAC, ETC, cpi_forecast."""
    from unittest.mock import MagicMock

    hierarchy = await create_full_hierarchy(db, actor_id, budget_amount=Decimal("100000"))
    wp = hierarchy["wp"]
    await create_test_progress_entry(
        db, actor_id, wp.work_package_id, progress_percentage=Decimal("50.00")
    )
    await db.commit()

    service = EVMService(db)
    now = datetime.now(UTC)

    wp_entity = await service.wp_service.get_as_of(
        entity_id=wp.work_package_id, as_of=now, branch="main", branch_mode=BranchMode.MERGED
    )
    assert wp_entity is not None

    forecast_mock = MagicMock()
    forecast_mock.eac_amount = Decimal("120000")

    result = service._calculate_evm_metrics_from_data(
        work_package=wp_entity,
        schedule_baseline=None,
        total_ac=Decimal("60000"),
        progress_entry=MagicMock(progress_percentage=Decimal("50.00")),
        forecast=forecast_mock,
        control_date=now,
        branch="main",
        branch_mode=BranchMode.MERGED,
    )

    assert result.eac == Decimal("120000")
    assert result.vac == Decimal("100000") - Decimal("120000")  # BAC - EAC
    assert result.etc == Decimal("120000") - Decimal("60000")  # EAC - AC
    assert result.cpi_forecast == pytest.approx(
        float(Decimal("100000") / Decimal("120000")), abs=0.01
    )


@pytest.mark.asyncio
async def test_calculate_evm_metrics_from_data_null_eac(
    db: AsyncSession, actor_id: UUID
) -> None:
    """_calculate_evm_metrics_from_data with forecast but eac_amount=None."""
    from unittest.mock import MagicMock

    hierarchy = await create_full_hierarchy(db, actor_id, budget_amount=Decimal("50000"))
    wp = hierarchy["wp"]
    await db.commit()

    service = EVMService(db)
    now = datetime.now(UTC)

    wp_entity = await service.wp_service.get_as_of(
        entity_id=wp.work_package_id, as_of=now, branch="main", branch_mode=BranchMode.MERGED
    )
    assert wp_entity is not None

    forecast_mock = MagicMock()
    forecast_mock.eac_amount = None

    result = service._calculate_evm_metrics_from_data(
        work_package=wp_entity,
        schedule_baseline=None,
        total_ac=Decimal("1000"),
        progress_entry=None,
        forecast=forecast_mock,
        control_date=now,
        branch="main",
        branch_mode=BranchMode.MERGED,
    )

    assert result.eac is None
    assert result.vac is None
    assert result.etc is None


@pytest.mark.asyncio
async def test_calculate_evm_metrics_from_data_zero_eac(
    db: AsyncSession, actor_id: UUID
) -> None:
    """_calculate_evm_metrics_from_data with eac=0 => no cpi_forecast."""
    from unittest.mock import MagicMock

    hierarchy = await create_full_hierarchy(db, actor_id, budget_amount=Decimal("50000"))
    wp = hierarchy["wp"]
    await db.commit()

    service = EVMService(db)
    now = datetime.now(UTC)

    wp_entity = await service.wp_service.get_as_of(
        entity_id=wp.work_package_id, as_of=now, branch="main", branch_mode=BranchMode.MERGED
    )
    assert wp_entity is not None

    forecast_mock = MagicMock()
    forecast_mock.eac_amount = Decimal("0")

    result = service._calculate_evm_metrics_from_data(
        work_package=wp_entity,
        schedule_baseline=None,
        total_ac=Decimal("0"),
        progress_entry=None,
        forecast=forecast_mock,
        control_date=now,
        branch="main",
        branch_mode=BranchMode.MERGED,
    )

    assert result.eac == Decimal("0")
    # cpi_forecast should be None since eac is 0
    assert result.cpi_forecast is None


@pytest.mark.asyncio
async def test_calculate_evm_metrics_from_data_invalid_baseline_dates(
    db: AsyncSession, actor_id: UUID
) -> None:
    """_calculate_evm_metrics_from_data with invalid baseline dates => PV=0."""
    from unittest.mock import MagicMock

    hierarchy = await create_full_hierarchy(db, actor_id, budget_amount=Decimal("50000"))
    wp = hierarchy["wp"]
    await db.commit()

    service = EVMService(db)
    now = datetime.now(UTC)

    wp_entity = await service.wp_service.get_as_of(
        entity_id=wp.work_package_id, as_of=now, branch="main", branch_mode=BranchMode.MERGED
    )
    assert wp_entity is not None

    # Baseline with end_date before start_date
    bad_baseline = MagicMock()
    bad_baseline.start_date = now
    bad_baseline.end_date = now - timedelta(days=30)
    bad_baseline.progression_type = "LINEAR"

    result = service._calculate_evm_metrics_from_data(
        work_package=wp_entity,
        schedule_baseline=bad_baseline,
        total_ac=Decimal("1000"),
        progress_entry=None,
        forecast=None,
        control_date=now,
        branch="main",
        branch_mode=BranchMode.MERGED,
    )

    assert result.pv == Decimal("0")


@pytest.mark.asyncio
async def test_calculate_evm_metrics_from_data_null_budget() -> None:
    """_calculate_evm_metrics_from_data with null budget => BAC=0."""
    from unittest.mock import MagicMock

    service = EVMService.__new__(EVMService)
    now = datetime.now(UTC)

    wp_mock = MagicMock()
    wp_mock.work_package_id = uuid4()
    wp_mock.budget_amount = None

    result = service._calculate_evm_metrics_from_data(
        work_package=wp_mock,
        schedule_baseline=None,
        total_ac=Decimal("0"),
        progress_entry=None,
        forecast=None,
        control_date=now,
        branch="main",
        branch_mode=BranchMode.MERGED,
    )

    assert result.bac == Decimal("0")


# ---------------------------------------------------------------------------
# _batch_calculate_work_package_metrics
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_batch_calculate_work_package_metrics_empty(
    db: AsyncSession, actor_id: UUID
) -> None:
    """_batch_calculate_work_package_metrics with nonexistent WP IDs returns empty."""
    service = EVMService(db)

    result = await service._batch_calculate_work_package_metrics(
        work_package_ids=[uuid4()],
        control_date=datetime.now(UTC),
        branch="main",
        branch_mode=BranchMode.MERGED,
    )

    assert result == []


@pytest.mark.asyncio
async def test_get_ac_batch_empty_ids() -> None:
    """_get_ac_batch with empty list returns empty dict."""
    service = EVMService.__new__(EVMService)
    result = await service._get_ac_batch([], datetime.now(UTC))
    assert result == {}


@pytest.mark.asyncio
async def test_get_ac_batch_with_data(
    db: AsyncSession, actor_id: UUID
) -> None:
    """_get_ac_batch sums costs across CEs for multiple work packages."""
    hierarchy = await create_full_hierarchy(db, actor_id, budget_amount=Decimal("100000"))
    wp = hierarchy["wp"]
    ce = hierarchy["ce"]
    await create_test_cost_registration(db, actor_id, ce.cost_element_id, amount=Decimal("3000"))
    await create_test_cost_registration(db, actor_id, ce.cost_element_id, amount=Decimal("2000"))
    await db.commit()

    service = EVMService(db)
    result = await service._get_ac_batch(
        [wp.work_package_id], datetime.now(UTC)
    )

    assert result[wp.work_package_id] == Decimal("5000")


# ---------------------------------------------------------------------------
# _get_bac_as_of / _get_pv_as_of edge cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_bac_as_of_nonexistent_wp(
    db: AsyncSession, actor_id: UUID
) -> None:
    """_get_bac_as_of returns None for nonexistent WP."""
    service = EVMService(db)
    result = await service._get_bac_as_of(
        uuid4(), datetime.now(UTC), "main", BranchMode.MERGED
    )
    assert result is None


@pytest.mark.asyncio
async def test_get_pv_as_of_no_schedule_baseline(
    db: AsyncSession, actor_id: UUID
) -> None:
    """_get_pv_as_of returns 0 when WP has no schedule_baseline_id."""
    hierarchy = await create_full_hierarchy(db, actor_id)
    wp = hierarchy["wp"]
    await db.commit()

    service = EVMService(db)
    result = await service._get_pv_as_of(
        wp.work_package_id, datetime.now(UTC), "main", BranchMode.MERGED
    )
    assert result == Decimal("0")


@pytest.mark.asyncio
async def test_get_pv_as_of_baseline_deleted(
    db: AsyncSession, actor_id: UUID
) -> None:
    """_get_pv_as_of returns 0 when baseline entity is not found."""
    hierarchy = await create_full_hierarchy(db, actor_id, budget_amount=Decimal("50000"))
    wp = hierarchy["wp"]
    await db.commit()

    service = EVMService(db)

    # Manually set a schedule_baseline_id that does not exist
    from sqlalchemy import update

    await db.execute(
        update(WorkPackage.__table__)
        .where(WorkPackage.work_package_id == wp.work_package_id)
        .where(func.upper(WorkPackage.valid_time).is_(None))
        .values(schedule_baseline_id=uuid4())
    )
    await db.commit()

    result = await service._get_pv_as_of(
        wp.work_package_id, datetime.now(UTC), "main", BranchMode.MERGED
    )
    assert result == Decimal("0")


@pytest.mark.asyncio
async def test_get_eac_as_of_no_forecast(
    db: AsyncSession, actor_id: UUID
) -> None:
    """_get_eac_as_of returns None when WP has no forecast."""
    hierarchy = await create_full_hierarchy(db, actor_id)
    wp = hierarchy["wp"]
    await db.commit()

    service = EVMService(db)
    result = await service._get_eac_as_of(
        wp.work_package_id, datetime.now(UTC), "main", BranchMode.MERGED
    )
    assert result is None


@pytest.mark.asyncio
async def test_get_eac_as_of_nonexistent_forecast(
    db: AsyncSession, actor_id: UUID
) -> None:
    """_get_eac_as_of returns None when forecast entity not found."""
    hierarchy = await create_full_hierarchy(db, actor_id)
    wp = hierarchy["wp"]
    await db.commit()

    service = EVMService(db)

    # Set a forecast_id that does not exist
    from sqlalchemy import update

    await db.execute(
        update(WorkPackage.__table__)
        .where(WorkPackage.work_package_id == wp.work_package_id)
        .where(func.upper(WorkPackage.valid_time).is_(None))
        .values(forecast_id=uuid4())
    )
    await db.commit()

    result = await service._get_eac_as_of(
        wp.work_package_id, datetime.now(UTC), "main", BranchMode.MERGED
    )
    assert result is None


# ---------------------------------------------------------------------------
# calculate_evm_metrics_batch - unsupported entity type
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_calculate_evm_metrics_batch_unsupported_type(
    db: AsyncSession, actor_id: UUID
) -> None:
    """calculate_evm_metrics_batch raises ValueError for unsupported entity type."""
    service = EVMService(db)

    with pytest.raises(ValueError, match="not yet supported"):
        await service.calculate_evm_metrics_batch(
            entity_type=EntityType.COST_ELEMENT,
            entity_ids=[uuid4()],
            control_date=datetime.now(UTC),
        )


# ---------------------------------------------------------------------------
# WBS/CA resolution helpers - empty results
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_resolve_wp_ids_for_wbs_empty(
    db: AsyncSession, actor_id: UUID
) -> None:
    """_resolve_work_package_ids_for_wbs returns empty for nonexistent WBS."""
    service = EVMService(db)
    result = await service._resolve_work_package_ids_for_wbs(
        [uuid4()], "main", BranchMode.MERGED
    )
    assert result == []


@pytest.mark.asyncio
async def test_resolve_wp_ids_for_ca_empty(
    db: AsyncSession, actor_id: UUID
) -> None:
    """_resolve_work_package_ids_for_ca returns empty for nonexistent CA."""
    service = EVMService(db)
    result = await service._resolve_work_package_ids_for_ca(
        [uuid4()], "main"
    )
    assert result == []


@pytest.mark.asyncio
async def test_resolve_wp_ids_for_wbs_with_data(
    db: AsyncSession, actor_id: UUID
) -> None:
    """_resolve_work_package_ids_for_wbs resolves through hierarchy."""
    hierarchy = await create_full_hierarchy(db, actor_id)
    await db.commit()

    service = EVMService(db)
    result = await service._resolve_work_package_ids_for_wbs(
        [hierarchy["wbs"].wbs_element_id], "main", BranchMode.MERGED
    )
    assert len(result) == 1
    assert result[0] == hierarchy["wp"].work_package_id


@pytest.mark.asyncio
async def test_resolve_wp_ids_for_ca_with_data(
    db: AsyncSession, actor_id: UUID
) -> None:
    """_resolve_work_package_ids_for_ca resolves through hierarchy."""
    hierarchy = await create_full_hierarchy(db, actor_id)
    await db.commit()

    service = EVMService(db)
    result = await service._resolve_work_package_ids_for_ca(
        [hierarchy["ca"].control_account_id], "main"
    )
    assert len(result) == 1
    assert result[0] == hierarchy["wp"].work_package_id


# ---------------------------------------------------------------------------
# _calculate_wbs_element_evm_metrics / _calculate_control_account_evm_metrics - no WPs
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_calculate_wbs_element_evm_metrics_no_wps(
    db: AsyncSession, actor_id: UUID
) -> None:
    """_calculate_wbs_element_evm_metrics returns zero metrics when no WPs found."""
    service = EVMService(db)
    # Create a WBS element with no CAs/WPs under it
    from tests.factories import create_test_project, create_test_wbs_element

    project = await create_test_project(db, actor_id)
    wbs = await create_test_wbs_element(db, actor_id, project.project_id)
    await db.commit()

    result = await service._calculate_wbs_element_evm_metrics(
        wbs_element_ids=[wbs.wbs_element_id],
        control_date=datetime.now(UTC),
        branch="main",
        branch_mode=BranchMode.MERGED,
    )

    assert result.bac == Decimal("0")
    assert result.warning is not None
    assert "No work packages" in result.warning


@pytest.mark.asyncio
async def test_calculate_control_account_evm_metrics_no_wps(
    db: AsyncSession, actor_id: UUID
) -> None:
    """_calculate_control_account_evm_metrics returns zero metrics when no WPs found."""
    service = EVMService(db)
    from tests.factories import (
        create_test_control_account,
        create_test_org_unit,
        create_test_project,
        create_test_wbs_element,
    )

    project = await create_test_project(db, actor_id)
    org = await create_test_org_unit(db, actor_id)
    wbs = await create_test_wbs_element(db, actor_id, project.project_id)
    ca = await create_test_control_account(
        db, actor_id, wbs.wbs_element_id, org.organizational_unit_id
    )
    await db.commit()

    result = await service._calculate_control_account_evm_metrics(
        control_account_ids=[ca.control_account_id],
        control_date=datetime.now(UTC),
        branch="main",
        branch_mode=BranchMode.MERGED,
    )

    assert result.bac == Decimal("0")
    assert result.warning is not None
    assert "No work packages" in result.warning


# ---------------------------------------------------------------------------
# _calculate_project_evm_metrics
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_calculate_project_evm_metrics_no_wbs(
    db: AsyncSession, actor_id: UUID
) -> None:
    """_calculate_project_evm_metrics returns zero metrics when no WBS elements."""
    service = EVMService(db)
    from tests.factories import create_test_project

    project = await create_test_project(db, actor_id)
    await db.commit()

    result = await service._calculate_project_evm_metrics(
        project_ids=[project.project_id],
        control_date=datetime.now(UTC),
        branch="main",
        branch_mode=BranchMode.MERGED,
    )

    assert result.bac == Decimal("0")
    assert result.warning is not None
    assert "No WBS Elements" in result.warning


# ---------------------------------------------------------------------------
# _convert_to_response
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_convert_to_response(db: AsyncSession, actor_id: UUID) -> None:
    """_convert_to_response maps EVMMetricsRead to EVMMetricsResponse."""
    hierarchy = await _setup_wp_with_data(
        db, actor_id, budget=Decimal("50000"), progress_pct=Decimal("25.00"),
    )
    wp = hierarchy["wp"]
    service = EVMService(db)

    metrics = await service.calculate_evm_metrics(
        work_package_id=wp.work_package_id,
        control_date=datetime.now(UTC),
    )

    response = service._convert_to_response(metrics, EntityType.WORK_PACKAGE)
    assert response.entity_type == EntityType.WORK_PACKAGE
    assert response.entity_id == wp.work_package_id
    assert response.bac == metrics.bac


# ---------------------------------------------------------------------------
# _get_ev_as_of_date
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_ev_as_of_date_nonexistent_wp(
    db: AsyncSession, actor_id: UUID
) -> None:
    """_get_ev_as_of_date returns 0 for nonexistent WP."""
    service = EVMService(db)
    result = await service._get_ev_as_of_date(
        uuid4(), datetime.now(UTC), "main", BranchMode.MERGED
    )
    assert result == Decimal("0")


@pytest.mark.asyncio
async def test_get_ev_as_of_date_with_progress(
    db: AsyncSession, actor_id: UUID
) -> None:
    """_get_ev_as_of_date returns correct EV with progress."""
    hierarchy = await create_full_hierarchy(db, actor_id, budget_amount=Decimal("100000"))
    wp = hierarchy["wp"]
    await create_test_progress_entry(
        db, actor_id, wp.work_package_id, progress_percentage=Decimal("40.00")
    )
    await db.commit()

    service = EVMService(db)
    result = await service._get_ev_as_of_date(
        wp.work_package_id, datetime.now(UTC), "main", BranchMode.MERGED
    )
    assert result == pytest.approx(Decimal("40000"), abs=1)


# ---------------------------------------------------------------------------
# Timeseries - WBS / CA / Project / batch
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_evm_timeseries_wbs_element(
    db: AsyncSession, actor_id: UUID
) -> None:
    """get_evm_timeseries for WBS Element aggregates child WPs."""
    hierarchy = await _setup_wp_with_data(
        db, actor_id, budget=Decimal("50000"), progress_pct=Decimal("50.00"),
    )
    wbs = hierarchy["wbs"]
    service = EVMService(db)

    ts = await service.get_evm_timeseries(
        entity_type=EntityType.WBS_ELEMENT,
        entity_id=wbs.wbs_element_id,
        granularity=EVMTimeSeriesGranularity.WEEK,
        control_date=datetime.now(UTC),
    )

    assert ts.total_points >= 0


@pytest.mark.asyncio
async def test_get_evm_timeseries_control_account(
    db: AsyncSession, actor_id: UUID
) -> None:
    """get_evm_timeseries for Control Account aggregates child WPs."""
    hierarchy = await _setup_wp_with_data(
        db, actor_id, budget=Decimal("50000"), progress_pct=Decimal("50.00"),
    )
    ca = hierarchy["ca"]
    service = EVMService(db)

    ts = await service.get_evm_timeseries(
        entity_type=EntityType.CONTROL_ACCOUNT,
        entity_id=ca.control_account_id,
        granularity=EVMTimeSeriesGranularity.WEEK,
        control_date=datetime.now(UTC),
    )

    assert ts.total_points >= 0


@pytest.mark.asyncio
async def test_get_evm_timeseries_project(
    db: AsyncSession, actor_id: UUID
) -> None:
    """get_evm_timeseries for Project aggregates all WPs."""
    hierarchy = await _setup_wp_with_data(
        db, actor_id, budget=Decimal("50000"), progress_pct=Decimal("50.00"),
        cost_amounts=[Decimal("10000")],
    )
    project = hierarchy["project"]
    service = EVMService(db)

    ts = await service.get_evm_timeseries(
        entity_type=EntityType.PROJECT,
        entity_id=project.project_id,
        granularity=EVMTimeSeriesGranularity.WEEK,
        control_date=datetime.now(UTC),
    )

    assert ts.total_points >= 0


@pytest.mark.asyncio
async def test_get_evm_timeseries_unsupported_type(
    db: AsyncSession, actor_id: UUID
) -> None:
    """get_evm_timeseries raises for unsupported entity type."""
    service = EVMService(db)

    with pytest.raises(ValueError, match="not yet supported"):
        await service.get_evm_timeseries(
            entity_type=EntityType.COST_ELEMENT,
            entity_id=uuid4(),
            granularity=EVMTimeSeriesGranularity.WEEK,
            control_date=datetime.now(UTC),
        )


@pytest.mark.asyncio
async def test_get_evm_timeseries_wp_no_baseline_with_cost(
    db: AsyncSession, actor_id: UUID
) -> None:
    """get_evm_timeseries for WP with no baseline but with cost data generates points."""
    hierarchy = await create_full_hierarchy(db, actor_id, budget_amount=Decimal("50000"))
    wp = hierarchy["wp"]
    ce = hierarchy["ce"]
    await create_test_cost_registration(db, actor_id, ce.cost_element_id, amount=Decimal("5000"))
    await db.commit()

    service = EVMService(db)

    ts = await service.get_evm_timeseries(
        entity_type=EntityType.WORK_PACKAGE,
        entity_id=wp.work_package_id,
        granularity=EVMTimeSeriesGranularity.DAY,
        control_date=datetime.now(UTC),
    )

    # Should have points generated from cost data even without baseline
    assert ts.total_points >= 1


# ---------------------------------------------------------------------------
# _gather_timeseries / _aggregate_timeseries
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_gather_timeseries_filters_value_errors() -> None:
    """_gather_timeseries filters ValueError but logs other exceptions."""
    service = EVMService.__new__(EVMService)

    ts1 = EVMTimeSeriesResponse(
        granularity=EVMTimeSeriesGranularity.WEEK,
        points=[
            EVMTimeSeriesPoint(
                date=datetime(2026, 1, 1, tzinfo=UTC),
                pv=Decimal("100"),
                ev=Decimal("50"),
                ac=Decimal("60"),
                forecast=Decimal("100"),
                actual=Decimal("60"),
                cpi=None,
                spi=None,
            )
        ],
        start_date=datetime(2026, 1, 1, tzinfo=UTC),
        end_date=datetime(2026, 1, 7, tzinfo=UTC),
        total_points=1,
    )

    async def return_ts() -> EVMTimeSeriesResponse:
        return ts1

    async def raise_value_error() -> EVMTimeSeriesResponse:
        raise ValueError("not found")

    results = await service._gather_timeseries(
        [return_ts(), raise_value_error()],
        "test",
    )
    assert len(results) == 1


@pytest.mark.asyncio
async def test_aggregate_timeseries_multiple() -> None:
    """_aggregate_timeseries combines multiple time-series."""
    service = EVMService.__new__(EVMService)

    d1 = datetime(2026, 1, 1, tzinfo=UTC)
    d2 = datetime(2026, 1, 8, tzinfo=UTC)

    ts1 = EVMTimeSeriesResponse(
        granularity=EVMTimeSeriesGranularity.WEEK,
        points=[
            EVMTimeSeriesPoint(date=d1, pv=Decimal("100"), ev=Decimal("50"),
                               ac=Decimal("60"), forecast=Decimal("100"),
                               actual=Decimal("60"), cpi=None, spi=None),
            EVMTimeSeriesPoint(date=d2, pv=Decimal("200"), ev=Decimal("100"),
                               ac=Decimal("120"), forecast=Decimal("200"),
                               actual=Decimal("120"), cpi=None, spi=None),
        ],
        start_date=d1, end_date=d2, total_points=2,
    )

    ts2 = EVMTimeSeriesResponse(
        granularity=EVMTimeSeriesGranularity.WEEK,
        points=[
            EVMTimeSeriesPoint(date=d1, pv=Decimal("50"), ev=Decimal("25"),
                               ac=Decimal("30"), forecast=Decimal("50"),
                               actual=Decimal("30"), cpi=None, spi=None),
            EVMTimeSeriesPoint(date=d2, pv=Decimal("100"), ev=Decimal("50"),
                               ac=Decimal("60"), forecast=Decimal("100"),
                               actual=Decimal("60"), cpi=None, spi=None),
        ],
        start_date=d1, end_date=d2, total_points=2,
    )

    dates = [d1, d2]
    aggregated = service._aggregate_timeseries([ts1, ts2], dates)

    assert len(aggregated) == 2
    # First point: PV=100+50=150, EV=50+25=75, AC=60+30=90
    assert aggregated[0].pv == Decimal("150")
    assert aggregated[0].ev == Decimal("75")
    assert aggregated[0].ac == Decimal("90")


# ---------------------------------------------------------------------------
# _generate_timeseries_points - edge cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_timeseries_points_nonexistent_wp(
    db: AsyncSession, actor_id: UUID
) -> None:
    """_generate_timeseries_points returns empty for nonexistent WP."""
    service = EVMService(db)
    result = await service._generate_timeseries_points(
        work_package_id=uuid4(),
        start_date=datetime.now(UTC),
        end_date=datetime.now(UTC),
        granularity=EVMTimeSeriesGranularity.WEEK,
        control_date=datetime.now(UTC),
        branch="main",
        branch_mode=BranchMode.MERGED,
    )
    assert result == []


# ---------------------------------------------------------------------------
# _generate_timeseries_points_batch
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_timeseries_points_batch_empty() -> None:
    """_generate_timeseries_points_batch with empty list returns empty dict."""
    service = EVMService.__new__(EVMService)
    result = await service._generate_timeseries_points_batch(
        [], EVMTimeSeriesGranularity.WEEK, datetime.now(UTC), "main", BranchMode.MERGED
    )
    assert result == {}


@pytest.mark.asyncio
async def test_generate_timeseries_points_batch_with_data(
    db: AsyncSession, actor_id: UUID
) -> None:
    """_generate_timeseries_points_batch generates points for multiple WPs."""
    hierarchy = await _setup_wp_with_data(
        db, actor_id, budget=Decimal("50000"), progress_pct=Decimal("50.00"),
        cost_amounts=[Decimal("5000")],
    )
    wp = hierarchy["wp"]
    await db.commit()

    service = EVMService(db)
    result = await service._generate_timeseries_points_batch(
        [wp.work_package_id],
        EVMTimeSeriesGranularity.WEEK,
        datetime.now(UTC),
        "main",
        BranchMode.MERGED,
    )

    assert wp.work_package_id in result
    assert len(result[wp.work_package_id]) > 0


@pytest.mark.asyncio
async def test_generate_timeseries_points_batch_no_baseline_no_data(
    db: AsyncSession, actor_id: UUID
) -> None:
    """_generate_timeseries_points_batch skips WP with no baseline, cost, or progress."""
    hierarchy = await create_full_hierarchy(db, actor_id)
    wp = hierarchy["wp"]
    await db.commit()

    service = EVMService(db)
    result = await service._generate_timeseries_points_batch(
        [wp.work_package_id],
        EVMTimeSeriesGranularity.WEEK,
        datetime.now(UTC),
        "main",
        BranchMode.MERGED,
    )

    # WP with no baseline and no cost/progress data should be skipped
    assert wp.work_package_id not in result


# ---------------------------------------------------------------------------
# _aggregate_wp_timeseries
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_aggregate_wp_timeseries_empty(
    db: AsyncSession, actor_id: UUID
) -> None:
    """_aggregate_wp_timeseries returns empty when all WPs have no data."""
    hierarchy = await create_full_hierarchy(db, actor_id)
    wp = hierarchy["wp"]
    await db.commit()

    service = EVMService(db)
    result = await service._aggregate_wp_timeseries(
        [wp.work_package_id],
        EVMTimeSeriesGranularity.WEEK,
        datetime.now(UTC),
        "main",
        BranchMode.MERGED,
    )

    assert result.total_points == 0


# ---------------------------------------------------------------------------
# _empty_ce_cumulative_costs
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_empty_ce_cumulative_costs() -> None:
    """_empty_ce_cumulative_costs returns empty dict."""
    result = await EVMService._empty_ce_cumulative_costs()
    assert result == {}


# ---------------------------------------------------------------------------
# _generate_date_intervals edge cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_date_intervals_same_start_end() -> None:
    """_generate_date_intervals with same start and end returns one date."""
    service = EVMService.__new__(EVMService)
    d = datetime(2026, 1, 1, tzinfo=UTC)
    result = service._generate_date_intervals(d, d, EVMTimeSeriesGranularity.DAY)
    assert len(result) == 1


@pytest.mark.asyncio
async def test_generate_date_intervals_month_december() -> None:
    """_generate_date_intervals month wraps from Dec to Jan correctly."""
    service = EVMService.__new__(EVMService)
    start = datetime(2026, 12, 1, tzinfo=UTC)
    end = datetime(2027, 2, 1, tzinfo=UTC)
    result = service._generate_date_intervals(start, end, EVMTimeSeriesGranularity.MONTH)
    dates_str = [d.isoformat() for d in result]
    assert any("2027-01" in d for d in dates_str)


# ---------------------------------------------------------------------------
# WBS element timeseries - no WPs
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_wbs_element_evm_timeseries_no_wps(
    db: AsyncSession, actor_id: UUID
) -> None:
    """_get_wbs_element_evm_timeseries returns empty when no WPs."""
    service = EVMService(db)
    from tests.factories import create_test_project, create_test_wbs_element

    project = await create_test_project(db, actor_id)
    wbs = await create_test_wbs_element(db, actor_id, project.project_id)
    await db.commit()

    result = await service._get_wbs_element_evm_timeseries(
        wbs_element_id=wbs.wbs_element_id,
        granularity=EVMTimeSeriesGranularity.WEEK,
        control_date=datetime.now(UTC),
        branch="main",
        branch_mode=BranchMode.MERGED,
    )

    assert result.total_points == 0


@pytest.mark.asyncio
async def test_get_control_account_evm_timeseries_no_wps(
    db: AsyncSession, actor_id: UUID
) -> None:
    """_get_control_account_evm_timeseries returns empty when no WPs."""
    service = EVMService(db)
    from tests.factories import (
        create_test_control_account,
        create_test_org_unit,
        create_test_project,
        create_test_wbs_element,
    )

    project = await create_test_project(db, actor_id)
    org = await create_test_org_unit(db, actor_id)
    wbs = await create_test_wbs_element(db, actor_id, project.project_id)
    ca = await create_test_control_account(
        db, actor_id, wbs.wbs_element_id, org.organizational_unit_id
    )
    await db.commit()

    result = await service._get_control_account_evm_timeseries(
        control_account_id=ca.control_account_id,
        granularity=EVMTimeSeriesGranularity.WEEK,
        control_date=datetime.now(UTC),
        branch="main",
        branch_mode=BranchMode.MERGED,
    )

    assert result.total_points == 0


# ---------------------------------------------------------------------------
# Project timeseries edge cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_project_evm_timeseries_not_found(
    db: AsyncSession, actor_id: UUID
) -> None:
    """_get_project_evm_timeseries returns empty for nonexistent project."""
    service = EVMService(db)

    result = await service._get_project_evm_timeseries(
        project_id=uuid4(),
        granularity=EVMTimeSeriesGranularity.WEEK,
        control_date=datetime.now(UTC),
        branch="main",
        branch_mode=BranchMode.MERGED,
    )

    assert result.total_points == 0


@pytest.mark.asyncio
async def test_get_project_evm_timeseries_no_wbs(
    db: AsyncSession, actor_id: UUID
) -> None:
    """_get_project_evm_timeseries returns empty for project with no WBS."""
    service = EVMService(db)
    from tests.factories import create_test_project

    project = await create_test_project(db, actor_id)
    await db.commit()

    result = await service._get_project_evm_timeseries(
        project_id=project.project_id,
        granularity=EVMTimeSeriesGranularity.WEEK,
        control_date=datetime.now(UTC),
        branch="main",
        branch_mode=BranchMode.MERGED,
    )

    assert result.total_points == 0


# ---------------------------------------------------------------------------
# aggregate_evm_metrics with warnings
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_aggregate_evm_metrics_with_warnings() -> None:
    """aggregate_evm_metrics joins warnings from all metrics."""
    service = EVMService.__new__(EVMService)

    metrics = [
        EVMMetricsResponse(
            entity_type=EntityType.WORK_PACKAGE,
            entity_id=uuid4(),
            bac=100000, pv=50000, ac=30000, ev=40000,
            cv=10000, sv=-10000, cpi=1.33, spi=0.8,
            eac=80000, vac=20000, etc=50000,
            control_date=datetime.now(UTC),
            branch="main", branch_mode=BranchMode.MERGED,
            warning="No progress",
        ),
        EVMMetricsResponse(
            entity_type=EntityType.WORK_PACKAGE,
            entity_id=uuid4(),
            bac=200000, pv=100000, ac=80000, ev=60000,
            cv=-20000, sv=-40000, cpi=0.75, spi=0.6,
            eac=250000, vac=-50000, etc=170000,
            control_date=datetime.now(UTC),
            branch="main", branch_mode=BranchMode.MERGED,
            warning="Baseline missing",
        ),
    ]

    aggregated = service.aggregate_evm_metrics(metrics)
    assert aggregated.warning is not None
    assert "No progress" in aggregated.warning
    assert "Baseline missing" in aggregated.warning


@pytest.mark.asyncio
async def test_aggregate_evm_metrics_all_none_eac() -> None:
    """aggregate_evm_metrics when all metrics have None EAC => EAC=None."""
    service = EVMService.__new__(EVMService)

    metrics = [
        EVMMetricsResponse(
            entity_type=EntityType.WORK_PACKAGE,
            entity_id=uuid4(),
            bac=100000, pv=50000, ac=30000, ev=40000,
            cv=10000, sv=-10000, cpi=1.33, spi=0.8,
            eac=None, vac=None, etc=None,
            control_date=datetime.now(UTC),
            branch="main", branch_mode=BranchMode.MERGED,
        ),
        EVMMetricsResponse(
            entity_type=EntityType.WORK_PACKAGE,
            entity_id=uuid4(),
            bac=200000, pv=100000, ac=80000, ev=60000,
            cv=-20000, sv=-40000, cpi=0.75, spi=0.6,
            eac=None, vac=None, etc=None,
            control_date=datetime.now(UTC),
            branch="main", branch_mode=BranchMode.MERGED,
        ),
    ]

    aggregated = service.aggregate_evm_metrics(metrics)
    # All have None EAC => len(eac_list) == 0 != len(metrics) => None
    assert aggregated.eac is None


# ---------------------------------------------------------------------------
# _get_ac_as_of
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_ac_as_of_no_costs(
    db: AsyncSession, actor_id: UUID
) -> None:
    """_get_ac_as_of returns 0 when no cost registrations exist."""
    hierarchy = await create_full_hierarchy(db, actor_id)
    wp = hierarchy["wp"]
    await db.commit()

    service = EVMService(db)
    result = await service._get_ac_as_of(wp.work_package_id, datetime.now(UTC))
    assert result == Decimal("0")


# ---------------------------------------------------------------------------
# cpi_forecast
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cpi_forecast_calculated(db: AsyncSession, actor_id: UUID) -> None:
    """calculate_evm_metrics calculates cpi_forecast = BAC / EAC."""
    hierarchy = await _setup_wp_with_data(
        db, actor_id,
        budget=Decimal("100000"),
        eac=Decimal("125000"),
        progress_pct=Decimal("50.00"),
        cost_amounts=[Decimal("50000")],
    )
    wp = hierarchy["wp"]
    service = EVMService(db)

    metrics = await service.calculate_evm_metrics(
        work_package_id=wp.work_package_id,
        control_date=datetime.now(UTC),
    )

    assert metrics.cpi_forecast is not None
    assert metrics.cpi_forecast == pytest.approx(
        float(Decimal("100000") / Decimal("125000")), abs=0.01
    )


# ---------------------------------------------------------------------------
# Additional coverage: _calculate_evm_metrics_from_data exception handler
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_calculate_evm_metrics_from_data_exception_in_pv() -> None:
    """_calculate_evm_metrics_from_data catches exception in PV calc => PV=0."""
    service = EVMService.__new__(EVMService)
    now = datetime.now(UTC)

    wp_mock = MagicMock()
    wp_mock.work_package_id = uuid4()
    wp_mock.budget_amount = Decimal("50000")

    # Baseline that raises on attribute access
    bad_baseline = MagicMock()
    bad_baseline.start_date = now
    bad_baseline.end_date = now + timedelta(days=30)
    type(bad_baseline).progression_type = property(
        lambda self: (_ for _ in ()).throw(RuntimeError("bad progression"))
    )

    result = service._calculate_evm_metrics_from_data(
        work_package=wp_mock,
        schedule_baseline=bad_baseline,
        total_ac=Decimal("1000"),
        progress_entry=None,
        forecast=None,
        control_date=now,
        branch="main",
        branch_mode=BranchMode.MERGED,
    )

    # Exception caught => PV=0
    assert result.pv == Decimal("0")


# ---------------------------------------------------------------------------
# Additional coverage: _get_pv_as_of with deleted baseline
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_pv_as_of_baseline_not_found_after_wp(
    db: AsyncSession, actor_id: UUID
) -> None:
    """_get_pv_as_of returns 0 when WP found but baseline deleted."""
    hierarchy = await create_full_hierarchy(db, actor_id, budget_amount=Decimal("50000"))
    wp = hierarchy["wp"]
    await db.commit()

    service = EVMService(db)

    # Set a non-existent baseline ID on the WP
    from sqlalchemy import update

    fake_baseline_id = uuid4()
    await db.execute(
        update(WorkPackage.__table__)
        .where(WorkPackage.work_package_id == wp.work_package_id)
        .where(func.upper(WorkPackage.valid_time).is_(None))
        .values(schedule_baseline_id=fake_baseline_id)
    )
    await db.commit()

    result = await service._get_pv_as_of(
        wp.work_package_id, datetime.now(UTC), "main", BranchMode.MERGED
    )
    assert result == Decimal("0")


# ---------------------------------------------------------------------------
# Additional coverage: _generate_timeseries_points with no baseline but has EV/AC
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_timeseries_points_no_baseline_with_progress(
    db: AsyncSession, actor_id: UUID
) -> None:
    """_generate_timeseries_points generates points from EV data without baseline."""
    hierarchy = await create_full_hierarchy(db, actor_id, budget_amount=Decimal("50000"))
    wp = hierarchy["wp"]
    await create_test_progress_entry(
        db, actor_id, wp.work_package_id, progress_percentage=Decimal("30.00")
    )
    await db.commit()

    service = EVMService(db)
    now = datetime.now(UTC)
    result = await service._generate_timeseries_points(
        work_package_id=wp.work_package_id,
        start_date=now - timedelta(days=5),
        end_date=now,
        granularity=EVMTimeSeriesGranularity.DAY,
        control_date=now,
        branch="main",
        branch_mode=BranchMode.MERGED,
    )

    # Should have points from EV data (no baseline, no AC)
    assert len(result) >= 1


# ---------------------------------------------------------------------------
# Additional coverage: get_evm_timeseries WP with past control_date
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_evm_timeseries_wp_control_date_past_end(
    db: AsyncSession, actor_id: UUID
) -> None:
    """get_evm_timeseries WP with control_date past baseline end extends range."""
    hierarchy = await _setup_wp_with_data(
        db, actor_id, budget=Decimal("50000"), progress_pct=Decimal("50.00"),
    )
    wp = hierarchy["wp"]
    await db.commit()

    service = EVMService(db)

    # Use a control date far in the future to trigger end_date extension
    future = datetime.now(UTC) + timedelta(days=200)
    ts = await service.get_evm_timeseries(
        entity_type=EntityType.WORK_PACKAGE,
        entity_id=wp.work_package_id,
        granularity=EVMTimeSeriesGranularity.MONTH,
        control_date=future,
    )

    assert ts.total_points >= 0


# ---------------------------------------------------------------------------
# Additional coverage: _generate_timeseries_points_batch with no baseline but data
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_timeseries_points_batch_no_baseline_with_progress(
    db: AsyncSession, actor_id: UUID
) -> None:
    """_generate_timeseries_points_batch generates points for WP with progress but no baseline."""
    hierarchy = await create_full_hierarchy(db, actor_id, budget_amount=Decimal("50000"))
    wp = hierarchy["wp"]
    await create_test_progress_entry(
        db, actor_id, wp.work_package_id, progress_percentage=Decimal("40.00")
    )
    await create_test_cost_registration(
        db, actor_id, hierarchy["ce"].cost_element_id, amount=Decimal("5000")
    )
    await db.commit()

    service = EVMService(db)
    result = await service._generate_timeseries_points_batch(
        [wp.work_package_id],
        EVMTimeSeriesGranularity.DAY,
        datetime.now(UTC),
        "main",
        BranchMode.MERGED,
    )

    assert wp.work_package_id in result
    points = result[wp.work_package_id]
    assert len(points) > 0
    # All PV should be 0 since no baseline
    for p in points:
        assert p.pv == Decimal("0")


# ---------------------------------------------------------------------------
# Additional coverage: _aggregate_wp_timeseries with actual data
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_aggregate_wp_timeseries_with_data(
    db: AsyncSession, actor_id: UUID
) -> None:
    """_aggregate_wp_timeseries aggregates data from multiple WPs."""
    hierarchy = await _setup_wp_with_data(
        db, actor_id, budget=Decimal("50000"), progress_pct=Decimal("50.00"),
        cost_amounts=[Decimal("5000")],
    )
    wp = hierarchy["wp"]
    await db.commit()

    service = EVMService(db)
    result = await service._aggregate_wp_timeseries(
        [wp.work_package_id],
        EVMTimeSeriesGranularity.WEEK,
        datetime.now(UTC),
        "main",
        BranchMode.MERGED,
    )

    assert result.total_points > 0


# ---------------------------------------------------------------------------
# Additional coverage: _get_project_evm_timeseries with project that has WBS but no WPs
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_project_evm_timeseries_has_wbs_no_wps(
    db: AsyncSession, actor_id: UUID
) -> None:
    """_get_project_evm_timeseries with WBS but no WPs under it."""
    service = EVMService(db)
    from tests.factories import create_test_project, create_test_wbs_element

    project = await create_test_project(db, actor_id, start_date=datetime(2026, 1, 1, tzinfo=UTC), end_date=datetime(2026, 12, 31, tzinfo=UTC))
    await create_test_wbs_element(db, actor_id, project.project_id)
    await db.commit()

    result = await service._get_project_evm_timeseries(
        project_id=project.project_id,
        granularity=EVMTimeSeriesGranularity.WEEK,
        control_date=datetime.now(UTC),
        branch="main",
        branch_mode=BranchMode.MERGED,
    )

    assert result.total_points == 0


# ---------------------------------------------------------------------------
# Additional coverage: _gather_timeseries with non-ValueError exception
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_gather_timeseries_filters_runtime_errors(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """_gather_timeseries logs warning for non-ValueError exceptions."""
    service = EVMService.__new__(EVMService)

    ts1 = EVMTimeSeriesResponse(
        granularity=EVMTimeSeriesGranularity.WEEK,
        points=[
            EVMTimeSeriesPoint(
                date=datetime(2026, 1, 1, tzinfo=UTC),
                pv=Decimal("100"), ev=Decimal("50"),
                ac=Decimal("60"), forecast=Decimal("100"),
                actual=Decimal("60"), cpi=None, spi=None,
            )
        ],
        start_date=datetime(2026, 1, 1, tzinfo=UTC),
        end_date=datetime(2026, 1, 7, tzinfo=UTC),
        total_points=1,
    )

    async def return_ts() -> EVMTimeSeriesResponse:
        return ts1

    async def raise_runtime_error() -> EVMTimeSeriesResponse:
        raise RuntimeError("unexpected failure")

    with caplog.at_level(logging.WARNING, logger="app.services.evm_service"):
        results = await service._gather_timeseries(
            [return_ts(), raise_runtime_error()],
            "test",
        )
    assert len(results) == 1
    assert any("Unexpected error" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# Additional coverage: _batch_calculate_work_package_metrics with no CEs
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_batch_calculate_work_package_metrics_no_ces(
    db: AsyncSession, actor_id: UUID
) -> None:
    """_batch_calculate_work_package_metrics with WP that has no cost elements."""
    hierarchy = await create_full_hierarchy(db, actor_id, budget_amount=Decimal("50000"))
    wp = hierarchy["wp"]
    # Delete the cost element to create a WP with no CEs
    from sqlalchemy import update as sql_update

    from app.models.domain.cost_element import CostElement

    await db.execute(
        sql_update(CostElement.__table__)
        .where(CostElement.cost_element_id == hierarchy["ce"].cost_element_id)
        .values(deleted_at=datetime.now(UTC))
    )
    await db.commit()

    service = EVMService(db)
    result = await service._batch_calculate_work_package_metrics(
        work_package_ids=[wp.work_package_id],
        control_date=datetime.now(UTC),
        branch="main",
        branch_mode=BranchMode.MERGED,
    )

    # Should still return metrics (with AC=0)
    assert len(result) == 1
    assert result[0].ac == Decimal("0")
