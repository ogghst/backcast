# Detailed Implementation Plan: EAC Calculation Helper with Forecast/BAC Fallback

**Task:** EAC Calculation Helper Function
**Status:** Planning Phase - Execution Strategy
**Date:** 2025-11-23
**Analysis Code:** 918279
**Plan Code:** 918279

---

## Objective

Implement a service layer helper function that calculates Estimate at Completion (EAC) using forecast values as the primary source, with Budget at Completion (BAC) as a fallback. Add EAC and "forecasted quality" metrics to EVM metrics dataclasses and API responses.

---

## Clarifications Confirmed

1. ✅ **Fallback:** Use BAC (Budget at Completion) when no forecast exists
2. ✅ **EAC for cost elements with no BAC:** Return `Decimal("0.00")`
3. ✅ **EAC in EVM metrics:** Add to `CostElementEVMMetrics`, `WBEEVMMetrics`, `ProjectEVMMetrics`
4. ✅ **Forecasted quality metric:** Percentage showing how much EAC comes from forecasts vs BAC
   - At cost element level: 100% if from forecast, 0% if from BAC
   - At aggregate level: (Sum of forecast EACs) / (Total EAC) × 100

---

## IMPLEMENTATION STEPS

### Step 1: Create EAC Calculation Service Module

**Description:** Create new service file `backend/app/services/eac_calculation.py` with helper functions for calculating EAC with forecast/BAC fallback.

**Test-First Requirement:**
- Create `backend/tests/services/test_eac_calculation.py`
- Write failing tests for:
  - `calculate_cost_element_eac()` with forecast EAC
  - `calculate_cost_element_eac()` with BAC fallback
  - `calculate_cost_element_eac()` with no BAC (returns 0.00)
  - `calculate_forecasted_quality()` at cost element level (100% for forecast, 0% for BAC)
  - `aggregate_eac()` for multiple cost elements
  - `aggregate_forecasted_quality()` for multiple cost elements

**Acceptance Criteria:**
- ✅ Service file `backend/app/services/eac_calculation.py` exists
- ✅ Function `calculate_cost_element_eac(forecast_eac: Decimal | None, budget_bac: Decimal) -> Decimal`:
  - Returns `forecast_eac` if not None
  - Returns `budget_bac` if `forecast_eac` is None
  - Returns `Decimal("0.00")` if both are None/zero
- ✅ Function `calculate_forecasted_quality(forecast_eac: Decimal | None, calculated_eac: Decimal) -> Decimal`:
  - Returns `Decimal("1.0000")` (100%) if `forecast_eac` is not None
  - Returns `Decimal("0.0000")` (0%) if `forecast_eac` is None
  - Returns `Decimal("0.0000")` if `calculated_eac` is 0
- ✅ Function `aggregate_eac(eac_values: Iterable[Decimal]) -> Decimal`:
  - Sums all EAC values
  - Returns `Decimal("0.00")` if empty
  - Quantized to 2 decimal places
- ✅ Function `aggregate_forecasted_quality(forecast_eac_sum: Decimal, total_eac: Decimal) -> Decimal`:
  - Returns `forecast_eac_sum / total_eac` if `total_eac > 0`
  - Returns `Decimal("0.0000")` if `total_eac == 0`
  - Quantized to 4 decimal places
- ✅ All functions use quantization helpers (TWO_PLACES, FOUR_PLACES)
- ✅ All tests pass

**Expected Files:**
- `backend/app/services/eac_calculation.py` (NEW)
- `backend/tests/services/test_eac_calculation.py` (NEW)

**Dependencies:** None (first step)

---

### Step 2: Add EAC and Forecasted Quality to EVM Metrics Dataclasses

**Description:** Extend `CostElementEVMMetrics`, `WBEEVMMetrics`, and `ProjectEVMMetrics` dataclasses to include `eac` and `forecasted_quality` fields.

**Test-First Requirement:**
- Update existing tests in `backend/tests/services/test_evm_aggregation.py` (or create if missing)
- Write failing tests verifying:
  - `CostElementEVMMetrics` includes `eac` and `forecasted_quality` fields
  - `WBEEVMMetrics` includes `eac` and `forecasted_quality` fields
  - `ProjectEVMMetrics` includes `eac` and `forecasted_quality` fields

**Acceptance Criteria:**
- ✅ `CostElementEVMMetrics` dataclass includes:
  - `eac: Decimal` field
  - `forecasted_quality: Decimal` field (4 decimal places, 0.0000 to 1.0000)
- ✅ `WBEEVMMetrics` dataclass includes:
  - `eac: Decimal` field
  - `forecasted_quality: Decimal` field
