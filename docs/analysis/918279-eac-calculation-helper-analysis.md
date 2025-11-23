# High-Level Analysis: EAC Calculation Helper with Forecast/BAC Fallback

**Task:** EAC Calculation Helper Function
**Status:** Analysis Phase - Business Problem and Technical Approach
**Date:** 2025-11-23
**Analysis Code:** 918279

---

## Objective

Create a helper function that calculates Estimate at Completion (EAC) using forecast values as the primary source, with Budget at Completion (BAC) as a fallback when no forecast exists. The function must support cost element, WBE, and project levels, following established aggregation patterns in the codebase.

---

## User Story

**As a** project manager
**I want to** have a consistent EAC value calculated from forecasts or falling back to planned budget (BAC)
**So that** I can always have an estimate at completion value for EVM calculations and reporting, even when forecasts haven't been created yet.

---

## CODEBASE PATTERN ANALYSIS

### Pattern 1: EVM Aggregation Service (E4-005) - Primary Reference

**Location:** `backend/app/services/evm_aggregation.py`

**Pattern Characteristics:**
- Service layer for EVM metric calculations
- Functions for cost element level: `get_cost_element_evm_metrics()`
- Aggregation functions: `aggregate_cost_element_metrics()` for WBE/project levels
- Returns dataclass types: `CostElementEVMMetrics`, `WBEEVMMetrics`, `ProjectEVMMetrics`
- Uses existing calculation services: `calculate_cost_element_planned_value()`, `calculate_cost_element_earned_value()`
- Quantization: Uses `_quantize()` helper for Decimal precision (2 decimal places)

**Reusable Elements:**
- Service layer pattern (`backend/app/services/`)
- Dataclass return types with `@dataclass(slots=True)`
- Aggregation by summing cost element values
- Helper functions for single cost element calculations

### Pattern 2: Planned Value Calculation Service (E4-002)

**Location:** `backend/app/services/planned_value.py`

**Pattern Characteristics:**
- Service functions: `calculate_cost_element_planned_value()` returns `(Decimal, Decimal)` tuple
- Aggregation function: `aggregate_planned_value()` for multiple cost elements
- Returns `AggregateResult` dataclass with `planned_value`, `percent_complete`, `budget_bac`
- Quantization: Uses `TWO_PLACES` and `FOUR_PLACES` constants
- Handles None/empty cases: Returns zeros if no schedule exists

**Reusable Elements:**
- Tuple return pattern for single cost element: `(value, percent)`
- AggregateResult dataclass pattern
- Quantization constants and helpers
- Empty case handling

### Pattern 3: Earned Value Calculation Service (E4-002)

**Location:** `backend/app/services/earned_value.py`

**Pattern Characteristics:**
- Service function: `calculate_cost_element_earned_value()` returns `(Decimal, Decimal)` tuple
- Aggregation function: `aggregate_earned_value()` for multiple cost elements
- Returns `AggregateResult` dataclass
- Similar structure to planned value service

**Reusable Elements:**
- Same tuple return and aggregation patterns
- Consistent service layer structure

### Pattern 4: Forecast EAC Retrieval (Current Implementation)

**Location:** `backend/app/api/routes/earned_value.py`

**Pattern Characteristics:**
- Helper function: `_get_forecast_eac_map()` in route layer
- Returns `dict[uuid.UUID, Decimal | None]` mapping cost_element_id -> EAC
- Queries current forecasts (`is_current=True`) filtered by `control_date`
- Returns `None` if no current forecast exists

**Current Limitations:**
- Located in route layer (should be in service layer)
- No fallback to BAC
- Returns `None` when no forecast exists

**Reusable Elements:**
- Forecast query pattern (can be moved to service)
- Map-based return for batch operations

### Established Architectural Layers

**Service Layer:** `backend/app/services/`
- Pure calculation functions (no database session dependencies)
- Reusable across different route handlers
- Returns dataclasses or tuples
- Quantization helpers for Decimal precision

**Route Layer:** `backend/app/api/routes/`
- Uses service layer functions
- Handles database queries and session management
- Returns API response models

**Model Layer:** `backend/app/models/`
- SQLModel definitions
- Base/Create/Update/Public schemas

---

## INTEGRATION TOUCHPOINT MAPPING

### Backend Integration Points

1. **New Service File** (`backend/app/services/eac_calculation.py` - NEW)
   - Create new service module following `planned_value.py` and `earned_value.py` patterns
   - Functions:
     - `calculate_cost_element_eac()` - Single cost element EAC
     - `aggregate_eac()` - Aggregate EAC for WBE/project levels
   - Dependencies:
     - `Forecast` model (for forecast EAC)
     - `CostElement` model (for BAC fallback)
     - `CostElementSchedule` model (for planned value calculation if needed)

