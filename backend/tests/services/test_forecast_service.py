"""Tests for ForecastService.

Covers creation, retrieval, update, linking to work packages,
ensure_exists, batch retrieval, and error handling.
"""

from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.forecast_service import (
    ForecastAlreadyExistsError,
    ForecastService,
)
from tests.factories import create_full_hierarchy


@pytest.mark.asyncio
async def test_create_root_forecast(db: AsyncSession, actor_id: UUID) -> None:
    """create_root should persist a forecast with the given fields."""
    service = ForecastService(db)

    forecast = await service.create_root(
        root_id=uuid4(),
        actor_id=actor_id,
        eac_amount=Decimal("120000.00"),
        basis_of_estimate="Initial estimate based on historical data",
    )

    assert forecast.forecast_id is not None
    assert forecast.eac_amount == Decimal("120000.00")
    assert forecast.branch == "main"


@pytest.mark.asyncio
async def test_get_by_id_returns_created_forecast(
    db: AsyncSession, actor_id: UUID
) -> None:
    """get_by_id should retrieve a forecast by its root ID."""
    service = ForecastService(db)

    forecast = await service.create_root(
        root_id=uuid4(),
        actor_id=actor_id,
        eac_amount=Decimal("50000.00"),
        basis_of_estimate="Expert judgment",
    )

    found = await service.get_by_id(forecast.forecast_id)
    assert found is not None
    assert found.forecast_id == forecast.forecast_id
    assert found.eac_amount == Decimal("50000.00")


@pytest.mark.asyncio
async def test_get_by_id_returns_none_for_unknown(
    db: AsyncSession, actor_id: UUID
) -> None:
    """get_by_id should return None when no forecast matches."""
    service = ForecastService(db)

    found = await service.get_by_id(uuid4())
    assert found is None


@pytest.mark.asyncio
async def test_create_for_work_package_links_forecast(
    db: AsyncSession, actor_id: UUID
) -> None:
    """create_for_work_package should create a forecast and link it to the WP."""
    hierarchy = await create_full_hierarchy(db, actor_id)
    wp = hierarchy["wp"]
    service = ForecastService(db)

    forecast = await service.create_for_work_package(
        work_package_id=wp.work_package_id,
        actor_id=actor_id,
        eac_amount=Decimal("80000.00"),
        basis_of_estimate="Bottom-up estimate",
    )

    assert forecast is not None

    # Verify retrieval via get_for_work_package
    linked = await service.get_for_work_package(wp.work_package_id)
    assert linked is not None
    assert linked.forecast_id == forecast.forecast_id


@pytest.mark.asyncio
async def test_create_for_work_package_raises_on_duplicate(
    db: AsyncSession, actor_id: UUID
) -> None:
    """create_for_work_package should raise ForecastAlreadyExistsError on second call."""
    hierarchy = await create_full_hierarchy(db, actor_id)
    wp = hierarchy["wp"]
    service = ForecastService(db)

    await service.create_for_work_package(
        work_package_id=wp.work_package_id,
        actor_id=actor_id,
        eac_amount=Decimal("50000.00"),
        basis_of_estimate="First estimate",
    )

    with pytest.raises(ForecastAlreadyExistsError):
        await service.create_for_work_package(
            work_package_id=wp.work_package_id,
            actor_id=actor_id,
            eac_amount=Decimal("60000.00"),
            basis_of_estimate="Second estimate",
        )


@pytest.mark.asyncio
async def test_get_for_work_package_returns_none_without_forecast(
    db: AsyncSession, actor_id: UUID
) -> None:
    """get_for_work_package should return None when no forecast is linked."""
    hierarchy = await create_full_hierarchy(db, actor_id)
    service = ForecastService(db)

    found = await service.get_for_work_package(hierarchy["wp"].work_package_id)
    assert found is None


