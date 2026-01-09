# Technical Debt Register

**Last Updated:** 2026-01-09
**Total Debt Items:** 6
**Total Estimated Effort:** 13 hours

---

## Summary

| Severity | Items | Effort | % of Total |
| -------- | ----- | ------ | ---------- |
| High     | 0     | 0h     | 0%         |
| Medium   | 5     | 12h    | 92%        |
| Low      | 1     | 1h     | 8%         |

---

## Debt Items

### Medium Severity

#### [TD-012] E2E Test Data Isolation

- **Source:** E2E Test Stabilization ACT phase (2026-01-09)
- **Description:** E2E tests share database state, causing occasional flakiness when tests create data that affects pagination or search results in other tests.
- **Impact:** Test flakiness, false positives/negatives
- **Estimated Effort:** 3 hours
- **Target Date:** 2026-01-20
- **Status:** 🔴 Open
- **Owner:** Full Stack Developer
- **Recommendation:** Implement test data cleanup hooks or database isolation strategies

#### [TD-013] FilterParser Error Messages

- **Source:** E2E Test Stabilization ACT phase (2026-01-09)
- **Description:** FilterParser provides generic error messages when filters fail. Could be more helpful for debugging.
- **Impact:** Harder to debug filter issues
- **Estimated Effort:** 2 hours
- **Target Date:** 2026-01-25
- **Status:** 🔴 Open
- **Owner:** Backend Developer
- **Recommendation:** Add specific error messages for type mismatches, invalid fields, etc.

#### [TD-014] Frontend Filter Type Safety

- **Source:** E2E Test Stabilization ACT phase (2026-01-09)
- **Description:** Frontend filter types use `Record<string, any>` instead of strict typing based on entity schemas.
- **Impact:** Potential runtime errors, loss of type safety
- **Estimated Effort:** 3 hours
- **Target Date:** 2026-01-25
- **Status:** 🔴 Open
- **Owner:** Frontend Developer
- **Recommendation:** Generate filter types from OpenAPI schema or create strict filter interfaces

#### [TD-015] useTableParams Type Safety

- **Source:** E2E Test Stabilization ACT phase (2026-01-09)
- **Description:** `useTableParams` hook uses loose typing for filters and sort fields. Should be generic with entity-specific types.
- **Impact:** Loss of type safety, harder to catch errors at compile time
- **Estimated Effort:** 2 hours
- **Target Date:** 2026-01-30
- **Status:** 🔴 Open
- **Owner:** Frontend Developer
- **Recommendation:** Refactor to accept generic type parameter for entity

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

#### [TD-017] Remaining Page-Level API Adapters

- **Source:** Frontend Architecture Cleanup ACT phase
- **Description:** 5 page-level files still use legacy adapter pattern (UserList, DepartmentManagement, CostElementTypeManagement, CostElementManagement, WBEList). These work fine due to backward compatibility but could be migrated to named methods pattern.
- **Impact:** Minor code duplication, inconsistent patterns
- **Estimated Effort:** 1 hour
- **Target Date:** 2026-01-15
- **Status:** 🟡 Open
- **Owner:** Frontend Developer

---

## Debt Aging

| Age Bucket | Items | Effort | % of Total |
| ---------- | ----- | ------ | ---------- |
| < 1 week   | 4     | 10h    | 77%        |
| 1-2 weeks  | 2     | 3h     | 23%        |
| 2-4 weeks  | 0     | 0h     | 0%         |
| > 1 month  | 0     | 0h     | 0%         |

---

## Debt by Category

| Category       | Items | Effort |
| -------------- | ----- | ------ |
| Type Safety    | 2     | 5h     |
| Test Quality   | 1     | 3h     |
| Performance    | 1     | 3h     |
| Error Handling | 1     | 2h     |
| Architecture   | 1     | 1h     |

---

## Paydown Plan

**Current Sprint Allocation:** 3-4 hours for debt paydown

**Target:** Reduce type safety debt by 2026-01-30

**Strategy:**

1. Prioritize TD-003 (test isolation) to improve test reliability
2. Address TD-004 and TD-005 (type safety) together for efficiency
3. Allocate 20% of each sprint to debt paydown
4. Bundle related items for efficiency
5. Track debt trends and prevent accumulation

---

## Retired Debt

| ID     | Item                                   | Retired Date | Resolution                                                                 |
| ------ | -------------------------------------- | ------------ | -------------------------------------------------------------------------- |
| N/A    | Backend test environment loop mismatch | 2026-01-06   | Fixed conftest.py fixture scopes                                           |
| TD-001 | Generic TemporalService get_by_root_id | 2026-01-07   | Added `get_by_root_id` to `TemporalService[T]`, removed duplicate wrappers |
| TD-006 | `useUserStore` server state violation  | 2026-01-07   | Deleted store; verified unused in production code                          |
| TD-008 | Inconsistent Zustand middleware        | 2026-01-07   | Refactored all stores to use `immer` middleware                            |
| TD-009 | Duplicate history hooks                | 2026-01-07   | Standardized on generic `useEntityHistory` hook                            |
| TD-010 | API adapter duplication                | 2026-01-07   | Added named methods support to `createResourceHooks` (backward compatible) |
| TD-011 | Hardcoded pagination values            | 2026-01-07   | Centralized in `constants/pagination.ts`                                   |
| TD-002 | Remaining Unit Test Failures           | 2026-01-07   | Fixed field naming mismatch in tests; verified integration stability       |

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
