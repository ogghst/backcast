# Database Migration Troubleshooting Guide

**Last Updated:** 2026-01-18
**Related:** EVM Foundation Iteration (2026-01-18-evm-foundation)

This guide provides troubleshooting steps for common database migration issues, particularly those related to bitemporal versioning with PostgreSQL TSTZRANGE columns.

---

## Table of Contents

1. [Common Issues](#common-issues)
2. [btree_gist Extension](#btree_gist-extension)
3. [Migration Execution](#migration-execution)
4. [Test Failures](#test-failures)
5. [Verification Steps](#verification-steps)
6. [Prevention Strategies](#prevention-strategies)

---

## Common Issues

### Issue 1: "relation does not exist" Errors

**Symptom:**
```python
sqlalchemy.exc.ProgrammingError: relation "progress_entries" does not exist
```

**Root Cause:**
Migration file exists but table was not created in the database.

**Troubleshooting Steps:**

1. **Check if migration ran:**
   ```bash
   cd backend
   uv run alembic current
   ```
   Expected: Should show the latest revision ID (e.g., `20260118_100000`)

2. **Check if table exists:**
   ```sql
   SELECT table_name
   FROM information_schema.tables
   WHERE table_schema = 'public' AND table_name = 'progress_entries';
   ```

3. **Check migration logs:**
   ```bash
   uv run alembic upgrade head --sql
   ```

4. **Common fixes:**
   - Re-run migration: `uv run alembic downgrade base && uv run alembic upgrade head`
   - Check for SQL syntax errors in migration file
   - Verify PostgreSQL extensions are enabled (see below)

---

### Issue 2: GIST Index Creation Fails

**Symptom:**
```python
sqlalchemy.exc.ProgrammingError: index "ix_progress_entries_valid_time" requires btree_gist extension
```

**Root Cause:**
PostgreSQL `btree_gist` extension is not enabled, which is required for GIST indexes on TSTZRANGE columns.

**Solution:**

**Option A: Add to migration (Recommended)**
```python
def upgrade() -> None:
    # Create btree_gist extension if not exists
    op.execute('CREATE EXTENSION IF NOT EXISTS btree_gist SCHEMA public;')

    # Then create indexes
    op.execute('CREATE INDEX ix_progress_entries_valid_time ON progress_entries USING GIST (valid_time);')
```

**Option B: Manually enable extension**
```sql
-- Connect to your database
psql -d backcast_evs

-- Enable extension
CREATE EXTENSION IF NOT EXISTS btree_gist SCHEMA public;

-- Verify
SELECT * FROM pg_extension WHERE extname = 'btree_gist';
```

**Option C: Enable via PostgreSQL superuser**
```bash
# If you don't have permissions, run as superuser
sudo -u postgres psql -d backcast_evs -c "CREATE EXTENSION IF NOT EXISTS btree_gist SCHEMA public;"
```

---

### Issue 3: TSTZRANGE Column Errors

**Symptom:**
```python
sqlalchemy.exc.ProgrammingError: type "tstzrange" does not exist
```

**Root Cause:**
PostgreSQL doesn't recognize TSTZRANGE type (shouldn't happen in PostgreSQL 9.2+).

**Solution:**

1. **Verify PostgreSQL version:**
   ```sql
   SELECT version();
   ```
   Required: PostgreSQL 9.2 or higher

2. **Check if btree_gist is enabled (required for TSTZRANGE indexes):**
   ```sql
   SELECT * FROM pg_extension WHERE extname = 'btree_gist';
   ```

---

### Issue 4: Test Fixture Silent Failures

**Symptom:**
Tests fail with "relation does not exist" but no migration error was shown.

**Root Cause:**
Test fixture has `try/except` that catches migration errors and doesn't raise them.

**Solution:**

Update `backend/tests/conftest.py` to fail fast:

```python
# BEFORE (Bad):
try:
    command.upgrade(alembic_cfg, "head")
except Exception as e:
    print(f"Migration failed: {e}")
    pass  # Silent failure!

# AFTER (Good):
command.upgrade(alembic_cfg, "head")  # Let errors propagate

# Add verification
required_tables = ['progress_entries', 'cost_elements', ...]
for table in required_tables:
    result = await conn.execute(
        text(f"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = '{table}')")
    )
    exists = result.scalar_one()
    assert exists, f"Required table '{table}' not found after migrations!"
```

---

## btree_gist Extension

### What is btree_gist?

The `btree_gist` extension provides GiST index operator classes that implement B-tree equivalent behavior for complex data types like `TSTZRANGE` (timestamp with time zone ranges).

### Why is it Required?

Our bitemporal versioning system uses TSTZRANGE columns for:
- `valid_time`: Business time when data was valid
- `transaction_time`: System time when data was recorded

To create GIST indexes on these columns (for efficient range queries), PostgreSQL needs the btree_gist extension.

### How to Verify it's Enabled

```sql
-- Check if extension exists
SELECT * FROM pg_extension WHERE extname = 'btree_gist';

-- Check available extensions
SELECT * FROM pg_available_extensions WHERE name = 'btree_gist';
```

### How to Enable It

```sql
-- In migration file (Recommended)
CREATE EXTENSION IF NOT EXISTS btree_gist SCHEMA public;

-- Or manually in psql
CREATE EXTENSION IF NOT EXISTS btree_gist SCHEMA public;
```

---

## Migration Execution

### How to Manually Run Migrations

```bash
# Navigate to backend directory
cd backend

# Run all pending migrations
uv run alembic upgrade head

# Run specific migration
uv run alembic upgrade 20260118_100000

# Rollback to previous version
uv run alembic downgrade -1

# Rollback to base (no migrations)
uv run alembic downgrade base

# Show current version
uv run alembic current

# Show migration history
uv run alembic history
```

### How to Create a New Migration

```bash
# Autogenerate migration from model changes
uv run alembic revision --autogenerate -m "description"

# Create empty migration
uv run alembic revision -m "description"
```

### How to Troubleshoot a Failed Migration

1. **Check migration status:**
   ```bash
   uv run alembic current
   ```

2. **View migration SQL without executing:**
   ```bash
   uv run alembic upgrade head --sql
   ```

3. **Manually test SQL in psql:**
   ```bash
   psql -d backcast_evs
   # Paste SQL from migration file
   ```

4. **Check PostgreSQL logs:**
   ```bash
   # Location varies by system
   tail -f /var/log/postgresql/postgresql-15-main.log
   ```

---

## Test Failures

### When Tests Fail with "relation does not exist"

**Diagnostic Steps:**

1. **Check test database connection:**
   ```python
   # In tests/conftest.py
   print(f"Test DB URL: {TEST_DATABASE_URL}")
   ```

2. **Verify migrations ran:**
   ```bash
   # Set test database URL
   export DATABASE_URL="postgresql+asyncpg://user:pass@localhost/test_db"

   # Run migrations
   uv run alembic upgrade head

   # Verify table exists
   psql -d test_db -c "\dt progress_entries"
   ```

3. **Check test fixture order:**
   - `apply_migrations` fixture should run before `db_session`
   - Check fixture scope (should be `scope="session"`)

---

### When Coverage Collection Fails

**Symptom:**
```
CoverageWarning: Module app.services.evm_service was never imported.
CoverageWarning: No data was collected.
```

**Solution:**

Update `backend/pyproject.toml`:

```toml
[tool.pytest.ini_options]
addopts = [
    "--cov=app",
    "--cov-report=term-missing",
    "--cov-report=html",
    "--cov-context=test",
    "--cov-fail-under=80"
]
```

Run coverage with proper source:
```bash
cd backend
uv run pytest --cov=app --cov-report=term-missing
```

---

## Verification Steps

### After Running Migrations

Always verify the following:

1. **Table exists:**
   ```sql
   SELECT table_name
   FROM information_schema.tables
   WHERE table_name = 'your_table_name';
   ```

2. **Columns exist:**
   ```sql
   SELECT column_name, data_type
   FROM information_schema.columns
   WHERE table_name = 'your_table_name';
   ```

3. **Indexes exist:**
   ```sql
   SELECT indexname
   FROM pg_indexes
   WHERE tablename = 'your_table_name';
   ```

4. **Constraints exist:**
   ```sql
   SELECT conname, contype
   FROM pg_constraint
   JOIN pg_class ON pg_constraint.conrelid = pg_class.oid
   WHERE relname = 'your_table_name';
   ```

5. **Extensions enabled:**
   ```sql
   SELECT extname FROM pg_extension WHERE extname = 'btree_gist';
   ```

---

## Prevention Strategies

### 1. Always Test Migrations in Development First

Before pushing to CI/CD:
```bash
# Create fresh database
createdb test_migration_db

# Run migrations
DATABASE_URL="postgresql://localhost/test_migration_db" uv run alembic upgrade head

# Verify schema
psql -d test_migration_db -c "\dt"

# Drop test database
dropdb test_migration_db
```

### 2. Add Extension Creation to Migrations

Always include extension creation in migrations that need them:
```python
def upgrade() -> None:
    # Enable required extensions
    op.execute('CREATE EXTENSION IF NOT EXISTS btree_gist SCHEMA public;')

    # Create tables
    op.execute('CREATE TABLE ...')
```

### 3. Use Migration Verification Tests

Add tests to verify migrations (see `backend/tests/integration/test_migrations.py`):
```python
@pytest.mark.asyncio
async def test_progress_entries_table_exists(db_session):
    result = await db_session.execute(
        text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'progress_entries')")
    )
    assert result.scalar_one() is True
```

### 4. Fail Fast in Test Fixtures

Never silently catch migration errors:
```python
# BAD
try:
    command.upgrade(alembic_cfg, "head")
except Exception as e:
    print(f"Error: {e}")
    pass

# GOOD
command.upgrade(alembic_cfg, "head")

# Add verification
for table in required_tables:
    assert table_exists(table), f"Table {table} not created!"
```

### 5. Document Required Extensions

Keep a list of required PostgreSQL extensions in project docs:

**Required Extensions:**
- `btree_gist`: For GIST indexes on TSTZRANGE columns
- `uuid-ossp`: For UUID generation (if using gen_random_uuid())

---

## Quick Reference

### Common Commands

```bash
# Run migrations
uv run alembic upgrade head

# Check current version
uv run alembic current

# Rollback
uv run alembic downgrade -1

# Create migration
uv run alembic revision --autogenerate -m "description"

# Test migration SQL
uv run alembic upgrade head --sql
```

### SQL Queries for Verification

```sql
-- Check table exists
SELECT table_name FROM information_schema.tables WHERE table_name = 'progress_entries';

-- Check indexes
SELECT indexname FROM pg_indexes WHERE tablename = 'progress_entries';

-- Check extensions
SELECT extname FROM pg_extension WHERE extname = 'btree_gist';

-- Check constraints
SELECT conname FROM pg_constraint WHERE conrelid = 'progress_entries'::regclass;
```

---

## Related Documentation

- [Database Schema](/docs/02-architecture/database-schema.md)
- [Bitemporal Versioning](/docs/02-architecture/bitemporal-versioning.md)
- [Testing Guide](/docs/00-meta/testing-guide.md)
- [EVM Foundation Iteration](/docs/03-project-plan/iterations/2026-01-18-evm-foundation/)

---

**For issues not covered here, please contact the backend team or create a GitHub issue.**
