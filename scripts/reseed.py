import asyncio
import sys
import logging
from pathlib import Path

# Add backend to path
root_dir = Path(__file__).resolve().parent.parent
backend_dir = root_dir / "backend"
sys.path.append(str(backend_dir))

from app.db.session import async_session_maker
from app.db.seeder import DataSeeder

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    logger.info("Starting re-seeding...")
    async with async_session_maker() as session:
        seeder = DataSeeder()
        await seeder.seed_all(session)
    logger.info("Re-seeding complete.")

if __name__ == "__main__":
    asyncio.run(main())
