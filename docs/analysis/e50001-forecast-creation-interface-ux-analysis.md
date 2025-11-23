# High-Level Analysis: E5-001 Forecast Creation Interface - User Stories and UI/UX

**Task:** E5-001 (Forecast Creation Interface)
**Status:** Analysis Phase - User Stories and UI/UX Definition
**Date:** 2025-11-22
**Analysis Code:** E50001

---

## Objective

Define detailed user stories and user interface experience for E5-001 (Forecast Creation Interface), enabling project managers to create and update estimates at completion (EAC) with assumptions and rationale at the cost element level, supporting complete forecast lifecycle management with version history tracking.

---

## User Story

### Primary User Story

**As a** project manager
**I want to** create and update cost forecasts (EAC) for cost elements with full version history and assumptions
**So that** I can track forecast evolution over time, document the rationale behind each forecast, compare forecasts across baseline snapshots, and support decision-making with transparent forecast management.

### Secondary User Stories

**As a** project controller
**I want to** view all forecast history for a cost element with clear indication of the current forecast
**So that** I can analyze forecast accuracy trends and prepare variance reports.

**As a** department manager
**I want to** create forecasts with documented assumptions and forecast type classification
**So that** I can provide transparent justification for my estimates at completion.

**As an** executive
**I want to** see current forecasts aggregated at project and WBE levels
**So that** I can assess overall project financial health and forecast at completion.

**As a** cost estimating manager
**I want to** detect deviations from planned to forecasts at cost element and WBE levels
**So that** I can adapt planned costs in pricelists immediately according to variations.

---

## Detailed User Interface Experience

### 1. Forecast Tab in Cost Element Detail Page

**Location:** Cost Element Detail Page (`/projects/:id/wbes/:wbeId/cost-elements/:costElementId`)

**Experience Flow:**

1. **Navigation:** User navigates to cost element detail page via row click from Cost Elements table
2. **Tab Selection:** User sees tabbed interface with existing tabs: Info, Cost Registrations, Schedule, Earned Value, Metrics, Timeline, AI Assessment
3. **New Tab:** "Forecasts" tab added between "Earned Value" and "Metrics" tabs
4. **Tab Content:** Upon selecting "Forecasts" tab, user sees:
   - Forecasts table showing all forecast history for the cost element
   - "Add Forecast" button in table header (right-aligned)
   - Table displays: Forecast Date, EAC (Estimate at Completion), Forecast Type, Estimator, Current Indicator, Assumptions (truncated), Actions (Edit/Delete)
   - Current forecast highlighted with visual indicator (badge/chip)
   - Table sorted by forecast_date descending (newest first) by default
   - Optional sorting by EAC, Forecast Type, or Estimator

**Visual Design:**
- Follows Chakra UI design system consistent with existing tabs
- Table uses DataTable component (matches CostRegistrationsTable, EarnedValueEntriesTable pattern)
- Current forecast badge: "Current" badge in green/chakra color scheme
- Empty state: "No forecasts created yet. Click 'Add Forecast' to create your first forecast."
- Responsive design: Table scrolls horizontally on mobile, maintains column visibility toggle

### 2. Add Forecast Dialog

**Trigger:** Click "Add Forecast" button in Forecasts tab

**Dialog Experience:**

