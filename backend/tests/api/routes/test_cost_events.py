"""Route tests for Cost Event API endpoints."""

from decimal import Decimal
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.factories import (
    create_full_hierarchy,
    create_test_cost_event,
)

PREFIX = "/cost-events"


@pytest.mark.asyncio
async def test_create_cost_event(
    client: AsyncClient,
    db: AsyncSession,
    actor_id: UUID,
) -> None:
    """POST /cost-events creates a new event and returns 201."""
    h = await create_full_hierarchy(db, actor_id)
    await db.commit()

    payload = {
        "project_id": str(h["project"].project_id),
        "name": "Test Quality Event",
        "cost_event_type_id": str(h["cet"].cost_event_type_id),
        "status": "open",
        "coq_category": "internal_failure",
        "estimated_impact": "5000",
    }
    response = await client.post(PREFIX, json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Quality Event"
    assert data["cost_event_id"] is not None
    assert data["project_id"] == str(h["project"].project_id)


@pytest.mark.asyncio
async def test_list_cost_events(
    client: AsyncClient,
    db: AsyncSession,
    actor_id: UUID,
) -> None:
    """GET /cost-events returns a paginated list."""
    h = await create_full_hierarchy(db, actor_id)
    await create_test_cost_event(
        db, actor_id, h["project"].project_id, h["cet"].cost_event_type_id
    )
    await db.commit()

    response = await client.get(PREFIX, params={"page": 1, "per_page": 20})
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_get_cost_event(
    client: AsyncClient,
    db: AsyncSession,
    actor_id: UUID,
) -> None:
    """GET /cost-events/{id} returns the cost event."""
    h = await create_full_hierarchy(db, actor_id)
    event = await create_test_cost_event(
        db, actor_id, h["project"].project_id, h["cet"].cost_event_type_id
    )
    await db.commit()

    response = await client.get(f"{PREFIX}/{event.cost_event_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["cost_event_id"] == str(event.cost_event_id)


@pytest.mark.asyncio
async def test_update_cost_event(
    client: AsyncClient,
    db: AsyncSession,
    actor_id: UUID,
) -> None:
    """PUT /cost-events/{id} updates the event."""
    h = await create_full_hierarchy(db, actor_id)
    event = await create_test_cost_event(
        db, actor_id, h["project"].project_id, h["cet"].cost_event_type_id
    )
    await db.commit()

    response = await client.put(
        f"{PREFIX}/{event.cost_event_id}",
        json={"name": "Updated Event", "estimated_impact": "8000"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Event"
    assert Decimal(data["estimated_impact"]) == Decimal("8000")


@pytest.mark.asyncio
async def test_get_coq_metrics(
    client: AsyncClient,
    db: AsyncSession,
    actor_id: UUID,
) -> None:
    """GET /cost-events/project/{id}/coq-metrics returns COQ metrics."""
    h = await create_full_hierarchy(db, actor_id)
    await db.commit()

    response = await client.get(
        f"{PREFIX}/project/{h['project'].project_id}/coq-metrics"
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)


@pytest.mark.asyncio
async def test_filter_cost_events_by_project(
    client: AsyncClient,
    db: AsyncSession,
    actor_id: UUID,
) -> None:
    """GET /cost-events filtered by project_id."""
    h = await create_full_hierarchy(db, actor_id)
    await db.commit()

    response = await client.get(
        PREFIX,
        params={"project_id": str(h["project"].project_id)},
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
