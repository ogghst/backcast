"""Check branch content for CO-2026-001."""
import asyncio
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import async_session_maker
from app.models.domain.change_order import ChangeOrder
from app.models.domain.wbe import WBE


async def check_branches():
    """Check branch content."""
    async with async_session_maker() as session:
        # Get CO-2026-001
        co_stmt = select(ChangeOrder).where(
            ChangeOrder.code == "CO-2026-001"
        )
        co_result = await session.execute(co_stmt)
        co = co_result.scalar_one_or_none()

        if not co:
            print("Change Order CO-2026-001 not found")
            return

        print(f"Change Order: {co.code}")
        print(f"Project ID: {co.project_id}")
        print(f"Expected branch: BR-CO-2026-001")
        print()

        # Check main branch
        print("=" * 60)
        print("MAIN BRANCH")
        print("=" * 60)
        main_wbe_stmt = select(WBE).where(
            WBE.project_id == co.project_id,
            WBE.branch == "main",
            func.upper(WBE.valid_time).is_(None),
            WBE.deleted_at.is_(None),
        )
        main_wbe_result = await session.execute(main_wbe_stmt)
        main_wbes = main_wbe_result.scalars().all()

        print(f"Count: {len(main_wbes)} WBEs")
        main_budget = sum(w.budget_allocation for w in main_wbes)
        print(f"Total Budget: {main_budget}")
        print(f"WBEs:")
        for wbe in main_wbes:
            print(f"  - {wbe.code}: {wbe.budget_allocation}")
        print()

        # Check BR-CO-2026-001 branch
        print("=" * 60)
        print("BR-CO-2026-001 BRANCH")
        print("=" * 60)
        co_wbe_stmt = select(WBE).where(
            WBE.project_id == co.project_id,
            WBE.branch == "BR-CO-2026-001",
            func.upper(WBE.valid_time).is_(None),
            WBE.deleted_at.is_(None),
        )
        co_wbe_result = await session.execute(co_wbe_stmt)
        co_wbes = co_wbe_result.scalars().all()

        print(f"Count: {len(co_wbes)} WBEs")
        if co_wbes:
            co_budget = sum(w.budget_allocation for w in co_wbes)
            print(f"Total Budget: {co_budget}")
            print(f"WBEs:")
            for wbe in co_wbes:
                print(f"  - {wbe.code}: {wbe.budget_allocation}")
        else:
            print("BRANCH IS EMPTY OR DOES NOT EXIST")
        print()

        # Check ALL branches for this project
        print("=" * 60)
        print("ALL BRANCHES FOR THIS PROJECT")
        print("=" * 60)
        all_wbe_stmt = select(WBE).where(
            WBE.project_id == co.project_id,
            func.upper(WBE.valid_time).is_(None),
            WBE.deleted_at.is_(None),
        )
        all_wbe_result = await session.execute(all_wbe_stmt)
        all_wbes = all_wbe_result.scalars().all()

        branches = {}
        for wbe in all_wbes:
            if wbe.branch not in branches:
                branches[wbe.branch] = []
            branches[wbe.branch].append(wbe)

        for branch in sorted(branches.keys()):
            branch_wbes = branches[branch]
            budget = sum(w.budget_allocation for w in branch_wbes)
            print(f"{branch}: {budget} ({len(branch_wbes)} WBEs)")


if __name__ == "__main__":
    asyncio.run(check_branches())
