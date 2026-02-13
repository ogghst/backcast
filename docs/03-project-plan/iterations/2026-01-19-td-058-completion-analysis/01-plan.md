# Plan: Complete TD-058 Overlapping Valid Time Constraint Implementation

**Created:** 2026-01-19
**Based on:** [00-analysis.md](./00-analysis.md)
**Approved Option:** Option A - Complete TD-058 (Re-open and finish original work)

---

## Scope & Success Criteria

### Approved Approach Summary

- **Selected Option**: Option A - Re-open TD-058 and complete all missing work
- **Architecture**: Application-level constraint enforcement in EVCS versioning commands
- **Key Decisions**:
  - Extend overlap checks to MergeCommand and RevertCommand
  - Add comprehensive test coverage for all overlap scenarios
  - Maintain consistency with existing `_check_overlap()` helper pattern
  - Follow TDD methodology: write tests first, then implement

### Success Criteria

**Functional Criteria:**

- [ ] MergeBranchCommand prevents overlapping valid_time ranges on target branch VERIFIED BY: test_merge_command_overlap_prevention
- [ ] RevertCommand prevents overlapping valid_time ranges when reverting to historical versions VERIFIED BY: test_revert_command_overlap_prevention
- [ ] CreateVersionCommand directly detects overlaps (not just via UpdateCommand) VERIFIED BY: test_create_version_command_direct_overlap
- [ ] Consecutive non-overlapping versions are allowed (valid use case) VERIFIED BY: test_consecutive_non_overlapping_versions
- [ ] Branch isolation allows same root_id on different branches VERIFIED BY: test_branch_isolation_allows_same_root_id
- [ ] Soft-deleted entities can be re-created without overlap errors VERIFIED BY: test_deleted_entity_recreation
- [ ] Time travel edge cases (past correction, future scheduling) work correctly VERIFIED BY: existing tests + new edge case tests

**Technical Criteria:**

- [ ] Performance: Overlap check uses indexed query (root_id + branch + deleted_at) VERIFIED BY: code review of SQL patterns
- [ ] Security: No privilege escalation via overlap bypass VERIFIED BY: code review of command access patterns
- [ ] Code Quality: MyPy strict mode (zero errors), Ruff clean VERIFIED BY: CI pipeline
- [ ] Test Coverage: ≥80% for versioning commands module VERIFIED BY: pytest --cov report

**TDD Criteria:**

- [ ] All new tests written BEFORE implementation code
- [ ] Each test fails first (RED), implementation passes (GREEN), then refactor if needed
- [ ] Tests follow Arrange-Act-Assert pattern
- [ ] Test coverage report shows ≥80% for commands.py

### Scope Boundaries

**In Scope:**

- Adding overlap checks to MergeBranchCommand.execute()
- Adding overlap checks to RevertCommand.execute()
- Writing 5 new unit tests for missing overlap scenarios
- Verifying existing tests still pass
- Updating TD-058 status in technical debt register

**Out of Scope:**

- Frontend changes (overlap detection is backend-only)
- Database schema changes (constraint is application-level)
- Performance optimization beyond ensuring indexed queries
- API contract changes (overlap errors are internal)

---

## Work Decomposition

### Task Breakdown

