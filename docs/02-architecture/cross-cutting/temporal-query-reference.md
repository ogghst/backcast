# Temporal Query Reference

**Last Updated:** 2026-01-14
**Related ADRs:** [ADR-005: Bitemporal Versioning](../decisions/ADR-005-bitemporal-versioning.md)

## Overview

This document is the **definitive reference** for bitemporal query semantics and time travel in the Backcast  system. It covers:

- **Bitemporal Fundamentals:** Two time dimensions (valid time, transaction time)
- **Time Travel Semantics:** Valid Time Travel (supported) vs System Time Travel (deprecated)
- **Query Filter Pattern:** Standardized bitemporal filters for time-travel queries
- **Branch Modes:** STRICT vs MERGE behavior for queries
- **Common Pitfalls:** Query mistakes to avoid when working with temporal data
- **Compliance:** Detection patterns and justified deviations

**What This Document Covers:**

- Query semantics and filter patterns
- Time travel behavior and correctness
- Branch mode resolution logic
- Common pitfalls and mistakes

**What This Document Does NOT Cover:**

- Code patterns for implementing queries → See [EVCS Implementation Guide](../backend/contexts/evcs-core/evcs-implementation-guide.md)
- Choosing entity types → See [Entity Classification Guide](../backend/contexts/evcs-core/entity-classification.md)
- Architecture and type system → See [EVCS Core Architecture](../backend/contexts/evcs-core/architecture.md)

> **For code examples and implementation patterns, see [EVCS Implementation Guide](../backend/contexts/evcs-core/evcs-implementation-guide.md).**

---

## Bitemporal Fundamentals

### Two Time Dimensions

| Dimension            | Purpose                                    | Example                                                    |
| -------------------- | ------------------------------------------ | ---------------------------------------------------------- |
| **Valid Time**       | When the fact was true in the real world   | A project budget was valid from Jan 1 to Mar 31            |
| **Transaction Time** | When the fact was recorded in the database | The budget was entered on Feb 15, then corrected on Feb 20 |

**Implementation:** PostgreSQL `TSTZRANGE` types for both dimensions.

### Key Concepts

- **Append-Only:** Updates create new versions with new `transaction_time` ranges
- **Soft Delete:** `deleted_at` timestamp marks removal (reversible)
- **Branch Isolation:** Each branch (e.g., change orders) maintains separate timelines

---

## Time Travel Semantics

> [!IMPORTANT]
> **ALWAYS use Valid Time Travel semantics. NEVER use System Time Travel semantics.**
>
> All time-travel queries MUST only filter by `valid_time`. The `transaction_time` dimension is used for audit/correction tracking but MUST NOT be used for filtering query results.

### Valid Time Travel (THE ONLY SUPPORTED SEMANTIC)

**Use Case:** "Show me entities as they were valid at a specific point in time."

**Context:** All time-travel queries, including:

- List views and reports
- History browsing
- Forward-looking scenarios (e.g., forecasts with future `control_date`)
- Branch-aware queries
- Single-entity `get_as_of()` queries

**Semantics:**

- `valid_time` must contain the target `as_of` timestamp
- `transaction_time` is **NEVER used for filtering** (only for audit/correction tracking)
- `deleted_at`: If the entity was logically deleted _after_ `as_of`, it should appear. If deleted _before_ `as_of`, it should not.

**Why This Matters:**

Queries filter by `valid_time` only to show what business facts were valid at the specified time. This allows:

- **Historical queries**: "What was the forecast on Feb 10th?"
- **Forward-looking queries**: "What will the forecast be on Mar 15th?" (when `control_date > now()`)
- **Consistent semantics**: All time-travel queries work the same way

The `transaction_time` dimension tracks when corrections were made but does not filter results. If overlapping `valid_time` ranges exist (due to corrections), the latest version by `transaction_time` should be used - this is handled by `DISTINCT ON` in branch mode filtering or by ordering in service methods.

