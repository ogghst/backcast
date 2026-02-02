# Backlog

**Last Updated:** 2026-01-19
**Total Items:** 34
**Total Estimated Points:** 206
**Completed:** 14 items (76 points)

---

## Quick Stats

| Priority | Items | Points | % of Backlog |
| -------- | ----- | ------ | ------------ |
| Critical | 7     | 55     | 25%          |
| High     | 13    | 92     | 42%          |
| Medium   | 12    | 56     | 26%          |
| Low      | 4     | 16     | 7%           |

---

## Backlog Items

### Critical Priority

#### [E06-U01] Create Change Orders ✅

- **Epic:** E006 (Branching & Change Order Management)
- **Story Points:** 5
- **Business Value:** CRITICAL - Core differentiator, enables isolated development
- **Dependencies:** E04-U02 (WBE creation)
- **Acceptance Criteria:**
  - UI for creating change orders with title, description, reason
  - Automatic branch creation (`co-{id}`) on save
  - Change order appears in list with status (Draft/Submitted/Approved/Merged)
  - RBAC: Only Project Managers can create change orders
- **Estimated Complexity:** Simple
- **Status:** ✅ Complete (Backend & Frontend)
- **Completed:** 2026-01-15

#### [E06-U02] Automatic Branch Creation for Change Orders ✅

- **Epic:** E006 (Branching & Change Order Management)
- **Story Points:** 5
- **Business Value:** CRITICAL - Automates branch workflow
- **Dependencies:** E06-U01 ✅
- **Acceptance Criteria:**
  - Branch `co-{id}` created automatically when change order is saved
  - Branch initialized as copy of current main state
  - Branch metadata includes change order ID and creator
- **Estimated Complexity:** Simple
- **Status:** ✅ Complete (implemented with E06-U01)
- **Completed:** 2026-01-15
- **Ready for Iteration:** No (already complete)

#### [E06-U05] Merge Approved Change Orders

- **Epic:** E006 (Branching & Change Order Management)
- **Story Points:** 13
- **Business Value:** CRITICAL - Completes change order lifecycle
- **Dependencies:** E06-U01, E06-U04
- **Acceptance Criteria:**
  - Merge approved change order branch into main
  - Conflict detection and resolution UI
  - Immutable history of merge operation
  - Rollback capability if merge causes issues
- **Estimated Complexity:** Complex
- **Ready for Iteration:** No (blocked by E06-U01, E06-U04)

#### [E03-U06] Generic VersionedRepository for Reusability

- **Epic:** E003 (Entity Versioning System)
- **Story Points:** 13
- **Business Value:** CRITICAL - Reduces duplication, enforces consistency
- **Dependencies:** E03-U03
- **Acceptance Criteria:**
  - Generic `VersionedRepository[T]` with common CRUD operations
  - Type-safe query builders
  - Automatic branch filtering
  - Automatic valid-time filtering
- **Estimated Complexity:** Complex
- **Ready for Iteration:** No (blocked by E03-U03)

#### [E03-U07] Automatic Filtering to Active/Latest Versions

- **Epic:** E003 (Entity Versioning System)
- **Story Points:** 8
- **Business Value:** CRITICAL - Default UX expectation
- **Dependencies:** E03-U03
- **Acceptance Criteria:**
  - Repository filters by default to current valid version
  - Optional parameter to query all versions
  - Performance: <100ms for queries
- **Estimated Complexity:** Medium
- **Ready for Iteration:** No (blocked by E03-U03)

#### [E03-U05] Time-Travel Queries (Query State at Any Past Date)

- **Epic:** E003 (Entity Versioning System)
- **Story Points:** 8
- **Business Value:** CRITICAL - Core audit capability
- **Dependencies:** E03-U02
- **Acceptance Criteria:**
  - Query entity state as of any historical date
  - Returns version valid at specified time
  - Performance: <200ms for historical queries
