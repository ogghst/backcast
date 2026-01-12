# Technical Debt Register

**Last Updated:** 2026-01-13
**Total Debt Items:** 5 (16 completed)
**Total Estimated Effort:** 12 hours
**Completed Effort:** 19.25 hours

---

## Summary

| Severity | Items | Effort | % of Total |
| -------- | ----- | ------ | ---------- |
| High     | 0     | 0h     | 0%         |
| Medium   | 2     | 5h     | 83%        |
| Low      | 3     | 7h     | 58%        |

---

## Debt Items

### High Severity

_No high severity debt items._

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

---

### Low Severity

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

| ID | Item | Retired Date | Resolution |
| --- | ---- | ----------- | ---------- |
| TD-012 | E2E Test Data Isolation | 2026-01-09 | Implemented Playwright global setup with TRUNCATE |
| TD-023 | Time-Travel Architecture Documentation | 2026-01-11 | Enhanced time-travel.md with bitemporal fundamentals, filter patterns, and Zombie Check TDD |
| TD-024 | Zombie Check TDD Pattern Documentation | 2026-01-11 | Added comprehensive Zombie Check TDD section with full test example to time-travel.md |
| TD-025 | Frontend Lint Errors | 2026-01-11 | Fixed 6 ESLint errors across test files and utilities |
| TD-026 | Expose get_as_of in Service Interfaces | 2026-01-11 | Added `get_{entity}_as_of()` methods to 6 services |
| TD-027 | BranchableSoftDeleteCommand Implementation | 2026-01-12 | Implemented branch-aware soft delete for multi-branch entities |
| TD-028 | Control Date Handling in CreateBranchCommand | 2026-01-12 | Fixed duplicate records issue by adding control_date parameter |
| TD-029 | WBE/CostElement BranchableService Extension | 2026-01-12 | Extended WBE and CostElement services to use BranchableService |
| TD-030 | Backend Ruff Linting Errors (Phase 1) | 2026-01-12 | Fixed 6 linting errors: import organization and trailing whitespace |
| TD-031 | Change Order Field Name Override Pattern | 2026-01-12 | Documented acceptable pattern for custom field names in BranchableService |
| TD-013 | FilterParser Error Messages | 2026-01-09 | Implemented strict type validation, custom exceptions, and global 400 handler |
| TD-014 | Frontend Filter Type Safety | 2026-01-09 | Implemented strict `Filterable` types and migrated 7 components |
| TD-015 | useTableParams Type Safety | 2026-01-09 | Refactored hook to use `TEntity` and `TFilters` generics |
| TD-017 | Remaining Page-Level API Adapters | 2026-01-09 | Migrated 5 files to named methods pattern |
| N/A | Backend test environment loop mismatch | 2026-01-06 | Fixed conftest.py fixture scopes |
| TD-001 | Generic TemporalService get_by_root_id | 2026-01-07 | Added `get_by_root_id` to `TemporalService[T]`, removed duplicate wrappers |
| TD-006 | `useUserStore` server state violation | 2026-01-07 | Deleted store; verified unused in production code |
| TD-008 | Inconsistent Zustand middleware | 2026-01-07 | Refactored all stores to use `immer` middleware |
| TD-009 | Duplicate history hooks | 2026-01-07 | Standardized on generic `useEntityHistory` hook |
| TD-010 | API adapter duplication | 2026-01-07 | Added named methods support to `createResourceHooks` (backward compatible) |
| TD-011 | Hardcoded pagination values | 2026-01-07 | Centralized in `constants/pagination.ts` |
| TD-002 | Remaining Unit Test Failures | 2026-01-07 | Fixed field naming mismatch in tests; verified integration stability |
| TD-051 | Time Travel Parameter Type Handling | 2026-01-12 | Updated BranchableService.get_as_of signature to accept branch_mode and implemented MERGE logic |
| TD-054 | Ruff Linting Errors (Branch Mode) | 2026-01-13 | Fixed 12 auto-fixable errors (imports, whitespace) |
| TD-055 | Unused Imports (Frontend Components) | 2026-01-13 | Removed unused imports from ViewModeSelector, TimeMachineCompact |
| TD-056 | MyPy Query Examples Type Error | 2026-01-13 | Removed examples parameter from Query() in projects.py and wbes.py |

---

## Maintenance Notes

**Last Reviewed:** 2026-01-13
**Next Review:** 2026-01-20

**Process:**

- Extract debt items from each iteration's ACT phase
- Assess severity and estimate effort
- Add to register within 24 hours of iteration completion
- Review and prioritize during sprint planning
- Track trends and prevent accumulation

**Recent Trends:**

- Branch Mode Support: Created 1 new item (TD-053), resolved 3 items (TD-054, TD-055, TD-056)
- Net debt change: +1 item, -15 minutes cleanup effort
- Overall debt trend: Stable (5 open items)
