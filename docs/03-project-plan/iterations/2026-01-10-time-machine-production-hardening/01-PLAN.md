# PLAN Phase: Time Machine Production Hardening

**Date:** 2026-01-10  
**Status:** 🔵 AWAITING APPROVAL  
**Iteration:** [2026-01-10-time-machine-production-hardening](./00-ANALYSIS.md)

---

## Phase 1: Context Summary

### Analysis Reference

See [00-ANALYSIS.md](./00-ANALYSIS.md) for full context discovery including:

- Bug investigation results (3 critical bugs identified, partially fixed)
- Branch isolation options comparison (4 options analyzed)
- Seeding architecture requirements

### Key Decisions from Analysis

| Decision         | Choice                                    |
| ---------------- | ----------------------------------------- |
| Control Dates    | Out of scope (change orders/baselines)    |
| Admin Backdating | Deferred as TD-018                        |
| Branch Isolation | **Option D: Branch Mode with Fallback**   |
| Test Data        | Enhanced seeding with explicit entity IDs |

### Architecture Alignment

- **Existing Pattern**: Fallback to main branch documented in `evcs-implementation-guide.md` (lines 339-378)
- **Protocols**: VersionableProtocol, BranchableProtocol remain unchanged
- **Service Layer**: TemporalService to be enhanced with `branch_mode` parameter

---

## Phase 2: Problem Definition

### 1. Problem Statement

**What:** Time-travel queries return incorrect historical versions due to bitemporal bugs.

**Why Important Now:** Core product feature ("time travel project at specific date") is not working correctly. 3 of 5 time machine tests are failing.

**Impact if Not Addressed:**

- Users see wrong historical data
- Audit compliance compromised
- EVM calculations at control dates are incorrect

**Business Value:**

- Reliable historical queries for project analysis
- Accurate EVM metrics at control dates
- Trustworthy audit trail

### 2. Success Criteria (Measurable)

**Functional Criteria:**

- [ ] All 5 existing time machine tests pass
- [ ] 10+ new edge case tests added and passing
- [ ] `branch_mode` parameter works correctly (strict/merge)
- [ ] Seed data remains consistent across test runs

**Technical Criteria:**

- [ ] MyPy strict mode passes
- [ ] Ruff linting passes
- [ ] Time-travel query < 100ms (with indexes)
- [ ] No transaction_time overlap in version history

**Business Criteria:**

- [ ] Historical queries return correct version for any timestamp
- [ ] Change order preview shows merged view correctly

### 3. Scope Definition

**In Scope:**

| Item                     | Description                               |
| ------------------------ | ----------------------------------------- |
| CreateVersionCommand fix | Use clock_timestamp() for new versions    |
| SoftDeleteCommand fix    | Proper transaction_time handling          |
| branch_mode parameter    | Add `strict`/`merge` modes to get_as_of() |
| Seeding enhancement      | Add entity_id fields to JSON files        |
| Test suite               | Unit, integration, edge case tests        |
| Documentation            | Update evcs-implementation-guide.md, architecture.md       |

**Out of Scope:**

| Item                      | Reason              | Deferred To      |
| ------------------------- | ------------------- | ---------------- |
| Control date management   | Change orders scope | Future iteration |
| Admin backdating          | Lower priority      | TD-018           |
| list_branches_as_of() API | Discovery feature   | TD-019           |
| Frontend changes          | Backend focus       | Future iteration |

---

## Phase 3: Implementation Tasks

### Task Breakdown

| #   | Task                                       | Effort | Priority | Dependencies |
| --- | ------------------------------------------ | ------ | -------- | ------------ |
| 1   | Fix CreateVersionCommand clock_timestamp() | 1h     | Critical | None         |
| 2   | Fix SoftDeleteCommand time-travel          | 1h     | Critical | Task 1       |
| 3   | Add BranchMode enum                        | 0.5h   | High     | None         |
| 4   | Implement get_as_of with branch_mode       | 2h     | High     | Tasks 1-3    |
| 5   | Add branch deletion check for merge mode   | 1h     | High     | Task 4       |
| 6   | Update seed JSON files with entity_id      | 1h     | Medium   | None         |
| 7   | Modify DataSeeder to use provided IDs      | 1h     | Medium   | Task 6       |
| 8   | Unit tests for commands                    | 2h     | High     | Tasks 1-2    |
| 9   | Integration tests for time-travel          | 2h     | High     | Task 4       |
| 10  | Edge case tests                            | 2h     | High     | Task 9       |
| 11  | Update architecture documentation          | 1h     | Medium   | All          |
| 12  | Update evcs-implementation-guide.md                         | 1h     | Medium   | Task 4       |

**Total Estimated Effort:** 15.5 hours

---

