# Analysis: Full EVM Foundation for Backcast 

**Created:** 2026-01-18
**Request:** Implement foundational cost tracking features for Earned Value Management (EVM)

---

## Clarified Requirements

The system shall implement foundational EVM capabilities that enable project managers to track cost performance, measure progress, and calculate earned value metrics with full bitemporal versioning support.

### Functional Requirements

1. **Progress Tracking (% Complete)**
   - Mechanism to record and track progress on cost elements (0-100%)
   - Progress reporting must be versionable (track changes over time)
   - Support for manual progress entry by project managers
   - Progress history must be queryable "as of" any point in time
   - Used for calculating Earned Value: **EV = BAC × % Complete**

2. **Enhanced Cost Registration System**
   - Time-aware aggregation of cost registrations for Actual Cost (AC) calculation
   - Proper temporal filtering for "as of" queries (control date support)
   - Summation of actual costs as of any control date using bitemporal filtering
   - Ensure cost registrations respect versionable (but not branchable) architecture
   - Support for querying costs by time periods

3. **Time-Aware Cost Queries**
   - Query cost registrations as of a specific control date
   - Aggregate costs by time periods (daily, weekly, monthly)
   - Handle branch isolation correctly (costs are global, cost elements are branchable)
   - Support cumulative cost calculations over time

4. **EVM Metrics Foundation**
   - Budget at Completion (BAC) from cost element budget
   - Actual Cost (AC) from cost registrations
   - Planned Value (PV) from schedule baseline progression
   - Earned Value (EV) from BAC × % Complete
   - Variances: CV = EV - AC, SV = EV - PV
   - Performance Indices: CPI = EV / AC, SPI = EV / PV
   - All metrics must support time-travel queries (as of specific dates)

5. **API Endpoints**
   - Progress tracking CRUD operations
   - Cost aggregation queries with control date parameter
   - EVM metrics calculation endpoint
   - Historical progress reporting

### Non-Functional Requirements

- **Performance**: EVM calculations should complete within 500ms for standard queries
- **Accuracy**: Decimal precision (2 decimal places) for all currency calculations
- **Consistency**: Time-travel queries must use bitemporal filtering matching EVCS patterns
- **Testability**: Unit tests (80%+ coverage), integration tests, and API tests required
- **Maintainability**: Follow existing service/repository/model layered architecture
- **Auditability**: All progress updates and cost changes must preserve version history

### Constraints

- **Existing Framework**: Must leverage EVCS bitemporal versioning (TSTZRANGE)
- **No Breaking Changes**: Existing cost registration endpoints must remain functional
- **Database**: PostgreSQL 15+ with TSTZRANGE indexes
- **Backend Port**: 8020
- **Progress Tracking**: Manual entry only (no automated calculation in this iteration)
- **Scope**: Foundation only - does not include advanced features like forecasting or change order impact analysis

---

## Context Discovery

### Product Scope

**Relevant Domain Concepts:**
- **Earned Value Management (EVM)**: Project management methodology integrating scope, schedule, and cost for performance measurement
- **Progress Tracking**: Measuring work completion percentage against planned baseline
- **Bitemporal Versioning**: System tracks both valid_time (business validity) and transaction_time (system recording time)
- **Cost Elements**: Leaf-level budget entities where budgets are allocated and costs tracked (branchable)
- **Schedule Baselines**: 1-to-1 relationship with cost elements, defining time-phased budget progression via progression strategies
- **Cost Registrations**: Actual cost entries against cost elements (versionable but NOT branchable - global facts)

**Business Context:**
- Project managers need to track whether they're earning value as planned
- Progress reporting enables comparison of planned vs. actual work completion
- Cost tracking must support historical analysis (as-of queries) for audits and retrospectives
- Branch isolation allows change order scenarios to compare alternative budgets vs. actual costs

### Architecture Context

**Bounded Contexts Involved:**
1. **Cost Element & Financial Tracking** - Primary context for EVM calculations
2. **Schedule Baseline Management** - Provides Planned Value (PV) via progression strategies
3. **Cost Registration** - Source of Actual Costs (AC)
4. **Change Order & Branching** - Branch isolation for what-if scenarios
5. **Progress Tracking** - NEW context for this iteration

