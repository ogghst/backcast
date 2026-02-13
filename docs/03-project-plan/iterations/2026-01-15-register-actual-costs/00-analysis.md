# Analysis: [E05-U01] Register Actual Costs against Cost Elements

**Created:** 2026-01-15
**Updated:** 2026-01-15
**Request:** Implement cost registration functionality to track actual expenditures against cost elements with budget validation and versioning support.

**Decisions Applied:**
- ✅ Versioned entity (bitemporal tracking)
- ✅ NOT branchable (costs are global across branches)
- ✅ Mandatory change order impact analysis
- ✅ High volume: 20,000 registrations/month
- ✅ Team has high EVCS versioning experience

---

## Clarified Requirements

### Functional Requirements

Based on the product backlog and user decisions:

1. **Cost Registration Entity**
   - Create a new domain entity `CostRegistration` to track actual costs
   - Required fields: `cost_registration_id`, `cost_element_id`, `amount`
   - Optional fields: `quantity`, `unit_of_measure`, `registration_date` (defaults to control date), `description`, `invoice_number`, `vendor_reference`
   - Each registration represents a single cost incurred against a cost element
   - **Versioned but NOT branchable** (follows `CostElementType` pattern)
   - `quantity` allows tracking of units consumed (e.g., labor hours, material quantity)
   - `unit_of_measure` specifies the unit type (e.g., "hours", "kg", "m", "each")

2. **Budget Validation**
   - Validate that cumulative actual costs do not exceed allocated budget
   - Provide warning when approaching budget limit (configurable threshold, default: 80%)
   - Block when exceeding budget (configurable via system settings)
   - Real-time validation on create and update operations
   - Validation applies to main branch budget (costs are global)

3. **Versioning Support (Non-Branchable)**
   - Cost registrations support **bitemporal versioning** (like `CostElementType`)
   - Use `VersionableMixin` but NOT `BranchableMixin`
   - Track cost changes over time for audit trail
   - Enable time-travel queries for historical cost analysis
   - Soft delete capability for reversibility
   - Costs are **global** - same across all branches (not copied to branches)

4. **Change Order Impact Analysis (Mandatory)**
   - Impact analysis must include cost registrations in variance calculations
   - When comparing change order branch to main:
     - Budget differences come from branchable `CostElement` (different versions per branch)
     - Cost registrations come from main branch only (global, not branch-specific)
     - Variance = (Branch Budget - Main Budget) - Actual Costs (global)
   - Impact analysis shows: "If this change order is approved, budget variance will be X"

5. **API Endpoints**
   - CRUD operations for cost registrations
   - List endpoint with filtering (by cost_element, date range, pagination)
   - Budget status endpoint (used/remaining/percentage)
   - Time-travel query endpoint (as_of parameter)

### Non-Functional Requirements

- **Performance**: <100ms for single registration, <200ms for paginated list queries
- **High Volume Support**: 20,000 registrations/month = ~667/day = ~84/hour
- **Data Integrity**: Atomic operations, rollback on validation failure
- **Type Safety**: Strict typing with Pydantic V2, MyPy compliance
- **Test Coverage**: 80%+ minimum, 100% for validation logic
- **Scalability**: Table partitioning strategy for 240k+ records/year

### Constraints

- Must use existing EVCS patterns (TemporalService, command pattern)
- **Must NOT be branchable** - costs are global across branches
- Must maintain backward compatibility with existing cost element structure
- Budget validation uses main branch budget (costs are not branch-specific)
- Change order impact analysis must include cost registration data

---

## Context Discovery

### Product Scope

**Relevant User Stories:**
- E05-U01: Register Actual Costs against Cost Elements (current)
- E05-U05: Validate Cost Registrations against Budgets (dependent)
- E05-U06: View Cost History and Trends (dependent on versioning)
- E08-U03: Calculate AC from Cost Registrations (dependent)

**Business Requirements:**
- Core EVM data requirement - Actual Cost (AC) calculation foundation
- Enables budget tracking and variance analysis
- Supports change order impact analysis through versioned cost data

### Architecture Context

