# E5-001 Forecast Creation Interface - Detailed Implementation Plan

## Overview
- **Approach:** Full CRUD with automatic versioning logic (Approach 1 from analysis)
- **Key Constraints:**
  - Forecast type as strict enum (bottom_up, performance_based, management_judgment)
  - ETC calculated as EAC - AC (display-only, not stored)
  - History ordered by forecast_date descending
  - Auto-promote previous forecast when deleting current forecast
  - Forecast date must be in past (alert if future, not blocked)
  - EAC allows any positive value (warnings if EAC > BAC or EAC < AC)
  - Maximum three forecast dates per cost element
  - Only current forecast can be edited
- **Standards:** TDD with failing tests first, ≤100 LOC / ≤5 files per commit target, reuse existing abstractions, no duplication

---

## 1. Implementation Steps

### Step 1: Backend ForecastType Enum and Model Updates

**Acceptance Criteria:**
- `ForecastType` enum created with values: `bottom_up`, `performance_based`, `management_judgment`
- `ForecastBase` model updated to use `ForecastType` enum instead of string
- Model validation tests pass for enum values
- Invalid enum values raise validation errors

**Test-First Requirement:**
- Create/update `backend/tests/models/test_forecast.py` with tests for enum validation
- Tests should fail before enum implementation

**Expected Files:**
- `backend/app/models/forecast.py` (add ForecastType enum, update ForecastBase)
- `backend/tests/models/test_forecast.py` (enum validation tests)

**Dependencies:** None

---

### Step 2: Backend Validation Helper Functions

**Acceptance Criteria:**
- Helper function `validate_cost_element_exists()` (reuse from earned_value_entries.py)
- Helper function `validate_forecast_date()` - ensures date is in past, returns warning dict if future
- Helper function `validate_forecast_type()` - validates against ForecastType enum
- Helper function `validate_eac()` - ensures EAC > 0
- Helper function `validate_max_forecast_dates()` - ensures max 3 unique forecast_date values per cost_element_id
- Helper function `ensure_single_current_forecast()` - sets all other forecasts to `is_current=False` when creating/updating with `is_current=True`
- Helper function `get_previous_forecast_for_promotion()` - finds previous forecast by forecast_date for auto-promotion on delete
- All helper functions have unit tests that pass

**Test-First Requirement:**
- Create `backend/tests/api/routes/test_forecast_helpers.py` with failing tests for all helper functions
- Tests should fail before helper implementation

**Expected Files:**
- `backend/app/api/routes/forecasts.py` (helper functions section)
- `backend/tests/api/routes/test_forecast_helpers.py` (new test file)

**Dependencies:** Step 1 complete

---

### Step 3: Backend Forecast CRUD API - List and Read Endpoints

**Acceptance Criteria:**
- `GET /forecasts/?cost_element_id={id}` endpoint returns list of forecasts for cost element
- `GET /forecasts/{id}` endpoint returns single forecast by ID
- List endpoint orders by `forecast_date DESC` (newest first)
- List endpoint filters by `cost_element_id` query parameter
- List endpoint respects time machine control_date (only forecasts where `forecast_date <= control_date`)
- Responses use `ForecastPublic` schema
- 404 errors for non-existent forecasts
- All tests pass

**Test-First Requirement:**
- Create `backend/tests/api/routes/test_forecasts.py` with failing tests for list and read endpoints
- Tests should fail before endpoint implementation

**Expected Files:**
- `backend/app/api/routes/forecasts.py` (list and read endpoints)
- `backend/tests/api/routes/test_forecasts.py` (list and read tests)
- `backend/app/api/main.py` (router registration)

**Dependencies:** Step 2 complete

---

### Step 4: Backend Forecast CRUD API - Create Endpoint

**Acceptance Criteria:**
- `POST /forecasts/` endpoint creates new forecast
- Validates cost_element_id exists
- Validates forecast_date is in past (returns warning if future, not blocked)
- Validates forecast_type against enum
- Validates EAC > 0
- Validates max 3 forecast dates per cost element (raises 400 if exceeded)
- Auto-sets `is_current=False` for all other forecasts if `is_current=True` in request
- Sets `estimator_id` from current_user
- Returns `ForecastPublic` with warning if forecast_date is future
- All tests pass

**Test-First Requirement:**
- Add failing tests for create endpoint in `backend/tests/api/routes/test_forecasts.py`
- Tests should fail before endpoint implementation

