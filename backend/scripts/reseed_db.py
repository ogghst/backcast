#!/usr/bin/env python3
import asyncio
import logging
import sys
from pathlib import Path

# Add the backend directory to sys.path to allow importing app
backend_dir = Path(__file__).parent.parent
sys.path.append(str(backend_dir))

from sqlalchemy import text
from app.db.session import async_session_maker, engine
from app.db.seeder import DataSeeder
from app.core.logging import setup_logging

logger = logging.getLogger(__name__)

async def clear_database():
    """Truncate all tables except alembic_version."""
    async with async_session_maker() as session:
        # Get all table names in public schema except alembic_version
        result = await session.execute(
            text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name != 'alembic_version'")
        )
        tables = [row[0] for row in result.fetchall()]
        
        if not tables:
            logger.info("No tables found to truncate.")
            return

        # Truncate all tables with CASCADE to handle foreign keys
        truncate_query = f"TRUNCATE TABLE {', '.join(tables)} CASCADE"
        logger.info(f"Truncating tables: {', '.join(tables)}")
        await session.execute(text(truncate_query))
        await session.commit()
    logger.info("Database cleared successfully.")

async def reseed_database():
    """Seed the database with initial data."""
    async with async_session_maker() as session:
        seeder = DataSeeder()
        await seeder.seed_all(session)
    logger.info("Database reseeded successfully.")

async def main():
    setup_logging()
    
    print("WARNING: This will clear all data in the database!")
    confirm = input("Are you sure you want to continue? [y/N]: ")
    if confirm.lower() != 'y':
        print("Aborted.")
        return

    try:
        await clear_database()
        await reseed_database()
        print("Success: Database cleared and reseeded.")
    except Exception as e:
        logger.error(f"Error during reseed: {e}")
        print(f"Error: {e}")
        sys.exit(1)
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
