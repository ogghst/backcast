import asyncio
import os
import sys

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


async def wipe() -> None:
    db_url = os.environ.get("WIPE_DATABASE_URL")
    if not db_url:
        db_url = os.environ.get("DATABASE_URL")

    if not db_url:
        print("Error: WIPE_DATABASE_URL (or DATABASE_URL) not set")
        print(f"Env keys available: {list(os.environ.keys())}")
        sys.exit(1)

    print(f"Wiping DB: {db_url}")
    engine = create_async_engine(db_url)

    async with engine.begin() as conn:
        # Drop all tables by dropping and recreating the public schema
        # This is more reliable than drop_all which can fail with custom types
        try:
            await conn.execute(text("DROP SCHEMA public CASCADE"))
            await conn.execute(text("CREATE SCHEMA public"))
            # Grant permissions to current database user (backcast), not postgres
            await conn.execute(text("GRANT ALL ON SCHEMA public TO current_user"))
            await conn.execute(text("GRANT ALL ON SCHEMA public TO public"))
            print("Dropped and recreated public schema")
        except Exception as e:
            print(f"Error dropping schema: {e}")
            # Fallback to dropping individual tables
            try:
                await conn.execute(text("DROP TABLE IF EXISTS alembic_version CASCADE"))
                # List all tables and drop them
                result = await conn.execute(text(
                    "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
                ))
                tables = [row[0] for row in result]
                for table in tables:
                    await conn.execute(text(f'DROP TABLE IF EXISTS "{table}" CASCADE'))
                print(f"Dropped {len(tables)} tables")
            except Exception as e2:
                print(f"Error in fallback: {e2}")
                raise

    await engine.dispose()
    print("Wipe complete.")


if __name__ == "__main__":
    asyncio.run(wipe())
