# Analysis: E05-U05 Validate Cost Registrations against Budgets

**Created:** 2026-04-14
**Request:** Implement real-time validation with warning thresholds and configurable blocking for cost registration budget enforcement
**Story Points:** 8
**Epic:** E005 (Financial Data Management)
**Dependencies:** E04-U03 ✅, E05-U01 ✅

---

## Clarified Requirements

### Functional Requirements

1. **Real-time Budget Validation**: When creating or updating cost registrations, the system must validate that total costs ≤ allocated budget
2. **Warning Threshold**: Display a warning when approaching budget limit (default: 80% of budget)
3. **Configurable Blocking**: Optionally block cost registration when exceeding budget (configurable via settings)
4. **Budget Status API**: Existing `get_budget_status()` endpoint provides budget, used, remaining, percentage
5. **User Feedback**: Clear visual indicators and messages for warnings and blocking scenarios

### Non-Functional Requirements

- **Performance**: Validation must not add significant latency to cost registration operations (<100ms overhead)
- **Flexibility**: Warning threshold and blocking behavior must be configurable
- **User Experience**: Warnings should inform users without interrupting workflow unnecessarily
- **Testability**: All validation scenarios must have comprehensive test coverage

### Constraints

- **Permissive Current Implementation**: Backend currently allows over-budget registrations (line 124 in cost_registration_service.py: "Budget validation removed - allowing over-budget registration with frontend warning")
- **Frontend Warning Exists**: CostRegistrationModal.tsx already implements a client-side warning modal (lines 101-144)
- **No Server-Side Enforcement**: Current implementation relies solely on frontend validation
- **Configuration System**: No existing configuration infrastructure for budget thresholds in Settings

---

## Context Discovery

### Product Scope

**Relevant User Stories:**
- **E05-U01** ✅: Register Actual Costs against Cost Elements (complete)
- **E05-U05**: Current story - Validate Cost Registrations against Budgets
- **E05-U06**: View Cost History and Trends (dependent on validation)

**Business Requirements:**
From `docs/01-product-scope/functional-requirements.md`:
- Section 6.2: "The system must maintain the integrity of budget allocations and provide warnings when total allocated budgets exceed available project budgets"
- Enables proactive budget management before cost overruns occur
- Supports PMI standards for cost control and forecasting

### Architecture Context

**Bounded Contexts Involved:**
1. **Cost Element & Financial Tracking** (Context 6) - Primary context
2. **EVM Calculations & Reporting** (Context 7) - Consumer of budget status data

**Existing Patterns to Follow:**
- **Service Layer Validation**: Similar to `CostElementService` validation patterns
- **Exception Handling**: Use custom exception classes like `OverlappingVersionError`
- **API Response Patterns**: Standardized error responses via `HTTPException`
- **Configuration Management**: Pydantic `BaseSettings` pattern in `backend/app/core/config.py`

**Architectural Constraints:**
- **EVCS Versioning**: Cost registrations are versionable but NOT branchable (global facts)
- **Bitemporal Queries**: Must respect `as_of` parameter for historical accuracy
- **RBAC**: Existing `cost-registration-create` permission must be maintained
- **Time-Travel**: Validation must work correctly with time-travel queries

### Codebase Analysis

**Backend:**

**Existing Related APIs:**
- `backend/app/api/routes/cost_registrations.py`:
  - `POST /cost-registrations` (line 123-153): Create endpoint with try/except error handling
  - `GET /cost-registrations/budget-status/{cost_element_id}` (line 160-205): Returns budget status
  - Current docstring mentions "Raises BudgetExceededError" but exception is not implemented

**Data Models:**
- `backend/app/models/schemas/cost_registration.py`:
  - `CostRegistrationCreate`: Input schema for creating registrations
  - `CostRegistrationUpdate`: Input schema for updating registrations
  - `CostRegistrationRead`: Output schema returned to client
- `backend/app/services/cost_registration_service.py`:
  - `BudgetStatus`: Pydantic model with budget, used, remaining, percentage (lines 28-35)
  - `create_cost_registration()`: Currently permissive (line 124 comment)
  - `get_budget_status()`: Fully implemented with time-travel support (lines 371-430)

**Similar Patterns:**
- `backend/app/core/versioning/exceptions.py`: `OverlappingVersionError` - Custom exception pattern to follow
- `backend/app/services/cost_element_service.py`: Multiple `ValueError` raises for validation (lines 197, 212, 344)
- `backend/app/api/routes/cost_registrations.py`: Try/except pattern for error handling (lines 143-153)

