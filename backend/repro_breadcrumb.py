import asyncio
from uuid import UUID
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.services.wbe import WBEService
from app.core.versioning.enums import BranchMode
import json
import os

async def repro():
    # Database URL
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/backcast_evs")
    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        service = WBEService(session)
        
        # We need a level 2 WBE ID from the seed data
        # L2 WBE 1.1 in Demo Project 1
        wbe_id = UUID("da6e1632-20b0-536d-b16f-b60a37fb5dc8")
        
        try:
            breadcrumb = await service.get_breadcrumb(wbe_id, branch="main", branch_mode=BranchMode.MERGE)
            print("Breadcrumb for Level 2 WBE (da6e...):")
            print(json.dumps(breadcrumb, indent=2, default=str))
            
            # Also check a Level 1 WBE
            l1_id = UUID("3a42f62c-96f8-5392-bff1-2e16f97734f0")
            breadcrumb_l1 = await service.get_breadcrumb(l1_id, branch="main", branch_mode=BranchMode.MERGE)
            print("\nBreadcrumb for Level 1 WBE (3a42...):")
            print(json.dumps(breadcrumb_l1, indent=2, default=str))
            
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(repro())
