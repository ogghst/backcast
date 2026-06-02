"""Route tests for WBS Element API endpoints."""

from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.factories import (
    create_full_hierarchy,
    create_test_project,
    create_test_wbs_element,
)

PREFIX = "/wbs-elements"


@pytest.mark.asyncio
async def test_create_wbs_element(
    client: AsyncClient,
    db: AsyncSession,
    actor_id: UUID,
) -> None:
    """POST /wbs-elements creates a new WBS element and returns 201."""
    project = await create_test_project(db, actor_id)
    await db.commit()

    payload = {
        "project_id": str(project.project_id),
        "code": f"1.{uuid4().hex[:4]}",
        "name": "Test WBS Element",
        "level": 1,
    }
    response = await client.post(PREFIX, json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test WBS Element"
    assert data["wbs_element_id"] is not None
    assert data["project_id"] == str(project.project_id)


@pytest.mark.asyncio
async def test_list_wbs_elements(
    client: AsyncClient,
    db: AsyncSession,
    actor_id: UUID,
) -> None:
    """GET /wbs-elements returns a paginated list."""
    project = await create_test_project(db, actor_id)
    await create_test_wbs_element(db, actor_id, project.project_id)
    await db.commit()

    response = await client.get(PREFIX, params={"page": 1, "per_page": 20})
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_get_wbs_element(
    client: AsyncClient,
    db: AsyncSession,
    actor_id: UUID,
) -> None:
    """GET /wbs-elements/{id} returns the WBS element."""
    h = await create_full_hierarchy(db, actor_id)
    await db.commit()

    response = await client.get(f"{PREFIX}/{h['wbs'].wbs_element_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["wbs_element_id"] == str(h["wbs"].wbs_element_id)


@pytest.mark.asyncio
async def test_get_wbs_element_not_found(client: AsyncClient) -> None:
    """GET /wbs-elements/{id} returns 404 for unknown ID."""
    response = await client.get(f"{PREFIX}/{uuid4()}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_wbs_element(
    client: AsyncClient,
    db: AsyncSession,
    actor_id: UUID,
) -> None:
    """PUT /wbs-elements/{id} updates the element."""
    h = await create_full_hierarchy(db, actor_id)
    await db.commit()

    response = await client.put(
        f"{PREFIX}/{h['wbs'].wbs_element_id}",
        json={"name": "Updated WBS Name"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated WBS Name"


@pytest.mark.asyncio
async def test_create_child_wbs_element(
    client: AsyncClient,
    db: AsyncSession,
    actor_id: UUID,
) -> None:
    """Create a child WBS element with parent_wbs_element_id."""
    h = await create_full_hierarchy(db, actor_id)
    await db.commit()

    payload = {
        "project_id": str(h["project"].project_id),
        "code": "1.1",
        "name": "Child WBS Element",
        "level": 2,
        "parent_wbs_element_id": str(h["wbs"].wbs_element_id),
    }
    response = await client.post(PREFIX, json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Child WBS Element"
    assert data["parent_wbs_element_id"] == str(h["wbs"].wbs_element_id)
    assert data["level"] == 2


@pytest.mark.asyncio
async def test_get_wbs_tree(
    client: AsyncClient,
    db: AsyncSession,
    actor_id: UUID,
) -> None:
    """GET /wbs-elements/project/{project_id}/tree returns the WBS tree."""
    h = await create_full_hierarchy(db, actor_id)
    await db.commit()

    response = await client.get(f"{PREFIX}/project/{h['project'].project_id}/tree")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    for item in data:
        assert "wbs_element_id" in item
