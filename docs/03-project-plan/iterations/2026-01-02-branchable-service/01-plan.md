# PLAN Phase: Verify and Finalize Branchable Service

## Phase 1: Context Analysis

### Documentation Review

- **Architecture**: `BranchableProtocol` and `BranchableService` are defined in `docs/02-architecture/backend/contexts/evcs-core/architecture.md`.
- **Project Plan**: Backlog indicates "Migrate backend entities to new EVCS Core pattern".
- **Current State**: `branch_service.py` and `commands.py` implement the logic but have low/no test coverage (0% and 53%).

### Codebase Analysis

- Patterns: `TemporalService` pattern verified successfully. `BranchableService` extends this with `branch` logic.
- Testing: Need to introduce a mock `BranchableEntity` for testing, similar to `VersionedEntity` used in `TemporalService` tests.

## Phase 2: Problem Definition

### 1. Problem Statement

The `BranchableService` and associated commands (`CreateBranch`, `Merge`, `Revert`) are implemented but unverified. Low test coverage implies high risk of bugs in critical branching logic.

### 2. Success Criteria (Measurable)

- [ ] `BranchableService` test coverage > 90%
- [ ] `commands.py` test coverage > 90%
- [ ] Validated branching flows:
  - Create Root -> Create Branch -> Update Branch -> Merge Back
  - Revert changes
- [ ] No regression in `TemporalService`

### 3. Scope Definition

**In Scope:**

- `app/core/versioning/branch_service.py`
- `app/core/versioning/commands.py` (Branching commands)
- New test file: `tests/unit/core/versioning/test_branch_service.py`

**Out of Scope:**

- Migrating actual domain entities (Projects/WBEs) to use it (will follow in next iteration).

## Phase 3: Implementation Options

| Aspect             | Option A: Test & Fix                                                            | Option B: Rewrite & Test                         |
| ------------------ | ------------------------------------------------------------------------------- | ------------------------------------------------ |
| **Approach**       | Write comprehensive tests for existing code, fix bugs as found.                 | Rewrite service/commands from scratch using TDD. |
| **Pros**           | Leverages existing work. Faster.                                                | clean slate.                                     |
| **Cons**           | Might inherit bad assumptions.                                                  | Slower. Duplicates effort.                       |
| **Recommendation** | **Option A**. The existing code aligns with the architecture we just validated. |

## Phase 4: Technical Design

### TDD Test Blueprint

`tests/unit/core/versioning/test_branch_service.py`:

1.  **Fixture**: `MockBranchableEntity` (SQLAlchemy model).
2.  **Test**: `test_create_root_creates_main_branch`
3.  **Test**: `test_create_branch_clones_state`
4.  **Test**: `test_update_branch_isolates_changes`
5.  **Test**: `test_merge_branch_applies_changes`
6.  **Test**: `test_revert_restores_state`

### Implementation Strategy

1.  Setup test infrastructure (mock entity).
2.  Write tests for each command operation via `BranchableService`.
3.  Fix any bugs discovered in `branch_service.py` or `commands.py`.
4.  Refine type hints and docstrings.

## Phase 5: Risk Assessment

- **Complexity**: Branching logic (merging, valid_time management) is complex. **Mitigation**: Detailed test cases for temporal bounds.

## Phase 6: Effort Estimation

- **Time**: 1 day (Development + Testing)
- **Prerequisites**: Existing `BranchableProtocol` definitions.

## Output Format

Approval Status: Pending
Date: 2026-01-02
