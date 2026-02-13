# Analysis: [E05-U04] Define Schedule Baselines with Progression Types

**Created:** 2026-01-15
**Request:** Implement schedule baseline functionality to define planned work progression over time with configurable progression types (linear/gaussian/logarithmic) for Planned Value (PV) calculations.

---

## Clarified Requirements

### Functional Requirements

Based on the product backlog and bounded contexts:

1. **Schedule Baseline Entity**

   - Create a new domain entity `ScheduleBaseline` to define planned work progression
   - Required fields: `schedule_baseline_id`, `cost_element_id`, `start_date`, `end_date`, `progression_type`
   - Optional fields: `description`
   - Each baseline defines how work progresses over time for a specific cost element
   - **Versioned AND branchable** (like `CostElement` - can be part of change order configuration per PMI standards)

2. **Progression Types**

   - **Linear**: Constant rate of progress (default)
     - Formula: `progress = (current_date - start_date) / (end_date - start_date)`
   - **Gaussian**: Bell curve progression (S-curve)
     - Formula: `progress = gaussian_cdf(current_date, mean, std_dev)`
     - Acceleration in middle, slower at start/end
   - **Logarithmic**: Front-loaded progression
     - Formula: `progress = log(current_date - start_date + 1) / log(end_date - start_date + 1)`
     - Rapid early progress, tapering off

3. **Planned Value (PV) Calculation Support**

   - PV = BAC × % Planned Completion (derived from schedule baseline)
   - Time-phased calculation: PV at any point in time based on progression function
   - Enables EVM metric: SPI = EV / PV (Schedule Performance Index)

4. **Versioning Support (Branchable)**

   - Schedule baselines support **bitemporal versioning** and **branching** (like `CostElement`)
   - Use `VersionableMixin` AND `BranchableMixin`
   - Track schedule changes over time for audit trail
   - Enable time-travel queries for historical PV analysis
   - Soft delete capability for reversibility
   - Baselines are **branchable** - can be modified in change orders per PMI standards
   - Change order branches can have different schedule configurations for impact analysis

5. **API Endpoints**
   - CRUD operations for schedule baselines
   - List endpoint with filtering (by cost_element, date range, progression type)
   - PV calculation endpoint: `GET /schedule-baselines/{id}/planned-value?as_of={date}`
   - Progress preview endpoint: `GET /schedule-baselines/{id}/progress?from={date}&to={date}`

### Non-Functional Requirements

- **Performance**: <100ms for single baseline, <200ms for PV calculation
- **Calculation Accuracy**: IEEE 754 double precision for progression functions
- **Data Integrity**: Atomic operations, rollback on validation failure
- **Type Safety**: Strict typing with Pydantic V2, MyPy compliance
- **Test Coverage**: 80%+ minimum, 100% for progression calculations
- **Extensibility**: Support custom progression types in future (plugin architecture)

### Constraints

- Must use existing EVCS patterns (BranchableService, command pattern)
- **Must be branchable** - baselines are part of change order configuration per PMI standards
- Must maintain backward compatibility with existing cost element structure
- Progression type functions must be pure (no side effects)
- PV calculations must match EVM standard (PMI practice)
- Change order impact analysis must compare branch schedule baselines to main

---

## Context Discovery

### Product Scope

**Relevant User Stories:**

- E05-U04: Define Schedule Baselines with Progression Types (current)
- E08-U01: Calculate PV using Schedule Baselines (dependent)
- E08-U04: View Performance Indices (CPI/SPI/TCPI) (depends on PV)

**Business Requirements:**

- Schedule management for planned value calculations
- Enables Schedule Performance Index (SPI) measurement
- Supports time-phased budget distribution
- Foundation for EVM variance analysis (SV = EV - PV)

### Architecture Context

**Bounded Contexts Involved:**

1. **Cost Element & Financial Tracking** (Context 6) - Primary context

   - ScheduleBaseline is a new entity within this context
   - Relates to existing CostElement entity
   - Used by EVM Calculations & Reporting context
   - Similar to ScheduleRegistration mentioned in bounded contexts

