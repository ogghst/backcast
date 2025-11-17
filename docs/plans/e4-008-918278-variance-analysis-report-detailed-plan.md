# Detailed Implementation Plan: E4-008 Variance Analysis Report

**Task:** E4-008 - Variance Analysis Report
**Sprint:** Sprint 5 - Reporting and Performance Dashboards
**Status:** Planning Phase
**Date:** 2025-11-17
**Current Time:** 11:47 CET (Europe/Rome)
**Approach:** Approach A - Dedicated Variance Analysis Service with Focused Report Component

---

## EXECUTION CONTEXT

- This plan will be implemented using TDD discipline with human supervision
- Implementation will occur in steps within this conversation thread
- Each step must have clear stop/go criteria
- Maximum 3 iteration attempts per step before stopping to ask for help
- Red-green-refactor cycle must be followed for each step
- Tests must verify behavior, not just compilation

---

## SCOPE BOUNDARIES

**In Scope:**
- Configuration database table for variance thresholds (critical/warning levels as percentages)
- Backend API endpoint for variance analysis report data
- Variance percentage calculations (CV% = CV/BAC, SV% = SV/BAC, undefined if BAC = 0)
- Report default: show only problem areas, sorted by most negative CV
- User filtering by CV and SV
- Trend analysis: monthly level variance evolution over time
- Frontend report component using DataTable with TanStack Table
- Tabular display emphasizing variance metrics (CV, SV, CV%, SV%)
- Color-coded status indicators for variances based on configurable thresholds
- Time-machine integration (control date filtering)
- Drill-down navigation to cost element detail page (as in E4-007)
- Quick variance explanation feature in drill-down view
- Summary section highlighting total variances and problem areas count
- Responsive design (mobile, tablet, desktop)

**Out of Scope (MVP):**
- Export functionality (CSV, Excel) - deferred to E4-010
- Advanced trend analysis (daily, weekly granularity) - future enhancement
- Server-side pagination (not needed for 30-40 WBEs, up to 200 cost elements)
- WBE-level and cost element-level dedicated report pages - future enhancement
- Report scheduling or email delivery
- Variance root cause analysis beyond basic explanation

**Design for Future:**
- Configuration table structure should support additional threshold types
- Trend analysis architecture should support multiple granularities
- Component structure should support export functionality integration

---

## STAKEHOLDER CLARIFICATIONS CONFIRMED

- **Separate Backend Endpoint:** Approach A - dedicated service and endpoint (confirmed)
- **Variance Thresholds:** Percentage-based, configurable at admin level via configuration database table (confirmed)
- **Variance Percentage Calculation:** CV% = CV/BAC, SV% = SV/BAC, undefined if BAC = 0, show both percentage and absolute values (confirmed)
- **Default Behavior:** Show only problem areas (negative variances), sorted by most negative CV (confirmed)
- **User Filtering:** Users can filter by CV and SV (confirmed)
- **Trend Analysis:** Required for MVP, monthly level, showing variance evolution over time (confirmed)
- **Drill-Down:** Navigate to cost element detail page (as in E4-007), include quick variance explanation (confirmed)

---

## IMPLEMENTATION STEPS

### Phase 1: Configuration Table for Variance Thresholds

#### Step 1: Create Variance Threshold Configuration Model

**Description:** Create database model for storing variance threshold configurations. Thresholds are percentage-based (CV% and SV%) and configurable at admin level.

**Test-First Requirement:**
- Write failing test that verifies model structure:
  - Required fields: `threshold_type` (enum: "critical_cv", "warning_cv", "critical_sv", "warning_sv"), `threshold_percentage` (Decimal, -100 to 0)
  - Optional fields: `description`, `is_active` (boolean, default True)
  - Timestamps: `created_at`, `updated_at`
  - Unique constraint: one active threshold per type
  - Test model serialization/deserialization
  - Test CRUD operations

**Acceptance Criteria:**
- ✅ New model file: `backend/app/models/variance_threshold_config.py`
- ✅ Model classes:
  - `VarianceThresholdConfigBase` (shared properties)
  - `VarianceThresholdConfigCreate` (creation schema)
  - `VarianceThresholdConfigUpdate` (update schema)
  - `VarianceThresholdConfigPublic` (response schema)
  - `VarianceThresholdConfig` (database model with SQLModel)
- ✅ Enum: `VarianceThresholdType` with values: "critical_cv", "warning_cv", "critical_sv", "warning_sv"
- ✅ Validation: `threshold_percentage` must be between -100 and 0 (negative values only)
- ✅ Unique constraint: only one active threshold per type
- ✅ Models exported in `backend/app/models/__init__.py`
- ✅ Test passes verifying model structure, validation, and CRUD operations

**Expected Files Created:**
- `backend/app/models/variance_threshold_config.py`
- `backend/tests/models/test_variance_threshold_config.py`

**Expected Files Modified:**
- `backend/app/models/__init__.py`

**Dependencies:**
- None (first step)

**Estimated Effort:** 2-3 hours

---

#### Step 2: Create Database Migration for Variance Threshold Config Table

**Description:** Create Alembic migration to add `variance_threshold_config` table to database schema.

**Test-First Requirement:**
- Write failing test that verifies:
  - Table exists with correct columns
  - Unique constraint on (threshold_type, is_active) where is_active = True
  - Foreign keys and indexes are correct
  - Default values are set correctly

**Acceptance Criteria:**
- ✅ New migration file: `backend/app/alembic/versions/XXXX_add_variance_threshold_config_table.py`
- ✅ Migration creates `variance_threshold_config` table with:
  - `variance_threshold_config_id` (UUID primary key)
  - `threshold_type` (enum, not null)
  - `threshold_percentage` (DECIMAL(5, 2), not null, constraint: -100 <= value <= 0)
  - `description` (VARCHAR(500), nullable)
  - `is_active` (BOOLEAN, not null, default True)
  - `created_at` (TIMESTAMP, not null)
  - `updated_at` (TIMESTAMP, not null)
- ✅ Unique constraint: `(threshold_type, is_active)` where `is_active = True`
- ✅ Index on `threshold_type` and `is_active`
- ✅ Migration up/down tested
- ✅ Migration applied successfully to test database