@pytest.mark.asyncio
async def test_ensure_exists_creates_when_missing(
    db: AsyncSession, actor_id: UUID
) -> None:
    """ensure_exists should create a default forecast when none exists."""
    hierarchy = await create_full_hierarchy(db, actor_id)
    wp = hierarchy["wp"]
    service = ForecastService(db)

    forecast = await service.ensure_exists(
        work_package_id=wp.work_package_id,
        actor_id=actor_id,
        budget_amount=Decimal("75000.00"),
    )

    assert forecast is not None
    assert forecast.eac_amount == Decimal("75000.00")

    # Calling again should return the same forecast
    forecast2 = await service.ensure_exists(
        work_package_id=wp.work_package_id,
        actor_id=actor_id,
    )
    assert forecast2.forecast_id == forecast.forecast_id


@pytest.mark.asyncio
async def test_ensure_exists_defaults_to_zero_eac(
    db: AsyncSession, actor_id: UUID
) -> None:
    """ensure_exists without budget_amount should default EAC to 0."""
    hierarchy = await create_full_hierarchy(db, actor_id)
    wp = hierarchy["wp"]
    service = ForecastService(db)

    forecast = await service.ensure_exists(
        work_package_id=wp.work_package_id,
        actor_id=actor_id,
    )

    assert forecast.eac_amount == Decimal("0.00")


@pytest.mark.asyncio
async def test_update_forecast_changes_eac(db: AsyncSession, actor_id: UUID) -> None:
    """update_forecast should create a new version with updated EAC."""
    from app.models.schemas.forecast import ForecastUpdate

    hierarchy = await create_full_hierarchy(db, actor_id)
    wp = hierarchy["wp"]
    service = ForecastService(db)

    forecast = await service.create_for_work_package(
        work_package_id=wp.work_package_id,
        actor_id=actor_id,
        eac_amount=Decimal("50000.00"),
        basis_of_estimate="Original",
    )

    updated = await service.update_forecast(
        forecast_id=forecast.forecast_id,
        forecast_in=ForecastUpdate(
            eac_amount=Decimal("65000.00"),
            basis_of_estimate="Revised after scope change",
        ),
        actor_id=actor_id,
    )

    assert updated.eac_amount == Decimal("65000.00")


@pytest.mark.asyncio
async def test_list_returns_forecasts(db: AsyncSession, actor_id: UUID) -> None:
    """list should return all forecasts on a branch."""
    service = ForecastService(db)

    await service.create_root(
        root_id=uuid4(),
        actor_id=actor_id,
        eac_amount=Decimal("10000.00"),
        basis_of_estimate="List test A",
    )
    await service.create_root(
        root_id=uuid4(),
        actor_id=actor_id,
        eac_amount=Decimal("20000.00"),
        basis_of_estimate="List test B",
    )

    results = await service.list()
    assert len(results) >= 2


@pytest.mark.asyncio
async def test_get_forecasts_for_work_packages_batch(
    db: AsyncSession, actor_id: UUID
) -> None:
    """get_forecasts_for_work_packages should return a mapping of WP -> Forecast."""
    hierarchy = await create_full_hierarchy(db, actor_id)
    wp = hierarchy["wp"]
    service = ForecastService(db)

    forecast = await service.create_for_work_package(
        work_package_id=wp.work_package_id,
        actor_id=actor_id,
        eac_amount=Decimal("90000.00"),
        basis_of_estimate="Batch test",
    )

    result = await service.get_forecasts_for_work_packages([wp.work_package_id])

    assert wp.work_package_id in result
    assert result[wp.work_package_id].forecast_id == forecast.forecast_id


@pytest.mark.asyncio
async def test_get_forecasts_for_work_packages_empty_input(
    db: AsyncSession, actor_id: UUID
) -> None:
    """get_forecasts_for_work_packages should return empty dict for empty input."""
    service = ForecastService(db)

    result = await service.get_forecasts_for_work_packages([])
    assert result == {}