**Existing Patterns to Follow:**
- **TemporalService**: Base class for versioned entities with `get_as_of()` for time-travel
- **BranchableService**: Extends TemporalService with branch isolation (CostElement, ScheduleBaseline)
- **TemporalService (non-branchable)**: For versionable but non-branchable entities (CostRegistration, ProgressEntry)
- **Progression Strategies**: Strategy pattern for Linear, Gaussian, Logarithmic progression curves
- **Bitemporal Filtering**: Standardized WHERE clauses via `_apply_bitemporal_filter_for_time_travel()`

**Architectural Constraints:**
- Layered architecture: API Routes → Services → Repositories → Models
- Dependency injection for services via FastAPI `Depends()`
- Pydantic schemas for request/response validation
- Async/await throughout with AsyncSession
- Generic commands for versioned entities (CreateVersionCommand, UpdateVersionCommand)

### Codebase Analysis

**Backend - Existing Related Code:**

1. **Cost Registration Model** (`backend/app/models/domain/cost_registration.py`)
   - VersionableMixin (has valid_time, transaction_time, deleted_at)
   - NOT branchable (costs are global facts across all branches)
   - Fields: amount, quantity, unit_of_measure, registration_date, description, invoice_number
   - **Key Insight**: Already supports time-travel via `get_cost_registration_as_of()` in service

2. **Cost Registration Service** (`backend/app/services/cost_registration_service.py`)
   - Inherits from `TemporalService[CostRegistration]`
   - Has `get_total_for_cost_element(cost_element_id, as_of=None)` method (lines 232-280)
   - **Already implements time-travel filtering for cost aggregation**
   - Has budget validation (BudgetExceededError)
   - Has `get_budget_status()` method
   - **Missing**: Period-based aggregation (weekly, monthly)

3. **Cost Element Model** (`backend/app/models/domain/cost_element.py`)
   - VersionableMixin + BranchableMixin
   - Fields: budget_amount (for BAC), schedule_baseline_id (1:1 relationship)
   - **Missing**: progress_percentage field (needs to be added)

4. **Cost Element Service** (`backend/app/services/cost_element_service.py`)
   - Inherits from `BranchableService[CostElement]`
   - Has `get_cost_element_as_of(id, as_of, branch)` for time-travel (lines 627-724)
   - **Missing**: Progress tracking methods
   - **Missing**: EVM metrics calculation methods

5. **Schedule Baseline Service** (`backend/app/services/schedule_baseline_service.py`)
   - Inherits from `BranchableService[ScheduleBaseline]`
   - Has `get_for_cost_element()` method (lines 193-223)
   - Has `ensure_exists()` for auto-creation (lines 225-288)
   - Supports progression strategies (LINEAR, GAUSSIAN, LOGARITHMIC)

6. **Progression Strategies** (`backend/app/services/progression/`)
   - `ProgressionStrategy` interface with `calculate_progress(current_date, start_date, end_date) -> float`
   - Three implementations: LinearProgression, GaussianProgression, LogarithmicProgression
   - Used for PV calculation: **PV = BAC × Progress**

7. **PV Calculation Endpoint** (`backend/app/api/routes/schedule_baselines.py:244-323`)
   - Route: `GET /schedule-baselines/{id}/pv`
   - Parameters: current_date, bac, branch
   - Returns: PV calculation with progress
   - **Limitation**: Does NOT use time-travel (always gets current baseline)

8. **Temporal Service Base** (`backend/app/core/versioning/service.py`)
   - `get_as_of(entity_id, as_of, branch, branch_mode)` method (lines 142-197)
   - `_apply_bitemporal_filter_for_time_travel(stmt, as_of)` method (lines 344-377)
   - **Correctly implements System Time Travel semantics for single-entity queries**

**Frontend:**

- No existing EVM UI components identified
- Would need new components for:
  - Progress entry form
  - EVM metrics dashboard
  - Cost tracking reports
- State management: TanStack Query for server state, Zustand for client state

**Database:**

- PostgreSQL 15+ with TSTZRANGE support
- Existing tables: cost_elements, schedule_baselines, cost_registrations
- **Missing**: progress_entries table (needs to be created)

---

## Solution Options

### Option 1: Dedicated Progress Tracking Model with EVM Service (Recommended)

**Architecture & Design:**

Create a new versionable `ProgressEntry` model to track progress over time, plus a dedicated `EVMService` to orchestrate EVM metric calculations.

**Data Model Changes:**