**Expected Files Created:**
- `backend/app/alembic/versions/XXXX_add_variance_threshold_config_table.py`

**Expected Files Modified:**
- None

**Dependencies:**
- Step 1 (model)

**Estimated Effort:** 1 hour

---

#### Step 3: Create CRUD API for Variance Threshold Configuration

**Description:** Create FastAPI endpoints for managing variance threshold configurations. Admin-only access required.

**Test-First Requirement:**
- Write failing test that verifies:
  - `GET /variance-threshold-configs` - List all configurations (admin only)
  - `GET /variance-threshold-configs/{config_id}` - Get single configuration (admin only)
  - `POST /variance-threshold-configs` - Create configuration (admin only)
  - `PUT /variance-threshold-configs/{config_id}` - Update configuration (admin only)
  - `DELETE /variance-threshold-configs/{config_id}` - Delete configuration (admin only)
  - Authorization checks (non-admin users get 403)
  - Validation: threshold_percentage must be -100 <= value <= 0
  - Unique constraint: only one active threshold per type

**Acceptance Criteria:**
- ✅ New route file: `backend/app/api/routes/variance_threshold_config.py`
- ✅ Router registered in `backend/app/api/main.py`
- ✅ Endpoints:
  - `GET /variance-threshold-configs` - List all (admin only)
  - `GET /variance-threshold-configs/{config_id}` - Get single (admin only)
  - `POST /variance-threshold-configs` - Create (admin only)
  - `PUT /variance-threshold-configs/{config_id}` - Update (admin only)
  - `DELETE /variance-threshold-configs/{config_id}` - Delete (admin only)
- ✅ Authorization: Admin role required (use `get_current_active_superuser` dependency)
- ✅ Validation: `threshold_percentage` between -100 and 0
- ✅ Business logic: When creating/updating active threshold, deactivate previous active threshold of same type
- ✅ Tests passing verifying all CRUD operations and authorization

**Expected Files Created:**
- `backend/app/api/routes/variance_threshold_config.py`
- `backend/tests/api/routes/test_variance_threshold_config.py`

**Expected Files Modified:**
- `backend/app/api/main.py` (router registration)

**Dependencies:**
- Step 1 (model), Step 2 (migration)

**Estimated Effort:** 3-4 hours

---

#### Step 4: Seed Default Variance Threshold Configurations

**Description:** Create seed data for default variance threshold configurations. Defaults: critical CV = -10%, warning CV = -5%, critical SV = -10%, warning SV = -5%.

**Test-First Requirement:**
- Write failing test that verifies:
  - Seed function creates 4 default configurations if none exist
  - Seed function does not overwrite existing configurations
  - Default values are correct: critical = -10%, warning = -5%

**Acceptance Criteria:**
- ✅ Seed function: `_seed_variance_threshold_configs(session: Session)`
- ✅ Function creates 4 default configurations:
  - `threshold_type="critical_cv"`, `threshold_percentage=-10.00`, `is_active=True`
  - `threshold_type="warning_cv"`, `threshold_percentage=-5.00`, `is_active=True`
  - `threshold_type="critical_sv"`, `threshold_percentage=-10.00`, `is_active=True`
  - `threshold_type="warning_sv"`, `threshold_percentage=-5.00`, `is_active=True`
- ✅ Function only creates if configurations don't exist
- ✅ Function called in `backend/app/core/db.py` `init_db()` function
- ✅ Test passes verifying seed data creation

**Expected Files Modified:**
- `backend/app/core/seeds.py` (add seed function)
- `backend/app/core/db.py` (call seed function in init_db)

**Dependencies:**
- Step 1 (model), Step 2 (migration), Step 3 (CRUD API)

**Estimated Effort:** 1 hour

---

### Phase 2: Backend Service and Models

#### Step 5: Create Variance Analysis Report Models

**Description:** Create Pydantic response models for variance analysis report data structure. Includes variance percentages and severity indicators.

**Test-First Requirement:**
- Write failing test that verifies model structure:
  - Required fields: cost_element_id, wbe_id, wbe_name, department_code, department_name, all EVM metrics, CV, SV, CV%, SV%
  - Optional fields: cv_percentage, sv_percentage (undefined if BAC = 0), variance_severity
  - Data types: UUIDs, strings, Decimals, optional None values for percentages
  - Test model serialization/deserialization

**Acceptance Criteria:**
- ✅ New model file: `backend/app/models/variance_analysis_report.py`
- ✅ Model classes:
  - `VarianceAnalysisReportRowPublic` with fields:
    - Hierarchy: `cost_element_id`, `wbe_id`, `wbe_name`, `wbe_serial_number`, `department_code`, `department_name`, `cost_element_type_id`, `cost_element_type_name`
    - Core metrics: `planned_value`, `earned_value`, `actual_cost`, `budget_bac`
    - Performance indices: `cpi`, `spi`, `tcpi`
    - Variances: `cost_variance`, `schedule_variance`
    - Variance percentages: `cv_percentage` (Decimal | None), `sv_percentage` (Decimal | None)
    - Severity: `variance_severity` (str | None: "critical", "warning", "normal")
    - Flags: `has_cost_variance_issue` (bool), `has_schedule_variance_issue` (bool)
  - `VarianceAnalysisReportPublic` containing:
    - `project_id`, `project_name`, `control_date`
    - `rows: list[VarianceAnalysisReportRowPublic]` (filtered to problem areas by default)
    - `summary: EVMIndicesProjectPublic` (aggregated project totals)
    - `total_problem_areas: int` (count of rows with issues)
    - `config_used: dict` (variance threshold config used for severity calculation)
- ✅ Validation: CV% = CV/BAC if BAC > 0, else None; SV% = SV/BAC if BAC > 0, else None
- ✅ Models exported in `backend/app/models/__init__.py`
- ✅ Test passes verifying model structure and serialization

**Expected Files Created:**
- `backend/app/models/variance_analysis_report.py`
- `backend/tests/models/test_variance_analysis_report.py`

**Expected Files Modified:**
- `backend/app/models/__init__.py`

**Dependencies:**
- Step 1 (variance threshold config model)