- **Estimated Complexity:** Medium
- **Ready for Iteration:** No (blocked by E03-U02)

#### [E06-U08] Delete/Archive Branches

- **Epic:** E006 (Branching & Change Order Management)
- **Story Points:** 3
- **Business Value:** CRITICAL - Cleanup after merge
- **Dependencies:** E06-U05
- **Acceptance Criteria:**
  - Delete branch after successful merge
  - Archive option for historical reference
  - Confirmation before deletion
- **Estimated Complexity:** Simple
- **Ready for Iteration:** No (blocked by E06-U05)

---

### High Priority

#### [E04-U06] Maintain Project-WBE-Cost Element Hierarchy Integrity

- **Epic:** E004 (Project Structure Management)
- **Story Points:** 8
- **Business Value:** HIGH - Data consistency
- **Dependencies:** E04-U03
- **Acceptance Criteria:**
  - Cascading delete: Project delete → WBE delete → Cost Element delete
  - Validation: Cannot delete parent if children have dependencies
  - Re-parenting support with validation
- **Estimated Complexity:** Medium
- **Ready for Iteration:** No (blocked by E04-U03)

#### [E06-U04] Compare Branch to Main (Impact Analysis) ✅

- **Epic:** E006 (Branching & Change Order Management)
- **Story Points:** 8
- **Business Value:** HIGH - Change order approval decision support
- **Dependencies:** E06-U01 ✅, E03-U04 ✅
- **Acceptance Criteria:**
  - UI shows side-by-side comparison of branch vs main
  - Highlights differences in Projects, WBEs, Cost Elements
  - Shows variance in budget amounts
  - Export comparison report as PDF (deferred - future enhancement)
- **Estimated Complexity:** Medium
- **Status:** ✅ Complete (Phase 3 - Impact Analysis & Comparison)
- **Completed:** 2026-01-14
- **Related Docs:** [Phase 3 ACT](iterations/2026-01-11-change-orders-implementation/phase3/04-act.md)

#### [E06-U03] Modify Entities in Branch (Isolated from Main) ✅

- **Epic:** E006 (Branching & Change Order Management)
- **Story Points:** 8
- **Business Value:** HIGH - Core isolation feature
- **Dependencies:** E06-U02 ✅
- **Acceptance Criteria:**
  - Modify entities in branch without affecting main
  - Branch isolation enforced at repository level
  - Merge conflict detection
- **Estimated Complexity:** Medium
- **Status:** ✅ Complete (Core EVCS functionality in BranchableService)
- **Completed:** 2026-01-15 (previously implemented)

#### [E05-U01] Register Actual Costs against Cost Elements ✅

- **Epic:** E005 (Financial Data Management)
- **Story Points:** 5
- **Business Value:** HIGH - Core EVM data
- **Dependencies:** E04-U03 ✅
- **Acceptance Criteria:**
  - Cost registration entity with date, amount, cost_element_id
  - Validation: Cannot exceed allocated budget
  - Versioning support
  - Import from CSV (deferred to new story)
- **Estimated Complexity:** Simple
- **Status:** ✅ Complete (Backend & Frontend)
- **Completed:** 2026-01-19
- **Notes:** Core functionality delivered. CSV import deferred to [E05-U01-CSV].
- **Ready for Iteration:** No (already complete)

#### [E05-U02] Create/Update Forecasts (EAC) ✅

- **Epic:** E005 (Financial Data Management)
- **Story Points:** 5
- **Business Value:** HIGH - Forecasting for proactive management
- **Dependencies:** E04-U03 ✅
- **Acceptance Criteria:**
  - Estimate at Complete (EAC) per cost element
  - Versioning support for forecast changes
  - Forecast vs actual comparison
  - One forecast per cost element (1:1 relationship enforced)
  - Auto-creation of forecast when cost element is created
  - Cascade delete of forecast when cost element is soft deleted
