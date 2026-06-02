"""Route tests for Cost Registration API endpoints."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.factories import (
    create_full_hierarchy,
    create_test_cost_registration,
)

PREFIX = "/cost-registrations"


@pytest.mark.asyncio
async def test_create_cost_registration(
    client: AsyncClient,
    db: AsyncSession,
    actor_id: UUID,
) -> None:
    """POST /cost-registrations creates a new registration and returns 201."""
    h = await create_full_hierarchy(db, actor_id)
    await db.commit()

    payload = {
        "cost_element_id": str(h["ce"].cost_element_id),
        "amount": "2500",
        "description": "Test cost registration",
        "registration_date": datetime.now(UTC).isoformat(),
    }
    response = await client.post(PREFIX, json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["cost_element_id"] == str(h["ce"].cost_element_id)
    assert data["cost_registration_id"] is not None


@pytest.mark.asyncio
async def test_list_cost_registrations(
    client: AsyncClient,
    db: AsyncSession,
    actor_id: UUID,
) -> None:
    """GET /cost-registrations returns a paginated list."""
    h = await create_full_hierarchy(db, actor_id)
    await create_test_cost_registration(db, actor_id, h["ce"].cost_element_id)
    await db.commit()

    response = await client.get(PREFIX, params={"page": 1, "per_page": 20})
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_get_cost_registration(
    client: AsyncClient,
    db: AsyncSession,
    actor_id: UUID,
) -> None:
    """GET /cost-registrations/{id} returns the registration."""
    h = await create_full_hierarchy(db, actor_id)
    cr = await create_test_cost_registration(db, actor_id, h["ce"].cost_element_id)
    await db.commit()

    response = await client.get(f"{PREFIX}/{cr.cost_registration_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["cost_registration_id"] == str(cr.cost_registration_id)


@pytest.mark.asyncio
async def test_get_cost_registration_not_found(client: AsyncClient) -> None:
    """GET /cost-registrations/{id} returns 404 for unknown ID."""
    response = await client.get(f"{PREFIX}/{uuid4()}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_cost_registrations_by_cost_element(
    client: AsyncClient,
    db: AsyncSession,
    actor_id: UUID,
) -> None:
    """GET /cost-registrations filtered by cost_element_id."""
    h = await create_full_hierarchy(db, actor_id)
    await db.commit()

    response = await client.get(
        PREFIX,
        params={"cost_element_id": str(h["ce"].cost_element_id)},
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