**Estimated Effort:** 2-3 hours

---

#### Step 6: Create Helper Function to Get Active Variance Thresholds

**Description:** Create helper function that retrieves active variance threshold configurations from database.

**Test-First Requirement:**
- Write failing test that verifies:
  - Function returns dictionary with threshold_type as key, threshold_percentage as value
  - Only returns active thresholds (is_active = True)
  - Returns None for missing threshold types
  - Handles empty database (returns empty dict or defaults)

**Acceptance Criteria:**
- ✅ Helper function: `get_active_variance_thresholds(session: Session) -> dict[str, Decimal]`
- ✅ Function queries `VarianceThresholdConfig` where `is_active = True`
- ✅ Returns dict: `{"critical_cv": Decimal("-10.00"), "warning_cv": Decimal("-5.00"), ...}`
- ✅ Location: `backend/app/services/variance_analysis_report.py` or shared helpers
- ✅ Test passes verifying function returns correct thresholds

**Expected Files Created:**
- `backend/app/services/variance_analysis_report.py` (or helper module)

**Expected Files Modified:**
- None

**Dependencies:**
- Step 1 (variance threshold config model)

**Estimated Effort:** 1 hour

---

#### Step 7: Create Variance Severity Calculation Function

**Description:** Create function that calculates variance severity based on thresholds. Determines if cost element has critical/warning/normal variance.

**Test-First Requirement:**
- Write failing test that verifies:
  - Critical CV: CV% < critical_cv threshold (e.g., -15% < -10%)
  - Warning CV: critical_cv threshold <= CV% < warning_cv threshold (e.g., -7% between -10% and -5%)
  - Normal CV: CV% >= warning_cv threshold (e.g., -3% >= -5%)
  - Same logic for SV
  - Returns "critical", "warning", "normal", or None if percentages undefined
  - Handles zero BAC (percentages undefined, returns None)

**Acceptance Criteria:**
- ✅ Function: `calculate_variance_severity(cv_percentage: Decimal | None, sv_percentage: Decimal | None, thresholds: dict[str, Decimal]) -> str | None`
- ✅ Logic:
  - If CV% < critical_cv threshold → "critical" for cost variance
  - If critical_cv threshold <= CV% < warning_cv threshold → "warning" for cost variance
  - If CV% >= warning_cv threshold → "normal" for cost variance
  - Same for SV%
  - Overall severity = max(severity_cv, severity_sv) or None if both undefined
- ✅ Returns: "critical", "warning", "normal", or None
- ✅ Location: `backend/app/services/variance_analysis_report.py`
- ✅ Test passes verifying severity calculation for all cases

**Expected Files Created:**
- `backend/app/services/variance_analysis_report.py` (if not exists)

**Expected Files Modified:**
- None

**Dependencies:**
- Step 6 (get active thresholds)

**Estimated Effort:** 2 hours

---

#### Step 8: Create Variance Analysis Report Service Function

**Description:** Create service function that aggregates EVM metrics for all cost elements, calculates variance percentages and severity, filters to problem areas, and returns report rows.

**Test-First Requirement:**
- Write failing test that verifies:
  - Function signature: `get_variance_analysis_report(session, project_id, control_date, show_only_problems=True, sort_by="cv") -> VarianceAnalysisReportPublic`
  - Returns cost elements with EVM metrics, CV%, SV%, and severity
  - Filters to problem areas when `show_only_problems=True` (only rows with negative CV or SV)
  - Sorts by most negative CV when `sort_by="cv"`
  - Sorts by most negative SV when `sort_by="sv"`
  - Calculates variance percentages (CV/BAC, SV/BAC) correctly, returns None if BAC = 0
  - Respects time-machine control date
  - Handles empty project (returns empty rows list, zero summary)
  - Includes summary with aggregated totals and problem area count

**Acceptance Criteria:**
- ✅ Service function: `get_variance_analysis_report(session, project_id, control_date, show_only_problems=True, sort_by="cv") -> VarianceAnalysisReportPublic`
- ✅ Reuses existing `get_cost_element_evm_metrics()` from `evm_aggregation.py`
- ✅ For each cost element:
  - Calls `get_cost_element_evm_metrics()` to get EVM metrics
  - Calculates CV% = CV/BAC if BAC > 0, else None
  - Calculates SV% = SV/BAC if BAC > 0, else None
  - Gets active variance thresholds
  - Calculates variance severity using `calculate_variance_severity()`
  - Sets flags: `has_cost_variance_issue` (CV < 0), `has_schedule_variance_issue` (SV < 0)
- ✅ Filters rows: if `show_only_problems=True`, only include rows where CV < 0 or SV < 0
- ✅ Sorts rows: by most negative CV if `sort_by="cv"`, by most negative SV if `sort_by="sv"`
- ✅ Aggregates project summary using existing EVM aggregation functions
- ✅ Counts problem areas: number of rows with CV < 0 or SV < 0
- ✅ Returns `VarianceAnalysisReportPublic` with rows, summary, total_problem_areas, config_used
- ✅ Test passes verifying function returns correct data structure and filtering/sorting

**Expected Files Created:**
- `backend/app/services/variance_analysis_report.py` (if not exists)

**Expected Files Modified:**
- None

**Dependencies:**
- Step 5 (report models), Step 7 (severity calculation)

**Estimated Effort:** 4-5 hours

---

### Phase 3: Trend Analysis Backend

#### Step 9: Create Variance Trend Analysis Models

**Description:** Create Pydantic response models for variance trend analysis. Monthly-level data showing variance evolution over time.

**Test-First Requirement:**
- Write failing test that verifies model structure:
  - Required fields: `month` (date), `cost_variance`, `schedule_variance`, `cv_percentage`, `sv_percentage`
  - Optional fields: None (all required for trend point)
  - Data types: date, Decimal, Decimal | None for percentages
  - Test model serialization/deserialization
  - Test list of trend points