1. **Dialog Opens:** Modal dialog appears (size: `lg` - matches AddEarnedValueEntry pattern)
2. **Form Fields (in order):**
   - **Forecast Date** (required, date picker)
     - Default: Today's date
     - Validation: Cannot be in the past (alert shown, not blocked) - matches cost registration pattern
     - Help text: "Date when this forecast was created"

   - **Estimate at Completion (EAC)** (required, number input, currency format)
     - Default: Current cost element's budget BAC (if available)
     - Validation: Must be > 0
     - Display: Formatted as currency (e.g., €100,000.00)
     - Help text: "Expected total cost at project completion for this cost element"
     - Real-time preview: Shows calculated ETC (Estimate to Complete) = EAC - AC, if AC available

   - **Forecast Type** (required, select dropdown)
     - Options: "Bottom-up", "Performance-based", "Management Judgment"
     - Default: "Bottom-up"
     - Help text: "Methodology used to derive this forecast"

   - **Mark as Current** (checkbox)
     - Default: Checked (true)
     - Help text: "This forecast will become the active forecast for EVM calculations. Previous current forecast will be automatically updated."
     - Warning shown if other current forecast exists: "Marking this as current will replace the existing current forecast dated [date]."

   - **Assumptions** (optional, textarea)
     - Placeholder: "Document the assumptions, risks, and rationale underlying this forecast..."
     - Character limit: 5000 characters (with counter)
     - Help text: "Optional: Explain the reasoning behind this forecast value"

   - **Estimator** (auto-filled, read-only display)
     - Shows: Current user's name (from session)
     - Help text: "Forecast creator (auto-filled from your account)"

3. **Form Validation:**
   - Real-time validation on blur (matches existing patterns)
   - Error messages displayed inline below fields
   - Submit button disabled until all required fields valid
   - EAC validation: Must be positive number, currency format

4. **Submission:**
   - Click "Create Forecast" button (primary button, bottom right)
   - Loading state: Button shows spinner, form disabled during submission
   - Success: Dialog closes, success toast: "Forecast created successfully"
   - Error: Error toast with detailed message, form remains open
   - Query invalidation: Forecasts table refreshes, EVM metrics refresh (if current forecast changed)

### 3. Edit Forecast Dialog

**Trigger:** Click "Edit" action button in Forecasts table row

**Dialog Experience:**

1. **Dialog Opens:** Modal dialog pre-populated with existing forecast data
2. **Form Fields:** Same as Add Forecast, but:
   - All fields pre-filled with current values
   - "Mark as Current" checkbox shows current state
   - If forecast is current: Warning badge "This is the current forecast"
   - Form title: "Edit Forecast" (vs "Add Forecast")
3. **Validation:** Same as Add Forecast
4. **Submission:**
   - Click "Update Forecast" button
   - Success toast: "Forecast updated successfully"
   - Versioning behavior: If updating `is_current` flag, automatically updates other forecasts
   - Query invalidation: Table refreshes, metrics refresh if current changed

### 4. Delete Forecast Dialog

**Trigger:** Click "Delete" action button in Forecasts table row

**Confirmation Dialog:**

1. **Warning Dialog Opens:** Confirmation modal (size: `md`)
2. **Content:**
   - Title: "Delete Forecast?"
   - Message: "Are you sure you want to delete the forecast dated [forecast_date] with EAC [eac]?"
   - Special case: If deleting current forecast:
     - Additional warning: "This is the current forecast. Deleting it will leave no current forecast active for this cost element."
     - Suggestion: "Consider editing instead, or create a new forecast first."
3. **Actions:**
   - "Cancel" button (secondary, left)
   - "Delete Forecast" button (destructive/red, right)
4. **Submission:**
   - Success toast: "Forecast deleted successfully"
   - Query invalidation: Table refreshes, metrics refresh if current was deleted

### 5. Forecast History View

**Table Display (Forecasts Tab):**

Columns:
1. **Forecast Date** (sortable)
   - Format: "YYYY-MM-DD" (e.g., "2025-11-22")
   - Display: Date only

2. **EAC** (sortable)
   - Format: Currency (e.g., "€100,000.00")
   - Alignment: Right-aligned
   - Color coding:
     - Green if EAC < BAC (under budget)
     - Yellow if EAC ≈ BAC (±5%)
     - Red if EAC > BAC (over budget)

3. **ETC** (calculated, read-only)
   - Format: Currency
   - Formula: EAC - AC (Actual Cost)
   - Shows "N/A" if AC not available
   - Alignment: Right-aligned

