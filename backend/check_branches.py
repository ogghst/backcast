"""Check what branches exist for this project."""
import asyncio
from sqlalchemy import select, func, cast, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import async_session_maker
from app.models.domain.change_order import ChangeOrder
from app.models.domain.wbe import WBE


async def check_branches():
    """Check all branches."""
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
        print(f"Expected change branch: BR-{co.code}")

        # Get ALL current WBEs (where upper bound of valid_time is null)
        current_wbes_stmt = select(WBE).where(
            WBE.project_id == co.project_id,
            func.upper(cast(Any, WBE).valid_time).is_(None),
            cast(Any, WBE).deleted_at.is_(None),
        )
        current_wbes_result = await session.execute(current_wbes_stmt)
        current_wbes = current_wbes_result.scalars().all()

        print(f"\nCurrent WBEs (valid_time upper is null): {len(current_wbes)}")
        branches = set()
        for wbe in current_wbes:
            branches.add(wbe.branch)
            print(f"  - Branch: {wbe.branch}, Name: {wbe.name}, Budget: {wbe.budget_allocation}")

        print(f"\nUnique branches: {sorted(branches)}")

        # Now calculate budgets per branch
        print("\nBudgets per branch:")
        for branch in sorted(branches):
            branch_wbes = [w for w in current_wbes if w.branch == branch]
            budget = sum(w.budget_allocation for w in branch_wbes)
            print(f"  {branch}: {budget} ({len(branch_wbes)} WBEs)")


if __name__ == "__main__":
    asyncio.run(check_branches())
