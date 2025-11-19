# 483921 Project Performance Dashboard Plan

**Context Recap:**
Approach A (composite dashboard page) approved. Scope limited to a single project, with WBE and cost-element filtering, configurable thresholds stored in `VarianceThresholdConfig` managed through existing Admin CRUD UI. Dashboard must reuse existing components (e.g., `BudgetTimeline`, `EarnedValueSummary`) and stay aligned with Time Machine context.

---

## 1. Implementation Steps (TDD-Centric Checklist)

### Dashboard Element Definitions

- **Project Context & Filters Panel**
  - *Goal:* Establish single-project scope with quick switching plus WBE/cost-element filtering.
  - *Structure:* Left-aligned stacked controls (project selector, multi-select WBEs, multi-select cost elements, clear/apply buttons) respecting Chakra form layout.
  - *Content:* Project dropdown (existing selector), WBE checkbox list grouped by machine, cost-element multi-select (department name + type), badges showing counts, pill-summary of applied filters.

- **Timeline Section (BudgetTimeline reuse)**
  - *Goal:* Visualize PV/EV/AC curves over time filtered to current project/WBEs/cost elements and aligned to Time Machine control date.
  - *Structure:* Card with heading, legend, Chart.js line chart, toggle between aggregated/multi-line modes.
  - *Content:* PV/EV/AC datasets, y-axis currency formatting, tooltip summary, empty state messaging when data absent.

- **KPI Card Deck (EarnedValueSummary composition)**
  - *Goal:* Surface headline metrics (CPI, SPI, TCPI, CV, SV, BAC, AC, EV) with color-coded thresholds from `VarianceThresholdConfig`.
  - *Structure:* Responsive grid (1/2/4 columns) of Chakra cards, each with label, value, status indicator icon, delta text if applicable.
  - *Content:* Metric values, configurable thresholds, tooltip describing threshold ranges, link to admin config when user has permission.

- **Drilldown Deck**
  - *Goal:* Highlight WBEs/cost elements contributing most to variance and provide navigation entry points.
  - *Structure:* DataTable-based grid with tabs (WBEs vs cost elements) and severity badges, right-aligned “View detail” buttons.
  - *Content:* Columns for hierarchy info, BAC, EV, AC, CV, SV, CPI/SPI, severity scores. Rows sorted by magnitude of variance; clicking navigates to detail route.

- **Admin Variance Threshold Manager**
  - *Goal:* Allow authorized users to configure CPI/SPI/TCPI/CV/SV threshold bands consumed by dashboard KPI cards.
  - *Structure:* Table-plus-form pattern in admin area showing existing configs, with drawer/modal for create/edit, delete action.
  - *Content:* Fields for metric type, green/yellow/red boundaries, description, updated timestamp, validation messaging.

1. **Route & Skeleton Setup**
   - *Acceptance Criteria:* New `/reports/project-performance-dashboard` route accessible from reports nav; renders placeholder sections for timeline, KPI cards, and drilldown deck referencing selected project.
   - *Test-First:* Add failing React Testing Library spec verifying route renders headings when feature flag enabled.
   - *Expected Files:* `frontend/src/routes/reports.tsx`, new `ProjectPerformanceDashboard.tsx`, route tests under `frontend/src/routes/__tests__/`.
   - *Dependencies:* None.
   - *Checkpoint after Step 2.*

2. **Project Context & Filters**
   - *Acceptance Criteria:* Dashboard loads selected project (from route param or picker) and exposes WBE + cost element filters (multi-select) wired to state only.
   - *Test-First:* Add failing component test ensuring filters render options sourced via mocked `ProjectsService`/`WbeService`.
   - *Expected Files:* Dashboard component, `frontend/src/components/forms/ProjectSelector.tsx` (existing) or new filter component, tests under `frontend/src/components/Reports/__tests__/`.
   - *Dependencies:* Step 1.

3. **BudgetTimeline Composition**
   - *Acceptance Criteria:* Existing `BudgetTimeline` renders within dashboard, honoring selected WBE/cost-element filters and control date.
   - *Test-First:* Extend `BudgetTimeline` tests with new spec expecting query params include filter IDs when invoked from dashboard (failing).
   - *Expected Files:* `frontend/src/components/Projects/BudgetTimeline.tsx`, new adapter hook, related tests.
   - *Dependencies:* Steps 1-2.

