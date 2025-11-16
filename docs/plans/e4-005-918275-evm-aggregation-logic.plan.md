# Implementation Plan: E4-005 EVM Aggregation Logic

**Task:** E4-005 - EVM Aggregation Logic
**Sprint:** Sprint 4 - Earned Value Recording and Core EVM Calculations
**Status:** Planning Complete - Ready for Implementation
**Date:** 2025-11-16
**Current Time:** 22:53 CET (Europe/Rome)

---

## WORKING AGREEMENTS ACKNOWLEDGMENT

✅ **Test-Driven Development (TDD):** All code changes must be preceded by failing tests
✅ **Incremental Change:** Small, atomic commits (<100 lines, <5 files target)
✅ **Architectural Respect:** Follow existing patterns and abstractions (reuse existing services)
✅ **No Code Duplication:** Eliminate duplication in `evm_indices.py` by reusing `planned_value`, `earned_value`, and cost aggregation services

---

## Objective

Create a unified EVM aggregation endpoint that provides all EVM metrics (PV, EV, AC, BAC, CPI, SPI, TCPI, CV, SV) at cost element, WBE, and project levels. Refactor existing `evm_indices.py` to reuse existing services instead of duplicating calculation logic. Deprecate separate endpoints (`planned_value`, `earned_value`, existing `evm_indices`) in favor of the unified endpoint.

---

## Requirements Summary

**From User Clarifications:**
- ✅ Create new unified endpoint for EVM metrics
- ✅ Include cost element level aggregation
- ✅ Deprecate existing separate endpoints (planned_value, earned_value, evm_indices)
- ✅ Use EVMIndices models in unified endpoint
- ✅ No caching needed

**From Analysis Document:**
- ✅ Eliminate code duplication in `evm_indices.py` helpers (`_get_wbe_evm_inputs`, `_get_project_evm_inputs`)
- ✅ Reuse existing `planned_value`, `earned_value`, and cost aggregation services
- ✅ Provide hierarchical aggregation: cost element → WBE → project
- ✅ All metrics: PV, EV, AC, BAC, CPI, SPI, TCPI, CV, SV
- ✅ Time-machine control date support

**Key Business Rules:**
- CPI = EV / AC (None when AC = 0)
- SPI = EV / PV (None when PV = 0)
- TCPI = (BAC - EV) / (BAC - AC) ('overrun' when BAC ≤ AC)
- CV = EV - AC (always defined)
- SV = EV - PV (always defined)
- All calculations respect time-machine control date

---

## Implementation Approach

**Strategy:** Incremental Backend-First TDD with Refactoring
1. **Phase 1:** Create cost element level EVMIndices model
2. **Phase 2:** Create unified aggregation service that reuses existing services
3. **Phase 3:** Create unified API endpoints (cost element, WBE, project levels)
4. **Phase 4:** Refactor existing evm_indices.py to use unified service
5. **Phase 5:** Deprecate separate endpoints (planned_value, earned_value, old evm_indices)
6. **Phase 6:** Integration testing and verification

**Architecture Pattern:**
- Service layer: Unified aggregation service reusing existing services - `backend/app/services/evm_aggregation.py`
- API layer: Unified FastAPI routes - `backend/app/api/routes/evm_aggregation.py` (or extend `evm_indices.py`)
- Models layer: Extend existing EVMIndices models - `backend/app/models/evm_indices.py`
- Refactoring: Update `evm_indices.py` to use unified service, mark old endpoints as deprecated

---

## IMPLEMENTATION STEPS

### PHASE 1: Cost Element Level Model

#### Step 1.1: Add Cost Element EVMIndices Model

**Objective:** Create `EVMIndicesCostElementPublic` model following existing pattern.

**Acceptance Criteria:**
- ✅ `EVMIndicesCostElementPublic` class exists in `backend/app/models/evm_indices.py`
- ✅ Extends `EVMIndicesBase`
- ✅ Includes `cost_element_id: uuid.UUID` field
- ✅ Model exported in `backend/app/models/__init__.py`
- ✅ No syntax errors, imports correctly

**Test-First Requirement:**
- None (model definition, no business logic)

**Files to Modify:**
- `backend/app/models/evm_indices.py`
- `backend/app/models/__init__.py`

**Dependencies:**
- None

**Estimated Time:** 15 minutes

---

### PHASE 2: Unified Aggregation Service

#### Step 2.1: Create Unified Aggregation Service Module