**Configuration Infrastructure:**
- `backend/app/core/config.py`: `Settings` class using `pydantic_settings.BaseSettings`
- Environment-based configuration via `.env` file
- No current budget validation settings

**Frontend:**

**Comparable Components:**
- `frontend/src/features/cost-registration/components/CostRegistrationModal.tsx`:
  - **Already Implements Client-Side Warning**: Lines 101-144 show budget exceeded confirmation modal
  - Calculates effective used amount (subtracting old amount when editing)
  - Shows budget, currently used, and projected total
  - Uses `App.useApp().modal.confirm()` for warning dialog
  - Registration proceeds only after user confirmation

**State Management:**
- `frontend/src/features/cost-registration/api/useCostRegistrations.ts`:
  - `useBudgetStatus()`: Hook for fetching budget status (lines 134-148)
  - `useCreateCostRegistration()`: Mutation hook with error handling (lines 174-221)
  - Lines 212-216: Already check for "Budget exceeded" in error message
  - Invalidates budget status queries after mutations

**API Integration:**
- Generated OpenAPI client: `frontend/src/api/generated/services/CostRegistrationsService.ts`
- Query keys factory: `frontend/src/api/queryKeys.ts`

---

## Solution Options

### Option 1: Server-Side Enforcement with Configuration (Recommended)

**Architecture & Design:**
- Add budget validation settings to `backend/app/core/config.py`:
  - `BUDGET_WARNING_THRESHOLD: Decimal = Decimal("0.8")` (80%)
  - `BUDGET_BLOCKING_ENABLED: bool = False` (default permissive)
- Create custom exception `BudgetExceededError` in `backend/app/core/exceptions.py`
- Modify `CostRegistrationService.create_cost_registration()` and `update_cost_registration()`:
  - Calculate projected total (current used + new amount)
  - Check against budget threshold
  - Raise warning exception if exceeding threshold but blocking disabled
  - Raise blocking exception if exceeding budget and blocking enabled
- Update API route `POST /cost-registrations` to handle new exceptions
- Enhance `BudgetStatus` response to include warning level and blocking status

**UX Design:**
- **Warning Scenario**: Backend returns 200 with warning metadata in response body
  - Frontend displays toast notification: "Warning: Cost registration at 85% of budget"
  - Visual indicator: Yellow/amber progress bar in budget status widget
- **Blocking Scenario**: Backend returns 403 Forbidden with error details
  - Frontend shows error modal: "Cannot exceed budget limit (€10,000)"
  - Provides option to request budget increase via change order
- **Configuration**: Admin can enable/disable blocking via environment variable

**Implementation:**
- **Backend Changes**:
  - `backend/app/core/config.py`: Add budget validation settings
  - `backend/app/core/exceptions.py`: Create `BudgetExceededError` and `BudgetWarningException`
  - `backend/app/services/cost_registration_service.py`: Add validation logic in `create_cost_registration()` and `update_cost_registration()`
  - `backend/app/models/schemas/cost_registration.py`: Add `BudgetValidationResult` schema
  - `backend/app/api/routes/cost_registrations.py`: Update create/update endpoints to handle validation results
  - `backend/tests/unit/services/test_cost_registration_budget_validation.py`: Update tests for new validation behavior

- **Frontend Changes**:
  - `frontend/src/features/cost-registration/api/useCostRegistrations.ts`: Update error handling for new validation responses
  - `frontend/src/features/cost-registration/components/CostRegistrationModal.tsx`: Enhance to display server-side warnings
  - Add visual budget status indicator with warning levels

**Trade-offs:**

| Aspect          | Assessment                 |
| --------------- | -------------------------- |
| Pros            | - Centralized validation logic<br>- Single source of truth for budget rules<br>- Impossible to bypass via API calls<br>- Configurable per environment<br>- Follows defense-in-depth principle |
| Cons            | - More backend complexity<br>- Requires migration to update existing data if changing thresholds<br>- Additional database query per registration |
| Complexity      | Medium                    |
| Maintainability | Good (clear separation of concerns) |
| Performance     | Minimal impact (<50ms per validation) |

---

### Option 2: Client-Side Only (Current Approach Enhanced)

**Architecture & Design:**
- Keep backend permissive (no blocking)
- Enhance existing `CostRegistrationModal.tsx` warning modal:
  - Make warning threshold configurable via frontend settings
  - Add visual indicators (progress bar color changes: green → yellow → red)
  - Implement optional blocking based on user preference
