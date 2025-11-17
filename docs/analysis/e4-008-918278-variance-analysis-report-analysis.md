# High-Level Analysis: E4-008 Variance Analysis Report

**Task:** E4-008 - Variance Analysis Report
**Sprint:** Sprint 5 - Reporting and Performance Dashboards
**Status:** Analysis Phase
**Date:** 2025-11-17
**Current Time:** 11:47 CET (Europe/Rome)

---

## User Story

As a project manager analyzing project performance,
I want to view a Variance Analysis Report that highlights areas where performance deviates from plan, focusing on cost and schedule variances with drill-down capabilities,
So that I can quickly identify problem areas, investigate root causes, and take corrective actions to bring the project back on track.

---

## 1. CODEBASE PATTERN ANALYSIS

### 1.1 Existing Report Display Components

1. **Cost Performance Report – E4-007 (Primary Pattern)**
   - **Location:**
     - Backend: `backend/app/services/cost_performance_report.py`, `backend/app/api/routes/cost_performance_report.py`, `backend/app/models/cost_performance_report.py`
     - Frontend: `frontend/src/components/Reports/CostPerformanceReport.tsx`, `frontend/src/routes/_layout/projects.$id.reports.cost-performance.tsx`
   - **Architecture Layers:**
     - Service layer: `get_cost_performance_report()` function that aggregates EVM metrics for all cost elements
     - API layer: FastAPI router with `/projects/{project_id}/reports/cost-performance` endpoint
     - Models layer: `CostPerformanceReportPublic` (summary + rows array), `CostPerformanceReportRowPublic` (individual row with all EVM metrics)
     - Frontend: React component using `DataTable` with TanStack Table v8
   - **Features:**
     - Tabular display with all EVM metrics (PV, EV, AC, BAC, CPI, SPI, TCPI, CV, SV)
     - Color-coded status indicators for CPI, SPI, TCPI, CV, SV
     - Drill-down navigation: row click navigates to cost element detail page
     - Summary row showing aggregated project totals
     - Client-side filtering and sorting
     - Time-machine integration via `useTimeMachine()` hook
   - **Patterns to respect:**
     - Dedicated service function that reuses existing `EvmMetricsService` aggregation logic
     - Response model with summary (project-level metrics) and rows array (cost element-level metrics)
     - Frontend component with column definitions, formatting helpers, status indicator helpers
     - Report route under `/projects/{project_id}/reports/{report-type}` pattern
     - Reuses existing `DataTable` component for consistent table behavior

2. **DataTable Component – E1-007**
   - **Location:** `frontend/src/components/DataTable/DataTable.tsx`
   - **Architecture Layers:**
     - TanStack Table v8 (`@tanstack/react-table`) for table logic
     - Chakra UI (`Table.Root`, `Table.Header`, `Table.Body`) for styling
     - Column definitions with `ColumnDefExtended` type
   - **Features:**
     - Sorting, filtering, column resizing, column visibility toggle, pagination
     - Row click handlers for navigation
     - Loading states with skeleton components
   - **Patterns to respect:**
     - TypeScript generics for type-safe data (`DataTable<TData>`)
     - Manual pagination via URL search params
     - Client-side filtering and sorting
     - Responsive design with mobile optimization

3. **Status Indicator Helpers – E4-006, E4-007**
   - **Location:** `frontend/src/components/Reports/CostPerformanceReport.tsx`, `frontend/src/components/Projects/EarnedValueSummary.tsx`
   - **Functions:**
     - `getVarianceStatus()` - Returns color, icon, and label for CV/SV values (negative=red, zero=yellow, positive=green)
     - `getCpiStatus()`, `getSpiStatus()`, `getTcpiStatus()` - Status indicators for performance indices
   - **Patterns to respect:**
     - Status helpers return `{ color: string, icon: Component, label: string }`
     - Color thresholds: red (<0.95 or negative), yellow (0.95-1.0 or zero), green (>1.0 or positive)
     - Handles null/undefined values with gray "N/A" status