**Expected Files:**
- `backend/app/api/routes/forecasts.py` (create endpoint)
- `backend/tests/api/routes/test_forecasts.py` (create tests)

**Dependencies:** Step 3 complete

---

### Step 5: Backend Forecast CRUD API - Update Endpoint

**Acceptance Criteria:**
- `PUT /forecasts/{id}` endpoint updates existing forecast
- Only allows updating current forecast (`is_current=True`)
- Returns 400 error if attempting to update non-current forecast
- Validates all fields same as create endpoint
- Auto-sets `is_current=False` for all other forecasts if `is_current=True` in update
- Updates `last_modified_at` timestamp
- Returns `ForecastPublic` with warning if forecast_date is future
- All tests pass

**Test-First Requirement:**
- Add failing tests for update endpoint in `backend/tests/api/routes/test_forecasts.py`
- Tests should fail before endpoint implementation

**Expected Files:**
- `backend/app/api/routes/forecasts.py` (update endpoint)
- `backend/tests/api/routes/test_forecasts.py` (update tests)

**Dependencies:** Step 4 complete

---

### Step 6: Backend Forecast CRUD API - Delete Endpoint with Auto-Promotion

**Acceptance Criteria:**
- `DELETE /forecasts/{id}` endpoint deletes forecast
- If deleted forecast was current (`is_current=True`), automatically promotes previous forecast (by forecast_date DESC) to current
- If no previous forecast exists, no current forecast remains (acceptable state)
- Returns 200 with success message
- All tests pass including auto-promotion scenarios

**Test-First Requirement:**
- Add failing tests for delete endpoint in `backend/tests/api/routes/test_forecasts.py`
- Tests should fail before endpoint implementation
- Include tests for auto-promotion logic

**Expected Files:**
- `backend/app/api/routes/forecasts.py` (delete endpoint)
- `backend/tests/api/routes/test_forecasts.py` (delete tests)

**Dependencies:** Step 5 complete

---

### Step 7: Backend API Client Regeneration

**Acceptance Criteria:**
- OpenAPI client regenerated with new Forecast endpoints
- TypeScript types generated for Forecast models
- Client includes `ForecastsService` with methods: `readForecasts()`, `readForecast()`, `createForecast()`, `updateForecast()`, `deleteForecast()`
- TypeScript compilation succeeds

**Test-First Requirement:**
- Attempt to import Forecast types in frontend component (should fail before regeneration)
- After regeneration, import should succeed

**Expected Files:**
- `frontend/src/client/schemas.gen.ts` (updated)
- `frontend/src/client/services/ForecastsService.ts` (new or updated)
- `frontend/src/client/index.ts` (updated exports)

**Dependencies:** Step 6 complete

---

### Step 8: Frontend ForecastsTable Component Scaffolding

**Acceptance Criteria:**
- `ForecastsTable.tsx` component created with DataTable structure
- Table columns defined: Forecast Date, EAC, ETC (calculated), Forecast Type, Current indicator, Estimator, Assumptions (truncated), Actions
- Table uses TanStack Table v8 (matches existing DataTable pattern)
- Table fetches forecasts using `ForecastsService.readForecasts()`
- Table orders by forecast_date descending
- Empty state displayed when no forecasts
- Component accepts `costElementId` prop
- TypeScript compilation succeeds (may have runtime errors for missing data)

**Test-First Requirement:**
- Create component file with table structure
- Add failing test or TypeScript check for component rendering
- Test should fail before full implementation

**Expected Files:**
- `frontend/src/components/Projects/ForecastsTable.tsx` (new)
- Optional: `frontend/src/components/Projects/__tests__/ForecastsTable.test.tsx` (component test)

**Dependencies:** Step 7 complete

---

### Step 9: Frontend AddForecast Dialog Component

**Acceptance Criteria:**
- `AddForecast.tsx` component created with dialog form
- Form fields: Forecast Date (date picker, default: today), EAC (number input, currency), Forecast Type (select dropdown with enum values), Mark as Current (checkbox, default: checked), Assumptions (textarea, optional), Estimator (read-only, current user)
- Form validation: forecast_date required, EAC required and > 0, forecast_type required
- Real-time ETC calculation displayed: ETC = EAC - AC (if AC available)
- Warning displayed if forecast_date is future (alert, not blocked)
- Warning displayed if EAC > BAC (yellow badge)
- Warning displayed if EAC < AC (yellow badge)
- Form uses React Hook Form (matches AddEarnedValueEntry pattern)
- Submit button creates forecast via `ForecastsService.createForecast()`
- Success toast on create, error toast on failure
- Query invalidation refreshes forecasts table
- Dialog closes on success