2. **EVM Aggregation Service** (`backend/app/services/evm_aggregation.py`)
   - **Status:** May need to add EAC field to `CostElementEVMMetrics`, `WBEEVMMetrics`, `ProjectEVMMetrics` dataclasses
   - **Impact:** If EAC is added to EVM metrics, update aggregation logic

3. **Earned Value Routes** (`backend/app/api/routes/earned_value.py`)
   - **Current:** Uses `_get_forecast_eac_map()` helper
   - **Change:** Replace with service layer function calls
   - **Impact:** Refactor to use new service function

4. **EVM Aggregation Routes** (`backend/app/api/routes/evm_aggregation.py`)
   - **Current:** Uses `_get_forecast_eac_map()` helper
   - **Change:** Replace with service layer function calls
   - **Impact:** Refactor to use new service function

5. **Forecast Routes** (`backend/app/api/routes/forecasts.py`)
   - **Status:** No changes needed (forecast creation/update logic remains unchanged)

### Frontend Integration Points

1. **EarnedValueSummary Component** (`frontend/src/components/Projects/EarnedValueSummary.tsx`)
   - **Status:** Already displays EAC from API responses
   - **Impact:** None - will automatically use new fallback logic via API

2. **API Client Types** (`frontend/src/client/types.gen.ts`)
   - **Status:** Auto-generated from OpenAPI spec
   - **Impact:** None - types will update when backend changes are reflected in OpenAPI

### Configuration Patterns

**No configuration needed** - EAC calculation logic is deterministic based on:
- Forecast existence (current forecast with `is_current=True`)
- BAC value from cost element
- Control date for time machine filtering

---

## ABSTRACTION INVENTORY

### Existing Abstractions to Leverage

1. **Service Layer Pattern:**
   - Location: `backend/app/services/`
   - Pattern: Pure functions, no session dependencies
   - Examples: `planned_value.py`, `earned_value.py`, `evm_aggregation.py`

2. **Quantization Helpers:**
   - Location: `backend/app/services/planned_value.py`, `earned_value.py`
   - Constants: `TWO_PLACES = Decimal("0.01")`, `FOUR_PLACES = Decimal("0.0001")`
   - Function: `_quantize(value: Decimal, exp: Decimal) -> Decimal`

3. **AggregateResult Dataclass Pattern:**
   - Location: `backend/app/services/planned_value.py`, `earned_value.py`
   - Pattern: `@dataclass(slots=True)` with `planned_value`, `percent_complete`, `budget_bac`
   - Can be adapted for EAC aggregation

4. **Tuple Return Pattern:**
   - Location: `calculate_cost_element_planned_value()`, `calculate_cost_element_earned_value()`
   - Pattern: Returns `(Decimal, Decimal)` tuple for single cost element
   - Can be adapted: `calculate_cost_element_eac()` returns `Decimal`

5. **Forecast Query Pattern:**
   - Location: `backend/app/api/routes/earned_value.py` - `_get_forecast_eac_map()`
   - Pattern: Query current forecasts filtered by control_date
   - Can be extracted to service layer

6. **BAC Retrieval Pattern:**
   - Location: `backend/app/services/evm_aggregation.py`
   - Pattern: `bac = cost_element.budget_bac or Decimal("0.00")`
   - Reusable for fallback logic

### Test Utilities

1. **Test Fixtures:**
   - Location: `backend/tests/`
   - Pattern: Database fixtures for CostElement, Forecast, etc.
   - Reusable for EAC calculation tests

2. **Test Patterns:**
   - Location: `backend/tests/services/` (if exists) or `backend/tests/api/routes/`
   - Pattern: Test service functions with mocked data
   - Can follow existing test patterns

---

## ALTERNATIVE APPROACHES

### Approach 1: Service Layer Function with Forecast/BAC Fallback (RECOMMENDED)

**Description:**
Create a new service module `eac_calculation.py` with functions that:
1. Calculate EAC for single cost element: Use forecast EAC if exists, else use BAC
2. Aggregate EAC for WBE/project: Sum cost element EACs (with fallback logic per element)

**Implementation:**
- **Service Functions:**
  - `calculate_cost_element_eac(forecast_eac: Decimal | None, budget_bac: Decimal) -> Decimal`
  - `aggregate_eac(eac_values: Iterable[Decimal]) -> Decimal`
- **Route Integration:**
  - Replace `_get_forecast_eac_map()` calls with service function calls
  - Service function accepts forecast map and cost elements, returns EAC map with fallback
- **Location:** `backend/app/services/eac_calculation.py`

