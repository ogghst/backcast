# Plan: RBAC Seeding Fix

**Created:** 2026-05-10
**Based on:** [00-analysis.md](00-analysis.md)
**Approved Option:** Option 2 -- Synchronize Both Files + Add `seed_user_role_assignments()` Method

---

## Scope & Success Criteria

### Approved Approach Summary

- **Selected Option**: Option 2 from analysis
- **Architecture**: Both `seed/rbac_roles.json` and `config/rbac.json` are synchronized to contain identical role and permission definitions. A new `seed_user_role_assignments()` method is added to `DataSeeder` using direct SQLAlchemy queries, following the established `seed_rbac_roles()` pattern. Only GLOBAL-scoped assignments are seeded (project-scoped deferred).
- **Key Decisions**:
  - `seed/rbac_roles.json` is the authoritative source; `config/rbac.json` is synchronized to match it (plus `change_order_approver` added from config)
  - "contributor" users in `seed/users.json` are permanently changed to "manager" -- no runtime mapping
  - Direct SQLAlchemy queries in the seeder (consistent with `seed_rbac_roles()` pattern, avoids ContextVar complexity)
  - A CI-sync test validates the two files stay identical going forward
  - Global-only scope for this iteration; project-scoped assignments deferred

### Success Criteria

**Functional Criteria:**

