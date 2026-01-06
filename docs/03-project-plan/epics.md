# Epics and User Stories

**Last Updated:** 2025-12-29
**Status:** Live

---

## Epic 1: Foundation & Infrastructure (E001)
**Business Value:** Establish robust technical foundation
**Status:** Complete

**User Stories:**
- **E01-U01:** Development environment configuration
- **E01-U02:** Database migrations (Alembic async)
- **E01-U03:** Async database sessions (SQLAlchemy 2.0)
- **E01-U04:** Authentication/authorization (JWT)
- **E01-U05:** CI/CD pipeline (GitHub Actions)

---

## Epic 2: Core Entity Management (Non-Versioned) (E002)
**Business Value:** Enable basic CRUD operations for foundational entities
**Status:** In Progress

**User Stories:**
- **E02-U01:** User CRUD with repository pattern, Pydantic schemas, comprehensive tests
- **E02-U02:** Department CRUD
- **E02-U03:** User roles and permissions management
- **E02-U04:** Complete test coverage for all CRUD operations

---

## Epic 3: Entity Versioning System (EVCS Core) (E003)
**Business Value:** Implement Git-like versioning for complete audit trails
**Priority:** CRITICAL

**User Stories:**
- **E03-U01:** Composite primary key support `(id, branch)`
- **E03-U02:** Version tables with immutable snapshots
- **E03-U03:** Versioning helper functions (create/update/delete)
- **E03-U04:** Entity history viewing
- **E03-U05:** Time-travel queries (query state at any past date)
- **E03-U06:** Generic VersionedRepository for reusability
- **E03-U07:** Automatic filtering to active/latest versions

**Dependencies:**
- E03-U01 must be complete before E03-U02
- E03-U02 must be complete before E03-U04, E03-U05
- E03-U03 must be complete before E03-U06, E03-U07

---

## Epic 4: Project Structure Management (E004)
**Business Value:** Enable hierarchical project organization
**Priority:** HIGH

**User Stories:**
- **E04-U01:** Create projects with metadata
- **E04-U02:** Create WBEs within projects (track individual machines)
- **E04-U03:** Create cost elements within WBEs (departmental budgets)
- **E04-U04:** Allocate revenue across WBEs
- **E04-U05:** Allocate budgets to cost elements
- **E04-U06:** Maintain project-WBE-cost element hierarchy integrity
- **E04-U07:** Tree view of project structure

**Dependencies:**
- E04-U01 must be complete before E04-U02, E04-U04
- E04-U02 must be complete before E04-U03, E04-U05, E04-U06, E04-U07
- E04-U03 must be complete before E04-U05, E04-U06, E04-U07

---

## Epic 5: Financial Data Management (E005)
**Business Value:** Track costs, forecasts, and earned value
**Priority:** HIGH

**User Stories:**
- **E05-U01:** Register actual costs against cost elements
- **E05-U02:** Create/update forecasts (EAC)
- **E05-U03:** Record earned value (% complete)
- **E05-U04:** Define schedule baselines with progression types (linear/gaussian/logarithmic)
- **E05-U05:** Validate cost registrations against budgets
- **E05-U06:** View cost history and trends
- **E05-U07:** Manage quality events (track rework costs)

**Dependencies:**
- E04-U03 must be complete before E05-U01, E05-U02, E05-U03, E05-U04, E05-U07
- E05-U01 must be complete before E05-U05, E05-U06

---

## Epic 6: Branching & Change Order Management (E006)
**Business Value:** Enable isolated change order development
**Priority:** CRITICAL

**User Stories:**
- **E06-U01:** Create change orders
- **E06-U02:** Automatic branch creation for change orders (`co-{id}`)
- **E06-U03:** Modify entities in branch (isolated from main)
- **E06-U04:** Compare branch to main (impact analysis)
- **E06-U05:** Merge approved change orders
- **E06-U06:** Lock/unlock branches
- **E06-U07:** Merged view showing main + branch changes
- **E06-U08:** Delete/archive branches

**Dependencies:**
- E04-U02 must be complete before E06-U01
- E06-U01 must be complete before E06-U02, E06-U04, E06-U05
- E06-U02 must be complete before E06-U03, E06-U06, E06-U07
- E03-U04 must be complete before E06-U04
- E06-U03 must be complete before E06-U07
- E06-U05 must be complete before E06-U08

---

## Epic 7: Baseline Management (E007)
**Business Value:** Capture project snapshots at key milestones
**Priority:** MEDIUM

**User Stories:**
- **E07-U01:** Create baselines at milestones (kickoff, BOM release, commissioning, etc.)
- **E07-U02:** Snapshot all cost element data immutably
- **E07-U03:** Compare current state to any baseline
- **E07-U04:** Mark baselines as PMB (Performance Measurement Baseline)
- **E07-U05:** Cancel baselines (corrections)
- **E07-U06:** Preserve baseline schedule registrations

**Dependencies:**
- E04-U03 must be complete before E07-U01, E07-U02
- E05-U04 must be complete before E07-U01, E07-U06
- E07-U01 must be complete before E07-U02, E07-U03, E07-U04, E07-U05, E07-U06

---

## Epic 8: EVM Calculations & Reporting (E008)
**Business Value:** Standard EVM metrics and analytics
**Priority:** HIGH

**User Stories:**
- **E08-U01:** Calculate PV using schedule baselines
- **E08-U02:** Calculate EV from % complete
- **E08-U03:** Calculate AC from cost registrations
- **E08-U04:** View performance indices (CPI/SPI/TCPI)
- **E08-U05:** View variances (CV/SV/VAC)
- **E08-U06:** Generate cost performance reports
- **E08-U07:** Generate variance analysis reports
- **E08-U08:** Time machine control for historical metrics

**Dependencies:**
- E05-U04 must be complete before E08-U01
- E05-U03 must be complete before E08-U02
- E05-U01 must be complete before E08-U03
- E08-U01, E08-U02, E08-U03 must be complete before E08-U04, E08-U05
- E03-U05 must be complete before E08-U08