**Objective:** Create service module structure with imports from existing services.

**Acceptance Criteria:**
- ✅ `backend/app/services/evm_aggregation.py` exists
- ✅ Imports from `planned_value`, `earned_value`, `evm_indices`, and cost aggregation services
- ✅ File imports correctly (no syntax errors)
- ✅ Follows existing service module patterns

**Test-First Requirement:**
- None (infrastructure setup)

**Files to Create:**
- `backend/app/services/evm_aggregation.py`

**Dependencies:**
- None

**Estimated Time:** 15 minutes

---

#### Step 2.2: Implement Cost Element EVM Metrics Function

**Objective:** Create function to get all EVM metrics for a single cost element by reusing existing services.

**Acceptance Criteria:**
- ✅ `get_cost_element_evm_metrics()` function exists
- ✅ Takes `cost_element`, `schedule`, `entry`, `cost_registrations`, `control_date` as parameters
- ✅ Reuses `calculate_cost_element_planned_value()` from `planned_value` service
- ✅ Reuses `calculate_cost_element_earned_value()` from `earned_value` service
- ✅ Calculates AC from cost_registrations (sum of amounts)
- ✅ Calculates BAC from cost_element.budget_bac
- ✅ Calculates CPI, SPI, TCPI using existing `evm_indices` service functions
- ✅ Calculates CV, SV using existing `evm_indices` service functions
- ✅ Returns dataclass with all metrics (PV, EV, AC, BAC, CPI, SPI, TCPI, CV, SV)
- ✅ Handles None values correctly (schedule=None, entry=None, empty cost_registrations)

**Test-First Requirement:**
- Create failing test: `test_get_cost_element_evm_metrics_normal_case()` in `backend/tests/services/test_evm_aggregation.py`
- Test should verify all metrics are calculated correctly
- Test should verify None handling for missing schedule/entry

**Files to Create/Modify:**
- `backend/app/services/evm_aggregation.py`
- `backend/tests/services/test_evm_aggregation.py`

**Dependencies:**
- Step 2.1

**Estimated Time:** 1-2 hours

---

#### Step 2.3: Implement WBE EVM Metrics Aggregation Function

**Objective:** Create function to aggregate EVM metrics for a WBE by reusing existing aggregation services.

**Acceptance Criteria:**
- ✅ `get_wbe_evm_metrics()` function exists
- ✅ Takes `session`, `wbe_id`, `control_date` as parameters
- ✅ Queries cost elements for WBE (respecting time-machine cutoff)
- ✅ Gets schedules using existing `_get_schedule_map()` pattern (or calls planned_value service)
- ✅ Gets entries using existing `_get_entry_map()` pattern (or calls earned_value service)
- ✅ Gets cost registrations using existing cost aggregation patterns
- ✅ Calls `get_cost_element_evm_metrics()` for each cost element
- ✅ Aggregates PV, EV, AC, BAC using existing aggregation functions
- ✅ Calculates CPI, SPI, TCPI from aggregated values
- ✅ Calculates CV, SV from aggregated values
- ✅ Returns dataclass with all aggregated metrics
- ✅ Handles empty WBE (no cost elements) correctly

**Test-First Requirement:**
- Create failing test: `test_get_wbe_evm_metrics_normal_case()` in `backend/tests/services/test_evm_aggregation.py`
- Create failing test: `test_get_wbe_evm_metrics_empty_wbe()` in `backend/tests/services/test_evm_aggregation.py`
- Tests should verify aggregation matches manual calculation

**Files to Modify:**
- `backend/app/services/evm_aggregation.py`
- `backend/tests/services/test_evm_aggregation.py`

**Dependencies:**
- Step 2.2

**Estimated Time:** 2-3 hours

---

#### Step 2.4: Implement Project EVM Metrics Aggregation Function

**Objective:** Create function to aggregate EVM metrics for a project by aggregating from WBEs.

**Acceptance Criteria:**
- ✅ `get_project_evm_metrics()` function exists
- ✅ Takes `session`, `project_id`, `control_date` as parameters
- ✅ Queries WBEs for project (respecting time-machine cutoff)
- ✅ Calls `get_wbe_evm_metrics()` for each WBE
- ✅ Aggregates PV, EV, AC, BAC across all WBEs
- ✅ Calculates CPI, SPI, TCPI from aggregated values
- ✅ Calculates CV, SV from aggregated values
- ✅ Returns dataclass with all aggregated metrics
- ✅ Handles empty project (no WBEs) correctly

