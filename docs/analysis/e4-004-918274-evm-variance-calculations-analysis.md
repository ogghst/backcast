# High-Level Analysis: E4-004 EVM Variance Calculations (CV, SV)

**Task:** E4-004 - Variance Calculations
**Sprint:** Sprint 4 - Earned Value Recording and Core EVM Calculations
**Status:** Analysis Phase
**Date:** 2025-11-16
**Current Time:** 22:24 CET (Europe/Rome)

---

## User Story

As a project manager monitoring performance at a given control date,
I want cost variance (CV) and schedule variance (SV) metrics at project, WBE, and cost element levels,
So that I can quickly understand the absolute dollar amount by which we are over/under budget and ahead/behind schedule.

---

## 1. CODEBASE PATTERN ANALYSIS

1. **EVM Performance Indices (CPI, SPI, TCPI) – E4-003**
   - **Location:** `backend/app/services/evm_indices.py`, `backend/app/api/routes/evm_indices.py`, related tests under `backend/tests/services/test_evm_indices.py` and `backend/tests/api/routes/test_evm_indices.py`.
   - **Architecture Layers:**
     - Service layer: pure functions such as `calculate_cpi`, `calculate_spi`, `calculate_tcpi` with edge case handling (None for undefined cases, 'overrun' string for TCPI overrun).
     - API layer: FastAPI router that injects `SessionDep`, `CurrentUser`, and time-machine control date, retrieves PV/EV/AC/BAC via shared helpers (`_get_wbe_evm_inputs`, `_get_project_evm_inputs`), and returns response models.
     - Models: `EVMIndicesBase`, `EVMIndicesWBEPublic`, `EVMIndicesProjectPublic` in `backend/app/models/evm_indices.py`.
   - **Patterns to respect:**
     - Pure calculation functions in service layer with `Decimal` quantization (4 decimal places for indices).
     - Reuse of existing EVM input retrieval helpers (`_get_wbe_evm_inputs`, `_get_project_evm_inputs`).
     - Response models that include both calculated metrics and underlying inputs (PV, EV, AC, BAC) for transparency.
     - Edge case handling with explicit business rules (None for undefined, string literals for special cases).

2. **Planned Value (PV) Calculation Engine – E4-001**
   - **Location:** `backend/app/services/planned_value.py`, `backend/app/api/routes/planned_value.py`.
   - **Architecture Layers:**
     - Service layer: pure functions such as `calculate_planned_value`, `calculate_cost_element_planned_value`, and aggregation helpers.
     - API layer: FastAPI router with endpoints at cost element, WBE, and project levels.
     - Models: PV response schemas following Base/Create/Update/Public pattern.
   - **Patterns to respect:**
     - Hierarchical aggregation (cost element → WBE → project) implemented in service layer.
     - Use of time-machine control date for all queries.
     - `Decimal` quantization to 2 decimal places for monetary values.

3. **Earned Value (EV) Calculation Engine – E4-002**
   - **Location:** `backend/app/services/earned_value.py`, `backend/app/api/routes/earned_value.py`.
   - **Architecture Layers:**
     - Service layer: `calculate_earned_value`, `calculate_cost_element_earned_value`, and aggregation helpers mirroring PV patterns.
     - API layer: earned value router with control date dependency, entry selection logic, and hierarchical aggregation.
   - **Patterns to respect:**
     - Mirrored structure with PV for consistency.
     - Reuse of time-machine helpers and selection logic.
     - `Decimal`-based math with quantization for financial correctness.

4. **Cost Aggregation Patterns – E3-002**
   - **Location:** `backend/app/api/routes/cost_summary.py` and related services/models.
   - **Architecture Layers:**
     - Aggregation endpoints that roll up cost registrations into AC totals.
     - Response schemas that expose computed ratios and absolute values.
   - **Relevance:** Variance calculations require AC (actual cost) which is already aggregated in cost summary patterns.

### Architectural Layers to Respect

- **Service layer (`backend/app/services/…`)** for pure variance calculation functions (CV, SV) with proper `Decimal` handling.
- **API layer (`backend/app/api/routes/…`)** for wiring control date, querying PV/EV/AC inputs via existing helpers, and returning variance DTOs.
- **Models layer (`backend/app/models/…`)** for typed response schemas that keep variance formulas and decimals consistent.
- **Frontend consumption** through existing summary components or new variance-specific displays (E4-006).

---

## 2. INTEGRATION TOUCHPOINT MAPPING

### Backend Modules and Methods

