# High-Level Analysis: E4-005 EVM Aggregation Logic

**Task:** E4-005 - EVM Aggregation Logic
**Sprint:** Sprint 4 - Earned Value Recording and Core EVM Calculations
**Status:** Analysis Phase
**Date:** 2025-11-16
**Current Time:** 22:46 CET (Europe/Rome)

---

## User Story

As a project manager viewing hierarchical reports,
I want all EVM metrics (PV, EV, AC, BAC, CPI, SPI, TCPI, CV, SV) aggregated consistently from cost elements to WBEs to project level,
So that I can see unified performance data at each hierarchy level without discrepancies or redundant calculations.

---

## 1. CODEBASE PATTERN ANALYSIS

### Existing EVM Calculation Implementations

1. **Planned Value (PV) Calculation Engine – E4-001**
   - **Location:** `backend/app/services/planned_value.py`, `backend/app/api/routes/planned_value.py`
   - **Endpoints:**
     - `GET /projects/{project_id}/planned-value/cost-elements/{cost_element_id}`
     - `GET /projects/{project_id}/planned-value/wbes/{wbe_id}`
     - `GET /projects/{project_id}/planned-value`
   - **Aggregation Pattern:** Service-level `aggregate_planned_value()` function that sums PV and BAC, computes weighted percent complete
   - **Architecture:** Pure service functions + API routes with hierarchical queries (cost elements → WBE → project)

2. **Earned Value (EV) Calculation Engine – E4-002**
   - **Location:** `backend/app/services/earned_value.py`, `backend/app/api/routes/earned_value.py`
   - **Endpoints:**
     - `GET /projects/{project_id}/earned-value/cost-elements/{cost_element_id}`
     - `GET /projects/{project_id}/earned-value/wbes/{wbe_id}`
     - `GET /projects/{project_id}/earned-value`
   - **Aggregation Pattern:** Service-level `aggregate_earned_value()` function that sums EV and BAC, computes weighted percent complete
   - **Architecture:** Mirrors PV pattern with earned value entry selection logic

3. **EVM Performance Indices (CPI, SPI, TCPI) – E4-003**
   - **Location:** `backend/app/services/evm_indices.py`, `backend/app/api/routes/evm_indices.py`
   - **Endpoints:**
     - `GET /projects/{project_id}/evm-indices/wbes/{wbe_id}`
     - `GET /projects/{project_id}/evm-indices`
   - **Aggregation Pattern:**
     - Service-level `aggregate_evm_indices()` function for PV/EV/AC/BAC aggregation
     - API-level helpers `_get_wbe_evm_inputs()` and `_get_project_evm_inputs()` that **duplicate** PV/EV/AC calculation logic
   - **Issue Identified:** The evm_indices endpoints recalculate PV, EV, and AC internally rather than reusing existing planned_value/earned_value/cost_summary services

4. **Cost Aggregation (AC) – E3-002**
   - **Location:** `backend/app/api/routes/cost_summary.py`
   - **Endpoints:**
     - `GET /cost-summary/cost-element/{cost_element_id}`
     - `GET /cost-summary/wbe/{wbe_id}`
     - `GET /cost-summary/project/{project_id}`
   - **Aggregation Pattern:** Direct SQLModel queries with Python sum() aggregation
   - **Architecture:** Hierarchical aggregation from cost registrations

5. **Variance Calculations (CV, SV) – E4-004**
   - **Location:** `backend/app/services/evm_indices.py` (functions `calculate_cost_variance`, `calculate_schedule_variance`)
   - **Status:** Already implemented and included in evm_indices endpoints
   - **Note:** Variances are calculated in evm_indices endpoints alongside CPI/SPI/TCPI

### Architectural Layers to Respect

- **Service Layer (`backend/app/services/…`):** Pure calculation functions with no DB access
- **API Layer (`backend/app/api/routes/…`):** FastAPI routes with dependency injection, time-machine control date
- **Models Layer (`backend/app/models/…`):** Response schemas following Base/Create/Update/Public pattern
- **Aggregation Pattern:** Hierarchical roll-up (cost element → WBE → project) with consistent quantization

### Code Duplication Identified

