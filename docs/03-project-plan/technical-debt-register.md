# Technical Debt Register

**Last Updated:** 2026-01-06
**Total Debt Items:** 5
**Total Estimated Effort:** 18 hours

---

## Summary

| Severity | Items | Effort | % of Total |
| -------- | ----- | ------ | ---------- |
| High     | 2     | 10h    | 56%        |
| Medium   | 3     | 8h     | 44%        |
| Low      | 0     | 0h     | 0%         |

---

## Debt Items

### High Severity

#### [TD-001] Generic TemporalService get_by_root_id

- **Source:** Hybrid Sprint 2/3 ACT phase
- **Description:** Duplication in ProjectService and WBEService for root ID querying logic. Each service implements its own `get_by_root_id` instead of using a generic method.
- **Impact:** DRY violation, maintenance burden, inconsistent behavior across services
- **Estimated Effort:** 6 hours
- **Target Date:** 2026-01-10
- **Status:** 🔴 Open
- **Owner:** Backend Developer

#### [TD-002] Remaining Unit Test Failures

- **Source:** Hybrid Sprint 2/3 ACT phase
- **Description:** Unit tests in `tests/unit/core` and `test_integration_branch_service` are failing, reducing confidence in complex branching logic.
- **Impact:** Reduced confidence in complex branching features, potential undetected bugs
- **Estimated Effort:** 4 hours
- **Target Date:** 2026-01-10
- **Status:** 🔴 Open
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

_No low severity debt items._

---

## Debt Aging

| Age Bucket | Items | Effort | % of Total |
| ---------- | ----- | ------ | ---------- |
| < 1 week   | 2     | 10h    | 100%       |
| 1-2 weeks  | 0     | 0h     | 0%         |
| 2-4 weeks  | 0     | 0h     | 0%         |
| > 1 month  | 0     | 0h     | 0%         |

---

## Debt by Category

| Category         | Items | Effort |
| ---------------- | ----- | ------ |
| Code Duplication | 1     | 6h     |
| Test Coverage    | 1     | 4h     |
| Performance      | 0     | 0h     |
| Documentation    | 0     | 0h     |

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

| ID  | Item                                   | Retired Date | Resolution                       |
| --- | -------------------------------------- | ------------ | -------------------------------- |
| N/A | Backend test environment loop mismatch | 2026-01-06   | Fixed conftest.py fixture scopes |

---

## Maintenance Notes

**Last Reviewed:** 2026-01-06
**Next Review:** 2026-01-13

**Process:**

- Extract debt items from each iteration's ACT phase
- Assess severity and estimate effort
- Add to register within 24 hours of iteration completion
- Review and prioritize during sprint planning
