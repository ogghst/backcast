# Database Strategy

**Last Updated:** 2025-12-29

## ORM and Database Layer

### Technology Stack

- **Database:** PostgreSQL 15+
- **ORM:** SQLAlchemy 2.0 (async mode)
- **Driver:** asyncpg
- **Migration Tool:** Alembic (async template)

### Design Principles

**Async-First:**
All database operations use `AsyncSession` and `await` pattern for optimal concurrency.

**Type Safety:**

- SQLAlchemy 2.0 `Mapped[]` type hints for all columns
- Strict MyPy validation of all repository code
- Explicit return type annotations on all repository methods

---

## Connection Management

### Session Factory

```python
# app/db/session.py
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)
```

### Session Lifecycle

**Dependency Injection Pattern:**
Sessions provided via FastAPI dependency, automatically committed/rolled back:

```python
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```

---

## Transaction Patterns

### Implicit Transactions

Most operations use implicit transactions via dependency injection.

### Explicit Transactions

For complex operations requiring atomicity:

```python
async with session.begin():
    # All operations in this block are atomic
    await repo.create_entity(data1)
    await repo.update_entity(data2)
    # Commits on context exit, rolls back on exception
```

---

## Migration Strategy

### Alembic Configuration

**Auto-generation:**

- Run `alembic revision --autogenerate -m "description"`
- Always review generated migration before applying
- Test on copy of production data when possible

**Versioning:**

- Sequential numbered migrations
- Never edit applied migrations (create new ones)
- Maintain both `upgrade()` and `downgrade()` paths

**Best Practices:**

- Use batch operations for large table changes
- Add indexes in separate migrations from table creation
- Test data migrations with prod-like data volumes

---

## Query Patterns

### Standard Queries

**Select with filters:**

```python
stmt = select(Model).where(Model.field == value)
result = await session.execute(stmt)
entities = result.scalars().all()
```

**Join queries:**

```python
stmt = (
    select(Parent)
    .join(Child)
    .where(Child.status == "active")
    .options(selectinload(Parent.children))
)
```

### Performance Optimization

**Eager Loading:**
Use `selectinload()` or `joinedload()` to avoid N+1 queries:

```python
stmt = select(User).options(
    selectinload(User.versions),
    selectinload(User.department),
)
```

**Pagination:**
Always limit queries that could return many rows:

```python
stmt = select(Model).limit(100).offset(skip)
```

---

## Indexing Strategy

### Required Indexes

**Version Tables:**

- `(head_id, valid_from)` - Time travel queries
- `(head_id, branch)` - Branch filtering
- `valid_to` - Active version filtering

**Standard Tables:**

- Primary keys (automatic)
- Foreign keys for joins
- Fields used in WHERE clauses frequently

### Index Monitoring

- Review slow query logs monthly
- Use `EXPLAIN ANALYZE` for query optimization
- Add indexes based on actual usage patterns

---

## Data Integrity

### Constraints

**Foreign Keys:**

- Always define FK relationships
- Use `ondelete` appropriately ("CASCADE", "SET NULL", "RESTRICT")

**Check Constraints:**

- Enforce business rules at DB level where possible
- Example: `CHECK (valid_from < valid_to OR valid_to IS NULL)`

**Unique Constraints:**

- Composite primary keys for versioned entities
- Unique indexes for natural keys (email, etc.)

---

## Backup and Recovery

### Backup Strategy

- Automated daily backups (PostgreSQL pg_dump)
- Point-in-time recovery enabled (WAL archiving)
- Test restore procedure quarterly

### Disaster Recovery

- RTO (Recovery Time Objective): < 1 hour
- RPO (Recovery Point Objective): < 15 minutes
- Documented restoration procedure in ops runbook

---

## Bitemporal Versioning (EVCS Pattern)

See [EVCS Core Architecture](../backend/contexts/evcs-core/architecture.md) for complete documentation.

> [!NOTE] > **Non-versioned entities** (user preferences, system config) use `SimpleEntityBase` with standard `created_at`/`updated_at` timestamps instead of TSTZRANGE. See [Non-Versioned Entities](../backend/contexts/evcs-core/architecture.md#non-versioned-entities).

### PostgreSQL Range Types

The versioning system uses PostgreSQL native `TSTZRANGE` (timestamp with timezone range) for temporal tracking:

```sql
-- Column definitions
valid_time TSTZRANGE NOT NULL DEFAULT tstzrange(NOW(), NULL, '[]'),
transaction_time TSTZRANGE NOT NULL DEFAULT tstzrange(NOW(), NOW(), '[]')
```

### Range Operators

| Operator | Meaning          | Example                                    |
| -------- | ---------------- | ------------------------------------------ |
| `@>`     | Contains element | `valid_time @> NOW()`                      |
| `&&`     | Overlaps range   | `valid_time && '[2025-01-01, 2025-12-31)'` |
| `<@`     | Contained by     | `point <@ valid_time`                      |

### Current Version Query Pattern

```sql
SELECT * FROM entity_versions
WHERE entity_id = :id
  AND branch = :branch
  AND valid_time @> NOW()::timestamptz
  AND transaction_time @> NOW()::timestamptz
  AND deleted_at IS NULL
ORDER BY valid_time DESC
LIMIT 1;
```

### GIST Indexing for Ranges

GIST indexes are **required** for efficient range queries:

```sql
-- Required indexes for each versioned table
CREATE INDEX ix_{table}_valid_gist ON {table} USING GIST (valid_time);
CREATE INDEX ix_{table}_tx_gist ON {table} USING GIST (transaction_time);

-- Partial unique index: one current version per entity per branch
CREATE UNIQUE INDEX uq_{table}_current ON {table} (entity_id, branch)
WHERE upper(valid_time) IS NULL
  AND upper(transaction_time) IS NULL
  AND deleted_at IS NULL;
```

### Time Travel Queries

Query entity state at a specific point in time:

```sql
SELECT * FROM entity_versions
WHERE entity_id = :id
  AND branch = :branch
  AND valid_time @> :as_of_time::timestamptz
  AND transaction_time @> :as_of_time::timestamptz
  AND deleted_at IS NULL;
```

### SQLAlchemy Integration

```python
from sqlalchemy.dialects.postgresql import TSTZRANGE
from sqlalchemy import func
from app.core.base.base import EntityBase
from app.models.mixins import VersionableMixin

class VersionedEntity(EntityBase, VersionableMixin):
    """Versioned entity with temporal tracking."""
    __tablename__ = "versioned_entities"
    
    # valid_time, transaction_time, deleted_at inherited from VersionableMixin

# Query with range operator
stmt = select(Entity).where(
    Entity.valid_time.op("@>")(func.now())
)
```

### Related Documentation

- [EVCS Core Architecture](../backend/contexts/evcs-core/architecture.md)
- [Temporal Patterns Reference](../backend/contexts/evcs-core/evcs-implementation-guide.md)
- [ADR-005: Bitemporal Versioning](../decisions/ADR-005-bitemporal-versioning.md)