**Problem:** The `evm_indices.py` router contains helper functions `_get_wbe_evm_inputs()` and `_get_project_evm_inputs()` that:
- Re-implement PV calculation logic (duplicating `planned_value.py` service)
- Re-implement EV calculation logic (duplicating `earned_value.py` service)
- Re-implement AC aggregation logic (duplicating `cost_summary.py` patterns)
- Query cost elements, schedules, and entries independently

**Impact:**
- Maintenance burden: Changes to PV/EV/AC calculation logic must be updated in multiple places
- Inconsistency risk: Different implementations may diverge over time
- Performance: Multiple queries for the same data when all metrics are needed
- Testing: More test surface area to maintain

---

## 2. INTEGRATION TOUCHPOINT MAPPING

### Backend Modules Requiring Modification

1. **New Unified EVM Aggregation Service (Proposed)**
   - **Candidate:** `backend/app/services/evm_aggregation.py`
   - **Functions:**
     - `get_cost_element_evm_metrics()` - Returns all EVM metrics for a single cost element
     - `get_wbe_evm_metrics()` - Aggregates all EVM metrics for a WBE
     - `get_project_evm_metrics()` - Aggregates all EVM metrics for a project
   - **Dependencies:** Reuses existing `planned_value`, `earned_value`, and cost aggregation services
   - **Output:** Unified dataclass/response model containing PV, EV, AC, BAC, CPI, SPI, TCPI, CV, SV

2. **New Unified EVM Aggregation API Router (Proposed)**
   - **Candidate:** `backend/app/api/routes/evm_aggregation.py` OR extend existing `evm_indices.py`
   - **Endpoints:**
     - `GET /projects/{project_id}/evm-metrics/cost-elements/{cost_element_id}` (optional in MVP)
     - `GET /projects/{project_id}/evm-metrics/wbes/{wbe_id}` (required)
     - `GET /projects/{project_id}/evm-metrics` (required)
   - **Dependencies:** `SessionDep`, `CurrentUser`, `get_time_machine_control_date`
   - **Responsibility:** Single endpoint returning all EVM metrics at each hierarchy level

3. **Refactoring Existing Modules**
   - **`backend/app/api/routes/evm_indices.py`:**
     - Option A: Remove `_get_wbe_evm_inputs()` and `_get_project_evm_inputs()` helpers
     - Option B: Refactor to call unified aggregation service instead of duplicating logic
   - **`backend/app/api/routes/planned_value.py`:**
     - No changes required (keep as-is for backward compatibility)
   - **`backend/app/api/routes/earned_value.py`:**
     - No changes required (keep as-is for backward compatibility)
   - **`backend/app/api/routes/cost_summary.py`:**
     - No changes required (keep as-is for backward compatibility)

### System Dependencies and External Integrations

- **Database:** No schema changes required; aggregation uses existing data
- **Frontend:**
  - Existing components may call separate PV/EV/AC/indices endpoints
  - New unified endpoint can reduce API calls (1 call instead of 4+)
  - Backward compatibility: Keep existing endpoints for components that only need specific metrics
- **Time-Machine:** All aggregation must respect control date via `get_time_machine_control_date` dependency

### Configuration Patterns

- Reuse existing time-machine control date injection
- Reuse existing Decimal quantization patterns (TWO_PLACES, FOUR_PLACES)
- Follow existing API versioning (`/api/v1/projects/{project_id}/...`)

---

## 3. ABSTRACTION INVENTORY

### Existing Abstractions to Leverage

1. **Service Functions (Pure Calculations)**
   - `calculate_cost_element_planned_value()` from `planned_value.py`
   - `calculate_cost_element_earned_value()` from `earned_value.py`
   - `calculate_cpi()`, `calculate_spi()`, `calculate_tcpi()` from `evm_indices.py`
   - `calculate_cost_variance()`, `calculate_schedule_variance()` from `evm_indices.py`
   - `aggregate_planned_value()`, `aggregate_earned_value()`, `aggregate_evm_indices()` from respective services

2. **Aggregation Helpers**
   - `_get_schedule_map()` pattern from `planned_value.py` and `evm_indices.py`
   - `_get_entry_map()` pattern from `earned_value.py` and `evm_indices.py`
   - Cost registration aggregation patterns from `cost_summary.py`

3. **Time-Machine Helpers**
   - `get_time_machine_control_date` dependency
   - `apply_time_machine_filters()` for schedule/entry/cost registration filtering
   - `end_of_day()` helper for cutoff calculations