**Test-First Requirement:**
- Create failing test: `test_get_project_evm_metrics_normal_case()` in `backend/tests/services/test_evm_aggregation.py`
- Create failing test: `test_get_project_evm_metrics_empty_project()` in `backend/tests/services/test_evm_aggregation.py`
- Tests should verify aggregation matches manual calculation

**Files to Modify:**
- `backend/app/services/evm_aggregation.py`
- `backend/tests/services/test_evm_aggregation.py`

**Dependencies:**
- Step 2.3

**Estimated Time:** 2-3 hours

---

### PHASE 3: Unified API Endpoints

#### Step 3.1: Create Unified EVM Aggregation Router

**Objective:** Create new API router for unified EVM metrics endpoints.

**Acceptance Criteria:**
- ✅ `backend/app/api/routes/evm_aggregation.py` exists (or extend `evm_indices.py`)
- ✅ Router uses prefix `/projects` and tag `evm-metrics`
- ✅ Imports unified aggregation service
- ✅ Imports EVMIndices models (including new cost element model)
- ✅ Imports dependencies: `SessionDep`, `CurrentUser`, `get_time_machine_control_date`
- ✅ File imports correctly (no syntax errors)

**Test-First Requirement:**
- None (infrastructure setup)

**Files to Create:**
- `backend/app/api/routes/evm_aggregation.py` (OR extend `backend/app/api/routes/evm_indices.py`)

**Dependencies:**
- Phase 2 complete

**Estimated Time:** 15 minutes

---

#### Step 3.2: Implement Cost Element Level Endpoint

**Objective:** Create API endpoint for cost element level EVM metrics.

**Acceptance Criteria:**
- ✅ Endpoint: `GET /projects/{project_id}/evm-metrics/cost-elements/{cost_element_id}`
- ✅ Response model: `EVMIndicesCostElementPublic`
- ✅ Validates project exists
- ✅ Validates cost element exists and belongs to project
- ✅ Validates cost element created_at <= control_date (time-machine)
- ✅ Calls `get_cost_element_evm_metrics()` from unified service
- ✅ Returns all EVM metrics (PV, EV, AC, BAC, CPI, SPI, TCPI, CV, SV)
- ✅ Handles 404 for non-existent cost element
- ✅ Handles 404 for cost element created after control_date

**Test-First Requirement:**
- Create failing test: `test_get_cost_element_evm_metrics_endpoint_normal_case()` in `backend/tests/api/routes/test_evm_aggregation.py`
- Create failing test: `test_get_cost_element_evm_metrics_endpoint_not_found()` in `backend/tests/api/routes/test_evm_aggregation.py`
- Create failing test: `test_get_cost_element_evm_metrics_endpoint_time_machine()` in `backend/tests/api/routes/test_evm_aggregation.py`

**Files to Modify:**
- `backend/app/api/routes/evm_aggregation.py` (or `evm_indices.py`)
- `backend/tests/api/routes/test_evm_aggregation.py` (or extend `test_evm_indices.py`)

**Dependencies:**
- Step 3.1, Step 2.2

**Estimated Time:** 1-2 hours

---

#### Step 3.3: Implement WBE Level Endpoint

**Objective:** Create API endpoint for WBE level EVM metrics.

**Acceptance Criteria:**
- ✅ Endpoint: `GET /projects/{project_id}/evm-metrics/wbes/{wbe_id}`
- ✅ Response model: `EVMIndicesWBEPublic`
- ✅ Validates project exists
- ✅ Validates WBE exists and belongs to project
- ✅ Validates WBE created_at <= control_date (time-machine)
- ✅ Calls `get_wbe_evm_metrics()` from unified service
- ✅ Returns all EVM metrics (PV, EV, AC, BAC, CPI, SPI, TCPI, CV, SV)
- ✅ Handles 404 for non-existent WBE
- ✅ Handles 404 for WBE created after control_date
- ✅ Handles empty WBE (no cost elements) correctly

**Test-First Requirement:**
- Create failing test: `test_get_wbe_evm_metrics_endpoint_normal_case()` in `backend/tests/api/routes/test_evm_aggregation.py`
- Create failing test: `test_get_wbe_evm_metrics_endpoint_not_found()` in `backend/tests/api/routes/test_evm_aggregation.py`
- Create failing test: `test_get_wbe_evm_metrics_endpoint_empty_wbe()` in `backend/tests/api/routes/test_evm_aggregation.py`

