# Database Strategy

**Last Updated:** 2026-07-01

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
    str(settings.ASYNC_DATABASE_URI),
    echo=settings.LOG_LEVEL.upper() == "DEBUG",
    pool_pre_ping=True,
    pool_size=20,
    max_overflow=30,
    pool_recycle=300,   # recycle connections before the DB/PGBouncer idle timeout
    pool_timeout=30,
)

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)
```

The pool sizing (`pool_size=20, max_overflow=30` → 50-connection cap) and the
`DB_CONCURRENCY_SEMAPHORE` (size 10, also in `session.py`) were tuned after a
connection-pool-exhaustion incident; do not lower these without checking the
`get_pool_status()` utilization metric. A task-local `tool_scoped_session_factory`
(async_scoped_session on `asyncio.current_task`) exists for concurrent AI tool
execution — LangGraph runs multiple tools per task and each needs its own session.

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

> **Test gotcha:** because `get_db` commits on exit, the backend test `db` fixture
> also commits — so data created by tests is visible to the ASGI client and persists
> in the dev DB. Tests that create persistent rows MUST clean up (autouse
> `@pytest_asyncio.fixture` deleting the ids, or a rolled-back session) or junk
> accumulates. Async fixtures need `@pytest_asyncio.fixture`, not `@pytest.fixture`.

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

**Versioned Tables:**

Versioned entities (Project, WBSElement, CostElement, WorkPackage, ChangeOrder,
CustomEntityTemplate) use a **root ID** + `valid_time` TSTZRANGE column, not
`head_id`/`valid_from`/`valid_to`:

- `(root_id, branch)` — branch filtering + current-version lookup (the root ID is
  `project_id`, `wbs_element_id`, `work_package_id`, etc.)
- GIST on `valid_time` — time-travel / as-of queries
- GIST on `transaction_time` — audit-history queries

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
- Example (range bounds): `CHECK (lower(valid_time) < upper(valid_time))`

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
SELECT * FROM projects
WHERE project_id = :root_id         -- root ID, not per-version id
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

-- C1 partial unique index: the EVCS "one current version per (root, branch)"
-- invariant. Note: root_id (NOT entity_id) and NO transaction_time clause —
-- ADR-005's upper(transaction_time) IS NULL is intentionally deferred (frozen
-- decision C1). Mirrored in each model's __table_args__ and in migration
-- c93e9767de59.
CREATE UNIQUE INDEX ix_{table}_current_version ON {table} (root_id, branch)
WHERE upper(valid_time) IS NULL
  AND deleted_at IS NULL;
```

### Time Travel Queries

Query entity state at a specific point in time:

```sql
SELECT * FROM projects
WHERE project_id = :root_id
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

### Custom Fields (JSONB)

Admin-defined custom fields ride EVCS for free — no EAV table. Each branchable
entity (`projects`, `wbs_elements`, `work_packages`, `change_orders`) carries
three nullable JSONB/UUID columns added in migration `c93e9767de59`:

- `custom_fields JSONB` — `{field_code: value}` dict, validated against the
  entity's `CustomEntityTemplate`. Rides `clone()` / `UpdateCommand` like any
  other column, so it versions/branches automatically.
- `custom_entity_template_root_id UUID` — root ID of the template the values
  were validated against.
- `custom_field_definitions_snapshot JSONB` — point-in-time snapshot of the
  field definitions, so historical versions stay interpretable after the
  template is edited.

The same migration applies the **C1 unique partial index** per branchable table
(see [GIST Indexing](#gist-indexing-for-ranges) above). `custom_entity_templates`
itself (the template registry) is Versionable but NOT branchable, org-scoped —
its C1 index is single-column on `custom_entity_template_id`.

### ORM UUID Convention

UUID columns use `Mapped[UUID]` (stdlib `uuid.UUID`) with the
`sqlalchemy.dialects.postgresql.UUID` (`PG_UUID`) type:

```python
from uuid import UUID
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

project_id: Mapped[UUID] = mapped_column(PG_UUID, nullable=False, index=True)
```

`PG_UUID` returns `uuid.UUID` objects at runtime (`as_uuid=True` default).
**Use the ORM attribute directly — never wrap it in `UUID(field)`** (raises
`AttributeError` because `uuid.UUID` has no `.hex`-style attributes the wrapper
expects). The EVCS/AI modules are unified on `Mapped[UUID]`.

> **Legacy debt:** a handful of older models still declare UUID columns as
> `Mapped[str]` with `PG_UUID` (e.g. `documents`, `document_version`,
> `document_folder`, `document_entity_link`, `schedule_dependency`, and
> `started_at`/`completed_at` on the AI execution model are `Mapped[str]` over
> `DateTime`). These return `str` at runtime — convert at the boundary. Do not
> propagate the pattern to new models.

### Project Portfolio Attribution

`Project` carries nullable root-ID portfolio FKs (no DB-level constraint —
integrity is app-level per the EVCS root-ID convention, see ADR-005):

- `organizational_unit_id` — org unit owning the project
- `project_manager_id` — PM user root ID
- `customer_id` — customer root ID

A GLOBAL organizational unit
(`00000000-0000-4000-8000-00000000fffd`) is seeded so projects without an
explicit org unit still resolve; custom-field templates are seeded against it.

### Related Documentation

- [EVCS Core Architecture](../backend/contexts/evcs-core/architecture.md)
- [Temporal Patterns Reference](../backend/contexts/evcs-core/evcs-implementation-guide.md)
- [ADR-005: Bitemporal Versioning](../decisions/ADR-005-bitemporal-versioning.md)
