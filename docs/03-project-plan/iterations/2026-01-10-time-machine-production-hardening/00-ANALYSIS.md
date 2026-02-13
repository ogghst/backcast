# Request Analysis: Time Machine Production Hardening

**Date:** 2026-01-10  
**Analyst:** AI Assistant  
**Status:** ✅ ANALYSIS COMPLETE - Ready for PLAN Phase

---

## Clarified Requirements

### User Intent

Enable users to:

1. **View the state of any entity at any past point in time** (Time Travel)
2. **Perform CRUD operations at control dates** - key project milestones like "Acquisition Date", "Kick-off Date", "Current Date"
3. **Enforce temporal integrity** - edits cannot be made at a time prior to the last edit (append-only semantics)

This addresses the core product vision: _"Ability to time travel project at a specific date"_ while adding production-grade robustness with **battle-tested code** and **comprehensive test coverage**.

### Functional Requirements

1. **Time Travel Queries**

   - Query any entity (Project, WBE, Cost Element) as it was at any timestamp
   - Support for bitemporal queries (valid_time AND transaction_time)
   - Handle edge cases: entities that didn't exist yet, deleted entities, updated entities

2. **Control Date Management** _(Clarified)_

   - Control dates (Acquisition, Kick-off, etc.) managed separately as part of **change orders/baselines**
   - Out of scope for this iteration - focus on time-travel infrastructure

3. **Temporal Integrity Constraints**

   - Append-only: New versions must have transaction_time > previous version
   - No backdating: Cannot create versions in the past
   - **Backdating by Admin**: Future iteration as technical debt (not in this sprint)

4. **Test Data Consistency** _(New Requirement)_
   - Update seeding architecture to include **explicit entity IDs** in JSON files
   - Re-seed projects at each test run for consistent, predictable data
   - Enables reliable time-travel testing with known entity states

### Non-Functional Requirements

1. **Test Coverage**: Comprehensive E2E, integration, and unit tests
2. **Performance**: Time-travel queries should be indexed and performant
3. **Type Safety**: MyPy strict compliance
4. **Documentation**: Updated architecture docs reflecting fixes
5. **Test Repeatability**: Deterministic seed data with fixed entity IDs

### Constraints

- Must work with existing PostgreSQL TSTZRANGE infrastructure
- Cannot break existing functionality
- Must use existing Protocol-based architecture

---

## Context Discovery Findings

### Product Scope

**Relevant User Stories:**

- Time Travel: "Ability to time travel project at a specific date" (vision.md)
- Audit Trail: "Maintain complete audit trails for compliance and analysis"
- Change Orders: "Support safe experimentation with change orders via branch isolation"

**Business Requirements:**

- EVM metrics calculated at specific control dates
- Baseline management at project milestones

### Architecture Context

**Bounded Contexts Involved:**

- **EVCS Core**: Bitemporal versioning, time-travel logic
- **Project Management**: Projects, WBEs, Cost Elements
- **API Layer**: RESTful endpoints with `as_of` parameter

**Existing Patterns:**

- VersionableProtocol / BranchableProtocol for entity types
- TemporalService generic service layer
- Command pattern for versioned operations (CreateVersionCommand, UpdateVersionCommand, SoftDeleteCommand)

**Key Architecture Documents:**

- `docs/02-architecture/backend/contexts/evcs-core/architecture.md`
- `docs/02-architecture/backend/contexts/evcs-core/evcs-implementation-guide.md`
- `docs/02-architecture/backend/contexts/evcs-core/entity-classification.md`

### Codebase Analysis

**Backend - Existing Related APIs:**

- `/api/v1/projects/{id}?as_of=<timestamp>` - Project time travel
- `/api/v1/wbes/{id}?as_of=<timestamp>` - WBE time travel
- `/api/v1/cost-elements/{id}?as_of=<timestamp>` - Cost Element time travel

**Backend - Data Models:**

- `app/models/mixins.py`: VersionableMixin, BranchableMixin
- `app/models/protocols.py`: VersionableProtocol, BranchableProtocol
- `app/models/domain/project.py`, `wbe.py`, `cost_element.py`

**Backend - Service Layer:**

- `app/core/versioning/service.py`: TemporalService with `get_as_of()` method
- `app/core/versioning/commands.py`: Version creation/update/delete commands

