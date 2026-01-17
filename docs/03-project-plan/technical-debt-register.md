# Technical Debt Register

**Last Updated:** 2026-01-15
**Total Debt Items:** 8 (20 completed)
**Total Estimated Effort:** 17 hours
**Completed Effort:** 19.25 hours

---

## Debt Items

### High Severity

#### [TD-060] Backend Test Environment Subprocess Failure

- **Source:** Fix Overlapping Valid Time Iteration (2026-01-16)
- **Description:** `wipe_db.py` subprocess call in `conftest.py` fails with various errors (python path, env vars) in local/agent environment, blocking test execution.
- **Impact:** Cannot run backend tests reliably; blocks verification of fixes.
- **Estimated Effort:** 2 hours
- **Target Date:** 2026-01-17
- **Status:** 🔴 Open
- **Owner:** DevOps / Backend Lead
- **Notes:** Seems related to how `sys.executable` or `os.environ` behaves in `uv run` context vs direct execution.

---

### Medium Severity

#### [TD-016] Performance Optimization (Large Projects)

- **Source:** Hierarchical Nav ACT phase
- **Description:** `useWBEs` fetches full list. Needs pagination or server-side tree loading for very large projects.
- **Impact:** Slow load times for large datasets
- **Estimated Effort:** 3 hours
- **Target Date:** 2026-02-01
- **Status:** 🔴 Open
- **Owner:** Full Stack Developer

#### [TD-049] Change Order Merge Test Implementation

- **Source:** Phase 1 Change Orders ACT phase (2026-01-12)
- **Description:** `test_merge_change_order` test fails because merge functionality is deferred to Phase 4. Test expectations written before implementation planned.
- **Impact:** 1 test failure blocks CI (currently skipped/deferred)
- **Estimated Effort:** 2 hours
- **Target Date:** Phase 4 (2026-01-26)
- **Status:** 🔴 Open
- **Owner:** Backend Developer
- **Notes:** Merge workflow will be implemented in Phase 4, test should be enabled then
- **Documentation:** [Phase 1 ACT](./iterations/2026-01-11-change-orders-implementation/phase1/04-act.md)

#### [TD-057] MERGE Mode Branch Deletion Detection

- **Source:** EVCS Documentation Compliance Analysis (2026-01-14)
- **Description:** `get_as_of()` with MERGE mode falls back to main branch even when entity is deleted on requested branch. The `_is_deleted_on_branch()` check may not properly detect deleted entities during fallback.
- **Impact:** Zombie check test `test_wbe_zombie_check_merge_mode_no_fallback` fails; deleted entities on branches incorrectly appear in MERGE mode queries
- **Estimated Effort:** 2 hours
- **Target Date:** 2026-01-20
- **Status:** 🔴 Open
- **Owner:** Backend Developer
- **Notes:** Expected behavior: deleted entities on a branch should NOT fall back to main during MERGE mode queries. The `_is_deleted_on_branch()` method in TemporalService/BranchableService needs investigation.
- **Documentation:** [EVCS Implementation Guide](../02-architecture/backend/contexts/evcs-core/evcs-implementation-guide.md), [Temporal Query Reference](../02-architecture/cross-cutting/temporal-query-reference.md)
- **Test File:** [tests/unit/test_zombie_checks.py](../../backend/tests/unit/test_zombie_checks.py)

---

### Low Severity

#### [TD-059] WBE Hierarchical Filter API Response Format

- **Source:** Backend Test Suite Run (2026-01-14)
- **Description:** `test_get_wbes_param_filter` fails with `TypeError: string indices must be integers, not 'str'` when querying `/api/v1/wbes?parent_wbe_id=null`. The API response format doesn't match expected list of dictionaries structure.
- **Impact:** Hierarchical WBE filtering (parent_wbe_id parameter) returns incorrect response format; test blocked
- **Estimated Effort:** 1 hour
- **Target Date:** 2026-01-20
- **Status:** 🔴 Open
- **Owner:** Backend Developer
- **Notes:**
  - Test expects: List of WBE dictionaries with `code` field
  - Actual response: Unknown type (likely error dict or string)
  - May be related to parameter parsing for `parent_wbe_id=null` string value
  - Pre-existing issue, unrelated to temporal query changes