- ✅ `ProjectEVMMetrics` dataclass includes:
  - `eac: Decimal` field
  - `forecasted_quality: Decimal` field
- ✅ All existing tests still pass (fields added, not breaking changes)
- ✅ New field tests pass

**Expected Files:**
- `backend/app/services/evm_aggregation.py` (MODIFY)
- `backend/tests/services/test_evm_aggregation.py` (MODIFY or CREATE)

**Dependencies:** Step 1 (EAC calculation functions available)

---

### Step 3: Update EVM Aggregation Service to Calculate EAC

**Description:** Modify `get_cost_element_evm_metrics()` and `aggregate_cost_element_metrics()` to calculate and include EAC and forecasted quality.

**Test-First Requirement:**
- Write failing tests in `backend/tests/services/test_evm_aggregation.py`:
  - `get_cost_element_evm_metrics()` returns EAC from forecast when available
  - `get_cost_element_evm_metrics()` returns EAC from BAC when no forecast
  - `get_cost_element_evm_metrics()` returns forecasted_quality = 1.0000 for forecast, 0.0000 for BAC
  - `aggregate_cost_element_metrics()` aggregates EAC correctly
  - `aggregate_cost_element_metrics()` calculates forecasted_quality correctly

**Acceptance Criteria:**
- ✅ `get_cost_element_evm_metrics()` function signature updated to accept:
  - `forecast_eac: Decimal | None` parameter
- ✅ Function calculates EAC using `calculate_cost_element_eac(forecast_eac, budget_bac)`
- ✅ Function calculates forecasted quality using `calculate_forecasted_quality(forecast_eac, eac)`
- ✅ Returns `CostElementEVMMetrics` with `eac` and `forecasted_quality` populated
- ✅ `aggregate_cost_element_metrics()` aggregates EAC using `aggregate_eac()`
- ✅ `aggregate_cost_element_metrics()` calculates forecasted quality using `aggregate_forecasted_quality()`
- ✅ Returns aggregated metrics with `eac` and `forecasted_quality` populated
- ✅ All tests pass

**Expected Files:**
- `backend/app/services/evm_aggregation.py` (MODIFY)
- `backend/tests/services/test_evm_aggregation.py` (MODIFY)

**Dependencies:** Step 1, Step 2

---

### Step 4: Update EVM Indices Models to Include EAC and Forecasted Quality

**Description:** Add `eac` and `forecasted_quality` fields to `EVMIndicesBase` model and all public schemas.

**Test-First Requirement:**
- Write failing tests in `backend/tests/models/test_evm_indices.py` (or create if missing):
  - `EVMIndicesBase` includes `eac` and `forecasted_quality` fields
  - `EVMIndicesCostElementPublic` includes fields
  - `EVMIndicesWBEPublic` includes fields
  - `EVMIndicesProjectPublic` includes fields

**Acceptance Criteria:**
- ✅ `EVMIndicesBase` model includes:
  - `eac: Decimal | None` field (nullable, DECIMAL(15, 2))
  - `forecasted_quality: Decimal | None` field (nullable, DECIMAL(7, 4), 0.0000 to 1.0000)
- ✅ All public schemas (`EVMIndicesCostElementPublic`, `EVMIndicesWBEPublic`, `EVMIndicesProjectPublic`) inherit fields
- ✅ Field descriptions added for API documentation
- ✅ All model tests pass

**Expected Files:**
- `backend/app/models/evm_indices.py` (MODIFY)
- `backend/tests/models/test_evm_indices.py` (MODIFY or CREATE)

**Dependencies:** Step 2, Step 3

---

### Step 5: Update EVM Aggregation Routes to Pass Forecast EAC and Return EAC

**Description:** Modify `evm_aggregation.py` routes to fetch forecast EAC, pass to service functions, and include in API responses.

**Test-First Requirement:**
- Write failing integration tests in `backend/tests/api/routes/test_evm_aggregation.py`:
  - Cost element endpoint returns EAC from forecast
  - Cost element endpoint returns EAC from BAC when no forecast
  - Cost element endpoint returns forecasted_quality
  - WBE endpoint aggregates EAC correctly
  - WBE endpoint calculates forecasted_quality correctly
  - Project endpoint aggregates EAC correctly
  - Project endpoint calculates forecasted_quality correctly

**Acceptance Criteria:**
- ✅ `get_cost_element_evm_metrics_endpoint()`:
  - Fetches forecast EAC using `_get_forecast_eac_map()` helper
  - Passes `forecast_eac` to `get_cost_element_evm_metrics()`
  - Returns `EVMIndicesCostElementPublic` with `eac` and `forecasted_quality` populated
