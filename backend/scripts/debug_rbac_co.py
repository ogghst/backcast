import asyncio
import logging

# Add backend directory to path
import os
import sys

from sqlalchemy import select

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.db.session import async_session_maker
from app.models.domain.user import User
from app.services.approval_matrix_service import ApprovalMatrixService
from app.services.change_order_service import ChangeOrderService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def debug_rbac():
    async with async_session_maker() as session:
        print("\n--- DEBUGGING RBAC FOR CO-2026-003 ---\n")

        # 1. Fetch the Change Order
        co_service = ChangeOrderService(session)
        co = await co_service.get_current_by_code("CO-2026-003", branch="main")

        if not co:
            print("❌ ERROR: Change Order CO-2026-003 not found!")
            return

        print(f"✅ Found Change Order: {co.code} (ID: {co.change_order_id})")
        print(f"   Status: {co.status}")
        print(f"   Impact Level: {co.impact_level}")
        print(f"   Assigned Approver ID: {co.assigned_approver_id}")

        # 2. Find an Admin User
        stmt = select(User).where(User.role == "admin").limit(1)
        result = await session.execute(stmt)
        admin_user = result.scalar_one_or_none()

        if not admin_user:
            print("❌ ERROR: No admin user found in the database!")
            return

        print(f"\n✅ Found Admin User: {admin_user.full_name} (ID: {admin_user.user_id})")
        print(f"   Role: {admin_user.role}")
        print(f"   Is Active: {admin_user.is_active}")

        # 3. Check Permissions via ApprovalMatrixService
        approval_service = ApprovalMatrixService(session)

        # Check authority levels
        user_authority = approval_service.get_user_authority_level(admin_user)
        print(f"\n   User Authority Level: {user_authority}")

        if co.impact_level:
            required_authority = approval_service.get_authority_for_impact(co.impact_level)
            print(f"   Required Authority for {co.impact_level}: {required_authority}")
        else:
            print("   Change Order has NO IMPACT LEVEL (None)")

        # Check can_approve
        can_approve = await approval_service.can_approve(admin_user, co)
        print(f"\n   can_approve(admin, co) -> {can_approve}")

        if can_approve:
            print("\n✅ SUCCESS: Admin user SHOULD be able to approve this CO.")
        else:
            print("\n❌ FAILURE: Admin user CANNOT approve this CO.")
            if not co.impact_level:
               print("   -> Reason: Impact Level is None")
            elif not admin_user.is_active:
               print("   -> Reason: User is not active")
            else:
               print("   -> Reason: Insufficient authority (Logic check needed)")

if __name__ == "__main__":
    asyncio.run(debug_rbac())
