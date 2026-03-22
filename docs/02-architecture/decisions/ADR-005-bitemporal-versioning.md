# ADR-005: Bitemporal Versioning Pattern

## Status

✅ Accepted (2026-01-01)

**Supersedes:** [ADR-002: Entity Versioning Pattern](ADR-002-entity-versioning-pattern.md)

## Context

The Backcast  system requires a robust versioning system that provides:

- Complete history of all entity changes
- Time-travel queries to any past state (valid time)
- Audit trail of when changes were recorded (transaction time)
- Branch isolation for change orders
- Soft delete with recovery capability
- Minimal boilerplate for new entities

The original ADR-002 established a dual-table pattern (Head + Version) with composite primary keys. While functional, this pattern required significant boilerplate per entity and lacked:

- Bitemporal tracking (no transaction time)
- Native PostgreSQL range type support
- Unified branching across all entity types
- Generic command and service patterns

## Decision

Adopt a **Bitemporal Single-Table Pattern** with PostgreSQL `TSTZRANGE` native types:

### Core Design

**Single Table Per Entity:**
Each versioned entity uses one table containing all version snapshots.

```python
class TemporalBase(Base):
    __abstract__ = True

    id: Mapped[UUID]                           # Unique version ID
    {entity}_id: Mapped[UUID]                  # Stable entity root ID
    valid_time: Mapped[TSTZRANGE]              # When data is/was effective
    transaction_time: Mapped[TSTZRANGE]        # When data was recorded
    deleted_at: Mapped[datetime | None]        # Soft delete timestamp
    branch: Mapped[str]                        # Branch name (default: "main")
    parent_id: Mapped[UUID | None]             # Previous version (DAG)
    merge_from_branch: Mapped[str | None]      # Merge source tracking
```

**Bitemporal Model:**

- `valid_time`: Business time - when the data was/is effective in the real world
- `transaction_time`: System time - when the record was created/modified in the database

**Range Types:**
Use PostgreSQL `TSTZRANGE` with containment operator (`@>`) for temporal queries:

```sql
SELECT * FROM entity_versions
WHERE valid_time @> NOW()::timestamptz
  AND transaction_time @> NOW()::timestamptz
  AND deleted_at IS NULL;
```

### Generic Commands

Replace entity-specific commands with generic, type-safe commands:

| Command                  | Purpose                                        |
| ------------------------ | ---------------------------------------------- |
| `CreateCommand[T]`       | Create new entity with initial version         |
| `UpdateCommand[T]`       | Close current version, create new with changes |
| `SoftDeleteCommand[T]`   | Set `deleted_at` timestamp                     |
| `UndeleteCommand[T]`     | Clear `deleted_at` timestamp                   |
| `CreateBranchCommand[T]` | Clone current version to new branch            |
| `MergeBranchCommand[T]`  | Merge source branch to target                  |
| `RevertCommand[T]`       | Restore previous version state                 |

### Generic Service

Base service class for all temporal entities:

```python
class TemporalService(Generic[T]):
    def create(self, root_id: UUID, branch: str = "main", **fields) -> T
    def get_current(self, root_id: UUID, branch: str = "main") -> T | None
    def update(self, root_id: UUID, updates: dict, branch: str = "main") -> T
    def soft_delete(self, root_id: UUID, branch: str = "main") -> T | None
    def create_branch(self, root_id: UUID, new_branch: str, from_branch: str = "main") -> T
    def merge_branch(self, root_id: UUID, source_branch: str, target_branch: str = "main") -> T
    def revert(self, root_id: UUID, branch: str = "main", to_version_id: UUID | None = None) -> T
```

### Implementation Guidelines

1.  **SQL-Side Time Synchronization**: All temporal operations (commands, queries) MUST use `func.current_timestamp()` (SQL) rather than `datetime.now()` (Client) to prevent clock skew issues in distributed environments.
2.  **Explicit Base Cloning**: When cloning versioned entities using `clone()`, explicit exclusion of temporal fields (`valid_time`, `transaction_time`) is REQUIRED to prevent closed ranges from leaking into new open-ended versions.

## Consequences

### Positive

- **Simplified Model:** Single table per entity eliminates join complexity
- **Full Audit Trail:** Bitemporal model captures both valid and transaction time
- **Reduced Boilerplate:** New entities require ~20 lines vs ~200 lines previously
- **Native DB Support:** PostgreSQL `TSTZRANGE` enables efficient range queries with GIST indexes
- **Consistent Branching:** All entities support branching by default
- **Type Safety:** Generic commands/services maintain compile-time type checking
- **DAG History:** Explicit `parent_id` enables version chain traversal
- **Reversible Deletes:** `deleted_at` timestamp allows undelete operations

### Negative

- **Storage Increase:** Full version snapshots use more space than delta storage
- **Migration Required:** Existing dual-table entities must be migrated
- **Learning Curve:** Team must understand bitemporal semantics
- **Query Complexity:** Temporal queries require understanding of range operators

## Alternatives Considered

### Alternative 1: Keep Dual-Table Pattern (ADR-002)

Continue with Head + Version tables.

- **Pros:** No migration needed, team already familiar
- **Cons:** Lacks transaction time, requires significant boilerplate, no native range types
- **Rejected:** Does not meet enhanced audit and performance requirements

### Alternative 2: Event Sourcing

Store events, rebuild state by replay.

