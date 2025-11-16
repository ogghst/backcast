# Implementation Plan: E4-004 EVM Variance Calculations (CV, SV)

**Task:** E4-004 - Variance Calculations
**Sprint:** Sprint 4 - Earned Value Recording and Core EVM Calculations
**Status:** Planning Complete - Ready for Implementation
**Date:** 2025-11-16
**Current Time:** 22:24 CET (Europe/Rome)

---

## WORKING AGREEMENTS ACKNOWLEDGMENT

✅ **Test-Driven Development (TDD):** All code changes must be preceded by failing tests
✅ **Incremental Change:** Small, atomic commits (<100 lines, <5 files target)
✅ **Architectural Respect:** Follow existing patterns and abstractions (extend E4-003 EVM indices patterns)
✅ **No Code Duplication:** Reuse existing implementations where possible

---

## Objective

Implement EVM Variance Calculations engine computing Cost Variance (CV) and Schedule Variance (SV) at project and WBE levels (cost element optional) by extending the existing EVM indices service and router. This follows the E4-003 EVM Performance Indices pattern and provides absolute dollar amounts for cost and schedule deviations, complementing performance indices (CPI, SPI).

---

## Requirements Summary

**From Analysis Document:**
- ✅ **Recommended Approach:** Extend EVM Indices Service and Router (Approach A)
- ✅ **Required Levels:** Project and WBE levels (cost element level optional in MVP)
- ✅ **Business Rules:**
  - CV = EV - AC (negative = over-budget, positive = under-budget, zero = on-budget)
  - SV = EV - PV (negative = behind-schedule, positive = ahead-of-schedule, zero = on-schedule)
- ✅ **Precision:** 2 decimal places (monetary values, matching PV/EV/AC)
- ✅ **Input Sources:** Reuse existing `_get_wbe_evm_inputs()` and `_get_project_evm_inputs()` helpers
- ✅ **Time-Machine Integration:** All variances computed as-of control date (same as indices)

**Key Business Rules:**
- CV = EV - AC (always defined, can be negative, zero, or positive)
- SV = EV - PV (always defined, can be negative, zero, or positive)
- Variances computed at project and WBE levels using aggregated PV, EV, AC
- All calculations respect time-machine control date
- Backward compatibility: Extend `EVMIndicesBase` model with optional variance fields

---

## Implementation Approach

**Strategy:** Incremental Backend-First TDD (extend E4-003 pattern)
1. **Phase 1:** Service layer - Add CV and SV calculation functions (TDD: failing tests first)
2. **Phase 2:** Response models - Extend `EVMIndicesBase` with variance fields
3. **Phase 3:** API routes - Update existing endpoints to compute and return variances
4. **Phase 4:** Integration testing - Verify end-to-end behavior and backward compatibility
5. **Phase 5:** OpenAPI client regeneration - Update frontend types

**Architecture Pattern:**
- Service layer: Pure functions (no database access) - extend `backend/app/services/evm_indices.py`
- API layer: Update existing FastAPI routes - extend `backend/app/api/routes/evm_indices.py`
- Models layer: Extend response schemas - extend `backend/app/models/evm_indices.py`
- Tests: Service unit tests + API integration tests

---

## IMPLEMENTATION STEPS

### PHASE 1: Service Layer (Backend)

#### Step 1.1: Add CV Calculation Function

**Objective:** Create function to calculate Cost Variance (CV) = EV - AC with proper Decimal handling.

**Acceptance Criteria:**
- ✅ `calculate_cost_variance()` function exists in `evm_indices.py`
- ✅ Returns `Decimal` quantized to 2 decimal places
- ✅ Handles all cases: positive, negative, zero
- ✅ Formula: CV = EV - AC
- ✅ No edge cases requiring None (always defined)

**Test-First Requirement:**
- Create test: `test_calculate_cost_variance_under_budget()` - EV=100, AC=80 → CV=20.00
- Create test: `test_calculate_cost_variance_over_budget()` - EV=80, AC=100 → CV=-20.00
- Create test: `test_calculate_cost_variance_on_budget()` - EV=100, AC=100 → CV=0.00
- Create test: `test_calculate_cost_variance_zero_ev_positive_ac()` - EV=0, AC=50 → CV=-50.00
- Create test: `test_calculate_cost_variance_quantization()` - Verify 2 decimal places
- Create test: `test_calculate_cost_variance_negative_values()` - Handle negative EV/AC appropriately

**Files to Modify:**
- `backend/app/services/evm_indices.py`
- `backend/tests/services/test_evm_indices.py`

**Dependencies:**
- None (service module already exists from E4-003)

**Estimated Time:** 1-2 hours

---

#### Step 1.2: Add SV Calculation Function