**Acceptance Criteria:**
- ✅ Model classes in `backend/app/models/variance_analysis_report.py`:
  - `VarianceTrendPointPublic` with fields:
    - `month: date` (first day of month)
    - `cost_variance: Decimal`
    - `schedule_variance: Decimal`
    - `cv_percentage: Decimal | None` (CV/BAC if BAC > 0, else None)
    - `sv_percentage: Decimal | None` (SV/BAC if BAC > 0, else None)
  - `VarianceTrendPublic` containing:
    - `cost_element_id: uuid.UUID` (if cost element level) or None (if project/WBE level)
    - `wbe_id: uuid.UUID` (if WBE level) or None (if project level)
    - `project_id: uuid.UUID`
    - `control_date: date` (current control date)
    - `trend_points: list[VarianceTrendPointPublic]` (monthly data points)
- ✅ Models exported in `backend/app/models/__init__.py`
- ✅ Test passes verifying model structure and serialization

**Expected Files Modified:**
- `backend/app/models/variance_analysis_report.py`

**Dependencies:**
- Step 5 (report models)

**Estimated Effort:** 1-2 hours

---

#### Step 10: Create Variance Trend Analysis Service Function

**Description:** Create service function that calculates monthly variance evolution over time. For each month from project start to control date, calculates CV and SV as of that month.

**Test-First Requirement:**
- Write failing test that verifies:
  - Function signature: `get_variance_trend(session, project_id, cost_element_id=None, wbe_id=None, control_date) -> VarianceTrendPublic`
  - Returns monthly trend points from project start date to control date
  - Each point contains CV, SV, CV%, SV% as of that month's end
  - For project level: aggregates all cost elements
  - For WBE level: aggregates cost elements in WBE
  - For cost element level: single cost element data
  - Handles empty data (returns empty trend_points list)

**Acceptance Criteria:**
- ✅ Service function: `get_variance_trend(session, project_id, cost_element_id=None, wbe_id=None, control_date) -> VarianceTrendPublic`
- ✅ Function generates monthly data points:
  - Start: project start date (first day of month)
  - End: control date (last day of month)
  - Granularity: monthly (first day of each month)
- ✅ For each month:
  - Uses time-machine control date = last day of month
  - Calls `get_cost_element_evm_metrics()` for each cost element (respecting filters)
  - Aggregates CV, SV, BAC for selected level (project/WBE/cost element)
  - Calculates CV% = CV/BAC if BAC > 0, else None
  - Calculates SV% = SV/BAC if BAC > 0, else None
  - Creates `VarianceTrendPointPublic` for that month
- ✅ Aggregates across cost elements if project/WBE level
- ✅ Returns `VarianceTrendPublic` with trend_points list
- ✅ Test passes verifying trend calculation and aggregation

**Expected Files Modified:**
- `backend/app/services/variance_analysis_report.py`

**Dependencies:**
- Step 9 (trend models), Step 8 (report service)

**Estimated Effort:** 4-5 hours

---

### Phase 4: Backend API Routes

#### Step 11: Create Variance Analysis Report API Endpoint

**Description:** Create FastAPI endpoint that exposes the variance analysis report via REST API.

**Test-First Requirement:**
- Write failing test that verifies:
  - `GET /projects/{project_id}/reports/variance-analysis` returns VarianceAnalysisReportPublic
  - Query parameters: `show_only_problems` (bool, default True), `sort_by` (str, "cv" | "sv", default "cv")
  - Respects time-machine control date
  - Returns 404 if project not found
  - Returns 200 with correct data structure
  - Authorization: authenticated user required

**Acceptance Criteria:**
- ✅ New route file: `backend/app/api/routes/variance_analysis_report.py`
- ✅ Router registered in `backend/app/api/main.py`
- ✅ Endpoint: `GET /projects/{project_id}/reports/variance-analysis`
- ✅ Query parameters:
  - `show_only_problems: bool = True` (filter to problem areas)
  - `sort_by: str = "cv"` (sort by "cv" or "sv")
- ✅ Dependencies: `SessionDep`, `CurrentUser`, `get_time_machine_control_date`
- ✅ Calls `get_variance_analysis_report()` service function
- ✅ Returns `VarianceAnalysisReportPublic` response model
- ✅ Error handling: 404 if project not found
- ✅ Test passes verifying endpoint returns correct data

**Expected Files Created:**
- `backend/app/api/routes/variance_analysis_report.py`
- `backend/tests/api/routes/test_variance_analysis_report.py`

**Expected Files Modified:**
- `backend/app/api/main.py` (router registration)

**Dependencies:**
- Step 8 (service function)

**Estimated Effort:** 2-3 hours

---

#### Step 12: Create Variance Trend Analysis API Endpoint

**Description:** Create FastAPI endpoint that exposes variance trend analysis via REST API.

**Test-First Requirement:**
- Write failing test that verifies:
  - `GET /projects/{project_id}/reports/variance-analysis/trend` returns VarianceTrendPublic (project level)
  - `GET /projects/{project_id}/reports/variance-analysis/trend?wbe_id={wbe_id}` returns WBE level trend
  - `GET /projects/{project_id}/reports/variance-analysis/trend?cost_element_id={cost_element_id}` returns cost element level trend
  - Respects time-machine control date
  - Returns 404 if project/WBE/cost element not found
  - Returns 200 with correct data structure

**Acceptance Criteria:**
- ✅ Endpoint in `backend/app/api/routes/variance_analysis_report.py`:
  - `GET /projects/{project_id}/reports/variance-analysis/trend`
- ✅ Query parameters:
  - `wbe_id: uuid.UUID | None = None` (optional, for WBE level)
  - `cost_element_id: uuid.UUID | None = None` (optional, for cost element level)
- ✅ Dependencies: `SessionDep`, `CurrentUser`, `get_time_machine_control_date`
- ✅ Calls `get_variance_trend()` service function
- ✅ Returns `VarianceTrendPublic` response model
- ✅ Error handling: 404 if project/WBE/cost element not found
- ✅ Validation: wbe_id and cost_element_id are mutually exclusive
- ✅ Test passes verifying endpoint returns correct trend data

**Expected Files Modified:**
- `backend/app/api/routes/variance_analysis_report.py`
- `backend/tests/api/routes/test_variance_analysis_report.py`

**Dependencies:**
- Step 10 (trend service function), Step 11 (report endpoint)

**Estimated Effort:** 2-3 hours

