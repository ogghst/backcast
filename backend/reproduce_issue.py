
import asyncio
import logging
from datetime import datetime, UTC
from uuid import uuid4

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.services.change_order_service import ChangeOrderService
from app.models.schemas.change_order import ChangeOrderCreate, ChangeOrderUpdate
from app.models.domain.change_order import ChangeOrder

# Helper to setup DB
async def get_session():
    engine = create_async_engine(str(settings.DATABASE_URL))
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    return async_session()

async def reproduce():
    session = await get_session()
    service = ChangeOrderService(session)
    
    # 1. Create a project (mocking ID as we assume one exists or we need to find one)
    # We can query an existing project ID from DB
    from sqlalchemy import select
    from app.models.domain.project import Project
    
    try:
        stmt = select(Project).limit(1)
        res = await session.execute(stmt)
        project = res.scalar_one_or_none()
        
        if not project:
            print("No project found to attach CO to.")
            return

        actor_id = uuid4() # Mock user
        
        print(f"Using Project ID: {project.project_id}")

        # 2. Create Change Order
        co_create = ChangeOrderCreate(
            code=f"CO-TEST-{uuid4().hex[:6]}",
            project_id=project.project_id,
            title="Original Title",
            description="Original Description"
        )
        
        print("Creating Change Order...")
        co = await service.create_change_order(co_create, actor_id=actor_id)
        print(f"Created CO: {co.change_order_id} - Title: {co.title}")
        print(f"Valid Time: {co.valid_time}")

        # 3. Update Change Order Title
        print("Updating Change Order Title...")
        co_update = ChangeOrderUpdate(
            title="Updated Title 222",
            description="Updated Description"
        )
        
        co_id = co.change_order_id
        
        updated_co = await service.update_change_order(
            change_order_id=co_id,
            change_order_in=co_update,
            actor_id=actor_id
        )
        
        print(f"Updated CO: {updated_co.change_order_id} - Title: {updated_co.title}")
        print(f"New Version ID: {updated_co.id}")
        print(f"Valid Time: {updated_co.valid_time}")
        
        # 4. Query DB directly to see rows
        from sqlalchemy import text
        stmt = text("SELECT id, title, valid_time, transaction_time FROM change_orders WHERE change_order_id = :coid ORDER BY transaction_time")
        rows = await session.execute(stmt, {"coid": co_id})
        
        print("\nDB Rows:")
        for row in rows:
            print(f"ID: {row.id}, Title: {row.title}, Valid: {row.valid_time}, Trans: {row.transaction_time}")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await session.close()

if __name__ == "__main__":
    asyncio.run(reproduce())