| #   | Task                                                                | Files                                                  | Dependencies | Success Criteria                                                                 | Complexity |
| --- | ------------------------------------------------------------------- | ------------------------------------------------------ | ------------ | -------------------------------------------------------------------------------- | ---------- |
| 1   | Write test for CreateVersionCommand direct overlap detection        | `tests/unit/core/branching/test_commands_overlap.py`   | None         | Test fails with OverlappingVersionError when expected                            | Low        |
| 2   | Write test for consecutive non-overlapping versions                 | `tests/unit/core/branching/test_commands_overlap.py`   | None         | Test passes for valid consecutive version creation                               | Low        |
| 3   | Write test for branch isolation with same root_id                   | `tests/unit/core/branching/test_commands_overlap.py`   | None         | Test passes when same root_id used on different branches                         | Low        |
| 4   | Write test for deleted entity re-creation                           | `tests/unit/core/branching/test_commands_overlap.py`   | None         | Test passes when creating new version after soft-delete                          | Medium     |
| 5   | Write test for MergeCommand overlap prevention                      | `tests/unit/core/branching/test_commands_overlap.py`   | None         | Test fails with OverlappingVersionError when merge would create overlap          | Medium     |
| 6   | Write test for RevertCommand overlap prevention                     | `tests/unit/core/branching/test_commands_overlap.py`   | None         | Test fails with OverlappingVersionError when revert would create overlap         | Medium     |
| 7   | Run all tests to verify RED phase (all new tests fail as expected)  | N/A (test execution)                                   | Tasks 1-6    | All 6 new tests fail with appropriate errors                                    | Low        |
| 8   | Implement overlap check in MergeBranchCommand                       | `app/core/branching/commands.py` (line ~337)           | Task 7       | Test T-005 (merge overlap) passes                                               | Medium     |
| 9   | Implement overlap check in RevertCommand                            | `app/core/branching/commands.py` (line ~414)           | Task 8       | Test T-006 (revert overlap) passes                                              | Medium     |
| 10  | Run all overlap tests to verify GREEN phase                         | N/A (test execution)                                   | Tasks 8-9    | All 8 tests pass (6 new + 2 existing)                                           | Low        |
| 11  | Verify code quality (MyPy, Ruff)                                    | N/A (code quality checks)                              | Task 10      | Zero MyPy errors, zero Ruff errors                                              | Low        |
| 12  | Generate test coverage report                                       | N/A (coverage report)                                  | Task 11      | Coverage ≥80% for versioning commands                                           | Low        |
| 13  | Update TD-058 status in technical debt register                     | `docs/03-project-plan/technical-debt-register.md`      | Task 12      | TD-058 marked as complete with notes on implementation                           | Low        |

### Test-to-Requirement Traceability

| Acceptance Criterion                                          | Test ID | Test File                                      | Expected Behavior                                                                                  |
| ------------------------------------------------------------- | ------- | ---------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| CreateVersionCommand directly detects overlaps                | T-001   | test_commands_overlap.py                       | CreateVersionCommand raises OverlappingVersionError when control_date overlaps existing version    |
| Consecutive non-overlapping versions allowed                  | T-003   | test_commands_overlap.py                       | CreateVersionCommand succeeds when creating V1[T1,T2), V2[T2,T3), V3[T3,T4) sequentially            |
| Branch isolation allows same root_id                          | T-004   | test_commands_overlap.py                       | CreateVersionCommand succeeds for same root_id on different branches without overlap error         |
| Soft-deleted entities can be re-created                       | T-005   | test_commands_overlap.py                       | CreateVersionCommand succeeds after soft-delete (deleted_at filter works correctly)                |
| MergeCommand prevents overlap on target branch                | T-006   | test_commands_overlap.py                       | MergeBranchCommand raises OverlappingVersionError when merge would create overlapping valid_time    |
| RevertCommand prevents overlap when reverting                 | T-007   | test_commands_overlap.py                       | RevertCommand raises OverlappingVersionError when revert would create overlapping valid_time        |
| UpdateCommand overlap detection (existing)                    | T-002   | test_commands_overlap.py (existing)            | UpdateCommand raises OverlappingVersionError for time-travel updates that would overlap             |
| Future scheduling overlap prevention (existing)               | T-008   | test_commands_overlap.py (existing)            | CreateVersionCommand prevents overlaps with future-dated versions                                    |

---

## Test Specification

### Test Hierarchy

```
tests/unit/core/branching/test_commands_overlap.py
├── Existing Tests
│   ├── test_update_command_detects_overlap (T-002)
│   └── test_update_command_future_overlap_prevention (T-008)
├── CreateVersionCommand Tests
│   ├── test_create_version_command_direct_overlap (T-001)
│   ├── test_consecutive_non_overlapping_versions (T-003)
│   ├── test_branch_isolation_allows_same_root_id (T-004)
│   └── test_deleted_entity_recreation (T-005)
├── MergeCommand Tests
│   └── test_merge_command_overlap_prevention (T-006)
└── RevertCommand Tests
    └── test_revert_command_overlap_prevention (T-007)
```

### Test Cases (Detailed Specifications)

#### Test T-001: test_create_version_command_direct_overlap

**Criterion**: CreateVersionCommand directly detects overlaps
**Type**: Unit Test
**Expected Result**: OverlappingVersionError raised

**Test Specification**:
```python
async def test_create_version_command_direct_overlap():
    """Test CreateVersionCommand raises error for overlapping range.

    Arrange:
        - Create V1 [Now-10d, Infinity) using CreateVersionCommand

    Act:
        - Call CreateVersionCommand with same root_id, control_date=Now-5d

    Assert:
        - Raises OverlappingVersionError
        - Error message contains root_id
        - Error message indicates conflicting range
    """
```