**Test-First Requirement:**
- Create component file with form structure
- Add failing test or TypeScript check for form validation
- Test should fail before full implementation

**Expected Files:**
- `frontend/src/components/Projects/AddForecast.tsx` (new)
- Optional: `frontend/src/components/Projects/__tests__/AddForecast.test.tsx` (component test)

**Dependencies:** Step 8 complete

---

### Step 10: Frontend EditForecast Dialog Component

**Acceptance Criteria:**
- `EditForecast.tsx` component created with dialog form
- Form pre-populated with existing forecast data
- Only allows editing if forecast is current (`is_current=True`)
- Disables form if forecast is not current (shows message: "Only current forecast can be edited")
- Form fields same as AddForecast
- Form validation same as AddForecast
- Submit button updates forecast via `ForecastsService.updateForecast()`
- Success toast on update, error toast on failure
- Query invalidation refreshes forecasts table
- Dialog closes on success

**Test-First Requirement:**
- Create component file with form structure
- Add failing test for edit functionality
- Test should fail before full implementation

**Expected Files:**
- `frontend/src/components/Projects/EditForecast.tsx` (new)
- Optional: `frontend/src/components/Projects/__tests__/EditForecast.test.tsx` (component test)

**Dependencies:** Step 9 complete

---

### Step 11: Frontend DeleteForecast Confirmation Dialog

**Acceptance Criteria:**
- Delete confirmation dialog component or inline confirmation
- Shows warning message with forecast details
- Special warning if deleting current forecast: "This is the current forecast. Deleting it will automatically promote the previous forecast."
- Delete button calls `ForecastsService.deleteForecast()`
- Success toast on delete, error toast on failure
- Query invalidation refreshes forecasts table
- Confirmation dialog closes on success

**Test-First Requirement:**
- Create delete confirmation component or add to ForecastsTable
- Add failing test for delete functionality
- Test should fail before full implementation

**Expected Files:**
- `frontend/src/components/Projects/ForecastsTable.tsx` (delete confirmation logic)
- Or: `frontend/src/components/Projects/DeleteForecast.tsx` (new, if separate component)

**Dependencies:** Step 10 complete

---

### Step 12: Frontend ForecastsTable Integration - ETC Calculation and Warnings

**Acceptance Criteria:**
- ForecastsTable displays calculated ETC column (EAC - AC)
- ETC shows "N/A" if AC not available
- EAC column color-coded: green if EAC < BAC, yellow if EAC ≈ BAC (±5%), red if EAC > BAC
- Current forecast badge displayed (green "Current" badge)
- Forecast type displayed as colored badge/chip
- Assumptions column truncated to 100 characters with tooltip for full text
- Edit button only shown for current forecast
- Delete button shown for all forecasts
- Table actions work correctly

**Test-First Requirement:**
- Update ForecastsTable with ETC calculation and warnings
- Add failing test for ETC calculation logic
- Test should fail before implementation

**Expected Files:**
- `frontend/src/components/Projects/ForecastsTable.tsx` (ETC calculation, warnings, badges)
- Optional: `frontend/src/hooks/useForecastCalculations.ts` (ETC calculation hook)

**Dependencies:** Step 11 complete

---

### Step 13: Frontend Cost Element Detail Page - Forecasts Tab Integration

**Acceptance Criteria:**
- "Forecasts" tab added to cost element detail page
- Tab positioned between "Earned Value" and "Metrics" tabs
- Tab content displays ForecastsTable component
- Tab navigation works correctly
- Route search param `view=forecasts` works
- Tab persists in URL state

**Test-First Requirement:**
- Update cost element detail route file
- Add failing test for tab navigation
- Test should fail before implementation

**Expected Files:**
- `frontend/src/routes/_layout/projects.$id.wbes.$wbeId.cost-elements.$costElementId.tsx` (add Forecasts tab)
- Optional: Integration test for tab navigation

**Dependencies:** Step 12 complete

---

### Step 14: Frontend Validation Hooks and Utilities

