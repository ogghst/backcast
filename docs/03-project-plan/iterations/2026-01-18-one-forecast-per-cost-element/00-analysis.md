# Analysis: One Forecast Per Cost Element (Branchable)

**Created:** 2026-01-18
**Request:** Analyze architectural proposal for one-to-one relationship between Cost Elements and Forecasts, following the schedule baseline pattern
**Status:** Complete

---

## Executive Summary

This analysis evaluates a proposal to establish a **one-to-one branchable relationship** between Cost Elements and Forecasts, eliminating ambiguity in Estimate at Complete (EAC) calculations and ensuring architectural consistency with the schedule baseline pattern.

---

## Clarified Requirements

### Problem Statement

**Current State:**
- Multiple forecasts can exist for a single cost element
- This creates ambiguity in determining which forecast to use for EVM calculations (EAC, VAC, ETC)
- Users must manually select or the system must apply complex logic to determine the "active" forecast
- What-if scenario analysis is unclear when multiple forecasts exist

**Proposed Solution:**
- Enforce one forecast per cost element
- Make forecast a branchable entity (using EVCS for what-if scenarios)
- Eliminates ambiguity in EVM calculations
- Ensures architectural consistency with schedule baseline pattern

### Functional Requirements

From the functional requirements documentation and EVM specifications:

1. **Forecast Purpose** (EVM):
   - Define Estimate at Complete (EAC) for cost elements
   - Support VAC (Variance at Complete) = BAC - EAC
   - Support ETC (Estimate to Complete) = EAC - AC
   - Support versioning and branching for what-if scenarios

2. **EVM Calculation Clarity**:
   - EAC is the projected total cost for completing work
   - System must use exactly one forecast per cost element for calculations
   - No ambiguity in which forecast to use

3. **Change Order Support**:
   - Branch isolation for change orders
   - Impact analysis before approval
   - Merged view for comparison

### Non-Functional Requirements

- **Performance**: EVM calculations must complete in <100ms
- **Data Integrity**: No ambiguity in which forecast to use for calculations
- **Audit Trail**: Complete history of forecast changes
- **Usability**: Clear, intuitive interface for forecast management
- **Scalability**: Support 50 concurrent projects with 20 WBEs × 15 cost elements each

### Constraints

- **EVCS Architecture**: Must align with ADR-005 bitemporal versioning pattern
- **Schedule Baseline Pattern**: Must follow the same architectural approach
- **Existing Data**: Any migration must preserve existing forecast data
- **Change Order Workflow**: Must integrate with existing branching infrastructure

---

## Context Discovery

### Product Scope

**Relevant User Stories:**
- EVM Forecast Management - versioned, branchable forecasts
- EVM Calculations - EAC, VAC, ETC calculations
- Change Order Management - branching for what-if scenarios

**Business Requirements:**
- Provide clear, unambiguous EVM calculations (EAC, VAC, ETC)
- Support what-if scenario analysis without data confusion
- Maintain complete audit trail of forecast changes
- Enable comparison of current performance against historical forecasts

### Architecture Context

**Bounded Contexts Involved:**
1. **Cost Element & Financial Tracking** (Context 6)
   - Primary owner of forecasts
   - Cost elements are branchable entities

2. **EVCS Core** (Context 0)
   - Provides branching and versioning framework
   - ADR-005: Bitemporal Single-Table Pattern

3. **Change Order Processing** (Context 7)
   - Creates branches for what-if scenarios

4. **EVM Calculations & Reporting** (Context 8)
   - Consumer of forecasts for EAC calculations
   - Requires unambiguous forecast selection

**Existing Patterns to Follow:**
- **Schedule Baseline**: Recently migrated to 1:1 relationship (2026-01-18)
- **Branchable Entities**: CostElement, Project, WBE all use `BranchableMixin` + `VersionableMixin`
- **BranchableService**: Generic service class for CRUD with branching