- **Estimated Complexity:** Simple
- **Status:** ✅ Complete (Backend & Frontend)
- **Completed:** 2026-01-19
- **Implementation Notes:**
  - Implemented 1:1 relationship using inverted FK pattern (cost_element.forecast_id)
  - Old /forecasts endpoints deprecated (410 Gone)
  - New nested endpoints: GET/PUT/DELETE /cost-elements/{id}/forecast
  - Followed schedule baseline 1:1 implementation pattern
- **Ready for Iteration:** No (already complete)

#### [E05-U03] Record Earned Value (% Complete)

- **Epic:** E005 (Financial Data Management)
- **Story Points:** 5
- **Business Value:** HIGH - Core EVM metric
- **Dependencies:** E04-U03 ✅
- **Acceptance Criteria:**
  - Record % complete per cost element
  - Automatic EV calculation (BAC × % complete)
  - Versioning support
- **Estimated Complexity:** Simple
- **Ready for Iteration:** Yes (E04-U03 complete)

#### [E05-U05] Validate Cost Registrations against Budgets

- **Epic:** E005 (Financial Data Management)
- **Story Points:** 8
- **Business Value:** HIGH - Budget control
- **Dependencies:** E04-U03 ✅, E05-U01
- **Acceptance Criteria:**
  - Real-time validation: Total costs ≤ allocated budget
  - Warning when approaching budget limit
  - Block when exceeding budget (configurable)
- **Estimated Complexity:** Medium
- **Ready for Iteration:** No (blocked by E05-U01)

#### [E05-U06] View Cost History and Trends

- **Epic:** E005 (Financial Data Management)
- **Story Points:** 5
- **Business Value:** HIGH - Historical analysis
- **Dependencies:** E03-U04 ✅, E05-U01
- **Acceptance Criteria:**
  - Timeline view of cost registrations
  - Trend analysis (burn rate)
  - Export to CSV
- **Estimated Complexity:** Simple
- **Ready for Iteration:** No (blocked by E05-U01)

#### [E08-U01] Calculate PV using Schedule Baselines

- **Epic:** E008 (EVM Calculations & Reporting)
- **Story Points:** 8
- **Business Value:** HIGH - Core EVM calculation
- **Dependencies:** E05-U04 ✅
- **Acceptance Criteria:**
  - Planned Value (PV) calculation from schedule baseline
  - Time-phased budget distribution
  - PV at any point in time
- **Estimated Complexity:** Medium
- **Ready for Iteration:** Yes (E05-U04 ready)

#### [E08-U02] Calculate EV from % Complete

- **Epic:** E008 (EVM Calculations & Reporting)
- **Story Points:** 5
- **Business Value:** HIGH - Core EVM calculation
- **Dependencies:** E05-U03 ✅
- **Acceptance Criteria:**
  - Earned Value (EV) = BAC × % complete
  - Rollup calculation from cost elements
- **Estimated Complexity:** Simple
- **Ready for Iteration:** Yes (E05-U03 ready)

#### [E08-U03] Calculate AC from Cost Registrations

- **Epic:** E008 (EVM Calculations & Reporting)
- **Story Points:** 5
- **Business Value:** HIGH - Core EVM calculation
- **Dependencies:** E05-U01
- **Acceptance Criteria:**
  - Actual Cost (AC) sum of cost registrations
  - Time-phased AC calculation
- **Estimated Complexity:** Simple
- **Ready for Iteration:** No (blocked by E05-U01)

#### [E08-U04] View Performance Indices (CPI/SPI/TCPI)

- **Epic:** E008 (EVM Calculations & Reporting)
- **Story Points:** 8
- **Business Value:** HIGH - Performance metrics
- **Dependencies:** E08-U01, E08-U02, E08-U03
- **Acceptance Criteria:**
  - CPI = EV/AC (Cost Performance Index)
  - SPI = EV/PV (Schedule Performance Index)
  - TCPI (To-Complete Performance Index)
  - Threshold-based color coding