## Phase 4: Technical Design

### 4.1 BranchMode Enum

**File:** `app/core/versioning/enums.py` (new)

```python
from enum import Enum

class BranchMode(str, Enum):
    """Branch resolution mode for time-travel queries."""
    STRICT = "strict"  # Only return entities from specified branch
    MERGE = "merge"    # Fall back to main if not found on branch
```

### 4.2 Enhanced get_as_of Signature

**File:** `app/core/versioning/service.py`

```python
async def get_as_of(
    self,
    entity_id: UUID,
    as_of: datetime,
    branch: str = "main",
    branch_mode: BranchMode = BranchMode.STRICT,
) -> TVersionable | None:
    """Time travel: Get entity as it was at specific timestamp.

    Args:
        entity_id: Root entity ID
        as_of: Timestamp to query
        branch: Branch name (default: main)
        branch_mode: Resolution mode
            - STRICT: Only return from specified branch
            - MERGE: Fall back to main if not found on branch

    Returns:
        Entity version at timestamp, or None if not found
    """
```

### 4.3 CreateVersionCommand Fix

**File:** `app/core/versioning/commands.py`

```python
# In CreateVersionCommand.execute():
async def execute(self, session: AsyncSession) -> TVersionable:
    """Create new version with clock_timestamp() for unique transaction_time."""
    version = cast(Any, self.entity_class)(
        created_by=self.actor_id, **self.fields
    )
    session.add(version)
    await session.flush()

    # Fix transaction_time to use clock_timestamp()
    stmt = text(
        f"""
        UPDATE {self.entity_class.__tablename__}
        SET transaction_time = tstzrange(clock_timestamp(), NULL, '[]')
        WHERE id = :version_id
        """
    )
    await session.execute(stmt, {"version_id": version.id})
    await session.refresh(version)
    return cast(TVersionable, version)
```

### 4.4 Seed JSON Enhancement

**Before (current):**

```json
[
  {
    "code": "PRJ-DEMO-001",
    "name": "Demo Project 1",
    "budget": 1000000.0
  }
]
```

**After (with entity_id):**

```json
[
  {
    "project_id": "11111111-1111-1111-1111-111111111111",
    "code": "PRJ-DEMO-001",
    "name": "Demo Project 1",
    "budget": 1000000.0
  }
]
```

### 4.5 TDD Test Blueprint

```
├── Unit Tests (app/core/versioning/)
│   ├── test_commands.py
│   │   ├── test_create_uses_clock_timestamp
│   │   ├── test_update_closes_both_temporal_dims
│   │   ├── test_delete_transaction_time_preserved
│   │   └── test_versions_have_non_overlapping_times
│   └── test_service.py
│       ├── test_get_as_of_strict_mode_branch_not_found
│       ├── test_get_as_of_merge_mode_fallback_to_main
│       ├── test_get_as_of_merge_mode_respects_deletion
│       └── test_get_as_of_before_creation_returns_none
│
├── Integration Tests (tests/api/)
│   └── test_time_machine.py
│       ├── test_wbe_time_travel_basic ✅ (existing, passing)
│       ├── test_wbe_time_travel_update ✅ (existing, now should pass)
│       ├── test_wbe_time_travel_delete (existing, needs fix)
│       ├── test_project_time_travel ✅ (existing, passing)
│       ├── test_multiple_wbes_time_travel (existing, needs fix)
│       └── NEW: test_branch_mode_merge_fallback
│
└── Edge Case Tests (tests/api/test_time_machine_edge_cases.py)
    ├── test_query_1ms_after_creation
    ├── test_rapid_successive_updates
    ├── test_concurrent_updates_different_branches
    ├── test_deleted_entity_visible_before_deletion
    ├── test_soft_delete_and_undelete
    ├── test_merge_mode_deletion_respected
    └── test_merge_mode_modified_on_branch
```

### First 5 Test Cases (Ordered Simplest to Complex)

**1. test_create_uses_clock_timestamp** (Unit)

```python
async def test_create_uses_clock_timestamp(db_session):
    """New versions should have unique transaction_time lower bounds."""
    cmd1 = CreateVersionCommand(Project, uuid4(), uuid4(), name="P1", budget=100)
    cmd2 = CreateVersionCommand(Project, uuid4(), uuid4(), name="P2", budget=200)

    p1 = await cmd1.execute(db_session)
    p2 = await cmd2.execute(db_session)

    # Different entities should have different transaction_time starts
    assert p1.transaction_time.lower != p2.transaction_time.lower
```

**2. test_get_as_of_strict_mode_not_found** (Unit)