### 1.2 Existing EVM Metrics Services

1. **EVM Aggregation Service – E4-005**
   - **Location:** `backend/app/services/evm_aggregation.py`
   - **Function:** `get_cost_element_evm_metrics()` computes all EVM metrics for a cost element
   - **Data Provided:**
     - Core metrics: `planned_value`, `earned_value`, `actual_cost`, `budget_bac`
     - Performance indices: `cpi`, `spi`, `tcpi`
     - Variances: `cost_variance` (CV = EV - AC), `schedule_variance` (SV = EV - PV)
   - **Patterns to respect:**
     - Reuses schedule map, entry map, and cost registration queries from existing helpers
     - Returns `CostElementEVMMetrics` dataclass with all computed metrics
     - Handles time-machine control date filtering

2. **Cost Performance Report Service – E4-007**
   - **Location:** `backend/app/services/cost_performance_report.py`
   - **Function:** `get_cost_performance_report()` aggregates EVM metrics for all cost elements
   - **Pattern:**
     - Iterates through all cost elements in project
     - Calls `get_cost_element_evm_metrics()` for each
     - Builds report rows array with hierarchical metadata (WBE, department, cost element type)
     - Calculates project summary using aggregated totals
   - **Patterns to respect:**
     - Reuses existing helper functions (`_get_schedule_map`, `_get_entry_map`)
     - Handles empty projects gracefully (returns empty report with zero summary)
     - Builds lookup maps for efficient data access

### 1.3 Existing Navigation Patterns

1. **Report Route Pattern – E4-007**
   - **Location:** `frontend/src/routes/_layout/projects.$id.reports.cost-performance.tsx`
   - **Pattern:** Nested route under project detail: `/projects/{project_id}/reports/{report-type}`
   - **Integration:** Project detail page guards for nested routes (WBE, budget-timeline, reports)
   - **Patterns to respect:**
     - Report routes follow `/projects/:id/reports/:report-type` pattern
     - Report page components receive `projectId` from route params
     - Navigation links from project detail page to report pages

2. **Drill-Down Navigation – E4-007**
   - **Pattern:** Row click handler in `DataTable` navigates to cost element detail page
   - **Navigation:** Uses TanStack Router `navigate()` with typed route and params
   - **URL Pattern:** `/projects/{projectId}/wbes/{wbeId}/cost-elements/{costElementId}`
   - **Patterns to respect:**
     - Row data must include `cost_element_id` and `wbe_id` for navigation
     - Navigation preserves time-machine control date (via search params if needed)
     - Navigation can set default tab/view for detail page

---

## 2. INTEGRATION TOUCHPOINT MAPPING

### 2.1 Backend Modules Requiring Modification

1. **New Variance Analysis Report API Endpoint (Proposed)**
   - **Candidate:** `backend/app/api/routes/variance_analysis_report.py` OR extend `cost_performance_report.py`
   - **Endpoints:**
     - `GET /projects/{project_id}/reports/variance-analysis` (project level)
     - Optional future: WBE-level and cost element-level reports
   - **Response Model:**
     - `VarianceAnalysisReportPublic` - Container with summary and rows array
     - `VarianceAnalysisReportRowPublic` - Row data focusing on variance metrics
     - Rows should include all EVM metrics (for context) but emphasize CV and SV
     - Include filtering metadata (severity thresholds, variance type filters)
   - **Dependencies:**
     - Reuse existing `EvmMetricsService` aggregation logic (same as E4-007)
     - Reuse `get_cost_element_evm_metrics()` from `evm_aggregation.py`
     - `SessionDep`, `CurrentUser`, `get_time_machine_control_date`
   - **Data Structure:**
     - Flat array of rows with hierarchical metadata (project_id, wbe_id, cost_element_id)
     - Include all EVM metrics for context (PV, EV, AC, BAC, CPI, SPI, TCPI)
     - Emphasize variance metrics: CV, SV, CV% (CV/BAC), SV% (SV/BAC)
     - Optional: Include variance severity indicators (critical, warning, normal)