4. **Testing Utilities**
   - Existing pytest fixtures for projects, WBEs, cost elements, schedules, cost registrations, earned value entries
   - Time-machine test helpers
   - Aggregation test patterns from E4-001, E4-002, E4-003

5. **Response Models**
   - Existing `PlannedValue*Public`, `EarnedValue*Public`, `EVMIndices*Public` models
   - Can create new unified `EVMAggregation*Public` models OR extend existing ones

---

## 4. ALTERNATIVE APPROACHES

### Approach A – Unified EVM Aggregation Service + Router (Recommended)

- **Summary:** Create a new `evm_aggregation` service and API router that provides all EVM metrics (PV, EV, AC, BAC, CPI, SPI, TCPI, CV, SV) in a single endpoint per hierarchy level, reusing existing service functions to eliminate duplication.

- **Architecture:**
  - Service layer: `evm_aggregation.py` with functions that call `planned_value`, `earned_value`, and cost aggregation services
  - API layer: New router or extend `evm_indices.py` to provide unified endpoints
  - Response models: Unified `EVMAggregation*Public` models containing all metrics

- **Pros:**
  - Eliminates code duplication in `evm_indices.py` helpers
  - Single source of truth for EVM metric aggregation
  - Reduces API calls for frontend (1 call instead of 4+)
  - Maintains backward compatibility (keep existing endpoints)
  - Easier to test and maintain
  - Consistent aggregation logic across all metrics

- **Cons/Risks:**
  - Introduces new API surface (though can be additive)
  - Requires refactoring `evm_indices.py` to use unified service
  - Need to ensure all existing functionality preserved

- **Architectural Alignment:** High – follows existing service/router pattern, reuses abstractions, respects TDD discipline

- **Estimated Complexity:** Medium – service layer straightforward (compose existing functions), API layer requires careful refactoring to avoid breaking changes

- **Risk Factors:**
  - Must ensure backward compatibility with existing endpoints
  - Need comprehensive tests to verify aggregation matches individual endpoint results

### Approach B – Refactor evm_indices.py to Reuse Existing Services

- **Summary:** Keep existing endpoints but refactor `_get_wbe_evm_inputs()` and `_get_project_evm_inputs()` in `evm_indices.py` to call `planned_value`, `earned_value`, and `cost_summary` services instead of duplicating logic.

- **Pros:**
  - Eliminates code duplication
  - No new API surface
  - Minimal changes to existing code

- **Cons/Risks:**
  - Still requires multiple API calls for frontend to get all metrics
  - Doesn't solve the "unified aggregation" requirement for hierarchical reporting
  - May introduce circular dependencies if not careful
  - Performance: Multiple service calls may be less efficient than single aggregation

- **Architectural Alignment:** Medium – reduces duplication but doesn't provide unified aggregation

- **Estimated Complexity:** Low-Medium – refactoring existing code, need to avoid circular dependencies

- **Risk Factors:**
  - Potential circular dependencies between routers
  - May need to extract shared helpers to service layer

### Approach C – Extend Existing evm_indices Endpoints to Include All Metrics

- **Summary:** Keep `evm_indices.py` as-is but refactor to reuse existing services, and ensure endpoints return all metrics (they already return PV, EV, AC, BAC, CPI, SPI, TCPI, CV, SV).

- **Pros:**
  - Minimal API changes
  - Already returns most metrics

- **Cons/Risks:**
  - Doesn't eliminate duplication (still reimplements PV/EV/AC)
  - Doesn't provide cost-element level aggregation endpoint
  - May not be the "unified aggregation" intended by E4-005

- **Architectural Alignment:** Low – doesn't address code duplication or provide true unified aggregation

- **Estimated Complexity:** Low – mostly documentation/clarification

- **Risk Factors:**
  - May not meet the "hierarchical reporting" requirement if aggregation logic remains duplicated

---

## 5. ARCHITECTURAL IMPACT ASSESSMENT

### Principles Followed (for Approach A)