4. **Forecast Type** (sortable)
   - Display: Badge/chip with type name
   - Colors:
     - Bottom-up: Blue
     - Performance-based: Purple
     - Management Judgment: Orange

5. **Current** (indicator)
   - Display: "Current" badge (green) if `is_current=True`
   - Empty cell if `is_current=False`

6. **Estimator** (sortable)
   - Display: User's full name
   - Tooltip: User email on hover

7. **Assumptions** (truncated)
   - Display: First 100 characters + "..." if longer
   - Tooltip: Full assumptions text on hover
   - Click: Could expand in-place or open detail view (future enhancement)

8. **Actions**
   - Edit button on only the current forecast (icon button)
   - Delete button (icon button, destructive)
   - Actions disabled for forecasts older than X days? (TBD - clarify requirement)

**Table Features:**
- Column visibility toggle (matches DataTable pattern)
- Single-column sorting (click column header)
- Client-side filtering (text input for date/EAC/type/search)
- Pagination (if > 20 forecasts)
- Row hover highlight

### 6. Current Forecast Indicator in Other Views

**EVM Summary Cards:**
- Current forecast EAC displayed in EarnedValueSummary component
- Badge/label: "Current EAC" with value
- Tooltip: "Latest forecast dated [date]"

**Baseline Snapshots:**
- Forecast EAC shown in baseline snapshot views (already implemented)
- Label: "Forecast EAC at Baseline" to distinguish from current forecast

**Timeline Views:**
- Future enhancement: Show forecast EAC trend over time (separate line in timeline)
- Not in scope for E5-001, but architecture should support

### 7. Mobile/Responsive Experience

**Mobile Optimization:**
- Table: Horizontal scroll with sticky first column (Forecast Date)
- Dialogs: Full-width on mobile, max-width on desktop
- Form fields: Stack vertically, full-width on mobile
- Buttons: Full-width on mobile, auto-width on desktop
- Actions column: Dropdown menu instead of icon buttons on mobile

---

## CODEBASE PATTERN ANALYSIS

### 1. Existing Implementation Patterns

**Pattern 1: Earned Value Entries (E3-006) - Primary Reference**
**Location:**
- Backend: `backend/app/api/routes/earned_value_entries.py`
- Frontend: `frontend/src/components/Projects/EarnedValueEntriesTable.tsx`
- Add Dialog: `frontend/src/components/Projects/AddEarnedValueEntry.tsx`
- Edit Dialog: `frontend/src/components/Projects/EditEarnedValueEntry.tsx`

**Pattern Characteristics:**
- Cost-element-scoped CRUD API
- Query parameter pattern: `?cost_element_id={id}`
- Validation functions: `validate_cost_element_exists()`, duplicate date protection
- Tabbed interface integration in cost element detail page
- DataTable component with Add/Edit/Delete actions
- React Hook Form for form management
- TanStack Query for data fetching and mutations
- Chakra UI Dialog components
- Form validation with error display
- Success/error toast notifications

**Reusable Components:**
- `DataTable` component (TanStack Table v8 wrapper)
- `useCustomToast()` hook for notifications
- `useRevenuePlanValidation()` pattern (can adapt for EAC validation)
- `useRegistrationDateValidation()` pattern (can adapt for forecast date validation)
- Dialog pattern from Add/Edit components

**Pattern 2: Cost Element Schedules (E2-003)**
**Location:**
- Backend: `backend/app/api/routes/cost_element_schedules.py`
- Frontend: `frontend/src/components/Projects/CostElementSchedulesTable.tsx`
- Add/Edit: `frontend/src/components/Projects/AddCostElementSchedule.tsx`, `EditCostElementSchedule.tsx`

**Pattern Characteristics:**
- Versioned records (schedule registrations)
- Full history table view
- Registration date tracking
- Description field for change rationale
- Tabbed interface in cost element detail page

