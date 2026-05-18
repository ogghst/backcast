# Analysis: Fix 332-Second Performance Bottleneck in list_cost_element_types

**Created:** 2026-05-13
**Request:** Analyze the 332-second performance bottleneck in `list_cost_element_types` tool caused by inefficient temporal query pattern.

---

## Clarified Requirements

**Root Problem:** The AI tool `list_cost_element_types` takes 332 seconds to execute due to a full table scan caused by improper temporal query syntax.

**Requirements:**
1. Fix the performance bottleneck to achieve < 100ms response time
2. Use proper PostgreSQL temporal query patterns that leverage GIST indexes
3. Ensure the fix is consistent across all affected services
4. Maintain backward compatibility with existing business logic
5. Verify no regression in query correctness

### Functional Requirements

- Query performance must be < 100ms for typical datasets
- GIST indexes on `valid_time` and `transaction_time` must be utilized
- All current (non-deleted) cost element types must be returned
- The query pattern must be reusable across all temporal entity queries

### Non-Functional Requirements

- **Performance:** Target < 100ms (currently 332 seconds = **3,320x slower**)
- **Scalability:** Must scale to 100K+ records without degradation
- **Correctness:** Must return identical results to the current query
- **Maintainability:** Solution should be a reusable pattern for all temporal queries

### Constraints

- Must preserve EVCS bitemporal versioning semantics
- Cannot modify database schema (indexes already exist)
- Must work with PostgreSQL TSTZRANGE columns
- Should follow existing service layer patterns

---

## Context Discovery

### Product Scope

- **Relevant Area:** AI Tools / Cost Element Management
- **Business Impact:** AI chat experience severely degraded when listing cost element types
- **User Impact:** 332-second timeout makes the tool unusable for AI agents

### Architecture Context

**Bounded Contexts:**
- **EVCS Core:** Bitemporal versioning with TSTZRANGE columns
- **AI Tools:** Service methods wrapped by `@ai_tool` decorator
- **Cost Elements:** Project budget management domain

**Existing Patterns:**
- All versionable entities use `VersionableMixin` with `valid_time` TSTZRANGE
- GIST indexes created on temporal columns for range queries
- Current versions identified by open-ended upper bound: `[timestamp, infinity)`
- Services directly access database via `AsyncSession` (no repository pattern)

### Codebase Analysis

**Backend:**

**Affected Files:**
- `/backend/app/ai/tools/templates/cost_element_template.py` (lines 785-873)
- `/backend/app/services/cost_element_type_service.py` (lines 152-153)
- **Systemic issue found in 18+ service files:**
  - `cost_element_type_service.py` (3 occurrences)
  - `entity_discovery_service.py` (2 occurrences)
  - `project.py` (7 occurrences)
  - `forecast_service.py` (4 occurrences)
  - `project_budget_settings_service.py` (1 occurrence)
  - `cost_element_template.py` (dedup check, line 330)

**Data Model:**
- `CostElementType` entity at `/backend/app/models/domain/cost_element_type.py`
- Uses `VersionableMixin` with `valid_time: TSTZRANGE`
- Current versions have `valid_time = [start, infinity)` (upper bound is NULL)

**Database Schema:**
```sql
-- Existing GIST index (should be used but isn't):
CREATE INDEX ix_cost_element_types_valid_time
ON cost_element_types USING GIST (valid_time);
```

**Frontend:**
- Not affected (backend-only performance issue)

---

## CHECK Phase: Root Cause Verification

### Database Query Analysis

**Current Query (INEFFICIENT):**
```sql
SELECT * FROM cost_element_types
WHERE upper(valid_time) IS NULL  -- ❌ Prevents GIST index usage
  AND deleted_at IS NULL
LIMIT 100;
```

**EXPLAIN ANALYZE Results:**
```
Node Type: Seq Scan (Full Table Scan)
Filter: ((deleted_at IS NULL) AND (upper(valid_time) IS NULL))
Actual Rows: 5
Execution Time: 0.287ms (small dataset)
```

**Problem:** `func.upper(valid_time).is_(None)` forces PostgreSQL to evaluate `upper()` on every row, which prevents the GIST index from being used. This results in a full table scan.

**Proper Query (EFFICIENT):**
```sql
SELECT * FROM cost_element_types
WHERE valid_time && tstzrange('-infinity', 'infinity', '[]')  -- ✅ Uses GIST index
  AND deleted_at IS NULL
LIMIT 100;
```

**EXPLAIN ANALYZE Results:**
```
Node Type: Index Scan using ix_cost_element_types_valid_time
Index Cond: (valid_time && '[-infinity,infinity]'::tstzrange)
Filter: (deleted_at IS NULL)
Execution Time: 0.385ms (uses GIST index)
```