---

### Phase 5: OpenAPI Client Regeneration

#### Step 13: Regenerate OpenAPI Client

**Description:** Regenerate frontend OpenAPI client to include new variance analysis report endpoints and models.

**Test-First Requirement:**
- Write failing test that verifies:
  - New service: `VarianceAnalysisReportService` with methods
  - New types: `VarianceAnalysisReportPublic`, `VarianceAnalysisReportRowPublic`, `VarianceTrendPublic`, `VarianceTrendPointPublic`
  - TypeScript compilation succeeds

**Acceptance Criteria:**
- ✅ Run OpenAPI client generation: `cd frontend && npm run generate:client`
- ✅ New service methods in generated client:
  - `VarianceAnalysisReportService.getProjectVarianceAnalysisReport()`
  - `VarianceAnalysisReportService.getVarianceTrend()`
- ✅ New TypeScript types generated for all models
- ✅ TypeScript compilation succeeds: `npm run build`
- ✅ No breaking changes to existing client code

**Expected Files Modified:**
- `frontend/src/client/` (generated files)

**Dependencies:**
- Step 11 (report endpoint), Step 12 (trend endpoint)

**Estimated Effort:** 15 minutes

---

### Phase 6: Frontend Report Component (Basic)

#### Step 14: Create Variance Analysis Report Component (Basic Structure)

**Description:** Create basic React component structure for variance analysis report. Uses DataTable with column definitions emphasizing variance metrics.

**Test-First Requirement:**
- Write failing test that verifies:
  - Component renders with loading state
  - Component fetches data from API using React Query
  - Component displays table with correct columns
  - Component handles empty state (no problem areas)

**Acceptance Criteria:**
- ✅ New component file: `frontend/src/components/Reports/VarianceAnalysisReport.tsx`
- ✅ Component props: `projectId: string`
- ✅ Uses React Query: `useQuery()` with `VarianceAnalysisReportService.getProjectVarianceAnalysisReport()`
- ✅ Uses `DataTable` component with TanStack Table v8
- ✅ Column definitions (basic structure):
  - Hierarchy columns: WBE, Cost Element
  - Core metrics: BAC, PV, EV, AC (for context)
  - Variance metrics: CV, SV, CV%, SV% (PRIMARY COLUMNS)
  - Performance indices: CPI, SPI (secondary, for context)
- ✅ Loading state: skeleton table
- ✅ Empty state: message when no problem areas
- ✅ Test passes verifying component renders and fetches data

**Expected Files Created:**
- `frontend/src/components/Reports/VarianceAnalysisReport.tsx`
- `frontend/src/components/Reports/__tests__/VarianceAnalysisReport.test.tsx`

**Dependencies:**
- Step 13 (OpenAPI client)

**Estimated Effort:** 3-4 hours

---

#### Step 15: Add Variance Status Indicators and Formatting

**Description:** Add color-coded status indicators for variances based on configurable thresholds. Add formatting helpers for currency and percentages.

**Test-First Requirement:**
- Write failing test that verifies:
  - Status indicator functions return correct color/icon/label based on variance value
  - Formatting helpers format currency and percentages correctly
  - Status indicators handle undefined/null values (CV%, SV%)

**Acceptance Criteria:**
- ✅ Status indicator helpers (reuse/extend from `CostPerformanceReport.tsx`):
  - `getVarianceStatus()` - Returns color, icon, label for CV/SV values
  - `getSeverityStatus()` - Returns color, icon, label for severity ("critical", "warning", "normal")
- ✅ Formatting helpers:
  - `formatCurrency()` - Format CV, SV as currency (€X,XXX.XX)
  - `formatPercentage()` - Format CV%, SV% as percentage (X.XX% or "N/A")
- ✅ Color coding:
  - Critical: Red (based on thresholds from config)
  - Warning: Yellow (based on thresholds from config)
  - Normal/Positive: Green
  - Undefined/Zero: Gray
- ✅ Column cells use status indicators for visual emphasis
- ✅ Test passes verifying status indicators and formatting

**Expected Files Modified:**
- `frontend/src/components/Reports/VarianceAnalysisReport.tsx`

**Dependencies:**
- Step 14 (basic component)

**Estimated Effort:** 2-3 hours

---

### Phase 7: Frontend Filtering and Sorting

#### Step 16: Add Filter Controls (CV and SV)

**Description:** Add filter controls allowing users to filter report by CV and SV. Default: show only problem areas.

**Test-First Requirement:**
- Write failing test that verifies:
  - Filter controls render (checkboxes or toggle buttons)
  - Default state: "Show only problem areas" checked
  - Filtering updates API query parameters
  - Filtering updates displayed rows

**Acceptance Criteria:**
- ✅ Filter controls UI:
  - Toggle: "Show only problem areas" (default: checked, maps to `show_only_problems=true`)
  - Optionally: Checkboxes for "CV only", "SV only", "Both" (if filtering by variance type)
- ✅ Filter state managed with React `useState`
- ✅ Filter changes update API query:
  - `show_only_problems` query parameter
  - React Query refetches data when filters change
- ✅ Filter UI uses Chakra UI components (Switch, Checkbox)
- ✅ Filter section styled consistently with other reports
- ✅ Test passes verifying filtering functionality

**Expected Files Modified:**
- `frontend/src/components/Reports/VarianceAnalysisReport.tsx`

**Dependencies:**
- Step 14 (basic component), Step 11 (API endpoint with query params)

**Estimated Effort:** 2-3 hours

---

#### Step 17: Add Sort Controls

**Description:** Add sort controls allowing users to sort report by CV or SV. Default: sort by most negative CV.

**Test-First Requirement:**
- Write failing test that verifies:
  - Sort controls render (radio buttons or dropdown)
  - Default state: "Sort by CV (most negative first)"
  - Sorting updates API query parameters
  - Sorting updates displayed rows

**Acceptance Criteria:**
- ✅ Sort controls UI:
  - Radio buttons or dropdown: "Sort by CV", "Sort by SV" (default: "cv")
  - Visual indicator: arrow showing sort direction (descending for negative values)
