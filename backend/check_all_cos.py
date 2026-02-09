"""Check all change orders."""
import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import async_session_maker
from app.models.domain.change_order import ChangeOrder


async def check_all_cos():
    """Check all COs."""
    async with async_session_maker() as session:
        # Get all change orders
        co_stmt = select(ChangeOrder).order_by(ChangeOrder.code)
        co_result = await session.execute(co_stmt)
        cos = co_result.scalars().all()

        print(f"Found {len(cos)} change orders:")
        for co in cos:
            expected_branch = f"BR-{co.code}"
            print(f"\n  Code: {co.code}")
            print(f"    ID: {co.change_order_id}")
            print(f"    Project ID: {co.project_id}")
            print(f"    Expected branch: {expected_branch}")


if __name__ == "__main__":
    asyncio.run(check_all_cos())
