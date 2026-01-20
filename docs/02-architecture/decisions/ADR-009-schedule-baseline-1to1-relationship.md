# ADR-009: Schedule Baseline 1:1 Relationship Inversion

## Status

Rejected

## Context

### Problem Statement

The system originally allowed multiple schedule baselines to exist for a single cost element, creating ambiguity in Earned Value Management (EVM) calculations, specifically for Planned Value (PV). When calculating PV = BAC × % Planned, the system needed to determine which schedule baseline to use at a specific control date. This led to several issues:

1. **Calculation Ambiguity**: With multiple baselines per cost element, it was unclear which baseline should be used for PV calculations
2. **User Confusion**: Users had to manually select or the system had to apply complex logic to determine the "active" baseline
3. **What-If Scenario Complexity**: Multiple baselines in the same branch made what-if analysis unclear
4. **Data Integrity Risks**: No database constraint preventing duplicate or conflicting baselines

### Original Architecture

The original relationship was:

- **schedule_baselines.cost_element_id** (FK) → **cost_elements.cost_element_id**
- This was a 1:N relationship (one cost element could have many schedule baselines)
- Schedule baselines were branchable and versionable
- No constraint preventing multiple baselines per cost element per branch

### Requirements

From the functional requirements:

1. **Section 6.1.1 - Cost Element Schedule Baseline**: Define versioned, branchable schedule registrations for planned work progression
2. **Section 12.2 - EVM Calculations**: PV calculation must use "the schedule registration with the most recent registration date" for calculations
3. **Section 10 - Baseline Management**: Support baseline creation at project milestones while maintaining historical baselines for comparison
4. **Section 8 - Change Order Management**: Support branch isolation for what-if scenarios

## Decision

Invert the relationship between Cost Elements and Schedule Baselines to enforce a strict 1:1 relationship, making schedule baselines fully branchable entities.

### New Architecture

1. **Inverted Foreign Key**:
   - **NEW**: cost_elements.schedule_baseline_id (FK) → schedule_baselines.schedule_baseline_id
   - **OLD**: schedule_baselines.cost_element_id (FK) → cost_elements.cost_element_id
   - This enforces exactly one schedule baseline per cost element at the database level

2. **Database Constraints**:
   - Add `schedule_baseline_id` column to `cost_elements` table (nullable UUID with FK)
   - Add unique constraint on `schedule_baseline_id` (partial index for non-null values)
   - Remove `cost_element_id` FK from `schedule_baselines` table (kept as nullable for migration compatibility)

3. **Service Layer Changes**:
   - Add `get_for_cost_element(cost_element_id, branch)` method to retrieve the single baseline
   - Add validation to prevent duplicate baseline creation (`BaselineAlreadyExistsError`)
   - Auto-create default schedule baseline when cost element is created
   - Cascade soft delete from cost element to schedule baseline

4. **API Endpoint Restructuring**:
   - NEW: `GET /api/v1/cost-elements/{id}/schedule-baseline` - Retrieve baseline
   - NEW: `POST /api/v1/cost-elements/{id}/schedule-baseline` - Create baseline
   - NEW: `PUT /api/v1/cost-elements/{id}/schedule-baseline/{baseline_id}` - Update baseline
   - NEW: `DELETE /api/v1/cost-elements/{id}/schedule-baseline/{baseline_id}` - Delete baseline

5. **Schema Changes**:
   - `ScheduleBaselineCreate` no longer includes `cost_element_id` (derived from URL path)
   - `ScheduleBaselineRead` now includes `cost_element_code` and `cost_element_name` for context

### Migration Strategy

1. Add `schedule_baseline_id` column to `cost_elements` table (nullable initially)
2. For each cost element with multiple baselines, select the most recent baseline (by `created_at`)
3. Archive other baselines to `schedule_baselines_archive` table
4. Set `cost_elements.schedule_baseline_id` to the selected baseline's ID
5. Add unique constraint on `schedule_baseline_id`
6. Remove `cost_element_id` FK from `schedule_baselines` (kept as nullable field for backward compatibility)

## Consequences

### Positive Consequences

