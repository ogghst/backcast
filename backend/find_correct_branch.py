"""Find the correct branch."""
import asyncio
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import async_session_maker
from app.models.domain.change_order import ChangeOrder
from app.models.domain.wbe import WBE


async def find_correct_branch():
    """Find correct branch."""
    async with async_session_maker() as session:
        # Get CO-2026-001
        co_stmt = select(ChangeOrder).where(
            ChangeOrder.code == "CO-2026-001",
            ChangeOrder.branch == "main"
        )
        co_result = await session.execute(co_stmt)
        co = co_result.scalar_one_or_none()

        if not co:
            print("Change Order CO-2026-001 not found")
            return

        expected_branch = f"co-{co.code}"
        print(f"Expected branch: {expected_branch}")

        # Check if any WBEs exist with that branch
        wbe_stmt = select(WBE).where(
            WBE.project_id == co.project_id,
            WBE.branch == expected_branch,
            func.upper(WBE.valid_time).is_(None),
            WBE.deleted_at.is_(None),
        )
        wbe_result = await session.execute(wbe_stmt)
        wbes = wbe_result.scalars().all()

        print(f"Found {len(wbes)} WBEs in branch {expected_branch}")
        if wbes:
            budget = sum(w.budget_allocation for w in wbes)
            print(f"Total budget: {budget}")

        # Check what the actual issue is - the co-xxx branches are project-based
        print("\nActual branches in database:")
        all_wbes_stmt = select(WBE).where(
            WBE.project_id == co.project_id,
            func.upper(WBE.valid_time).is_(None),
            WBE.deleted_at.is_(None),
        )
        all_wbes_result = await session.execute(all_wbes_stmt)
        all_wbes = all_wbes_result.scalars().all()

        branches = set(w.branch for w in all_wbes)
        for branch in sorted(branches):
            if branch.startswith("co-"):
                branch_wbes = [w for w in all_wbes if w.branch == branch]
                budget = sum(w.budget_allocation for w in branch_wbes)
                print(f"  {branch}: {budget} ({len(branch_wbes)} WBEs)")


if __name__ == "__main__":
    asyncio.run(find_correct_branch())