- Store threshold preference in browser localStorage
- Add "Always allow over-budget" checkbox with "Don't show again" option

**UX Design:**
- **Default Behavior**: Warning modal appears when exceeding 80% (configurable)
- **User Choice**: "Proceed anyway" or "Cancel"
- **Persistent Preference**: Remember user's choice for future registrations
- **Visual Feedback**: Budget progress bar shows warning colors

**Implementation:**
- **Backend Changes**: None (keep current permissive approach)
- **Frontend Changes**:
  - `frontend/src/features/cost-registration/components/CostRegistrationModal.tsx`:
    - Extract threshold to constant or setting
    - Add localStorage for user preference
    - Enhance warning modal with visual indicators
  - `frontend/src/features/cost-registration/components/BudgetProgressBar.tsx`: New component for visual budget status
  - Add TypeScript types for budget validation settings

**Trade-offs:**

| Aspect          | Assessment                 |
| --------------- | -------------------------- |
| Pros            | - No backend changes required<br>- Faster to implement<br>- Flexible per-user preferences<br>- No database overhead |
| Cons            | - Validation can be bypassed via direct API calls<br>- No centralized control<br>- Settings lost when clearing browser data<br>- Doesn't enforce business rules at data layer |
| Complexity      | Low                       |
| Maintainability | Fair (frontend-only logic) |
| Performance     | Excellent (no backend overhead) |

---

### Option 3: Hybrid Approach with Audit Trail

**Architecture & Design:**
- Implement server-side validation (Option 1)
- Add budget override mechanism:
  - Users can request budget override with justification
  - Override requires elevated permissions (Project Manager or higher)
  - All overrides logged in audit trail
- Create `BudgetOverride` entity to track exceptions:
  - `cost_registration_id`, `original_budget`, `exceeded_amount`, `justification`, `approved_by`, `approved_at`
- Dashboard widget showing budget exceptions

**UX Design:**
- **Standard Flow**: Enforce validation (warning or block based on config)
- **Override Flow**: When blocked, show "Request Budget Override" button
  - Opens form requiring justification
  - Submits to Project Manager for approval
  - On approval, allows registration to proceed
- **Audit View**: Admin dashboard shows all budget exceptions

**Implementation:**
- **Backend Changes** (Option 1 plus):
  - `backend/app/models/domain/budget_override.py`: New entity for tracking overrides
  - `backend/app/services/budget_override_service.py`: CRUD for override requests
  - `backend/app/api/routes/budget_overrides.py`: New API endpoints
  - Migration to create `budget_overrides` table
  - Update RBAC permissions for override approval

- **Frontend Changes** (Option 1 plus):
  - Override request modal component
  - Admin dashboard widget for budget exceptions
  - Notification system for override approvals

**Trade-offs:**

| Aspect          | Assessment                 |
| --------------- | -------------------------- |
| Pros            | - Enforces business rules while allowing exceptions<br>- Full audit trail for compliance<br>- Flexible for urgent situations<br>- Supports change order workflow integration |
| Cons            | - Highest complexity (new entity, API, UI)<br>- Additional approval workflow overhead<br>- More database storage and queries<br>- Longer implementation time |
| Complexity      | High                      |
| Maintainability | Good (structured but complex) |
| Performance     | Good (additional queries for overrides) |

---

## Comparison Summary

| Criteria           | Option 1 (Server-Side) | Option 2 (Client-Side) | Option 3 (Hybrid) |
| ------------------ | ---------------------- | ---------------------- | ----------------- |
| Development Effort | Medium (3-4 days)      | Low (1-2 days)         | High (5-7 days)   |
| UX Quality         | Good (consistent)       | Fair (variable)        | Excellent (flexible) |
| Flexibility        | Good (configurable)     | Excellent (per-user)   | Excellent (overrides) |
| Security           | Excellent (enforced)    | Poor (bypassable)      | Excellent (audited) |
| Compliance         | Good                   | Poor                   | Excellent         |
| Maintenance        | Good                   | Fair                   | Fair (complex)    |
| Best For           | Production deployment   | Rapid prototyping      | Enterprise compliance |

---

## Recommendation

**I recommend Option 1 (Server-Side Enforcement with Configuration) because:**

