#!/usr/bin/env python
"""Repair script for CO-2026-003 approval workflow.

This script recovers a stuck change order by:
1. Completing or skipping the impact analysis
2. Calculating and setting impact level
3. Assigning admin user as approver
4. Creating new version with proper state
5. Approving the change order
"""
import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import get_db
from app.services.change_order_service import ChangeOrderService
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import TSTZRANGE
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.domain.change_order import ChangeOrder
from app.models.domain.user import User
from uuid import UUID
from typing import Any, cast


async def get_current_co_by_code(session: AsyncSession, code: str) -> ChangeOrder | None:
    """Get the current version of a change order by its code.

    Uses temporal query to find the version with an open valid_time upper bound.
    """
    stmt = (
        select(ChangeOrder)
        .where(
            ChangeOrder.code == code,
            ChangeOrder.branch == "main",
            func.upper(cast(Any, ChangeOrder.valid_time)).is_(None),  # Open upper bound
            ChangeOrder.deleted_at.is_(None),
        )
        .order_by(cast(Any, ChangeOrder.valid_time).desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def repair_change_order():
    """Repair CO-2026-003 to make it approvable."""
    async for session in get_db():
        co_service = ChangeOrderService(session)

        # 1. Get admin user
        admin_stmt = select(User).where(
            User.email == "admin@backcast.org",
            User.deleted_at.is_(None)
        )
        admin_result = await session.execute(admin_stmt)
        admin = admin_result.scalar_one_or_none()

        if not admin:
            print("❌ Admin user not found")
            return

        print(f"✅ Found admin: {admin.email} (ID: {admin.id})")

        # 2. Get change order by code (current version)
        co = await get_current_co_by_code(session, "CO-2026-003")

        if not co:
            print("❌ Change order not found")
            return

        print(f"✅ Found CO: {co.code} (ID: {co.change_order_id})")
        print(f"   Status: {co.status}")
        print(f"   Impact Level: {co.impact_level}")
        print(f"   Assigned Approver: {co.assigned_approver_id}")
        print(f"   Impact Analysis: {co.impact_analysis_status}")

        # Capture the IDs before any updates (to avoid stale object issues)
        co_id = co.change_order_id
        admin_id = admin.id

        # 3. Create new version with proper state
        print("\n🔧 Creating new version with proper state...")

        update_data = {
            "status": "Under Review",
            "impact_level": "LOW",  # Adjust based on actual impact
            "assigned_approver_id": admin_id,  # Use 'id' not 'user_id' for FK
            "impact_analysis_status": "skipped",
        }

        updated_co = await co_service.update(
            root_id=co_id,
            actor_id=admin_id,  # Use 'id' for actor_id too
            branch="main",
            **update_data
        )

        print(f"✅ Updated CO status to: {updated_co.status}")

        # Commit the update before approving
        await session.commit()

        # 4. Approve the change order
        print("\n✅ Approving change order...")

        approved_co = await co_service.approve_change_order(
            change_order_id=co_id,  # Use captured ID
            approver_id=admin_id,  # Use 'id' not 'user_id'
            actor_id=admin_id,
            branch="main",
            comments="Recovered from stuck workflow - impact analysis skipped, admin override"
        )

        print(f"✅ Change order approved! Final status: {approved_co.status}")

        # Commit the approval
        await session.commit()
        break


if __name__ == "__main__":
    asyncio.run(repair_change_order())