2. **Service Layer (Extend or Reuse)**
   - **Option A – Reuse Cost Performance Report Service:**
     - Extend `get_cost_performance_report()` with optional filtering parameters
     - Add variance-based filtering logic (filter by CV/SV thresholds)
     - Add variance severity calculation
     - **Pros:** Minimal code duplication, single source of truth for report data
     - **Cons:** May complicate cost performance report if not needed there

   - **Option B – New Variance Analysis Service (Recommended):**
     - **Candidate:** `backend/app/services/variance_analysis_report.py`
     - New function: `get_variance_analysis_report()` that reuses `get_cost_element_evm_metrics()`
     - Add variance filtering and severity calculation logic
     - Return filtered/prioritized rows focusing on problem areas
     - **Pros:** Clear separation of concerns, focused on variance analysis use case
     - **Cons:** Some code duplication with cost performance report (acceptable given different focus)

3. **Models Layer (New Models)**
   - **Candidate:** `backend/app/models/variance_analysis_report.py`
   - **Models:**
     - `VarianceAnalysisReportRowPublic` - Similar to `CostPerformanceReportRowPublic` but with variance emphasis
     - `VarianceAnalysisReportPublic` - Container with summary and rows array
     - Optional: Include variance severity enum/indicator
   - **Fields:**
     - All fields from `CostPerformanceReportRowPublic` (hierarchy, core metrics, indices, variances)
     - Add: `cv_percentage` (CV/BAC), `sv_percentage` (SV/BAC)
     - Add: `variance_severity` (optional: "critical", "warning", "normal" based on thresholds)
     - Add: `has_cost_variance_issue`, `has_schedule_variance_issue` (boolean flags)

### 2.2 Frontend Components Requiring Modification

1. **New VarianceAnalysisReport Component (Proposed)**
   - **Candidate:** `frontend/src/components/Reports/VarianceAnalysisReport.tsx`
   - **Architecture:**
     - Uses `DataTable` component with TanStack Table v8
     - React Query for data fetching (`ReportsService.getVarianceAnalysisReport()`)
     - Time-machine integration via `useTimeMachine()` hook
   - **Features:**
     - Tabular display emphasizing variance metrics (CV, SV, CV%, SV%)
     - Color-coded status indicators for variances (red=negative, yellow=zero, green=positive)
     - Default filtering/sorting by variance severity (most negative first)
     - Drill-down navigation: row click navigates to cost element detail page
     - Optional: Filter controls (variance type: CV only, SV only, both; severity threshold)
     - Summary section highlighting total variances and problem areas count
     - Visual emphasis on rows with significant variances (conditional row styling)
   - **Column Definitions:**
     - Hierarchy columns: WBE (machine_type), Cost Element (department_code, department_name)
     - Core metrics: BAC, PV, EV, AC (for context)
     - Variance metrics: CV, SV, CV% (CV/BAC), SV% (SV/BAC) - **PRIMARY COLUMNS**
     - Performance indices: CPI, SPI (secondary, for context)
     - Status indicators: Color-coded cells for CV, SV with severity badges

2. **Report Route Integration (Proposed)**
   - **Candidate:** `frontend/src/routes/_layout/projects.$id.reports.variance-analysis.tsx`
   - **Architecture:**
     - New route following E4-007 pattern: `/projects/:id/reports/variance-analysis`
     - Component wrapper that passes `projectId` to `VarianceAnalysisReport`
   - **Integration:**
     - Add navigation link from project detail page to variance analysis report
     - Follow same route guard pattern as cost performance report

3. **Navigation Integration**
   - **Project Detail Page:** Add "Variance Analysis" link in reports section or navigation tabs
   - **Drill-Down:** Row click navigates to cost element detail page (same as E4-007)

### 2.3 System Dependencies and External Integrations