```python
# New model: backend/app/models/domain/progress_entry.py
class ProgressEntry(EntityBase, VersionableMixin):
    """Progress tracking for cost elements - versionable, not branchable.

    Progress is tracked as a percentage (0-100) and is valid for a specific time period.
    Like cost registrations, progress is a global fact (not branchable) - work completed
    is the same across all change order branches.

    Attributes:
        progress_entry_id: Root ID for the progress entry aggregation
        cost_element_id: Reference to cost element
        progress_percentage: Progress value (0.0 to 100.0)
        reported_date: When progress was measured (business date)
        reported_by_user_id: User who reported the progress
        notes: Optional notes about progress
    """
    __tablename__ = "progress_entries"

    progress_entry_id: Mapped[UUID] = mapped_column(PG_UUID, nullable=False, index=True)
    cost_element_id: Mapped[UUID] = mapped_column(PG_UUID, ForeignKey("cost_elements.cost_element_id"), nullable=False, index=True)
    progress_percentage: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)  # 0.00 to 100.00
    reported_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    reported_by_user_id: Mapped[UUID] = mapped_column(PG_UUID, ForeignKey("users.user_id"), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
```

**Service Layer:**

```python
# New service: backend/app/services/progress_entry_service.py
class ProgressEntryService(TemporalService[ProgressEntry]):
    """Service for progress tracking (versionable, not branchable)."""

    async def create(self, progress_in: ProgressEntryCreate, actor_id: UUID) -> ProgressEntry:
        # Validate progress_percentage is 0-100
        # Use CreateVersionCommand

    async def get_latest_progress(self, cost_element_id: UUID, as_of: datetime | None = None) -> ProgressEntry | None:
        """Get the latest progress entry for a cost element as of a specific date."""

    async def get_progress_history(self, cost_element_id: UUID) -> list[ProgressEntry]:
        """Get all progress entries for a cost element (for charts)."""

# New service: backend/app/services/evm_service.py
class EVMService:
    """Service for calculating EVM metrics with time-travel support."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.ce_service = CostElementService(db)
        self.sb_service = ScheduleBaselineService(db)
        self.cr_service = CostRegistrationService(db)
        self.pe_service = ProgressEntryService(db)

    async def calculate_evm_metrics(
        self,
        cost_element_id: UUID,
        control_date: datetime,
        branch: str = "main"
    ) -> EVMMetricsResponse:
        """Calculate all EVM metrics as of control_date.

        1. Get cost element as of control_date → BAC
        2. Get schedule baseline as of control_date → PV
        3. Get cost registrations as of control_date → AC
        4. Get latest progress as of control_date → EV
        5. Calculate variances and indices
        """
```

**API Endpoints:**

```
POST   /api/v1/progress-entries                    # Create progress entry
GET    /api/v1/progress-entries/{id}               # Get progress entry
GET    /api/v1/progress-entries                    # List progress entries
GET    /api/v1/cost-elements/{id}/progress         # Get latest progress
GET    /api/v1/cost-elements/{id}/progress/history # Get progress history

GET    /api/v1/cost-elements/{id}/evm              # Calculate EVM metrics
       Query params: control_date, branch
```

**UX Design:**

- Progress entry form with slider/input for 0-100%
- EVM dashboard showing BAC, PV, AC, EV, CV, SV, CPI, SPI
- Historical charts for progress over time
- Cost tracking tables with cumulative sums

**Implementation:**

**Phase 1: Progress Tracking Foundation**
1. Create ProgressEntry model
2. Create migration for progress_entries table
3. Create ProgressEntryService with CRUD operations
4. Create API routes for progress entries
5. Write unit and integration tests

**Phase 2: EVM Calculation Service**
1. Create EVMService with time-travel support
2. Implement calculate_evm_metrics() method
3. Create EVMMetricsRead schema
4. Add GET /cost-elements/{id}/evm endpoint
5. Write tests for EVM calculations

**Phase 3: Enhanced Cost Queries**
1. Add period-based aggregation methods to CostRegistrationService
2. Add GET /cost-registrations/aggregated endpoint
3. Support daily/weekly/monthly aggregation
4. Write tests

**Trade-offs:**

