# Implementation Plan: E3-004 Cost History Views (Integrated into Budget Timeline)

**Task:** E3-004 - Cost History Views
**Sprint:** Sprint 3 - Cost Registration and Data Entry
**Status:** Planning Complete - Ready for Implementation
**Date:** 2025-01-27

---

## Objective

Enhance the existing Budget Timeline component to optionally display cost history (Actual Cost) alongside budget (Planned Value) for EVM comparison. Enable users to toggle between showing budget, costs, or both at project, WBE, and cost element levels.

---

## Requirements Summary

**From Analysis:**
- Cost history view integrated into Budget Timeline component (not separate)
- Display mode toggle: "budget" | "costs" | "both"
- Show Actual Cost (AC) as cumulative line over time alongside Planned Value (PV)
- Support EVM theory: PV (budget) vs AC (actual costs) comparison
- Follow Chart.js multi-dataset pattern for EVM visualization

**Visual Standards:**
- PV: Blue (#3182ce) - solid line
- AC: Red/Orange (#f56565 or #ed8936) - solid line
- EV: Green (#48bb78) - dashed line (future Sprint 4)

---

## Implementation Approach

**Strategy:** Backend-First TDD, then Frontend Enhancement
- Phase 1-3: Backend time-phased cost aggregation API with tests
- Phase 4: Frontend client regeneration
- Phase 5-7: Frontend component enhancements
- Phase 8: Testing and refinement

**Architecture Pattern:**
- Backend: Project-scoped endpoint following `/cost-elements-with-schedules` pattern
- Frontend: Enhance existing BudgetTimeline component with displayMode prop
- Chart: Multi-dataset line chart with time scale (Chart.js)

**TDD Discipline:**
- Write failing tests first for each phase
- Target <100 lines, <5 files per commit
- Comprehensive test coverage for time-series aggregation

---

## Data Model Analysis

### Time-Phased Cost Aggregation

**Response Schema:**
```python
class CostTimelinePointPublic(SQLModel):
    date: date  # Date for this point
    cumulative_cost: Decimal  # Cumulative cost up to this date
    period_cost: Decimal  # Cost for this specific period

class CostTimelinePublic(SQLModel):
    data: list[CostTimelinePointPublic]  # Time series points
    total_cost: Decimal  # Total cost across all registrations
```

**Aggregation Logic:**
- Get all cost registrations for filtered cost elements
- Group by registration_date
- Calculate cumulative cost by sorting dates and summing progressively
- Generate time series points (daily granularity, matching budget timeline)
- Aggregate costs at project/WBE/cost element levels based on filters

**Query Parameters:**
- `project_id` (path parameter)
- `wbe_ids?` (list, optional) - Filter by WBE IDs
- `cost_element_ids?` (list, optional) - Filter by cost element IDs
- `start_date?` (date, optional) - Start date for time series
- `end_date?` (date, optional) - End date for time series

---

## Phase Breakdown

### Phase 1: Backend Model Schema (TDD - Backend First)

**Objective:** Create response schemas for cost timeline data

**Files to Create:**
1. `backend/app/models/cost_timeline.py` - Schema definitions

**Commits:**

**Commit 1.1:** Create CostTimelinePointPublic schema
- Fields: `date` (date), `cumulative_cost` (Decimal), `period_cost` (Decimal)
- Use Decimal for monetary values (DECIMAL(15,2))
- Add model to `__init__.py` exports

**Commit 1.2:** Create CostTimelinePublic schema
- Fields: `data` (list[CostTimelinePointPublic]), `total_cost` (Decimal)
- Add model to `__init__.py` exports

**Estimated Time:** 30 minutes
**Test Target:** Schema validation tests (if applicable)

---

### Phase 2: Backend Aggregation Endpoint (TDD)

**Objective:** Create API endpoint that returns time-phased cost aggregation

**Files to Create:**
1. `backend/app/api/routes/cost_timeline.py` - Cost timeline endpoint

**Files to Modify:**
1. `backend/app/api/main.py` - Register router

**Commits:**

**Commit 2.1:** Add failing test for cost timeline endpoint
- Test: `test_get_project_cost_timeline()`
- Validates: Returns time series with cumulative costs by date
- Test case: Single cost registration, verify cumulative calculation

**Commit 2.2:** Implement basic cost timeline endpoint
- Endpoint: `GET /api/v1/projects/{project_id}/cost-timeline/`
- Function: `get_project_cost_timeline()`
- Query: Get all cost registrations for project (via WBEs → cost elements)
- Aggregate by date: Group by registration_date, sum amounts
- Calculate cumulative: Sort by date, progressive sum
- Generate time series: Daily points from min to max date
- Response schema: `CostTimelinePublic`
- Handle 404 if project not found

**Commit 2.3:** Add WBE filtering
- Query parameter: `wbe_ids?: list[UUID]` (optional)
- Filter cost elements by WBE IDs
- Update test: `test_get_project_cost_timeline_filtered_by_wbe()`

**Commit 2.4:** Add cost element filtering
- Query parameter: `cost_element_ids?: list[UUID]` (optional)
- Filter cost registrations by cost element IDs
- Update test: `test_get_project_cost_timeline_filtered_by_cost_elements()`

**Commit 2.5:** Add date range filtering
- Query parameters: `start_date?: date`, `end_date?: date` (optional)
- Filter time series to date range
- Update test: `test_get_project_cost_timeline_date_range()`

**Commit 2.6:** Add edge case tests
- Test: `test_get_project_cost_timeline_empty()` (no cost registrations)
- Test: `test_get_project_cost_timeline_multiple_dates()` (multiple registrations on different dates)
- Test: `test_get_project_cost_timeline_same_date()` (multiple registrations on same date)
- Test: `test_get_project_cost_timeline_not_found()` (404)

**Commit 2.7:** Register router in main.py
- Import cost_timeline router
- Add to API router: `api_router.include_router(cost_timeline.router)`

**Estimated Time:** 3-4 hours
**Test Target:** 7-8 tests passing

---

### Phase 3: Backend Tests Enhancement (TDD)

**Objective:** Ensure comprehensive test coverage for all edge cases

**Files to Create:**
1. `backend/tests/api/routes/test_cost_timeline.py` - Test suite

**Test Cases:**
1. Basic functionality with single cost registration
2. Multiple cost registrations on different dates
3. Multiple cost registrations on same date (cumulative calculation)
4. WBE filtering
5. Cost element filtering
6. Date range filtering
7. Empty project (no cost registrations)
8. Project not found (404)
9. Invalid date range (start_date > end_date)
10. Cost registrations across multiple WBEs

**Estimated Time:** 1-2 hours
**Test Target:** 10+ tests passing

---

### Phase 4: Frontend Client Generation

**Objective:** Regenerate frontend client with new cost timeline types

**Files to Modify:**
1. `frontend/src/client/sdk.gen.ts` - Regenerated client
2. `frontend/src/client/types.gen.ts` - Regenerated types

**Commits:**

**Commit 4.1:** Regenerate frontend client
- Run client generation script
- Verify new CostTimelineService and types are available

**Estimated Time:** 15 minutes

---

### Phase 5: Budget Timeline Component Enhancement

**Objective:** Add display mode and Actual Cost dataset to Budget Timeline

**Files to Modify:**
1. `frontend/src/components/Projects/BudgetTimeline.tsx`

**Commits:**

**Commit 5.1:** Add displayMode prop to BudgetTimeline
- Add prop: `displayMode?: "budget" | "costs" | "both"` (default: "budget")
- Update interface: `BudgetTimelineProps`
- Maintain backward compatibility (default shows budget only)

**Commit 5.2:** Add cost data fetching logic
- Add props: `projectId?: string`, `costElementIds?: string[]`, `wbeIds?: string[]`
- Fetch cost timeline data using CostTimelineService
- Use useQuery hook with proper query keys
- Handle loading and error states

**Commit 5.3:** Add Actual Cost dataset to chart
- Create AC dataset when displayMode includes "costs"
- Color: Red (#f56565) - solid line
- Label: "Actual Cost (AC)"
- Data: Transform cost timeline points to Chart.js format
- Add to chartData.datasets array conditionally based on displayMode

**Commit 5.4:** Update chart configuration for multi-dataset
- Update tooltips to show both PV and AC when both visible
- Update legend to show both datasets
- Ensure both datasets use same Y-axis scale
- Update Y-axis title: "Cumulative Amount (€)" when both visible

**Commit 5.5:** Handle empty states and edge cases
- Show message when no cost data available
- Handle case when cost data date range doesn't match budget date range
- Merge date ranges for proper time scale

**Estimated Time:** 2-3 hours

---

### Phase 6: Budget Timeline Filter Enhancement

**Objective:** Add display mode toggle to filter component

**Files to Modify:**
1. `frontend/src/components/Projects/BudgetTimelineFilter.tsx`

**Commits:**

**Commit 6.1:** Add display mode state and UI
- Add state: `displayMode` (default: "budget")
- Add radio buttons or toggle: "Budget", "Costs", "Both"
- Update interface: `BudgetTimelineFilterProps` to include `displayMode` and `onDisplayModeChange`

**Commit 6.2:** Connect display mode to parent
- Call `onDisplayModeChange` callback when display mode changes
- Pass display mode to parent component

**Estimated Time:** 1 hour

---

### Phase 7: Integration in Detail Pages

**Objective:** Integrate display mode state and pass to Budget Timeline

**Files to Modify:**
1. `frontend/src/routes/_layout/projects.$id.tsx`
2. `frontend/src/routes/_layout/projects.$id.wbes.$wbeId.tsx`
3. `frontend/src/routes/_layout/projects.$id.budget-timeline.tsx` (if exists)

**Commits:**

**Commit 7.1:** Add display mode state to project detail page
- Add state: `displayMode` (default: "budget")
- Pass displayMode to BudgetTimeline component
- Pass displayMode and onDisplayModeChange to BudgetTimelineFilter

**Commit 7.2:** Pass cost filtering props to BudgetTimeline
- Pass `projectId` to BudgetTimeline
- Pass filter selections (wbeIds, costElementIds) to BudgetTimeline
- Ensure cost timeline query uses same filters as budget timeline

**Commit 7.3:** Repeat for WBE detail page
- Similar changes as project detail page
- Pass `wbeId` and filter selections

**Commit 7.4:** Update budget timeline page (if exists)
- Similar integration as detail pages

**Estimated Time:** 1-2 hours

---

### Phase 8: Testing and Refinement

**Objective:** Manual testing, bug fixes, and UI refinements

**Test Scenarios:**
1. Toggle between "budget", "costs", "both" - verify chart updates
2. Filter by WBE - verify both PV and AC update correctly
3. Filter by cost element - verify both PV and AC update correctly
4. Empty states - no costs, no budget, etc.
5. Date range alignment - verify PV and AC use same time scale
6. Tooltip accuracy - verify both values show correctly
7. Legend clarity - verify both lines are labeled correctly
8. Performance - verify with large datasets (100+ cost registrations)

**Refinements:**
- Color adjustments if needed
- Tooltip formatting improvements
- Legend positioning
- Error message clarity
- Loading state indicators

**Estimated Time:** 1-2 hours

---

## Total Estimated Time

- Phase 1: 30 minutes
- Phase 2: 3-4 hours
- Phase 3: 1-2 hours
- Phase 4: 15 minutes
- Phase 5: 2-3 hours
- Phase 6: 1 hour
- Phase 7: 1-2 hours
- Phase 8: 1-2 hours

**Total: 10-14 hours**

---

## Success Criteria

- Users can toggle between "budget", "costs", or "both" in Budget Timeline
- PV and AC lines displayed on same time scale for direct comparison
- Performance is acceptable with 100+ cost registrations
- Visualization follows EVM standards (PV = blue, AC = red)
- Works at project, WBE, and cost element levels
- Backward compatible (default shows budget only, existing behavior preserved)
- All tests passing (10+ backend tests)
- Manual testing successful across all scenarios

---

## Dependencies

- E3-001: Cost Registration Interface ✅ Complete
- E3-002: Cost Aggregation Logic ✅ Complete
- E2-005: Time-Phased Budget Planning ✅ Complete

---

**Document Owner:** Development Team
**Status:** Ready for Implementation
**Next Step:** Begin Phase 1 - Backend Model Schema
