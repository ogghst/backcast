# Technical Debt Register

**Last Updated:** 2026-03-14
**Total Open Items:** 6
**Total Estimated Effort:** 102 hours

---

This file tracks active technical debt items. For completed/closed debt, see [technical-debt-archive.md](./technical-debt-archive.md).

---

## High Severity (P0 - P1)

### [TD-067] FK Constraint: Business Key vs Primary Key in Temporal Entities

- **Source:** Change Order Workflow Recovery (2026-02-06)
- **Description:** `ChangeOrder.assigned_approver_id` foreign key references `users(id)` (auto-generated primary key) instead of `users(user_id)` (business key). This causes issues in bitemporal queries because PK changes across versions while business key remains stable.
- **Impact:** Data integrity issues in bitemporal queries; using PK may return wrong or expired versions
- **Estimated Effort:** 2-3 days (16-24 hours)
- **Target Date:** 2026-02-15
- **Status:** 🔴 Open
- **Owner:** Backend Developer
- **Priority:** High
- **Risk:** Data integrity issues in bitemporal queries
- **Action Items:**
  - [ ] Audit all FK references in temporal entities
  - [ ] Create migration plan
  - [ ] Update coding standards
  - [ ] Schedule implementation iteration
- **References:** ADR-005 Bitemporal Versioning, CO-2026-003 recovery

---

### [TD-074] WebSocket Protocol Unit Tests Missing

- **Source:** WebSocket Streaming Implementation (2026-03-08)
- **Description:** Comprehensive unit tests for WebSocket message protocol not implemented.
- **Impact:** Test coverage ~75%, below 80% target
- **Estimated Effort:** 4 hours
- **Target Date:** 2026-03-15
- **Status:** 🔴 Open
- **Owner:** QA/Test Developer
- **Priority:** Medium (P2)
- **Action Items:**
  - [ ] Document WebSocket mocking strategy
  - [ ] Add connection lifecycle tests
  - [ ] Add streaming token tests
  - [ ] Add reconnection logic tests

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
| High (P0-P1) | 2 | 20-24 hours |
| Medium (P2-P3) | 4 | 66-76 hours |
| Low (P4+) | 0 | 0 hours |
| **Total** | **6** | **~102 hours** |

## Summary

| Priority | Count | Total Effort |
|----------|-------|--------------|
| High (P0-P1) | 3 | 24-28 hours |
| Medium (P2-P3) | 4 | 66-76 hours |
| Low (P4+) | 1 | 1 hour |
| **Total** | **8** | **~107 hours** |

---

## Links

- [Technical Debt Archive](./technical-debt-archive.md) - Completed debt items (27 items)
- [Sprint Backlog](./sprint-backlog.md) - Current iteration
- [Product Backlog](./product-backlog.md) - All pending work