**Backend - Seeding Architecture:**

- `app/db/seeder.py`: DataSeeder class with JSON-based seeding
- `backend/seed/`: JSON files for users, departments, projects, wbes, cost_elements
- Current limitation: Entity IDs generated at runtime, not deterministic
- **Need**: Add `entity_id` fields to JSON for test consistency

**Frontend - Comparable Components:**

- `TimeMachineStore` in Zustand for selected time state
- `useTimeMachine` React context for component access
- `TimeMachinePanel` and `TimeMachineButton` UI components

### Critical Bugs Discovered During Investigation

#### Bug 1: Missing transaction_time Filter in get_as_of()

**Location:** `app/core/versioning/service.py`
**Impact:** CRITICAL - Time travel queries returned wrong versions
**Root Cause:** Only filtering by valid_time, ignoring transaction_time
**Status:** ✅ Fixed

#### Bug 2: transaction_time Not Closed on Updates

**Location:** `app/core/versioning/commands.py`
**Impact:** CRITICAL - Old versions matched all time-travel queries
**Root Cause:** `_close_version()` only closed valid_time, not transaction_time
**Status:** ✅ Fixed

#### Bug 3: PostgreSQL now() vs clock_timestamp()

**Location:** `app/core/versioning/commands.py`
**Impact:** HIGH - Old and new versions got same transaction_time lower bound
**Root Cause:** `now()` is transaction-scoped, returns same value for all operations in transaction
**Status:** ⚠️ Partially Fixed (UpdateVersionCommand only)

---

## Branch Isolation Analysis for Time-Travel Queries

### Option A: Time-Travel Within Specific Branch Only

**Description:** Time-travel queries return entities only from the specified branch (default: `main`).

```python
# Query: "Show me Project X on branch 'main' as of 2026-01-01"
get_as_of(project_id, as_of="2026-01-01", branch="main")
```

**Pros:**

| Benefit | Description |
|---------|-------------|
| **Conceptual Clarity** | Each branch is an isolated "timeline" - matches Git mental model |
| **Change Order Safety** | Draft changes on feature branches don't pollute main history |
| **Simpler Queries** | Single branch filter, no complex fallback logic |
| **Performance** | Smaller result set per query, faster indexing |
| **Merge Semantics** | Clear distinction between "what was on main" vs "what was drafted" |

**Cons:**

| Drawback | Description |
|----------|-------------|
| **Missing Context** | Can't easily see "what changes were being proposed at time T" |
| **Branch Discovery** | Need separate API to list what branches existed at time T |
| **Historical Branches** | If branch was deleted, may lose access to its history |

---

### Option B: Time-Travel Across All Branches

**Description:** Time-travel queries return all versions across all branches that existed at the requested timestamp.

```python
# Query: "Show me all versions of Project X that existed at 2026-01-01"
get_as_of(project_id, as_of="2026-01-01", branch=None)  # Returns list from all branches
```

**Pros:**

| Benefit | Description |
|---------|-------------|
| **Complete Picture** | See all parallel development at a point in time |
| **Audit Compliance** | Full visibility into all changes being worked on |
| **Branch Comparison** | Compare main vs feature branch at same timestamp |
| **No Lost History** | Even deleted branches remain visible in history |

**Cons:**

| Drawback | Description |
|----------|-------------|
| **API Complexity** | Returns multiple results, needs different response schema |
| **UX Confusion** | "Which version is the 'real' one?" - cognitive load on users |
| **Performance** | Queries return more data, more complex WHERE clauses |
| **Implementation Effort** | Need to redesign get_as_of() return type |
| **Merge Conflicts** | Hard to show divergent histories cleanly |

---

### Option C: Hybrid - Branch-Specific with Cross-Branch Discovery

**Description:** Default behavior is branch-specific, but provide separate APIs for cross-branch exploration.

```python
# Primary API: Branch-specific time travel (simple, fast)
get_as_of(project_id, as_of="2026-01-01", branch="main")

# Discovery API: What branches existed at time T?
list_branches_as_of(project_id, as_of="2026-01-01")

# Comparison API: Compare two branches at time T
compare_branches_as_of(project_id, as_of="2026-01-01", branch_a="main", branch_b="BR-123")
```

