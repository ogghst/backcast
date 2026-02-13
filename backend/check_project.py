"""Check project data in database."""
import asyncio
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import async_session_maker
from app.models.domain.change_order import ChangeOrder
from app.models.domain.wbe import WBE


async def check_project_data():
    """Check all WBEs for the project."""
    async with async_session_maker() as session:
        # Get the change order
        co_stmt = select(ChangeOrder).where(
            ChangeOrder.code == "CO-2026-001",
            ChangeOrder.branch == "main"
        )
        co_result = await session.execute(co_stmt)
        co = co_result.scalar_one_or_none()

        if not co:
            print("Change Order CO-2026-001 not found")
            return

        print(f"Project ID: {co.project_id}")

        # Get ALL WBEs for this project (any branch, any time)
        all_wbe_stmt = select(WBE).where(
            WBE.project_id == co.project_id
        ).order_by(WBE.branch, WBE.wbe_id)
        all_wbe_result = await session.execute(all_wbe_stmt)
        all_wbes = all_wbe_result.scalars().all()

        print(f"\nALL WBEs for project: {len(all_wbes)}")
        for wbe in all_wbes:
            print(f"  - ID: {wbe.wbe_id}, Branch: {wbe.branch}, Name: {wbe.name}")
            print(f"    Budget: {wbe.budget_allocation}, valid_time: {wbe.valid_time}, deleted_at: {wbe.deleted_at}")


if __name__ == "__main__":
    asyncio.run(check_project_data())
