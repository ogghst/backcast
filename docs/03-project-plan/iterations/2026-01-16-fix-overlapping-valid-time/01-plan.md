# Plan: Fix Overlapping Valid Time Constraint (TD-058)

**Created:** 2026-01-16
**Based on:** [00-analysis.md](./00-analysis.md)
**Approved Option:** Option 1: Application-Level Constraint

---

## Scope & Success Criteria

### Approved Approach Summary

- **Selected Option**: Application-Level Constraint in `CreateVersionCommand` and `UpdateVersionCommand`.
- **Architecture**: Core EVCS (`backend/app/core/branching/commands.py`).
- **Key Decisions**: Enforce non-overlapping constraints in the application layer during write operations.

### Success Criteria

**Functional Criteria:**

- Attempting to create a version that overlaps with an existing version's `valid_time` (on the same branch) raises a specific error VERIFIED BY: Unit tests.
- Normal updates correctly close the previous version and do not trigger the error VERIFIED BY: Unit tests.
- Time-travel insertions (correcting history) must adjust adjacent intervals or raise error if invalid VERIFIED BY: Unit tests.

**Technical Criteria:**

- **Code Quality**: Changes pass `mypy` strict mode and `ruff` checks.
- **Performance**: Overlap check should be efficient (indexed query).

**TDD Criteria:**

- [ ] All tests written **before** implementation code VERIFIED BY: Git commit history
- [ ] Tests validate **all acceptance criteria** VERIFIED BY: Test-to-requirement traceability matrix
- [ ] Each test **failed first** (RED phase) VERIFIED BY: Do-prompt daily log
- [ ] Test coverage ≥80% VERIFIED BY: `pytest --cov` report

### Scope Boundaries

**In Scope:**

- `backend/app/core/branching/commands.py` (Constraint logic)
- `backend/app/core/branching/exceptions.py` (New exception type)
- Unit tests in `backend/tests/unit/core/branching/test_commands_overlap.py`

**Out of Scope:**

- Database migration for `EXCLUDE` constraints (deferred).
- Fixing existing bad data (script separate if needed).

---

## Work Decomposition

### Task Breakdown

| Task | Description                      | Files                                                        | Dependencies | Success          | Est. Complexity |
| ---- | -------------------------------- | ------------------------------------------------------------ | ------------ | ---------------- | --------------- |
| 1    | Define `OverlappingVersionError` | `backend/app/core/branching/exceptions.py`                   | None         | Exception exists | Low             |
| 2    | Test Overlap Creation (Red)      | `backend/tests/unit/core/branching/test_commands_overlap.py` | Task 1       | Test fails       | Low             |
| 3    | Implement Overlap Check          | `backend/app/core/branching/commands.py`                     | Task 2       | Test passes      | Medium          |

### 2.1.1 Test-to-Requirement Traceability

| Acceptance Criterion   | Test ID | Test File                  | Expected Behavior                                                                      |
| ---------------------- | ------- | -------------------------- | -------------------------------------------------------------------------------------- |
| Prevent New Overlap    | T-001   | `test_commands_overlap.py` | `CreateVersionCommand` raises `OverlappingVersionError` if range overlaps              |
| Prevent Update Overlap | T-002   | `test_commands_overlap.py` | `UpdateVersionCommand` raises `OverlappingVersionError` if new range overlaps existing |
| Allow Non-Overlapping  | T-003   | `test_commands_overlap.py` | Valid sequence of versions succeeds                                                    |

---

## Test Specification

### Test Hierarchy

```text
├── Unit Tests
│   └── backend/tests/unit/core/branching/test_commands_overlap.py
```

### Test Cases

| Test ID | Description                           | Type | Verification                                                                    |
| ------- | ------------------------------------- | ---- | ------------------------------------------------------------------------------- |
| T-001   | `test_create_version_detects_overlap` | Unit | Raises `OverlappingVersionError` when inserting `[T1, T3)` if `[T2, T4)` exists |
| T-002   | `test_update_version_detects_overlap` | Unit | Raises `OverlappingVersionError` when updating results in overlap               |
| T-003   | `test_consecutive_versions_allowed`   | Unit | Succeeds when `V1=[T1, T2)` and `V2=[T2, T3)`                                   |

### Test Infrastructure

- **Test Framework**: `pytest`
- **Fixtures Needed**: `db_session`

---

## Risk Assessment

| Risk Type   | Description                                 | Probability | Impact | Mitigation                                      |
| ----------- | ------------------------------------------- | ----------- | ------ | ----------------------------------------------- |
| Performance | Overlap check slows down high-volume writes | Low         | Low    | Ensure `valid_time` and `root_id` are indexed   |
| Regression  | Existing valid update flows blocked         | Medium      | High   | Comprehensive test cases for standard workflows |

---

## Documentation References

### Required Documentation

**Architecture & Standards:**

- Coding Standards: `docs/02-architecture/coding-standards.md`

### Code References

**Existing Patterns:**

- `backend/app/core/branching/commands.py`: Existing `_check_valid_time` (if any) or validation logic.

---

## Prerequisites & Dependencies

### Technical Prerequisites

- [x] Environment configured

### Documentation Prerequisites

- [x] Analysis phase approved