**Acceptance Criteria:**
- `useForecastDateValidation()` hook validates forecast date (past date, alert if future)
- `useEACValidation()` hook validates EAC and shows warnings (EAC > BAC, EAC < AC)
- `useETCCalculation()` hook calculates ETC = EAC - AC
- Hooks follow existing validation hook patterns (useRevenuePlanValidation, useRegistrationDateValidation)
- Hooks integrated into AddForecast and EditForecast components
- All validation working correctly

**Test-First Requirement:**
- Create validation hooks
- Add failing tests for hook logic
- Tests should fail before implementation

**Expected Files:**
- `frontend/src/hooks/useForecastDateValidation.ts` (new)
- `frontend/src/hooks/useEACValidation.ts` (new)
- `frontend/src/hooks/useETCCalculation.ts` (new)
- Optional: Hook tests

**Dependencies:** Step 13 complete

---

### Step 15: Backend Integration Tests and Edge Cases

**Acceptance Criteria:**
- Integration tests for full forecast lifecycle (create → update → delete with auto-promotion)
- Tests for concurrent forecast creation with `is_current=True` (race condition handling)
- Tests for max forecast dates enforcement (3 unique dates)
- Tests for forecast date validation (past date required, future date warning)
- Tests for EAC validation (positive value required)
- Tests for edit restriction (only current forecast editable)
- Tests for auto-promotion on delete (various scenarios)
- All integration tests pass

**Test-First Requirement:**
- Add integration tests to `backend/tests/api/routes/test_forecasts.py`
- Tests should cover edge cases and error scenarios
- Run tests to verify coverage

**Expected Files:**
- `backend/tests/api/routes/test_forecasts.py` (integration tests)

**Dependencies:** Step 14 complete

---

### Step 16: Frontend E2E Tests (Playwright)

**Acceptance Criteria:**
- E2E test for creating forecast (full workflow)
- E2E test for editing current forecast
- E2E test for deleting current forecast (with auto-promotion verification)
- E2E test for forecast date validation (future date alert)
- E2E test for EAC warnings (EAC > BAC, EAC < AC)
- E2E test for max forecast dates enforcement (error on 4th date)
- E2E test for edit restriction (non-current forecast)
- All E2E tests pass

**Test-First Requirement:**
- Create E2E test file `frontend/tests/forecast-crud.spec.ts`
- Add failing E2E tests
- Tests should fail before full implementation

**Expected Files:**
- `frontend/tests/forecast-crud.spec.ts` (new E2E test file)

**Dependencies:** Step 15 complete

---

### Step 17: Documentation and Project Status Update

**Acceptance Criteria:**
- `docs/project_status.md` updated with E5-001 completion status
- Completion report created in `docs/completions/e5-001-forecast-creation-interface-completion.md`
- All automated tests green
- No linter errors
- Code review checklist completed

**Test-First Requirement:**
- Introduce temporary failing check (e.g., TODO in test) before updating docs
- Remove failing check after documentation updated

**Expected Files:**
- `docs/project_status.md` (E5-001 status update)
- `docs/completions/e5-001-forecast-creation-interface-completion.md` (new completion report)

**Dependencies:** Steps 1-16 complete

---

## 2. TDD Discipline Rules

- **Failing Test First:** Every step must begin with a failing test or TypeScript check
- **Red-Green-Refactor:** Follow strict red → green → refactor cycle; refactor only when tests pass
- **Maximum Iterations:** Limit to 3 attempts per step before stopping to ask for help
- **Behavior Verification:** Tests must verify behavior (API responses, UI rendering, validation), not just compilation state
- **Incremental Commits:** Target ≤100 lines changed and ≤5 files per commit
- **No Code Duplication:** Reuse existing abstractions and patterns

---

## 3. Process Checkpoints

### Checkpoint 1: After Step 6 (Backend CRUD Complete)
**Pause and ask:**
1. Should we continue with the plan as-is?
2. Have any assumptions been invalidated?
3. Does the backend API match our expectations?
4. Are there any issues with the versioning logic or validation?

### Checkpoint 2: After Step 13 (Frontend Integration Complete)
**Pause and ask:**
1. Should we continue with the plan as-is?
2. Have any assumptions been invalidated?
3. Does the UI behavior match our expectations?
4. Are there any UX issues or missing features?