- [ ] FR-1: After a fresh reseed, every seeded user has exactly one `UserRoleAssignment` record with `scope_type='global'` and `scope_id=NULL`, matching their `User.role` value. VERIFIED BY: integration test querying `user_role_assignments` after `seed_all()`
- [ ] FR-2: After a fresh reseed, the `change_order_approver` role exists in `rbac_roles` with its full permission set (7 permissions). VERIFIED BY: integration test querying `rbac_roles` by name
- [ ] FR-3: `seed/rbac_roles.json` and `config/rbac.json` contain structurally identical role and permission definitions (same roles, same permissions per role, descriptions allowed to differ only in seed file's `_comment` field). VERIFIED BY: CI-sync unit test comparing parsed JSON structures
- [ ] FR-4: Running `seed_all()` twice produces the same database state (no duplicate `UserRoleAssignment` records, no errors). VERIFIED BY: integration test calling `seed_all()` twice and counting rows
- [ ] FR-5: `seed_user_role_assignments()` works correctly against both a fresh database (empty `user_role_assignments` table) and one where the Alembic data migration already ran. VERIFIED BY: two integration test scenarios

**Technical Criteria:**

- [ ] TC-1: Zero MyPy strict errors on modified files. VERIFIED BY: `mypy app/db/seeder.py app/models/domain/user_role_assignment.py`
- [ ] TC-2: Zero Ruff errors on modified files. VERIFIED BY: `ruff check app/db/seeder.py`
- [ ] TC-3: Test coverage >= 80% for new/modified code. VERIFIED BY: `pytest --cov=app/db/seeder --cov=app/db/seed_context`
- [ ] TC-4: No breaking changes to `reseed_db.py` flow. VERIFIED BY: manual reseed execution during CHECK phase

**TDD Criteria:**

- [ ] All test specifications below are implemented before (or alongside) implementation code
- [ ] Each test follows Arrange-Act-Assert pattern
- [ ] Tests cover happy path, idempotency, and edge cases

### Scope Boundaries

**In Scope:**

- Synchronize `seed/rbac_roles.json` and `config/rbac.json` to identical content
- Add `change_order_approver` role to `seed/rbac_roles.json`
- Fix `seed/users.json` to replace "contributor" with "manager"
- Add `seed_user_role_assignments()` method to `DataSeeder`
- Update `seed_all()` to call the new method after `seed_users()`
- Add CI-sync test validating the two JSON files stay in sync
- Add unit/integration tests for the new seeding method

**Out of Scope:**

- Project-scoped `UserRoleAssignment` seeding (deferred to future iteration)
- Changes to `UnifiedRBACService` or its ContextVar session injection
- Changes to `RoleChecker` / `ProjectRoleChecker` fallback logic
- Frontend modifications
- Changes to the Alembic data migration

---

## Work Decomposition

### Task Breakdown

| # | Task | Files | Dependencies | Success Criteria | Complexity |
|---|------|-------|-------------|------------------|------------|
| 1 | Synchronize `seed/rbac_roles.json` | `backend/seed/rbac_roles.json` | none | 7 roles including `change_order_approver`; all permissions from seed file preserved; `change_order_approver` permissions added from config | Low |
| 2 | Synchronize `config/rbac.json` | `backend/config/rbac.json` | none | Identical role and permission definitions to seed file (descriptions may differ); `viewer` no longer has `change-order-approve`; manager has all seed-file permissions including `change-order-delete`, `change-order-implement`, `forecast-read`; admin/ai-admin have MCP permissions; ai-manager has `mcp-tool-execute` | Low |
| 3 | Fix `seed/users.json` | `backend/seed/users.json` | none | No user has role "contributor"; eng.lead and const.super users have role "manager" | Low |
| 4 | Add `seed_user_role_assignments()` to DataSeeder | `backend/app/db/seeder.py` | Task 1, 3 | Method creates GLOBAL `UserRoleAssignment` for each user; uses direct SQLAlchemy queries; idempotent via existence checks; logs created/skipped counts | Med |
| 5 | Update `seed_all()` call order | `backend/app/db/seeder.py` | Task 4 | `seed_user_role_assignments()` called after `seed_users()` and before `seed_co_workflow_config()` | Low |
| 6 | Add CI-sync test | `backend/tests/unit/db/test_rbac_config_sync.py` | Task 1, 2 | Test parses both JSON files and asserts same role names, same permission sets per role | Low |
| 7 | Add unit tests for `seed_user_role_assignments()` | `backend/tests/unit/db/test_seeder.py` | Task 4 | Tests for happy path, idempotency, missing role handling, empty users | Med |
| 8 | Run quality gates | all modified files | Tasks 1-7 | MyPy, Ruff, and pytest pass with zero errors and >= 80% coverage on modified code | Low |

### Test-to-Requirement Traceability

| Acceptance Criterion | Test ID | Test File | Expected Behavior |
|---|---|---|---|
| FR-1 (UserRoleAssignment records) | T-001 | `tests/unit/db/test_seeder.py` | `seed_user_role_assignments()` creates one global assignment per user |
| FR-2 (change_order_approver role) | T-002 | `tests/unit/db/test_rbac_config_sync.py` | Both JSON files contain `change_order_approver` role with 7 permissions |
| FR-3 (files in sync) | T-003 | `tests/unit/db/test_rbac_config_sync.py` | Parsed role/permission structures are identical between the two files |
| FR-4 (idempotency) | T-004 | `tests/unit/db/test_seeder.py` | Calling `seed_user_role_assignments()` twice produces no duplicates |
| FR-5 (post-migration compatibility) | T-005 | `tests/unit/db/test_seeder.py` | Method works when `user_role_assignments` already has rows |
| FR-1 edge (missing role) | T-006 | `tests/unit/db/test_seeder.py` | User with unrecognized role is skipped gracefully with a warning log |
| TC-1 (MyPy) | T-007 | CI pipeline | Zero MyPy errors on `app/db/seeder.py` |
| TC-2 (Ruff) | T-008 | CI pipeline | Zero Ruff errors on `app/db/seeder.py` |
| TC-3 (coverage) | T-009 | CI pipeline | >= 80% coverage on modified seeder code |

---

## Test Specification

### Test Hierarchy

```text
tests/
├── unit/
│   └── db/
│       ├── test_seeder.py                    (existing -- extend)
│       │   ├── TestSeedUserRoleAssignments   (new class)
│       │   │   ├── test_happy_path_creates_assignments
│       │   │   ├── test_idempotent_no_duplicates
│       │   │   ├── test_skips_user_with_missing_role
│       │   │   ├── test_handles_empty_users
│       │   │   └── test_works_after_migration
│       │   └── TestSeedAll                   (existing -- update)
│       │       └── test_seed_all_includes_user_role_assignments
│       └── test_rbac_config_sync.py          (new file)
│           └── TestRBACConfigSync
│               ├── test_same_role_names
│               ├── test_same_permissions_per_role
│               └── test_change_order_approver_exists
```

### Test Cases

| Test ID | Test Name | Criterion | Type | Expected Result |
|---|---|---|---|---|
| T-001 | `test_happy_path_creates_assignments` | FR-1 | Unit | After seeding 3 users with valid roles, exactly 3 `UserRoleAssignment` rows exist in the mock session, each with `scope_type='global'`, `scope_id=None`, and the correct `role_id` |
| T-002 | `test_change_order_approver_role_exists_in_seed` | FR-2 | Unit | `seed/rbac_roles.json` parses successfully and contains a `change_order_approver` key with 7 permissions |
| T-003 | `test_seed_and_config_have_identical_role_permissions` | FR-3 | Unit | For every role in `seed/rbac_roles.json`, the same role exists in `config/rbac.json` with the exact same permission set (sorted comparison) |
| T-004 | `test_idempotent_no_duplicates` | FR-4 | Unit | Calling `seed_user_role_assignments()` twice with the same users does not raise `IntegrityError` and the assignment count remains at 3 (not 6) |
| T-005 | `test_works_after_migration` | FR-5 | Unit | When the session already returns existing `UserRoleAssignment` rows matching the users, the method skips all of them and logs "skipped" count |
| T-006 | `test_skips_user_with_missing_role` | FR-1 edge | Unit | When one user has a role not found in `rbac_roles`, that user is skipped with a warning log; other users are still assigned |
| T-007 | `test_seed_all_includes_user_role_assignments` | FR-1 | Unit | `seed_all()` calls `seed_user_role_assignments()` after `seed_users()` |

### Test Infrastructure Needs

- **Fixtures**: Reuse existing `db_session` fixture from `tests/unit/db/test_seeder.py`. The `tmp_path` fixture for temporary seed files.
- **Mocks**: Mock `sqlalchemy.select` results to simulate existing users and roles without requiring a live database. Follow the pattern in existing `TestSeedUsers` (mock service, provide seed data via tmp_path).
- **Database state**: For the sync test (T-003), no database needed -- pure file parsing. For seeder tests (T-001, T-004, T-005, T-006), use the same mock-based approach as existing seeder tests in `test_seeder.py`.

---

## Risk Assessment

| Risk Type | Description | Probability | Impact | Mitigation |
|---|---|---|---|---|
| Technical | "contributor" role references exist elsewhere in codebase | Low | Low | Grep search confirms "contributor" only appears in `users.json` seed data |
| Technical | Future divergence of the two JSON files after this fix | Med | Med | CI-sync test (T-003) catches any divergence at PR time |
| Integration | Alembic migration `20260510b` runs on `alembic upgrade head` but reseed truncates tables first | Low | Low | Reseed truncates ALL tables except `alembic_version`, so migration data is gone; `seed_user_role_assignments()` starts clean |
| Integration | `seed_user_role_assignments()` fails if `rbac_roles` table is empty | Low | Med | Method is called after `seed_rbac_roles()` in `seed_all()` -- roles always exist |
| Data | Users with legacy role values not matching any RBAC role | Low | Low | After fixing `users.json`, all 5 users have valid role names (admin, viewer, manager, manager, manager). Graceful skip with warning log handles any future mismatch. |

---

## Task Dependency Graph

```yaml
# Task Dependency Graph
tasks:
  - id: BE-001
    name: "Synchronize seed/rbac_roles.json with change_order_approver and all permissions"
    agent: pdca-backend-do-executor
    dependencies: []

  - id: BE-002
    name: "Synchronize config/rbac.json to match seed file permissions"
    agent: pdca-backend-do-executor
    dependencies: [BE-001]

  - id: BE-003
    name: "Fix seed/users.json: change contributor to manager"
    agent: pdca-backend-do-executor
    dependencies: []

  - id: BE-004
    name: "Add seed_user_role_assignments() method to DataSeeder"
    agent: pdca-backend-do-executor
    dependencies: [BE-001, BE-003]

  - id: BE-005
    name: "Update seed_all() call order to include new method"
    agent: pdca-backend-do-executor
    dependencies: [BE-004]

  - id: BE-006
    name: "Add CI-sync test for rbac config file parity"
    agent: pdca-backend-do-executor
    dependencies: [BE-001, BE-002]

  - id: BE-007
    name: "Add unit tests for seed_user_role_assignments()"
    agent: pdca-backend-do-executor
    dependencies: [BE-004]

  - id: BE-008
    name: "Run quality gates (MyPy, Ruff, pytest) on modified code"
    agent: pdca-backend-do-executor
    dependencies: [BE-005, BE-006, BE-007]
    kind: test
```

### Execution Levels

```
Level 0 (parallel): BE-001, BE-003
Level 1 (parallel): BE-002 (after BE-001), BE-004 (after BE-001 + BE-003)
Level 2 (parallel): BE-005 (after BE-004), BE-006 (after BE-002), BE-007 (after BE-004)
Level 3 (serial):   BE-008 (after all above)
```

Note: All tasks are backend-only. Tests (BE-008) run serially last since they validate the combined output of all prior tasks. The CI-sync test (BE-006) is a pure file-comparison test with no database dependency but must run after both JSON files are synchronized.

---

## Documentation References

### Code References

- Seeder pattern: `backend/app/db/seeder.py` -- `seed_rbac_roles()` (line ~960) for direct SQLAlchemy query pattern
- Seed context: `backend/app/db/seed_context.py` -- `seed_operation()` context manager
- UserRoleAssignment model: `backend/app/models/domain/user_role_assignment.py`
- RBACRole model: `backend/app/models/domain/rbac.py`
- Reseed script: `backend/scripts/reseed_db.py`
- Existing test pattern: `backend/tests/unit/db/test_seeder.py` -- `TestSeedUsers` class

### Related Iterations

- Unified RBAC refactoring (parent): `docs/03-project-plan/iterations/2026-05-10-unified-rbac-refactoring/`
- CHECK report that identified these issues: `docs/03-project-plan/iterations/2026-05-10-unified-rbac-refactoring/03-check.md`

---

## Prerequisites

### Technical

- [x] Database migrations applied (unified RBAC schema exists)
- [x] `UserRoleAssignment` model exists with unique constraint
- [x] `RBACRole` and `RBACRolePermission` models exist
- [x] `seed_operation()` context manager available

### Documentation

- [x] Analysis phase approved
- [x] Architecture patterns reviewed (seed_rbac_roles direct query pattern)
- [x] User decisions recorded (contributor -> manager, seed file authority, CI test, global-only scope)