- **Database:** No schema changes required; report uses existing EVM aggregation data
- **API Client:** OpenAPI client regeneration required after backend model changes
- **Time-Machine:** All report data respects control date (same as E4-007)
- **No External Dependencies:** Self-contained within existing codebase

---

## 3. ABSTRACTION INVENTORY

### 3.1 Reusable Abstractions

1. **EVM Metrics Service (`evm_aggregation.py`)**
   - `get_cost_element_evm_metrics()` - Core function computing all EVM metrics
   - Can be reused directly without modification
   - Provides all required variance data (CV, SV)

2. **Report Service Pattern (from `cost_performance_report.py`)**
   - Pattern: Service function that iterates cost elements, calls `get_cost_element_evm_metrics()`, builds rows array
   - Can be followed as template for variance analysis service
   - Helper functions: `_get_schedule_map()`, `_get_entry_map()` can be reused

3. **Status Indicator Helpers (from `CostPerformanceReport.tsx`)**
   - `getVarianceStatus()` - Already handles CV/SV status determination
   - Can be reused directly or extended with severity levels
   - Formatting helpers: `formatCurrency()`, `formatPercent()` can be reused

4. **DataTable Component (`DataTable.tsx`)**
   - Fully reusable for table display
   - Supports sorting, filtering, pagination, row click handlers
   - Column definitions follow `ColumnDefExtended<TData>` pattern

5. **Report Route Pattern (from `projects.$id.reports.cost-performance.tsx`)**
   - Can be replicated for variance analysis report
   - Route structure: `/projects/:id/reports/:report-type`
   - Component wrapper pattern

### 3.2 Test Utilities and Fixtures

1. **Backend Test Patterns (from `test_cost_performance_report.py`)**
   - Test fixtures for creating projects, WBEs, cost elements with schedules and earned value
   - Test patterns for verifying report structure and data accuracy
   - Can be reused or adapted for variance analysis report tests

2. **Frontend Test Patterns (from `CostPerformanceReport.test.tsx`)**
   - Component testing patterns using Vitest and React Testing Library
   - Mock patterns for API responses
   - Can be reused for variance analysis report component tests

---

## 4. ALTERNATIVE APPROACHES

### Approach A – Dedicated Variance Analysis Service with Focused Report Component (RECOMMENDED)

- **Summary:** Create a new dedicated service and report component focused specifically on variance analysis, emphasizing problem areas and variance metrics.

- **Backend:**
  - New service: `backend/app/services/variance_analysis_report.py` with `get_variance_analysis_report()`
  - Reuses `get_cost_element_evm_metrics()` from `evm_aggregation.py`
  - Adds variance-specific logic: severity calculation, optional filtering by thresholds
  - New models: `VarianceAnalysisReportPublic`, `VarianceAnalysisReportRowPublic`
  - New endpoint: `GET /projects/{project_id}/reports/variance-analysis`
  - Response includes all EVM metrics (for context) but emphasizes CV, SV, CV%, SV%

- **Frontend:**
  - New component: `VarianceAnalysisReport.tsx`
  - Uses `DataTable` with column definitions emphasizing variance metrics
  - Default sorting by variance severity (most negative first)
  - Visual emphasis on problem areas (conditional row styling, status badges)
  - Optional filter controls for variance type and severity thresholds
  - Reuses status indicator helpers from `CostPerformanceReport.tsx`

- **Pros:**
  - Clear separation of concerns (variance analysis vs. cost performance)
  - Focused on problem identification (emphasizes areas needing attention)
  - Easy to extend with advanced variance analysis features (trend analysis, root cause indicators)
  - Follows established patterns (E4-007 structure)
  - Can optimize for variance-specific use cases (filtering, sorting, visualization)

- **Cons/Risks:**
  - Some code duplication with cost performance report (acceptable given different focus)
  - Requires new service, models, and endpoint (but follows established patterns)
  - Initial implementation complexity (similar to E4-007)

- **Architectural Alignment:** High – follows established patterns, respects component composition, maintains consistency with E4-007

- **Estimated Complexity:** Medium – 15-20 hours (backend 5-7h, frontend 8-12h, testing 2-3h)

