# Analysis: Time-Aware EVM (Earned Value Management) Analysis for Cost Elements

**Created:** 2026-01-18
**Request:** Implement time-aware EVM calculations for cost elements with control date support

---

## Clarified Requirements

The system shall support time-aware Earned Value Management (EVM) calculations that consider a "control date" parameter to determine the state of the system as of a specific point in time.

### Functional Requirements

1. **Control Date Parameter**: All EVM calculations shall accept a `control_date` parameter that represents the point in time for which calculations should be performed
2. **Time-Aware Planned Value (PV)**: PV calculations shall query the schedule baseline version that was active at the control date
3. **Time-Aware Actual Cost (AC)**: AC calculations shall sum cost registrations that existed at the control date (using `registration_date <= control_date`)
4. **Time-Aware Budget at Completion (BAC)**: BAC shall be derived from the cost element's budget amount as of the control date
5. **Complete EVM Metrics**: Calculate all standard EVM metrics based on the control date:
   - **PV** (Planned Value) = BAC × Progress (from schedule baseline active at control date)
   - **AC** (Actual Cost) = Sum of cost registrations as of control date
   - **EV** (Earned Value) = Currently placeholder (requires progress reporting implementation)
   - **CV** (Cost Variance) = EV - AC
   - **SV** (Schedule Variance) = EV - PV
   - **CPI** (Cost Performance Index) = EV / AC
   - **SPI** (Schedule Performance Index) = EV / PV
6. **Branch Isolation**: EVM calculations shall respect branch isolation for cost elements and schedule baselines
7. **API Endpoint**: Provide a dedicated API endpoint `/api/v1/cost-elements/{id}/evm` with `control_date` query parameter

### Non-Functional Requirements

- **Performance**: EVM calculations should complete within 500ms for standard queries
- **Accuracy**: Decimal precision shall be maintained (2 decimal places for currency)
- **Consistency**: Time-travel queries must use the same bitemporal filtering as other entity queries
- **Testability**: All EVM calculations shall have unit and integration tests

### Constraints

- **Existing Framework**: Must leverage the existing EVCS (Entity Versioning Control System) temporal framework
- **No Breaking Changes**: Existing PV calculation endpoint should remain functional
- **Database**: PostgreSQL 15+ with TSTZRANGE for temporal queries
- **Backend Port**: 8020

---

## Context Discovery

### Product Scope

**Relevant Domain Concepts:**
- **Earned Value Management (EVM)**: Project management technique for measuring project performance and progress
- **Bitemporal Versioning**: System tracks both valid_time (business validity) and transaction_time (system recording time)
- **Branch Isolation**: Change orders create isolated branches for what-if scenarios
- **Cost Elements**: Leaf-level budget allocation entities where budgets are allocated and costs tracked
- **Schedule Baselines**: 1-to-1 relationship with cost elements, defining time-phased budget progression
- **Cost Registrations**: Actual cost entries against cost elements (versionable but not branchable)

### Architecture Context

**Bounded Contexts Involved:**
1. **Cost Element & Financial Tracking** - Primary context for EVM calculations
2. **Schedule Baseline Management** - Provides PV calculation logic
3. **Change Order & Branching** - Requires branch isolation support
4. **Cost Registration** - Source of Actual Costs (AC)

**Existing Patterns to Follow:**
- **TemporalService**: Base class for versioned entities with `get_as_of()` method for time-travel
- **BranchableService**: Extends TemporalService with branch isolation
- **Progression Strategies**: Strategy pattern for Linear, Gaussian, Logarithmic progression curves
- **Bitemporal Filtering**: Standardized WHERE clauses via `_apply_bitemporal_filter_for_time_travel()`

**Architectural Constraints:**
- Layered architecture: API Routes → Services → Repositories → Models
- Dependency injection for services
- Pydantic schemas for request/response validation
- Async/await throughout

### Codebase Analysis

**Backend - Existing Related APIs:**

1. **PV Calculation Endpoint** (backend/app/api/routes/schedule_baselines.py:244-323)
   - Route: `GET /schedule-baselines/{id}/pv`
   - Parameters: `current_date`, `bac`, `branch`
   - Returns: PV calculation with progress
   - **Limitation**: Does NOT use time-travel (always gets current baseline)