**Files to Modify:**
- `backend/app/api/routes/evm_aggregation.py` (or `evm_indices.py`)
- `backend/tests/api/routes/test_evm_aggregation.py` (or extend `test_evm_indices.py`)

**Dependencies:**
- Step 3.2, Step 2.3

**Estimated Time:** 1-2 hours

---

#### Step 3.4: Implement Project Level Endpoint

**Objective:** Create API endpoint for project level EVM metrics.

**Acceptance Criteria:**
- ✅ Endpoint: `GET /projects/{project_id}/evm-metrics`
- ✅ Response model: `EVMIndicesProjectPublic`
- ✅ Validates project exists
- ✅ Calls `get_project_evm_metrics()` from unified service
- ✅ Returns all EVM metrics (PV, EV, AC, BAC, CPI, SPI, TCPI, CV, SV)
- ✅ Handles 404 for non-existent project
- ✅ Handles empty project (no WBEs) correctly

**Test-First Requirement:**
- Create failing test: `test_get_project_evm_metrics_endpoint_normal_case()` in `backend/tests/api/routes/test_evm_aggregation.py`
- Create failing test: `test_get_project_evm_metrics_endpoint_not_found()` in `backend/tests/api/routes/test_evm_aggregation.py`
- Create failing test: `test_get_project_evm_metrics_endpoint_empty_project()` in `backend/tests/api/routes/test_evm_aggregation.py`

**Files to Modify:**
- `backend/app/api/routes/evm_aggregation.py` (or `evm_indices.py`)
- `backend/tests/api/routes/test_evm_aggregation.py` (or extend `test_evm_indices.py`)

**Dependencies:**
- Step 3.3, Step 2.4

**Estimated Time:** 1-2 hours

---

#### Step 3.5: Register Unified Router

**Objective:** Register unified EVM aggregation router in main API.

**Acceptance Criteria:**
- ✅ Router registered in `backend/app/api/main.py`
- ✅ Router imported correctly
- ✅ API starts without errors
- ✅ Endpoints accessible at `/api/v1/projects/{project_id}/evm-metrics/...`

**Test-First Requirement:**
- None (infrastructure setup, verified by integration tests)

**Files to Modify:**
- `backend/app/api/main.py`

**Dependencies:**
- Step 3.4

**Estimated Time:** 15 minutes

---

### PHASE 4: Refactor Existing evm_indices.py

#### Step 4.1: Refactor evm_indices.py to Use Unified Service

**Objective:** Replace duplicate logic in `_get_wbe_evm_inputs()` and `_get_project_evm_inputs()` with calls to unified aggregation service.

**Acceptance Criteria:**
- ✅ `_get_wbe_evm_inputs()` removed or refactored to call `get_wbe_evm_metrics()` from unified service
- ✅ `_get_project_evm_inputs()` removed or refactored to call `get_project_evm_metrics()` from unified service
- ✅ Existing `evm_indices` endpoints continue to work (backward compatibility during deprecation)
- ✅ All existing tests for `evm_indices` endpoints still pass
- ✅ No code duplication (PV/EV/AC calculation logic removed from `evm_indices.py`)

**Test-First Requirement:**
- Run existing tests: `backend/tests/api/routes/test_evm_indices.py` - all should still pass
- If tests fail, fix implementation to maintain backward compatibility

**Files to Modify:**
- `backend/app/api/routes/evm_indices.py`

**Dependencies:**
- Phase 3 complete

**Estimated Time:** 2-3 hours

---

### PHASE 5: Deprecate Separate Endpoints

#### Step 5.1: Mark Planned Value Endpoints as Deprecated

**Objective:** Add deprecation warnings to planned_value endpoints.

**Acceptance Criteria:**
- ✅ All endpoints in `backend/app/api/routes/planned_value.py` have deprecation notice in docstring
- ✅ Deprecation notice includes migration path to unified endpoint
- ✅ Endpoints still functional (backward compatibility)
- ✅ OpenAPI schema includes deprecation notice

**Test-First Requirement:**
- None (documentation change, endpoints remain functional)

**Files to Modify:**
- `backend/app/api/routes/planned_value.py`

**Dependencies:**
- Phase 4 complete

**Estimated Time:** 30 minutes

---

#### Step 5.2: Mark Earned Value Endpoints as Deprecated

