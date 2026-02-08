"""Check CO branch naming."""
import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import async_session_maker
from app.models.domain.change_order import ChangeOrder


async def check_co_branch():
    """Check CO branch."""
    async with async_session_maker() as session:
        # Get the change order
        co_stmt = select(ChangeOrder).where(
            ChangeOrder.code == "CO-2026-001"
        )
        co_result = await session.execute(co_stmt)
        cos = co_result.scalars().all()

        print(f"Found {len(cos)} change orders with code CO-2026-001")
        for co in cos:
            expected_branch = f"BR-{co.code}"
            print(f"\nChange Order:")
            print(f"  ID: {co.change_order_id}")
            print(f"  Code: {co.code}")
            print(f"  Branch: {co.branch}")
            print(f"  Expected branch name: {expected_branch}")
            print(f"  Actual UUID-based branch: BR-{co.change_order_id}")


if __name__ == "__main__":
    asyncio.run(check_co_branch())