**Reusable Elements:**
- History table pattern with version tracking
- Description field pattern for change documentation
- Registration date pattern (similar to forecast_date)

**Pattern 3: Cost Registrations (E3-001)**
**Location:**
- Backend: `backend/app/api/routes/cost_registrations.py`
- Frontend: `frontend/src/components/Projects/CostRegistrationsTable.tsx`
- Add/Edit: `frontend/src/components/Projects/AddCostRegistration.tsx`, `EditCostRegistration.tsx`

**Pattern Characteristics:**
- Date validation with schedule boundary checking (alerts, not blocks)
- Cost category dropdown (hardcoded endpoint pattern)
- Currency formatting
- Date picker with default values

**Reusable Elements:**
- Date validation hook pattern
- Currency formatting utilities
- Dropdown with hardcoded options pattern

### 2. Established Architectural Layers

**Backend Layers:**
- **Routes Layer:** `backend/app/api/routes/` - API endpoints
- **Models Layer:** `backend/app/models/` - SQLModel definitions with Base/Create/Update/Public schemas
- **Services Layer:** (Not consistently used, but exists for complex logic like EVM calculations)
- **Validation Layer:** Helper functions in route files (e.g., `validate_cost_element_exists()`)

**Frontend Layers:**
- **Routes Layer:** `frontend/src/routes/` - TanStack Router file-based routing
- **Components Layer:** `frontend/src/components/Projects/` - Feature-specific components
- **Client Layer:** `frontend/src/client/` - Auto-generated OpenAPI client
- **Context Layer:** `frontend/src/context/` - React context providers (TimeMachineContext, etc.)
- **Hooks Layer:** `frontend/src/hooks/` - Custom React hooks (validation hooks)

**Key Patterns:**
- Backend: FastAPI with SQLModel ORM, Pydantic validation
- Frontend: React with TypeScript, TanStack Query, React Hook Form, Chakra UI
- API Client: Auto-generated from OpenAPI spec
- Testing: Pytest (backend), Vitest/Playwright (frontend)

### 3. Integration Touchpoint Mapping

**Backend Integration Points:**

1. **Forecast Routes** (`backend/app/api/routes/forecasts.py` - NEW)
   - Pattern: Follow `earned_value_entries.py` structure
   - Endpoints:
     - `GET /forecasts/?cost_element_id={id}` - List forecasts
     - `POST /forecasts/` - Create forecast
     - `PUT /forecasts/{id}` - Update forecast
     - `DELETE /forecasts/{id}` - Delete forecast
   - Dependencies:
     - `Forecast` model (exists)
     - `CostElement` model (for validation)
     - `User` model (for estimator_id)

2. **Router Registration** (`backend/app/api/main.py`)
   - Add: `app.include_router(forecasts.router, prefix="/forecasts", tags=["forecasts"])`

3. **Versioning Logic** (NEW helper function)
   - Location: `backend/app/api/routes/forecasts.py`
   - Function: `ensure_single_current_forecast(session, cost_element_id, exclude_id=None)`
   - Called: In create/update endpoints when `is_current=True`
   - Pattern: Similar to `ensure_unique_completion_date()` in earned_value_entries.py

4. **Baseline Integration** (`backend/app/api/routes/baseline_logs.py`)
   - Status: ✅ Already queries for `is_current=True` forecasts
   - Impact: None - forecast CRUD won't affect baseline snapshotting logic
   - Test: Verify baseline creation still works after forecast CRUD implementation

**Frontend Integration Points:**

1. **Cost Element Detail Route** (`frontend/src/routes/_layout/projects.$id.wbes.$wbeId.cost-elements.$costElementId.tsx`)
   - Add: "forecasts" to `COST_ELEMENT_VIEW_OPTIONS` array
   - Add: `<Tabs.Trigger value="forecasts">Forecasts</Tabs.Trigger>`
   - Add: `<Tabs.Content value="forecasts">` with `<ForecastsTable />`

