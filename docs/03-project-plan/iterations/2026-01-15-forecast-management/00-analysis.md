# Analysis: [E05-U02] Create/Update Forecasts (EAC)

**Created:** 2026-01-15
**Request:** Implement forecast management functionality to track Estimate at Complete (EAC) per cost element with versioning support and comparison to actual costs.

---

## Clarified Requirements

### Functional Requirements

Based on the product backlog and project requirements:

1. **Forecast Entity**

   - Create a new domain entity `Forecast` to track EAC estimates
   - Required fields: `forecast_id`, `cost_element_id`, `eac_amount`, `forecast_date`
   - Optional fields: `basis_of_estimate`, `confidence_level` (Low/Medium/High)
   - Each forecast represents the projected total cost at completion for a cost element
   - **Versioned AND Branchable** (follows `CostElement` pattern for simulation capabilities)

2. **Forecast vs Actual Comparison**

   - Compare EAC to BAC (Budget at Complete) for variance analysis
   - Compare EAC to AC (Actual Cost) to determine remaining work estimate
   - Calculate ETC = EAC - AC (Estimate to Complete)
   - Visual indicators for over-budget forecasts

3. **Versioning Support (Branchable)**

   - Forecasts support **full bitemporal branching** (like `CostElement`)
   - Use `BranchableMixin` (inherits from `VersionableMixin`)
   - Track forecast changes over time per branch
   - Supports "What-if" scenario analysis (advanced simulation tools)
   - Enable time-travel queries for historical forecast analysis per branch
   - Soft delete capability for reversibility

4. **Latest Forecast Semantics**

   - For any cost element, the "current" forecast is the most recent one
   - System should always use latest forecast for calculations
   - Historical analysis uses time-travel queries

5. **API Endpoints**
   - CRUD operations for forecasts
   - List endpoint with filtering (by cost_element, date range, pagination)
   - Forecast comparison endpoint (EAC vs BAC vs AC)
   - Time-travel query endpoint (as_of parameter)
   - Latest forecast per cost element endpoint

### Non-Functional Requirements

- **Performance**: <100ms for single forecast, <200ms for paginated list queries
- **Data Integrity**: Atomic operations, rollback on validation failure
- **Type Safety**: Strict typing with Pydantic V2, MyPy compliance
- **Test Coverage**: 80%+ minimum, 100% for calculation logic
- **Scalability**: Efficient queries for rollup calculations

### Constraints

- Must use existing EVCS patterns (BranchableService, command pattern)
- **Must be branchable** - core capability for advanced simulation
- Must maintain backward compatibility with existing cost element structure
- Forecasts are independent but can reference cost registrations for EAC calculations

---

## Context Discovery

### Product Scope

**Relevant User Stories:**

- E05-U02: Create/Update Forecasts (EAC) (current)
- E05-U01: Register Actual Costs against Cost Elements (parallel - can reference)
- E08-U04: View Performance Indices (dependent - uses EAC)
- E08-U05: View Variances (dependent - uses EAC)

**Business Requirements:**

- Core EVM forecasting capability - enables proactive project management
- Provides early warning for budget overruns
- Supports "what-if" scenario analysis through versioning
- Foundation for EVM performance metrics (CPI, TCPI)

### Architecture Context

**Bounded Contexts Involved:**

1. **Cost Element & Financial Tracking** (Context 6) - Primary context

   - Forecast is a new entity within this context
   - Relates to existing CostElement entity
   - Related to CostRegistration (from E05-U01)
   - Used by EVM Calculations & Reporting context

2. **EVCS Core** (Context 0) - Versioning framework
   - Forecast uses `BranchableMixin` (extends `VersionableMixin`)
   - Follows `CostElement` pattern (versioned, branchable)
   - Time-travel capability for historical analysis

**Existing Patterns to Follow:**

- Service Layer Pattern: `BranchableService[TBranchable]`
- Command Pattern: `CreateVersionCommand`, `UpdateVersionCommand` (with branch awareness)
- API Route Conventions: Standard CRUD with RBAC via `RoleChecker`
- Pydantic V2 Strict Mode: All schemas with `ConfigDict(strict=True)`
- Pagination: `PaginatedResponse` with server-side filtering