- ✅ `get_wbe_evm_metrics_endpoint()`:
  - Fetches forecast EAC map for all cost elements
  - Passes forecast EAC to `get_cost_element_evm_metrics()` for each cost element
  - Aggregates EAC and forecasted quality correctly
  - Returns `EVMIndicesWBEPublic` with `eac` and `forecasted_quality` populated
- ✅ `get_project_evm_metrics_endpoint()`:
  - Same as WBE but for project level
  - Returns `EVMIndicesProjectPublic` with `eac` and `forecasted_quality` populated
- ✅ All integration tests pass
- ✅ Empty cases handled (no cost elements, no forecasts)

**Expected Files:**
- `backend/app/api/routes/evm_aggregation.py` (MODIFY)
- `backend/tests/api/routes/test_evm_aggregation.py` (MODIFY or CREATE)

**Dependencies:** Step 3, Step 4

---

### Step 6: Update Earned Value Models to Include EAC and Forecasted Quality

**Description:** Add `eac` and `forecasted_quality` fields to `EarnedValueBase` model and all public schemas.

**Test-First Requirement:**
- Write failing tests in `backend/tests/models/test_earned_value.py` (or create if missing):
  - `EarnedValueBase` includes `eac` and `forecasted_quality` fields
  - All public schemas inherit fields

**Acceptance Criteria:**
- ✅ `EarnedValueBase` model includes:
  - `eac: Decimal | None` field (nullable, DECIMAL(15, 2))
  - `forecasted_quality: Decimal | None` field (nullable, DECIMAL(7, 4))
- ✅ All public schemas (`EarnedValueCostElementPublic`, `EarnedValueWBEPublic`, `EarnedValueProjectPublic`) inherit fields
- ✅ All model tests pass

**Expected Files:**
- `backend/app/models/earned_value.py` (MODIFY)
- `backend/tests/models/test_earned_value.py` (MODIFY or CREATE)

**Dependencies:** Step 1, Step 4

---

### Step 7: Update Earned Value Routes to Calculate and Return EAC

**Description:** Modify `earned_value.py` routes to calculate EAC with fallback and include in API responses.

**Test-First Requirement:**
- Write failing integration tests in `backend/tests/api/routes/test_earned_value.py`:
  - Cost element endpoint returns EAC from forecast
  - Cost element endpoint returns EAC from BAC when no forecast
  - Cost element endpoint returns forecasted_quality
  - WBE endpoint aggregates EAC correctly
  - Project endpoint aggregates EAC correctly

**Acceptance Criteria:**
- ✅ `get_cost_element_earned_value()`:
  - Fetches forecast EAC using `_get_forecast_eac_map()`
  - Calculates EAC using `calculate_cost_element_eac(forecast_eac, budget_bac)`
  - Calculates forecasted quality using `calculate_forecasted_quality(forecast_eac, eac)`
  - Returns `EarnedValueCostElementPublic` with `eac` and `forecasted_quality` populated
- ✅ `get_wbe_earned_value()`:
  - Fetches forecast EAC map
  - Calculates EAC for each cost element
  - Aggregates EAC and forecasted quality
  - Returns `EarnedValueWBEPublic` with `eac` and `forecasted_quality` populated
- ✅ `get_project_earned_value()`:
  - Same as WBE but for project level
  - Returns `EarnedValueProjectPublic` with `eac` and `forecasted_quality` populated
- ✅ All integration tests pass

**Expected Files:**
- `backend/app/api/routes/earned_value.py` (MODIFY)
- `backend/tests/api/routes/test_earned_value.py` (MODIFY)

**Dependencies:** Step 1, Step 6

---

### Step 8: Regenerate Frontend OpenAPI Client

**Description:** Regenerate frontend client to include new EAC and forecasted_quality fields in type definitions.

**Test-First Requirement:**
- Verify frontend client types include new fields (manual check)

**Acceptance Criteria:**
- ✅ OpenAPI client regenerated successfully
- ✅ Type definitions include `eac` and `forecasted_quality` fields in:
  - `EVMIndicesCostElementPublic`
  - `EVMIndicesWBEPublic`
  - `EVMIndicesProjectPublic`
  - `EarnedValueCostElementPublic`
  - `EarnedValueWBEPublic`
  - `EarnedValueProjectPublic`
- ✅ No TypeScript compilation errors

**Expected Files:**
- `frontend/src/client/types.gen.ts` (REGENERATED)
- `frontend/src/client/schemas.gen.ts` (REGENERATED)
- `frontend/src/client/sdk.gen.ts` (REGENERATED)