**Objective:** Add deprecation warnings to earned_value endpoints.

**Acceptance Criteria:**
- ✅ All endpoints in `backend/app/api/routes/earned_value.py` have deprecation notice in docstring
- ✅ Deprecation notice includes migration path to unified endpoint
- ✅ Endpoints still functional (backward compatibility)
- ✅ OpenAPI schema includes deprecation notice

**Test-First Requirement:**
- None (documentation change, endpoints remain functional)

**Files to Modify:**
- `backend/app/api/routes/earned_value.py`

**Dependencies:**
- Step 5.1

**Estimated Time:** 30 minutes

---

#### Step 5.3: Mark Old EVM Indices Endpoints as Deprecated

**Objective:** Add deprecation warnings to existing evm_indices endpoints (WBE and project levels).

**Acceptance Criteria:**
- ✅ Endpoints in `backend/app/api/routes/evm_indices.py` have deprecation notice in docstring
- ✅ Deprecation notice includes migration path to unified endpoint
- ✅ Endpoints still functional (backward compatibility)
- ✅ OpenAPI schema includes deprecation notice
- ✅ Note: Cost element level endpoint is new (not deprecated)

**Test-First Requirement:**
- None (documentation change, endpoints remain functional)

**Files to Modify:**
- `backend/app/api/routes/evm_indices.py`

**Dependencies:**
- Step 5.2

**Estimated Time:** 30 minutes

---

### PHASE 6: Integration Testing and Verification

#### Step 6.1: End-to-End Integration Tests

**Objective:** Verify unified endpoints produce same results as calling separate endpoints and aggregating.

**Acceptance Criteria:**
- ✅ Integration test: Unified cost element endpoint matches individual PV/EV/AC endpoint results
- ✅ Integration test: Unified WBE endpoint matches aggregating cost element results
- ✅ Integration test: Unified project endpoint matches aggregating WBE results
- ✅ Integration test: Time-machine control date filtering works correctly
- ✅ Integration test: Edge cases (None CPI/SPI/TCPI, empty hierarchies) handled correctly
- ✅ All integration tests pass

**Test-First Requirement:**
- Create integration tests in `backend/tests/api/routes/test_evm_aggregation_integration.py`
- Tests should compare unified endpoint results with manual aggregation of separate endpoints

**Files to Create:**
- `backend/tests/api/routes/test_evm_aggregation_integration.py`

**Dependencies:**
- Phase 5 complete

**Estimated Time:** 2-3 hours

---

#### Step 6.2: Regenerate OpenAPI Client

**Objective:** Regenerate frontend OpenAPI client with new unified endpoints and models.

**Acceptance Criteria:**
- ✅ OpenAPI client regenerated
- ✅ New `EVMIndicesCostElementPublic` type available in frontend
- ✅ New unified endpoint methods available in frontend client
- ✅ TypeScript compilation succeeds
- ✅ No breaking changes to existing client code (deprecated endpoints still available)

**Test-First Requirement:**
- None (client generation, verified by TypeScript compilation)

**Files to Modify:**
- `frontend/src/client/*` (auto-generated)

**Dependencies:**
- Step 6.1

**Estimated Time:** 15 minutes

---

#### Step 6.3: Verify No Regressions

**Objective:** Run full test suite to ensure no regressions introduced.