@pytest.mark.asyncio
async def test_backward_compat_aliases(db: AsyncSession, actor_id: UUID) -> None:
    """Backward-compatible aliases should delegate to work package methods."""
    hierarchy = await create_full_hierarchy(db, actor_id)
    wp = hierarchy["wp"]
    service = ForecastService(db)

    # create_for_cost_element alias
    forecast = await service.create_for_cost_element(
        cost_element_id=wp.work_package_id,
        actor_id=actor_id,
        eac_amount=Decimal("30000.00"),
        basis_of_estimate="Compat test",
    )
    assert forecast is not None

    # get_for_cost_element alias
    found = await service.get_for_cost_element(wp.work_package_id)
    assert found is not None
    assert found.forecast_id == forecast.forecast_id

    # get_forecasts_for_cost_elements alias
    batch = await service.get_forecasts_for_cost_elements([wp.work_package_id])
    assert wp.work_package_id in batch


@pytest.mark.asyncio
async def test_create_forecast_with_control_date(
    db: AsyncSession, actor_id: UUID
) -> None:
    """create_forecast uses control_date from schema when provided."""
    from datetime import UTC, datetime, timedelta

    from app.models.schemas.forecast import ForecastCreate

    service = ForecastService(db)
    control_date = datetime.now(UTC) - timedelta(days=5)

    forecast_in = ForecastCreate(
        eac_amount=Decimal("100000.00"),
        basis_of_estimate="With control_date",
        control_date=control_date,
    )
    forecast = await service.create_forecast(forecast_in, actor_id)
    assert forecast is not None
    assert forecast.eac_amount == Decimal("100000.00")


@pytest.mark.asyncio
async def test_create_forecast_with_explicit_branch(
    db: AsyncSession, actor_id: UUID
) -> None:
    """create_forecast passes branch parameter correctly."""
    from app.models.schemas.forecast import ForecastCreate

    service = ForecastService(db)

    forecast_in = ForecastCreate(
        eac_amount=Decimal("55000.00"),
        basis_of_estimate="Branch test",
    )
    forecast = await service.create_forecast(forecast_in, actor_id, branch="main")
    assert forecast is not None
    assert forecast.branch == "main"


@pytest.mark.asyncio
async def test_get_forecasts_for_work_packages_with_as_of(
    db: AsyncSession, actor_id: UUID
) -> None:
    """get_forecasts_for_work_packages supports time-travel via as_of."""
    from datetime import UTC, datetime, timedelta

    hierarchy = await create_full_hierarchy(db, actor_id)
    wp = hierarchy["wp"]
    service = ForecastService(db)

    forecast = await service.create_for_work_package(
        work_package_id=wp.work_package_id,
        actor_id=actor_id,
        eac_amount=Decimal("80000.00"),
        basis_of_estimate="AsOf test",
    )

    as_of = datetime.now(UTC) + timedelta(hours=1)
    result = await service.get_forecasts_for_work_packages(
        [wp.work_package_id], as_of=as_of
    )
    assert wp.work_package_id in result
    assert result[wp.work_package_id].forecast_id == forecast.forecast_id


@pytest.mark.asyncio
async def test_soft_delete_forecast_with_branch_and_control_date(
    db: AsyncSession, actor_id: UUID
) -> None:
    """soft_delete passes branch and control_date to BranchableSoftDeleteCommand."""
    from datetime import UTC, datetime

    hierarchy = await create_full_hierarchy(db, actor_id)
    wp = hierarchy["wp"]
    service = ForecastService(db)

    forecast = await service.create_for_work_package(
        work_package_id=wp.work_package_id,
        actor_id=actor_id,
        eac_amount=Decimal("50000.00"),
        basis_of_estimate="Delete test",
    )
    await db.commit()

    control_date = datetime.now(UTC)
    await service.soft_delete(
        forecast.forecast_id, actor_id, branch="main", control_date=control_date
    )
    await db.commit()

    result = await service.get_by_id(forecast.forecast_id)
    assert result is None