```python
async def test_get_as_of_strict_mode_not_found(service, project):
    """Strict mode returns None if entity not on specified branch."""
    result = await service.get_as_of(
        project.project_id,
        as_of=datetime.now(UTC),
        branch="nonexistent-branch",
        branch_mode=BranchMode.STRICT
    )
    assert result is None
```

**3. test_get_as_of_merge_mode_fallback** (Unit)

```python
async def test_get_as_of_merge_mode_fallback(service, project):
    """Merge mode falls back to main if not on specified branch."""
    result = await service.get_as_of(
        project.project_id,
        as_of=datetime.now(UTC),
        branch="nonexistent-branch",
        branch_mode=BranchMode.MERGE
    )
    assert result is not None
    assert result.branch == "main"
```

**4. test_wbe_time_travel_delete_visible_before** (Integration)

```python
async def test_wbe_time_travel_delete_visible_before(client, wbe):
    """Deleted WBE should be visible when querying before deletion."""
    time_before_delete = datetime.now(UTC)
    await client.delete(f"/api/v1/wbes/{wbe.wbe_id}")

    response = await client.get(
        f"/api/v1/wbes/{wbe.wbe_id}",
        params={"as_of": time_before_delete.isoformat()}
    )
    assert response.status_code == 200
```

**5. test_merge_mode_respects_branch_deletion** (Integration)

```python
async def test_merge_mode_respects_branch_deletion(client, project, wbe):
    """Merge mode should not fall back if entity deleted on branch."""
    # Create WBE on main, delete on feature branch
    await create_branch(project.project_id, "feature-1")
    await delete_on_branch(wbe.wbe_id, "feature-1")

    response = await client.get(
        f"/api/v1/wbes/{wbe.wbe_id}",
        params={"branch": "feature-1", "branch_mode": "merge"}
    )
    assert response.status_code == 404  # Deletion respected, no fallback
```

---

## Phase 5: Risk Assessment

| Risk Type   | Description                                  | Probability | Impact | Mitigation                                       |
| ----------- | -------------------------------------------- | ----------- | ------ | ------------------------------------------------ |
| Technical   | clock_timestamp() not supported in tests     | Low         | Medium | Use SQLite-compatible alternative for unit tests |
| Technical   | Transaction isolation affects timestamps     | Medium      | High   | Flush and commit strategically                   |
| Integration | Existing tests break with new behavior       | Medium      | Medium | Default branch_mode=STRICT preserves behavior    |
| Schedule    | Seeding changes require more effort          | Low         | Low    | Parallelize with command fixes                   |
| Data        | Existing data has incorrect transaction_time | Low         | High   | Document as known limitation, don't migrate      |

---

## Phase 6: Effort Estimation

### Time Breakdown

| Phase             | Tasks       | Effort    |
| ----------------- | ----------- | --------- |
| **Core Fixes**    | Tasks 1-5   | 5.5h      |
| **Seeding**       | Tasks 6-7   | 2h        |
| **Testing**       | Tasks 8-10  | 6h        |
| **Documentation** | Tasks 11-12 | 2h        |
| **Total**         |             | **15.5h** |

### Prerequisites

1. ✅ Docker PostgreSQL running (already available)
2. ✅ Existing test infrastructure (pytest-asyncio configured)
3. ⬜ No additional infrastructure needed

### Implementation Order

```
Phase 1: Core Fixes (5.5h)
├── Task 1: CreateVersionCommand fix
├── Task 2: SoftDeleteCommand fix
├── Task 3: BranchMode enum
├── Task 4: get_as_of with branch_mode
└── Task 5: Branch deletion check

Phase 2: Testing (6h) [can overlap]
├── Task 8: Unit tests
├── Task 9: Integration tests
└── Task 10: Edge case tests

Phase 3: Infrastructure (2h) [parallel]
├── Task 6: Seed JSON updates
└── Task 7: DataSeeder modifications

Phase 4: Documentation (2h)
├── Task 11: architecture.md
└── Task 12: evcs-implementation-guide.md
```

---

## Approval Checklist

- [ ] Problem statement clear
- [ ] Success criteria measurable
- [ ] Scope well-defined
- [ ] Technical design sound
- [ ] Risks identified and mitigated
- [ ] Effort realistic

---

## Approval

**Status:** 🔵 AWAITING APPROVAL

**To proceed to DO phase, please confirm:**

1. Implementation tasks are acceptable
2. Priority order is correct
3. Scope boundaries are agreed

---

## Related Documents

- [Analysis](./00-ANALYSIS.md)
- [EVCS Core Architecture](../../../02-architecture/backend/contexts/evcs-core/architecture.md)
- [Temporal Patterns](../../../02-architecture/backend/contexts/evcs-core/evcs-implementation-guide.md)
- [ADR-005: Bitemporal Versioning](../../../02-architecture/decisions/ADR-005-bitemporal-versioning.md)
