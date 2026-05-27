"""Route tests for Control Account API endpoints."""

from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.factories import create_full_hierarchy

PREFIX = "/control-accounts"


@pytest.mark.asyncio
async def test_create_control_account(
    client: AsyncClient,
    db: AsyncSession,
    actor_id: UUID,
) -> None:
    """POST /control-accounts creates a new CA and returns 201."""
    h = await create_full_hierarchy(db, actor_id)
    await db.commit()

    # Create a second org unit so the CA doesn't collide with the seeded one
    from tests.factories import create_test_org_unit

    org2 = await create_test_org_unit(db, actor_id)
    await db.commit()

    payload = {
        "wbs_element_id": str(h["wbs"].wbs_element_id),
        "organizational_unit_id": str(org2.organizational_unit_id),
        "name": "New Control Account",
        "code": "CA-NEW",
    }
    response = await client.post(PREFIX, json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "New Control Account"
    assert data["control_account_id"] is not None
    assert data["wbs_element_id"] == str(h["wbs"].wbs_element_id)


@pytest.mark.asyncio
async def test_list_control_accounts(
    client: AsyncClient,
    db: AsyncSession,
    actor_id: UUID,
) -> None:
    """GET /control-accounts returns a paginated list."""
    await create_full_hierarchy(db, actor_id)
    await db.commit()

    response = await client.get(PREFIX, params={"page": 1, "per_page": 20})
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_get_control_account(
    client: AsyncClient,
    db: AsyncSession,
    actor_id: UUID,
) -> None:
    """GET /control-accounts/{id} returns the control account."""
    h = await create_full_hierarchy(db, actor_id)
    await db.commit()

    response = await client.get(f"{PREFIX}/{h['ca'].control_account_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["control_account_id"] == str(h["ca"].control_account_id)


@pytest.mark.asyncio
async def test_get_control_account_not_found(client: AsyncClient) -> None:
    """GET /control-accounts/{id} returns 404 for unknown ID."""
    response = await client.get(f"{PREFIX}/{uuid4()}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_control_account(
    client: AsyncClient,
    db: AsyncSession,
    actor_id: UUID,
) -> None:
    """PUT /control-accounts/{id} updates the CA."""
    h = await create_full_hierarchy(db, actor_id)
    await db.commit()

    response = await client.put(
        f"{PREFIX}/{h['ca'].control_account_id}",
        json={"name": "Updated CA Name"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated CA Name"


@pytest.mark.asyncio
async def test_filter_control_accounts_by_wbs_element(
    client: AsyncClient,
    db: AsyncSession,
    actor_id: UUID,
) -> None:
    """GET /control-accounts filtered by wbs_element_id returns matching CAs."""
    h = await create_full_hierarchy(db, actor_id)
    await db.commit()

    response = await client.get(
        PREFIX,
        params={"wbs_element_id": str(h["wbs"].wbs_element_id)},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    for item in data["items"]:
        assert item["wbs_element_id"] == str(h["wbs"].wbs_element_id)
