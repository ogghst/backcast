# Current Iteration

**Iteration:** FK Constraint Migration (Technical Debt)
**Start Date:** 2026-02-07
**Status:** 🏗️ **IN PLANNING**

---

## Goal

Migrate all temporal entity foreign keys to reference stable Business Keys (e.g., `user_id`, `project_id`) instead of auto-generated Primary Keys (`id`) to ensure bitemporal data integrity.

**Key Focus Areas:**

1. **Audit**: Identify all PK-based FKs in temporal entities
2. **Migration**: Create and test Alembic migrations for Option 1 (Preferred)
3. **Standards**: Update coding standards and validation guidelines

---

## Stories in Scope

| Story                                           | Points | Priority | Status          | Dependencies     |
| :---------------------------------------------- | :----- | :------- | :-------------- | :--------------- |
| **[TD-001] Audit FKs in Temporal Entities**      | 3      | High     | 📅 To Do        | N/A              |
| **[TD-002] Implement Option 1 Migration**       | 13     | High     | 📅 To Do        | TD-001           |
| **[TD-003] Update Coding Standards**            | 2      | Medium   | 📅 To Do        | TD-002           |

**Total Estimated Effort:** 18 points

---

## Success Criteria

- [ ] All temporal entities use business key FKs
- [ ] Migration script tested and validated
- [ ] Coding standards updated in documentation
- [ ] No data loss or corruption during migration

---

## Iteration Records

### Recent Completed Iterations

- **Backend RSC Compliance (2026-02-07):** ✅ Complete
  - Refactored `ChangeOrderService` audit logging
  - Implemented `UpdateChangeOrderStatusCommand`
  - Enforced Command pattern for state changes
  - Verified with comprehensive test suite

- **Workflow Recovery & Hardening (2026-02-06):** ✅ Complete
  - Admin Recovery API and UI implemented
  - Impact Analysis Timeout (300s) added
  - Resolved CO-2026-003 stuck workflow
  - Root cause (FK Mismatch) identified and documented

- **Phase 6: Change Order Workflow Integration (2026-02-05):** ✅ Complete
  - Automatic impact analysis on creation
  - Weighted impact severity scoring (0-100+)
  - Impact-based approver routing (LOW to CRITICAL)
  - Submission validation logic

- **Phase 5: Advanced Impact Analysis (2026-02-05):** ✅ Complete
  - Schedule baseline comparison (duration deltas)
  - EVM Performance Index projections (CPI/SPI/TCPI/EAC)
  - VAC projections and KPI scorecard extension

- **EVM Foundation Implementation (E08) (2026-02-03):** ✅ Complete
  - PV, EV, AC calculations
  - Performance indices (CPI/SPI)
  - EVM Dashboard and trend visualization

- **Branch Entity Versionable (2026-01-29):** ✅ Complete
  - Added `VersionableMixin` to Branch model
  - Implemented temporal query support (`get_as_of`, `list_branches_as_of`)
  - Added `branch_id` UUID as stable root identifier
  - Migration created and applied

- **Merge Branch Logic (2026-01-26):** ✅ Complete
  - `ChangeOrderService.merge_change_order` implementation
  - API `POST /merge` with conflict handling (409 Conflict)
  - Conflict detection for nested modifications

- **TD-058: Overlapping Valid Time Fix (2026-01-27):** ✅ Complete
  - Fixed merge mode deletion causing overlapping valid_time ranges
  - Added overlap checks to merge and revert commands

- **EVM Time Series Implementation (2026-01-23):** ✅ Complete
  - EVM calculations with time-phased data
  - Historical trend support

- **EVM Analyzer Master-Detail UI (2026-01-22):** ✅ Complete
  - Enhanced EVM analysis charts
  - CPI vs SPI Performance Indices chart

- **Progress Entries UI (E05-U03):** ✅ Complete (2026-01-22)
  - Frontend Progress Entries Tab
  - Progress Entry Modal for creating/editing entries
  - Query keys and API hooks

- **Schedule Baseline & Forecast Management (2026-01-17):** ✅ Complete
  - Schedule Baseline model with progression types
  - Cost Registration model and API
  - Forecast 1:1 relationship with Cost Element
  - Nested endpoints: `/cost-elements/{id}/schedule-baseline`, `/cost-elements/{id}/forecast`

---

## Previous Iterations

- **[2026-01-19] Temporal and Branch Context Consistency:** ✅ Complete (100%)
- **[2026-01-19] Code Quality Cleanup:** ✅ Complete (100%)
- **[2026-01-19] Complete Query Key Factory:** ✅ Complete (100%)
- **[2026-01-18] Refactor TanStack Query:** ✅ Complete (100%)
- **[2026-01-18] EVM Foundation:** ✅ Complete (100%)
- **[2026-01-18] One Forecast Per Cost Element:** ✅ Complete (100%)
- **[2026-01-16] Fix Overlapping Valid Time:** ✅ Complete (100%)
- **[2026-01-15] Schedule Baselines:** ✅ Complete (100%)
- **[2026-01-15] Register Actual Costs:** ✅ Complete (100%)