4. **KPI Card Deck (EarnedValueSummary reuse)**
   - *Acceptance Criteria:* Dashboard shows CPI/SPI/TCPI/CV/SV cards sourced from `EvmMetricsService`, thresholds configurable via `VarianceThresholdConfig` (fetched once, cached).
   - *Test-First:* Add failing test verifying cards reflect custom thresholds (e.g., SPI warning boundary defined in config).
   - *Expected Files:* `frontend/src/components/Reports/ProjectPerformanceDashboard.tsx`, utility for threshold lookup, tests in `frontend/src/components/Reports/__tests__/`.
   - *Dependencies:* Steps 1-3.

5. **Drilldown Deck & Navigation**
   - *Acceptance Criteria:* Grid listing top N WBEs/cost elements by variance with quick links to detail pages; honors filters and Time Machine date.
   - *Test-First:* Failing DataTable spec confirming rows sorted by severity and navigation callback invoked on click.
   - *Expected Files:* new `DrilldownDeck.tsx`, tests, potential `ReportsService` additions.
   - *Dependencies:* Steps 1-4.

6. **VarianceThresholdConfig Admin CRUD Verification**
   - *Acceptance Criteria:* Admin area exposes full CRUD for variance thresholds (list, create, edit, delete) if not already present; dashboard consumes these values.
   - *Test-First:* Add failing Playwright (or RTL) test ensuring admin screen shows form field updates persisted via mocked API.
   - *Expected Files:* `frontend/src/routes/admin/variance-thresholds.tsx` (or equivalent), client service definitions, tests.
   - *Dependencies:* Step 4 (threshold usage).

7. **End-to-End Integration & Playwright**
   - *Acceptance Criteria:* Playwright scenario loads dashboard, adjusts filters, verifies timeline + KPI updates, and drills into WBE detail.
   - *Test-First:* Write failing Playwright spec referencing new route.
   - *Expected Files:* `frontend/tests/project-performance-dashboard.spec.ts`, test fixtures.
   - *Dependencies:* Steps 1-6.

---

## 2. TDD Discipline Rules

- Every step begins with a failing automated test (unit, component, or E2E) that captures the intended behavior.
- Follow strict red → green → refactor cycle before progressing.
- Limit to max **three attempts** per step; if still red, pause and ask for guidance.
- Tests must assert behavior (e.g., data filtering, threshold application), not just rendering.

---

## 3. Process Checkpoints

- **Checkpoint 1:** After Step 2
  - Ask: “Continue as planned?”, “Any invalidated assumptions (project picker, filters)?”, “State matches expectations?”
- **Checkpoint 2:** After Step 5
  - Review cross-widget interactions and data dependencies before wiring threshold CRUD.
- **Checkpoint 3:** After Step 7
  - Confirm acceptance before merging or expanding scope.

---

## 4. Scope Boundaries

- Limit dashboard to **single-project** context with WBE & cost-element filters; no portfolio view.
- Use existing components/abstractions where possible; no net-new visualization libraries.
- Threshold logic must source from `VarianceThresholdConfig`; no hard-coded overrides elsewhere.
- If potential enhancements arise (e.g., additional charts), seek explicit approval before proceeding.

---

## 5. Rollback Strategy

- **Safe rollback point:** Current main branch prior to dashboard introduction (no changes merged yet). Keep work in feature branch with incremental commits per step.
- **If abandonment required:** Revert feature branch to pre-step commit; fallback approach would be “Approach C” (dashboard tab inside Cost Performance Report) using same assets but reduced scope. Seek confirmation before switching strategies.

---

## Tracking Checklist

1. ☐ Route & skeleton in place (Step 1)
2. ☐ Project/WBE/Cost element filters wired (Step 2) **[Checkpoint 1]**
3. ☐ Dashboard renders filtered `BudgetTimeline` (Step 3)
4. ☐ KPI cards honor configurable thresholds (Step 4)
5. ☐ Drilldown deck with navigation links (Step 5) **[Checkpoint 2]**
6. ☐ VarianceThresholdConfig admin CRUD verified/exposed (Step 6)
7. ☐ Playwright E2E coverage passes (Step 7) **[Checkpoint 3]**