- **Estimated Complexity:** Medium
- **Ready for Iteration:** No (blocked by E08-U01, E08-U02, E08-U03)

---

### Medium Priority

#### [E04-U04] Allocate Revenue across WBEs

- **Epic:** E004 (Project Structure Management)
- **Story Points:** 5
- **Business Value:** MEDIUM - Revenue tracking
- **Dependencies:** E04-U02
- **Acceptance Criteria:**
  - Allocate revenue amounts to WBEs
  - Revenue validation rules
  - Versioning support
- **Estimated Complexity:** Simple
- **Ready for Iteration:** Yes (E04-U02 complete)

#### [E04-U05] Allocate Budgets to Cost Elements

- **Epic:** E004 (Project Structure Management)
- **Story Points:** 5
- **Business Value:** MEDIUM - Budget distribution
- **Dependencies:** E04-U03 ✅
- **Acceptance Criteria:**
  - Allocate budget amounts to cost elements
  - Budget validation (WBE total ≥ sum of cost elements)
  - Versioning support
- **Estimated Complexity:** Simple
- **Ready for Iteration:** Yes (E04-U03 complete)

#### [E04-U07] Tree View of Project Structure

- **Epic:** E004 (Project Structure Management)
- **Story Points:** 5
- **Business Value:** MEDIUM - Visual hierarchy
- **Dependencies:** E04-U03 ✅
- **Acceptance Criteria:**
  - Tree view: Project → WBEs → Cost Elements
  - Expandable/collapsible nodes
  - Quick navigation to entity details
- **Estimated Complexity:** Simple
- **Ready for Iteration:** Yes (E04-U03 complete)

#### [E05-U04] Define Schedule Baselines with Progression Types

- **Epic:** E005 (Financial Data Management)
- **Story Points:** 8
- **Business Value:** MEDIUM - Schedule management
- **Dependencies:** E04-U03 ✅
- **Acceptance Criteria:**
  - Create schedule baselines with start/end dates
  - Progression types: linear/gaussian/logarithmic
  - Link to cost elements for PV calculation
- **Estimated Complexity:** Medium
- **Ready for Iteration:** Yes (E04-U03 complete)

#### [E05-U07] Manage Quality Events (Track Rework Costs)

- **Epic:** E005 (Financial Data Management)
- **Story Points:** 5
- **Business Value:** MEDIUM - Quality tracking
- **Dependencies:** E05-U01
- **Acceptance Criteria:**
  - Quality event entity with description, cost impact
  - Link to cost elements for rework cost tracking
  - Versioning support
- **Estimated Complexity:** Simple
- **Ready for Iteration:** No (blocked by E05-U01)

#### [E06-U06] Lock/Unlock Branches

- **Epic:** E006 (Branching & Change Order Management)
- **Story Points:** 3
- **Business Value:** MEDIUM - Access control
- **Dependencies:** E06-U02
- **Acceptance Criteria:**
  - Lock branch to prevent modifications
  - Unlock to allow edits
  - RBAC: Only approvers can lock/unlock
- **Estimated Complexity:** Simple
- **Status:** ✅ Complete (Phase 2 Backend)
- **Ready for Iteration:** No (blocked by E06-U02)

#### [E06-U06-UI] Workflow-Aware Status Management

- **Epic:** E006 (Branching & Change Order Management)
- **Story Points:** 5
- **Business Value:** HIGH - User experience & data integrity
- **Dependencies:** E06-U06 ✅
- **Acceptance Criteria:**
  - Create mode: Status dropdown shows only "Draft" (or disabled)
  - Edit mode: Status dropdown shows only valid transitions from current state
  - Status field disabled when branch is locked
  - Status field disabled when `can_edit_on_status()` returns false
  - Visual warning when working on locked branch
  - Backend provides `available_transitions` in ChangeOrderPublic schema
  - Frontend uses `useWorkflowInfo()` hook for dynamic options