- **Risk Factors:**
  - Variance threshold definition (what constitutes "critical" vs "warning" variance) - needs business rule clarification
  - Performance with large datasets (many cost elements) - same consideration as E4-007

### Approach B – Extend Cost Performance Report with Variance Filtering

- **Summary:** Add variance-focused filtering and visualization options to existing Cost Performance Report component, allowing users to filter and sort by variance metrics.

- **Backend:**
  - Extend `get_cost_performance_report()` with optional query parameters:
    - `filter_by_variance: bool` - Filter rows to show only those with significant variances
    - `variance_threshold: float` - Threshold for "significant" variance (e.g., -10000)
    - `sort_by: str` - Sort field (e.g., "cv", "sv", "cv_percentage")
  - Add variance percentage calculations to `CostPerformanceReportRowPublic`
  - Response model remains the same (no breaking changes)

- **Frontend:**
  - Extend `CostPerformanceReport.tsx` with variance-specific features:
    - Add filter controls: variance type selector, threshold slider
    - Add default sorting option: "Most variance first"
    - Add visual emphasis mode: highlight rows with significant variances
    - Add variance-focused column ordering: move CV/SV columns to front
  - Component can switch between "comprehensive" and "variance-focused" views

- **Pros:**
  - Minimal code duplication (reuses existing report infrastructure)
  - Single report component handles multiple use cases
  - Less maintenance burden (one report to maintain instead of two)
  - Users can toggle between comprehensive and variance-focused views

- **Cons/Risks:**
  - Increases complexity of Cost Performance Report component (may violate single responsibility principle)
  - Mixes concerns (comprehensive reporting vs. problem identification)
  - May make component harder to extend with variance-specific features (trend analysis, root cause indicators)
  - Filtering logic may complicate cost performance report unnecessarily

- **Architectural Alignment:** Medium – functional but mixes concerns, may create maintenance burden

- **Estimated Complexity:** Medium – 12-16 hours (backend 3-5h, frontend 7-10h, testing 2-3h)

- **Risk Factors:**
  - Component complexity increases (may become harder to maintain)
  - User experience may be less focused (comprehensive report tries to do too much)

### Approach C – Client-Side Filtering of Cost Performance Report

- **Summary:** Build variance analysis view as a client-side wrapper around Cost Performance Report, filtering and reordering data client-side without backend changes.

- **Backend:**
  - No backend changes required
  - Reuses existing `/projects/{project_id}/reports/cost-performance` endpoint

- **Frontend:**
  - New component: `VarianceAnalysisReport.tsx`
  - Fetches data from cost performance report endpoint
  - Client-side filtering: filters rows based on variance thresholds
  - Client-side sorting: sorts by CV or SV (most negative first)
  - Client-side column reordering: emphasizes variance columns
  - Visual emphasis: conditional row styling for problem areas
  - Adds variance percentage calculations client-side

- **Pros:**
  - No backend changes required (fastest to implement)
  - Reuses existing API completely
  - Can be implemented quickly as a view layer on top of cost performance report

- **Cons/Risks:**
  - All data fetched even if filtered out (inefficient for large projects)
  - Variance percentage calculations duplicated (should be server-side for consistency)
  - Cannot add variance-specific backend optimizations (severity indicators, advanced filtering)
  - Client-side filtering may not scale well for large datasets
  - Violates principle of server-side data preparation (report generation should be server-side)

- **Architectural Alignment:** Low – works but violates best practices for report generation, may not scale well

- **Estimated Complexity:** Low – 8-12 hours (frontend only, 6-10h, testing 2-3h)

- **Risk Factors:**
  - Performance with large datasets (fetching all data then filtering client-side)
  - Data consistency (client-side calculations may differ from server-side)

---

## 5. ARCHITECTURAL IMPACT ASSESSMENT

### 5.1 Architectural Principles