| Aspect          | Assessment                           |
| --------------- | ------------------------------------ |
| Pros            | - Clear separation of concerns       |
|                 | - Progress is versionable (full audit trail) |
|                 | - Reuses existing temporal framework |
|                 | - Easy to test independently         |
|                 | - Follows established EVCS patterns  |
| Cons            | - Adds new model and service (3-4 new files) |
|                 | - Requires database migration        |
|                 | - Slightly more complex than denormalized approach |
| Complexity      | Medium                               |
| Maintainability | Excellent                            |
| Performance     | Good (can optimize with indexes)     |
| Scalability     | Excellent (follows existing patterns) |

---

### Option 2: Denormalized Progress on Cost Element

**Architecture & Design:**

Add `progress_percentage` field directly to CostElement model and track progress via version updates.

**Data Model Changes:**

```python
# Modify existing: backend/app/models/domain/cost_element.py
class CostElement(EntityBase, VersionableMixin, BranchableMixin):
    # ... existing fields ...

    progress_percentage: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2), nullable=True,
        comment="Current progress percentage (0-100)"
    )
    progress_last_updated: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
        comment="When progress was last reported"
    )
```

**Service Layer:**

- Add `update_progress()` method to CostElementService
- Create EVMService similar to Option 1
- No separate ProgressEntryService needed

**UX Design:**

Same as Option 1 for EVM dashboard, but progress updates go through cost element update endpoint.

**Implementation:**

Simpler than Option 1:
1. Add fields to CostElement model
2. Create migration to add columns
3. Add update_progress() method to CostElementService
4. Create EVMService
5. Add EVM endpoint

**Trade-offs:**

| Aspect          | Assessment                           |
| --------------- | ------------------------------------ |
| Pros            | - Simpler data model (no new table)  |
|                 | - Progress always in sync with cost element version |
|                 | - Fewer joins for queries            |
|                 | - Faster to implement (1-2 days)     |
| Cons            | - Loses detailed progress history     |
|                 | - Harder to audit progress changes   |
|                 | - Bloats CostElement versions        |
|                 | - Can't track progress notes separately |
|                 | - Violates single responsibility principle (budget + progress) |
| Complexity      | Low                                  |
| Maintainability | Fair                                 |
| Performance     | Excellent (fewer joins)              |
| Scalability     | Poor (progress history lost)         |

---

### Option 3: Embedded Progress History via JSONB

**Architecture & Design:**

Store progress history as a JSONB array on CostElement model.

**Data Model Changes:**

```python
class CostElement(EntityBase, VersionableMixin, BranchableMixin):
    # ... existing fields ...

    progress_history: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True,
        comment="Progress history: [{date, percentage, user_id, notes}, ...]"
    )
    current_progress: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=0
    )
```

**Service Layer:**

- Add `update_progress()` method that appends to JSONB array
- Create EVMService similar to Option 1
- JSONB queries for historical analysis

**Trade-offs:**

| Aspect          | Assessment                           |
| --------------- | ------------------------------------ |
| Pros            | - No new table                       |
|                 | - Progress history preserved         |
|                 | - Simple CRUD operations             |
| Cons            | - JSONB is harder to query than relational table |
|                 | - Can't use temporal versioning for progress |
|                 | - Harder to audit (changes in JSONB, not versions) |
|                 | - Doesn't follow EVCS patterns       |
|                 | - Complex queries for time-travel    |
| Complexity      | Medium                               |
| Maintainability | Poor                                 |
| Performance     | Good (JSONB is fast)                 |
| Scalability     | Fair (query complexity grows)        |

**Note:** Not recommended due to deviation from EVCS patterns and loss of bitemporal audit trail.

---

## Comparison Summary

| Criteria                | Option 1 (ProgressEntry Model) | Option 2 (Denormalized) | Option 3 (JSONB) |
| ----------------------- | ------------------------------ | ----------------------- | ---------------- |
| Development Effort      | 3-4 days                       | 1-2 days                | 2-3 days         |
| Architecture Quality    | Excellent                      | Good                    | Poor             |
| Progress History        | Full audit trail               | Lost on update          | Partial          |
| Time-Travel Support     | Full bitemporal                | Via cost element version | Complex queries  |
| Testability             | Excellent                      | Good                    | Fair             |
| Separation of Concerns  | Excellent                      | Fair                    | Poor             |
| Follows EVCS Patterns   | Yes                            | Partially               | No               |
| Audit Trail Quality     | Excellent                      | Fair                    | Poor             |
| Query Performance       | Good (with indexes)            | Excellent               | Good             |
| Best For                | Production system               | Quick prototype         | Not recommended  |