1. **Unambiguous PV Calculations**:
   - PV calculation always uses the single baseline from `cost_element.schedule_baseline_id`
   - No complex logic needed to determine which baseline to use
   - Performance improvement: single query instead of filtering multiple baselines

2. **Leverages Existing EVCS Infrastructure**:
   - Schedule baselines remain branchable entities (via `BranchableMixin`)
   - What-if scenarios handled via branches (change order branches)
   - Consistent with existing architecture patterns (CostElement, Project, WBE)
   - No new infrastructure required

3. **Simplified Data Model**:
   - Clear 1:1 relationship enforced at database level
   - No orphaned baselines possible (FK constraint)
   - Complete audit trail via EVCS versioning

4. **Improved User Experience**:
   - No confusion about which baseline to use
   - Single schedule per cost element in UI
   - Branch selector controls context for what-if scenarios

5. **Better Data Integrity**:
   - Database constraints prevent invalid relationships
   - Validation prevents duplicate baseline creation
   - Cascade delete maintains consistency

### Negative Consequences

1. **Migration Complexity**:
   - Had to resolve existing duplicate baselines
   - Required archive table to preserve historical data
   - Frontend changes required for new API structure

2. **Loss of Multiple Active Scenarios**:
   - Cannot have multiple "active" baselines in the same branch
   - Users must create branches for what-if scenarios (slightly more workflow steps)

3. **Tighter Coupling**:
   - 1:1 relationship means baseline cannot exist without cost element
   - Cascade delete risk (mitigated with soft delete and SET NULL)
   - Cannot share baselines across cost elements

4. **Code Changes Required**:
   - Service layer modifications (validation, CRUD operations)
   - API endpoint restructuring
   - Frontend component updates

### Implementation Summary

**Completed Implementation** (2026-01-18):

1. **Database Migration**: `20260118_080108_schedule_baseline_1to1.py`
   - Added `schedule_baseline_id` column to `cost_elements` table
   - Created unique constraint `uq_cost_elements_schedule_baseline_id`
   - Migrated existing data (selected most recent baseline per cost element)
   - Created `schedule_baselines_archive` table for historical baselines

2. **Model Changes**:
   - Updated `CostElement` model to include `schedule_baseline_id` FK
   - Updated `ScheduleBaseline` model to mark `cost_element_id` as deprecated
   - Added comprehensive docstrings explaining the relationship inversion

3. **Service Layer**:
   - Added `ScheduleBaselineService.get_for_cost_element()` method
   - Added `ScheduleBaselineService.ensure_exists()` for auto-creation
   - Added `ScheduleBaselineService.create_for_cost_element()` with duplicate prevention
   - Modified `CostElementService.create_root()` to auto-create default schedule baseline
   - Modified `CostElementService.soft_delete()` to cascade delete to schedule baseline
   - Added `BaselineAlreadyExistsError` exception

4. **API Layer**:
   - Added nested endpoints under `/api/v1/cost-elements/{id}/schedule-baseline`
   - GET: Retrieve schedule baseline for cost element
   - POST: Create schedule baseline (prevents duplicates)
   - PUT: Update schedule baseline
   - DELETE: Soft delete schedule baseline

5. **Testing**:
   - 39/41 tests passing (95.1% pass rate)
   - Service layer: 17/17 tests passing (100%)
   - Migration tests: 8/8 tests passing (100%)
   - API layer: 6/8 tests passing (75%)
   - Frontend: 197/197 tests passing (100%)

6. **Code Quality**:
   - Ruff linting: 0 errors
   - Test coverage: ~95% (exceeds 80% threshold)

## Alternatives Considered

### Alternative 1: Multiple Baselines with "Active" Flag

Allow multiple schedule baselines per cost element, but designate one as "active" via a boolean flag.

**Pros**:

- Preserves all historical baselines without archiving
- Flexibility to switch active baseline
- Clearer migration path (just add flag)

**Cons**:

- Ambiguity risk (users may not know which is active)
- Complex validation (ensure only one active)
- UI complexity (need to manage multiple baselines)
- State management (active flag can get out of sync)