**Follows:**
- **Single Responsibility Principle:** Dedicated variance analysis service and component focused on problem identification
- **DRY (Don't Repeat Yourself):** Reuses existing EVM aggregation services, status helpers, DataTable component
- **Separation of Concerns:** Clear separation between cost performance reporting (comprehensive) and variance analysis (problem-focused)
- **Consistency:** Follows E4-007 pattern for report structure and implementation
- **Testability:** Service layer is pure and testable, component uses dependency injection patterns

**Potential Violations:**
- **Code Duplication:** Some duplication with cost performance report (acceptable given different focus and use case)
- **Component Complexity:** Variance analysis component may become complex if adding many advanced features (mitigated by keeping core simple)

### 5.2 Maintenance Burden

**Low Risk Areas:**
- Backend service follows established patterns (easy to maintain and extend)
- Frontend component reuses existing abstractions (DataTable, status helpers)
- Models follow existing schema patterns (consistent with codebase)

**Medium Risk Areas:**
- Variance threshold definitions (business rules) may need adjustment over time
- Two report components to maintain (cost performance and variance analysis) - mitigated by following same patterns

**Future Maintenance Considerations:**
- If adding trend analysis (E4-008 mentions "trend analysis"), may need time-series data structures
- If adding root cause indicators, may need additional data sources or calculations
- Export functionality (E4-010) should work with both reports (reuse export utilities)

### 5.3 Testing Challenges

**Test Coverage Requirements:**
- Service layer: Test variance calculation accuracy, filtering logic, severity determination
- API layer: Test endpoint responses, error handling, time-machine integration
- Frontend component: Test table display, sorting, filtering, navigation, status indicators
- Edge cases:
  - Projects with no variances (all on-track)
  - Projects with all negative variances (major problems)
  - Projects with mixed variances (some positive, some negative)
  - Zero BAC scenarios (variance percentages undefined)
  - Null/undefined variance values

**Integration Testing:**
- Verify variance analysis report data matches cost performance report data (same underlying metrics)
- Verify time-machine integration (variances computed correctly for different control dates)
- Verify drill-down navigation (row click navigates correctly)

**Performance Testing:**
- Large projects (many cost elements) - verify report generation performance
- Filtering/sorting performance with large datasets

---

## Risks, Unknowns, and Ambiguities

### Business Rules Clarifications Needed

1. **Variance Severity Thresholds:**
   - What defines "critical" variance? (e.g., CV < -10% of BAC? CV < -€50,000?)
   - What defines "warning" variance? (e.g., -5% < CV < 0?)
   - Should thresholds be absolute (€ amount) or relative (% of BAC)?
   - Should thresholds be configurable per project or system-wide?

2. **Variance Percentage Calculation:**
   - CV% = CV / BAC? (standard EVM practice)
   - SV% = SV / BAC? (standard EVM practice)
   - How to handle zero BAC scenarios? (variance percentage undefined)
   - Should percentages be displayed alongside absolute values?

3. **Default Sorting and Filtering:**
   - Should report default to showing only problem areas (negative variances)?
   - Should report default to sorting by most negative CV, then most negative SV?
   - Should users be able to filter by variance type (CV only, SV only, both)?

4. **Trend Analysis Scope (PRD mentions "trend analysis"):**
   - Is trend analysis required for MVP, or future enhancement?
   - If required, what time periods? (weekly, monthly, quarterly?)
   - Should trend analysis show variance evolution over time or historical snapshots?

5. **Drill-Down Scope:**
   - Should drill-down navigate to cost element detail page (as in E4-007)?
   - Should drill-down show additional variance breakdown (e.g., by time period, by cost category)?
   - Should drill-down include variance explanations or root cause indicators?

### Performance Considerations

- Variance analysis report may need to process same data as cost performance report (similar performance characteristics)
- If adding trend analysis, may need time-series queries (performance impact to be evaluated)
- Filtering by variance thresholds should be efficient (indexed queries if thresholds are absolute values)

### Data Quality Risks

- Incomplete or inconsistent EV, PV, or AC data will yield misleading variances (same as E4-007)
- Need clear UI indicators when required inputs are missing (e.g., no EV yet → variances not meaningful)
- Negative variances are valid and expected (over-budget, behind-schedule); UI should handle appropriately

### Integration with Existing Features

- **Time-Machine:** All variance calculations must respect control date (same as E4-007)
- **Export (E4-010):** Variance analysis report should be exportable (reuse export utilities)
- **Dashboard (E4-009):** Variance analysis data may be needed for dashboard visualizations (ensure data structure supports this)

---

## Summary & Next Steps

### User Story Summary

**What:** Create a Variance Analysis Report that highlights areas where project performance deviates from plan, focusing on cost and schedule variances (CV, SV) with drill-down capabilities to supporting detail. The report should emphasize problem areas (negative variances) and enable quick identification of root causes.

**Why:** Provide project managers with a focused view of performance problems, enabling rapid identification of areas needing attention, investigation of root causes, and implementation of corrective actions. Supports proactive project management by surfacing issues early before they escalate.

### Recommended Approach

**Approach A – Dedicated Variance Analysis Service with Focused Report Component** is recommended because:

1. **Clear Focus:** Dedicated service and component focused on problem identification (emphasizes areas needing attention)
2. **Scalability:** Easy to extend with advanced variance analysis features (trend analysis, root cause indicators, variance explanations)
3. **User Experience:** Provides focused, actionable view of problems (not buried in comprehensive report)
4. **Consistency:** Follows established E4-007 pattern (easy to understand and maintain)
5. **Separation of Concerns:** Clear separation between comprehensive reporting (cost performance) and problem identification (variance analysis)

### Business Rules to Confirm

- **Variance Severity Thresholds:** Define "critical" and "warning" variance thresholds (absolute € or relative % of BAC?)
- **Variance Percentage:** Confirm CV% = CV/BAC, SV% = SV/BAC (standard EVM practice)
- **Default Behavior:** Default to showing problem areas only, or show all with sorting by severity?
- **Trend Analysis:** Required for MVP, or future enhancement?
- **Drill-Down:** Navigate to cost element detail page (as in E4-007), or additional variance breakdown?

### Implementation Scope

- **Backend:**
  - New service: `backend/app/services/variance_analysis_report.py`
  - New models: `backend/app/models/variance_analysis_report.py`
  - New endpoint: `GET /projects/{project_id}/reports/variance-analysis`
  - Reuses existing `EvmMetricsService` aggregation logic
  - Adds variance-specific logic (severity calculation, optional filtering)
  - Estimated: 5-7 hours

- **Frontend:**
  - New component: `VarianceAnalysisReport.tsx`
  - New route: `projects.$id.reports.variance-analysis.tsx`
  - Uses `DataTable` with variance-emphasized column definitions
  - Reuses status indicator helpers from `CostPerformanceReport.tsx`
  - Default sorting by variance severity
  - Optional filter controls (variance type, severity threshold)
  - Estimated: 8-12 hours

- **Testing:**
  - Backend service and API tests (variance calculation, filtering, severity determination)
  - Frontend component tests (table display, sorting, filtering, navigation)
  - Integration tests (time-machine, data accuracy, drill-down navigation)
  - Estimated: 2-3 hours

**Total Estimated Effort:** 15-20 hours

### Next Steps

1. **Clarify Business Rules:** Confirm variance severity thresholds, percentage calculations, default behavior, trend analysis scope
2. **Detailed Planning:** Create TDD-focused implementation plan following E4-007 detailed plan pattern
3. **Implementation:** Follow TDD discipline with failing tests first, incremental commits, architectural respect

---

**Reference:** This analysis follows the PLA-1 high-level analysis template and leverages existing Cost Performance Report (E4-007), EVM aggregation (E4-005), variance calculations (E4-004), and time-machine patterns documented in `docs/analysis/*.md` and `docs/plans/*.plan.md`. The recommended approach aligns with established report generation patterns and maintains consistency with the existing codebase.
