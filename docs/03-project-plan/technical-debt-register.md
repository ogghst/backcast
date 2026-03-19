# Technical Debt Register

**Last Updated:** 2026-03-19
**Total Open Items:** 4
**Total Estimated Effort:** 74 hours

---

This file tracks active technical debt items. For completed/closed debt, see [technical-debt-archive.md](./technical-debt-archive.md).

---

## Medium Severity (P2 - P3)

### [TD-016] Performance Optimization (Large Projects)

- **Source:** Hierarchical Nav ACT phase
- **Description:** `useWBEs` fetches full list. Needs pagination or server-side tree loading.
- **Impact:** Slow load times for large datasets
- **Estimated Effort:** 3 hours
- **Status:** 🔴 Open
- **Owner:** Full Stack Developer

---

### [TD-063] Add Zombie Check Tests for All Versioned Entities

- **Source:** Code Quality Cleanup ACT phase (2026-01-19)
- **Description:** Zombie check tests only implemented for forecasts. Need for Projects, WBEs, CostElements, etc.
- **Impact:** Data integrity verification for time-travel queries
- **Estimated Effort:** 1 day
- **Target Date:** 2026-01-22
- **Status:** 🔴 Open
- **Owner:** QA Engineer

---

### [TD-064] Docker Compose for Local Development

- **Source:** Temporal Context Consistency ACT phase (2026-01-19)
- **Description:** Need standardized Docker Compose setup for backend, frontend, and PostgreSQL.
- **Impact:** Prevents development blockages
- **Estimated Effort:** 3 hours
- **Status:** 🔴 Open
- **Owner:** Tech Lead

---

### [TD-065] Automate OpenAPI Client Generation in CI/CD

- **Source:** Temporal Context Consistency ACT phase (2026-01-19)
- **Description:** Manual type update required when OpenAPI spec regeneration failed.
- **Impact:** Ensures frontend-backend contract alignment
- **Estimated Effort:** 2 hours
- **Status:** 🔴 Open
- **Owner:** Frontend Developer

---

### [TD-082] Missing Archive Action for Rejected Change Orders

- **Source:** Change Order Workflow UI Test (2026-02-25)
- **Description:** UI only shows "Submit" action from Rejected state, missing "Archive" button.
- **Impact:** Incomplete workflow implementation
- **Estimated Effort:** 2 hours
- **Target Date:** 2026-03-15
- **Status:** 🔴 Open
- **Owner:** Frontend Developer
- **Priority:** Medium

---

## Summary

| Priority | Count | Total Effort |
|----------|-------|--------------|
| High (P0-P1) | 0 | 0 hours |
| Medium (P2-P3) | 4 | 74 hours |
| Low (P4+) | 0 | 0 hours |
| **Total** | **4** | **~74 hours** |

---

## Links

- [Technical Debt Archive](./technical-debt-archive.md) - Completed debt items (31 items)
- [Sprint Backlog](./sprint-backlog.md) - Current iteration
- [Product Backlog](./product-backlog.md) - All pending work
