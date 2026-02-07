#!/usr/bin/env python3
"""Debug script to check WBEs on different branches."""

import asyncio
from sqlalchemy import select, func, cast, Any
from app.models.domain.wbe import WBE
from app.db.session import async_session_maker


async def check_wbe_branches():
    """Check WBEs on CO-2026-003 branch vs main branch."""
    async with async_session_maker() as session:
        # Check if WBEs exist on CO-2026-003 branch
        change_branch_stmt = select(WBE).where(
            WBE.branch == 'co-CO-2026-003',
            func.upper(cast(Any, WBE).valid_time).is_(None),
            cast(Any, WBE).deleted_at.is_(None),
        )
        result = await session.execute(change_branch_stmt)
        wbes = result.scalars().all()

        print(f'WBEs on co-CO-2026-003 branch: {len(wbes)}')
        for wbe in wbes:
            print(f'  - {wbe.name}: budget={wbe.budget_allocation}, id={wbe.wbe_id}')

        # Check main branch for the same project
        if wbes:
            project_id = wbes[0].project_id
            main_stmt = select(WBE).where(
                WBE.project_id == project_id,
                WBE.branch == 'main',
                func.upper(cast(Any, WBE).valid_time).is_(None),
                cast(Any, WBE).deleted_at.is_(None),
            )
            main_result = await session.execute(main_stmt)
            main_wbes = main_result.scalars().all()

            print(f'\nWBEs on main branch for same project: {len(main_wbes)}')
            for wbe in main_wbes:
                print(f'  - {wbe.name}: budget={wbe.budget_allocation}, id={wbe.wbe_id}')

            # Compare budgets
            print('\nBudget comparison:')
            main_budgets = {wbe.wbe_id: wbe.budget_allocation for wbe in main_wbes}
            change_budgets = {wbe.wbe_id: wbe.budget_allocation for wbe in wbes}

            for wbe_id in set(list(main_budgets.keys()) + list(change_budgets.keys())):
                main_budget = main_budgets.get(wbe_id)
                change_budget = change_budgets.get(wbe_id)

                if main_budget != change_budget:
                    print(f'  - WBE {wbe_id}: main={main_budget}, change={change_budget}, delta={change_budget - main_budget if main_budget else change_budget}')


if __name__ == '__main__':
    asyncio.run(check_wbe_branches())