- **Pros:** Perfect audit trail, natural event-driven architecture
- **Cons:** Complex queries, slow reads, difficult time-travel implementation
- **Rejected:** Read performance critical for EVM calculations

### Alternative 3: Delta Storage

Store only changed fields between versions.

- **Pros:** Minimal storage, efficient for small changes
- **Cons:** Complex reconstruction, difficult querying, schema evolution challenges
- **Rejected:** Query simplicity more important than storage efficiency

## Implementation Notes

### Indexing Strategy

Required indexes for optimal query performance:

```sql
-- GIST indexes for range queries
CREATE INDEX ix_entity_valid_gist ON entity_versions USING GIST (valid_time);
CREATE INDEX ix_entity_tx_gist ON entity_versions USING GIST (transaction_time);

-- Partial unique index for current version per branch
CREATE UNIQUE INDEX uq_entity_current_branch ON entity_versions (entity_id, branch)
WHERE upper(valid_time) IS NULL
  AND upper(transaction_time) IS NULL
  AND deleted_at IS NULL;
```

### Migration from ADR-002

Entities using the dual-table pattern should be migrated:

1. Create new single table with `TSTZRANGE` columns
2. Migrate data: `valid_from` → `lower(valid_time)`, etc.
3. Update commands to generic pattern
4. Update services to extend `TemporalService[T]`
5. Drop old version tables

### Foreign Key Constraints in Temporal Entities

**Problem:** PostgreSQL foreign key constraints require referencing either a PRIMARY KEY or a column with a UNIQUE constraint. However, temporal entities use business keys (e.g., `user_id`, `project_id`) that are indexed but not unique across all versions.

**Challenge:**
```python
# INVALID: users.user_id is not PK or UNIQUE
class ChangeOrder(Base):
    assigned_approver_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.user_id")  # ❌ Fails: user_id not unique
    )
```

**Solution: Application-Level Referential Integrity**

Since database FKs cannot reference business keys in temporal tables, enforce referential integrity at the application layer:

```python
# CORRECT: No FK constraint, application-level validation
class ChangeOrder(Base):
    # Note: No FK constraint to users.user_id
    # Application-level validation in service layer ensures integrity
    assigned_approver_id: Mapped[UUID | None] = mapped_column(
        PG_UUID, nullable=True
    )
```

**Implementation Pattern:**

1. **Model Layer:** Remove FK constraints from temporal entity references
   ```python
   # ❌ Don't do this
   assigned_approver_id = mapped_column(
       PG_UUID, ForeignKey("users.user_id", ondelete="SET NULL")
   )

   # ✅ Do this instead
   assigned_approver_id = mapped_column(PG_UUID, nullable=True)
   ```

2. **Database Layer:** Create supporting indexes for validation
   ```sql
   -- Unique index on current versions (supports validation queries)
   CREATE UNIQUE INDEX uq_users_current_user_id
   ON users (user_id)
   WHERE upper_inf(transaction_time) AND deleted_at IS NULL;

   -- Index on referencing table for efficient lookups
   CREATE INDEX ix_change_orders_assigned_approver
   ON change_orders (assigned_approver_id)
   WHERE assigned_approver_id IS NOT NULL;
   ```

3. **Service Layer:** Validate references in business logic
   ```python
   async def assign_approver(
       self,
       change_order_id: UUID,
       user_id: UUID
   ) -> ChangeOrder:
       # Validate user exists and is current
       user = await self.user_service.get_current(user_id)
       if not user or not user.is_active:
           raise ValueError(f"User {user_id} not found or inactive")

       # Safe to assign - reference is valid
       return await self.update(
           change_order_id,
           {"assigned_approver_id": user_id}
       )
   ```

**When to Use FK vs Application-Level Integrity:**

| Scenario | Approach | Rationale |
|----------|----------|-----------|
| Temporal → Temporal (business key) | Application-level | Business key not unique, FK invalid |
| Temporal → Temporal (system ID) | Database FK | System ID (`id`) is PK, FK valid |
| Temporal → Non-Temporal | Database FK | Target table has standard PK |
| Non-Temporal → Temporal | Application-level | Temporal PK represents single version, not entity |

**Examples:**

```python
# ✅ VALID: FK to non-temporal table
class Project(Base):  # Non-temporal
    department_id: Mapped[UUID] = mapped_column(
        ForeignKey("departments.id")  # OK: departments.id is PK
    )

# ❌ INVALID: FK to temporal business key
class ChangeOrder(Base):
    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.project_id")  # FAILS: project_id not unique
    )

# ✅ VALID: Application-level reference
class ChangeOrder(Base):
    project_id: Mapped[UUID] = mapped_column(
        PG_UUID  # No FK - validate in service
    )
```

**Benefits:**
- Enables temporal entity relationships without database constraints
- Supports referencing "current" version by business key
- Maintains data integrity through validation logic
- Allows flexible validation rules (e.g., check user.is_active)

**Trade-offs:**
- No automatic cascade deletes (must implement in service)
- Requires explicit validation in service layer
- Possible orphaned references if validation incomplete
- Less performant than database-enforced FKs

### Related Documentation

- [EVCS Core Architecture](../backend/contexts/evcs-core/architecture.md)
- [Temporal Patterns Reference](../backend/contexts/evcs-core/evcs-implementation-guide.md)
- [Database Strategy](../cross-cutting/database-strategy.md)