### Checkpoint 3: After Step 16 (E2E Tests Complete)
**Pause and ask:**
1. Should we continue with the plan as-is?
2. Have any assumptions been invalidated?
3. Are all tests passing and coverage adequate?
4. Ready for documentation and final review?

---

## 4. Scope Boundaries

- **In Scope:**
  - Forecast CRUD API with versioning logic
  - ForecastsTable component with Add/Edit/Delete dialogs
  - Forecasts tab in cost element detail page
  - Validation and warnings (EAC > BAC, EAC < AC, future date)
  - Auto-promotion on delete
  - ETC calculation (display-only)
  - Maximum 3 forecast dates enforcement
  - Edit restriction (only current forecast)

- **Out of Scope:**
  - Forecast wizard (E5-001A - future enhancement)
  - Forecast export functionality (E4-010 covers report export)
  - Forecast trend analysis visualization (E5-007)
  - Forecast integration in reports (E5-006)
  - Role-based permissions for forecast creation (follows existing patterns)

**Any additional enhancements or refactors require explicit user approval before proceeding.**

---

## 5. Rollback Strategy

### Safe Rollback Points

1. **After Step 1 (Enum and Model Updates):**
   - Rollback: Revert enum changes, keep model as string
   - Impact: Low - only model changes, no API changes yet

2. **After Step 6 (Backend CRUD Complete):**
   - Rollback: Remove forecast routes, keep model
   - Impact: Medium - backend API removed, frontend not started yet
   - Alternative: Keep backend API, postpone frontend implementation

3. **After Step 13 (Frontend Integration Complete):**
   - Rollback: Remove Forecasts tab and components
   - Impact: High - frontend changes reverted, backend remains
   - Alternative: Keep backend, simplify frontend to basic table only

### Alternative Approaches

If Approach 1 (Full CRUD) fails:
1. **Backend-Only Approach:** Implement backend API only, provide basic frontend table without dialogs
2. **Simplified Frontend:** Use inline editing instead of dialogs
3. **Defer to Post-MVP:** Mark as incomplete, implement in next sprint

**If rollback needed, consult user before proceeding with alternative approach.**

---

## 6. Risk Mitigation

### High-Risk Areas

1. **Versioning Race Conditions:**
   - Mitigation: Use database transaction with proper locking in `ensure_single_current_forecast()`
   - Testing: Add concurrent test scenarios in Step 15

2. **Max Forecast Dates Enforcement:**
   - Mitigation: Count unique forecast_date values per cost_element_id before allowing create
   - Testing: Add test for 4th forecast date attempt in Step 15

3. **Auto-Promotion Logic:**
   - Mitigation: Query forecasts ordered by forecast_date DESC, find first non-deleted forecast
   - Testing: Add comprehensive auto-promotion tests in Step 15

4. **Edit Restriction (Only Current Forecast):**
   - Mitigation: Backend validates `is_current=True` before allowing update
   - Testing: Add test for editing non-current forecast in Step 15

### Medium-Risk Areas

1. **ETC Calculation:**
   - Mitigation: Fetch AC from cost element or cost aggregation endpoint
   - Testing: Add test for ETC calculation with/without AC in Step 12

2. **Forecast Date Validation:**
   - Mitigation: Backend validates date <= today(), frontend shows alert if future
   - Testing: Add test for future date handling in Step 15

3. **EAC Warnings:**
   - Mitigation: Fetch BAC and AC, compare in frontend, show warnings
   - Testing: Add test for warning display in Step 12

---

## 7. Estimated Effort

- **Backend (Steps 1-6):** 8-12 hours
- **Frontend (Steps 7-14):** 6-8 hours
- **Testing (Steps 15-16):** 4-6 hours
- **Documentation (Step 17):** 1-2 hours
- **Total:** 19-28 hours

---

## 8. Success Criteria

The implementation is considered successful when:

1. ✅ All backend tests pass (unit, integration)
2. ✅ All frontend tests pass (component, E2E)
3. ✅ Forecast CRUD operations work correctly
4. ✅ Versioning logic ensures single current forecast
5. ✅ Auto-promotion works on delete
6. ✅ Validation and warnings display correctly
7. ✅ ETC calculation works (EAC - AC)
8. ✅ Max 3 forecast dates enforced
9. ✅ Edit restriction works (only current forecast)
10. ✅ Forecasts tab integrated in cost element detail page
11. ✅ No linter errors
12. ✅ Documentation updated

---

**Plan Complete - Ready for Implementation**