**Pros:**
- ✅ Follows established service layer pattern
- ✅ Reusable across different route handlers
- ✅ Clear separation of concerns (calculation logic in service, queries in routes)
- ✅ Easy to test (pure functions)
- ✅ Consistent with existing codebase architecture
- ✅ Supports all three levels (cost element, WBE, project)

**Cons:**
- ⚠️ Requires refactoring existing route code
- ⚠️ Need to pass both forecast map and cost elements to service function

**Alignment:** Perfect alignment with existing architecture

**Estimated Complexity:**
- Service layer: 4-6 hours (functions + tests)
- Route refactoring: 2-3 hours
- Total: 6-9 hours

**Risk Factors:**
- Low risk - well-established patterns
- Need to ensure fallback logic is consistent across all usage points

### Approach 2: Extend Existing EVM Aggregation Service

**Description:**
Add EAC calculation to `evm_aggregation.py` service, extending `CostElementEVMMetrics` dataclass to include `eac` field, and adding EAC aggregation logic.

**Implementation:**
- Add `eac: Decimal` field to `CostElementEVMMetrics`, `WBEEVMMetrics`, `ProjectEVMMetrics`
- Add EAC calculation in `get_cost_element_evm_metrics()` function
- Add EAC aggregation in `aggregate_cost_element_metrics()` function
- Update route handlers to use EAC from EVM metrics

**Pros:**
- ✅ Centralizes all EVM metrics in one place
- ✅ EAC becomes part of unified EVM metrics response
- ✅ Single source of truth for all EVM calculations

**Cons:**
- ❌ Mixes EAC calculation (forecast-based) with other EVM metrics (calculated)
- ❌ EAC is not a "calculated" metric like CPI/SPI - it's stored/retrieved
- ❌ Requires passing forecast data to EVM aggregation service
- ❌ Breaks separation: EVM service would need database queries for forecasts
- ❌ More complex - EVM service becomes dependent on forecast queries

**Alignment:** Partial - violates service layer purity (would need database access)

**Estimated Complexity:** 8-12 hours (more complex due to architectural changes)

**Risk Factors:**
- Medium risk - architectural violation (service layer accessing database)
- Higher maintenance burden

### Approach 3: Route-Level Helper with Fallback

**Description:**
Keep EAC calculation in route layer, extend `_get_forecast_eac_map()` to include BAC fallback logic, rename to `_get_eac_map()`.

**Implementation:**
- Modify `_get_forecast_eac_map()` to accept cost elements
- Add fallback logic: if forecast EAC is None, use `cost_element.budget_bac`
- Keep in route layer, used by both `earned_value.py` and `evm_aggregation.py` routes

**Pros:**
- ✅ Minimal changes to existing code
- ✅ Quick implementation
- ✅ No new service file needed

**Cons:**
- ❌ Violates service layer pattern (calculation logic in routes)
- ❌ Not reusable outside route handlers
- ❌ Harder to test (requires database session)
- ❌ Inconsistent with other calculation services
- ❌ Duplicates logic if used in multiple places

**Alignment:** Poor - violates established architectural patterns

**Estimated Complexity:** 3-4 hours (quick but architectural debt)

**Risk Factors:**
- High risk - creates architectural inconsistency
- Technical debt for future refactoring

---

## ARCHITECTURAL IMPACT ASSESSMENT

### Architectural Principles