**Objective:** Create function to calculate Schedule Variance (SV) = EV - PV with proper Decimal handling.

**Acceptance Criteria:**
- ✅ `calculate_schedule_variance()` function exists in `evm_indices.py`
- ✅ Returns `Decimal` quantized to 2 decimal places
- ✅ Handles all cases: positive, negative, zero
- ✅ Formula: SV = EV - PV
- ✅ No edge cases requiring None (always defined)

**Test-First Requirement:**
- Create test: `test_calculate_schedule_variance_ahead_schedule()` - EV=100, PV=80 → SV=20.00
- Create test: `test_calculate_schedule_variance_behind_schedule()` - EV=80, PV=100 → SV=-20.00
- Create test: `test_calculate_schedule_variance_on_schedule()` - EV=100, PV=100 → SV=0.00
- Create test: `test_calculate_schedule_variance_zero_ev_positive_pv()` - EV=0, PV=50 → SV=-50.00
- Create test: `test_calculate_schedule_variance_quantization()` - Verify 2 decimal places
- Create test: `test_calculate_schedule_variance_negative_values()` - Handle negative EV/PV appropriately

**Files to Modify:**
- `backend/app/services/evm_indices.py`
- `backend/tests/services/test_evm_indices.py`

**Dependencies:**
- Step 1.1

**Estimated Time:** 1-2 hours

---

### PHASE 2: Response Models (Backend)

#### Step 2.1: Extend EVMIndicesBase Model with Variance Fields

**Objective:** Add `cost_variance` and `schedule_variance` fields to `EVMIndicesBase` model with proper types and documentation.

**Acceptance Criteria:**
- ✅ `cost_variance` field added to `EVMIndicesBase`
- ✅ `schedule_variance` field added to `EVMIndicesBase`
- ✅ Fields are `Decimal` type with `DECIMAL(15, 2)` precision (matching PV/EV/AC)
- ✅ Fields are required (not optional) with default `Decimal("0.00")` for backward compatibility
- ✅ Field descriptions document formulas and interpretation (negative/positive meanings)
- ✅ Model validation passes
- ✅ No breaking changes to existing `EVMIndicesWBEPublic` and `EVMIndicesProjectPublic` (they inherit fields)

**Test-First Requirement:**
- Create test: `test_evm_indices_base_with_variances()` - Verify model can be instantiated with CV/SV
- Create test: `test_evm_indices_base_defaults()` - Verify default values are 0.00
- Create test: `test_evm_indices_base_quantization()` - Verify 2 decimal place precision
- Update existing model tests to verify backward compatibility (existing indices still work)

**Files to Modify:**
- `backend/app/models/evm_indices.py`
- `backend/tests/models/test_evm_indices.py` (if exists) or add to service tests

**Dependencies:**
- Step 1.2

**Estimated Time:** 1 hour

---

### PHASE 3: API Routes (Backend)

#### Step 3.1: Update WBE EVM Indices Endpoint

**Objective:** Modify `get_wbe_evm_indices()` endpoint to compute and return CV and SV alongside existing indices.

**Acceptance Criteria:**
- ✅ `get_wbe_evm_indices()` computes CV and SV using service functions
- ✅ Response includes `cost_variance` and `schedule_variance` fields
- ✅ CV and SV use same PV/EV/AC inputs as CPI/SPI (consistency)
- ✅ Endpoint still returns all existing fields (CPI, SPI, TCPI, PV, EV, AC, BAC)
- ✅ No breaking changes to response structure (only adds fields)

**Test-First Requirement:**
- Create test: `test_get_wbe_evm_indices_includes_variances()` - Verify CV and SV in response
- Create test: `test_get_wbe_evm_indices_variance_calculation()` - Verify CV=EV-AC, SV=EV-PV
- Create test: `test_get_wbe_evm_indices_backward_compatibility()` - Verify existing fields still present
- Create test: `test_get_wbe_evm_indices_negative_variances()` - Verify negative values handled correctly
- Update existing WBE endpoint tests to verify new fields

**Files to Modify:**
- `backend/app/api/routes/evm_indices.py`
- `backend/tests/api/routes/test_evm_indices.py`

**Dependencies:**
- Step 2.1

**Estimated Time:** 1-2 hours

---

#### Step 3.2: Update Project EVM Indices Endpoint

**Objective:** Modify `get_project_evm_indices()` endpoint to compute and return CV and SV alongside existing indices.

**Acceptance Criteria:**
- ✅ `get_project_evm_indices()` computes CV and SV using service functions
- ✅ Response includes `cost_variance` and `schedule_variance` fields
- ✅ CV and SV use same PV/EV/AC inputs as CPI/SPI (consistency)
- ✅ Endpoint still returns all existing fields (CPI, SPI, TCPI, PV, EV, AC, BAC)
- ✅ No breaking changes to response structure (only adds fields)

