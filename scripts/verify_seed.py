import asyncio
import sys
import logging
from pathlib import Path
from sqlalchemy import select, func

# Add backend to path
root_dir = Path(__file__).resolve().parent.parent
backend_dir = root_dir / "backend"
sys.path.append(str(backend_dir))

from app.db.session import async_session_maker
from app.models.domain.project import Project
from app.models.domain.wbe import WBE
from app.models.domain.cost_element import CostElement
from app.models.domain.cost_element_type import CostElementType
from app.models.domain.department import Department
from app.models.domain.user import User

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    async with async_session_maker() as session:
        # Check Departments
        result = await session.execute(select(Department))
        depts = result.scalars().all()
        logger.info(f"Departments count: {len(depts)}")
        for d in depts:
            logger.info(f" - {d.code}: {d.name}")

        # Check Users
        result = await session.execute(select(User))
        users = result.scalars().all()
        logger.info(f"Users count: {len(users)}")
        for u in users:
            logger.info(f" - {u.email} ({u.role}) Dept: {u.department}")

        # Check CE Types
        result = await session.execute(select(CostElementType))
        ce_types = result.scalars().all()
        logger.info(f"Cost Element Types count: {len(ce_types)}")
        for cet in ce_types:
            # We need to manually match department since it's lazy loaded or just ID
            # Let's just print ID or try to find name from depts list
            d_name = next((d.code for d in depts if d.id == cet.department_id), "UNKNOWN")
            logger.info(f" - {cet.code}: {cet.name} (Dept: {d_name})")

        # Check Projects
        result = await session.execute(select(func.count(Project.id)))
        proj_count = result.scalar()
        logger.info(f"Projects count: {proj_count}")
        
        # Details of PRJ-DEMO
        stmt = select(Project).where(Project.code.like('PRJ-DEMO%'))
        result = await session.execute(stmt)
        projects = result.scalars().all()
        
        for p in projects:
            # Count WBEs
            wbes_res = await session.execute(select(func.count(WBE.id)).where(WBE.project_id == p.project_id))
            wbe_count = wbes_res.scalar()
            
            # Count Cost Elements
            stmt_ce = select(func.count(CostElement.id)).join(WBE, CostElement.wbe_id == WBE.wbe_id).where(WBE.project_id == p.project_id)
            ce_res = await session.execute(stmt_ce)
            ce_count = ce_res.scalar()
            logger.info(f"Project {p.code}: {wbe_count} WBEs, {ce_count} Cost Elements")

if __name__ == "__main__":
    asyncio.run(main())