2. **New Components** (`frontend/src/components/Projects/`)
   - `ForecastsTable.tsx` - Main table component
   - `AddForecast.tsx` - Add dialog component
   - `EditForecast.tsx` - Edit dialog component
   - Pattern: Mirror EarnedValueEntriesTable structure

3. **Client Generation**
   - Regenerate OpenAPI client after backend implementation
   - New services: `ForecastsService.readForecasts()`, `createForecast()`, `updateForecast()`, `deleteForecast()`

4. **EVM Summary Integration** (`frontend/src/components/Projects/EarnedValueSummary.tsx`)
   - Future enhancement: Display current forecast EAC in summary cards
   - Not in scope for E5-001, but architecture should support

5. **Time Machine Integration**
   - Forecast queries should respect `control_date` from TimeMachineContext
   - Filter: Only show forecasts where `forecast_date <= control_date`
   - Impact: Forecasts table, EVM calculations using forecast EAC

### 4. Configuration Patterns

**Forecast Type Enum:**
- Current: STRING field in model (flexible)
- Options: Hardcoded in frontend dropdown ("Bottom-up", "Performance-based", "Management Judgment")
- Validation: Backend validates against enum values (application-level, not database enum)
- Pattern: Similar to cost categories (hardcoded endpoint) or progression types (hardcoded in frontend)

**User Session:**
- Current user: Accessed via `current_user: CurrentUser` dependency in backend
- Estimator: Auto-filled from session in frontend (read-only display)
- Pattern: Matches `created_by_id` pattern in other entries

---

## ABSTRACTION INVENTORY

### Backend Abstractions

1. **Validation Functions:**
   - `validate_cost_element_exists(session, cost_element_id)` - Reusable, exists in earned_value_entries.py
   - `ensure_unique_completion_date()` - Pattern can be adapted for `is_current` uniqueness
   - `validate_percent_complete()` - Pattern for EAC validation (> 0)

2. **Model Patterns:**
   - Base/Create/Update/Public schema pattern (Forecast model already follows)
   - UUID primary keys
   - Timestamps (created_at, last_modified_at)
   - Foreign key relationships with proper constraints

3. **Query Patterns:**
   - Cost-element-scoped queries: `?cost_element_id={id}`
   - Filtering by boolean flags: `where(Forecast.is_current.is_(True))`
   - Ordering: `.order_by(Forecast.forecast_date.desc())`

### Frontend Abstractions

1. **Form Management:**
   - `useForm()` from React Hook Form
   - `useCustomToast()` hook for notifications
   - `useQueryClient()` for query invalidation
   - Form validation patterns (onBlur mode, error display)

2. **Data Table:**
   - `DataTable` component (TanStack Table v8 wrapper)
   - Column definitions pattern
   - Action buttons pattern
   - Pagination/sorting/filtering

3. **Dialog Components:**
   - Chakra UI `DialogRoot` pattern
   - Form submission with mutation pattern
   - Loading states pattern

4. **Validation Hooks:**
   - `useRevenuePlanValidation()` - Can adapt pattern for EAC validation
   - `useRegistrationDateValidation()` - Can adapt for forecast date validation
   - Custom hooks for real-time validation

5. **Query Patterns:**
   - `useQuery()` for data fetching
   - `useMutation()` for create/update/delete
   - Query key patterns: `["forecasts", costElementId, controlDate]`
   - Query invalidation patterns

---

## ALTERNATIVE APPROACHES

### Approach 1: Full CRUD with Versioning Logic (RECOMMENDED)

**Description:**
Implement complete CRUD API with automatic versioning management. When a forecast is created/updated with `is_current=True`, automatically set all other forecasts for that cost element to `is_current=False` in an atomic transaction.

**Implementation:**
- Backend: Full CRUD API (`GET/POST/PUT/DELETE /forecasts/`)
- Backend: Versioning helper function ensuring single current forecast
- Frontend: ForecastsTable with Add/Edit/Delete dialogs
- Frontend: Tab integration in cost element detail page
- Frontend: Form validation with React Hook Form
- Frontend: Real-time validation for EAC against budget