- **EVM Input Retrieval Helpers (Existing)**
  - `backend/app/api/routes/evm_indices.py`: Contains `_get_wbe_evm_inputs()` and `_get_project_evm_inputs()` that return `(pv, ev, ac, bac)` tuples.
  - **Impact:** Variance service can reuse these exact helpers to get PV, EV, and AC inputs, ensuring consistency with indices calculations.

- **PV/EV Services**
  - `backend/app/services/planned_value.py`: Provides PV calculation logic.
  - `backend/app/services/earned_value.py`: Provides EV calculation logic.
  - **Impact:** Variance calculations depend on PV and EV values, which are already computed by these services.

- **Cost Aggregation Services**
  - `backend/app/api/routes/cost_summary.py` and related services: Provide AC (actual cost) aggregation.
  - **Impact:** AC is already aggregated in EVM input helpers, so no additional cost aggregation logic needed.

- **Time-Machine Control Date**
  - `get_time_machine_control_date` dependency and helpers from PLA-1/E4-011.
  - **Impact:** All variance calculations must be computed "as-of" the same control date as PV, EV, and AC to ensure consistency.

- **New Service Module (Proposed)**
  - **Option 1 (Recommended):** Extend `backend/app/services/evm_indices.py`
    - Add functions:
      - `calculate_cost_variance(ev: Decimal, ac: Decimal) -> Decimal` (CV = EV - AC)
      - `calculate_schedule_variance(ev: Decimal, pv: Decimal) -> Decimal` (SV = EV - PV)
    - **Rationale:** Variances are closely related to indices (both derived from PV/EV/AC), and keeping them together maintains cohesion. Indices and variances are often displayed together in EVM reports.

  - **Option 2:** Create `backend/app/services/evm_variances.py`
    - Same functions as Option 1, but in a separate module.
    - **Rationale:** Clear separation if variances are considered distinct from indices, but adds another module to maintain.

- **New/Extended API Router (Proposed)**
  - **Option 1 (Recommended):** Extend `backend/app/api/routes/evm_indices.py`
    - Add variance fields to existing `EVMIndicesBase` model and endpoints.
    - Endpoints already return PV, EV, AC; adding CV and SV is a natural extension.
    - **Rationale:** Single endpoint provides both indices and variances, reducing API surface area and ensuring consistency (same control date, same inputs).

  - **Option 2:** Create `backend/app/api/routes/evm_variances.py`
    - New endpoints:
      - `GET /projects/{project_id}/evm-variances/wbes/{wbe_id}` (required)
      - `GET /projects/{project_id}/evm-variances` (required)
    - **Rationale:** Dedicated variance endpoints if variances are consumed separately from indices, but duplicates input retrieval logic.

### System Dependencies and External Integrations

- **Database:** Existing PostgreSQL schema already stores:
  - PV (from schedules), EV (from earned value entries), AC (from cost registrations), BAC (from budgets).
  - No schema changes required; variances are computed on the fly.
- **Frontend:** Existing components (e.g., `EarnedValueSummary`, `BudgetSummary`) may consume variances.
  - For E4-004, backend APIs and tests are the primary scope; UI consumption can be staged later (likely E4-006).
- **Analytics Libraries (Context7 Insight):**
  - Variances are simple subtraction operations (CV = EV - AC, SV = EV - PV), so no external numeric libraries needed.
  - Existing `Decimal` patterns are sufficient for financial precision.

### Configuration Patterns

- Reuse existing configuration for:
  - Time-machine control date persistence and injection.
  - Decimal precision (2 decimal places for monetary variances, matching PV/EV/AC).
  - API versioning and path conventions under `/api/v1/projects/{project_id}/…`.

---

## 3. ABSTRACTION INVENTORY

- **Decimal Quantization Helpers**
  - EVM indices service defines `TWO_PLACES`, `FOUR_PLACES`, `_quantize`, and uses `ROUND_HALF_UP`.
  - Variances should use `TWO_PLACES` (monetary values) to match PV/EV/AC precision, not `FOUR_PLACES` (indices).

- **EVM Input Retrieval Helpers**
  - `_get_wbe_evm_inputs()` and `_get_project_evm_inputs()` in `evm_indices.py` already return `(pv, ev, ac, bac)` tuples.
  - Variance calculations can directly reuse these helpers, ensuring consistency with indices.

- **Time-Machine Helpers**
  - Shared control-date logic enforces historical correctness across PV, EV, and cost timelines.
  - Variances must be computed using values that already respect these filters.

- **Testing Utilities**
  - Existing pytest fixtures for projects, WBEs, cost elements, schedules, cost registrations, and earned value entries.
  - Helpers such as `set_time_machine_date` and baseline creation utilities.
  - E4-004 tests can reuse these fixtures to construct scenarios where PV/EV/AC relationships produce known CV/SV values.

