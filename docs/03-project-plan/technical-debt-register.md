# Technical Debt Register

**Last Updated:** 2026-01-09  
**Total Debt Items:** 2 (4 completed)  
**Total Estimated Effort:** 3 hours  
**Completed Effort:** 8.5 hours

---

## Summary

| Severity | Items | Effort | % of Total |
| -------- | ----- | ------ | ---------- |
| High     | 0     | 0h     | 0%         |
| Medium   | 1     | 2h     | 66%        |
| Low      | 1     | 1h     | 33%        |

---

## Debt Items

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

---

### Low Severity

---

## Retired Debt

| ID | Item | Retired Date | Resolution |
| TD-012 | E2E Test Data Isolation | 2026-01-09 | Implemented Playwright global setup with TRUNCATE |
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

**Last Reviewed:** 2026-01-09
**Next Review:** 2026-01-16

**Process:**

- Extract debt items from each iteration's ACT phase
- Assess severity and estimate effort
- Add to register within 24 hours of iteration completion
- Review and prioritize during sprint planning
- Track trends and prevent accumulation