2. **EVCS Core** (Context 0) - Versioning framework

   - ScheduleBaseline uses `VersionableMixin` AND `BranchableMixin`
   - Follows `CostElement` pattern (fully branchable for change orders)
   - Time-travel capability for historical analysis

3. **EVM Calculations & Reporting** (Context 8) - Consumer
   - PV calculations depend on schedule baselines
   - Performance indices (SPI, TCPI) use PV as input
   - Variance analysis (SV = EV - PV)

**Existing Patterns to Follow:**

- Service Layer Pattern: `BranchableService[TBranchable]` for full branch support
- Command Pattern: `CreateVersionCommand`, `UpdateVersionCommand`
- API Route Conventions: Standard CRUD with RBAC via `RoleChecker`
- Pydantic V2 Strict Mode: All schemas with `ConfigDict(strict=True)`
- Pagination: `PaginatedResponse` with server-side filtering

**Architectural Constraints:**

- Must use PostgreSQL with asyncpg
- SQLAlchemy ORM with `Mapped[]` column syntax
- Entity must satisfy `BranchableProtocol` (VersionableMixin + BranchableMixin)
- API responses must follow OpenAPI spec for client generation
- Progression calculations must be pure functions (testable, reusable)

### Codebase Analysis

**Backend:**

**Existing Related APIs:**

- [cost_elements.py](../../../../backend/app/api/routes/cost_elements.py) - Cost Element CRUD patterns
- [cost_element_service.py](../../../../backend/app/services/cost_element_service.py) - Service layer patterns
- [cost_element.py](../../../../backend/app/models/domain/cost_element.py) - Domain model patterns

**Data Models:**

