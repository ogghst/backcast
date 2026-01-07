# Technical Debt Register

**Last Updated:** 2026-01-07
**Total Debt Items:** 4
**Total Estimated Effort:** 9 hours

---

## Summary

| Severity | Items | Effort | % of Total |
| -------- | ----- | ------ | ---------- |
| High     | 1     | 4h     | 31%        |
| Medium   | 3     | 8h     | 62%        |
| Low      | 1     | 1h     | 7%         |

---

## Debt Items

### High Severity

#### [TD-002] Remaining Unit Test Failures

- **Source:** Hybrid Sprint 2/3 ACT phase
- **Description:** Unit tests in `tests/unit/core` and `test_integration_branch_service` are failing, reducing confidence in complex branching logic.
- **Impact:** Reduced confidence in complex branching features, potential undetected bugs
- **Estimated Effort:** 4 hours
- **Target Date:** 2026-01-10
- **Status:** ✅ Closed
- **Owner:** Backend Developer

### Medium Severity

#### [TD-003] Frontend Types Casting

- **Source:** Hierarchical Nav ACT phase
- **Description:** Loose `as any` casting in `useCrud` hooks and table components. Needs strict typing matching generated API clients.
- **Impact:** Potential runtime errors, loss of type safety
- **Estimated Effort:** 3 hours
- **Target Date:** 2026-01-20
- **Status:** 🔴 Open
- **Owner:** Frontend Developer

#### [TD-004] Performance Optimization (Large Projects)

- **Source:** Hierarchical Nav ACT phase
- **Description:** `useWBEs` fetches full list. Needs pagination or server-side tree loading for very large projects.
- **Impact:** Slow load times for large datasets
- **Estimated Effort:** 3 hours
- **Target Date:** 2026-02-01
- **Status:** 🔴 Open
- **Owner:** Full Stack Developer

#### [TD-005] UI/UX Tree View

- **Source:** Hierarchical Nav ACT phase
- **Description:** Current list/table view is functional but a true Tree View would be better for hierarchy visualization.
- **Impact:** Sub-optimal UX for complex nested structures
- **Estimated Effort:** 2 hours
- **Target Date:** 2026-02-01
- **Status:** 🔴 Open
- **Owner:** Frontend Developer

---

### Low Severity

#### [TD-007] Remaining Page-Level API Adapters

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
| < 1 week   | 3     | 11h    | 58%        |
| 1-2 weeks  | 3     | 8h     | 42%        |
| 2-4 weeks  | 0     | 0h     | 0%         |
| > 1 month  | 0     | 0h     | 0%         |

---

## Debt by Category

| Category         | Items | Effort |
| ---------------- | ----- | ------ |
| Code Duplication | 2     | 7h     |
| Test Coverage    | 1     | 4h     |
| Performance      | 1     | 3h     |
| UI/UX            | 1     | 2h     |
| Architecture     | 1     | 1h     |

---

## Paydown Plan

**Current Sprint Allocation:** TBD hours for debt paydown

**Target:** Reduce all high severity debt by 2026-01-10

**Strategy:**

1. Prioritize TD-002 (test failures) to restore confidence
2. Refactor TD-001 (duplication) as part of E03-U06 implementation
3. Allocate 20% of each sprint to debt paydown
4. Bundle related items for efficiency

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

**Last Reviewed:** 2026-01-07
**Next Review:** 2026-01-14

**Process:**

- Extract debt items from each iteration's ACT phase
- Assess severity and estimate effort
- Add to register within 24 hours of iteration completion
- Review and prioritize during sprint planning