- **Single Source of Truth:** Unified aggregation service ensures consistent calculation logic
- **DRY (Don't Repeat Yourself):** Eliminates duplication in `evm_indices.py` helpers
- **Separation of Concerns:** Aggregation service composes existing services rather than reimplementing
- **Backward Compatibility:** Existing endpoints remain available for components that need specific metrics
- **Time-Machine Consistency:** All metrics computed as-of same control date

### Potential Maintenance Burden

- **New Service Module:** Additional service to maintain, but it's a thin composition layer
- **Refactoring Risk:** Need to carefully refactor `evm_indices.py` to avoid breaking existing functionality
- **Test Coverage:** Must verify unified aggregation matches individual endpoint results
- **API Versioning:** New unified endpoints may need versioning strategy if breaking changes occur

### Testing Challenges

- **Aggregation Accuracy:** Verify that unified aggregation produces same results as calling individual endpoints and aggregating client-side
- **Edge Cases:** Test scenarios where some metrics are undefined (CPI=None, SPI=None, TCPI='overrun')
- **Hierarchical Aggregation:** Test cost element → WBE → project roll-up with various data combinations
- **Time-Machine Scenarios:** Verify aggregation respects control date across all metrics
- **Performance:** Ensure unified aggregation doesn't introduce N+1 query patterns

### Performance Considerations

- **Query Efficiency:** Unified aggregation can batch queries more efficiently than multiple separate calls
- **Caching Opportunities:** Single aggregation endpoint may be easier to cache than multiple endpoints
- **Database Load:** Need to ensure aggregation doesn't create excessive database queries

---

## Risks, Unknowns, and Ambiguities

### Clarifications Needed

1. **Scope Definition:**
   - Does E4-005 require a new unified endpoint, or is refactoring existing duplication sufficient?
   - Should cost-element level aggregation be included (currently evm_indices only has WBE/project)?

2. **Backward Compatibility:**
   - Can we deprecate existing separate endpoints, or must they remain indefinitely?
   - Should unified endpoint be additive (new route) or replace existing routes?

3. **Response Model Design:**
   - Should unified endpoint use existing `EVMIndices*Public` models (extended) or new `EVMAggregation*Public` models?
   - Should response include all metrics or allow filtering?

4. **Performance Requirements:**
   - Are there performance targets for aggregation (e.g., <500ms for project-level)?
   - Should we consider caching or precomputation for large projects?

### Data Quality Risks

- Incomplete data (missing schedules, earned value entries, cost registrations) may cause some metrics to be undefined
- Need clear documentation and possibly UI indicators when metrics cannot be calculated
- Aggregation must handle None/null values gracefully (e.g., CPI=None doesn't break aggregation)

### Integration Risks

- Frontend components may need updates to use unified endpoint
- External integrations (if any) may depend on existing endpoint structure
- Need migration path for any components currently calling multiple endpoints

---

## Summary & Next Steps

- **What:** Implement unified EVM aggregation logic that rolls up all EVM metrics (PV, EV, AC, BAC, CPI, SPI, TCPI, CV, SV) from cost elements to WBEs to project level, eliminating code duplication and providing a single source of truth for hierarchical reporting.

- **Why:**
  - Eliminate code duplication in `evm_indices.py` that reimplements PV/EV/AC calculation
  - Provide unified aggregation endpoint for hierarchical reporting
  - Reduce API calls for frontend (1 call instead of 4+)
  - Ensure consistent aggregation logic across all EVM metrics

- **Recommended Approach:** **Approach A – Unified EVM Aggregation Service + Router**
  - Create `evm_aggregation.py` service that composes existing `planned_value`, `earned_value`, and cost aggregation services
  - Create unified API endpoints (or extend `evm_indices.py`) providing all metrics at WBE and project levels
  - Refactor `evm_indices.py` to use unified service instead of duplicating logic
  - Maintain backward compatibility with existing endpoints

- **Key Requirements:**
  - Hierarchical aggregation: cost element → WBE → project
  - All metrics: PV, EV, AC, BAC, CPI, SPI, TCPI, CV, SV
  - Time-machine control date support
  - Eliminate code duplication
  - Backward compatibility

- **Next Steps:**
  1. Clarify scope and requirements with stakeholders
  2. Proceed to detailed planning with TDD-focused implementation plan
  3. Design unified response models
  4. Plan refactoring strategy for `evm_indices.py`

---

**Reference:** This analysis follows the PLA-1 high-level analysis template and leverages existing PV/EV, cost aggregation, and EVM indices patterns documented in `docs/analysis/*.md` and `docs/completions/*.md`. The analysis identifies code duplication in `evm_indices.py` and proposes a unified aggregation service to eliminate redundancy while providing comprehensive hierarchical reporting capabilities.