2. **Cost Element with Time-Travel** (backend/app/api/routes/cost_elements.py:126-159)
   - Route: `GET /cost-elements/{id}`
   - Supports `as_of` parameter for time-travel
   - **Good pattern to follow**

3. **Cost Element Service** (backend/app/services/cost_element_service.py)
   - Has `get_cost_element_as_of()` method (lines 627-724)
   - Implements bitemporal filtering correctly
   - Includes branch mode support (STRICT/MERGE)

4. **Schedule Baseline Service** (backend/app/services/schedule_baseline_service.py)
   - Inherits from BranchableService
   - Has `get_for_cost_element()` method
   - **Missing**: No `get_as_of()` method exposed (but parent has it)

**Data Models:**

1. **CostElement** (backend/app/models/domain/cost_element.py)
   - Fields: `budget_amount` (for BAC), `schedule_baseline_id` (1:1 relationship)
   - Mixins: VersionableMixin, BranchableMixin
   - Supports bitemporal versioning

2. **ScheduleBaseline** (backend/app/models/domain/schedule_baseline.py)
   - Fields: `start_date`, `end_date`, `progression_type`
   - Mixins: VersionableMixin, BranchableMixin
   - Used for PV calculations via progression strategies

3. **CostRegistration** (backend/app/models/domain/cost_registration.py)
   - Fields: `amount`, `registration_date`, `cost_element_id`
   - Mixins: VersionableMixin only (NOT branchable)
   - **Key insight**: Costs are global facts, not branch-specific

**Progression Calculation:**

Three progression strategies exist (backend/app/services/progression/):
- **LinearProgression**: Straight-line progress over time
- **GaussianProgression**: S-curve with slow start, fast middle, tapering end
- **LogarithmicProgression**: Front-loaded progress

Each implements `calculate_progress(current_date, start_date, end_date) -> float`

**Existing Tests:**
- backend/tests/unit/services/test_pv_calculation.py - Comprehensive PV calculation tests
- Tests confirm: PV = BAC × Progress formula

**Frontend:**

- No existing EVM UI components identified
- Would need new component or integration into cost element detail page
- State management: TanStack Query for server state

---

## Solution Options

### Option 1: EVM Service with Time-Aware Methods (Recommended)

**Architecture & Design:**

Create a new dedicated `EVMService` that orchestrates time-aware EVM calculations by leveraging existing temporal services.

```python
class EVMService:
    """Service for calculating time-aware EVM metrics."""

    async def calculate_evm_metrics(
        self,
        cost_element_id: UUID,
        control_date: datetime,
        branch: str = "main"
    ) -> EVMMetricsResponse:
        """Calculate all EVM metrics as of control_date."""
        # 1. Get cost element as of control_date (for BAC)
        # 2. Get schedule baseline as of control_date (for PV)
        # 3. Get cost registrations as of control_date (for AC)
        # 4. Calculate metrics using progression strategy
        # 5. Return complete EVM metrics
```

**UX Design:**

- New API endpoint: `GET /api/v1/cost-elements/{id}/evm?control_date=2026-01-15T12:00:00Z`
- Response includes all EVM metrics with metadata about which versions were used
- Frontend can display EVM dashboard with control date picker for historical analysis

**Implementation:**

**Key Components:**

1. **New Service**: `backend/app/services/evm_service.py`
   - Inject `CostElementService`, `ScheduleBaselineService`, `CostRegistrationService`
   - Method: `calculate_evm_metrics(cost_element_id, control_date, branch)`

2. **New Schema**: `backend/app/models/schemas/evm.py`
   ```python
   class EVMMetricsRead(BaseModel):
       control_date: datetime
       bac: Decimal  # Budget at Completion
       pv: Decimal   # Planned Value
       ac: Decimal   # Actual Cost
       ev: Decimal   # Earned Value (placeholder)
       cv: Decimal   # Cost Variance
       sv: Decimal   # Schedule Variance
       cpi: Decimal  # Cost Performance Index
       spi: Decimal  # Schedule Performance Index

       # Metadata for transparency
       cost_element_version_id: UUID
       schedule_baseline_version_id: UUID | None
       progression_type: str | None
   ```