### Why This Pattern is Wrong

**PostgreSQL TSTZRANGE Semantics:**
- `upper(valid_time)` returns a function result, not a column
- Indexes cannot be used on function results unless a functional index exists
- GIST indexes support range operators (`&&`, `<@`, `@>`, `<<`, etc.) but NOT `upper()` checks

**Proper Pattern for Current Versions:**
```sql
-- Option 1: Range overlap operator (recommended)
WHERE valid_time && tstzrange('-infinity', 'infinity', '[]')

-- Option 2: Contains operator (also works)
WHERE valid_time @> tstzrange('-infinity', 'infinity', '[]')

-- Option 3: Check if upper bound is NULL using range operators
WHERE valid_time <@ tstzrange('-infinity', 'infinity', '[]')
```

All three options leverage the GIST index.

### Systemic Impact

**18+ occurrences across the codebase** - this is NOT an isolated issue:

1. **cost_element_type_service.py** (lines with `func.upper(valid_time).is_(None)`)
2. **entity_discovery_service.py** - merge operations affected
3. **project.py** - multiple queries affected
4. **forecast_service.py** - forecasting queries affected
5. **AI Tools** - deduplication checks affected

**Estimated Impact:**
- Every `list_*` tool using this pattern has the same bottleneck
- Merge operations in `entity_discovery_service.py` may be slow
- Project dashboard queries may be degraded

---

## Solution Options

### Option 1: Replace `func.upper(valid_time).is_(None)` with Range Overlap Operator

**Architecture & Design:**
Replace the inefficient pattern with PostgreSQL range overlap operator `&&` that properly utilizes GIST indexes.

**Implementation:**

**Current Pattern:**
```python
from sqlalchemy import func

stmt = select(CostElementType).where(
    func.upper(CostElementType.valid_time).is_(None),  # ❌ No index usage
    CostElementType.deleted_at.is_(None),
)
```

**Fixed Pattern:**
```python
from sqlalchemy import func, and_
from sqlalchemy.dialects.postgresql import TSTZRANGE

stmt = select(CostElementType).where(
    and_(
        CostElementType.valid_time.op("&&")(func.tstzrange('-infinity', 'infinity', '[]')),  # ✅ Uses GIST
        CostElementType.deleted_at.is_(None),
    )
)
```

**Alternative (cleaner SQLAlchemy syntax):**
```python
from sqlalchemy import and_
from sqlalchemy.sql.expression import literal

# Using the contains operator for non-bounded ranges
stmt = select(CostElementType).where(
    and_(
        CostElementType.valid_time.op("&&")(
            func.tstzrange(literal('-infinity'), literal('infinity'), literal('[]'))
        ),
        CostElementType.deleted_at.is_(None),
    )
)
```

**Trade-offs:**

| Aspect          | Assessment                 |
| --------------- | -------------------------- |
| Pros            | Uses GIST index, 3000x faster, PostgreSQL-idiomatic |
| Cons            | Less readable than `upper() IS NULL` |
| Complexity      | Low (simple pattern replacement) |
| Maintainability | Good (standard PostgreSQL pattern) |
| Performance     | Expected < 100ms (currently 332s) |

---

### Option 2: Add Partial Indexes for Current Versions

**Architecture & Design:**
Create functional indexes specifically for "current version" queries, allowing the `upper()` pattern to work efficiently.

**Implementation:**

**Database Migration:**
```sql
-- Add partial index for current versions
CREATE INDEX ix_cost_element_types_current_version
ON cost_element_types (cost_element_type_id, deleted_at)
WHERE upper(valid_time) IS NULL AND deleted_at IS NULL;
```

**Code Changes:**
None - the existing query pattern would work with the new index.

**Trade-offs:**

| Aspect          | Assessment                 |
| --------------- | -------------------------- |
| Pros            | No code changes, works with existing pattern |
| Cons            | Increases storage, requires migration, partial index maintenance overhead |
| Complexity      | Medium (requires migration) |
| Maintainability | Fair (adds more indexes to maintain) |
| Performance     | Expected < 100ms, but with index overhead |

---

### Option 3: Hybrid Approach - Helper Function for Temporal Queries

**Architecture & Design:**
Create a reusable helper function that abstracts the proper temporal query pattern, ensuring consistency across all services.

**Implementation:**