**Pros:**

| Benefit | Description |
|---------|-------------|
| **Best of Both** | Simple primary use case, power-user features available |
| **Progressive Disclosure** | Users start with main, explore branches when needed |
| **Clear Semantics** | Each API has single responsibility |
| **Backwards Compatible** | Existing `as_of` queries continue to work |

**Cons:**

| Drawback | Description |
|----------|-------------|
| **More APIs** | Additional endpoints to maintain |
| **Documentation** | Need to explain when to use which API |

---

### Option D: Branch Mode with Fallback (NEW) ⭐

**Description:** Add a `branch_mode` parameter that controls how branch resolution works:

- **`strict` (default)**: Only return entities from the specified branch
- **`merge`**: If no entity exists on the requested branch at the control date, fall back to main branch

This mirrors Git's working tree behavior - your branch "overlays" changes on top of main.

```python
from enum import Enum

class BranchMode(str, Enum):
    STRICT = "strict"  # Only look at specified branch
    MERGE = "merge"    # Fall back to main if not found on branch

# Strict mode (default): Only branch 'BR-123'
get_as_of(project_id, as_of="2026-01-01", branch="BR-123", branch_mode="strict")
# → Returns entity from BR-123, or 404 if not on that branch

# Merge mode: Branch with main fallback
get_as_of(project_id, as_of="2026-01-01", branch="BR-123", branch_mode="merge")
# → Returns entity from BR-123 if exists, else falls back to main
```

**Implementation Pattern (Already Documented in evcs-implementation-guide.md):**

```python
def get_as_of_with_fallback(
    session: Session,
    entity_class: Type[T],
    root_id: UUID,
    as_of: datetime,
    branch: str = "main",
    branch_mode: BranchMode = BranchMode.STRICT
) -> T | None:
    """Get entity at timestamp with optional main fallback."""

    # First, try the requested branch
    result = _get_from_branch(session, entity_class, root_id, as_of, branch)

    if result is not None:
        return result

    # If strict mode or already on main, no fallback
    if branch_mode == BranchMode.STRICT or branch == "main":
        return None

    # Merge mode: fall back to main branch
    return _get_from_branch(session, entity_class, root_id, as_of, "main")
```

**Use Case: Change Order Preview**

When viewing a project on change order branch `BR-456`:

- **WBE-001** modified on `BR-456` → Show `BR-456` version
- **WBE-002** not modified on `BR-456` → Show `main` version (fallback)
- **WBE-003** created on `BR-456` → Show `BR-456` version
- **WBE-004** deleted on `BR-456` → Show nothing (branch-specific deletion)

This gives users a "merged view" of what the project would look like if the change order were applied.

**Pros:**

| Benefit | Description |
|---------|-------------|
| **Intuitive for Change Orders** | Users see "what would the project look like if this CO is approved?" |
| **Git-like Semantics** | Branch overlays changes on main, unchanged items show main version |
| **Single API** | One endpoint with mode parameter, no additional APIs needed |
| **Backwards Compatible** | Default `strict` mode preserves current behavior |
| **Already Documented** | Pattern exists in `evcs-implementation-guide.md` (Fallback to Main Branch) |
| **Flexible** | Users choose the behavior they need per-query |

**Cons:**

| Drawback | Description |
|----------|-------------|
| **Two Queries** | Merge mode may require two database lookups (branch + main) |
| **Complexity** | Slightly more complex logic than strict-only |
| **Delete Semantics** | Need to handle "deleted on branch but exists on main" edge case |
| **Response Clarity** | Should indicate which branch the returned data came from |

**Edge Case: Deletions in Merge Mode**

When entity is deleted on branch but exists on main:

- **Option A**: Return main version (deletion not applied until merge)
- **Option B**: Return 404 (deletion is intentional, respect it)

**Recommendation**: Option B - respect branch deletions. If user deleted on branch, that's intentional.

```python
def get_as_of_with_fallback(...):
    # Check if explicitly deleted on branch
    if _is_deleted_on_branch(session, entity_class, root_id, as_of, branch):
        return None  # Respect branch deletion, don't fall back

    # Normal fallback logic...
```

---

### Comparison Summary