**Architectural Constraints:**
- **ADR-005**: Single-table bitemporal pattern with TSTZRANGE
- **EVCS Protocol**: Entities must satisfy `BranchableProtocol` and `VersionableProtocol`
- **Query Patterns**: Temporal queries use range operators (`@>`) for time-travel
- **Indexing**: GIST indexes for range queries, partial unique indexes for current versions

### Codebase Analysis

**Current Forecast Implementation:**

**Model**: `/backend/app/models/domain/forecast.py`
- Already branchable: `class Forecast(EntityBase, VersionableMixin, BranchableMixin)`
- Has `forecast_id` (root ID), `cost_element_id` (FK), `eac_amount`, `basis_of_estimate`
- **Current Issue**: No constraint preventing multiple forecasts per cost element
- **Current Issue**: N:1 relationship (multiple forecasts → one cost element)

**Cost Element Model**: `/backend/app/models/domain/cost_element.py`
- Branchable entity: `class CostElement(EntityBase, VersionableMixin, BranchableMixin)`
- Has `schedule_baseline_id` reference (pattern to follow)
- **No Reference**: Currently no direct reference to forecast

**Reference Pattern - Schedule Baseline**:

The schedule baseline migration (20260118_080108) successfully implemented:
1. Inverted foreign key: `cost_elements.schedule_baseline_id` → `schedule_baselines.schedule_baseline_id`
2. Unique index to enforce 1:1 relationship (no FK constraint due to bitemporal nature)
3. Auto-creation on cost element creation
4. Cascade delete handling

---

## Solution Options

### Option 1: One Forecast Per Cost Element (Branchable) ✅ **PROPOSED**

**Architecture & Design:**

Enforce a strict one-to-one relationship between Cost Elements and Forecasts, leveraging EVCS branching for what-if scenarios. **Follows the exact pattern used for schedule baselines.**

**Data Model Changes:**
1. Add `forecast_id` FK to `CostElement` entity (nullable for migration)
2. Add unique constraint: `cost_element_id` → `forecast_id` (1:1)
3. Make forecast cascade delete when cost element is deleted
4. Add validation: Cannot create forecast if one exists for cost element
5. Deprecate `cost_element_id` FK in `Forecast` entity

**Service Layer Changes:**
1. Modify `ForecastService.create()` to check for existing forecast
2. Add `get_for_cost_element(cost_element_id, branch)` method
3. Add `ensure_exists(cost_element_id, branch)` method for automatic creation
4. Modify `CostElementService` to auto-create forecast on cost element creation
5. Update `soft_delete()` to prevent deletion if forecast exists

**API Layer Changes:**
1. Deprecate independent forecast creation endpoint
2. Add forecast management to cost element endpoints
3. GET `/api/v1/cost-elements/{id}/forecast` - retrieve
4. PUT `/api/v1/cost-elements/{id}/forecast` - update (create if not exists)
5. DELETE `/api/v1/cost-elements/{id}/forecast` - soft delete (with confirmation)

**EVM Calculation Logic:**
```python
# Simplified EAC calculation
async def calculate_eac(
    cost_element_id: UUID,
    branch: str = "main"
) -> Decimal:
    # Get the ONE forecast for this cost element
    forecast = await forecast_service.get_for_cost_element(
        cost_element_id=cost_element_id,
        branch=branch
    )

    if not forecast:
        raise NoForecastError(cost_element_id)

    return forecast.eac_amount
```

**Migration Strategy:**
1. Identify cost elements with multiple forecasts
2. Select most recent forecast (by `created_at`) as primary
3. Archive other forecasts (soft delete)
4. Add `forecast_id` column to `cost_elements` table
5. Add unique index on `cost_elements.forecast_id`
6. Deprecate `cost_element_id` FK in `forecasts` table

**UX Design:**