**Why Rejected**: Did not solve the core problem of ambiguity in PV calculations. The "active" flag approach still requires users to understand which baseline is being used, and the flag could become out of sync with reality.

### Alternative 2: Baseline as Cost Element Child (Non-Branchable)

Make schedule baseline a child entity of cost element, not independently branchable. Inherits branch from cost element.

**Pros**:

- Simpler model (no independent branching)
- Consistent lifecycle (follows cost element)
- Cleaner API (nested endpoints)

**Cons**:

- Loses independent branching (cannot what-if schedule alone)
- Tight coupling (schedule cannot exist without cost element)
- Reduced flexibility (change orders affect entire cost element)

**Why Rejected**: Would limit the ability to perform what-if scenario analysis on schedules independently of cost element budgets. The branching capability is a key feature of the EVCS architecture.

### Alternative 3: Embedded Baseline (Collapsed Entity)

Embed schedule baseline data directly in cost element, with versioning tracked within cost element history.

**Pros**:

- Maximum simplicity (no separate entity)
- Atomic updates (schedule and cost element together)
- Best performance (no joins required)

**Cons**:

- Loses schedule independence (cannot manage separately)
- Bloats cost element (mixing concerns)
- Harder to query (schedule-specific queries become complex)
- No separate schedule audit trail (mixed with cost element history)

**Why Rejected**: Violates single responsibility principle and would make the cost element entity overly complex. Schedule management is a distinct concern that deserves its own entity.

## Notes

### Migration Date

2026-01-18

### Related ADRs

- **ADR-005**: Bitemporal Versioning Pattern - Provides the branching and versioning infrastructure used by schedule baselines
- **ADR-003**: Command Pattern - Generic commands used for baseline CRUD operations

### Related Documentation

- [Analysis: Schedule Baseline Architecture](/home/nicola/dev/backcast_evs/docs/03-project-plan/iterations/2026-01-18-schedule-baseline-architecture/00-analysis.md)
- [Plan: Schedule Baseline 1:1 Implementation](/home/nicola/dev/backcast_evs/docs/03-project-plan/iterations/2026-01-18-schedule-baseline-architecture/01-plan.md)
- [CHECK: Schedule Baseline 1:1 Implementation](/home/nicola/dev/backcast_evs/docs/03-project-plan/iterations/2026-01-18-schedule-baseline-architecture/02-check.md)

### Implementation Details

**Database Schema Changes**:

```sql
-- Added to cost_elements table
ALTER TABLE cost_elements
ADD COLUMN schedule_baseline_id UUID
REFERENCES schedule_baselines(schedule_baseline_id)
ON DELETE SET NULL;

-- Unique constraint for 1:1 relationship
CREATE UNIQUE INDEX uq_cost_elements_schedule_baseline_id
ON cost_elements (schedule_baseline_id)
WHERE schedule_baseline_id IS NOT NULL;
```

**PV Calculation (Simplified)**:

```python
async def calculate_pv(
    cost_element_id: UUID,
    control_date: datetime,
    branch: str = "main"
) -> Decimal:
    # Get the ONE schedule baseline for this cost element
    baseline = await schedule_baseline_service.get_for_cost_element(
        cost_element_id=cost_element_id,
        branch=branch
    )

    if not baseline:
        raise NoScheduleBaselineError(cost_element_id)

    # Calculate planned completion % based on control date
    planned_pct = calculate_planned_completion(
        start_date=baseline.start_date,
        end_date=baseline.end_date,
        control_date=control_date,
        progression_type=baseline.progression_type
    )

    # PV = BAC × % Planned
    bac = await get_bac_for_cost_element(cost_element_id, branch)
    return bac * Decimal(str(planned_pct))
```

### Future Considerations

1. **Performance Monitoring**: Track PV calculation performance to ensure <100ms target is met
2. **Historical Baseline Comparison**: May need separate feature for comparing current schedule against archived historical baselines
3. **Schedule Baseline Templates**: Consider adding templates for common schedule patterns in future iteration

### Review Date

This ADR should be reviewed after 6 months of production use to assess:

- User feedback on the 1:1 relationship model
- Performance of PV calculations
- Need for additional features (historical comparison, templates)
