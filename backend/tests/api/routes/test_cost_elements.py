"""Route tests for Cost Element (EOC) API endpoints."""

from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.factories import (
    create_full_hierarchy,
)

PREFIX = "/cost-elements"
WP_PREFIX = "/work-packages"


@pytest.mark.asyncio
async def test_create_cost_element(
    client: AsyncClient,
    db: AsyncSession,
    actor_id: UUID,
) -> None:
    """POST /work-packages/{wp_id}/cost-elements creates a new CE."""
    h = await create_full_hierarchy(db, actor_id)
    await db.commit()

    payload = {
        "work_package_id": str(h["wp"].work_package_id),
        "cost_element_type_id": str(h["ce_type"].cost_element_type_id),
        "amount": "15000",
    }
    response = await client.post(
        f"{WP_PREFIX}/{h['wp'].work_package_id}/cost-elements",
        json=payload,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["work_package_id"] == str(h["wp"].work_package_id)
    assert data["cost_element_type_id"] == str(h["ce_type"].cost_element_type_id)


@pytest.mark.asyncio
async def test_list_cost_elements(
    client: AsyncClient,
    db: AsyncSession,
    actor_id: UUID,
) -> None:
    """GET /cost-elements returns a paginated list."""
    await create_full_hierarchy(db, actor_id)
    await db.commit()

    response = await client.get(PREFIX, params={"page": 1, "per_page": 20})
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_get_cost_element(
    client: AsyncClient,
    db: AsyncSession,
    actor_id: UUID,
) -> None:
    """GET /cost-elements/{id} returns the cost element."""
    h = await create_full_hierarchy(db, actor_id)
    await db.commit()

    response = await client.get(f"{PREFIX}/{h['ce'].cost_element_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["cost_element_id"] == str(h["ce"].cost_element_id)


@pytest.mark.asyncio
async def test_get_cost_element_not_found(client: AsyncClient) -> None:
    """GET /cost-elements/{id} returns 404 for unknown ID."""
    response = await client.get(f"{PREFIX}/{uuid4()}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_cost_element(
    client: AsyncClient,
    db: AsyncSession,
    actor_id: UUID,
) -> None:
    """PUT /cost-elements/{id} updates the CE."""
    h = await create_full_hierarchy(db, actor_id)
    await db.commit()

    response = await client.put(
        f"{PREFIX}/{h['ce'].cost_element_id}",
        json={"description": "Updated cost element"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["description"] == "Updated cost element"


@pytest.mark.asyncio
async def test_list_cost_elements_by_work_package(
    client: AsyncClient,
    db: AsyncSession,
    actor_id: UUID,
) -> None:
    """GET /cost-elements filtered by work_package_id."""
    h = await create_full_hierarchy(db, actor_id)
    await db.commit()

    response = await client.get(
        PREFIX,
        params={"work_package_id": str(h["wp"].work_package_id)},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    for item in data["items"]:
        assert item["work_package_id"] == str(h["wp"].work_package_id)