- **Test File:** [tests/api/test_wbes.py](../../backend/tests/api/test_wbes.py#L548)
- **Error:** `TypeError: string indices must be integers, not 'str'` at `assert any(w["code"] == "TF-1" for w in data_null)`

#### [TD-050] Change Order API Error Path Coverage

- **Source:** Phase 1 Change Orders CHECK phase (2026-01-12)
- **Description:** Change Order API routes have 56.63% coverage. Error paths not fully tested (40+ uncovered lines).
- **Impact:** Reduced confidence in error handling
- **Estimated Effort:** 4 hours
- **Target Date:** Phase 2 (2026-01-19)
- **Status:** 🔴 Open
- **Owner:** QA Engineer
- **Notes:** Critical paths covered, error paths can be addressed in Phase 2
- **Documentation:** [Phase 1 CHECK](./iterations/2026-01-11-change-orders-implementation/phase1/03-check.md)

#### [TD-052] Test Execution Location Documentation

- **Source:** Phase 1 Change Orders ACT phase (2026-01-12)
- **Description:** Tests must be run from `backend/` directory, not project root. Alembic config path issue causes confusion.
- **Impact:** Developers may run tests incorrectly, get confusing errors
- **Estimated Effort:** 1 hour
- **Target Date:** 2026-01-15
- **Status:** 🔴 Open
- **Owner:** Tech Lead
- **Solution:** Add note to project README about test execution location
- **Documentation:** [Phase 1 ACT](./iterations/2026-01-11-change-orders-implementation/phase1/04-act.md)

#### [TD-053] Domain Model Test Coverage

- **Source:** Branch Mode Support ACT phase (2026-01-13)
- **Description:** Backend coverage 56.81% (below 80% target). Domain models (mostly data classes) lack tests. Service layer well covered.
- **Impact:** Reduced overall coverage metric
- **Estimated Effort:** 2 hours
- **Target Date:** 2026-01-30
- **Status:** 🔴 Open
- **Owner:** Backend Developer
- **Notes:** Data classes provide minimal value to test. Acceptable baseline for this iteration.
- **Documentation:** [Branch Mode CHECK](./iterations/2026-01-12-merge-isolation-strategies/03-check.md)

---

## Retired Debt

| ID     | Item                                         | Retired Date | Resolution                                                                                               |
| ------ | -------------------------------------------- | ------------ | -------------------------------------------------------------------------------------------------------- |
| TD-012 | E2E Test Data Isolation                      | 2026-01-09   | Implemented Playwright global setup with TRUNCATE                                                        |
| TD-023 | Time-Travel Architecture Documentation       | 2026-01-11   | Enhanced temporal-query-reference.md with bitemporal fundamentals, filter patterns, and Zombie Check TDD |
| TD-024 | Zombie Check TDD Pattern Documentation       | 2026-01-11   | Added comprehensive Zombie Check TDD section with full test example to temporal-query-reference.md       |
| TD-025 | Frontend Lint Errors                         | 2026-01-11   | Fixed 6 ESLint errors across test files and utilities                                                    |
| TD-026 | Expose get_as_of in Service Interfaces       | 2026-01-11   | Added `get_{entity}_as_of()` methods to 6 services                                                       |
| TD-027 | BranchableSoftDeleteCommand Implementation   | 2026-01-12   | Implemented branch-aware soft delete for multi-branch entities                                           |
| TD-028 | Control Date Handling in CreateBranchCommand | 2026-01-12   | Fixed duplicate records issue by adding control_date parameter                                           |
| TD-029 | WBE/CostElement BranchableService Extension  | 2026-01-12   | Extended WBE and CostElement services to use BranchableService                                           |
| TD-030 | Backend Ruff Linting Errors (Phase 1)        | 2026-01-12   | Fixed 6 linting errors: import organization and trailing whitespace                                      |
| TD-031 | Change Order Field Name Override Pattern     | 2026-01-12   | Documented acceptable pattern for custom field names in BranchableService                                |
| TD-013 | FilterParser Error Messages                  | 2026-01-09   | Implemented strict type validation, custom exceptions, and global 400 handler                            |
| TD-014 | Frontend Filter Type Safety                  | 2026-01-09   | Implemented strict `Filterable` types and migrated 7 components                                          |
| TD-015 | useTableParams Type Safety                   | 2026-01-09   | Refactored hook to use `TEntity` and `TFilters` generics                                                 |
| TD-017 | Remaining Page-Level API Adapters            | 2026-01-09   | Migrated 5 files to named methods pattern                                                                |
| N/A    | Backend test environment loop mismatch       | 2026-01-06   | Fixed conftest.py fixture scopes                                                                         |
| TD-001 | Generic TemporalService get_by_root_id       | 2026-01-07   | Added `get_by_root_id` to `TemporalService[T]`, removed duplicate wrappers                               |
| TD-006 | `useUserStore` server state violation        | 2026-01-07   | Deleted store; verified unused in production code                                                        |
| TD-008 | Inconsistent Zustand middleware              | 2026-01-07   | Refactored all stores to use `immer` middleware                                                          |
| TD-009 | Duplicate history hooks                      | 2026-01-07   | Standardized on generic `useEntityHistory` hook                                                          |
| TD-010 | API adapter duplication                      | 2026-01-07   | Added named methods support to `createResourceHooks` (backward compatible)                               |
| TD-011 | Hardcoded pagination values                  | 2026-01-07   | Centralized in `constants/pagination.ts`                                                                 |
| TD-002 | Remaining Unit Test Failures                 | 2026-01-07   | Fixed field naming mismatch in tests; verified integration stability                                     |
| TD-051 | Time Travel Parameter Type Handling          | 2026-01-12   | Updated BranchableService.get_as_of signature to accept branch_mode and implemented MERGE logic          |
| TD-054 | Ruff Linting Errors (Branch Mode)            | 2026-01-13   | Fixed 12 auto-fixable errors (imports, whitespace)                                                       |
| TD-055 | Unused Imports (Frontend Components)         | 2026-01-13   | Removed unused imports from ViewModeSelector, TimeMachineCompact                                         |
| TD-058 | Overlapping valid_time Constraint            | 2026-01-16   | Implemented application-level checks in commands                                                         |

---

## Maintenance Notes

**Last Reviewed:** 2026-01-15
**Next Review:** 2026-01-22

**Process:**

- Extract debt items from each iteration's ACT phase
- Assess severity and estimate effort
- Add to register within 24 hours of iteration completion
- Review and prioritize during sprint planning
- Track trends and prevent accumulation

**Recent Trends:**

- **2026-01-16 - Fix Overlapping Valid Time:** Addressed TD-058 by implementing strict overlap checks in `branching` and `versioning` core commands. Added TD-060 due to test environment failures blocking verification.
- **2026-01-15 - Contextual Navigation Iteration:** Completed with zero new technical debt items. All code followed best practices with ~100% test coverage. Standardized URL-driven navigation pattern for future entity detail pages.
- **2026-01-14 - Time Travel Bug Fix:** Completed TD-058 analysis and workaround (removed `transaction_time` filtering from `_apply_bitemporal_filter`), documented in technical debt register. Updated both `BranchableService` and `TemporalService` with `valid_time`-only filtering approach.
- **2026-01-14 - Test Suite Results:** Backend tests at 99.2% pass rate (253/255). Added TD-059 for pre-existing `test_get_wbes_param_filter` API response format issue.
- **2026-01-14 - Documentation Updates:** Updated temporal-query-reference.md and technical-debt-register.md to reflect new `valid_time`-only approach for time travel queries.
- Net debt change: 0 items, 0 hours effort (this iteration)
- Overall debt trend: Stable (8 open items, no new debt added)