**Test-First Requirement:**
- Create test: `test_get_project_evm_indices_includes_variances()` - Verify CV and SV in response
- Create test: `test_get_project_evm_indices_variance_calculation()` - Verify CV=EV-AC, SV=EV-PV
- Create test: `test_get_project_evm_indices_backward_compatibility()` - Verify existing fields still present
- Create test: `test_get_project_evm_indices_negative_variances()` - Verify negative values handled correctly
- Update existing project endpoint tests to verify new fields

**Files to Modify:**
- `backend/app/api/routes/evm_indices.py`
- `backend/tests/api/routes/test_evm_indices.py`

**Dependencies:**
- Step 3.1

**Estimated Time:** 1-2 hours

---

### PHASE 4: Integration Testing

#### Step 4.1: End-to-End Integration Tests

**Objective:** Verify variances work correctly with time-machine control dates and hierarchical aggregation.

**Acceptance Criteria:**
- ✅ Integration test: WBE with multiple cost elements - variances aggregate correctly
- ✅ Integration test: Project with multiple WBEs - variances aggregate correctly
- ✅ Integration test: Time-machine control date filtering - variances respect control date
- ✅ Integration test: Variances and indices use same inputs - consistency verified
- ✅ Integration test: Edge cases combination - zero values, negative values, all combinations

**Test-First Requirement:**
- Create test: `test_wbe_variance_integration_multiple_elements()` - Multiple cost elements aggregation
- Create test: `test_project_variance_integration_multiple_wbes()` - Multiple WBEs aggregation
- Create test: `test_variance_time_machine_control_date()` - Control date filtering
- Create test: `test_variance_indices_consistency()` - Same inputs produce consistent results
- Create test: `test_variance_edge_cases_combination()` - All edge cases together

**Files to Modify:**
- `backend/tests/api/routes/test_evm_indices.py`

**Dependencies:**
- Step 3.2

**Estimated Time:** 2-3 hours

---

### PHASE 5: OpenAPI Client Regeneration

#### Step 5.1: Regenerate OpenAPI Client

**Objective:** Regenerate frontend OpenAPI client to include new variance fields in TypeScript types.

**Acceptance Criteria:**
- ✅ OpenAPI schema includes `cost_variance` and `schedule_variance` fields
- ✅ Frontend client regenerated with updated types
- ✅ TypeScript compilation passes
- ✅ No breaking changes to existing client code (fields are additive)

**Test-First Requirement:**
- Verify OpenAPI schema: `GET /api/v1/projects/{project_id}/evm-indices` includes variance fields
- Verify OpenAPI schema: `GET /api/v1/projects/{project_id}/evm-indices/wbes/{wbe_id}` includes variance fields
- Run frontend TypeScript build to verify no type errors

**Files to Modify:**
- Frontend OpenAPI client (auto-generated)
- May need to update `backend/app/main.py` or OpenAPI config if schema generation needs adjustment

**Dependencies:**
- Step 4.1

**Estimated Time:** 15-30 minutes

---

## TDD DISCIPLINE RULES

1. **Failing Test First:** Every production code change must be preceded by a failing test that demonstrates the required behavior.
2. **Red-Green-Refactor Cycle:**
   - **Red:** Write failing test (verify it fails for the right reason)
   - **Green:** Write minimal code to make test pass
   - **Refactor:** Improve code while keeping tests green
3. **Maximum Iterations:** Maximum 3 attempts per step before stopping to ask for help.
4. **Test Quality:** Tests must verify behavior, not just compilation. Use assertions that check actual values and edge cases.
5. **Incremental Commits:** Each step should result in a small, atomic commit (<100 lines, <5 files target).

---

## PROCESS CHECKPOINTS

### Checkpoint 1: After Phase 1 (Service Layer)
**Pause and ask:**
- "Should we continue with the plan as-is?"
- "Do the CV and SV calculation functions match the expected behavior?"
- "Have any assumptions about edge cases been invalidated?"

### Checkpoint 2: After Phase 2 (Response Models)
**Pause and ask:**
- "Does the model extension maintain backward compatibility?"
- "Are the field types and defaults appropriate?"
- "Should variance fields be optional or required?"

### Checkpoint 3: After Phase 3 (API Routes)
**Pause and ask:**
- "Do the endpoints return variances correctly?"
- "Is backward compatibility maintained for existing clients?"
- "Are variances consistent with indices (same inputs)?"

### Checkpoint 4: After Phase 4 (Integration Testing)
**Pause and ask:**
- "Do all integration tests pass?"
- "Are there any performance concerns with the implementation?"
- "Should we proceed to client regeneration?"