- ✅ Sort state managed with React `useState`
- ✅ Sort changes update API query:
  - `sort_by` query parameter ("cv" or "sv")
  - React Query refetches data when sort changes
- ✅ Sort UI uses Chakra UI components (RadioGroup, Select)
- ✅ Sort section styled consistently with other reports
- ✅ Test passes verifying sorting functionality

**Expected Files Modified:**
- `frontend/src/components/Reports/VarianceAnalysisReport.tsx`

**Dependencies:**
- Step 16 (filter controls), Step 11 (API endpoint with sort_by param)

**Estimated Effort:** 2-3 hours

---

### Phase 8: Frontend Trend Analysis Visualization

#### Step 18: Create Variance Trend Chart Component

**Description:** Create Chart.js line chart component showing monthly variance evolution over time (CV and SV).

**Test-First Requirement:**
- Write failing test that verifies:
  - Component renders line chart with CV and SV lines
  - Chart shows monthly data points
  - Chart uses time scale on X-axis
  - Chart displays both CV and SV datasets

**Acceptance Criteria:**
- ✅ New component: `frontend/src/components/Reports/VarianceTrendChart.tsx`
- ✅ Uses Chart.js `Line` chart with `react-chartjs-2`
- ✅ Props: `trendData: VarianceTrendPublic`
- ✅ Chart configuration:
  - X-axis: Time scale (monthly, first day of each month)
  - Y-axis: Linear scale (currency for CV, SV)
  - Datasets:
    - CV line: Red/orange color, label "Cost Variance (CV)"
    - SV line: Blue color, label "Schedule Variance (SV)"
  - Tooltips: Show month, CV, SV, CV%, SV%
  - Legend: Both lines visible
- ✅ Handles empty data (no trend points)
- ✅ Responsive design
- ✅ Test passes verifying chart renders correctly

**Expected Files Created:**
- `frontend/src/components/Reports/VarianceTrendChart.tsx`
- `frontend/src/components/Reports/__tests__/VarianceTrendChart.test.tsx`

**Dependencies:**
- Step 13 (OpenAPI client), Step 12 (trend API endpoint)

**Estimated Effort:** 3-4 hours

---

#### Step 19: Integrate Trend Chart into Report Component

**Description:** Integrate variance trend chart into main report component. Show trend for project level or selected cost element.

**Test-First Requirement:**
- Write failing test that verifies:
  - Trend chart section renders in report component
  - Trend chart fetches data from API
  - Trend chart displays when data available
  - Trend chart shows loading state

**Acceptance Criteria:**
- ✅ Add trend chart section to `VarianceAnalysisReport.tsx`
- ✅ Use React Query: `useQuery()` with `VarianceAnalysisReportService.getVarianceTrend()`
- ✅ Chart displays project-level trend (default)
- ✅ Chart section includes:
  - Heading: "Variance Trend Analysis"
  - Control date indicator
  - Chart component
  - Loading state: skeleton chart
  - Empty state: message if no trend data
- ✅ Chart positioned above or below main table (design decision)
- ✅ Chart responsive design
- ✅ Test passes verifying trend chart integration

**Expected Files Modified:**
- `frontend/src/components/Reports/VarianceAnalysisReport.tsx`

**Dependencies:**
- Step 18 (trend chart component)

**Estimated Effort:** 2 hours

---

### Phase 9: Frontend Route and Navigation

#### Step 20: Create Variance Analysis Report Route

**Description:** Create TanStack Router route for variance analysis report page.

**Test-First Requirement:**
- Write failing test that verifies:
  - Route renders `VarianceAnalysisReport` component
  - Route displays report header with project name and control date
  - Route integrates with project detail navigation

**Acceptance Criteria:**
- ✅ New route file: `frontend/src/routes/_layout/projects.$id.reports.variance-analysis.tsx`
- ✅ Route path: `/projects/:id/reports/variance-analysis`
- ✅ Route uses `VarianceAnalysisReport` component
- ✅ Route displays report header:
  - Project name
  - Report title: "Variance Analysis Report"
  - Control date (from time-machine)
  - Report generation timestamp (optional)
- ✅ Route integrates with project detail navigation
- ✅ Test passes verifying route renders correctly

**Expected Files Created:**
- `frontend/src/routes/_layout/projects.$id.reports.variance-analysis.tsx`

**Dependencies:**
- Step 14 (report component)

**Estimated Effort:** 1-2 hours

---

#### Step 21: Add Navigation Links

**Description:** Add navigation link to variance analysis report from project detail page.

**Test-First Requirement:**
- Write failing test that verifies:
  - Navigation link appears in project detail page
  - Clicking link navigates to variance analysis report page
  - Link is visible and accessible

**Acceptance Criteria:**
- ✅ Add "Variance Analysis" link in project detail page
  - Location: Reports section or navigation tabs
  - Link navigates to `/projects/{projectId}/reports/variance-analysis`
- ✅ Link styled consistently with other navigation elements
- ✅ Link accessible (keyboard navigation, screen readers)
- ✅ Test passes verifying navigation works

**Expected Files Modified:**
- `frontend/src/routes/_layout/projects.$id.tsx` (project detail page)

**Dependencies:**
- Step 20 (report route)

**Estimated Effort:** 1 hour

---

#### Step 22: Add Drill-Down Navigation

**Description:** Implement row click navigation from report to cost element detail page (as in E4-007).

**Test-First Requirement:**
- Write failing test that verifies:
  - Clicking a row navigates to cost element detail page
  - Navigation URL is correct: `/projects/{projectId}/wbes/{wbeId}/cost-elements/{costElementId}`
  - Navigation preserves time-machine control date (if applicable)

**Acceptance Criteria:**
- ✅ Configure `onRowClick` handler in DataTable
- ✅ Handler extracts `cost_element_id` and `wbe_id` from row data
- ✅ Handler navigates using TanStack Router:
  ```typescript
  navigate({
    to: "/projects/$id/wbes/$wbeId/cost-elements/$costElementId",
    params: { id: projectId, wbeId: row.wbe_id, costElementId: row.cost_element_id },
    search: (prev) => ({ ...prev, tab: "metrics" }),
  })
  ```
- ✅ Navigation preserves time-machine control date via search params (if needed)
- ✅ Test passes verifying drill-down navigation works