---

## Recommendation

**I recommend Option 1 (Dedicated Progress Tracking Model with EVM Service)** because:

1. **Architectural Integrity**: Follows the established EVCS bitemporal versioning patterns
2. **Complete Audit Trail**: Progress changes are versioned with full history (valid_time + transaction_time)
3. **Separation of Concerns**: Progress tracking is a distinct domain concept from budget allocation
4. **Time-Travel Support**: Can query progress "as of" any date using existing temporal framework
5. **Testability**: Independent service and model are easy to unit test
6. **Reusability**: ProgressEntryService can be used by other components (reports, dashboards, batch jobs)
7. **Consistency**: Matches the pattern used for CostRegistration (global facts, versionable, not branchable)
8. **Future-Proof**: Enables future features like progress approvals, automated progress calculation, variance analysis

**Alternative consideration:** Choose Option 2 only if you need to implement this as a spike/prototype and plan to refactor later. However, the extra 1-2 days of development for Option 1 is worth the long-term maintainability and auditability benefits.

---

## Decision Questions

1. **Progress Granularity**: Should progress be tracked:
   - Per cost element (recommended)?
   - Per work breakdown element (higher level)?
   - Per department (aggregated view)?

2. **Progress Validation**: Should the system validate that progress:
   - Only increases (monotonically)?
   - Can decrease (if work is undone)?
   - Has no validation (user responsibility)?

3. **Progress Frequency**: How often can progress be reported:
   - Once per day (recommended)?
   - Multiple times per day?
   - Unlimited (any timestamp)?

4. **EVM Metric Behavior**: When calculating EV, if no progress has been reported:
   - Return EV = 0 (explicit null)?
   - Return EV = 0 with a warning?
   - Return null for all EVM metrics?

5. **Cost Aggregation Periods**: For time-based cost aggregation, which periods are needed:
   - Daily (recommended for foundation)?
   - Weekly?
   - Monthly?
   - All three?

6. **Performance Optimization**: For large cost element sets with many registrations:
   - Implement database-level aggregations (custom SQL with GROUP BY)?
   - Use application-level summation (simpler, slower)?
   - Cache EVM calculations for common control dates?

---

## Implementation Checklist (Option 1)

### Phase 1: Progress Tracking Foundation

**Data Model:**
- [ ] Create `backend/app/models/domain/progress_entry.py`
  - ProgressEntry class with VersionableMixin
  - Fields: progress_entry_id, cost_element_id, progress_percentage, reported_date, reported_by_user_id, notes
  - Constraints: progress_percentage 0-100, reported_date required
- [ ] Create Alembic migration for progress_entries table
  - Add table with TSTZRANGE columns (valid_time, transaction_time)
  - Add indexes on cost_element_id, reported_date, progress_entry_id
  - Add GIST indexes for range queries

**Service Layer:**
- [ ] Create `backend/app/services/progress_entry_service.py`
  - ProgressEntryService inheriting from TemporalService[ProgressEntry]
  - create() method with validation (0-100 range)
  - get_latest_progress(cost_element_id, as_of) method
  - get_progress_history(cost_element_id) method
  - get_all_progress_for_cost_element() with pagination

**API Layer:**
- [ ] Create `backend/app/api/routes/progress_entries.py`
  - POST /progress-entries (create)
  - GET /progress-entries/{id} (get by ID with as_of support)
  - GET /progress-entries (list with filters)
  - DELETE /progress-entries/{id} (soft delete)
- [ ] Add routes to `backend/app/api/routes/__init__.py`

**Schemas:**
- [ ] Create `backend/app/models/schemas/progress_entry.py`
  - ProgressEntryBase
  - ProgressEntryCreate
  - ProgressEntryUpdate
  - ProgressEntryRead

**Tests:**
- [ ] `backend/tests/unit/models/test_progress_entry.py`
- [ ] `backend/tests/unit/services/test_progress_entry_service.py`
- [ ] `backend/tests/api/test_progress_entries.py`
- [ ] `backend/tests/integration/test_progress_time_travel.py`

### Phase 2: EVM Calculation Service

