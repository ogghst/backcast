"""Check CO-2026-001 data in database."""
import asyncio
from decimal import Decimal
from sqlalchemy import select, func, cast, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import async_session_maker
from app.models.domain.change_order import ChangeOrder
from app.models.domain.wbe import WBE


async def check_co_data():
    """Check CO-2026-001 data."""
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

        print(f"Change Order ID: {co.change_order_id}")
        print(f"Project ID: {co.project_id}")
        print(f"Code: {co.code}")

        # Get main branch WBEs
        main_wbe_stmt = select(WBE).where(
            WBE.project_id == co.project_id,
            WBE.branch == "main",
            WBE.valid_time.is_(None),  # Upper bound is null
            WBE.deleted_at.is_(None),
        )
        main_wbe_result = await session.execute(main_wbe_stmt)
        main_wbes = main_wbe_result.scalars().all()

        print(f"\nMain branch WBEs: {len(main_wbes)}")
        main_budget = Decimal("0")
        for wbe in main_wbes:
            print(f"  - {wbe.name}: {wbe.budget_allocation}")
            main_budget += wbe.budget_allocation
        print(f"Main total budget: {main_budget}")

        # Get change branch WBEs
        branch_name = f"co-{co.code}"
        change_wbe_stmt = select(WBE).where(
            WBE.project_id == co.project_id,
            WBE.branch == branch_name,
            WBE.valid_time.is_(None),  # Upper bound is null
            WBE.deleted_at.is_(None),
        )
        change_wbe_result = await session.execute(change_wbe_stmt)
        change_wbes = change_wbe_result.scalars().all()

        print(f"\n{branch_name} branch WBEs: {len(change_wbes)}")
        change_budget = Decimal("0")
        for wbe in change_wbes:
            print(f"  - {wbe.name}: {wbe.budget_allocation}")
            change_budget += wbe.budget_allocation
        print(f"{branch_name} total budget: {change_budget}")

        print(f"\nDelta: {change_budget - main_budget}")
        print(f"Expected merged: {main_budget + (change_budget - main_budget)}")


if __name__ == "__main__":
    asyncio.run(check_co_data())
