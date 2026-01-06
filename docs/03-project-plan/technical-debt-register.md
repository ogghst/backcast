# Technical Debt Register

**Last Updated:** 2026-01-06
**Total Debt Items:** 2
**Total Estimated Effort:** 10 hours

---

## Summary

| Severity | Items | Effort | % of Total |
|----------|-------|--------|------------|
| High     |   2   |  10h   |    100%    |
| Medium   |   0   |   0h   |     0%     |
| Low      |   0   |   0h   |     0%     |

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

---

### Medium Severity

_No medium severity debt items._

---

### Low Severity

_No low severity debt items._

---

## Debt Aging

| Age Bucket | Items | Effort | % of Total |
|------------|-------|--------|------------|
| < 1 week   |   2   |  10h   |    100%    |
| 1-2 weeks  |   0   |   0h   |      0%    |
| 2-4 weeks  |   0   |   0h   |      0%    |
| > 1 month  |   0   |   0h   |      0%    |

---

## Debt by Category

| Category              | Items | Effort |
| --------------------- | ----- | ------ |
| Code Duplication      | 1     | 6h     |
| Test Coverage         | 1     | 4h     |
| Performance           | 0     | 0h     |
| Documentation         | 0     | 0h     |

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

| ID   | Item                                 | Retired Date | Resolution                                   |
| ---- | ------------------------------------ | ------------ | --------------------------------------------- |
| N/A  | Backend test environment loop mismatch | 2026-01-06   | Fixed conftest.py fixture scopes              |

---

## Maintenance Notes

**Last Reviewed:** 2026-01-06
**Next Review:** 2026-01-13

**Process:**
- Extract debt items from each iteration's ACT phase
- Assess severity and estimate effort
- Add to register within 24 hours of iteration completion
- Review and prioritize during sprint planning
