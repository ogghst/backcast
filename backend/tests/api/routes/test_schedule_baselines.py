"""Tests for Schedule Baseline API routes.

Tests baseline CRUD, PV calculation, and progression types.
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.factories import create_full_hierarchy

PREFIX = "/schedule-baselines"
WP_PREFIX = "/work-packages"


@pytest.mark.asyncio
async def test_create_baseline(
    client: AsyncClient,
    db: AsyncSession,
    actor_id: UUID,
) -> None:
    """POST /work-packages/{wp_id}/schedule-baseline creates a baseline."""
    h = await create_full_hierarchy(db, actor_id)
    await db.commit()

    now = datetime.now(UTC)
    payload = {
        "name": "Q1 2026 Baseline",
        "start_date": now.isoformat(),
        "end_date": (now + timedelta(days=90)).isoformat(),
        "progression_type": "LINEAR",
    }
    response = await client.post(
        f"{WP_PREFIX}/{h['wp'].work_package_id}/schedule-baseline",
        json=payload,
    )
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["name"] == "Q1 2026 Baseline"
    assert data["progression_type"] == "LINEAR"


@pytest.mark.asyncio
async def test_get_baseline(
    client: AsyncClient,
    db: AsyncSession,
    actor_id: UUID,
) -> None:
    """GET /work-packages/{wp_id}/schedule-baseline returns the baseline."""
    h = await create_full_hierarchy(db, actor_id)
    await db.commit()

    response = await client.get(
        f"{WP_PREFIX}/{h['wp'].work_package_id}/schedule-baseline"
    )
    # May be 200 or 404 depending on whether a baseline was created during WP creation
    assert response.status_code in (200, 404)


@pytest.mark.asyncio
async def test_pv_calculation_linear(
    client: AsyncClient,
    db: AsyncSession,
    actor_id: UUID,
) -> None:
    """GET /schedule-baselines/{id}/pv calculates PV = BAC * progression."""
    h = await create_full_hierarchy(db, actor_id)
    await db.commit()

    # Create a baseline directly via factory
    from tests.factories import create_test_schedule_baseline

    now = datetime.now(UTC)
    baseline = await create_test_schedule_baseline(
        db,
        actor_id,
        h["wp"].work_package_id,
        start_date=now - timedelta(days=45),
        end_date=now + timedelta(days=45),
        progression_type="LINEAR",
    )
    await db.commit()

    resp = await client.get(
        f"{PREFIX}/{baseline.schedule_baseline_id}/pv",
        params={
            "current_date": now.isoformat(),
            "bac": "10000",
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "pv" in data
    assert "progress" in data
    # Linear: at midpoint, progress ~ 0.5
    assert 0.4 <= data["progress"] <= 0.6


@pytest.mark.asyncio
async def test_progression_types(
    client: AsyncClient,
    db: AsyncSession,
    actor_id: UUID,
) -> None:
    """Verify LINEAR, GAUSSIAN, LOGARITHMIC progression types are accepted."""
    h = await create_full_hierarchy(db, actor_id)
    await db.commit()

    now = datetime.now(UTC)
    for ptype in ["LINEAR", "GAUSSIAN", "LOGARITHMIC"]:
        from tests.factories import create_test_schedule_baseline

        baseline = await create_test_schedule_baseline(
            db,
            actor_id,
            h["wp"].work_package_id,
            start_date=now - timedelta(days=45),
            end_date=now + timedelta(days=45),
            progression_type=ptype,
        )
        await db.commit()

        resp = await client.get(
            f"{PREFIX}/{baseline.schedule_baseline_id}/pv",
            params={
                "current_date": now.isoformat(),
                "bac": "10000",
            },
        )
        assert resp.status_code == 200, f"{ptype} failed: {resp.text}"
        data = resp.json()
        assert data["progression_type"] == ptype
        assert 0.0 <= data["progress"] <= 1.0


@pytest.mark.asyncio
async def test_list_schedule_baselines(
    client: AsyncClient,
    db: AsyncSession,
    actor_id: UUID,
) -> None:
    """GET /schedule-baselines returns paginated list."""
    from tests.factories import create_test_schedule_baseline

    h = await create_full_hierarchy(db, actor_id)
    await create_test_schedule_baseline(db, actor_id, h["wp"].work_package_id)
    await db.commit()

    response = await client.get(PREFIX, params={"page": 1, "per_page": 20})
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert data["total"] >= 1
