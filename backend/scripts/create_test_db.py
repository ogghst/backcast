import asyncio
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def create_test_database():
    """Create the test database if it doesn't exist."""
    # Get the default database URL (usually postgres)
    # We replace the database name with 'postgres' to connect to the system DB
    db_url = str(settings.DATABASE_URL)

    # Simple parsing to replace dbname
    # Assuming format: postgresql+asyncpg://user:pass@host:port/dbname
    base_url = db_url.rsplit("/", 1)[0]
    postgres_url = f"{base_url}/postgres"

    test_db_name = "backcast_evs_test"

    logger.info(f"Connecting to {postgres_url} to check/create {test_db_name}")

    engine = create_async_engine(postgres_url, isolation_level="AUTOCOMMIT")

    async with engine.connect() as conn:
        # Check if database exists
        result = await conn.execute(
            text(f"SELECT 1 FROM pg_database WHERE datname = '{test_db_name}'")
        )
        exists = result.scalar()

        if not exists:
            logger.info(f"Database {test_db_name} does not exist. Creating...")
            await conn.execute(text(f"CREATE DATABASE {test_db_name}"))
            logger.info(f"Database {test_db_name} created successfully.")
        else:
            logger.info(f"Database {test_db_name} already exists.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(create_test_database())
