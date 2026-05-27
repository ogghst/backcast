"""Tests for ScheduleBaselineService.

Covers creation, retrieval, update, linking to work packages,
and PV calculation with different progression types.
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.schedule_baseline_service import (
    BaselineAlreadyExistsError,
    ScheduleBaselineService,
)
from tests.factories import (
    create_full_hierarchy,
    create_test_schedule_baseline,
)


@pytest.mark.asyncio
async def test_create_root_baseline(db: AsyncSession, actor_id: UUID) -> None:
    """create_root should persist a schedule baseline with correct fields."""
    await create_full_hierarchy(db, actor_id)
    service = ScheduleBaselineService(db)

    baseline = await service.create_root(
        root_id=uuid4(),
        actor_id=actor_id,
        name="Q1 Baseline",
        start_date=datetime.now(UTC) - timedelta(days=30),
        end_date=datetime.now(UTC) + timedelta(days=60),
        progression_type="LINEAR",
    )

    assert baseline.schedule_baseline_id is not None
    assert baseline.name == "Q1 Baseline"
    assert baseline.progression_type == "LINEAR"


@pytest.mark.asyncio
async def test_get_by_id_returns_created_baseline(
    db: AsyncSession, actor_id: UUID
) -> None:
    """get_by_id should retrieve a baseline by its root ID."""
    hierarchy = await create_full_hierarchy(db, actor_id)
    baseline = await create_test_schedule_baseline(
        db, actor_id, hierarchy["wp"].work_package_id
    )
    service = ScheduleBaselineService(db)

    found = await service.get_by_id(baseline.schedule_baseline_id)

    assert found is not None
    assert found.schedule_baseline_id == baseline.schedule_baseline_id


@pytest.mark.asyncio
async def test_get_by_id_returns_none_for_unknown_uuid(
    db: AsyncSession, actor_id: UUID
) -> None:
    """get_by_id should return None when no baseline matches."""
    service = ScheduleBaselineService(db)

    found = await service.get_by_id(uuid4())

    assert found is None


@pytest.mark.asyncio
async def test_create_for_work_package_links_baseline(
    db: AsyncSession, actor_id: UUID
) -> None:
    """create_for_work_package should create baseline and link via work package."""
    hierarchy = await create_full_hierarchy(db, actor_id)
    wp = hierarchy["wp"]
    service = ScheduleBaselineService(db)

    now = datetime.now(UTC)
    baseline = await service.create_for_work_package(
        work_package_id=wp.work_package_id,
        actor_id=actor_id,
        name="WP Baseline",
        start_date=now - timedelta(days=10),
        end_date=now + timedelta(days=80),
        progression_type="LINEAR",
    )

    assert baseline is not None

    # Verify link via get_for_work_package
    linked = await service.get_for_work_package(wp.work_package_id)
    assert linked is not None
    assert linked.schedule_baseline_id == baseline.schedule_baseline_id


@pytest.mark.asyncio
async def test_create_for_work_package_raises_on_duplicate(
    db: AsyncSession, actor_id: UUID
) -> None:
    """create_for_work_package should raise BaselineAlreadyExistsError on second call."""
    hierarchy = await create_full_hierarchy(db, actor_id)
    wp = hierarchy["wp"]
    service = ScheduleBaselineService(db)

    now = datetime.now(UTC)
    await service.create_for_work_package(
        work_package_id=wp.work_package_id,
        actor_id=actor_id,
        name="First Baseline",
        start_date=now,
        end_date=now + timedelta(days=90),
    )

    with pytest.raises(BaselineAlreadyExistsError):
        await service.create_for_work_package(
            work_package_id=wp.work_package_id,
            actor_id=actor_id,
            name="Duplicate Baseline",
            start_date=now,
            end_date=now + timedelta(days=90),
        )


@pytest.mark.asyncio
async def test_get_for_work_package_returns_none_without_baseline(
    db: AsyncSession, actor_id: UUID
) -> None:
    """get_for_work_package should return None when no baseline is linked."""
    hierarchy = await create_full_hierarchy(db, actor_id)
    service = ScheduleBaselineService(db)

    found = await service.get_for_work_package(hierarchy["wp"].work_package_id)
    assert found is None


@pytest.mark.asyncio
async def test_ensure_exists_creates_when_missing(
    db: AsyncSession, actor_id: UUID
) -> None:
    """ensure_exists should create a default baseline when none exists."""
    hierarchy = await create_full_hierarchy(db, actor_id)
    wp = hierarchy["wp"]
    service = ScheduleBaselineService(db)

    baseline = await service.ensure_exists(
        work_package_id=wp.work_package_id,
        actor_id=actor_id,
        start_date=datetime.now(UTC),
        end_date=datetime.now(UTC) + timedelta(days=60),
    )

    assert baseline is not None
    assert baseline.progression_type == "LINEAR"

    # Calling again should return same baseline (not raise)
    baseline2 = await service.ensure_exists(
        work_package_id=wp.work_package_id,
        actor_id=actor_id,
    )
    assert baseline2.schedule_baseline_id == baseline.schedule_baseline_id


@pytest.mark.asyncio
async def test_update_schedule_baseline_changes_name(
    db: AsyncSession, actor_id: UUID
) -> None:
    """update_schedule_baseline should create a new version with updated fields."""
    from app.models.schemas.schedule_baseline import ScheduleBaselineUpdate

    hierarchy = await create_full_hierarchy(db, actor_id)
    baseline = await create_test_schedule_baseline(
        db, actor_id, hierarchy["wp"].work_package_id
    )
    service = ScheduleBaselineService(db)

    updated = await service.update_schedule_baseline(
        root_id=baseline.schedule_baseline_id,
        baseline_in=ScheduleBaselineUpdate(name="Updated Baseline Name"),
        actor_id=actor_id,
    )

    assert updated.name == "Updated Baseline Name"


@pytest.mark.asyncio
async def test_get_baselines_for_work_packages_batch(
    db: AsyncSession, actor_id: UUID
) -> None:
    """get_baselines_for_work_packages should return mapping for linked WPs."""
    hierarchy = await create_full_hierarchy(db, actor_id)
    wp = hierarchy["wp"]
    service = ScheduleBaselineService(db)

    now = datetime.now(UTC)
    baseline = await service.create_for_work_package(
        work_package_id=wp.work_package_id,
        actor_id=actor_id,
        name="Batch Test Baseline",
        start_date=now - timedelta(days=10),
        end_date=now + timedelta(days=80),
    )

    result = await service.get_baselines_for_work_packages([wp.work_package_id])

    assert wp.work_package_id in result
    assert (
        result[wp.work_package_id].schedule_baseline_id == baseline.schedule_baseline_id
    )


@pytest.mark.asyncio
async def test_get_baselines_for_work_packages_empty_input(
    db: AsyncSession, actor_id: UUID
) -> None:
    """get_baselines_for_work_packages should return empty dict for empty input."""
    service = ScheduleBaselineService(db)

    result = await service.get_baselines_for_work_packages([])
    assert result == {}


@pytest.mark.asyncio
async def test_backward_compat_get_for_cost_element(
    db: AsyncSession, actor_id: UUID
) -> None:
    """get_for_cost_element alias should behave same as get_for_work_package."""
    hierarchy = await create_full_hierarchy(db, actor_id)
    wp = hierarchy["wp"]
    service = ScheduleBaselineService(db)

    now = datetime.now(UTC)
    baseline = await service.create_for_work_package(
        work_package_id=wp.work_package_id,
        actor_id=actor_id,
        name="Compat Test",
        start_date=now,
        end_date=now + timedelta(days=30),
    )

    result = await service.get_for_cost_element(wp.work_package_id)
    assert result is not None
    assert result.schedule_baseline_id == baseline.schedule_baseline_id


@pytest.mark.asyncio
async def test_linear_pv_progression_at_midpoint(
    db: AsyncSession, actor_id: UUID
) -> None:
    """Linear PV at the midpoint should yield ~50% of BAC."""
    from app.services.progression import get_progression_strategy

    ScheduleBaselineService(db)
    start = datetime(2026, 1, 1, tzinfo=UTC)
    end = datetime(2026, 3, 1, tzinfo=UTC)
    mid = datetime(2026, 2, 1, tzinfo=UTC)

    strategy = get_progression_strategy("LINEAR")
    progress = strategy.calculate_progress(mid, start, end)

    # Linear: ~50% at midpoint (exact depends on day count in each month)
    assert 0.45 <= progress <= 0.55


@pytest.mark.asyncio
async def test_progression_strategies_boundary_values() -> None:
    """All progression strategies should clamp to 0.0 before start and 1.0 after end."""
    from app.services.progression import get_progression_strategy

    start = datetime(2026, 1, 1, tzinfo=UTC)
    end = datetime(2026, 4, 1, tzinfo=UTC)

    for ptype in ("LINEAR", "GAUSSIAN", "LOGARITHMIC"):
        strategy = get_progression_strategy(ptype)

        before = start - timedelta(days=30)
        assert strategy.calculate_progress(before, start, end) == 0.0

        after = end + timedelta(days=30)
        assert strategy.calculate_progress(after, start, end) == 1.0