**Pros:**
- ✅ Complete feature implementation matching PRD requirements
- ✅ Follows established patterns (EarnedValueEntries, CostRegistrations)
- ✅ Automatic versioning prevents data integrity issues
- ✅ Full user control over forecast lifecycle
- ✅ Consistent with codebase architecture
- ✅ Enables proper audit trail and history tracking
- ✅ Supports baseline integration (already queries `is_current=True`)

**Cons:**
- ⚠️ Requires implementing both backend and frontend (larger scope)
- ⚠️ Versioning logic needs careful implementation to prevent race conditions
- ⚠️ More complex than minimal approach

**Alignment:** Perfect alignment with existing architecture

**Estimated Complexity:**
- Backend: 8-12 hours (CRUD API + versioning logic + tests)
- Frontend: 6-8 hours (components + integration + tests)
- Total: 14-20 hours

**Risk Factors:**
- Low risk - well-established patterns
- Versioning logic needs transaction safety (use database transaction)
- Concurrent forecast creation with `is_current=True` requires proper locking

### Approach 2: Minimal API + Manual Versioning (NOT RECOMMENDED)

**Description:**
Implement only POST endpoint for creating forecasts. Users manually manage `is_current` flag via updates. No automatic versioning logic.

**Implementation:**
- Backend: Only POST endpoint
- Backend: No versioning logic (users handle manually)
- Frontend: Basic Add dialog only
- Frontend: Edit/Delete via direct API calls or minimal UI

**Pros:**
- ✅ Minimal implementation effort
- ✅ Maximum user flexibility

**Cons:**
- ❌ Violates PRD requirement for forecast creation interface (Section 7.1)
- ❌ Inconsistent with other operational records (EarnedValueEntries, CostRegistrations)
- ❌ High risk of data integrity issues (multiple `is_current=True` forecasts)
- ❌ Poor user experience (manual versioning management)
- ❌ No proper audit trail
- ❌ Doesn't match codebase patterns

**Alignment:** Poor - violates established patterns and PRD requirements

**Estimated Complexity:** 4-6 hours (minimal value, high risk)

**Risk Factors:**
- High risk - violates user requirements and data integrity

### Approach 3: Forecast Wizard with Multi-Step Form (FUTURE ENHANCEMENT)

**Description:**
Implement forecast creation as a multi-step wizard guiding users through forecast type selection, EAC entry, assumptions documentation, and review/confirmation.

**Implementation:**
- Backend: Same as Approach 1
- Frontend: Wizard component with multiple steps
- Frontend: Step 1: Forecast type and date
- Frontend: Step 2: EAC entry with context (BAC, AC, EV)
- Frontend: Step 3: Assumptions documentation
- Frontend: Step 4: Review and confirm

**Pros:**
- ✅ Enhanced user experience for complex forecasts
- ✅ Guided process reduces errors
- ✅ Contextual information at each step
- ✅ Better documentation of assumptions

**Cons:**
- ⚠️ More complex implementation
- ⚠️ Overkill for simple forecasts
- ⚠️ Not aligned with current simple dialog patterns
- ⚠️ Adds unnecessary complexity for MVP

**Alignment:** Future enhancement - not aligned with current MVP scope

**Estimated Complexity:** 12-16 hours frontend (complex wizard logic)

**Risk Factors:**
- Medium risk - complexity without clear value for MVP

---

## ARCHITECTURAL IMPACT ASSESSMENT

### Architectural Principles