- **Frontend Patterns (For Later Reuse)**
  - `EarnedValueSummary` and `BudgetSummary` components already display metrics with color-coded status indicators.
  - Once variances exist, these components (or new EVM summary components) can display CV/SV with appropriate color coding (negative = red/amber, positive = green).

---

## 4. ALTERNATIVE APPROACHES

### Approach A – Extend EVM Indices Service and Router (Recommended)

- **Summary:** Add CV and SV calculation functions to `evm_indices.py` service, and add variance fields to `EVMIndicesBase` model and existing endpoints in `evm_indices.py` router.
- **Formulas (from PRD/standard EVM):**
  - \(CV = EV - AC\) (negative = over-budget, positive = under-budget)
  - \(SV = EV - PV\) (negative = behind-schedule, positive = ahead-of-schedule)
- **Pros:**
  - Single endpoint provides both indices and variances, ensuring consistency (same control date, same inputs).
  - Reduces API surface area; clients get all EVM metrics in one call.
  - Reuses existing input retrieval helpers (`_get_wbe_evm_inputs`, `_get_project_evm_inputs`).
  - Aligns with existing E4-003 patterns and maintains service cohesion.
  - Natural extension: indices and variances are often displayed together in EVM reports.
- **Cons/Risks:**
  - Slightly larger response models (adds 2 fields to existing `EVMIndicesBase`).
  - If variances are consumed separately from indices, clients may fetch unnecessary data.
- **Architectural Alignment:** High – extends existing service/router, respects TDD discipline, maintains single source of truth.
- **Estimated Complexity:** Low – simple subtraction operations, minimal new code, leverages existing infrastructure.
- **Risk Factors:**
  - Need to ensure backward compatibility if existing clients consume `EVMIndicesBase` (add fields as optional or with defaults).

### Approach B – Dedicated Variance Service and Router

- **Summary:** Create `evm_variances.py` service and `evm_variances.py` router with dedicated endpoints for CV and SV calculations.
- **Pros:**
  - Clear separation of concerns; variances live in a focused module.
  - Clients can fetch only variances if indices are not needed.
  - Easy to test and reason about with pure functions.
- **Cons/Risks:**
  - Introduces another API surface area to document and maintain.
  - Duplicates input retrieval logic (need to reimplement `_get_wbe_evm_inputs`-like helpers or extract to shared module).
  - Risk of inconsistency if variance endpoints use different control dates or input sources than indices endpoints.
  - More endpoints for clients to call if they need both indices and variances.
- **Architectural Alignment:** Medium – follows service/router pattern but creates duplication and potential inconsistency.
- **Estimated Complexity:** Medium – similar logic but requires new router, models, and test files.
- **Risk Factors:**
  - Misaligned control dates or inconsistent input sources could yield misleading variances.
  - Code duplication increases maintenance burden.

### Approach C – Client-Side Variance Calculation Using Existing APIs

- **Summary:** Keep backend limited to PV, EV, AC, and BAC endpoints; compute CV/SV entirely in the frontend or external analytics tools.
- **Pros:**
  - Zero backend changes; reuses existing APIs.
  - Allows flexible experimentation with additional derived metrics in the UI.
- **Cons/Risks:**
  - Violates single-source-of-truth principle for EVM calculations.
  - Harder to test and validate; multiple clients may implement formulas differently.
  - Time-machine consistency harder to guarantee if clients mix data from different control dates.
  - Variances are core EVM metrics that should be server-side for reporting/export consistency.
- **Architectural Alignment:** Low – shifts core EVM logic out of the backend where other calculations live.
- **Estimated Complexity:** Low for initial implementation, but higher long-term maintenance burden.
- **Risk Factors:**
  - Inconsistent metrics across consumers.
  - More difficult to support reporting/export or external integrations expecting server-side variances.

---

## 5. ARCHITECTURAL IMPACT ASSESSMENT

- **Principles Followed (for Approach A):**
  - **Single Source of Truth:** All core EVM math (PV, EV, AC, BAC, CPI, SPI, TCPI, CV, SV) resides in backend services with tests.
  - **Separation of Concerns:** Variances extend existing indices service/router; PV, EV, and cost aggregation remain focused.
  - **Time-Machine Consistency:** Variances rely on values computed as-of a single control date, respecting PLA-1/E4-011 semantics.
  - **Reusability:** Shared helpers and quantization utilities reduce duplication.
  - **API Cohesion:** Single endpoint provides related EVM metrics together, reducing client round-trips.

