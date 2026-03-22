#!/usr/bin/env python3
"""Script to seed AI tools test data.

Run this script to load comprehensive test data for AI tools testing.
Usage:
    cd backend
    source .venv/bin/activate
    python -m app.db.scripts.seed_ai_tools_test_data
"""

import asyncio
import logging
import sys

from app.db.ai_tools_seeder import AIToolsTestDataSeeder
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
    logger.info("Starting AI Tools Test Data seeding...")

    try:
        # Create database session
        async with async_session_maker() as session:
            try:
                # Create seeder instance
                seeder = AIToolsTestDataSeeder()

                # Seed all data
                await seeder.seed_all(session)

                logger.info("✓ AI Tools Test Data seeded successfully!")
                logger.info("\nYou can now test AI tools with this data:")
                logger.info("  Project: AI-TEST-001 (AI Test Project 2026)")
                logger.info("  Cost Elements: 4 (CE-CONV-MAIN, CE-CONV-SEC, CE-PANEL-MAIN, CE-CTRL-SYS)")
                logger.info("  WBEs: 7 (3-level hierarchy)")
                logger.info("  Cost Registrations: 8")
                logger.info("  Progress Entries: 9")
                logger.info("  Forecasts: 4")

            except Exception as e:
                logger.error(f"Failed to seed AI tools test data: {e}")
                raise

    except Exception as e:
        logger.error(f"Fatal error during seeding: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
