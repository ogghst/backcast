import asyncio
import logging
from uuid import UUID

from app.db.database import AsyncSessionLocal
from sqlalchemy import select

from app.models.domain.change_order import ChangeOrder
from app.services.change_order_service import ChangeOrderService

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(message)s")


async def test_approve():
    async with AsyncSessionLocal() as session:
        # Get change order
        stmt = select(ChangeOrder).where(ChangeOrder.code == "CO-2026-001").limit(1)
        co = (await session.execute(stmt)).scalar_one_or_none()
        if not co:
            print("CO-2026-001 not found")
            return

        co_id = co.change_order_id
        admin_id = UUID("e03556f3-4385-5d68-a685-af307fc8af5c")

        print(f"Approving CO {co_id} (code {co.code}) with admin ID {admin_id}")

        service = ChangeOrderService(session)
        try:
            res = await service.approve_change_order(
                change_order_id=co_id,
                approver_id=admin_id,
                actor_id=admin_id,
                branch="main",
                comments="Test override",
            )
            print(f"Success! Status is now {res.status}")
        except Exception as e:
            print(f"Failed: {type(e).__name__} - {e}")


if __name__ == "__main__":
    asyncio.run(test_approve())