- `CostElement` ([cost_element.py:22-52](../../../../backend/app/models/domain/cost_element.py#L22-L52)) - **Pattern to follow**

  - Uses `TemporalBase`, `BranchableMixin`, `VersionableMixin`
  - Key relationship: `cost_element_id` (root ID)
  - Has `budget_amount` (BAC for PV calculations)
  - Branchable entity for change order configuration

- `CostElementType` ([cost_element_type.py:21-44](../../../../backend/app/models/domain/cost_element_type.py#L21-L44)) - Versionable but NOT branchable
  - Uses `VersionableMixin` only (no `BranchableMixin`)
  - Satisfies `VersionableProtocol`
  - Has `cost_element_type_id` as root ID

**Similar Patterns:**

- CRUD pattern from [cost_elements.py](../../../../backend/app/api/routes/cost_elements.py)
- Service layer with `BranchableService[T]` pattern (not `TemporalService`)
- Command pattern for create/update operations
- List endpoint with `FilterParser`, pagination, sorting

**Frontend:**

**Comparable Components:**

- [CostElementModal.tsx](../../../frontend/src/features/cost-elements/components/CostElementModal.tsx) - Modal form patterns
- Uses Ant Design Form with validation
- Date range pickers for start/end dates
- Select dropdown for progression type

**State Management:**

- TanStack Query for server state (via `createResourceHooks`)
- Ant Design Form for form state
- URL-driven navigation for entity detail views

**Routing Structure:**

- `/projects/:projectId` - Project detail with nested routes
- `/projects/:projectId/wbes/:wbeId` - WBE detail with cost elements
- New route: `/cost-elements/:costElementId/schedule` for schedule baselines

**Technical Debt:**

- No existing schedule baseline entity or patterns
- Progression calculation functions need to be designed
- PV calculation endpoint needs to be efficient for time-phased queries

---

## Solution Design

### Recommended Approach: Versioned & Branchable ScheduleBaseline with Pure Progression Functions

**Architecture & Design:**

**Backend Layer Design:**

```
API Routes (app/api/routes/schedule_baselines.py)
    ↓
Service Layer (app/services/schedule_baseline_service.py)
    ↓ extends
BranchableService[ScheduleBaseline]  # Full branch support per PMI standards
    ↓ uses
Command Pattern (CreateVersionCommand, UpdateVersionCommand)
    ↓
Model Layer (app/models/domain/schedule_baseline.py)
    ↓ extends VersionableMixin AND BranchableMixin
    ↓
Database Table (schedule_baselines)

Progression Module (app/services/progression/)
    ├── __init__.py
    ├── base.py          # ProgressionFunction protocol
    ├── linear.py        # LinearProgression
    ├── gaussian.py      # GaussianProgression
    └── logarithmic.py   # LogarithmicProgression
```

**Key Design Decisions:**

1. **Branchable Versioning (Per PMI Standards)**

   ```python
   class ScheduleBaseline(EntityBase, VersionableMixin, BranchableMixin):
       """Versioned and branchable schedule baseline for change orders."""
       __tablename__ = "schedule_baselines"

       # Root ID
       schedule_baseline_id: Mapped[UUID] = mapped_column(...)

       # Relations
       cost_element_id: Mapped[UUID] = mapped_column(...)

       # Schedule fields
       start_date: Mapped[date] = mapped_column(...)
       end_date: Mapped[date] = mapped_column(...)
       progression_type: Mapped[ProgressionType] = mapped_column(...)

       # Metadata
       description: Mapped[str | None] = mapped_column(...)

       # Inherits from VersionableMixin:
       # - valid_time, transaction_time, deleted_at
       # - created_by, deleted_by

       # Inherits from BranchableMixin:
       # - branch, parent_id, merge_from_branch
   ```

2. **Progression Functions (Pure, Testable)** - unchanged from previous design

   ```python
   # app/services/progression/base.py
   from typing import Protocol
   from datetime import date

   class ProgressionFunction(Protocol):
       """Protocol for progression functions."""

       def calculate_progress(
           self,
           current_date: date,
           start_date: date,
           end_date: date
       ) -> float:
           """Calculate progress ratio (0.0 to 1.0) for given date."""
           ...

   # app/services/progression/linear.py
   class LinearProgression:
       """Constant rate of progress."""

       def calculate_progress(
           self,
           current_date: date,
           start_date: date,
           end_date: date
       ) -> float:
           if current_date <= start_date:
               return 0.0
           if current_date >= end_date:
               return 1.0

           total_days = (end_date - start_date).days
           elapsed_days = (current_date - start_date).days
           return elapsed_days / total_days

   # app/services/progression/gaussian.py
   import math
   from scipy.stats import norm  # or pure python implementation

   class GaussianProgression:
       """Bell curve progression (S-curve)."""

       def __init__(self, mean_percent: float = 0.5, std_dev_percent: float = 0.15):
           # Mean at 50% of timeline, std dev at 15%
           self.mean_percent = mean_percent
           self.std_dev_percent = std_dev_percent

       def calculate_progress(
           self,
           current_date: date,
           start_date: date,
           end_date: date
       ) -> float:
           if current_date <= start_date:
               return 0.0
           if current_date >= end_date:
               return 1.0

           total_days = (end_date - start_date).days
           elapsed_days = (current_date - start_date).days
           percent_complete = elapsed_days / total_days

           # Gaussian CDF
           z_score = (percent_complete - self.mean_percent) / self.std_dev_percent
           return float(norm.cdf(z_score))

   # app/services/progression/logarithmic.py
   import math

   class LogarithmicProgression:
       """Front-loaded progression."""

       def calculate_progress(
           self,
           current_date: date,
           start_date: date,
           end_date: date
       ) -> float:
           if current_date <= start_date:
               return 0.0
           if current_date >= end_date:
               return 1.0

           total_days = (end_date - start_date).days
           elapsed_days = (current_date - start_date).days

           # Logarithmic progression
           numerator = math.log(elapsed_days + 1)
           denominator = math.log(total_days + 1)
           return numerator / denominator
   ```

3. **Service Layer with PV Calculation**

   ```python
   class ScheduleBaselineService(BranchableService[ScheduleBaseline]):
       """Service for versioned, branchable schedule baselines (PMI standard)."""

       def __init__(self):
           self.progression_functions = {
               ProgressionType.LINEAR: LinearProgression(),
               ProgressionType.GAUSSIAN: GaussianProgression(),
               ProgressionType.LOGARITHMIC: LogarithmicProgression(),
           }

       async def calculate_planned_value(
           self,
           schedule_baseline_id: UUID,
           as_of: date,
           bac: Decimal,
           session: AsyncSession,
           branch: str = "main"
       ) -> Decimal:
           """Calculate Planned Value (PV) as of specific date.

           PV = BAC × % Planned Completion (from progression function)
           """
           baseline = await self.get_by_root_id(schedule_baseline_id, branch=branch, session=session)

           progression_fn = self.progression_functions[baseline.progression_type]
           progress = progression_fn.calculate_progress(
               current_date=as_of,
               start_date=baseline.start_date,
               end_date=baseline.end_date
           )

           return Decimal(str(bac * Decimal(str(progress))))
   ```

4. **Enum for Progression Types**

   ```python
   from enum import Enum

   class ProgressionType(str, Enum):
       """Progression types for schedule baselines."""

       LINEAR = "linear"
       GAUSSIAN = "gaussian"
       LOGARITHMIC = "logarithmic"
   ```

**Component Structure (Frontend):**

```
features/schedule-baselines/
├── components/
│   ├── ScheduleBaselineList.tsx       # Table with filters
│   ├── ScheduleBaselineModal.tsx      # Create/Edit form
│   ├── ProgressionTypeSelect.tsx      # Progression type dropdown with descriptions
│   └── ProgressionChart.tsx           # Visual preview of progression curve
├── hooks/
│   └── useScheduleBaselines.ts        # TanStack Query hooks
└── types.ts
```

**State Management Approach:**

- Server State: TanStack Query (auto-refetch on mutations)
- Form State: Ant Design Form
- Local State: Modal visibility, chart preview data

**Data Flow and API Interactions:**

```
User creates schedule baseline
    ↓
Form validation (client-side: end_date > start_date)
    ↓
POST /api/v1/schedule-baselines
    ↓
Service validates dates and cost element exists
    ↓
If valid: CreateVersionCommand executes (BranchableService)
    ↓
Returns ScheduleBaselineRead
    ↓
TanStack Query invalidates related queries

User requests Planned Value
    ↓
GET /api/v1/schedule-baselines/{id}/planned-value?as_of=2026-01-15&branch=main
    ↓
Service retrieves baseline and CostElement.budget_amount (BAC)
    ↓
Progression function calculates progress ratio
    ↓
Returns PV = BAC × progress
```

**Key Design Patterns Applied:**

- **Strategy Pattern**: Progression functions as interchangeable strategies
- **Protocol Pattern**: `ProgressionFunction` protocol for extensibility
- **Repository Pattern**: `BranchableService` for versioned, branchable data access
- **Command Pattern**: Versioned create/update operations
- **Dependency Injection**: FastAPI `Depends()` for service and auth
- **Factory Pattern**: Progression function registry

**UX Design:**

**User Stories:**

1. As a project manager, I want to define schedule baselines for cost elements to establish planned work progression
2. As a project manager, I want to choose progression types to model different work patterns
3. As a project manager, I want to see Planned Value at any point in time to track schedule performance

**User Interaction Flow:**

```
Navigate to Cost Element Detail
    ↓
Click "Schedule" tab
    ↓
View Schedule Baselines table (list of baselines for this cost element)
    ↓
Click "Add Schedule Baseline" button
    ↓
Modal opens with form
    ↓
Fill in: start_date, end_date, progression_type (with descriptions)
    ↓
Visual preview of progression curve updates in real-time
    ↓
Submit → Validation (end_date > start_date)
    ↓
Success: Table refreshes
    ↓
Error: Inline validation message
```

**Visual Hierarchy and Layout:**

1. **Header**: Cost Element name, breadcrumb navigation
2. **Tab Navigation**: "Overview" | "Budget & Costs" | "Schedule" | "History"
3. **Schedule Baselines Table**:
   - Columns: Start Date, End Date, Progression Type, Branch, Actions
   - Visual indicator for active baseline
4. **Action Bar**: "Add Schedule Baseline" button
5. **Progression Preview**: When editing, show curve chart with start/end dates marked

**Navigation Patterns:**

- URL-driven: `/projects/:id/wbes/:wbeId/cost-elements/:ceId/schedule`
- Tab navigation: "Overview" | "Budget & Costs" | "Schedule" | "History"
- Breadcrumb: Projects > Project X > WBE Y > Cost Element Z > Schedule

**Accessibility Considerations:**

- Keyboard navigation for all actions
- ARIA labels for progression type descriptions
- High contrast colors for chart visualization
- Screen reader support for validation messages

**Edge Cases and Error States:**

1. **Invalid Date Range**: Modal error when `end_date <= start_date`
2. **Cost Element Deleted**: Redirect to parent WBE with notification
3. **Progression Calculation Error**: Return 0.0 progress with error log
4. **No Baseline Defined**: PV calculation returns 0 or uses default linear progression

**Technical Implementation:**

**Key Files to Create/Modify:**

**Backend:**

- `backend/app/models/domain/schedule_baseline.py` (NEW)
  - Extends `EntityBase`, `VersionableMixin` AND `BranchableMixin`
- `backend/app/services/schedule_baseline_service.py` (NEW)
  - Extends `BranchableService[ScheduleBaseline]`
- `backend/app/services/progression/` (NEW)
  - `base.py` - ProgressionFunction protocol
  - `linear.py` - LinearProgression implementation
  - `gaussian.py` - GaussianProgression implementation
  - `logarithmic.py` - LogarithmicProgression implementation
- `backend/app/api/routes/schedule_baselines.py` (NEW)
  - Standard CRUD endpoints with PV calculation endpoint
- `backend/app/models/schemas/schedule_baseline.py` (NEW)
  - Pydantic V2 strict schemas
- `backend/alembic/versions/xxx_create_schedule_baselines.py` (NEW)
  - Table creation with indexes

**Frontend:**

- `frontend/src/features/schedule-baselines/components/*` (NEW)
- `frontend/src/features/cost-elements/components/CostElementDetail.tsx` (MODIFY)
  - Add "Schedule" tab

**Integration Points:**

- CostElementService: Add `get_budget_amount(cost_element_id)` for BAC
- EVMCalculationService: Use `ScheduleBaselineService.calculate_planned_value()`
- RBAC: New permission `schedule-baseline-create`
- API Client: Auto-generate from OpenAPI spec

**Database Schema:**

```sql
CREATE TYPE progression_type AS ENUM ('linear', 'gaussian', 'logarithmic');

CREATE TABLE schedule_baselines (
    id UUID PRIMARY KEY,
    schedule_baseline_id UUID NOT NULL,
    cost_element_id UUID NOT NULL REFERENCES cost_elements(cost_element_id),
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    progression_type progression_type NOT NULL DEFAULT 'linear',
    description TEXT,

    -- Versioning fields (from VersionableMixin)
    valid_time TSTZRANGE NOT NULL,
    transaction_time TSTZRANGE NOT NULL,
    deleted_at TIMESTAMP,
    created_by UUID NOT NULL,
    deleted_by UUID,

    -- Branching fields (from BranchableMixin)
    branch VARCHAR(255) NOT NULL DEFAULT 'main',
    parent_id UUID,
    merge_from_branch VARCHAR(255)
);

-- Indexes for performance
CREATE INDEX idx_schedule_baselines_element_id ON schedule_baselines(cost_element_id);
CREATE INDEX idx_schedule_baselines_dates ON schedule_baselines(start_date, end_date);
CREATE INDEX idx_schedule_baselines_branch ON schedule_baselines(branch);
CREATE INDEX idx_schedule_baselines_valid_time ON schedule_baselines USING GIST(valid_time);
CREATE INDEX idx_schedule_baselines_transaction_time ON schedule_baselines USING GIST(transaction_time);

-- Constraint: end_date must be after start_date
ALTER TABLE schedule_baselines
ADD CONSTRAINT check_date_range CHECK (end_date > start_date);
```

**Potential Technical Challenges:**

1. **Gaussian Progression Implementation**

   - **Challenge**: Gaussian CDF requires scipy or custom implementation
   - **Solution**: Use pure Python approximation with `math.erf()` (built-in)
     ```python
     import math
     def gaussian_cdf(x: float, mean: float = 0.5, std_dev: float = 0.15) -> float:
         z = (x - mean) / std_dev
         return 0.5 * (1 + math.erf(z / math.sqrt(2)))
     ```

2. **Logarithmic Edge Cases**

   - **Challenge**: `log(0)` is undefined, `log(1) = 0`
   - **Solution**: Add offset to avoid log(0): `log(elapsed_days + 1)`

3. **PV Calculation Performance**

   - **Challenge**: Time-phased PV queries may be slow for multiple dates
   - **Solution**: Cache progression results, batch calculate for date ranges

4. **Progression Visualization**
   - **Challenge**: Rendering accurate S-curves in frontend
   - **Solution**: Use chart library (Recharts/ECharts) with backend-provided data points

**Performance Optimizations:**

1. **Progression Function Caching**

   ```python
   from functools import lru_cache

   @lru_cache(maxsize=1000)
   def calculate_progress_cached(
       progression_type: str,
       start_date: date,
       end_date: date,
       current_date: date
   ) -> float:
       """Cached progression calculation."""
       fn = progression_functions[progression_type]
       return fn.calculate_progress(current_date, start_date, end_date)
   ```

2. **Batch PV Calculation**
   ```python
   async def calculate_planned_value_range(
       self,
       schedule_baseline_id: UUID,
       date_range: tuple[date, date],
       bac: Decimal
   ) -> list[tuple[date, Decimal]]:
       """Calculate PV for multiple dates (e.g., monthly reporting)."""
       # Single query, multiple calculations
   ```

**Testing Approach (High-Level):**

**Unit Tests:**

- Progression function calculations (exact values for known inputs)
- Edge cases: dates before start, after end, at boundaries
- Invalid date range validation

**Integration Tests:**

- Full CRUD operations with versioning
- PV calculation endpoint with different progression types
- Time-travel queries (as_of parameter)

**Mathematical Tests:**

- Linear progression: exact arithmetic
- Gaussian progression: CDF properties (monotonic, bounds)
- Logarithmic progression: concavity, asymptotic behavior

**E2E Tests:**

- User creates schedule baseline, sees progression preview
- User requests PV calculation, sees correct value
- User switches progression types, sees curve change

**Trade-offs:**

| Aspect          | Assessment                                                                                                                                                                           |
| --------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Pros            | • Enables PV calculation for EVM<br>• Extensible progression function design<br>• Versioned for audit trail<br>• Pure functions for testing<br>• Supports schedule variance analysis |
| Cons            | • Gaussian complexity (requires math library)<br>• Additional entity to maintain<br>• Progression types may confuse users<br>• Performance considerations for calculations           |
| Complexity      | Medium - Leverages EVCS, adds progression logic                                                                                                                                      |
| Maintainability | Good - Follows established patterns                                                                                                                                                  |
| Performance     | Expected <100ms for CRUD, <200ms for PV with caching                                                                                                                                 |

---

## Implementation Roadmap

### Phase 1: Backend Foundation (Days 1-2)

**Tasks:**

1. Create `ScheduleBaseline` model (versioned AND branchable)
2. Create `ScheduleBaselineService` (extends `BranchableService`)
3. Implement progression functions (linear, gaussian, logarithmic)
4. Add validation logic (date ranges, cost element exists)
5. Create database migration with indexes

**Deliverables:**

- Working CRUD API for schedule baselines
- Progression function module with pure functions
- Time-travel query support
- Branch isolation for change orders

### Phase 2: PV Calculation (Days 3-4)

**Tasks:**

1. Add PV calculation endpoint to service
2. Implement progression caching
3. Add batch PV calculation for date ranges
4. Unit tests for progression functions (100% coverage)

**Deliverables:**

- PV calculation API endpoint
- Progression function test suite
- Performance benchmarks

### Phase 3: Frontend Implementation (Days 5-7)

**Tasks:**

1. Create schedule baseline components
2. Implement progression type selector with descriptions
3. Add progression curve visualization
4. Integrate with cost element detail view
5. E2E testing

**Deliverables:**

- Full UI for schedule baseline management
- Progression preview chart

### Phase 4: EVM Integration (Day 8)

**Tasks:**

1. Document PV calculation usage for EVM
2. Update EVM calculation service to use schedule baselines
3. Integration tests with cost elements and budgets
4. Documentation updates

**Deliverables:**

- EVM integration complete
- API documentation
- User documentation

---

## Progression Type Specifications

### Linear Progression (Default)

**Description:** Constant rate of progress throughout the schedule.

**Formula:**

```
progress = (current_date - start_date) / (end_date - start_date)
```

**Behavior:**

- Straight line from (start_date, 0%) to (end_date, 100%)
- Predictable, easy to understand
- Suitable for: Steady, consistent work rate

**Example Visualization:**

```
Progress %
    100|                    *
     75|                *
     50|            *
     25|        *
      0|*_______|_______|_______|_______
        start          mid           end
```

### Gaussian Progression (S-Curve)

**Description:** Bell curve progression with acceleration in the middle.

**Formula:**

```
z_score = (percent_complete - mean) / std_dev
progress = 0.5 * (1 + erf(z_score / sqrt(2)))
```

**Parameters:**

- `mean = 0.5` (midpoint of schedule)
- `std_dev = 0.15` (15% of schedule duration)

**Behavior:**

- Slow start, rapid acceleration in middle, taper at end
- Realistic for: Learning curves, team ramp-up
- Most projects follow this pattern naturally

**Example Visualization:**

```
Progress %
    100|                  ____----***
     75|             _--'
     50|         __--
     25|     __--
      0|__--       |_______|_______|
        start          mid           end
```

### Logarithmic Progression

**Description:** Front-loaded progression with rapid early progress.

**Formula:**

```
progress = log(elapsed_days + 1) / log(total_days + 1)
```

**Behavior:**

- Rapid initial progress, plateau toward end
- Suitable for: Front-loaded work, early-phase heavy projects
- May overstate early progress

**Example Visualization:**

```
Progress %
    100|            ****
     75|         **
     50|      **
     25|   **
      0|**
        |_______|_______|_______|_______
        start          mid           end
```

---

## Comparison to Other Parallel Tasks

| Criteria        | E05-U01 (Cost Registration) | E05-U02 (EAC Forecasts)    | **E05-U04 (Schedule Baselines)** |
| --------------- | --------------------------- | -------------------------- | -------------------------------- |
| Epic            | E005 Financial Data         | E005 Financial Data        | E005 Financial Data              |
| Bounded Context | Cost Element Tracking       | Cost Element Tracking      | Cost Element Tracking            |
| Entity Type     | Versioned (non-branchable)  | Versioned (non-branchable) | Versioned (branchable)           |
| Story Points    | 5                           | 5                          | 8                                |
| Primary Focus   | Actual cost tracking        | Forecasting                | Schedule management              |
| Dependencies    | E04-U03 ✅                  | E04-U03 ✅                 | E04-U03 ✅                       |
| Enables         | E05-U05, E05-U06, E08-U03   | E08-U02                    | **E08-U01** (PV calculation)     |
| Conflicts       | None (different entity)     | None (different entity)    | None (different entity)          |

**Why E05-U04 is Ideal for Parallel Execution:**

1. **Independent Domain**: Schedule management is separate from cost tracking and forecasting
2. **Different Entity**: Creates `ScheduleBaseline` (no overlap with `CostRegistration` or `Forecast`)
3. **Enables Different Downstream Work**: Unlocks E08-U01 (PV) vs E05-U05/E08-U03 (AC-related)
4. **Same Epic Alignment**: All three tasks in E005, maintaining cohesive iteration planning
5. **No Resource Conflicts**: Different developers can work on different entities simultaneously

---

## Recommendation

**Selected Approach:** Versioned & Branchable ScheduleBaseline with Pure Progression Functions

**Rationale:**

1. **Versioned AND Branchable** - Schedule baselines are project-specific and must be subject to formal change control (Change Orders) per PMI standards.
2. **Follows existing pattern** - `CostElement` and other project-specific entities use `BranchableMixin`.
3. **Supports mandatory requirements** - PV calculation, schedule variance analysis, and "what-if" impact analysis during change orders.
4. **Extensible design** - Progression functions as strategies allow future custom types.
5. **Pure functions** - Testable, reusable, cacheable.

**Key Design Decisions:**

- Use `VersionableMixin` AND `BranchableMixin` (Full Branching Support)
- Extend `BranchableService` (NOT `TemporalService`) to support Change Order isolation.
- Baselines are scoped to branches - allow impact analysis before merging.
- Progression functions are pure (no side effects).
- PV = BAC × progression_ratio.
- Table indexes on cost_element_id and date ranges.
- Cache progression calculations for performance.

**Next Steps:**

1. Proceed to PLAN phase with this approach.
2. Create detailed implementation plan.
3. Define database schema with progression_type enum.
4. Specify API contracts.
5. Plan testing strategy for progression functions.

---

## PMI Compliance Analysis

This design has been evaluated against Project Management Institute (PMI) standards, specifically the _PMBOK® Guide_ and _The Standard for Earned Value Management_.

### 1. Schedule Baseline Definition

**PMI Standard:** The schedule baseline is the approved version of a schedule model that can be changed only through formal change control procedures and is used as a basis for comparison to actual results.
**Compliance:**

- The `ScheduleBaseline` entity is distinct from the working schedule, representing a "frozen" or approved state.
- By making the entity **branchable**, we enforce that updates occur through the Change Order process (formal change control), rather than ad-hoc edits.
- The system supports multiple baselines (e.g., via different branches or re-baselining events), aligning with the concept of re-baselining.

### 2. Performance Measurement Baseline (PMB)

**PMI Standard:** The PMB integrates scope, schedule, and cost parameters. Planned Value (PV) is the authorized budget assigned to scheduled work (BCWS).
**Compliance:**

- The design explicitly links `ScheduleBaseline` (Time) with `CostElement` (Scope/Cost) budgets (BAC).
- The `calculate_planned_value` function strictly adheres to the definition of PV (BCWS): `PV = BAC * % Planned Complete`.
- This integration enables the calculation of the Cost Performance Index (CPI) and Schedule Performance Index (SPI), forming a complete PMB.

### 3. Planned Value Distribution (Resource Loading)

**PMI Standard:** Planned Value should reflect how work is authorized and funded over time. While linear distribution is simple, it is often unrealistic. S-curves are the standard representation for cumulative project progress.
**Compliance:**

- **Linear Progression:** Supported as a default, aligning with the "Level of Effort" (LOE) or simple "50/50" rules.
- **Gaussian (S-Curve):** The implementation of Gaussian progression directly supports the standard S-curve model (slow start, acceleration, taper), which is the industry standard for construction and development projects.
- **Logarithmic (Front-Loaded):** specific support for front-loaded activities (often seen in design or procurement phases) demonstrates advanced compliance with varying resource loading profiles.

### 4. Change Management & Traceability

**PMI Standard:** Changes to the baseline must be documented, approved, and traceable.
**Compliance:**

- The architecture uses **bitemporal versioning** (Transaction Time + Valid Time), providing an immutable audit trail of exactly _when_ a baseline was changed and _what_ the value was at any point in history.
- The branching mechanism allows "what-if" analysis for Change Orders without corrupting the active baseline, a highly mature capability in line with advanced project controls.

### Conclusion

The proposed architecture is **Fully Compliant** with PMI standards for Schedule Management and Earned Value Management. The explicit separation of the baseline entity, the support for non-linear PV distribution (S-curves), and the strict integration with Change Order branching provides a robust foundation for professional-grade project controls.

---

## References

- [Product Backlog: E05-U04](../product-backlog.md#e05-u04-define-schedule-baselines-with-progression-types)
- [Bounded Contexts: Cost Element & Financial Tracking](../../02-architecture/01-bounded-contexts.md#6-cost-element--financial-tracking)
- [Coding Standards](../../02-architecture/coding-standards.md)
- [Cost Element Model](../../../../backend/app/models/domain/cost_element.py) - Branchable pattern (Pattern to Follow)
- [Cost Element Service](../../../../backend/app/services/cost_element_service.py)
- [Cost Element API](../../../../backend/app/api/routes/cost_elements.py)
- [Analysis Prompt Template](../../04-pdca-prompts/analysis-prompt.md)
