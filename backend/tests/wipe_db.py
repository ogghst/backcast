import asyncio
import os
import sys

from sqlalchemy import MetaData, text
from sqlalchemy.ext.asyncio import create_async_engine


async def wipe():
    db_url = os.environ.get("WIPE_DATABASE_URL")
    if not db_url:
        print("Error: WIPE_DATABASE_URL not set")
        sys.exit(1)

    print(f"Wiping DB: {db_url}")
    engine = create_async_engine(db_url)

    async with engine.begin() as conn:
        meta = MetaData()
        await conn.run_sync(meta.reflect)
        await conn.run_sync(meta.drop_all)
        await conn.execute(text("DROP TABLE IF EXISTS alembic_version"))

    await engine.dispose()
    print("Wipe complete.")


if __name__ == "__main__":
    asyncio.run(wipe())