**Acceptance Criteria:**
- ✅ All existing tests pass (planned_value, earned_value, evm_indices, cost_summary)
- ✅ All new tests pass (evm_aggregation service and API)
- ✅ No linter errors
- ✅ TypeScript compilation succeeds
- ✅ No performance degradation (verify query counts haven't increased)

**Test-First Requirement:**
- Run full test suite: `python -m pytest backend/tests/`
- Run TypeScript compilation: `cd frontend && npm run build`

**Files to Verify:**
- All test files
- All production code files

**Dependencies:**
- Step 6.2

**Estimated Time:** 30 minutes

---

## TDD DISCIPLINE RULES

1. **Failing Test First:** Every production code change must be preceded by a failing test
2. **Red-Green-Refactor:** Follow strict red-green-refactor cycle for each step
3. **Maximum 3 Iterations:** If a step requires more than 3 red-green-refactor cycles, stop and ask for help
4. **Behavior Verification:** Tests must verify behavior (correct calculations, edge cases), not just compilation
5. **Test Coverage:** All new functions must have corresponding tests
6. **Incremental Commits:** Each step should result in a commit (<100 lines, <5 files target)

---

## PROCESS CHECKPOINTS

### Checkpoint 1: After Phase 2 (Unified Aggregation Service Complete)
**Questions:**
- Does the unified service correctly reuse existing services?
- Are all edge cases (None values, empty hierarchies) handled correctly?
- Should we continue with API endpoints as planned?

### Checkpoint 2: After Phase 3 (Unified API Endpoints Complete)
**Questions:**
- Do the unified endpoints return correct results?
- Is the API structure clear and consistent?
- Should we proceed with refactoring existing endpoints?

### Checkpoint 3: After Phase 4 (Refactoring Complete)
**Questions:**
- Do existing endpoints still work correctly after refactoring?
- Is code duplication eliminated?
- Should we proceed with deprecation notices?

### Checkpoint 4: After Phase 6 (Integration Testing Complete)
**Questions:**
- Do unified endpoints match results from separate endpoints?
- Are there any performance concerns?
- Is the implementation ready for production?

---

## SCOPE BOUNDARIES

**In Scope:**
- ✅ Unified EVM aggregation service reusing existing services
- ✅ Unified API endpoints at cost element, WBE, and project levels
- ✅ Cost element level EVMIndices model
- ✅ Refactoring evm_indices.py to eliminate duplication
- ✅ Deprecation notices on separate endpoints
- ✅ Integration tests verifying unified aggregation

**Out of Scope:**
- ❌ Caching (explicitly excluded by user)
- ❌ Removing deprecated endpoints (deprecation only, not removal)
- ❌ Frontend UI changes (backend-only implementation)
- ❌ Performance optimization beyond eliminating duplication
- ❌ New calculation formulas (reuse existing)

**If Useful Improvements Found:**
- Ask user for confirmation before implementing
- Document in plan if approved

---

## ROLLBACK STRATEGY

### Safe Rollback Points

1. **After Phase 2:** Can rollback unified service, keep existing endpoints
2. **After Phase 3:** Can rollback unified endpoints, keep existing endpoints
3. **After Phase 4:** Can rollback refactoring, restore duplicate logic in evm_indices.py
4. **After Phase 5:** Can remove deprecation notices, keep all endpoints active

### Rollback Procedure

1. **Identify rollback point:** Determine which phase to rollback to
2. **Git revert:** Revert commits from current phase back to safe point
3. **Verify:** Run test suite to ensure system works at rollback point
4. **Document:** Update plan with rollback reason and alternative approach

### Alternative Approaches if Rollback Needed

- **Alternative A:** Keep unified service but don't deprecate separate endpoints
- **Alternative B:** Only refactor evm_indices.py, don't create new unified endpoints
- **Alternative C:** Create unified endpoint but keep separate endpoints without deprecation

---

## ESTIMATED EFFORT

**Total Estimated Time:** 15-22 hours

**Breakdown:**
- Phase 1 (Model): 15 minutes
- Phase 2 (Service): 5-8 hours
- Phase 3 (API): 3-5 hours
- Phase 4 (Refactoring): 2-3 hours
- Phase 5 (Deprecation): 1.5 hours
- Phase 6 (Integration): 3-4 hours

**Risk Buffer:** Add 20% buffer for unexpected issues = **18-26 hours total**

---

## SUCCESS CRITERIA

✅ Unified EVM aggregation service created and reuses existing services
✅ Unified API endpoints provide all EVM metrics at cost element, WBE, and project levels
✅ Code duplication eliminated in evm_indices.py
✅ All existing tests pass (no regressions)
✅ All new tests pass (comprehensive coverage)
✅ Deprecation notices added to separate endpoints
✅ Integration tests verify unified aggregation matches separate endpoint aggregation
✅ OpenAPI client regenerated successfully
✅ Documentation updated

---

## NEXT STEPS

1. **Review Plan:** Confirm approach and scope
2. **Begin Implementation:** Start with Phase 1, Step 1.1 (TDD: failing test first)
3. **Checkpoint Reviews:** Pause at each checkpoint for feedback
4. **Completion:** Verify all success criteria met before marking complete

---

**Reference:** This plan follows the PLA-2 detailed planning template and is based on the high-level analysis in `docs/analysis/e4-005-918275-evm-aggregation-logic-analysis.md`. The plan implements user requirements: unified endpoint, cost element level, deprecation of separate endpoints, use of EVMIndices models, and no caching.
