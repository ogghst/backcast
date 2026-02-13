import asyncio
import logging
import sys
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Add backend directory to path
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.db.session import async_session_maker
from app.models.domain.change_order import ChangeOrder
from app.models.domain.user import User
from app.services.change_order_workflow_service import ChangeOrderWorkflowService
from app.services.change_order_service import ChangeOrderService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def verify_fix():
    # Use a separate session maker to ensure we can control commit/rollback
    async with async_session_maker() as session:
        print("\n--- VERIFYING FIX FOR CO-2026-003 ---\n")

        # 1. Fetch the Change Order
        co_service = ChangeOrderService(session)
        co = await co_service.get_current_by_code("CO-2026-003", branch="main")
        
        if not co:
            print("❌ ERROR: Change Order CO-2026-003 not found!")
            return

        print(f"✅ Found Change Order: {co.code}")
        print(f"   Status: {co.status}")
        
        # 2. Find an Admin User
        stmt = select(User).where(User.role == "admin").limit(1)
        result = await session.execute(stmt)
        admin_user = result.scalar_one_or_none()

        if not admin_user:
            print("❌ ERROR: No admin user found!")
            return

        print(f"✅ Found Admin User: {admin_user.full_name}")

        # 3. Attempt Approval
        workflow_service = ChangeOrderWorkflowService()
        print("\n🚀 Attempting to approve Change Order...")
        
        try:
            # We use the session directly implicitly via the services
            # workflow_service methods take db_session as argument
            updated_co = await workflow_service.approve_change_order(
                change_order_id=co.change_order_id,
                actor_id=admin_user.user_id,
                comments="Verification test - approval from Under Review",
                db_session=session
            )
            
            print(f"✅ SUCCESS! Change Order approved. New Status: {updated_co.status}")
            
            # 4. Rollback to keep data clean
            print("🔄 Rolling back transaction to preserve state...")
            await session.rollback()
            print("✅ Rollback complete.")
            
        except Exception as e:
            print(f"❌ FAILED to approve: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(verify_fix())