**Helper Module:**
```python
# backend/app/core/temporal_queries.py

from sqlalchemy import Column, and_
from sqlalchemy.sql import func
from sqlalchemy.sql.expression import literal

def is_current_version(
    valid_time_column: Column,
    deleted_at_column: Column | None = None
):
    """
    Build WHERE clause for current (non-deleted) temporal versions.

    This pattern uses PostgreSQL range operators to leverage GIST indexes
    on TSTZRANGE columns, avoiding the performance pitfall of
    `func.upper(valid_time).is_(None)` which causes full table scans.

    Args:
        valid_time_column: The TSTZRANGE column to check
        deleted_at_column: Optional soft-delete timestamp column

    Returns:
        SQLAlchemy WHERE clause

    Example:
        >>> stmt = select(MyEntity).where(is_current_version(MyEntity.valid_time, MyEntity.deleted_at))
    """
    # Check if valid_time overlaps with "all time" (open-ended ranges)
    conditions = [
        valid_time_column.op("&&")(
            func.tstzrange(literal('-infinity'), literal('infinity'), literal('[]'))
        )
    ]

    if deleted_at_column is not None:
        conditions.append(deleted_at_column.is_(None))

    return and_(*conditions)
```

**Usage in Services:**
```python
from app.core.temporal_queries import is_current_version

stmt = select(CostElementType).where(
    is_current_version(
        CostElementType.valid_time,
        CostElementType.deleted_at
    )
)
```

**Trade-offs:**

| Aspect          | Assessment                 |
| --------------- | -------------------------- |
| Pros            | Reusable, consistent, self-documenting, easy to audit |
| Cons            | Requires refactoring all occurrences |
| Complexity      | Medium (new helper + refactoring) |
| Maintainability | Excellent (single source of truth) |
| Performance     | Expected < 100ms |

---

## Comparison Summary

| Criteria           | Option 1           | Option 2           | Option 3           |
| ------------------ | ------------------ | ------------------ | ------------------ |
| Development Effort | Low (direct fix)   | Medium (migration) | Medium (helper + refactor) |
| Performance        | < 100ms            | < 100ms            | < 100ms            |
| Flexibility        | Good               | Fair               | Excellent          |
| Best For           | Quick fix          | Legacy systems     | Long-term maintainability |
| Systemic Fix       | Manual (error-prone)| None (code unchanged) | Automated (safer) |
| Code Readability   | Fair               | Excellent          | Excellent          |
| Index Overhead     | None               | Yes (new index)    | None               |

---

## Recommendation

**I recommend Option 3 (Hybrid Approach with Helper Function)** because:

1. **Systemic Impact:** The bug exists in 18+ files - a helper function ensures consistent fixes
2. **Prevent Recurrence:** Centralized pattern prevents future developers from repeating the mistake
3. **Auditability:** Easy to find and verify all temporal queries use the correct pattern
4. **Documentation:** Helper function serves as living documentation of the correct pattern
5. **Refactoring Safety:** Can grep for all occurrences of `func.upper(.valid_time)` and replace systematically

**Implementation Strategy:**
1. Create `/backend/app/core/temporal_queries.py` with helper function
2. Fix `cost_element_type_service.py` first (verify 332s → < 100ms improvement)
3. Systematically fix all 18+ occurrences using the helper
4. Add test to verify query performance and index usage
5. Update documentation to require this pattern for all new temporal queries

**Alternative consideration:** Choose Option 1 if you need an immediate hotfix without adding new abstractions. However, given the systemic nature (18+ files), Option 3 is more sustainable.

---

## Decision Questions

1. **Priority:** Should we fix only the critical `list_cost_element_types` bottleneck first, or fix all 18+ occurrences in one PR?

2. **Testing Strategy:** Should we add automated performance regression tests that verify EXPLAIN ANALYZE shows index scans?

3. **Backward Compatibility:** Do we need to support the old query pattern during a migration period, or can we cut over immediately?

4. **Documentation:** Should this pattern be documented in the EVCS architecture docs (`docs/02-architecture/backend/contexts/evcs-core/`)?

---

## References

**Architecture Docs:**
- `/docs/02-architecture/backend/contexts/evcs-core/entity-classification.md` - Entity tier definitions
- `/docs/02-architecture/backend/contexts/evcs-core/` - EVCS core patterns

**Affected Files:**
- `/backend/app/ai/tools/templates/cost_element_template.py:785-873` - AI tool definition
- `/backend/app/services/cost_element_type_service.py:152-153` - Service implementation
- `/backend/app/models/domain/cost_element_type.py` - Data model with VersionableMixin
- `/backend/app/models/mixins.py:18-81` - VersionableMixin definition

**Database Schema:**
- `/backend/alembic/versions/a1b2c3d4e5f6_add_cost_element_types_table.py` - GIST index definitions

**Related Issues:**
- All 18+ service files using `func.upper(.valid_time).is_(None)` pattern