- **Estimated Complexity:** Simple
- **Related Docs:** [`iterations/2026-01-11-change-orders-implementation/workflow-ui/00-analysis.md`](iterations/2026-01-11-change-orders-implementation/workflow-ui/00-analysis.md)
- **Ready for Iteration:** Yes (backend complete)

#### [E06-U07] Merged View Showing Main + Branch Changes

- **Epic:** E006 (Branching & Change Order Management)
- **Story Points:** 5
- **Business Value:** MEDIUM - Preview before merge
- **Dependencies:** E06-U03
- **Acceptance Criteria:**
  - Show main + branch changes combined
  - Highlight conflicts
  - Preview of merged state
- **Estimated Complexity:** Simple
- **Ready for Iteration:** No (blocked by E06-U03)

#### [E07-U01] Create Baselines at Milestones

- **Epic:** E007 (Baseline Management)
- **Story Points:** 5
- **Business Value:** MEDIUM - Milestone tracking
- **Dependencies:** E04-U03, E05-U04
- **Acceptance Criteria:**
  - Create baseline at project milestones
  - Immutable snapshot
  - Baseline metadata (date, creator, milestone type)
- **Estimated Complexity:** Simple
- **Ready for Iteration:** No (blocked by E04-U03, E05-U04)

#### [E07-U03] Compare Current State to Any Baseline

- **Epic:** E007 (Baseline Management)
- **Story Points:** 5
- **Business Value:** MEDIUM - Variance analysis
- **Dependencies:** E07-U01
- **Acceptance Criteria:**
  - Side-by-side comparison with baseline
  - Highlight differences
  - Export variance report
- **Estimated Complexity:** Simple
- **Ready for Iteration:** No (blocked by E07-U01)

#### [E07-U04] Mark Baselines as PMB (Performance Measurement Baseline)

- **Epic:** E007 (Baseline Management)
- **Story Points:** 3
- **Business Value:** MEDIUM - EVM reference point
- **Dependencies:** E07-U01
- **Acceptance Criteria:**
  - Mark baseline as PMB
  - Only one PMB active at a time
  - PMB used for EVM calculations
- **Estimated Complexity:** Simple
- **Ready for Iteration:** No (blocked by E07-U01)

#### [E08-U05] View Variances (CV/SV/VAC)

- **Epic:** E008 (EVM Calculations & Reporting)
- **Story Points:** 5
- **Business Value:** MEDIUM - Variance analysis
- **Dependencies:** E08-U01, E08-U02, E08-U03
- **Acceptance Criteria:**
  - CV = EV - AC (Cost Variance)
  - SV = EV - PV (Schedule Variance)
  - VAC = BAC - EAC (Variance at Complete)
  - Threshold-based color coding
- **Estimated Complexity:** Simple
- **Ready for Iteration:** No (blocked by E08-U01, E08-U02, E08-U03)

---

### Low Priority

#### [E07-U02] Snapshot All Cost Element Data Immutably

- **Epic:** E007 (Baseline Management)
- **Story Points:** 3
- **Business Value:** LOW - Baseline detail
- **Dependencies:** E07-U01
- **Acceptance Criteria:**
  - Immutable snapshot of all cost element data
  - Efficient storage (no duplication)
- **Estimated Complexity:** Simple
- **Ready for Iteration:** No (blocked by E07-U01)

#### [E07-U05] Cancel Baselines (Corrections)

- **Epic:** E007 (Baseline Management)
- **Story Points:** 3
- **Business Value:** LOW - Correction handling
- **Dependencies:** E07-U01
- **Acceptance Criteria:**
  - Cancel baseline with reason
  - Cannot delete PMB without setting new PMB
- **Estimated Complexity:** Simple
- **Ready for Iteration:** No (blocked by E07-U01)

#### [E07-U06] Preserve Baseline Schedule Registrations

- **Epic:** E007 (Baseline Management)
- **Story Points:** 3
- **Business Value:** LOW - Historical reference
- **Dependencies:** E07-U01
- **Acceptance Criteria:**
  - Preserve schedule registrations in baseline
  - Query historical schedule state