**Dependencies:** Step 4, Step 6, Step 5, Step 7

---

### Step 9: Update Frontend Components to Display Forecasted Quality (Optional)

**Description:** Optionally update frontend components to display forecasted quality metric. This is optional and can be done in a separate task.

**Test-First Requirement:**
- N/A (optional step)

**Acceptance Criteria:**
- ✅ If implemented: Frontend components can access `forecasted_quality` from API responses
- ✅ If implemented: Display format follows existing percentage patterns

**Expected Files:**
- `frontend/src/components/Projects/EarnedValueSummary.tsx` (OPTIONAL MODIFY)
- Other components as needed (OPTIONAL)

**Dependencies:** Step 8

---

## TDD DISCIPLINE RULES

1. **Failing Test First:** Every step must start with a failing test that defines the expected behavior
2. **Red-Green-Refactor Cycle:**
   - Red: Write failing test
   - Green: Write minimal code to make test pass
   - Refactor: Improve code while keeping tests green
3. **Maximum Iterations:** Maximum 3 attempts per step before stopping to ask for help
4. **Test Coverage:** All new functions must have unit tests. All route changes must have integration tests
5. **Behavior Verification:** Tests must verify behavior, not just compilation or structure

---

## PROCESS CHECKPOINTS

### Checkpoint 1: After Step 3 (EVM Aggregation Service Updated)
**Questions:**
- Does the EAC calculation logic work correctly for all cases?
- Are the forecasted quality calculations correct?
- Should we continue with route updates?

### Checkpoint 2: After Step 5 (EVM Aggregation Routes Updated)
**Questions:**
- Do API responses include EAC and forecasted_quality correctly?
- Are integration tests passing?
- Should we continue with earned value routes?

### Checkpoint 3: After Step 8 (Frontend Client Regenerated)
**Questions:**
- Are all type definitions correct?
- Should we proceed with optional frontend updates?
- Is the implementation complete for backend requirements?

---

## SCOPE BOUNDARIES

**In Scope:**
- ✅ EAC calculation with forecast/BAC fallback
- ✅ Forecasted quality metric calculation
- ✅ Adding EAC and forecasted_quality to EVM metrics dataclasses
- ✅ Adding EAC and forecasted_quality to API responses
- ✅ Service layer functions for EAC calculation
- ✅ Aggregation logic for WBE and project levels

**Out of Scope:**
- ❌ Frontend UI updates (optional, separate task)
- ❌ Historical EAC tracking (only current EAC)
- ❌ EAC calculation formulas beyond forecast/BAC fallback
- ❌ Performance optimizations (unless critical)

**If Useful Improvements Found:**
- Ask user for confirmation before implementing
- Document in checkpoints for discussion

---

## ROLLBACK STRATEGY

### Safe Rollback Points

1. **After Step 1:** Service functions created but not integrated
   - Rollback: Delete `eac_calculation.py` and tests
   - Alternative: Keep service functions, integrate differently

2. **After Step 3:** EVM service updated but routes not changed
   - Rollback: Remove EAC fields from dataclasses, revert service changes
   - Alternative: Keep service changes, update routes differently

3. **After Step 5:** Routes updated but models not changed
   - Rollback: Revert route changes, keep service layer
   - Alternative: Update models first, then routes

### Alternative Approaches

If current approach fails:
1. **Simpler Approach:** Keep EAC calculation in route layer (violates service pattern but faster)
2. **Different Service Structure:** Create separate EAC service instead of extending EVM service
3. **Phased Approach:** Implement EAC first, add forecasted_quality later

---

## ESTIMATED COMPLEXITY

- **Step 1:** 2-3 hours (service functions + tests)
- **Step 2:** 1 hour (dataclass updates + tests)
- **Step 3:** 2-3 hours (service integration + tests)
- **Step 4:** 1 hour (model updates + tests)
- **Step 5:** 3-4 hours (route updates + integration tests)
- **Step 6:** 1 hour (model updates + tests)
- **Step 7:** 2-3 hours (route updates + integration tests)
- **Step 8:** 0.5 hours (regeneration)
- **Step 9:** 1-2 hours (optional frontend)

**Total Estimated Time:** 13-18 hours

---

## RISK MITIGATION

1. **Forecast Query Performance:** Already handled efficiently with batch queries
2. **Type Compatibility:** Regenerate client after all backend changes
3. **Breaking Changes:** All new fields are nullable, backward compatible
4. **Test Coverage:** Comprehensive tests at each step prevent regressions

---

**Plan Complete - Ready for Implementation**