**Bounded Contexts Involved:**
1. **Cost Element & Financial Tracking** (Context 6) - Primary context
   - CostRegistration is a new entity within this context
   - Relates to existing CostElement entity
   - Used by EVM Calculations & Reporting context
   - Similar to ScheduleRegistration (versioned, non-branchable)

2. **EVCS Core** (Context 0) - Versioning framework
   - CostRegistration uses `VersionableMixin` (NOT `BranchableMixin`)
   - Follows `CostElementType` pattern (versionable reference data)
   - Time-travel capability for historical analysis

**Existing Patterns to Follow:**
- Service Layer Pattern: `TemporalService[TVersionable]` (not `BranchableService`)
- Command Pattern: `CreateVersionCommand`, `UpdateVersionCommand`
- API Route Conventions: Standard CRUD with RBAC via `RoleChecker`
- Pydantic V2 Strict Mode: All schemas with `ConfigDict(strict=True)`
- Pagination: `PaginatedResponse` with server-side filtering

**Architectural Constraints:**
- Must use PostgreSQL with asyncpg
- SQLAlchemy ORM with `Mapped[]` column syntax
- Entity must satisfy `VersionableProtocol` (NOT `BranchableProtocol`)
- API responses must follow OpenAPI spec for client generation

### Codebase Analysis

**Backend:**

**Existing Related APIs:**
- [cost_elements.py](../..../../../backend/app/api/routes/cost_elements.py) - Cost Element CRUD patterns
- [cost_element_service.py](../..../../../backend/app/services/cost_element_service.py) - Service layer patterns
- [cost_element.py](../..../../../backend/app/models/domain/cost_element.py) - Domain model patterns