| Criteria             | Option A: Strict | Option B: Cross-All | Option C: Hybrid | Option D: Mode+Fallback |
| -------------------- | ---------------- | ------------------- | ---------------- | ----------------------- |
| **Simplicity**       | ✅ High          | ❌ Low              | ⚡ Medium        | ✅ High                 |
| **Completeness**     | ⚠️ Branch only   | ✅ All data         | ✅ All data      | ✅ Merged view          |
| **Performance**      | ✅ Fast          | ⚠️ Slower           | ✅ Fast          | ⚡ 1-2 queries          |
| **Implementation**   | ✅ Easy          | ❌ Complex          | ⚡ Medium        | ⚡ Medium               |
| **UX Clarity**       | ✅ Clear         | ⚠️ Confusing        | ✅ Clear         | ✅ Clear                |
| **Git Mental Model** | ✅ Matches       | ❌ Differs          | ✅ Matches       | ✅ Matches best         |
| **CO Preview**       | ❌ Manual merge  | ⚠️ Complex          | ⚠️ Needs extra   | ✅ Built-in             |
| **Existing Pattern** | ✅ Current       | ❌ New              | ⚠️ Partial       | ✅ evcs-implementation-guide.md          |

---

### Recommendation: Option D (Branch Mode with Fallback) ⭐

**I recommend Option D** because:

1. **Best Change Order UX** - Users can preview "merged" state of change orders naturally
2. **Already Documented** - The fallback pattern exists in `evcs-implementation-guide.md` (lines 339-378)
3. **Single API** - No proliferation of endpoints, just one mode parameter
4. **Backwards Compatible** - Default `strict` mode = current behavior, no breaking changes
5. **Git Mental Model** - Perfectly matches how Git shows files (branch overlays main)
6. **Flexible** - Users choose `strict` for audit clarity, `merge` for CO preview

**Implementation Priority:**

1. **This Iteration**: Implement `branch_mode` parameter with `strict` (default) and `merge` modes
2. **Future Iteration**: Add `list_branches_as_of()` for discovery (Option C APIs)

---

## Updated Implementation Plan

### Phase 1: Complete Core Fixes (4 hours)

1. Fix CreateVersionCommand to use clock_timestamp()
2. Fix SoftDeleteCommand transaction_time handling
3. Ensure all version operations use consistent timestamp source

### Phase 2: Seeding Architecture Enhancement (3 hours)

1. Add `entity_id` fields to all seed JSON files
2. Update DataSeeder to use provided IDs instead of generating
3. Create test-specific seed files with known IDs
4. Add reseed script for test runs

### Phase 3: Comprehensive Test Suite (4 hours)

1. **Unit Tests**: TemporalService, Commands
2. **Integration Tests**: API time-travel endpoints
3. **Edge Case Tests**:
   - Query before entity creation → 404
   - Query after creation, before update → old version
   - Query after update → new version
   - Query deleted entity before deletion → entity visible
   - Query deleted entity after deletion → 404
   - Rapid successive updates (< 1ms apart)
   - Concurrent updates
   - Soft delete and undelete

### Phase 4: Documentation & Cleanup (2 hours)

1. Update architecture.md with fixes
2. Update evcs-implementation-guide.md with corrected examples
3. Document branch isolation behavior
4. Clean up debug test files

---

## Technical Debt Items Created

| ID     | Description                                                                 | Priority | Effort |
| ------ | --------------------------------------------------------------------------- | -------- | ------ |
| TD-018 | Admin backdating capability                                                 | Low      | 4h     |
| TD-019 | Cross-branch time-travel APIs (list_branches_as_of, compare_branches_as_of) | Medium   | 6h     |

---

## Approved for PLAN Phase ✅

**Decisions Confirmed:**

1. ✅ Control dates managed separately (change orders/baselines scope)
2. ✅ Admin backdating deferred as technical debt (TD-018)
3. ✅ **Branch isolation: Option D (Branch Mode with Fallback)**
   - Add `branch_mode` parameter: `strict` (default) | `merge`
   - `strict`: Only return entities from specified branch
   - `merge`: Fall back to main if not found on branch
4. ✅ Seeding enhanced with explicit entity IDs for test consistency

**Next Steps**: Create `01-PLAN.md` with detailed implementation tasks.
