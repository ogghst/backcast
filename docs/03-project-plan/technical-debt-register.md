# Technical Debt Register

**Last Updated:** 2026-01-11
**Total Debt Items:** 3 (7 completed)
**Total Estimated Effort:** 4 hours
**Completed Effort:** 11 hours

---

## Summary

| Severity | Items | Effort | % of Total |
| -------- | ----- | ------ | ---------- |
| High     | 1     | 1h     | 25%        |
| Medium   | 1     | 2h     | 50%        |
| Low      | 1     | 1h     | 25%        |

---

## Debt Items

### High Severity

#### [TD-026] Expose get_as_of in Service Interfaces

- **Source:** Documentation Audit (2026-01-11)
- **Description:** `TemporalService.get_as_of()` is implemented with full branch mode support and System Time Travel semantics, but individual service classes (e.g., `ProjectService`, `WBEService`) do not expose this method in their public interfaces.
- **Impact:** Developers cannot query entity state at specific timestamps via service layer; must either use `TemporalService` directly or rely on list endpoints with `as_of` parameter
- **Estimated Effort:** 1 hour
- **Target Date:** 2026-01-20
- **Status:** 🔴 Open
- **Owner:** Backend Developer
- **Proposed Solution:**
  1. Add `get_as_of(entity_id, as_of, branch, branch_mode)` method to each service that extends `TemporalService`
  2. Document in time-travel.md which services support time-travel queries
  3. Add tests for time-travel queries through service layer
- **Related Docs:** [time-travel.md](../02-architecture/cross-cutting/time-travel.md)

### Medium Severity

#### [TD-012] E2E Test Data Isolation ✅

- **Source:** E2E Test Stabilization ACT phase (2026-01-09)
- **Description:** E2E tests share database state, causing occasional flakiness when tests create data that affects pagination or search results in other tests.
- **Impact:** Test flakiness, false positives/negatives
- **Estimated Effort:** 3 hours
- **Actual Effort:** 1.5 hours
- **Target Date:** 2026-01-20
- **Status:** ✅ Complete (2026-01-09)
- **Owner:** Full Stack Developer
- **Solution:** Implemented Playwright global setup hook with database TRUNCATE before test suite
- **Documentation:**
  - [Analysis](./iterations/2026-01-09-e2e-test-isolation/00-ANALYSIS.md)
  - [Plan](./iterations/2026-01-09-e2e-test-isolation/01-PLAN.md)
  - [Implementation](./iterations/2026-01-09-e2e-test-isolation/02-DO.md)
  - [Check](./iterations/2026-01-09-e2e-test-isolation/03-CHECK.md)
  - [Act](./iterations/2026-01-09-e2e-test-isolation/04-ACT.md)

#### [TD-016] Performance Optimization (Large Projects)

- **Source:** Hierarchical Nav ACT phase
- **Description:** `useWBEs` fetches full list. Needs pagination or server-side tree loading for very large projects.
- **Impact:** Slow load times for large datasets
- **Estimated Effort:** 3 hours
- **Target Date:** 2026-02-01
- **Status:** 🔴 Open
- **Owner:** Full Stack Developer

#### [TD-024] Zombie Check TDD Pattern Documentation ✅

- **Source:** Time Travel List Standardization ACT phase (2026-01-10)
- **Description:** Document the "Create → Delete → Query Past" test pattern for verifying bitemporal history and zombie detection.
- **Impact:** Team may struggle with temporal testing without established patterns
- **Estimated Effort:** 1 hour
- **Actual Effort:** 1 hour
- **Target Date:** 2026-01-20
- **Status:** ✅ Complete (2026-01-11)
- **Owner:** Backend Developer
- **Solution:** Added comprehensive Zombie Check TDD section to time-travel.md with full test example
- **Documentation:**
  - [Iteration ACT](./iterations/2026-01-10-time-travel-list-standardization/04-ACT.md)
  - [time-travel.md](../02-architecture/cross-cutting/time-travel.md)

#### [TD-025] Frontend Lint Errors ✅

- **Source:** Frontend Error Handling iteration (2026-01-11)
- **Description:** 6 deferred lint errors unrelated to error handling functionality need resolution.
- **Impact:** Code quality maintenance debt
- **Estimated Effort:** 0.5 hours
- **Actual Effort:** 0.5 hours
- **Target Date:** 2026-01-15
- **Status:** ✅ Complete (2026-01-11)
- **Owner:** Frontend Developer
- **Solution:** Fixed 6 ESLint errors: removed unused imports, replaced `any` with proper types
- **Files Fixed:**
  - `frontend/src/features/wbes/api/useWBEs.test.tsx` - removed unused `waitFor` import, reordered vitest imports
  - `frontend/src/hooks/useTableParams.test.tsx` - added `TablePaginationConfig` type import
  - `frontend/src/pages/admin/UserList.test.tsx` - typed mock selector parameter
  - `frontend/src/stores/useTimeMachineStore.test.ts` - removed unused `vi` import
  - `frontend/src/utils/apiError.ts` - added `ValidationError` and `ApiErrorResponse` interfaces

---

### Low Severity

---

## Retired Debt

| ID | Item | Retired Date | Resolution |
| TD-012 | E2E Test Data Isolation | 2026-01-09 | Implemented Playwright global setup with TRUNCATE |
| TD-023 | Time-Travel Architecture Documentation | 2026-01-11 | Enhanced time-travel.md with bitemporal fundamentals, filter patterns, and Zombie Check TDD |
| TD-024 | Zombie Check TDD Pattern Documentation | 2026-01-11 | Added comprehensive Zombie Check TDD section with full test example to time-travel.md |
| TD-025 | Frontend Lint Errors | 2026-01-11 | Fixed 6 ESLint errors across test files and utilities |
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

---

## Maintenance Notes

**Last Reviewed:** 2026-01-11
**Next Review:** 2026-01-18

**Process:**

- Extract debt items from each iteration's ACT phase
- Assess severity and estimate effort
- Add to register within 24 hours of iteration completion
- Review and prioritize during sprint planning
- Track trends and prevent accumulation
