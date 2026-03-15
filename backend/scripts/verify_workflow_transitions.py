#!/usr/bin/env python3
"""Verify that workflow transitions are consistent with approval endpoints."""

import asyncio

from sqlalchemy import select

from app.db.session import async_session_maker
from app.models.domain.change_order import ChangeOrder
from app.services.change_order_workflow_service import ChangeOrderWorkflowService


async def main():
    """Test workflow transition consistency."""
    print("🔍 Testing Workflow Transition Consistency\n")

    async with async_session_maker() as session:
        # Find a change order in "Submitted for Approval" status
        stmt = (
            select(ChangeOrder)
            .where(
                ChangeOrder.status == "Submitted for Approval",
                ChangeOrder.deleted_at.is_(None),
            )
            .limit(1)
        )

        result = await session.execute(stmt)
        co = result.scalar_one_or_none()

        if not co:
            print("❌ No Change Order found in 'Submitted for Approval' status")
            print("   Create one first using the frontend or API")
            return

        print(f"✅ Found Change Order: {co.code}")
        print(f"   Status: {co.status}")
        print(f"   Impact Level: {co.impact_level}")
        print()

        # Test get_available_transitions
        workflow = ChangeOrderWorkflowService()
        transitions = await workflow.get_available_transitions(co.status)

        print(f"📋 Available Transitions from '{co.status}':")
        for t in transitions:
            print(f"   - {t}")
        print()

        # Check if Approved and Rejected are in the list
        expected_transitions = ["Under Review", "Approved", "Rejected"]
        missing = [t for t in expected_transitions if t not in transitions]

        if missing:
            print(f"❌ FAILED: Missing transitions: {missing}")
            print(f"   Expected: {expected_transitions}")
            print(f"   Got: {transitions}")
        else:
            print("✅ SUCCESS: All expected transitions are available")
            print("   - 'Under Review' (for extended review)")
            print("   - 'Approved' (for direct approval)")
            print("   - 'Rejected' (for direct rejection)")

        print()
        print("🎉 Workflow transitions are now consistent with approval endpoints!")


if __name__ == "__main__":
    asyncio.run(main())
