"""Service-level tests for CostElementService.

Tests cover CRUD operations (create/update/soft_delete), listing with
filters, get_by_id, history retrieval, time-travel queries, and batch fetch.
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schemas.cost_element import CostElementCreate, CostElementUpdate
from app.services.cost_element_service import CostElementService
from tests.factories import (
    create_full_hierarchy,
)


@pytest.fixture
def service(db: AsyncSession) -> CostElementService:
    return CostElementService(db)


@pytest.mark.asyncio
async def test_create_cost_element_via_service(
    db: AsyncSession, actor_id: UUID, service: CostElementService
) -> None:
    """create_cost_element persists a new EOC under a work package."""
    h = await create_full_hierarchy(db, actor_id)
    await db.commit()

    data = CostElementCreate(
        work_package_id=h["wp"].work_package_id,
        cost_element_type_id=h["ce_type"].cost_element_type_id,
        description="Test cost element",
    )
    ce = await service.create_cost_element(data, actor_id)
    await db.flush()

    assert ce.cost_element_id is not None
    assert ce.work_package_id == h["wp"].work_package_id
    assert ce.cost_element_type_id == h["ce_type"].cost_element_type_id
    assert ce.description == "Test cost element"


@pytest.mark.asyncio
async def test_create_cost_element_invalid_work_package_raises(
    db: AsyncSession, actor_id: UUID, service: CostElementService
) -> None:
    """create_cost_element raises ValueError for non-existent work package."""
    h = await create_full_hierarchy(db, actor_id)
    await db.commit()

    data = CostElementCreate(
        work_package_id=uuid4(),
        cost_element_type_id=h["ce_type"].cost_element_type_id,
    )
    with pytest.raises(ValueError, match="Work Package.*not found"):
        await service.create_cost_element(data, actor_id)


@pytest.mark.asyncio
async def test_create_cost_element_invalid_type_raises(
    db: AsyncSession, actor_id: UUID, service: CostElementService
) -> None:
    """create_cost_element raises ValueError for non-existent CostElementType."""
    h = await create_full_hierarchy(db, actor_id)
    await db.commit()

    data = CostElementCreate(
        work_package_id=h["wp"].work_package_id,
        cost_element_type_id=uuid4(),
    )
    with pytest.raises(ValueError, match="Cost Element Type.*not found"):
        await service.create_cost_element(data, actor_id)


@pytest.mark.asyncio
async def test_update_cost_element(
    db: AsyncSession, actor_id: UUID, service: CostElementService
) -> None:
    """update_cost_element creates a new version with updated description."""
    h = await create_full_hierarchy(db, actor_id)
    await db.commit()

    original_id = h["ce"].cost_element_id

    data = CostElementUpdate(description="Updated EOC")
    updated = await service.update_cost_element(original_id, data, actor_id)
    await db.flush()

    assert updated.cost_element_id == original_id
    assert updated.description == "Updated EOC"


@pytest.mark.asyncio
async def test_soft_delete_cost_element(
    db: AsyncSession, actor_id: UUID, service: CostElementService
) -> None:
    """soft_delete_cost_element marks the cost element as deleted."""
    h = await create_full_hierarchy(db, actor_id)
    await db.commit()

    ce_id = h["ce"].cost_element_id
    await service.soft_delete_cost_element(ce_id, actor_id)
    await db.commit()

    # get_by_id should return None after soft delete
    result = await service.get_by_id(ce_id)
    assert result is None


@pytest.mark.asyncio
async def test_get_by_id(
    db: AsyncSession, actor_id: UUID, service: CostElementService
) -> None:
    """get_by_id returns the current version of a cost element."""
    h = await create_full_hierarchy(db, actor_id)
    await db.commit()

    result = await service.get_by_id(h["ce"].cost_element_id)
    assert result is not None
    assert result.cost_element_id == h["ce"].cost_element_id


@pytest.mark.asyncio
async def test_get_by_id_not_found(
    db: AsyncSession, actor_id: UUID, service: CostElementService
) -> None:
    """get_by_id returns None for unknown cost element."""
    result = await service.get_by_id(uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_get_cost_elements_list(
    db: AsyncSession, actor_id: UUID, service: CostElementService
) -> None:
    """get_cost_elements returns paginated list with total."""
    h = await create_full_hierarchy(db, actor_id)
    await db.commit()

    items, total = await service.get_cost_elements()
    assert total >= 1
    assert any(ce.cost_element_id == h["ce"].cost_element_id for ce in items)


@pytest.mark.asyncio
async def test_get_cost_elements_filter_by_work_package(
    db: AsyncSession, actor_id: UUID, service: CostElementService
) -> None:
    """get_cost_elements filters by work_package_id."""
    h = await create_full_hierarchy(db, actor_id)
    await db.commit()

    items, total = await service.get_cost_elements(
        work_package_id=h["wp"].work_package_id
    )
    assert total >= 1
    assert all(ce.work_package_id == h["wp"].work_package_id for ce in items)

    # Random UUID returns 0
    items2, total2 = await service.get_cost_elements(work_package_id=uuid4())
    assert total2 == 0
    assert items2 == []


@pytest.mark.asyncio
async def test_get_cost_elements_filter_by_type(
    db: AsyncSession, actor_id: UUID, service: CostElementService
) -> None:
    """get_cost_elements filters by cost_element_type_id."""
    h = await create_full_hierarchy(db, actor_id)
    await db.commit()

    items, total = await service.get_cost_elements(
        cost_element_type_id=h["ce_type"].cost_element_type_id
    )
    assert total >= 1

    items2, total2 = await service.get_cost_elements(cost_element_type_id=uuid4())
    assert total2 == 0


@pytest.mark.asyncio
async def test_get_history(
    db: AsyncSession, actor_id: UUID, service: CostElementService
) -> None:
    """get_history returns all versions of a cost element."""
    h = await create_full_hierarchy(db, actor_id)
    await db.commit()

    # Create a new version by updating
    data = CostElementUpdate(description="Updated description")
    await service.update_cost_element(h["ce"].cost_element_id, data, actor_id)
    await db.commit()

    history = await service.get_history(h["ce"].cost_element_id)
    assert len(history) == 2
    # Most recent first
    assert history[0].description == "Updated description"


@pytest.mark.asyncio
async def test_get_cost_element_as_of(
    db: AsyncSession, actor_id: UUID, service: CostElementService
) -> None:
    """get_cost_element_as_of returns the version valid at the given timestamp."""
    h = await create_full_hierarchy(db, actor_id)
    await db.commit()

    # The original is valid from creation, so "as of now" should find it
    now = datetime.now(UTC)
    result = await service.get_cost_element_as_of(h["ce"].cost_element_id, as_of=now)
    assert result is not None
    assert result.cost_element_id == h["ce"].cost_element_id

    # "as of" far future returns the current version (open-ended valid_time)
    future = now + timedelta(days=365)
    result_future = await service.get_cost_element_as_of(
        h["ce"].cost_element_id, as_of=future
    )
    assert result_future is not None


@pytest.mark.asyncio
async def test_get_as_of_batch(
    db: AsyncSession, actor_id: UUID, service: CostElementService
) -> None:
    """get_as_of_batch returns a dict keyed by cost_element_id."""
    h = await create_full_hierarchy(db, actor_id)
    await db.commit()

    result = await service.get_as_of_batch(
        entity_ids=[h["ce"].cost_element_id, uuid4()]
    )
    assert h["ce"].cost_element_id in result
    assert len(result) == 1

    # Empty list returns empty dict
    empty = await service.get_as_of_batch(entity_ids=[])
    assert empty == {}


@pytest.mark.asyncio
async def test_update_cost_element_invalid_type_raises(
    db: AsyncSession, actor_id: UUID, service: CostElementService
) -> None:
    """update_cost_element raises ValueError when changing to non-existent CostElementType."""
    h = await create_full_hierarchy(db, actor_id)
    await db.commit()

    data = CostElementUpdate(cost_element_type_id=uuid4())
    with pytest.raises(ValueError, match="Cost Element Type.*not found"):
        await service.update_cost_element(h["ce"].cost_element_id, data, actor_id)


@pytest.mark.asyncio
async def test_get_as_of_batch_with_time_travel(
    db: AsyncSession, actor_id: UUID, service: CostElementService
) -> None:
    """get_as_of_batch returns entities at a specific timestamp."""
    from datetime import UTC, timedelta

    h = await create_full_hierarchy(db, actor_id)
    await db.commit()

    future = datetime.now(UTC) + timedelta(days=365)
    result = await service.get_as_of_batch(
        entity_ids=[h["ce"].cost_element_id], as_of=future
    )
    assert h["ce"].cost_element_id in result