**Architectural Constraints:**

- Must use PostgreSQL with asyncpg
- SQLAlchemy ORM with `Mapped[]` column syntax
- Entity must satisfy `BranchableProtocol`
- API responses must follow OpenAPI spec for client generation

### Codebase Analysis

**Backend:**

**Existing Related APIs:**

- [cost_elements.py](backend/app/api/routes/cost_elements.py) - Cost Element CRUD patterns
- [cost_element_service.py](backend/app/services/cost_element_service.py) - Service layer patterns
- [cost_element.py](backend/app/models/domain/cost_element.py) - Domain model patterns
- [E05-U01 Analysis](../2026-01-15-register-actual-costs/00-analysis.md) - **Reference for non-branchable versioned pattern**

**Data Models:**

- `CostElement` ([cost_element.py:22-52](backend/app/models/domain/cost_element.py#L22-L52)) - Branchable entity with `budget_amount` field

  - Key relationship: `cost_element_id` (root ID) for aggregation
  - Provides BAC (Budget at Complete) via `budget_amount`

- `CostElementType` ([cost_element_type.py:21-44](backend/app/models/domain/cost_element_type.py#L21-L44)) - **Pattern to follow**

  - Versionable but NOT branchable
  - Uses `VersionableMixin` only (no `BranchableMixin`)

- `CostRegistration` (from E05-U01) - **Direct reference pattern**
  - Versionable but NOT branchable
  - Similar entity structure to emulate

**Similar Patterns:**

- CRUD pattern from [cost_elements.py](backend/app/api/routes/cost_elements.py)
- Service layer with `TemporalService[T]` pattern (not `BranchableService`)
- Command pattern for create/update operations
- List endpoint with `FilterParser`, pagination, sorting

**Frontend:**

**Comparable Components:**

- [CostElementModal.tsx](frontend/src/features/cost-elements/components/CostElementModal.tsx) - Modal form patterns
- Uses Ant Design Form with validation
- Form submission with error handling

**State Management:**

- TanStack Query for server state (via `createResourceHooks`)
- Ant Design Form for form state
- URL-driven navigation for entity detail views

**Routing Structure:**

- `/projects/:projectId` - Project detail with nested routes
- `/projects/:projectId/wbes/:wbeId` - WBE detail with cost elements
- New route: `/cost-elements/:costElementId/forecasts` for forecast management

**Technical Debt:**

- No existing forecast entity or patterns
- EAC calculation logic needs to be designed
- Rollup calculation for WBE/Project level forecasts needed

---

## Solution Design

### Option 1: Versioned Forecast Entity (Branchable) - RECOMMENDED

**Architecture & Design:**

**Backend Layer Design:**

```
API Routes (app/api/routes/forecasts.py)
    ↓
Service Layer (app/services/forecast_service.py)
    ↓ extends
BranchableService[Forecast]
    ↓ uses
Command Pattern (CreateVersionCommand, UpdateVersionCommand)
    ↓
Model Layer (app/models/domain/forecast.py)
    ↓ extends BranchableMixin
    ↓
Database Table (forecasts)
```

**Key Design Decisions:**

1. **Branchable Versioning**

   ```python
   class Forecast(EntityBase, BranchableMixin):
       """Versioned AND branchable EAC tracking."""
       __tablename__ = "forecasts"

       # Root ID
       forecast_id: Mapped[UUID] = mapped_column(...)

       # Relations
       cost_element_id: Mapped[UUID] = mapped_column(...)

       # Business fields
       eac_amount: Mapped[Decimal] = mapped_column(...)  # Estimate at Complete
       forecast_date: Mapped[datetime] = mapped_column(...)
       basis_of_estimate: Mapped[str | None] = mapped_column(...)
       confidence_level: Mapped[ForecastConfidence] = mapped_column(...)

       # Inherits from BranchableMixin:
       # - valid_time: TSTZRANGE
       # - transaction_time: TSTZRANGE
       # - deleted_at: datetime | None
       # - created_by: UUID
       # - deleted_by: UUID | None
       # - branch_id: UUID
       # - parent_id: UUID | None
       # - merge_from_branch: UUID | None
   ```

2. **Service Layer**

   ```python
   class ForecastService(BranchableService[Forecast]):
       """Service for versioned, branchable forecasts."""

       async def get_latest_forecast(
           self,
           cost_element_id: UUID,
           branch_mode: BranchMode,
           as_of: datetime | None = None
       ) -> Forecast | None:
           """Get the most recent forecast for a cost element on the specified branch."""
           # BranchableService handles the branch/merge resolution
           pass

       async def get_forecast_comparison(
           self,
           cost_element_id: UUID,
           branch_mode: BranchMode,
           as_of: datetime | None = None
       ) -> ForecastComparison:
           """Get EAC vs BAC vs AC comparison."""
           forecast = await self.get_latest_forecast(cost_element_id, branch_mode, as_of)

           # Note: Cost Element is also branchable
           cost_element = await self._get_cost_element(cost_element_id, branch_mode, as_of)

           # Actual Cost is global (no branch)
           actual_cost = await self._get_actual_cost(cost_element_id, as_of)

           return ForecastComparison(
               bac=cost_element.budget_amount,
               eac=forecast.eac_amount if forecast else None,
               ac=actual_cost,
               variance_at_complete=(forecast.eac_amount - cost_element.budget_amount) if forecast else None,
               estimate_to_complete=(forecast.eac_amount - actual_cost) if forecast else None,
           )
   ```

3. **Enum for Confidence Level**
   ```python
   class ForecastConfidence(str, Enum):
       LOW = "low"
       MEDIUM = "medium"
       HIGH = "high"
   ```

**Component Structure (Frontend):**

```
features/forecasts/
├── components/
│   ├── ForecastList.tsx              # Table with filters
│   ├── ForecastModal.tsx             # Create/Edit form
│   └── ForecastComparisonCard.tsx    # Visual comparison (EAC vs BAC vs AC)
├── hooks/
│   └── useForecasts.ts               # TanStack Query hooks
└── types.ts
```

**State Management Approach:**

- Server State: TanStack Query (auto-refetch on mutations)
- Form State: Ant Design Form
- Local State: Modal visibility

**Data Flow and API Interactions:**

```
User creates forecast
    ↓
Form validation (client-side)
    ↓
POST /api/v1/forecasts
    ↓
Service validates forecast
    ↓
CreateVersionCommand executes (TemporalService, not BranchableService)
    ↓
Returns ForecastRead
    ↓
TanStack Query invalidates related queries
```

**UX Design:**

**User Stories:**

1. As a project manager, I want to create EAC forecasts to predict final project costs
2. As a project manager, I want to compare forecasts to budget and actuals for variance analysis
3. As a project manager, I want to see forecast history to understand prediction accuracy

**User Interaction Flow:**

```
Navigate to Cost Element Detail
    ↓
View Forecast Comparison Card (EAC vs BAC vs AC)
    ↓
Click "Create Forecast" button
    ↓
Modal opens with form
    ↓
Fill in: EAC amount, forecast date, confidence level, basis of estimate
    ↓
Submit → Create forecast
    ↓
Success: Table refreshes, comparison card updates
    ↓
Error: Inline validation message
```

**Visual Hierarchy and Layout:**

1. **Header**: Cost Element name, breadcrumb navigation
2. **Forecast Comparison Card**: Visual comparison
   - Shows: BAC, EAC, AC, VAC (Variance at Complete), ETC
   - Color coding: Green (within budget), Yellow (warning), Red (over budget)
3. **Action Bar**: "Create Forecast", "View History" buttons
4. **Forecasts Table**: Date, EAC, Confidence, Basis of Estimate, Actions

**Navigation Patterns:**

- URL-driven: `/projects/:id/wbes/:wbeId/cost-elements/:ceId/forecasts`
- Breadcrumb: Projects > Project X > WBE Y > Cost Element Z > Forecasts

**Accessibility Considerations:**

- Keyboard navigation for all actions
- ARIA labels for comparison indicators
- High contrast color coding for variance thresholds
- Screen reader support for validation messages

**Edge Cases and Error States:**

1. **No Forecast Yet**: Show "No forecast available" in comparison card
2. **Cost Element Deleted**: Redirect to parent WBE with notification
3. **Concurrent Updates**: Optimistic locking with version conflict detection

**Technical Implementation:**

**Key Files to Create/Modify:**

**Backend:**

- `backend/app/models/domain/forecast.py` (NEW)
  - Extends `EntityBase` and `BranchableMixin`
- `backend/app/services/forecast_service.py` (NEW)
  - Extends `BranchableService[Forecast]`
- `backend/app/api/routes/forecasts.py` (NEW)
  - Standard CRUD endpoints with time-travel support
- `backend/app/models/schemas/forecast.py` (NEW)
  - Pydantic V2 strict schemas
- `backend/alembic/versions/xxx_create_forecasts.py` (NEW)
  - Table creation with GIST indexes

**Frontend:**

- `frontend/src/features/forecasts/components/*` (NEW)
- `frontend/src/features/cost-elements/components/CostElementDetail.tsx` (MODIFY)
  - Add "Forecasts" tab

**Integration Points:**

- CostElementService: Reference for BAC amount
- CostRegistrationService (from E05-U01): Reference for AC amount
- RBAC: New permission `forecast-create`
- API Client: Auto-generate from OpenAPI spec

**Database Schema:**

```sql
CREATE TABLE forecasts (
    id UUID PRIMARY KEY,
    forecast_id UUID NOT NULL,
    cost_element_id UUID NOT NULL REFERENCES cost_elements(cost_element_id),
    eac_amount DECIMAL(15,2) NOT NULL,
    forecast_date DATE NOT NULL,
    confidence_level VARCHAR(20) NOT NULL,
    basis_of_estimate TEXT,

    -- Versioning fields (from BranchableMixin)
    valid_time TSTZRANGE NOT NULL,
    transaction_time TSTZRANGE NOT NULL,
    deleted_at TIMESTAMP,
    created_by UUID NOT NULL,
    deleted_by UUID,
    branch_id UUID NOT NULL,
    parent_id UUID,
    merge_from_branch UUID
);

-- Indexes for performance
CREATE INDEX idx_forecasts_element_id ON forecasts(cost_element_id);
CREATE INDEX idx_forecasts_date ON forecasts(forecast_date);
CREATE INDEX idx_forecasts_valid_time ON forecasts USING GIST(valid_time);
CREATE INDEX idx_forecasts_transaction_time ON forecasts USING GIST(transaction_time);

-- Partial index for current versions
CREATE INDEX idx_forecasts_current
ON forecasts(cost_element_id, forecast_date DESC)
WHERE upper(valid_time) IS NULL AND deleted_at IS NULL;
```

**Testing Approach (High-Level):**

**Unit Tests:**

- Latest forecast retrieval logic
- Forecast comparison calculations (EAC vs BAC vs AC)
- Version creation commands
- Time-travel queries (as_of parameter)

**Integration Tests:**

- Full CRUD operations
- Forecast comparison with cost element and cost registration data
- Time-travel forecast queries

**E2E Tests:**

- User creates forecast, sees comparison update
- Forecast history viewing
- Comparison card displays correctly

**Trade-offs:**

| Aspect          | Assessment                                                                                                                                                               |
| --------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Pros            | • Supports "What-if" scenario analysis (Advanced Simulation)<br>• Full audit trail with versioning<br>• Per-branch forecasts<br>• Consistent with Cost Element branching |
| Cons            | • Higher complexity (merge logic)<br>• User needs to be aware of active branch                                                                                           |
| Complexity      | Medium - Uses BranchableService                                                                                                                                          |
| Maintainability | Good - Follows established Branchable patterns                                                                                                                           |
| Performance     | Expected <100ms for CRUD with proper indexing                                                                                                                            |

### Deep Dive: Branching Strategy for Forecasts

A critical architectural decision is whether Forecasts should be **Branchable** (like Cost Elements) or **Global** (like Actual Costs).

#### Option A: Non-Branchable (Global) Forecasts

_Current Proposal (Option 1)_

In this model, a Forecast is a "Fact about an Estimate". It is recorded globally. If you are on a feature branch, you see the same EAC as the Main branch.

**Pros:**

- **Simplicity:** No need to handle merge logic or "fallback" strategies.
- **Single Source of Truth:** Avoids confusion about which number is "Official".
- **Alignment with Actuals:** actual costs are global; keeping forecasts global simplifies the `EAC - AC` math.

**Cons:**

- **No Scenario Planning:** You cannot create a "What-if" forecast associated with a pending Change Order.
- **Risk of "Pollution":** If a Project Manager wants to draft a sensitive re-forecast, they cannot do so in isolation. It becomes visible immediately.

#### Option B: Branchable Forecasts

In this model, Forecasts exist within the context of a Branch. A Change Order (which is a Branch) can carry its own specific EAC that differs from the Main timeline.

**Pros:**

- **Powerful Impact Analysis:** A Change Order can include not just scope changes (Cost Elements) but also the updated financial outlook (EAC).
  - _Example:_ Branch `CO-101-Repair` adds a generic "Repair" task. The PM updates the EAC for that task _on the branch_. Stakeholders can see: "Main EAC: $1M" vs "CO-101 EAC: $1.2M".
- **Drafting Safety:** PMs can work on a `draft/monthly-review` branch, adjust all numbers, and "Merge" them when official.

**Cons:**

- **Merge Complexity:** Merging a Forecast is not additive (like lines of code). It is usually a **Overwrite** strategy (Latest wins). The system must handle this logic.
- **User Cognitive Load:** Users must be aware of which branch they are viewing. "Why did my forecast disappear?" (Because you switched back to Main).

#### Recommendation on Branching

**Recommend Option B (Branchable) as per User Request.**
Because the core value proposition involves **Advanced Simulation**, enabling "What-if" analysis on branches is critical. The complexity trade-off is justified by the strategic need for simulation.

---

### Option 2: Add EAC Directly to CostElement (Branchable)

**Architecture & Design:**

- Add `eac_amount`, `forecast_date`, `confidence_level` fields directly to CostElement
- Leverages existing branchable nature of CostElement
- Each branch can have its own forecast

**Trade-offs:**

| Aspect          | Assessment                                                                                                                                                                                                                                                          |
| --------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Pros            | • No new entity needed<br>• Leverages existing CostElement structure<br>• Per-branch forecasts for change orders                                                                                                                                                    |
| Cons            | • Breaks semantic model (forecast is not a property of cost element)<br>• Cannot track multiple forecasts over time<br>• Loses audit trail for forecast changes<br>• Cannot analyze forecast accuracy historically<br>• Mixing branchable data with global concepts |
| Complexity      | Low initially, High long-term                                                                                                                                                                                                                                       |
| Maintainability | Poor - Semantically incorrect                                                                                                                                                                                                                                       |

**Recommendation:** Do NOT use this approach. Forecasts are time-series predictions, not properties of the cost element itself.

---

### Option 3: Simple Non-Versioned Forecasts

**Architecture & Design:**

- Create Forecast entity using `SimpleBase` (non-versioned)
- Simple CRUD with standard update
- No historical tracking

**Trade-offs:**

| Aspect          | Assessment                                                                                                                                                                                                                                          |
| --------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Pros            | • Simple implementation<br>• Lower storage overhead<br>• Faster queries (no version filtering)                                                                                                                                                      |
| Cons            | • No audit trail for forecast changes<br>• Cannot analyze forecast accuracy over time<br>• Inconsistent with other financial entities (CostRegistration)<br>• Lost history when forecasts updated<br>• Cannot support regulatory audit requirements |
| Complexity      | Low                                                                                                                                                                                                                                                 |
| Maintainability | Fair - But loses valuable historical data                                                                                                                                                                                                           |

**Recommendation:** Not recommended for EVM system where forecast accuracy analysis is important.

---

## Comparison Summary

| Criteria           | Option 1 (Versioned Non-Branchable) | Option 2 (EAC on CostElement) | Option 3 (Simple Non-Versioned)        |
| ------------------ | ----------------------------------- | ----------------------------- | -------------------------------------- |
| Development Effort | Medium (5-8 days)                   | Low (2-3 days)                | Low (2-3 days)                         |
| UX Quality         | High                                | Medium                        | Low                                    |
| Flexibility        | High                                | Low                           | Low                                    |
| Audit Capability   | Full                                | None                          | None                                   |
| Consistency        | High (matches CostRegistration)     | Low (semantic mismatch)       | Low (inconsistent with other entities) |
| Best For           | Production EVM system               | Quick prototype               | Simple CRUD apps                       |

---

## Recommendation

**I recommend Option 1: Versioned Forecast Entity (Branchable)**

**Rationale:**

1.  **Alignment with Core Mission**: "Advanced Simulation" requires creating hypothetical forecasts on branches without polluting the main timeline.
2.  **Consistency with Cost Elements**: Forecasts will behave like the scope they track—existing on branches and merging when approved.
3.  **Future Proofing**: Supporting branching now prevents a difficult migration later when simulation features are requested.

**Implementation note**: We must ensure the UI clearly indicates which branch a forecast belongs to.

---

## Decision Questions

1. **Do you need historical forecast tracking?** (i.e., ability to see what forecasts were made 3 months ago and compare to actuals)
2. **Is forecast accuracy analysis important?** (i.e., measuring how well predictions match reality)
3. **Should forecasts support regulatory audit requirements?** (i.e., complete change history)

If you answered YES to any of these, Option 1 is the correct choice.

---

## Implementation Roadmap

### Phase 1: Backend Foundation (Days 1-2)

**Tasks:**

1. Create `Forecast` model (Versioned, Branchable)
2. Create `ForecastService` (extends `BranchableService`)
3. Implement latest forecast retrieval logic
4. Implement forecast comparison (EAC vs BAC vs AC)
5. Create database migration with indexes

**Deliverables:**

- Working CRUD API for forecasts
- Forecast comparison endpoint
- Time-travel query support

### Phase 2: Integration (Day 3)

**Tasks:**

1. Integrate with CostElementService for BAC reference
2. Integrate with CostRegistrationService (from E05-U01) for AC reference
3. Add rollup calculation for WBE/Project level forecasts
4. Test integration with parallel E05-U01 work

**Deliverables:**

- Complete forecast comparison functionality
- Rollup calculations

### Phase 3: Frontend Implementation (Days 4-5)

**Tasks:**

1. Create forecast components
2. Implement forecast comparison card
3. Integrate with cost element detail view
4. E2E testing

**Deliverables:**

- Full UI for forecast management
- Forecast visualization

### Phase 4: Testing & Documentation (Day 6)

**Tasks:**

1. Complete unit tests (80%+ coverage)
2. Integration tests for all scenarios
3. E2E tests for critical flows
4. API documentation
5. User documentation

**Deliverables:**

- Complete test coverage
- Documentation

---

## References

- [Product Backlog: E05-U02](../product-backlog.md#e05-u02-createupdate-forecasts-eac)
- [Bounded Contexts: Cost Element & Financial Tracking](../../02-architecture/01-bounded-contexts.md#6-cost-element--financial-tracking)
- [Coding Standards](../../02-architecture/coding-standards.md)
- [Cost Element Model](backend/app/models/domain/cost_element.py) - For BAC reference
- [Cost Registration Analysis](../2026-01-15-register-actual-costs/00-analysis.md) - **Pattern reference for non-branchable versioned entities**
- [Analysis Prompt Template](../../04-pdca-prompts/analysis-prompt.md)