**Service Layer:**
- [ ] Create `backend/app/services/evm_service.py`
  - EVMService class (does NOT inherit from TemporalService)
  - calculate_evm_metrics(cost_element_id, control_date, branch) method
  - _get_bac_as_of() helper
  - _get_pv_as_of() helper
  - _get_ac_as_of() helper
  - _get_ev_as_of() helper
  - _calculate_variants() helper
  - _calculate_indices() helper

**Schemas:**
- [ ] Create `backend/app/models/schemas/evm.py`
  - EVMMetricsRead schema with all EVM metrics
  - Include metadata (version IDs, control_date, timestamps)

**API Layer:**
- [ ] Add route to `backend/app/api/routes/cost_elements.py`
  - GET /cost-elements/{id}/evm
  - Query params: control_date, branch
  - Return EVMMetricsRead

**Tests:**
- [ ] `backend/tests/unit/services/test_evm_service.py`
  - Test BAC calculation
  - Test PV calculation with time-travel
  - Test AC calculation with time-travel
  - Test EV calculation
  - Test variance calculations (CV, SV)
  - Test index calculations (CPI, SPI)
  - Test edge cases (no progress, no costs, no baseline)
- [ ] `backend/tests/api/test_evm_metrics.py`
  - Test API endpoint with various control dates
  - Test branch isolation
  - Test error handling

### Phase 3: Enhanced Cost Queries

**Service Layer:**
- [ ] Extend `backend/app/services/cost_registration_service.py`
  - get_costs_by_period(cost_element_id, period, start_date, end_date) method
  - get_cumulative_costs(cost_element_id, as_of) method
  - Support for 'daily', 'weekly', 'monthly' periods

**API Layer:**
- [ ] Add routes to `backend/app/api/routes/cost_registrations.py`
  - GET /cost-registrations/aggregated
  - Query params: cost_element_id, period, start_date, end_date
  - Return aggregated costs by period

**Tests:**
- [ ] `backend/tests/unit/services/test_cost_aggregation.py`
- [ ] `backend/tests/api/test_cost_aggregation.py`

### Phase 4: Integration & Documentation

**Integration:**
- [ ] Update API documentation (OpenAPI)
- [ ] Add EVM calculation guide to docs
- [ ] Document progress tracking workflow
- [ ] Create examples for common use cases

**Frontend (Optional - out of scope for backend iteration):**
- [ ] Progress entry form component
- [ ] EVM metrics dashboard component
- [ ] Cost tracking charts
- [ ] Historical progress visualization

---

## References

**Architecture Documentation:**
- [ADR-005: Bitemporal Versioning](/home/nicola/dev/backcast_evs/docs/02-architecture/decisions/adr-005-bitemporal-versioning.md)
- [Bounded Contexts](/home/nicola/dev/backcast_evs/docs/02-architecture/01-bounded-contexts.md)
- [System Architecture](/home/nicola/dev/backcast_evs/docs/02-architecture/00-system-map.md)

**Existing Code:**
- [CostRegistration Model](/home/nicola/dev/backcast_evs/backend/app/models/domain/cost_registration.py)
- [CostRegistration Service](/home/nicola/dev/backcast_evs/backend/app/services/cost_registration_service.py)
- [CostElement Service](/home/nicola/dev/backcast_evs/backend/app/services/cost_element_service.py)
- [ScheduleBaseline Service](/home/nicola/dev/backcast_evs/backend/app/services/schedule_baseline_service.py)
- [TemporalService Base](/home/nicola/dev/backcast_evs/backend/app/core/versioning/service.py)
- [Progression Strategies](/home/nicola/dev/backcast_evs/backend/app/services/progression/)

**Related Iterations:**
- [2026-01-18: Time-Aware EVM Analysis](/home/nicola/dev/backcast_evs/docs/03-project-plan/iterations/2026-01-18-time-aware-evm-analysis/00-analysis.md)
- [2026-01-18: Schedule Baseline Architecture](/home/nicola/dev/backcast_evs/docs/03-project-plan/iterations/2026-01-18-schedule-baseline-architecture/)
- [2026-01-15: Register Actual Costs](/home/nicola/dev/backcast_evs/docs/03-project-plan/iterations/2026-01-15-register-actual-costs/)

**EVM References:**
- [Earned Value Management (Wikipedia)](https://en.wikipedia.org/wiki/Earned_value_management)
- [EVM Formulas Guide](https://www.pmi.org/about/learn-about-pmi/what-is-project-management/earned-value-management)
