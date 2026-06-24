"""Tests for CostElementTypeService.

Covers created_by_name population on read paths (get_by_id, list).
"""

from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.cost_element_type_service import CostElementTypeService
from tests.factories import create_full_hierarchy


@pytest.mark.asyncio
async def test_get_by_id_populates_created_by_name(
    db: AsyncSession, actor_id: UUID
) -> None:
    """get_by_id should populate created_by_name from the creator user."""
    h = await create_full_hierarchy(db, actor_id)
    await db.commit()

    service = CostElementTypeService(db)
    found = await service.get_by_id(h["ce_type"].cost_element_type_id)
    assert found is not None
    assert found.created_by_name == "Admin User"


@pytest.mark.asyncio
async def test_get_cost_element_types_populates_created_by_name(
    db: AsyncSession, actor_id: UUID
) -> None:
    """get_cost_element_types should populate created_by_name on each item."""
    await create_full_hierarchy(db, actor_id)
    await db.commit()

    service = CostElementTypeService(db)
    items, _total = await service.get_cost_element_types()
    assert len(items) >= 1
    assert all(hasattr(i, "created_by_name") for i in items)
    assert any(i.created_by_name == "Admin User" for i in items)