**Expected Files Modified:**
- `frontend/src/components/Reports/VarianceAnalysisReport.tsx`

**Dependencies:**
- Step 14 (report component)

**Estimated Effort:** 1 hour

---

### Phase 10: Variance Explanation Feature

#### Step 23: Create Variance Explanation Helper Function

**Description:** Create helper function that generates quick variance explanation text based on EVM metrics. Used in drill-down view.

**Test-First Requirement:**
- Write failing test that verifies:
  - Function generates explanation for negative CV (over-budget)
  - Function generates explanation for negative SV (behind-schedule)
  - Function generates explanation for positive variances (under-budget, ahead-of-schedule)
  - Function handles undefined percentages

**Acceptance Criteria:**
- ✅ Helper function: `generateVarianceExplanation(row: VarianceAnalysisReportRowPublic): string`
- ✅ Function generates human-readable explanation:
  - For CV: "Cost Variance: Over-budget by €X,XXX (X.XX% of budget)" or "Under-budget by €X,XXX"
  - For SV: "Schedule Variance: Behind-schedule by €X,XXX (X.XX% of budget)" or "Ahead-of-schedule by €X,XXX"
  - Includes CPI/SPI context if available: "CPI: X.XX indicates cost performance..."
  - Handles undefined percentages: "Cost Variance: Over-budget by €X,XXX (percentage unavailable)"
- ✅ Location: `frontend/src/utils/varianceExplanation.ts` or in component
- ✅ Test passes verifying explanation generation

**Expected Files Created:**
- `frontend/src/utils/varianceExplanation.ts` (optional, or inline in component)

**Dependencies:**
- Step 5 (report models)

**Estimated Effort:** 1-2 hours

---

#### Step 24: Add Variance Explanation to Cost Element Detail Page

**Description:** Add variance explanation section to cost element detail page. Display quick explanation when user drills down from variance analysis report.

**Test-First Requirement:**
- Write failing test that verifies:
  - Variance explanation section renders in cost element detail page
  - Explanation shows CV and SV breakdown
  - Explanation appears in "Metrics" tab or dedicated section
  - Explanation updates when metrics change

**Acceptance Criteria:**
- ✅ Add variance explanation section to cost element detail page
  - Location: "Metrics" tab or dedicated "Variance Analysis" section
  - Section header: "Variance Explanation"
- ✅ Section displays:
  - Quick explanation text (from `generateVarianceExplanation()`)
  - CV breakdown: CV, CV%, CPI context
  - SV breakdown: SV, SV%, SPI context
  - Visual indicators (color-coded severity badges)
- ✅ Section fetches EVM metrics using existing `EvmMetricsService`
- ✅ Section respects time-machine control date
- ✅ Section styled consistently with other detail page sections
- ✅ Test passes verifying variance explanation display

**Expected Files Modified:**
- `frontend/src/routes/_layout/projects.$id.wbes.$wbeId.cost-elements.$costElementId.tsx` (cost element detail page)
- Or: `frontend/src/components/Projects/EarnedValueSummary.tsx` (if adding to existing metrics component)

**Dependencies:**
- Step 23 (explanation helper), Step 22 (drill-down navigation)

**Estimated Effort:** 2-3 hours

---

### Phase 11: Summary and Polish

#### Step 25: Add Summary Section to Report Component

**Description:** Add summary section highlighting total variances and problem areas count.

**Test-First Requirement:**
- Write failing test that verifies:
  - Summary section renders with correct metrics
  - Summary shows total problem areas count
  - Summary shows aggregated CV and SV totals
  - Summary updates when filters change

**Acceptance Criteria:**
- ✅ Add summary section to `VarianceAnalysisReport.tsx`
  - Location: Above or below main table
- ✅ Summary displays:
  - Total problem areas count (from `report.total_problem_areas`)
  - Aggregated CV total (from `report.summary.cost_variance`)
  - Aggregated SV total (from `report.summary.schedule_variance`)
  - Config used: Thresholds used for severity calculation (optional)
- ✅ Summary styled as cards or grid (consistent with other reports)
- ✅ Summary updates when filters/sorting change (React Query refetch)
- ✅ Test passes verifying summary display

**Expected Files Modified:**
- `frontend/src/components/Reports/VarianceAnalysisReport.tsx`

**Dependencies:**
- Step 14 (report component)

**Estimated Effort:** 2 hours

---

#### Step 26: Add Responsive Design and Polish

**Description:** Ensure report component is responsive across mobile, tablet, and desktop. Add final UI polish and accessibility improvements.

**Test-First Requirement:**
- Write failing test that verifies:
  - Component renders correctly on mobile (< 768px)
  - Component renders correctly on tablet (768px - 1024px)
  - Component renders correctly on desktop (> 1024px)
  - All interactive elements are keyboard accessible

**Acceptance Criteria:**
- ✅ Responsive design:
  - Mobile: Stacked layout, horizontal scroll for table
  - Tablet: Adjusted column widths, readable text
  - Desktop: Full width table, optimal spacing
- ✅ Accessibility:
  - All interactive elements keyboard accessible
  - ARIA labels on filter/sort controls
  - Screen reader support for table data
  - Color contrast meets WCAG standards
- ✅ UI polish:
  - Consistent spacing and typography
  - Loading states are clear
  - Error states are informative
  - Empty states are helpful
- ✅ Test passes verifying responsive design and accessibility

**Expected Files Modified:**
- `frontend/src/components/Reports/VarianceAnalysisReport.tsx`
- `frontend/src/components/Reports/VarianceTrendChart.tsx`

**Dependencies:**
- Step 25 (summary section)

**Estimated Effort:** 2-3 hours

---

### Phase 12: Testing and Documentation

#### Step 27: Backend Integration Tests

**Description:** Write comprehensive backend integration tests for variance analysis report service and API endpoints.

**Test-First Requirement:**
- Write failing test that verifies:
  - Service function handles all edge cases
  - API endpoints return correct status codes
  - API endpoints handle errors gracefully
  - Authorization checks work correctly