#### Test T-003: test_consecutive_non_overlapping_versions

**Criterion**: Consecutive non-overlapping versions allowed
**Type**: Unit Test
**Expected Result**: All versions created successfully

**Test Specification**:
```python
async def test_consecutive_non_overlapping_versions():
    """Test that consecutive versions with non-overlapping ranges succeed.

    Arrange:
        - None (fresh test)

    Act:
        - Create V1 with control_date=Jan 1
        - Close V1 at Feb 1 (via UpdateCommand or raw SQL)
        - Create V2 with control_date=Feb 1
        - Close V2 at Mar 1
        - Create V3 with control_date=Mar 1

    Assert:
        - All three versions created successfully
        - No OverlappingVersionError raised
        - V1.valid_time == [Jan 1, Feb 1)
        - V2.valid_time == [Feb 1, Mar 1)
        - V3.valid_time == [Mar 1, NULL)
    """
```

#### Test T-004: test_branch_isolation_allows_same_root_id

**Criterion**: Branch isolation allows same root_id on different branches
**Type**: Unit Test
**Expected Result**: Versions on different branches don't conflict

**Test Specification**:
```python
async def test_branch_isolation_allows_same_root_id():
    """Test that same root_id on different branches doesn't conflict.

    Arrange:
        - Create V1 on branch "main" [Now, Infinity)

    Act:
        - Create V2 on branch "feature" with same root_id [Now, Infinity)

    Assert:
        - Both versions created successfully
        - No OverlappingVersionError raised
        - V1.branch == "main"
        - V2.branch == "feature"
        - V1.wbe_id == V2.wbe_id (same root)
    """
```

#### Test T-005: test_deleted_entity_recreation

**Criterion**: Soft-deleted entities can be re-created
**Type**: Unit Test
**Expected Result**: New version created after soft-delete

**Test Specification**:
```python
async def test_deleted_entity_recreation():
    """Test creating new version after soft-delete.

    Arrange:
        - Create V1 [Jan 1, Feb 1)
        - Soft-delete V1 (set deleted_at = Feb 1)

    Act:
        - Create V2 with same root_id, control_date=Feb 1

    Assert:
        - V2 created successfully
        - No OverlappingVersionError raised
        - V1.deleted_at is not None
        - V2.deleted_at is None
    """
```

#### Test T-006: test_merge_command_overlap_prevention

**Criterion**: MergeCommand prevents overlap on target branch
**Type**: Unit Test
**Expected Result**: OverlappingVersionError raised

**Test Specification**:
```python
async def test_merge_command_overlap_prevention():
    """Test MergeCommand prevents overlapping valid_time on target branch.

    Arrange:
        - main branch: V1 [Jan 1, Mar 1) (closed version)
        - main branch: V2 [Mar 1, Infinity) (current head)
        - feature branch: V3 [Feb 15, Infinity)

    Act:
        - Merge feature branch into main branch

    Assert:
        - Raises OverlappingVersionError
        - Error indicates conflict between merge timestamp and existing V2
        - No merge version created
    """
```

#### Test T-007: test_revert_command_overlap_prevention

**Criterion**: RevertCommand prevents overlap when reverting
**Type**: Unit Test
**Expected Result**: OverlappingVersionError raised

**Test Specification**:
```python
async def test_revert_command_overlap_prevention():
    """Test RevertCommand prevents overlapping valid_time.

    Arrange:
        - V1 [Jan 1, Jan 15)
        - V2 [Jan 15, Feb 1)
        - V3 [Feb 1, Infinity) (current head)

    Act:
        - Revert to V1 (which would create V4 [Now, Infinity))

    Assert:
        - Raises OverlappingVersionError
        - Error indicates V3 would overlap with new reverted version
        - No revert version created
    """
```

### Test Infrastructure Needs

**Fixtures needed**:
- `db_session: AsyncSession` - from existing conftest.py
- `sample_wbe_root_id: UUID` - from existing test file
- `actor_id: UUID` - from existing test file
- `created_wbe: WBE` - from existing test file (may need enhancement for branch tests)

**Mocks/stubs**:
- None required (all tests use real database session)