**Principles Followed:**
- ✅ **Single Responsibility:** Forecast routes handle only forecast CRUD, versioning logic is isolated in helper function
- ✅ **DRY (Don't Repeat Yourself):** Reuses existing patterns (EarnedValueEntries, CostRegistrations)
- ✅ **Consistency:** Follows established codebase patterns for CRUD operations
- ✅ **Separation of Concerns:** Backend handles business logic, frontend handles presentation
- ✅ **Testability:** CRUD operations are easily testable following existing test patterns

**Principles to Consider:**
- ⚠️ **Transaction Safety:** Versioning logic must be atomic to prevent race conditions
- ⚠️ **Data Integrity:** Enforce single current forecast constraint at database level (application-level currently)

### Maintenance Burden

**Low Maintenance Areas:**
- ✅ Standard CRUD operations follow well-established patterns
- ✅ Frontend components mirror existing components (easy to maintain)
- ✅ API client auto-generated (no manual maintenance)

**Potential Maintenance Areas:**
- ⚠️ **Versioning Logic:** If business rules change for versioning (e.g., allow multiple current forecasts), logic needs update
- ⚠️ **Forecast Type Enum:** If new forecast types added, update in both frontend and backend validation
- ⚠️ **EAC Validation Rules:** If validation rules change (e.g., allow negative EAC), update validation logic
- ⚠️ **ETC Calculation:** If ETC calculation formula changes, update in frontend (currently EAC - AC)

**Mitigation:**
- Versioning logic isolated in helper function (easy to modify)
- Forecast type enum can be moved to shared constants file
- Validation rules documented and centralized

### Testing Challenges

**Backend Testing:**
- ✅ Standard CRUD tests follow existing patterns
- ✅ Versioning logic tests need careful setup (multiple forecasts per cost element)
- ⚠️ Race condition testing (concurrent forecast creation) may require test utilities
- ✅ Baseline integration tests (verify baseline snapshots still work)

**Frontend Testing:**
- ✅ Component tests follow existing patterns (AddEarnedValueEntry, EditEarnedValueEntry)
- ✅ Form validation tests (React Hook Form patterns)
- ✅ Integration tests (Forecasts tab in cost element detail page)
- ⚠️ E2E tests (Playwright) for full forecast workflow

**Test Coverage Targets:**
- Backend: 90%+ coverage (follow existing test patterns)
- Frontend: Component tests for all dialogs, integration tests for tab
- E2E: Critical user flows (create/edit/delete forecast, versioning behavior)

---

## Ambiguities and Missing Information - RESOLVED

1. **Forecast Type Validation:**
   - ✅ **RESOLVED:** `forecast_type` shall be strict enum (Python Enum class)
   - **Implementation:** Create `ForecastType` enum with values: `bottom_up`, `performance_based`, `management_judgment`
   - **Validation:** Backend validates against enum values, frontend uses enum for dropdown

2. **ETC Field Storage:**
   - ✅ **RESOLVED:** ETC shall be calculated (EAC - AC), not stored
   - **Implementation:** Calculate in frontend for display, show in table and dialogs
   - **Display:** Show ETC in forecasts table and Add/Edit dialogs as read-only calculated field

3. **Forecast History Ordering:**
   - ✅ **RESOLVED:** Forecast history shall be ordered by forecast_date descending
   - **Implementation:** Backend query orders by `forecast_date DESC`, frontend table uses same ordering

4. **Forecast Deletion Behavior:**
   - ✅ **RESOLVED:** System shall auto-promote previous forecast when deleting current forecast
   - **Implementation:** On delete, if deleted forecast was current, find previous forecast (by forecast_date) and set `is_current=True`
   - **Logic:** Query forecasts ordered by forecast_date DESC, find first non-deleted forecast, set as current

5. **Forecast Date Validation:**
   - ✅ **RESOLVED:** Forecast date shall be in the past, but alert if future (not blocked)
   - **Implementation:** Backend validates `forecast_date <= today()`, frontend shows alert if future date selected
   - **Pattern:** Matches cost registration date validation pattern (alert, not block)

6. **EAC Validation Rules:**
   - ✅ **RESOLVED:** EAC allows any positive value (no hard validation), show warnings if EAC > BAC or EAC < AC
   - **Implementation:** Backend validates EAC > 0, frontend shows warning badges/alerts if EAC > BAC or EAC < AC
   - **Display:** Color-coded warnings in table and dialogs

7. **Forecast Type Options:**
   - ✅ **RESOLVED:** Three forecast types are final for MVP: `bottom_up`, `performance_based`, `management_judgment`
   - **Implementation:** Strict enum with these three values, extensible for future additions

8. **Maximum Forecast Dates:**
   - ✅ **RESOLVED:** System shall enforce maximum of three forecast dates per cost element
   - **Implementation:** Backend validation checks count of unique forecast_date values per cost_element_id before allowing new forecast
   - **Error:** Return 400 error if attempting to create fourth unique forecast_date

---

## Risks and Unknown Factors

1. **Versioning Race Conditions:**
   - **Risk:** Concurrent forecast creation with `is_current=True` could result in multiple current forecasts
   - **Mitigation:** Use database transaction with proper locking in versioning helper function
   - **Testing:** Add concurrent test scenarios

2. **Baseline Snapshot Timing:**
   - **Risk:** If forecast updated between baseline creation and snapshot, which version captured?
   - **Status:** ✅ Already handled - baseline queries `is_current=True` at snapshot time
   - **Testing:** Verify baseline creation still works after forecast CRUD

3. **Forecast Type Extensibility:**
   - **Risk:** If new forecast types added, need updates in multiple places
   - **Mitigation:** Use shared constants/enum file, validate in backend

4. **EVM Calculation Integration:**
   - **Risk:** Forecast EAC may be used in future EVM calculations (EAC-based metrics)
   - **Status:** Not in scope for E5-001, but architecture should support
   - **Mitigation:** Ensure forecast queries respect control_date (time machine)

5. **Performance with Many Forecasts:**
   - **Risk:** If cost element has many forecasts (>100), table performance may degrade
   - **Mitigation:** Implement pagination, limit default query results
   - **Testing:** Load test with large forecast history

6. **User Permission Checks:**
   - **Risk:** Should all users be able to create/update forecasts?
   - **Status:** Current pattern uses `_current_user` dependency (authenticated users)
   - **Mitigation:** Follow existing permission patterns, add role-based checks if needed

7. **Forecast Export:**
   - **Risk:** Users may want to export forecast history
   - **Status:** Not in scope for E5-001 (E4-010 covers report export)
   - **Mitigation:** Architecture supports export via existing report export patterns

---

## Summary

### Feature Description

E5-001 (Forecast Creation Interface) enables project managers to create, update, and delete cost forecasts (EAC) for cost elements with full version history tracking. The feature provides a complete CRUD interface following established codebase patterns, with automatic versioning management ensuring a single current forecast per cost element.

### Key Deliverables

1. **Backend:** Forecast CRUD API with versioning logic (8-12 hours)
2. **Frontend:** ForecastsTable component with Add/Edit/Delete dialogs (6-8 hours)
3. **Integration:** Forecasts tab in cost element detail page (1-2 hours)
4. **Testing:** Comprehensive test coverage (4-6 hours)
5. **Total Estimate:** 14-20 hours

### Recommended Approach

**Approach 1: Full CRUD with Versioning Logic** is the recommended approach, providing complete feature implementation matching PRD requirements while following established codebase patterns.

### Next Steps

1. ✅ High-level analysis complete (this document)
2. ⏳ **Await stakeholder feedback** on ambiguities
3. ⏳ Create detailed implementation plan following TDD discipline
4. ⏳ Implement backend CRUD API with versioning logic
5. ⏳ Implement frontend UI components
6. ⏳ Integrate into cost element detail page
7. ⏳ Regenerate OpenAPI client
8. ⏳ Comprehensive testing and validation

---

**Analysis Complete - Ready for Detailed Planning Phase**
