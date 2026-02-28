# Epics and User Stories

**Last Updated:** 2026-01-14
**Status:** Live

---

## Epic 1: Foundation & Infrastructure (E001)

**Business Value:** Establish robust technical foundation
**Status:** ✅ Complete

**User Stories:**

- **E01-U01:** Development environment configuration ✅
- **E01-U02:** Database migrations (Alembic async) ✅
- **E01-U03:** Async database sessions (SQLAlchemy 2.0) ✅
- **E01-U04:** Authentication/authorization (JWT) ✅
- **E01-U05:** CI/CD pipeline (GitHub Actions) ✅

**Completed:** Sprint 1 (2025-12-27)

---

## Epic 2: Core Entity Management (Non-Versioned) (E002)

**Business Value:** Enable basic CRUD operations for foundational entities
**Status:** ✅ Complete

**User Stories:**

- **E02-U01:** User CRUD with repository pattern, Pydantic schemas, comprehensive tests ✅
- **E02-U02:** Department CRUD ✅
- **E02-U03:** User roles and permissions management (RBAC) ✅
- **E02-U04:** Complete test coverage for all CRUD operations ✅
- **E02-U05:** Frontend User & Department Management (Admin Only) ✅
- **E02-U06:** Frontend Authentication (Login/Logout/Protect Routes) ✅

**Completed:** Sprint 2 (2026-01-05)

---

## Epic 3: Entity Versioning System (EVCS Core) (E003)

**Business Value:** Implement Git-like versioning for complete audit trails
**Priority:** CRITICAL
**Status:** ✅ Complete

**User Stories:**

- **E03-U01:** Composite primary key support `(id, branch)` ✅
- **E03-U02:** Version tables with immutable snapshots ✅
- **E03-U03:** Versioning helper functions (create/update/delete) ✅
- **E03-U04:** Entity history viewing ✅
- **E03-U05:** Time-travel queries (query state at any past date) ✅
- **E03-U06:** Generic VersionedRepository for reusability ✅
- **E03-U07:** Automatic filtering to active/latest versions ✅

**Implementation Details:**

- Bitemporal tracking with `TSTZRANGE` (valid_time + transaction_time)
- `TemporalBase` and `TemporalService[T]` for versioned entities
- `SimpleBase` and `SimpleService` for non-versioned entities
- Time Machine control for historical queries
- Branch mode support (STRICT/MERGE) for change order preview
- 100% test pass rate on time-travel queries (2026-01-10)

**Completed:** Sprint 3-4 (2026-01-10)

---

## Epic 4: Project Structure Management (E004)

**Business Value:** Enable hierarchical project organization
**Priority:** HIGH
**Status:** ✅ Complete

**User Stories:**

- **E04-U01:** Create projects with metadata ✅
- **E04-U02:** Create WBEs within projects (track individual machines) ✅
- **E04-U03:** Create cost elements within WBEs (departmental budgets) ✅
- **E04-U06:** Maintain project-WBE-cost element hierarchy integrity ✅
- **E04-U07:** Tree view of project structure ✅

**Implementation Details:**

- 14 API endpoints (8 for Project, 6 for WBE)
- Cost Element CRUD with full EVCS support
- Frontend hierarchical navigation implemented
- Branch support for all entities (via BranchableService)

**Completed:** Sprint 2 (bonus), Sprint 5-6 (2026-01-05 to 2026-01-12)

---

## Epic 5: Financial Data Management (E005)

**Business Value:** Track costs, forecasts, and earned value
**Priority:** HIGH
**Status:** 🔄 In Progress

**User Stories:**

- **E05-U01:** Register actual costs against cost elements ⏳
- **E05-U02:** Create/update forecasts (EAC) ⏳
- **E05-U03:** Record earned value (% complete) ⏳
- **E05-U04:** Define schedule baselines with progression types (linear/gaussian/logarithmic) ⏳
- **E05-U05:** Validate cost registrations against budgets ⏳
- **E05-U06:** View cost history and trends ⏳
- **E05-U07:** Manage quality events (track rework costs) ⏳

**Progress:**

- Cost Element entity implemented (foundation for cost tracking)
- Control date CRUD implemented (2026-01-10)

**Targeted:** Sprint 8

---

## Epic 6: Branching & Change Order Management (E006)

**Business Value:** Enable isolated change order development
**Priority:** CRITICAL
**Status:** ✅ Complete (All Phases)

**User Stories:**

- **E06-U01:** Create change orders ✅
- **E06-U02:** Automatic branch creation for change orders (`BR-{id}`) ✅
- **E06-U03:** Modify entities in branch (isolated from main) ✅
- **E06-U04:** Compare branch to main (impact analysis) ✅
- **E06-U05:** Merge approved change orders ✅
- **E06-U06:** Lock/unlock branches ✅
- **E06-U07:** Merged view showing main + branch changes ✅
- **E06-U08:** Delete/archive branches ✅

**Implementation Details:**

- **Phase 1 Complete (2026-01-12):** Change Order creation, auto-branch creation, BranchableSoftDeleteCommand
- **Phase 2 Complete:** In-branch editing, workflow states (DRAFT/SUBMITTED/APPROVED/REJECTED)
- **Phase 3 Complete (2026-02-07):** Impact analysis, branch comparison, side-by-side diff, hierarchical diff view
- **Phase 4 Complete (2026-01-26):** Merge workflows, conflict detection, status transitions
- **Phase 5 Complete (2026-02-25):** Archive branch functionality (E06-U08)

**Key Features:**

- 7 API endpoints for change orders
- Frontend components: ChangeOrderList, ChangeOrderModal
- Branch selector implemented
- Branch mode with fallback (STRICT/MERGE) for preview
- Extended WBE and CostElement to BranchableService
- Side-by-side diff component for entity property comparison
- Hierarchical diff view (Project → WBE → Cost Elements tree)
- Dedicated impact analysis route at `/projects/:projectId/change-orders/:id/impact`

**Completed:** Phase 1 (2026-01-12)

---

## Epic 7: Baseline Management (E007)

**Business Value:** Capture project snapshots at key milestones
**Priority:** MEDIUM
**Status:** ⏳ Not Started

**User Stories:**

- **E07-U01:** Create baselines at milestones (kickoff, BOM release, commissioning, etc.)
- **E07-U02:** Snapshot all cost element data immutably
- **E07-U03:** Compare current state to any baseline
- **E07-U04:** Mark baselines as PMB (Performance Measurement Baseline)
- **E07-U05:** Cancel baselines (corrections)
- **E07-U06:** Preserve baseline schedule registrations

**Targeted:** Sprint 8

---

## Epic 8: EVM Calculations & Reporting (E008)

**Business Value:** Standard EVM metrics and analytics
**Priority:** HIGH
**Status:** ⏳ Not Started

**User Stories:**

- **E08-U01:** Calculate PV using schedule baselines
- **E08-U02:** Calculate EV from % complete
- **E08-U03:** Calculate AC from cost registrations
- **E08-U04:** View performance indices (CPI/SPI/TCPI)
- **E08-U05:** View variances (CV/SV/VAC)
- **E08-U06:** Generate cost performance reports
- **E08-U07:** Generate variance analysis reports
- **E08-U08:** Time machine control for historical metrics

**Targeted:** Sprint 8