3. **New API Route**: `backend/app/api/routes/cost_elements.py`
   ```python
   @router.get("/{cost_element_id}/evm")
   async def get_evm_metrics(
       cost_element_id: UUID,
       control_date: datetime,
       branch: str = "main"
   ) -> EVMMetricsRead
   ```

4. **Time-Travel Logic:**
   - Use `cost_element_service.get_cost_element_as_of(id, control_date)` for BAC
   - Use `schedule_baseline_service.get_as_of(baseline_id, control_date)` for PV
   - Filter cost registrations: `registration_date <= control_date` AND `valid_time @> control_date`

**Trade-offs:**

| Aspect          | Assessment                           |
| --------------- | ------------------------------------ |
| Pros            | - Clear separation of concerns       |
|                 | - Reuses existing temporal framework |
|                 | - Easy to test independently         |
|                 | - Follows existing patterns          |
| Cons            | - Adds new service class             |
|                 | - Requires dependency injection setup |
| Complexity      | Low                                  |
| Maintainability | Excellent                            |
| Performance     | Good (3 temporal queries, can optimize later) |

---

### Option 2: Extend Cost Element Service with EVM Methods

**Architecture & Design:**

Add EVM calculation methods directly to `CostElementService` as a convenience.

```python
class CostElementService:
    async def calculate_evm_metrics(
        self,
        cost_element_id: UUID,
        control_date: datetime,
        branch: str = "main"
    ) -> EVMMetricsResponse:
        # Same logic as Option 1, but in existing service
```

**UX Design:**

Same API endpoint and response as Option 1.

**Implementation:**

- Add methods to `backend/app/services/cost_element_service.py`
- Import and use `ScheduleBaselineService` and `CostRegistrationService`
- Same schema and route as Option 1

**Trade-offs:**

| Aspect          | Assessment                           |
| --------------- | ------------------------------------ |
| Pros            | - Keeps EVM logic close to cost elements |
|                 | - Fewer new files                    |
|                 | - Convenient for callers             |
| Cons            | - Bloats CostElementService          |
|                 | - Mixes concerns (CRUD + analytics)  |
|                 | - Harder to test independently       |
| Complexity      | Low                                  |
| Maintainability | Fair                                 |
| Performance     | Good (same as Option 1)              |

---

### Option 3: Controller-Level Calculation (Anti-Pattern)

**Architecture & Design:**

Implement EVM calculation logic directly in the API route handler without a dedicated service.

**Implementation:**

```python
@router.get("/{cost_element_id}/evm")
async def get_evm_metrics(
    cost_element_id: UUID,
    control_date: datetime,
    branch: str = "main",
    session = Depends(get_db)
) -> dict:
    # Direct database queries and calculations in route handler
    ce_service = CostElementService(session)
    sb_service = ScheduleBaselineService(session)
    # ... calculation logic ...
```

**Trade-offs:**

| Aspect          | Assessment                  |
| --------------- | --------------------------- |
| Pros            | - Quick to implement        |
|                 | - Fewer abstraction layers  |
| Cons            | - Violates layered architecture |
|                 | - Business logic in API layer |
|                 | - Hard to test              |
|                 | - Can't reuse logic         |
| Complexity      | Low (but technical debt)    |
| Maintainability | Poor                        |
| Performance     | Same as others              |

**Note:** This option is presented for completeness but is NOT recommended.

---

## Comparison Summary

| Criteria            | Option 1 (EVM Service) | Option 2 (Extend CE Service) | Option 3 (Controller) |
| ------------------- | ---------------------- | ---------------------------- | --------------------- |
| Development Effort  | 2-3 days               | 1-2 days                     | 1 day                 |
| Architecture Quality | Excellent              | Good                         | Poor                  |
| Testability         | Excellent              | Good                         | Fair                  |
| Reusability         | High                   | Medium                       | Low                   |
| Separation of Concerns | Excellent           | Fair                         | Poor                  |
| Follows EVCS Patterns | Yes                  | Mostly                       | No                    |
| Best For            | Production system      | Quick prototype              | Spike/MVP only        |

---

## Recommendation

**I recommend Option 1 (EVM Service with Time-Aware Methods)** because:

1. **Architectural Integrity**: Follows the established layered architecture and separation of concerns
2. **Leverages Existing Framework**: Reuses the temporal versioning infrastructure (`get_as_of`, bitemporal filtering)
3. **Testability**: Can unit test EVM calculations independently of API layer
4. **Reusability**: EVM service can be used by other components (reports, dashboards, batch jobs)
5. **Maintainability**: Clear boundaries make future enhancements easier (e.g., adding EV when progress tracking is implemented)
6. **Consistency**: Matches the pattern used for other analytical services (e.g., `ImpactAnalysisService`)

**Alternative consideration:** Choose Option 2 only if you need to implement this as a spike/prototype and plan to refactor later. However, the extra day of development for Option 1 is worth the long-term maintainability benefits.

---

## Decision Questions

1. **Earned Value (EV) Calculation**: Currently, EV (Earned Value) requires progress reporting (% complete) which is not yet implemented. Should we:
   - Return EV = 0 as a placeholder?
   - Omit EV and derived metrics (CV, SV, CPI, SPI) until progress tracking exists?
   - Implement a basic progress tracking mechanism first?

2. **Cost Registration Aggregation**: For AC calculation, should we:
   - Sum all cost registrations with `registration_date <= control_date`?
   - Also apply temporal filtering to ensure registrations existed at control_date?
   - Use `registration_date` only (simpler, assumes costs are immutable facts)?

3. **Error Handling**: When historical versions don't exist (e.g., cost element created after control_date), should we:
   - Return 404 error?
   - Return metrics with zeros/nulls and a warning?
   - Return the earliest available version with a metadata note?

4. **Performance Optimization**: For large cost element sets, should we:
   - Implement database-level aggregations (custom SQL)?
   - Use application-level summation (simpler, slower)?
   - Cache EVM calculations for common control dates?

---

## Implementation Checklist (Option 1)

### Phase 1: Foundation
- [ ] Create `backend/app/models/schemas/evm.py` with `EVMMetricsRead` schema
- [ ] Create `backend/app/services/evm_service.py` with `EVMService` class
- [ ] Implement `calculate_evm_metrics()` method with time-travel queries
- [ ] Write unit tests for EVMService

### Phase 2: API Integration
- [ ] Add `GET /cost-elements/{id}/evm` route to `cost_elements.py`
- [ ] Implement route handler with dependency injection
- [ ] Add API documentation (OpenAPI)
- [ ] Write integration tests for API endpoint

### Phase 3: Testing & Validation
- [ ] Test with historical control dates
- [ ] Test with branch isolation
- [ ] Test edge cases (element not created yet, no baseline, no costs)
- [ ] Performance test with realistic data volumes
- [ ] Verify precision of decimal calculations

### Phase 4: Documentation
- [ ] Update API documentation
- [ ] Add EVM calculation guide
- [ ] Document time-travel behavior
- [ ] Create examples for common use cases

---

## References

**Architecture Documentation:**
- [ADR-005: Bitemporal Versioning](/home/nicola/dev/backcast_evs/docs/02-architecture/decisions/adr-005-bitemporal-versioning.md)
- [Bounded Contexts](/home/nicola/dev/backcast_evs/docs/02-architecture/01-bounded-contexts.md)
- [System Architecture](/home/nicola/dev/backcast_evs/docs/02-architecture/00-system-map.md)

**Existing Code:**
- [CostElementService](/home/nicola/dev/backcast_evs/backend/app/services/cost_element_service.py)
- [ScheduleBaselineService](/home/nicola/dev/backcast_evs/backend/app/services/schedule_baseline_service.py)
- [TemporalService](/home/nicola/dev/backcast_evs/backend/app/core/versioning/service.py)
- [PV Calculation Tests](/home/nicola/dev/backcast_evs/backend/tests/unit/services/test_pv_calculation.py)

**Related Iterations:**
- [2026-01-18: Schedule Baseline Architecture](/home/nicola/dev/backcast_evs/docs/03-project-plan/iterations/2026-01-18-schedule-baseline-architecture/)
- [2026-01-15: Register Actual Costs](/home/nicola/dev/backcast_evs/docs/03-project-plan/iterations/2026-01-15-register-actual-costs/)