- Forecast management embedded in cost element detail view
- Single "Forecast" tab in cost element UI (no list of forecasts)
- Branch selector controls which version to view/edit
- Clear indication when switching branches affects forecast
- Validation prevents creating duplicate forecasts
- Warning when deleting forecast (requires confirmation)

**Branching Behavior:**

- Main branch: Operational forecast
- Change order branch: Modified forecast for what-if analysis
- EVM calculations automatically use forecast from selected branch
- Branch comparison shows forecast changes side-by-side

**Implementation - Key Technical Details:**

1. **Database Migration** (following schedule baseline pattern):
```sql
-- Add forecast_id to cost_elements (no FK constraint)
ALTER TABLE cost_elements
ADD COLUMN forecast_id UUID;

-- Migrate existing data (select most recent forecast per cost element)
UPDATE cost_elements ce
SET forecast_id = (
    SELECT f.forecast_id
    FROM forecasts f
    WHERE f.cost_element_id = ce.cost_element_id
      AND f.branch = 'main'
      AND f.deleted_at IS NULL
    ORDER BY f.created_at DESC
    LIMIT 1
);

-- Add unique index (enforces 1:1 relationship)
CREATE UNIQUE INDEX uq_cost_elements_forecast_id
ON cost_elements (forecast_id)
WHERE forecast_id IS NOT NULL;

-- Add index for queries
CREATE INDEX ix_cost_elements_forecast_id
ON cost_elements (forecast_id);

-- Remove cost_element_id FK from forecasts (optional, can keep for query performance)
-- ALTER TABLE forecasts DROP CONSTRAINT forecasts_cost_element_id_fkey;
```

2. **Service Validation**:
```python
class ForecastService(BranchableService[Forecast]):
    async def create_for_cost_element(
        self,
        cost_element_id: UUID,
        actor_id: UUID,
        branch: str = "main",
        **data: Any
    ) -> Forecast:
        # Check if forecast already exists
        existing = await self.get_for_cost_element(cost_element_id, branch)
        if existing:
            raise ForecastAlreadyExistsError(cost_element_id)

        # Create new forecast
        return await self.create_root(...)

    async def get_for_cost_element(
        self,
        cost_element_id: UUID,
        branch: str = "main"
    ) -> Forecast | None:
        # Query via cost element's forecast_id
        stmt = (
            select(Forecast)
            .join(CostElement, CostElement.forecast_id == Forecast.forecast_id)
            .where(
                CostElement.cost_element_id == cost_element_id,
                Forecast.branch == branch,
                Forecast.deleted_at.is_(None)
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
```

3. **Cost Element Auto-Creation**:
```python
class CostElementService(BranchableService[CostElement]):
    async def create_root(self, ...) -> CostElement:
        # Create cost element
        cost_element = await super().create_root(...)

        # Auto-create default forecast
        await forecast_service.create_for_cost_element(
            cost_element_id=cost_element.cost_element_id,
            actor_id=actor_id,
            branch=branch,
            eac_amount=cost_element.budget_amount,  # Default to BAC
            basis_of_estimate="Initial forecast based on budget"
        )

        return cost_element
```

**Trade-offs:**

| Aspect          | Assessment                 |
| --------------- | -------------------------- |
| Pros            | - **Unambiguous EVM calculations** - always use the one forecast<br>- **Leverages existing EVCS branching** - no new infrastructure<br>- **Architectural consistency** - follows schedule baseline pattern<br>- **Better UX** - no confusion about which forecast to use<br>- **Proven migration strategy** - schedule baseline pattern tested<br>- **Automatic audit trail** - via EVCS versioning |
| Cons            | - **Migration complexity** - need to resolve existing duplicates<br>- **Loss of historical forecasts** - unless archived separately<br>- **Less flexibility** - cannot have multiple "active" scenarios<br>- **Cascade delete risk** - deleting cost element deletes forecast |
| Complexity      | **Medium** - migration is main effort (proven pattern) |
| Maintainability | **Excellent** - clear, simple relationship |
| Performance     | **Excellent** - single query for EAC calculation (<100ms) |