**Database state**:
- Clean WBE table for each test (pytest-asyncio handles this via rollback)
- Specific temporal states created via SQL manipulation for edge cases

---

## Task Dependency Graph

```yaml
# Task Dependency Graph for TD-058 Completion
tasks:
  - id: TEST-001
    name: "Write test for CreateVersionCommand direct overlap detection"
    agent: pdca-backend-do-executor
    dependencies: []

  - id: TEST-002
    name: "Write test for consecutive non-overlapping versions"
    agent: pdca-backend-do-executor
    dependencies: []

  - id: TEST-003
    name: "Write test for branch isolation with same root_id"
    agent: pdca-backend-do-executor
    dependencies: []

  - id: TEST-004
    name: "Write test for deleted entity re-creation"
    agent: pdca-backend-do-executor
    dependencies: []

  - id: TEST-005
    name: "Write test for MergeCommand overlap prevention"
    agent: pdca-backend-do-executor
    dependencies: []

  - id: TEST-006
    name: "Write test for RevertCommand overlap prevention"
    agent: pdca-backend-do-executor
    dependencies: []

  - id: VERIFY-RED
    name: "Run all tests to verify RED phase (new tests fail as expected)"
    agent: pdca-backend-do-executor
    dependencies: [TEST-001, TEST-002, TEST-003, TEST-004, TEST-005, TEST-006]

  - id: IMPLEMENT-MERGE
    name: "Implement overlap check in MergeBranchCommand"
    agent: pdca-backend-do-executor
    dependencies: [VERIFY-RED]

  - id: IMPLEMENT-REVERT
    name: "Implement overlap check in RevertCommand"
    agent: pdca-backend-do-executor
    dependencies: [IMPLEMENT-MERGE]

  - id: VERIFY-GREEN
    name: "Run all overlap tests to verify GREEN phase"
    agent: pdca-backend-do-executor
    dependencies: [IMPLEMENT-REVERT]

  - id: CODE-QUALITY
    name: "Verify code quality (MyPy, Ruff)"
    agent: pdca-backend-do-executor
    dependencies: [VERIFY-GREEN]

  - id: COVERAGE
    name: "Generate test coverage report"
    agent: pdca-backend-do-executor
    dependencies: [CODE-QUALITY]

  - id: UPDATE-DOCS
    name: "Update TD-058 status in technical debt register"
    agent: pdca-backend-do-executor
    dependencies: [COVERAGE]
```

**Dependency Explanation**:
- Tests 1-6 can be written in parallel (no dependencies)
- VERIFY-RED must wait for all tests to be written
- Implementation tasks must wait for RED phase verification (TDD methodology)
- VERIFY-GREEN must wait for both implementations
- Code quality, coverage, and docs are sequential verification steps

---

## Risk Assessment

| Risk Type   | Description                                                           | Probability | Impact | Mitigation                                                                                      |
| ----------- | --------------------------------------------------------------------- | ----------- | ------ | ----------------------------------------------------------------------------------------------- |
| Technical   | MergeCommand overlap check may break existing merge workflows         | Low         | Medium | Existing tests will catch this; overlap check only prevents invalid merges                      |
| Technical   | RevertCommand overlap check may prevent valid revert scenarios        | Medium      | Medium | Careful test design to distinguish valid vs invalid reverts; may need to adjust check logic    |
| Integration | Test fixtures may not support multi-branch scenarios                  | Low         | Low    | Existing fixtures support branch field; may need minor fixture enhancement                    |
| Integration | Time-dependent tests may be flaky due to clock skew                   | Medium      | Low    | Use fixed timestamps via SQL manipulation; avoid reliance on datetime.now() in assertions     |
| Performance | Additional overlap checks may slow down merge/revert operations       | Very Low    | Low    | Overlap check uses indexed query (root_id + branch + deleted_at); O(1) with proper indexes     |

---

## Documentation References

### Required Reading

- **Coding Standards**: `/home/nicola/dev/backcast_evs/docs/00-meta/coding_standards.md`
  - Section: Backend Python Standards (MyPy strict, Ruff configuration)
  - Section: Testing Standards (pytest-asyncio, AAA pattern, 80% coverage)

- **Original TD-058 Analysis**: `/home/nicola/dev/backcast_evs/docs/03-project-plan/iterations/2026-01-16-fix-overlapping-valid-time/00-analysis.md`
  - Context: Original problem statement and selected approach