> **Note:** Overlapping `valid_time` ranges should be prevented at create/update time. See [Technical Debt Register](../../03-project-plan/technical-debt-register.md#td-058-overlapping-valid_time-constraint) for details.

### ~~System Time Travel~~ (DEPRECATED - DO NOT USE)

> [!CAUTION]
> **System Time Travel is DEPRECATED and must NOT be used.**
>
> Previous implementations that checked both `valid_time` AND `transaction_time` have been removed. This semantic was problematic because:
>
> - It prevented forward-looking queries (future `as_of` dates)
> - It was inconsistent with business requirements
> - It conflated "when it was valid" with "when it was recorded"

If you need audit/reproducibility features, implement them separately without mixing temporal dimensions in query filters.

---

## Standardized Filter Pattern

### `_apply_bitemporal_filter` Method

All list endpoints supporting `as_of` MUST use `TemporalService._apply_bitemporal_filter()`.

**Location:** `backend/app/core/versioning/service.py`

**Filters Applied:**

1. `valid_time @> as_of` - Check as_of is within valid_time range
2. `func.lower(valid_time) <= as_of` - Check entity existed at as_of
3. `deleted_at IS NULL OR deleted_at > as_of` - Zombie protection

**Why This Matters:**

The standardized filter includes critical components that custom implementations often miss:
- `func.lower(valid_time) <= as_of` - Prevents future entities from being included
- TIMESTAMP casting - Ensures proper timezone handling

> **For implementation examples and service integration, see [EVCS Implementation Guide](../backend/contexts/evcs-core/evcs-implementation-guide.md).**

---

## Zombie Check TDD Pattern

### Purpose

The "Zombie Check" verifies that soft-deleted entities correctly disappear from time-travel queries _after_ their deletion timestamp, but remain visible for queries _before_ deletion.

### Pattern: "Create → Delete → Query Past"

**Test Structure:**

```python
@pytest.mark.asyncio
async def test_project_zombie_check(session: AsyncSession):
    """Verify deleted entities respect time travel boundaries.

    Pattern: Create -> Delete -> Query Past
    """
    # 1. Create entity at T1
    control_date_t1 = datetime(2026, 1, 1, 12, 0, 0)
    project = await service.create(
        project_in=ProjectCreate(code="P001", name="Test Project"),
        actor_id=admin_user.user_id,
        control_date=control_date_t1,
    )

    # 2. Delete entity at T3
    control_date_t3 = datetime(2026, 1, 10, 12, 0, 0)
    await service.soft_delete(
        entity_id=project.project_id,
        actor_id=admin_user.user_id,
        control_date=control_date_t3,
    )

    # 3. Query at T2 (before deletion) - should return entity
    as_of_t2 = datetime(2026, 1, 5, 12, 0, 0)
    result = await service.get_as_of(
        entity_id=project.project_id,
        as_of=as_of_t2,
    )
    assert result is not None, "Entity should be visible before deletion"
    assert result.code == "P001"

    # 4. Query at T4 (after deletion) - should NOT return entity
    as_of_t4 = datetime(2026, 1, 15, 12, 0, 0)
    result = await service.get_as_of(
        entity_id=project.project_id,
        as_of=as_of_t4,
    )
    assert result is None, "Entity should NOT be visible after deletion"
```

### Why This Matters

Without proper `deleted_at` handling in `_apply_bitemporal_filter`, soft-deleted entities would either:

- **Always disappear** (missing the `deleted_at > as_of` condition)
- **Never disappear** (missing the `deleted_at` check entirely)

The Zombie Check ensures correct temporal boundaries for deletion.

---

## Branch Mode Behavior

### STRICT Mode (Default)

```python
result = await service.get_as_of(
    entity_id=project_id,
    as_of=some_date,
    branch="feature-branch-123",
    branch_mode=BranchMode.STRICT,  # Only search in this branch
)
```

**Behavior:** Returns `None` if entity not found on specified branch.

**Use Case:** Change order preview - see only what's changed in this CO.

### MERGE Mode

```python
result = await service.get_as_of(
    entity_id=project_id,
    as_of=some_date,
    branch="feature-branch-123",
    branch_mode=BranchMode.MERGE,  # Fall back to main if not found
)
```

**Behavior:** Falls back to `main` branch if not found in specified branch.

**Use Case:** "What-if" analysis - show base project with CO changes overlaid.

---

## Common Pitfalls

### 1. Past-Dated `control_date` Creates Inverted Ranges

```python
# ❌ Wrong: control_date in the past creates inverted valid_time range
# If today is 2026-01-19 and control_date is set to 2026-02-01:
# valid_time = [2026-02-01, 2026-01-19) → INVALID (inverted range)
await service.update(
    root_id=entity_id,
    actor_id=user_id,
    branch="main",
    control_date=datetime(2026, 2, 1),  # Future date when today is 2026-01-19
    **update_data,
)

# ✅ Correct: control_date should be current or past
await service.update(
    root_id=entity_id,
    actor_id=user_id,
    branch="main",
    control_date=datetime.now(UTC),  # Current time
    **update_data,
)
```

**Impact:** Past-dated `control_date` values (earlier than the current system time) will create inverted `valid_time` ranges when the new version's `valid_time` upper bound is set to the current time. This violates PostgreSQL range constraints and can cause query failures or unexpected behavior.

**Recommendation:** Always use `datetime.now(UTC)` or allow the system to default to current time for `control_date` unless you have a specific requirement for backdating. If backdating is required, ensure the date is not in the future relative to the current system time.

### 2. Using `@>` Operator Alone

```python
# ❌ Wrong: @> treats NULL upper bound as infinity
stmt.where(entity.valid_time.op("@>")(as_of))

# ✅ Correct: Also check lower bound
stmt.where(
    entity.valid_time.op("@>")(as_of),
    func.lower(entity.valid_time) <= as_of,
)
```

### 3. Forgetting `deleted_at` in Time Travel

```python
# ❌ Wrong: Deleted entities invisible in ALL time travel queries
stmt.where(
    entity.valid_time.op("@>")(as_of),
    entity.deleted_at.is_(None),  # Too restrictive!
)

# ✅ Correct: Respect deletion timing
stmt.where(
    entity.valid_time.op("@>")(as_of),
    or_(
        entity.deleted_at.is_(None),
        entity.deleted_at > as_of,  # Zombie protection
    ),
)
```

### 4. Custom Temporal Filter Implementations (CRITICAL BUG RISK)

> [!WARNING]
> **NEVER implement custom temporal filters. ALWAYS use `TemporalService._apply_bitemporal_filter()`.**
>
> The standardized filter includes critical components that custom implementations often miss:
>
> - `func.lower(valid_time) <= as_of` - Prevents future entities from being included
> - TIMESTAMP casting - Ensures proper timezone handling
>
> Custom filters will produce incorrect results in time-travel queries.

```python
# ❌ WRONG: Custom filter implementation (BUGGY!)
if as_of is not None:
    stmt = stmt.where(entity.valid_time.op("@>")(as_of))
    stmt = stmt.where(or_(entity.deleted_at.is_(None), entity.deleted_at > as_of))
# This misses func.lower(valid_time) <= as_of and TIMESTAMP casting!

# ✅ CORRECT: Use the standardized method
if as_of is not None:
    stmt = self._apply_bitemporal_filter(stmt, as_of)
else:
    stmt = stmt.where(func.upper(entity.valid_time).is_(None))
    stmt = stmt.where(entity.deleted_at.is_(None))
```

**Real-World Impact:**

- Cost element metrics (`used`, `remaining`, `AC`, `ETC`) were incorrect
- Historical cost analysis produced wrong sums
- Budget status calculations were unreliable

**See Also:** [ADR-005: Bitemporal Versioning](../decisions/ADR-005-bitemporal-versioning.md) | [TemporalService Implementation](../../../backend/app/core/versioning/service.py) (lines 230-264)

---

## Compliance Validation

### Detection Pattern

Use these grep patterns to find non-compliant custom temporal filters:

```bash
# Find @> operator without lower bound check
grep -rn "valid_time.*@>" backend/app/services/ | grep -v "func.lower.*valid_time"

# Find .contains() usage (non-standard pattern)
grep -rn "\.valid_time\.contains(" backend/app/services/
```

### Justified Deviations

The following custom implementations are justified and documented:

1. **CostElementService.get_cost_element_as_of()** (lines 679-750)
   - **Justification**: Complex query with joins to WBE and CostElementType for resolving parent_name and type_name
   - **Compliance**: Uses custom filters for related entities (WBE, CostElementType) with proper temporal checks

2. **ChangeOrderService.get_current()** (line 70)
   - **Justification**: Uses `clock_timestamp()` instead of `current_timestamp()` for proper transaction-scoped time handling
   - **Compliance**: Fixed with TIMESTAMP cast and lower bound check

3. **ChangeOrderService.get_current_by_code()** (line 548)
   - **Justification**: Uses `clock_timestamp()` for proper transaction-scoped time handling
   - **Compliance**: Fixed with TIMESTAMP cast and lower bound check

4. **ChangeOrderService.update_change_order()** (lines 226-299)
   - **Justification**: Handles Time Machine mode with `control_date` parameter for querying historical state
   - **Compliance**: Fixed with TIMESTAMP cast and lower bound check for all query statements

5. **WBEService._get_base_stmt()** (lines 122-154)
   - **Justification**: Provides parent name resolution for WBE hierarchy queries
   - **Compliance**: Fixed with TIMESTAMP cast and lower bound check

**Note**: All justified deviations have been remediated to include:

- `TIMESTAMP(timezone=True)` casting for proper timezone handling
- `func.lower(valid_time) <= as_of_tstz` to prevent future entities from leaking into historical queries

---

## Implementation Notes

### Zombie Check Tests

The zombie check pattern documented above is a best-practice TDD pattern for verifying bitemporal deletion behavior. However, this specific test pattern has not yet been implemented in the test suite.

**Recommended:** Add zombie check tests to verify that soft-deleted entities:

1. Remain visible for queries targeting timestamps before their deletion
2. Disappear for queries targeting timestamps after their deletion

> **For branch query implementation examples, see [EVCS Implementation Guide](../backend/contexts/evcs-core/evcs-implementation-guide.md).**

---

## Related Documentation

### Architecture & Design

- [ADR-005: Bitemporal Versioning](../decisions/ADR-005-bitemporal-versioning.md) - Architecture decision record
- [ADR-006: Protocol-Based Type System](../decisions/ADR-006-protocol-based-type-system.md) - Type system design
- [EVCS Core Architecture](../backend/contexts/evcs-core/architecture.md) - Complete EVCS system architecture

### Implementation Guides

- [EVCS Implementation Guide](../backend/contexts/evcs-core/evcs-implementation-guide.md) - Code patterns and recipes (CRUD, branching, relationships)
- [Entity Classification Guide](../backend/contexts/evcs-core/entity-classification.md) - Choosing Simple/Versionable/Branchable entity types

### User Guides

- [EVCS User Guide](../../05-user-guide/evcs-wbe-user-guide.md) - Working with versioned entities (API consumers)

### Source Code

- [TemporalService Implementation](../../../backend/app/core/versioning/service.py) - Core service with time travel support
- [BranchableService Implementation](../../../backend/app/core/branching/service.py) - Branch-aware service operations