---

## Comparison Summary

| Criteria           | Option 1: Branchable 1:1 | Option 2: Active Flag | Option 3: Non-Branchable Child | Option 4: Embedded |
| ------------------ | ------------------------- | ---------------------- | ------------------------------ | ------------------ |
| **Development Effort** | Medium (proven pattern) | Low (add flag) | Low (remove branching) | Low (collapse entity) |
| **Architectural Alignment** | **Excellent** (matches schedule baseline) | Good | Fair | Poor |
| **Migration Complexity** | Medium (proven pattern exists) | Low | Medium | Medium |
| **Performance** | Excellent (<100ms) | Good (~100ms) | Excellent (<100ms) | Excellent (<50ms) |
| **EVM Calculation Clarity** | Excellent (unambiguous) | Good (filter by active) | Excellent (direct link) | Excellent (embedded) |
| **What-If Support** | Excellent (branches) | Excellent (multiple baselines) | Fair (via cost element) | Poor (via cost element) |

---

## Recommendation

**I recommend Option 1: One Forecast Per Cost Element (Branchable)** because:

### Rationale

1. **Architectural Consistency**:
   - **Follows the exact pattern used for schedule baselines** (migrated 2026-01-18)
   - Leverages existing `BranchableMixin` and `BranchableService` infrastructure
   - Consistent with how CostElement, Project, WBE are implemented
   - Follows ADR-005 bitemporal versioning pattern

2. **Proven Migration Strategy**:
   - **Schedule baseline migration was successful** (migration: 20260118_080108)
   - Same approach can be reused for forecasts
   - Reduced risk due to proven pattern

3. **Solves the Core Problem**:
   - **Eliminates ambiguity in EVM calculations** - there's only one forecast to use
   - **Clear what-if scenario support** - branches provide isolated experiments
   - **Intuitive for users** - one forecast per cost element, branch selector controls context

4. **Performance & Scalability**:
   - **Single query for EAC calculation** (<100ms target)
   - **Efficient branching** - uses existing EVCS infrastructure

5. **Data Integrity**:
   - **Enforced 1:1 relationship** via database constraints
   - **Complete audit trail** via EVCS versioning

### Trade-offs to Consider

1. **Migration Complexity**:
   - Need to resolve existing duplicate forecasts
   - Must archive historical forecasts (or soft delete)
   - Frontend changes required for new API structure

2. **Loss of Multiple Active Scenarios**:
   - Cannot have multiple "active" forecasts in same branch
   - Users must create branches for what-if scenarios

---

## Decision Questions

1. **Is preserving all existing historical forecasts a requirement?**
   - If yes → Consider archiving strategy
   - If no → Option 1 can soft delete duplicates

2. **Should forecasts follow the same pattern as schedule baselines?**
   - If yes → Option 1 (1:1 Branchable) is the clear choice
   - If no → Consider alternative options

---

## References

### Architecture Documentation
- [ADR-005: Bitemporal Versioning Pattern](/home/nicola/dev/backcast_evs/docs/02-architecture/decisions/ADR-005-bitemporal-versioning.md)
- [Schedule Baseline Analysis](/home/nicola/dev/backcast_evs/docs/03-project-plan/iterations/2026-01-18-schedule-baseline-architecture/00-analysis.md)

### Code References
- [Forecast Model](/home/nicola/dev/backcast_evs/backend/app/models/domain/forecast.py)
- [CostElement Model](/home/nicola/dev/backcast_evs/backend/app/models/domain/cost_element.py)
- [Schedule Baseline Migration](/home/nicola/dev/backcast_evs/backend/alembic/versions/20260118_080108_schedule_baseline_1to1.py)

---

**Next Steps:**

Upon approval of this recommendation, proceed to **PLAN phase** to create detailed implementation plan.