---

## SCOPE BOUNDARIES

**In Scope:**
- ✅ CV and SV calculation functions (service layer)
- ✅ Extending `EVMIndicesBase` model with variance fields
- ✅ Updating existing WBE and project EVM indices endpoints
- ✅ Backward compatibility with existing API consumers
- ✅ Integration tests for variances
- ✅ OpenAPI client regeneration

**Out of Scope (Future Work):**
- ❌ Cost element level variance endpoints (optional in MVP, defer to later)
- ❌ Frontend UI components for displaying variances (E4-006)
- ❌ Variance trend analysis or historical tracking (E4-008)
- ❌ Variance export functionality (E4-010)
- ❌ Additional variance metrics (VAC - Variance at Completion, defer to E5-006)

**If Useful Improvements Found:**
- Ask user for confirmation before implementing
- Document in notes for future consideration

---

## ROLLBACK STRATEGY

### Safe Rollback Points

1. **After Phase 1 (Service Layer):**
   - **Rollback:** Revert changes to `evm_indices.py` service
   - **Impact:** Low - service functions are isolated, no API changes yet
   - **Alternative:** Keep service functions but don't expose via API yet

2. **After Phase 2 (Response Models):**
   - **Rollback:** Revert model changes, make variance fields optional or remove
   - **Impact:** Medium - may require API route adjustments
   - **Alternative:** Make variance fields optional with None defaults

3. **After Phase 3 (API Routes):**
   - **Rollback:** Revert API route changes, keep service functions for future use
   - **Impact:** Medium - clients may have started using new fields
   - **Alternative:** Keep routes but return default 0.00 for variances

4. **After Phase 4 (Integration Tests):**
   - **Rollback:** Remove integration tests, keep unit tests
   - **Impact:** Low - tests don't affect production code
   - **Alternative:** Comment out failing integration tests temporarily

### Alternative Approaches if Current Approach Fails

1. **If Backward Compatibility Issues:**
   - Make variance fields optional (default None) instead of required
   - Create separate variance endpoints instead of extending indices endpoints
   - Version API endpoints (v1 vs v2)

2. **If Performance Issues:**
   - Cache variance calculations
   - Precompute variances in background jobs
   - Optimize input retrieval helpers

3. **If Testing Complexity:**
   - Simplify test scenarios
   - Focus on happy path first, add edge cases incrementally
   - Use property-based testing for edge cases

---

## ESTIMATED EFFORT

**Total Estimated Time:** 8-12 hours

- Phase 1 (Service Layer): 2-4 hours
- Phase 2 (Response Models): 1 hour
- Phase 3 (API Routes): 2-4 hours
- Phase 4 (Integration Testing): 2-3 hours
- Phase 5 (Client Regeneration): 15-30 minutes

**Breakdown by Step:**
- Step 1.1 (CV Function): 1-2 hours
- Step 1.2 (SV Function): 1-2 hours
- Step 2.1 (Model Extension): 1 hour
- Step 3.1 (WBE Endpoint): 1-2 hours
- Step 3.2 (Project Endpoint): 1-2 hours
- Step 4.1 (Integration Tests): 2-3 hours
- Step 5.1 (Client Regeneration): 15-30 minutes

---

## SUCCESS CRITERIA

**Implementation is complete when:**
- ✅ All service layer tests pass (CV and SV functions)
- ✅ All API route tests pass (WBE and project endpoints)
- ✅ All integration tests pass (time-machine, aggregation, consistency)
- ✅ OpenAPI schema includes variance fields
- ✅ Frontend client regenerated successfully
- ✅ TypeScript compilation passes
- ✅ Backward compatibility verified (existing API consumers unaffected)
- ✅ Code follows existing patterns (E4-003 style)
- ✅ No linter errors
- ✅ All tests passing: `pytest backend/tests/services/test_evm_indices.py backend/tests/api/routes/test_evm_indices.py`

---

## NOTES

- **Backward Compatibility:** Extending `EVMIndicesBase` with required fields (default 0.00) should be safe since existing clients will receive the new fields with default values. If concerns arise, we can make fields optional.
- **Precision:** Variances use 2 decimal places (monetary) vs 4 decimal places (indices) - this matches PV/EV/AC precision.
- **Consistency:** Variances and indices must use the same PV/EV/AC inputs to ensure consistency. This is guaranteed by reusing `_get_wbe_evm_inputs()` and `_get_project_evm_inputs()` helpers.
- **Future Work:** Cost element level variances can be added later if needed, following the same pattern.

---

**Reference:** This plan extends the E4-003 EVM Performance Indices implementation and follows the same architectural patterns. Analysis document: `docs/analysis/e4-004-918274-evm-variance-calculations-analysis.md`.
