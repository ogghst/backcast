"""Database seeding entry point.

Run with: python -m app.db
"""

import asyncio
import logging
import sys

from app.db.seeder import DataSeeder
from app.db.session import async_session_maker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)


async def main() -> None:
    """Main seeding function."""
    logger.info("Starting database seeding process...")

    try:
        # Create database session
        async with async_session_maker() as session:
            # Create seeder instance
            seeder = DataSeeder()

            # Run all seeding operations
            await seeder.seed_all(session)

            logger.info("Database seeding completed successfully!")

    except Exception as e:
        logger.error(f"Database seeding failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