- **Estimated Complexity:** Simple
- **Ready for Iteration:** No (blocked by E07-U01)

#### [E05-U01-CSV] Import Cost Registrations from CSV

- **Epic:** E005 (Financial Data Management)
- **Story Points:** 3
- **Business Value:** LOW - Bulk data entry convenience
- **Dependencies:** E05-U01 ✅
- **Acceptance Criteria:**
  - Import cost registrations from CSV file
  - Validation of CSV format and data integrity
  - Rollback on failure (atomic batch)
- **Estimated Complexity:** Simple
- **Ready for Iteration:** Yes (E05-U01 complete)

---

#### [E08-U08] Time Machine Control for Historical Metrics

- **Epic:** E008 (EVM Calculations & Reporting)
- **Story Points:** 5
- **Business Value:** LOW - Historical reporting
- **Dependencies:** E03-U05, E08-U01, E08-U02, E08-U03
- **Acceptance Criteria:**
  - Query EVM metrics as of any historical date
  - Historical trend charts
- **Estimated Complexity:** Simple
- **Ready for Iteration:** No (blocked by E03-U05, E08-U01, E08-U02, E08-U03)

---

## Backlog Health Metrics

- **Items with Estimates:** 35/35 (100%)
- **Items with Dependencies Defined:** 35/35 (100%)
- **Items Ready for Sprint:** 11/35 (31%)
- **Average Item Size:** 6.1 points
- **Items Requiring Splitting (>13 points):** 0/34 (0%)

---

## Recently Completed (Moved from Backlog)

| Date       | Item                                              | Points | Iteration                | Notes                              |
| ---------- | ------------------------------------------------- | ------ | ------------------------ | ---------------------------------- |
| 2026-01-19 | E05-U01: Register Actual Costs                    | 5      | N/A                      | Core functionality delivered       |
| 2026-01-15 | E06-U04: Compare Branch to Main (Impact Analysis) | 8      | Change Orders v2 Phase 3 | Backend & Frontend Complete        |
| 2026-01-15 | E06-U03: Modify Entities in Branch                | 8      | Change Orders v2         | Core EVCS functionality            |
| 2026-01-15 | E06-U01: Create Change Orders                     | 5      | Change Orders v2         | Backend & Frontend Complete        |
| 2026-01-15 | E06-U02: Automatic Branch Creation                | 5      | Change Orders v2         | Implemented with E06-U01           |
| 2026-01-07 | E04-U03: Create Cost Elements within WBEs         | 8      | Hybrid Sprint 2/3        | Backend & Frontend Complete        |
| 2026-01-07 | E03-U04: Entity History Viewing                   | 5      | Hybrid Sprint 2/3        | Integrated for Projects, WBEs, CEs |
| 2026-01-05 | E04-U01: Create projects with metadata            | 5      | Hybrid Sprint 2/3        | Completed early                    |
| 2026-01-05 | E04-U02: Create WBEs within projects              | 5      | Hybrid Sprint 2/3        | Completed early                    |
| 2025-12-27 | E02-U01: User CRUD                                | 8      | Sprint 2                 | Complete with tests                |
| 2025-12-27 | E02-U02: Department CRUD                          | 5      | Sprint 2                 | Complete with tests                |
| 2025-12-27 | E02-U03: User roles and permissions               | 5      | Sprint 2                 | RBAC implemented                   |
| 2025-12-27 | E02-U04: Test coverage                            | 3      | Sprint 2                 | 80%+ achieved                      |

---

## Backlog Maintenance

**Last Groomed:** 2026-01-06
**Next Grooming:** 2026-01-13

**Grooming Checklist:**

- [x] All items have story point estimates
- [x] Dependencies are documented
- [x] Priorities are current
- [x] No duplicate items
- [x] Items are appropriately sized (13 points or less)
