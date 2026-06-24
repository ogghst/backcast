"""Tests for ChangeOrderService.

Covers created_by_name population on read paths (get_change_orders list).
"""

from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schemas.change_order import ChangeOrderCreate
from app.services.change_order_service import ChangeOrderService
from tests.factories import create_test_project


@pytest.mark.asyncio
async def test_get_change_orders_populates_created_by_name(
    db: AsyncSession, actor_id: UUID
) -> None:
    """get_change_orders should populate created_by_name on each change order."""
    project = await create_test_project(db, actor_id)
    await db.commit()

    service = ChangeOrderService(db)
    co = await service.create_change_order(
        change_order_in=ChangeOrderCreate(
            code="CO-CBN-001",
            project_id=project.project_id,
            title="Creator name test",
        ),
        actor_id=actor_id,
    )
    await db.commit()
    assert co.change_order_id is not None

    change_orders, _total = await service.get_change_orders(
        project_id=project.project_id
    )
    assert len(change_orders) >= 1
    assert all(hasattr(c, "created_by_name") for c in change_orders)
    assert any(c.created_by_name == "Admin User" for c in change_orders)
