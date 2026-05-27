"""Route tests for Work Package API endpoints."""

from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.factories import create_full_hierarchy

PREFIX = "/work-packages"


@pytest.mark.asyncio
async def test_create_work_package(
    client: AsyncClient,
    db: AsyncSession,
    actor_id: UUID,
) -> None:
    """POST /work-packages creates a new WP and returns 201."""
    h = await create_full_hierarchy(db, actor_id)
    await db.commit()

    payload = {
        "control_account_id": str(h["ca"].control_account_id),
        "name": "New Work Package",
        "code": "WP-NEW",
        "budget_amount": "30000",
        "status": "open",
    }
    response = await client.post(PREFIX, json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "New Work Package"
    assert data["work_package_id"] is not None
    assert data["control_account_id"] == str(h["ca"].control_account_id)


@pytest.mark.asyncio
async def test_list_work_packages(
    client: AsyncClient,
    db: AsyncSession,
    actor_id: UUID,
) -> None:
    """GET /work-packages returns a paginated list."""
    await create_full_hierarchy(db, actor_id)
    await db.commit()

    response = await client.get(PREFIX, params={"page": 1, "per_page": 20})
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_get_work_package(
    client: AsyncClient,
    db: AsyncSession,
    actor_id: UUID,
) -> None:
    """GET /work-packages/{id} returns the work package."""
    h = await create_full_hierarchy(db, actor_id)
    await db.commit()

    response = await client.get(f"{PREFIX}/{h['wp'].work_package_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["work_package_id"] == str(h["wp"].work_package_id)


@pytest.mark.asyncio
async def test_get_work_package_not_found(client: AsyncClient) -> None:
    """GET /work-packages/{id} returns 404 for unknown ID."""
    response = await client.get(f"{PREFIX}/{uuid4()}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_work_package(
    client: AsyncClient,
    db: AsyncSession,
    actor_id: UUID,
) -> None:
    """PUT /work-packages/{id} updates the WP."""
    h = await create_full_hierarchy(db, actor_id)
    await db.commit()

    response = await client.put(
        f"{PREFIX}/{h['wp'].work_package_id}",
        json={"name": "Updated WP Name", "budget_amount": "75000"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated WP Name"
    assert data["budget_amount"] == "75000"


@pytest.mark.asyncio
async def test_get_work_package_budget_status(
    client: AsyncClient,
    db: AsyncSession,
    actor_id: UUID,
) -> None:
    """GET /work-packages/{id}/budget-status returns budget info."""
    h = await create_full_hierarchy(db, actor_id)
    await db.commit()

    response = await client.get(f"{PREFIX}/{h['wp'].work_package_id}/budget-status")
    assert response.status_code == 200
    data = response.json()
    assert "budget" in data
    assert "used" in data
    assert "remaining" in data
    assert "percentage" in data


@pytest.mark.asyncio
async def test_get_work_package_breadcrumb(
    client: AsyncClient,
    db: AsyncSession,
    actor_id: UUID,
) -> None:
    """GET /work-packages/{id}/breadcrumb returns hierarchy info."""
    h = await create_full_hierarchy(db, actor_id)
    await db.commit()

    response = await client.get(f"{PREFIX}/{h['wp'].work_package_id}/breadcrumb")
    assert response.status_code == 200
    data = response.json()
    assert "project" in data
    assert "wbs_element" in data
    assert "control_account" in data
    assert "work_package" in data


@pytest.mark.asyncio
async def test_filter_work_packages_by_control_account(
    client: AsyncClient,
    db: AsyncSession,
    actor_id: UUID,
) -> None:
    """GET /work-packages filtered by control_account_id."""
    h = await create_full_hierarchy(db, actor_id)
    await db.commit()

    response = await client.get(
        PREFIX,
        params={"control_account_id": str(h["ca"].control_account_id)},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    for item in data["items"]:
        assert item["control_account_id"] == str(h["ca"].control_account_id)