- **EVCS Architecture**: `/home/nicola/dev/backcast_evs/docs/02-architecture/01-bounded-contexts.md`
  - Context: Entity versioning system design principles

### Code References

- **Existing Overlap Pattern**: `/home/nicola/dev/backcast_evs/backend/app/core/branching/commands.py` (lines 54-92)
  - `_check_overlap()` helper method used by UpdateCommand and CreateBranchCommand
  - Pattern to follow for MergeCommand and RevertCommand implementations

- **Existing Test Pattern**: `/home/nicola/dev/backcast_evs/backend/tests/unit/core/branching/test_commands_overlap.py`
  - Test fixture setup (sample_wbe_root_id, actor_id, created_wbe)
  - AAA (Arrange-Act-Assert) pattern in existing tests
  - SQL manipulation for temporal state setup

- **CreateVersionCommand Overlap Check**: `/home/nicola/dev/backcast_evs/backend/app/core/versioning/commands.py` (lines 154-192)
  - Reference implementation of overlap detection logic
  - Error handling pattern for SQLAlchemy vs test mocks

---

## Implementation Guidelines

### For MergeBranchCommand (Task 8)

**Location**: `/home/nicola/dev/backcast_evs/backend/app/core/branching/commands.py`, line 337 (before cloning)

**Implementation Pattern**:
```python
async def execute(self, session: AsyncSession) -> TBranchable:
    # ... existing code to get source and target ...

    # BEFORE: Line 327 (before cloning source to target)
    # Generate timestamp in Python to avoid empty ranges
    merge_timestamp = datetime.now(UTC)

    # NEW: Check for overlap on target branch
    await self._check_overlap(session, merge_timestamp, self.target_branch)

    # THEN: Continue with existing clone logic
    merged = cast(...)
```

**Key Points**:
- Use existing `_check_overlap()` helper method inherited from BranchCommandABC
- Check target branch (not source branch)
- Check happens BEFORE creating the merged version
- Use `merge_timestamp` as the new version's start time

### For RevertCommand (Task 9)

**Location**: `/home/nicola/dev/backcast_evs/backend/app/core/branching/commands.py`, line 414 (before cloning)

**Implementation Pattern**:
```python
async def execute(self, session: AsyncSession) -> TBranchable:
    # ... existing code to get current and target ...

    # BEFORE: Line 400 (before cloning target to new head)
    # Generate timestamp in Python to avoid empty ranges
    revert_timestamp = datetime.now(UTC)

    # NEW: Check for overlap on current branch
    await self._check_overlap(session, revert_timestamp, self.branch)

    # THEN: Continue with existing clone logic
    reverted = cast(...)
```

**Key Points**:
- Use existing `_check_overlap()` helper method
- Check current branch (where revert is happening)
- Check happens BEFORE creating the reverted version
- Use `revert_timestamp` as the new version's start time

---

## Prerequisites

### Technical

- [x] PostgreSQL 15+ running (via docker-compose)
- [x] Python 3.12+ environment with uv synced
- [x] Test database migrations applied
- [x] TD-060 resolved (test environment subprocess failure fixed)
- [x] Existing overlap tests passing (2 tests in test_commands_overlap.py)

### Documentation

- [x] Analysis phase approved (00-analysis.md complete)
- [x] Architecture patterns reviewed (EVCS versioning commands)
- [x] Original TD-058 scope understood (from 2026-01-16 iteration)

### Environment Setup Commands

```bash
# From project root
cd /home/nicola/dev/backcast_evs

# Ensure dependencies installed
cd backend && uv sync

# Start PostgreSQL (if not running)
docker-compose up -d postgres

# Run existing tests to verify baseline
cd backend && uv run pytest tests/unit/core/branching/test_commands_overlap.py -v
```

---

## Output

**File**: `/home/nicola/dev/backcast_evs/docs/03-project-plan/iterations/2026-01-19-td-058-completion-analysis/01-plan.md`

**Next Phase**: Execute this plan via DO phase agents following TDD methodology

---

## Key Principles

1. **TDD First**: Write tests BEFORE implementation (RED-GREEN-REFACTOR)
2. **WHAT Not HOW**: This plan specifies test behaviors; DO phase implements the code
3. **Measurable Criteria**: All success criteria objectively verifiable via tests
4. **Consistent Patterns**: Follow existing `_check_overlap()` helper pattern
5. **Sequential Tasks**: Clear dependencies enable parallel test writing, sequential implementation