**Data Models:**
- `CostElement` ([cost_element.py:22-52](../..../../../backend/app/models/domain/cost_element.py#L22-L52)) - Branchable entity with `budget_amount` field
  - Uses `TemporalBase`, `BranchableMixin`, `VersionableMixin`
  - Key relationship: `cost_element_id` (root ID) for aggregation

- `CostElementType` ([cost_element_type.py:21-44](../..../../../backend/app/models/domain/cost_element_type.py#L21-L44)) - **Pattern to follow**
  - Versionable but NOT branchable
  - Uses `VersionableMixin` only (no `BranchableMixin`)
  - Satisfies `VersionableProtocol`
  - Has `cost_element_type_id` as root ID

**Similar Patterns:**
- CRUD pattern from [cost_elements.py](../..../../../backend/app/api/routes/cost_elements.py)
- Service layer with `TemporalService[T]` pattern (not `BranchableService`)
- Command pattern for create/update operations
- List endpoint with `FilterParser`, pagination, sorting

**Frontend:**

**Comparable Components:**
- [CostElementModal.tsx](../../../frontend/src/features/cost-elements/components/CostElementModal.tsx) - Modal form patterns
- Uses Ant Design Form with validation
- Async options fetching (CostElementTypes for dropdown)
- Form submission with error handling

**State Management:**
- TanStack Query for server state (via `createResourceHooks`)
- Ant Design Form for form state
- URL-driven navigation for entity detail views

**Routing Structure:**
- `/projects/:projectId` - Project detail with nested routes
- `/projects/:projectId/wbes/:wbeId` - WBE detail with cost elements
- New route: `/cost-elements/:costElementId/costs` for cost registrations

**Technical Debt:**
- No existing cost registration entity or patterns
- Budget validation logic needs to be designed
- High-volume table partitioning strategy needed

---

## Solution Design

### Approved Approach: Versioned CostRegistration (Non-Branchable)

Based on user decisions, this is the definitive approach:

**Architecture & Design:**

**Backend Layer Design:**
```
API Routes (app/api/routes/cost_registrations.py)
    ↓
Service Layer (app/services/cost_registration_service.py)
    ↓ extends
TemporalService[CostRegistration]  # NOT BranchableService
    ↓ uses
Command Pattern (CreateVersionCommand, UpdateVersionCommand)
    ↓
Model Layer (app/models/domain/cost_registration.py)
    ↓ extends VersionableMixin (NOT BranchableMixin)
    ↓
Database Table (cost_registrations)
```

**Key Design Decisions:**

1. **Non-Branchable Versioning**
   ```python
   class CostRegistration(EntityBase, VersionableMixin):
       """Versioned but NOT branchable cost tracking."""
       __tablename__ = "cost_registrations"

       # Root ID
       cost_registration_id: Mapped[UUID] = mapped_column(...)

       # Relations
       cost_element_id: Mapped[UUID] = mapped_column(...)

       # Business fields
       amount: Mapped[Decimal] = mapped_column(...)
       quantity: Mapped[Decimal | None] = mapped_column(...)  # Optional: units consumed
       unit_of_measure: Mapped[str | None] = mapped_column(String(50), ...)  # Optional: "hours", "kg", etc.
       registration_date: Mapped[datetime | None] = mapped_column(...)  # Optional: defaults to control date
       description: Mapped[str | None] = mapped_column(...)
       invoice_number: Mapped[str | None] = mapped_column(String(100), ...)
       vendor_reference: Mapped[str | None] = mapped_column(String(255), ...)

       # Inherits from VersionableMixin:
       # - valid_time: TSTZRANGE
       # - transaction_time: TSTZRANGE
       # - deleted_at: datetime | None
       # - created_by: UUID
       # - deleted_by: UUID | None

       # Does NOT inherit BranchableMixin (no branch, parent_id, merge_from_branch)
   ```

2. **Service Layer**
   ```python
   class CostRegistrationService(TemporalService[CostRegistration]):
       """Service for versioned, non-branchable cost registrations."""

       async def get_total_for_cost_element(
           self, cost_element_id: UUID, as_of: datetime | None = None
       ) -> Decimal:
           """Calculate total costs for a cost element (time-travel aware)."""
           # Sum of all current cost registrations for this cost element
           pass
   ```

3. **Change Order Impact Analysis Integration**
   ```python
   # In ImpactAnalysisService (existing)
   async def compare_branch_to_main(branch: str) -> ImpactReport:
       """Compare change order branch to main, including cost impact."""

       # CostElement differences (branchable)
       main_budget = await get_cost_element_budget(ce_id, "main")
       branch_budget = await get_cost_element_budget(ce_id, branch)
       budget_delta = branch_budget - main_budget

       # Cost registrations (global, from main only)
       actual_costs = await cost_registration_service.get_total_for_cost_element(ce_id)

       # Impact calculation
       projected_variance = (branch_budget - main_budget) - actual_costs

       return ImpactReport(
           budget_delta=budget_delta,
           actual_costs=actual_costs,
           projected_variance=projected_variance
       )
   ```

**Component Structure (Frontend):**
```
features/cost-registrations/
├── components/
│   ├── CostRegistrationList.tsx       # Table with filters
│   ├── CostRegistrationModal.tsx      # Create/Edit form
│   └── BudgetStatusCard.tsx           # Visual budget indicator
├── hooks/
│   └── useCostRegistrations.ts        # TanStack Query hooks
└── types.ts
```

**State Management Approach:**
- Server State: TanStack Query (auto-refetch on mutations)
- Form State: Ant Design Form
- Local State: Modal visibility

**Data Flow and API Interactions:**
```
User creates cost registration
    ↓
Form validation (client-side)
    ↓
POST /api/v1/cost-registrations
    ↓
Service validates budget (calls CostElementService.get_budget_status)
    ↓
If valid: CreateVersionCommand executes (TemporalService, not BranchableService)
    ↓
Returns CostRegistrationRead
    ↓
TanStack Query invalidates related queries (cost elements, budget status)
```

**Key Design Patterns Applied:**
- **Repository Pattern**: `TemporalService` for versioned data access
- **Command Pattern**: Versioned create/update operations
- **Dependency Injection**: FastAPI `Depends()` for service and auth
- **Factory Pattern**: Command factory for cost registration operations

**UX Design:**

**User Stories:**
1. As a project manager, I want to register actual costs against cost elements to track project expenditures
2. As a project manager, I want to see budget utilization at a glance to avoid overspending
3. As a project manager, I want to see how change orders affect budget vs actual costs

**User Interaction Flow:**
```
Navigate to Cost Element Detail
    ↓
View Budget Status Card (color-coded: green/yellow/red)
    ↓
Click "Register Cost" button
    ↓
Modal opens with form
    ↓
Fill in: amount, date, description (optional), invoice number (optional)
    ↓
Submit → Budget validation against main branch budget
    ↓
Success: Table refreshes, budget status updates
    ↓
Error: Inline validation message
```

**Visual Hierarchy and Layout:**
1. **Header**: Cost Element name, breadcrumb navigation
2. **Budget Status Card**: Large, prominent, color-coded progress bar
   - Shows: Budget, Actual Costs, Remaining, Percentage
   - Color coding: Green (<80%), Yellow (80-99%), Red (≥100%)
3. **Action Bar**: "Register Cost", "Export" buttons
4. **Cost Registrations Table**: Date, Amount, Description, Invoice, Actions

**Navigation Patterns:**
- URL-driven: `/projects/:id/wbes/:wbeId/cost-elements/:ceId`
- Tab navigation: "Overview" | "Budget & Costs" | "History"
- Breadcrumb: Projects > Project X > WBE Y > Cost Element Z

**Accessibility Considerations:**
- Keyboard navigation for all actions
- ARIA labels for budget status indicators
- High contrast color coding for budget thresholds
- Screen reader support for validation messages

**Edge Cases and Error States:**
1. **Budget Exceeded**: Modal error with "Request Override" option (if allowed)
2. **Cost Element Deleted**: Redirect to parent WBE with notification
3. **Concurrent Updates**: Optimistic locking with version conflict detection

**Technical Implementation:**

**Key Files to Create/Modify:**

**Backend:**
- `backend/app/models/domain/cost_registration.py` (NEW)
  - Extends `EntityBase` and `VersionableMixin` (NOT `BranchableMixin`)
- `backend/app/services/cost_registration_service.py` (NEW)
  - Extends `TemporalService[CostRegistration]`
- `backend/app/api/routes/cost_registrations.py` (NEW)
  - Standard CRUD endpoints with time-travel support
- `backend/app/models/schemas/cost_registration.py` (NEW)
  - Pydantic V2 strict schemas
- `backend/app/services/cost_element_service.py` (MODIFY)
  - Add budget validation method
- `backend/app/services/impact_analysis_service.py` (MODIFY)
  - Include cost registrations in impact analysis
- `backend/alembic/versions/xxx_create_cost_registrations.py` (NEW)
  - Table creation with GIST indexes

**Frontend:**
- `frontend/src/features/cost-registrations/components/*` (NEW)
- `frontend/src/features/cost-elements/components/CostElementDetail.tsx` (MODIFY)
  - Add "Budget & Costs" tab

**Integration Points:**
- CostElementService: Add `get_budget_status(cost_element_id)` method
- ImpactAnalysisService: Include cost registration totals in comparison
- RBAC: New permission `cost-registration-create`
- API Client: Auto-generate from OpenAPI spec

**Database Schema:**
```sql
CREATE TABLE cost_registrations (
    id UUID PRIMARY KEY,
    cost_registration_id UUID NOT NULL,
    cost_element_id UUID NOT NULL REFERENCES cost_elements(cost_element_id),
    amount DECIMAL(15,2) NOT NULL,
    registration_date DATE NOT NULL,
    description TEXT,
    invoice_number VARCHAR(100),
    vendor_reference VARCHAR(255),

    -- Versioning fields (from VersionableMixin)
    valid_time TSTZRANGE NOT NULL,
    transaction_time TSTZRANGE NOT NULL,
    deleted_at TIMESTAMP,
    created_by UUID NOT NULL,
    deleted_by UUID
);

-- Indexes for performance
CREATE INDEX idx_cost_registrations_element_id ON cost_registrations(cost_element_id);
CREATE INDEX idx_cost_registrations_date ON cost_registrations(registration_date);
CREATE INDEX idx_cost_registrations_valid_time ON cost_registrations USING GIST(valid_time);
CREATE INDEX idx_cost_registrations_transaction_time ON cost_registrations USING GIST(transaction_time);

-- Partitioning strategy (for 20k/month volume)
-- Consider partitioning by registration_date (quarterly partitions)
```

**Potential Technical Challenges:**

1. **Budget Validation Race Condition**
   - **Challenge**: Concurrent cost registrations could exceed budget simultaneously
   - **Solution**: Use `SELECT FOR UPDATE` on cost_element row or application-level locking with Redis

2. **High Volume Performance (20k/month)**
   - **Challenge**: 240k+ records/year could slow queries
   - **Solutions**:
     - Table partitioning by quarter (registration_date)
     - Partial indexes on current versions only
     - Archive old versions to separate table

3. **Change Order Impact Analysis with Global Costs**
   - **Challenge**: Costs are global, budgets are branchable
   - **Solution**: Always query costs from main, compare against branch budgets
   - **Implementation**: ImpactAnalysisService already handles branch comparison

4. **Time-Travel Budget Queries**
   - **Challenge**: Querying budget status as of specific date
   - **Solution**: Use temporal filters on both cost_registrations and cost_elements

**Performance Optimizations:**

1. **Table Partitioning** (for 20k/month volume)
   ```sql
   -- Partition by quarter (create 4 partitions per year)
   CREATE TABLE cost_registrations_q1_2026 PARTITION OF cost_registrations
   FOR VALUES FROM ('2026-01-01') TO ('2026-04-01');
   ```

2. **Partial Indexes** (current versions only)
   ```sql
   CREATE INDEX idx_cost_registrations_current
   ON cost_registrations(cost_element_id)
   WHERE upper(valid_time) IS NULL AND deleted_at IS NULL;
   ```

3. **Caching Strategy**
   - Cache budget status for 5 minutes (TTL)
   - Invalidate cache on cost registration create/update
   - Use Redis for distributed caching

**Testing Approach (High-Level):**

**Unit Tests:**
- Budget validation logic (thresholds, blocking)
- Version creation commands
- Time-travel queries (as_of parameter)

**Integration Tests:**
- Full CRUD operations with budget enforcement
- Time-travel budget queries
- Impact analysis with cost registrations

**Performance Tests:**
- Query performance with 100k+ records (<100ms)
- Concurrent budget validation (10 simultaneous requests)

**E2E Tests:**
- User registers cost, sees budget update
- Budget exceeded warning/block interaction
- Change order impact view shows cost data

**Trade-offs:**

| Aspect | Assessment |
|--------|------------|
| Pros | • Full audit trail with versioning<br>• Time-travel capability for historical analysis<br>• Consistent with EVCS versioning patterns<br>• Supports change order impact analysis<br>• Global costs simplify queries (no branch filtering) |
| Cons | • Increased storage overhead (version table growth)<br>• More complex queries (need latest version filter)<br>• Performance overhead for versioning<br>• Requires partitioning for high volume |
| Complexity | Medium - Leverages existing EVCS framework |
| Maintainability | Good - Follows established patterns |
| Performance | Expected <100ms for CRUD with proper indexing and partitioning |

---

## Implementation Roadmap

### Phase 1: Backend Foundation (Days 1-2)

**Tasks:**
1. Create `CostRegistration` model (versioned, non-branchable)
2. Create `CostRegistrationService` (extends `TemporalService`)
3. Implement budget validation logic
4. Add budget status endpoint
5. Create database migration with indexes

**Deliverables:**
- Working CRUD API for cost registrations
- Budget validation on create/update
- Time-travel query support

### Phase 2: Performance Optimization (Days 3-4)

**Tasks:**
1. Add table partitioning strategy
2. Implement partial indexes for current versions
3. Add caching for budget status
4. Performance testing with 10k+ records

**Deliverables:**
- Optimized queries (<100ms)
- Table partitioning for high volume

### Phase 3: Change Order Integration (Day 5)

**Tasks:**
1. Modify `ImpactAnalysisService` to include cost registrations
2. Update impact comparison UI to show cost impact
3. Test change order workflow with costs
4. Documentation updates

**Deliverables:**
- Impact analysis includes cost data
- Change order comparison shows budget vs costs

### Phase 4: Frontend Implementation (Days 6-8)

**Tasks:**
1. Create cost registration components
2. Implement budget status card
3. Integrate with cost element detail view
4. E2E testing

**Deliverables:**
- Full UI for cost registration
- Budget visualization

### Phase 5: Testing & Documentation (Days 9-10)

**Tasks:**
1. Complete unit tests (80%+ coverage)
2. Integration tests for all scenarios
3. Performance testing
4. E2E tests for critical flows
5. API documentation
6. User documentation

**Deliverables:**
- Complete test coverage
- Performance benchmarks
- Documentation

---

## Performance Considerations for High Volume (20k/month)

### Volume Analysis

- **Per Month**: 20,000 registrations
- **Per Day**: ~667 registrations (assuming 30 days)
- **Per Hour**: ~84 registrations (assuming 8-hour workday)
- **Per Year**: 240,000 registrations
- **With Versioning**: ~480,000 rows (assuming 2x for versions)

### Performance Strategy

**1. Table Partitioning**
```sql
-- Partition by quarter (4 partitions per year)
-- Each partition holds ~60k records (manageable size)
-- Query performance: O(log n) per partition vs O(n) for full table
```

**2. Partial Indexes**
```sql
-- Index only current versions (90% of queries)
CREATE INDEX idx_cost_registrations_current
ON cost_registrations(cost_element_id, amount)
WHERE upper(valid_time) IS NULL AND deleted_at IS NULL;

-- Result: 10x smaller index, faster queries
```

**3. Caching Strategy**
```python
# Cache budget status for 5 minutes
# Key: "budget_status:{cost_element_id}"
# TTL: 300 seconds
# Invalidate on: cost_registration create/update/delete
```

**4. Async Task Queue (Future)**
```python
# For very large imports (>1000 records)
# Use Celery or background tasks
# Provide job ID for progress tracking
```

### Performance Targets

| Operation | Target | Strategy |
|-----------|--------|----------|
| Single CREATE | <100ms | Partial index, cache budget status |
| List (paginated) | <200ms | Partial index, partition pruning |
| Budget status | <50ms | Cached (5min TTL), partial index |
| Time-travel query | <300ms | GIST index on temporal ranges |
| Impact analysis | <500ms | Cached costs, branch comparison |

### Monitoring

- Track query performance with PostgreSQL `pg_stat_statements`
- Monitor table growth and partition usage
- Alert on slow queries (>1s)
- Track cache hit/miss ratio

---

## Decision Summary

**Selected Approach:** Versioned CostRegistration (Non-Branchable)

**Rationale:**
1. **Versioned but not branchable** - Costs are global facts, not subject to change orders
2. **Follows existing pattern** - `CostElementType` is versioned but not branchable
3. **Supports mandatory requirements** - Change order impact analysis, historical tracking
4. **Team expertise** - High EVCS experience enables efficient implementation
5. **Performance addressed** - Partitioning, indexing, caching strategies for 20k/month

**Key Design Decisions:**
- Use `VersionableMixin` only (NOT `BranchableMixin`)
- Extend `TemporalService` (NOT `BranchableService`)
- Costs are global - query from main branch only
- Budgets are branchable - compare branch budget vs global costs
- Table partitioning by quarter for high volume
- Partial indexes for current versions only
- Cache budget status with 5-minute TTL

**Next Steps:**
1. Proceed to PLAN phase with this approach
2. Create detailed implementation plan
3. Define database schema with partitioning
4. Specify API contracts
5. Plan testing strategy

---

## References

- [Product Backlog: E05-U01](../product-backlog.md#e05-u01-register-actual-costs-against-cost-elements)
- [Bounded Contexts: Cost Element & Financial Tracking](../../02-architecture/01-bounded-contexts.md#6-cost-element--financial-tracking)
- [Coding Standards](../../02-architecture/coding-standards.md)
- [Cost Element Model](../../../backend/app/models/domain/cost_element.py) - Branchable pattern
- [Cost Element Type Model](../../../backend/app/models/domain/cost_element_type.py) - **Non-branchable versioned pattern (reference)**
- [Cost Element Service](../../../backend/app/services/cost_element_service.py)
- [Cost Element API](../../../backend/app/api/routes/cost_elements.py)
- [Analysis Prompt Template](../../04-pdca-prompts/analysis-prompt.md)