- **Potential Maintenance Burden:**
  - Extending `EVMIndicesBase` model adds fields that existing clients may not expect (need to ensure backward compatibility or versioning).
  - Any change to PV, EV, or AC definitions must consider downstream impact on variances (and vice versa).
  - If variances are later needed in multiple contexts (dashboards, reports, exports), we must maintain API versioning and backwards compatibility.

- **Testing Challenges:**
  - Need scenario matrices covering:
    - Normal cases (EV, PV, AC > 0) with expected CV/SV (positive, negative, zero).
    - Edge cases:
      - CV: EV = AC → CV = 0 (on budget)
      - SV: EV = PV → SV = 0 (on schedule)
      - CV: EV < AC → CV < 0 (over-budget)
      - SV: EV < PV → SV < 0 (behind-schedule)
      - CV: EV > AC → CV > 0 (under-budget)
      - SV: EV > PV → SV > 0 (ahead-of-schedule)
    - Zero value scenarios:
      - CV: EV = 0, AC = 0 → CV = 0
      - SV: EV = 0, PV = 0 → SV = 0
      - CV: EV = 0, AC > 0 → CV < 0 (negative, no work earned but costs incurred)
      - SV: EV = 0, PV > 0 → SV < 0 (negative, no work earned but work planned)
    - Time-machine scenarios where values change as control date moves (e.g., before costs posted, after costs posted).
  - Hierarchical tests for WBE and project levels (required) to verify aggregation and consistency with indices.
  - Integration tests ensuring variances and indices use the same inputs and control dates.

---

## Risks, Unknowns, and Ambiguities

- **Business Rules Clarified:**
  - ✅ **CV formula:** CV = EV - AC (negative = over-budget, positive = under-budget, zero = on-budget).
  - ✅ **SV formula:** SV = EV - PV (negative = behind-schedule, positive = ahead-of-schedule, zero = on-schedule).
  - ✅ **Required levels:** Variances are required at project and WBE levels (cost element level optional in MVP, per E4-003 pattern).
  - ✅ **Precision:** Variances are monetary values, so should use 2 decimal places (matching PV/EV/AC), not 4 decimal places (indices).

- **Performance Considerations:**
  - Variances are simple subtractions, so computation overhead is negligible.
  - If extending existing indices endpoints, no additional queries needed (reuses existing input retrieval).
  - If creating separate endpoints, need to ensure efficient aggregation and avoid N+1 patterns.

- **Data Quality Risks:**
  - Incomplete or inconsistent EV, PV, or AC data can yield misleading variances even if formulas are correct.
  - Need clear documentation and possibly UI indicators when required inputs are missing (e.g., no EV yet → variances not meaningful).
  - Negative variances are valid and expected (over-budget, behind-schedule); UI should handle negative values appropriately.

- **Integration with E4-003:**
  - If extending `EVMIndicesBase`, need to ensure backward compatibility with existing clients consuming indices.
  - Consider whether to make variance fields optional (default to None) or required (default to 0.00) in response models.

---

## Summary & Next Steps

- **What:** Introduce EVM Variance Calculations engine that computes Cost Variance (CV) and Schedule Variance (SV) as-of a control date at project and WBE levels (cost element optional), using existing PV, EV, and AC inputs.
- **Why:** Provide project managers with absolute dollar amounts for cost and schedule deviations, complementing performance indices (CPI, SPI) to give both ratio and absolute perspectives on project health.
- **Recommended Approach:** **Approach A – Extend EVM Indices Service and Router**, adding CV and SV calculation functions to `evm_indices.py` service and variance fields to `EVMIndicesBase` model and existing endpoints. This ensures consistency, reduces API surface area, and maintains service cohesion.
- **Business Rules Confirmed:**
  - CV = EV - AC (negative = over-budget, positive = under-budget)
  - SV = EV - PV (negative = behind-schedule, positive = ahead-of-schedule)
  - Variances required at project and WBE levels (cost element optional)
  - Precision: 2 decimal places (monetary values)
- **Next Steps:** Proceed to detailed planning with a TDD-focused implementation plan, explicit failing tests for edge cases, and consideration of backward compatibility when extending `EVMIndicesBase`.

---

**Reference:** This analysis follows the PLA-1 high-level analysis template and leverages existing EVM indices (E4-003), PV (E4-001), EV (E4-002), and time-machine patterns documented in `docs/analysis/*.md` and `docs/plans/*.plan.md`. Context7's FastAPI documentation confirms that extending existing response models is a standard pattern for adding related fields without breaking changes.
