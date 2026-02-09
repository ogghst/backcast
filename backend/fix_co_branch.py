"""Fix CO-2026-001 by creating the correct branch."""
import asyncio
from datetime import datetime, UTC
from decimal import Decimal
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import async_session_maker
from app.models.domain.change_order import ChangeOrder
from app.models.domain.wbe import WBE
from uuid import UUID


async def fix_co_branch():
    """Fix CO-2026-001 branch."""
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

        expected_branch = f"BR-{co.code}"
        print(f"Creating branch: {expected_branch}")
        print(f"Project ID: {co.project_id}")

        # Get main branch WBEs
        main_wbe_stmt = select(WBE).where(
            WBE.project_id == co.project_id,
            WBE.branch == "main",
            func.upper(WBE.valid_time).is_(None),
            WBE.deleted_at.is_(None),
        )
        main_wbe_result = await session.execute(main_wbe_stmt)
        main_wbes = main_wbe_result.scalars().all()

        print(f"\nMain branch has {len(main_wbes)} WBEs")
        print("Copying them to the change branch...")

        # Use a system user ID for created_by (you may need to adjust this)
        system_user_id = UUID("00000000-0000-0000-0000-000000000000")  # Placeholder

        # Copy each WBE to the change branch using clone()
        for main_wbe in main_wbes:
            # Clone the WBE to the new branch
            new_wbe = main_wbe.clone(
                branch=expected_branch,  # NEW BRANCH
                created_by=system_user_id,
            )
            session.add(new_wbe)
            print(f"  + Created {main_wbe.name} in {expected_branch}")

        await session.commit()
        print(f"\n✓ Successfully created {len(main_wbes)} WBEs in branch {expected_branch}")

        # Verify
        verify_stmt = select(WBE).where(
            WBE.project_id == co.project_id,
            WBE.branch == expected_branch,
            func.upper(WBE.valid_time).is_(None),
            WBE.deleted_at.is_(None),
        )
        verify_result = await session.execute(verify_stmt)
        verify_wbes = verify_result.scalars().all()

        verify_budget = sum(w.budget_allocation for w in verify_wbes)
        print(f"Verification: {len(verify_wbes)} WBEs with total budget {verify_budget}")


if __name__ == "__main__":
    asyncio.run(fix_co_branch())