**Acceptance Criteria:**
- ✅ Comprehensive test file: `backend/tests/api/routes/test_variance_analysis_report.py`
- ✅ Test coverage:
  - Report endpoint: Success cases, empty project, filtering, sorting
  - Trend endpoint: Success cases, different levels (project/WBE/cost element)
  - Error cases: Project not found, invalid parameters
  - Authorization: Non-authenticated users get 401
  - Time-machine: Control date filtering works correctly
- ✅ All tests passing: `pytest backend/tests/api/routes/test_variance_analysis_report.py -v`
- ✅ Test coverage > 80% for service and API routes

**Expected Files Modified:**
- `backend/tests/api/routes/test_variance_analysis_report.py` (expand from Step 11)

**Dependencies:**
- Step 11 (report endpoint), Step 12 (trend endpoint)

**Estimated Effort:** 3-4 hours

---

#### Step 28: Frontend Component Tests

**Description:** Write comprehensive frontend component tests for variance analysis report component.

**Test-First Requirement:**
- Write failing test that verifies:
  - Component renders correctly with data
  - Component handles loading state
  - Component handles empty state
  - Filtering and sorting work correctly
  - Navigation works correctly

**Acceptance Criteria:**
- ✅ Comprehensive test file: `frontend/src/components/Reports/__tests__/VarianceAnalysisReport.test.tsx`
- ✅ Test coverage:
  - Component rendering: With data, loading, empty states
  - Filtering: Toggle "show only problem areas" updates displayed rows
  - Sorting: Changing sort_by updates displayed rows
  - Navigation: Row click navigates correctly
  - Trend chart: Renders when data available
- ✅ All tests passing: `npm test -- VarianceAnalysisReport`
- ✅ Test coverage > 80% for component

**Expected Files Modified:**
- `frontend/src/components/Reports/__tests__/VarianceAnalysisReport.test.tsx` (expand from Step 14)

**Dependencies:**
- Step 14 (report component)

**Estimated Effort:** 3-4 hours

---

#### Step 29: Update Project Status Documentation

**Description:** Update project status document to mark E4-008 as complete.

**Test-First Requirement:**
- N/A (documentation step)

**Acceptance Criteria:**
- ✅ Update `docs/project_status.md`:
  - Mark E4-008 as ✅ Done
  - Add completion notes: Implementation complete with configuration table, filtering, sorting, trend analysis, and drill-down explanation
  - Update Sprint 5 status if applicable
- ✅ Documentation is clear and accurate

**Expected Files Modified:**
- `docs/project_status.md`

**Dependencies:**
- All implementation steps complete

**Estimated Effort:** 30 minutes

---

## PROCESS CHECKPOINTS

After completing the following steps, pause and ask:

1. **After Step 4 (Seed Default Configurations):**
   - "Configuration table and seeding complete. Should we continue with backend service implementation?"

2. **After Step 13 (OpenAPI Client Regeneration):**
   - "Backend API complete and client regenerated. Should we continue with frontend component implementation?"

3. **After Step 19 (Trend Chart Integration):**
   - "Core frontend features complete (report, filtering, sorting, trend chart). Should we continue with navigation and variance explanation?"

4. **After Step 26 (Responsive Design and Polish):**
   - "All features implemented. Should we continue with comprehensive testing and documentation?"

---

## SCOPE BOUNDARIES

**In Scope (Confirmed):**
- Configuration table for variance thresholds (admin-configurable percentages)
- Separate backend endpoint (Approach A)
- Variance percentage calculations (CV% = CV/BAC, SV% = SV/BAC, undefined if BAC = 0)
- Default: show only problem areas, sorted by most negative CV
- User filtering by CV and SV
- Trend analysis: monthly level, variance evolution over time
- Drill-down to cost element with quick variance explanation

**Out of Scope (Deferred):**
- Export functionality (E4-010)
- Advanced trend analysis (daily, weekly granularity)
- Root cause analysis beyond basic explanation
- Server-side pagination (not needed for typical project sizes)

**No Scope Creep:**
- Do not add export functionality (E4-010)
- Do not add daily/weekly trend analysis (keep monthly only)
- Do not add advanced root cause analysis (keep basic explanation only)
- Ask for confirmation before adding any additional features

---

## ROLLBACK STRATEGY

**If we need to abandon this approach:**

**Safe Rollback Points:**
1. **After Phase 1 (Configuration Table):** Configuration table can remain as it may be useful for other features. Rollback would involve removing API endpoints and frontend usage.
2. **After Phase 2-3 (Backend Services):** Backend services can remain even if frontend is not implemented. Rollback would involve removing API routes and frontend components.
3. **Before Frontend Implementation:** If backend is working but frontend approach needs change, backend remains intact.

**Alternative Approaches:**
- **If Configuration Table is too complex:** Use application-level configuration (settings.py) for thresholds, remove database table
- **If Trend Analysis is too complex:** Remove trend analysis from MVP, keep basic report only
- **If Variance Explanation is too complex:** Remove explanation feature, keep basic drill-down navigation

**Next Steps if Rollback:**
- Document what was implemented and why rollback occurred
- Identify alternative approach
- Create new analysis document if needed
- Proceed with alternative approach

---

## ESTIMATED TOTAL EFFORT

- **Phase 1 (Configuration Table):** 7-9 hours
- **Phase 2 (Backend Service and Models):** 9-12 hours
- **Phase 3 (Trend Analysis Backend):** 5-7 hours
- **Phase 4 (Backend API Routes):** 4-6 hours
- **Phase 5 (OpenAPI Client):** 15 minutes
- **Phase 6 (Frontend Basic):** 5-7 hours
- **Phase 7 (Frontend Filtering/Sorting):** 4-6 hours
- **Phase 8 (Frontend Trend):** 5-6 hours
- **Phase 9 (Frontend Route/Navigation):** 3-4 hours
- **Phase 10 (Variance Explanation):** 3-5 hours
- **Phase 11 (Summary/Polish):** 4-5 hours
- **Phase 12 (Testing/Documentation):** 6-9 hours

**Total Estimated Effort:** 55-72 hours

---

**Document Owner:** Development Team
**Review Status:** Ready for Implementation
**Next Review:** After stakeholder feedback or at process checkpoints
