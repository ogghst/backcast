import asyncio
import os
import sys

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


async def create_db_if_not_exists(original_url: str, test_url: str) -> None:
    db_name = test_url.rstrip("/").split("/")[-1]
    engine = create_async_engine(original_url, isolation_level="AUTOCOMMIT")
    async with engine.connect() as conn:
        result = await conn.execute(text(f"SELECT 1 FROM pg_database WHERE datname = '{db_name}'"))
        exists = result.scalar() is not None
        if not exists:
            print(f"Creating test database: {db_name}")
            await conn.execute(text(f"CREATE DATABASE {db_name}"))
    await engine.dispose()


async def wipe() -> None:
    db_url = os.environ.get("WIPE_DATABASE_URL")
    orig_url = os.environ.get("ORIGINAL_DATABASE_URL")

    if not db_url:
        db_url = os.environ.get("DATABASE_URL")

    if not db_url:
        print("Error: WIPE_DATABASE_URL (or DATABASE_URL) not set")
        print(f"Env keys available: {list(os.environ.keys())}")
        sys.exit(1)

    if orig_url and orig_url != db_url:
        await create_db_if_not_exists(orig_url, db_url)

    print(f"Wiping DB: {db_url}")
    engine = create_async_engine(db_url)

    async with engine.begin() as conn:
        # Drop all tables by dropping and recreating the public schema
        # This is more reliable than drop_all which can fail with custom types
        try:
            # First, drop all custom types in the public schema to avoid conflicts
            result = await conn.execute(
                text("""
                    SELECT typname
                    FROM pg_type
                    WHERE typtype = 'e'
                    AND typnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')
                """)
            )
            enum_types = [row[0] for row in result]
            for enum_type in enum_types:
                try:
                    await conn.execute(text(f'DROP TYPE IF EXISTS "{enum_type}" CASCADE'))
                    print(f"Dropped enum type: {enum_type}")
                except Exception as e:
                    print(f"Warning: Could not drop type {enum_type}: {e}")

            # Now drop and recreate the public schema
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
                result = await conn.execute(
                    text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
                )
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