**Principles Followed:**
- ✅ **Single Responsibility:** EAC calculation service handles only EAC logic
- ✅ **DRY (Don't Repeat Yourself):** Reuses existing patterns (service layer, aggregation)
- ✅ **Separation of Concerns:** Calculation logic in service, queries in routes
- ✅ **Consistency:** Follows same patterns as `planned_value.py` and `earned_value.py`
- ✅ **Testability:** Pure functions are easily testable

**Principles to Consider:**
- ⚠️ **Service Layer Purity:** Service functions should not have database dependencies (forecast queries stay in routes)
- ⚠️ **Fallback Logic Consistency:** Ensure fallback to BAC is applied consistently at all levels

### Maintenance Burden

**Low Maintenance Areas:**
- ✅ Service layer functions follow well-established patterns
- ✅ Aggregation logic is straightforward (sum of values)
- ✅ Fallback logic is simple (forecast EAC or BAC)

**Potential Maintenance Areas:**
- ⚠️ **Fallback Logic Changes:** If business rules change (e.g., different fallback strategy), update service function
- ⚠️ **Forecast Query Changes:** If forecast query logic changes, update route handlers (not service)
- ⚠️ **EAC Calculation Formula:** If EAC calculation becomes more complex (e.g., weighted average of forecasts), update service function

**Mitigation:**
- Service function is isolated and well-documented
- Fallback logic is explicit and easy to modify
- Changes to forecast queries don't affect service layer

### Testing Challenges

**Service Layer Testing:**
- ✅ Standard unit tests for calculation functions
- ✅ Test cases: forecast exists, no forecast (fallback to BAC), None values
- ✅ Aggregation tests: multiple cost elements, empty list, mixed forecast/BAC

**Route Layer Testing:**
- ✅ Integration tests verify service function is called correctly
- ✅ Test forecast query logic separately
- ✅ Test EAC is included in API responses

**Test Coverage Targets:**
- Service layer: 90%+ coverage (calculation logic)
- Route layer: Integration tests for EAC in responses
- Edge cases: None forecasts, zero BAC, negative values (if allowed)

---

## Ambiguities and Missing Information

1. **EAC Aggregation Strategy:**
   - ✅ **RESOLVED:** EAC at WBE/project level = sum of cost element EACs (with fallback per element)
   - **Rationale:** Consistent with BAC aggregation (sum of cost element BACs)

2. **Fallback to BAC vs. Planned Value:**
   - ⚠️ **CLARIFICATION NEEDED:** User requested "fallback to planned value" - does this mean:
     - Option A: Fallback to BAC (Budget at Completion) - the total planned budget
     - Option B: Fallback to PV (Planned Value) - the planned value at control date
   - **Recommendation:** Option A (BAC) - EAC represents total completion estimate, not time-phased value
   - **Note:** PV is time-phased (changes with control date), BAC is static budget

3. **EAC for Cost Elements with No BAC:**
   - ⚠️ **CLARIFICATION NEEDED:** What should EAC be if cost element has no BAC and no forecast?
   - **Recommendation:** Return `Decimal("0.00")` (consistent with other metrics)

4. **EAC in EVM Metrics Dataclasses:**
   - ⚠️ **DECISION NEEDED:** Should EAC be added to `CostElementEVMMetrics`, `WBEEVMMetrics`, `ProjectEVMMetrics`?
   - **Impact:** Would require updating EVM aggregation service and all route handlers
   - **Recommendation:** Keep EAC separate for now (can be added later if needed)

---

## Risks and Unknown Factors

1. **Fallback Logic Consistency:**
   - **Risk:** Different parts of codebase might implement fallback differently
   - **Mitigation:** Centralize in service layer function

2. **Performance with Many Cost Elements:**
   - **Risk:** Aggregating EAC for projects with many cost elements (>1000) may be slow
   - **Mitigation:** Current aggregation pattern (sum in Python) is acceptable for reasonable sizes
   - **Future:** Could optimize with database aggregation if needed

3. **Forecast Query Performance:**
   - **Risk:** Querying forecasts for many cost elements could be slow
   - **Status:** Already handled in `_get_forecast_eac_map()` (single query with IN clause)
   - **Mitigation:** Current implementation is efficient

4. **EAC vs. Forecast EAC Naming:**
   - **Risk:** Confusion between "forecast EAC" (from Forecast model) and "calculated EAC" (with fallback)
   - **Mitigation:** Clear function naming: `calculate_eac()` implies calculation with fallback

5. **Time Machine Compatibility:**
   - **Risk:** EAC calculation must respect control_date filtering
   - **Status:** ✅ Already handled - forecast queries filter by `forecast_date <= control_date`
   - **Mitigation:** Service function should accept control_date for consistency

---

## Summary

### Feature Description

Create a service layer helper function that calculates Estimate at Completion (EAC) using forecast values as the primary source, with Budget at Completion (BAC) as a fallback when no forecast exists. The function must support cost element, WBE, and project levels, following established aggregation patterns.

### Key Deliverables

1. **Service Layer:** `eac_calculation.py` with calculation and aggregation functions (4-6 hours)
2. **Route Refactoring:** Update route handlers to use service functions (2-3 hours)
3. **Testing:** Comprehensive test coverage (2-3 hours)
4. **Total Estimate:** 6-9 hours

### Recommended Approach

**Approach 1: Service Layer Function with Forecast/BAC Fallback** is the recommended approach, providing clean separation of concerns while following established codebase patterns.

### Next Steps

1. ✅ High-level analysis complete (this document)
2. ⏳ **Await stakeholder feedback** on ambiguities (fallback to BAC vs. PV, EAC in EVM metrics)
3. ⏳ Create detailed implementation plan following TDD discipline
4. ⏳ Implement service layer functions
5. ⏳ Refactor route handlers
6. ⏳ Comprehensive testing and validation

---

**Analysis Complete - Ready for Detailed Planning Phase**
