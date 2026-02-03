#!/usr/bin/env python3
"""Quick database connection check for development environment."""

import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def check_database_connection():
    """Test database connection using asyncpg."""
    try:
        import asyncpg

        # Get database connection parameters
        db_user = os.getenv("POSTGRES_USER", "postgres")
        db_password = os.getenv("POSTGRES_PASSWORD", "postgres")
        db_server = os.getenv("POSTGRES_SERVER", "localhost")
        db_port = os.getenv("POSTGRES_PORT", "5432")
        db_name = os.getenv("POSTGRES_DB", "backcast_evs")

        print("=" * 60)
        print("Database Connection Check")
        print("=" * 60)
        print(f"Server: {db_server}:{db_port}")
        print(f"Database: {db_name}")
        print(f"User: {db_user}")
        print("-" * 60)

        # Attempt connection
        print("Attempting connection...")
        conn = await asyncpg.connect(
            user=db_user,
            password=db_password,
            database=db_name,
            host=db_server,
            port=int(db_port)
        )

        print("✅ Successfully connected to database!")

        # Get database version
        version = await conn.fetchval('SELECT version()')
        print(f"\nPostgreSQL Version:")
        print(f"  {version.split(',')[0]}")

        # Check if tables exist
        tables = await conn.fetch("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name
            LIMIT 10;
        """)

        print(f"\nFound {len(tables)} tables (showing first 10):")
        for table in tables:
            print(f"  - {table['table_name']}")

        # Check count of critical tables
        critical_tables = ['projects', 'wbes', 'cost_elements', 'users', 'departments']
        print(f"\nChecking critical tables:")
        for table_name in critical_tables:
            count = await conn.fetchval(f"""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name = '{table_name}'
                );
            """)
            status = "✅" if count else "❌"
            print(f"  {status} {table_name}")

        # Close connection
        await conn.close()
        print("\n" + "=" * 60)
        print("✅ Database connection test completed successfully!")
        print("=" * 60)

        return True

    except ImportError as e:
        print("❌ Error: asyncpg not installed")
        print(f"   {e}")
        print("\nTry: uv add asyncpg")
        return False

    except asyncpg.exceptions.CannotConnectNowError:
        print("❌ Error: Database is not ready to accept connections")
        print("\nPossible solutions:")
        print("  1. Check if PostgreSQL container is running:")
        print("     docker ps | grep postgres")
        print("  2. Start PostgreSQL if needed:")
        print("     docker-compose up -d postgres")
        return False

    except asyncpg.exceptions.InvalidPasswordError:
        print("❌ Error: Invalid database password")
        print(f"\nCheck POSTGRES_PASSWORD in .env file")
        return False

    except asyncpg.exceptions.InvalidCatalogNameError:
        print("❌ Error: Database does not exist")
        print(f"\nDatabase '{db_name}' not found.")
        print("\nPossible solutions:")
        print("  1. Create the database:")
        print("     docker exec -it <container> psql -U postgres -c 'CREATE DATABASE backcast_evs;'")
        print("  2. Run migrations:")
        print("     uv run alembic upgrade head")
        return False

    except Exception as e:
        print(f"❌ Unexpected error: {type(e).__name__}")
        print(f"   {e}")
        return False


async def check_test_database():
    """Test connection to test database if configured."""
    try:
        import asyncpg

        # Check for test database config
        test_db_name = os.getenv("POSTGRES_TEST_DB", "backcast_evs_test")
        db_user = os.getenv("POSTGRES_USER", "postgres")
        db_password = os.getenv("POSTGRES_PASSWORD", "postgres")
        db_server = os.getenv("POSTGRES_SERVER", "localhost")
        db_port = os.getenv("POSTGRES_PORT", "5432")

        print("\n" + "=" * 60)
        print("Test Database Connection Check")
        print("=" * 60)
        print(f"Database: {test_db_name}")
        print("-" * 60)

        conn = await asyncpg.connect(
            user=db_user,
            password=db_password,
            database=test_db_name,
            host=db_server,
            port=int(db_port)
        )

        print("✅ Successfully connected to test database!")

        # Check tables
        tables = await conn.fetch("""
            SELECT COUNT(*) as count
            FROM information_schema.tables
            WHERE table_schema = 'public';
        """)

        print(f"Found {tables[0]['count']} tables in test database")

        await conn.close()
        print("✅ Test database connection OK!")
        return True

    except asyncpg.exceptions.InvalidCatalogNameError:
        print("❌ Test database does not exist (this is OK if not using test DB)")
        return False
    except Exception as e:
        print(f"⚠️  Could not connect to test database: {e}")
        return False


if __name__ == "__main__":
    print("\n🔍 Checking Database Connections...\n")

    # Check main database
    main_ok = asyncio.run(check_database_connection())

    # Check test database
    test_ok = asyncio.run(check_test_database())

    print("\n" + "=" * 60)
    print("Summary:")
    print(f"  Main Database:   {'✅ OK' if main_ok else '❌ FAILED'}")
    print(f"  Test Database:  {'✅ OK' if test_ok else '⚠️  NOT AVAILABLE'}")
    print("=" * 60)

    if not main_ok:
        print("\n⚠️  Main database connection failed!")
        print("Tests will likely fail until this is fixed.")
        exit(1)
    else:
        print("\n✅ Database connections verified!")
        exit(0)