1. **Data Integrity**: Enforces business rules at the data layer, preventing violations via any API client
2. **Security**: Cannot be bypassed by direct API calls or missing frontend validation
3. **Consistency**: Single source of truth for budget validation rules across all clients
4. **Configurability**: Easy to adjust thresholds and blocking behavior per environment
5. **PMI Compliance**: Follows Project Management Institute standards for cost control
6. **Defense-in-Depth**: Complements existing frontend warning (already implemented)
7. **Maintainability**: Clear separation between validation logic and UI concerns

**Implementation Strategy:**
- Start with blocking disabled (`BUDGET_BLOCKING_ENABLED: bool = False`) to match current permissive behavior
- Enable warnings by default at 80% threshold
- Allow production teams to enable blocking via environment variable when ready
- Enhance frontend to display server-side validation results
- Maintain existing client-side warning as UX enhancement

**Alternative consideration:**
Choose **Option 2 (Client-Side Only)** if:
- This is a prototype/MVP and data integrity is not critical
- Rapid deployment is the priority over robust validation
- All API access is through the official frontend only
- Budget enforcement is "nice-to-have" rather than a requirement

Choose **Option 3 (Hybrid Approach)** if:
- Enterprise compliance requires audit trails for all budget exceptions
- Override workflow is needed for urgent situations
- Change order integration is required for budget increases
- Additional development time is available (5-7 days)

---

## Decision Questions - ANSWERED

**Decisions made on 2026-04-14:**

1. **Blocking Behavior**: ✅ **WARN ONLY** (do not block)
   - System will warn when approaching/exceeding budget limits
   - Registration will proceed regardless (no blocking)
   - Server-side warnings returned in API response

2. **Warning Threshold**: ✅ **CONFIGURABLE and PERSISTED ON DB, default 80%**
   - Threshold stored per-project in database
   - Default: 80% of budget
   - Configurable via project detail page and dedicated widget component

3. **Configuration Scope**: ✅ **PER-PROJECT SETTING**
   - Configuration UI on project detail page
   - Dedicated widget component for budget threshold management
   - Each project can have its own warning threshold

4. **Override Mechanism**: ✅ **PROJECT ADMIN ROLES SHALL OVERRIDE THE DEFAULT**
   - Users with project admin role can bypass default behavior
   - Role-based permission check for override capability
   - No separate approval workflow needed

5. **Migration Strategy**: ✅ **DO NOT CHANGE EXISTING REGISTRATIONS**
   - Existing over-budget registrations remain as-is
   - Validation only applies to new registrations
   - No data migration required

**Implementation Approach Update:**
Based on these decisions, the solution will be:
- **Modified Option 1**: Server-side warnings only (no blocking)
- **Per-project configuration**: Database-backed settings
- **Project admin override**: Role-based bypass mechanism
- **No migration**: Grandfather existing data

---

## References

**Architecture Documentation:**
- [Cost Element & Financial Tracking Context](/home/nicola/dev/backcast/docs/02-architecture/backend/contexts/project-management/architecture.md)
- [API Conventions](/home/nicola/dev/backcast/docs/02-architecture/cross-cutting/api-conventions.md)
- [Database Strategy](/home/nicola/dev/backcast/docs/02-architecture/cross-cutting/database-strategy.md)
- [Error Codes](/home/nicola/dev/backcast/docs/02-architecture/error-codes.md)

**Product Requirements:**
- [Functional Requirements - Cost Management](/home/nicola/dev/backcast/docs/01-product-scope/functional-requirements.md) (Section 6)
- [E05-U05 User Story](/home/nicola/dev/backcast/docs/03-project-plan/product-backlog.md) (line 246)
- [Epic E005: Financial Data Management](/home/nicola/dev/backcast/docs/03-project-plan/epics.md) (line 109)

**Code References:**
- `backend/app/services/cost_registration_service.py`: Lines 53-133 (create_cost_registration), 371-430 (get_budget_status)
- `backend/app/api/routes/cost_registrations.py`: Lines 123-153 (POST endpoint), 160-205 (budget-status endpoint)
- `frontend/src/features/cost-registration/components/CostRegistrationModal.tsx`: Lines 101-144 (existing warning modal)
- `frontend/src/features/cost-registration/api/useCostRegistrations.ts`: Lines 174-221 (create mutation with error handling)
- `backend/app/core/config.py`: Settings configuration pattern
- `backend/tests/unit/services/test_cost_registration_budget_validation.py`: Existing test expectations

**Related Work:**
- [E05-U01 Implementation](/home/nicola/dev/backcast/docs/03-project-plan/iterations/2026-01-15-register-actual-costs/00-analysis.md): Cost registration foundation
- Schedule Baseline Implementation: Similar validation patterns for progression types
