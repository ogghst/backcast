# Functional Design Document & Implementation Plan: E2-005 Time-Phased Budget Planning

**Task:** E2-005 - Time-Phased Budget Planning
**Sprint:** Sprint 2 - Budget Allocation and Revenue Distribution
**Status:** Planning Complete - Ready for Implementation
**Date:** 2025-01-27

---

## WORKING AGREEMENTS ACKNOWLEDGMENT

✅ **Test-Driven Development (TDD):** All code changes must be preceded by failing tests
✅ **Incremental Change:** Small, atomic commits (<100 lines, <5 files target)
✅ **Architectural Respect:** Follow existing patterns and abstractions
✅ **No Code Duplication:** Reuse existing implementations

---

## Objective

Enable users to visualize how budget (BAC) is distributed and consumed over time for one or multiple cost elements and WBEs based on their schedule baselines. Users can filter and select cost elements by project, WBE, or individual selection. The visualization uses each schedule's progression type (linear, gaussian, logarithmic) to calculate and display aggregated time-phased budget consumption, forming the foundation for Planned Value (PV) calculations in future sprints.

---

## Requirements Summary

**From PRD (Section 6.1 & 6.1.1):**
- Enable users to define time-phased budget consumption plans
- Use schedule baseline (start_date, end_date, progression_type) to determine time periods
- Support progression types: linear, gaussian, logarithmic
- Form basis for planned value calculation in EVM

**From Plan.md:**
- Time-phased budget planning enables users to define expected timing of cost incurrence
- Uses schedule data from E2-003 (Cost Element Schedule Management)
- Supports time-phased entry and visualization

**From Analysis (sprint2_high_level_analysis.md):**
- Additional UI to visualize time-phased budget consumption
- Visual timeline showing budget consumption over time
- Uses CostElementSchedule to determine time periods
- Charts budget_bac distribution based on progression_type

---

## Functional Design

### 1. Business Requirements

**User Story:**
As a project manager, I want to visualize how one or multiple WBE or cost element's budget (BAC) is distributed over its schedule period, so that I can understand the expected timing of budget consumption and verify the time-phased plan aligns with project expectations.

**Acceptance Criteria:**
1. Given one or multiple cost elements or WBEs with schedules (start_date, end_date, progression_type) and budget_bac, the system displays a timeline chart showing budget consumption over the schedule period
2. Users can filter and select cost elements using a filter interface with options:
   - Single cost element (by ID)
   - Multiple cost elements (by selection)
   - All cost elements within a specific WBE
   - All cost elements across multiple WBEs (by WBE selection)
   - All cost elements within a project
   - One or multiple cost element types (filtering by cost_element_type_id)
   - Combined filters: e.g., all cost elements of specific types within selected WBE(s) or project
3. The filter interface components are flexible and reusable across different contexts:
   - Project page: Filter all cost elements in the project (with optional WBE and type filters)
   - WBE page: Filter all cost elements in the WBE (with optional type filter)
   - Cost element page: Filter individual or selected cost elements
   - Dedicated budget timeline page: Full filtering capabilities
4. The chart shows cumulative budget consumption based on the progression type (linear, gaussian, logarithmic) for each selected cost element
5. When multiple cost elements are selected, the chart aggregates their budgets and displays either:
   - Individual lines for each cost element (multi-line chart)
   - Aggregated cumulative total (single line showing sum)
6. Users can view the time-phased budget plan from a dedicated page or section with filter interface
7. The visualization updates automatically when schedule or budget changes
8. The chart supports different time granularities (daily, weekly, monthly) for viewing
9. The visualization clearly shows total budget (BAC) and how it's distributed over time
10. The filter interface allows building selections before calculation, with clear indication of selected items

### 2. Data Requirements

**Input Data:**
- Filter selection: `projectId`, `wbeIds[]`, `costElementIds[]`, `costElementTypeIds[]`
- For each selected cost element:
  - `cost_element.budget_bac` - Total budget to distribute
  - `cost_element_schedule.start_date` - Schedule start date
  - `cost_element_schedule.end_date` - Schedule end date
  - `cost_element_schedule.progression_type` - Distribution curve type (linear, gaussian, logarithmic)
  - `cost_element.department_name` - For legend/identification
  - `cost_element.cost_element_type_id` - For type filtering

**Output Data (Calculated):**
- Time-phased budget consumption data points per cost element
- Aggregated cumulative budget values at each time point (sum across all selected)
- Individual cumulative budget values per cost element (for multi-line view)
- Period budget values (budget consumed per period)

**Progression Type Formulas:**
- **Linear:** Even distribution: `%_complete = (days_elapsed / total_days)`
- **Gaussian:** Normal distribution curve with peak at midpoint (will use approximation)
- **Logarithmic:** Slow start with accelerating completion (will use logarithmic curve)

### 3. User Interface Requirements

**Component Location:**
- **New dedicated page/route:** `/projects/:projectId/budget-timeline` or similar
- **Alternative:** Modal dialog accessible from project detail page
- Should be accessible from project, WBE, and cost element contexts

**Filter Interface Requirements:**
- Filter selection panel with clear options:
  - **Context-aware display:** Shows/hides filters based on component context (project/WBE/cost element page)
  - **Scope selector:** Project | WBE(s) | Cost Element(s) (context-dependent)
  - **Project selector:** Dropdown to select project (if multiple projects or context allows)
  - **WBE selector:** Multi-select dropdown/tags for WBE selection (hidden if on WBE page)
  - **Cost Element Type selector:** Multi-select dropdown for cost element types (filter by type_code/type_name)
  - **Cost Element selector:** Multi-select with search/filter for cost elements (context-dependent)
  - **Quick filters:**
    - "All cost elements in project" (project page context)
    - "All cost elements in selected WBE(s)" (project page context)
    - "All cost elements in this WBE" (WBE page context)
    - "All cost elements of selected types" (any context)
    - "Selected cost elements" (any context)
  - **Selection summary:** Shows count of selected items (e.g., "3 WBEs, 2 types, 15 cost elements")
  - **Apply/Clear buttons:** Build filter and trigger calculation
- **Component Flexibility:**
  - Components accept context props to control which filters are shown
  - Filters can be embedded in different pages (project, WBE, cost element)
  - Filter state can be pre-populated based on page context (e.g., WBE page pre-selects that WBE)

**Visualization Requirements:**
- Line chart showing cumulative budget consumption over time
- **Multi-line mode:** Individual lines for each cost element (toggle on/off)
- **Aggregated mode:** Single line showing sum of all selected cost elements (default)
- X-axis: Time (dates from earliest start_date to latest end_date across all selected)
- Y-axis: Cumulative budget value (from 0 to sum of all budget_bac)
- Support for different time granularities (monthly by default)
- Visual indicators for key dates (earliest start, current date, latest end)
- **Legend:**
  - In multi-line mode: One entry per cost element (department name, color)
  - In aggregated mode: Single entry showing total budget
- **Chart controls:**
  - Toggle between multi-line and aggregated view
  - Time granularity selector (daily/weekly/monthly)
  - Zoom/pan controls
- Responsive design for mobile/tablet

### 4. Technical Requirements

**Backend:**
- **NEW:** API endpoint to fetch cost elements with schedules for filtering
  - `GET /api/v1/projects/{project_id}/cost-elements-with-schedules`
  - Query parameter: `wbe_ids[]` (optional, filter by WBE IDs)
  - Query parameter: `cost_element_ids[]` (optional, filter by cost element IDs)
  - Query parameter: `cost_element_type_ids[]` (optional, filter by cost element type IDs)
  - Returns cost elements with their schedules for a project/WBE/type
  - Enables efficient filtering without multiple requests
- Calculation utility functions for progression types (can be client-side)
- Formulas must match future PV calculation engine requirements

**Frontend:**
- Chart library: react-chartjs-2 (already used in E2-006 BudgetSummary)
- Calculation functions for each progression type
- **Aggregation functions:** Sum multiple cost element timelines
- **Filter interface component:** Multi-select, search, quick filters
- Time series data generation (daily, weekly, monthly buckets)
- **Multi-line chart support:** Multiple datasets, color management
- Responsive chart component

---

## Implementation Approach

**Strategy:** Client-Side Calculation with Backend Data Fetching
- Backend provides efficient endpoint for fetching cost elements with schedules
- Calculate time-phased budget distribution in frontend using schedule data
- Aggregation logic runs client-side (deterministic calculations)
- Reuse react-chartjs-2 library from E2-006
- Follow existing component patterns (BudgetSummary, DataTable)

**Architecture Pattern:**
- **Backend:** New API endpoint for fetching cost elements with schedules
- **Frontend Filter Interface:** `BudgetTimelineFilter.tsx` component
- **Frontend Visualization:** `BudgetTimeline.tsx` component (accepts multiple cost elements)
- **Frontend Page/Route:** New route for budget timeline view
- **Calculations:** Utility functions for progression types and aggregation
- **Chart:** Multi-line or aggregated line chart using Chart.js with time axis

---

## Data Model Analysis

### Existing Data (No Changes Needed)
- ✅ `CostElement.budget_bac` - Total budget
- ✅ `CostElementSchedule.start_date` - Schedule start
- ✅ `CostElementSchedule.end_date` - Schedule end
- ✅ `CostElementSchedule.progression_type` - Distribution type

### Calculation Logic

**Time Period Calculation:**
```typescript
interface TimePeriod {
  date: Date;
  cumulativePercent: number;  // 0.0 to 1.0
  cumulativeBudget: number;   // 0 to budget_bac
  periodBudget: number;        // Budget for this period
}

// Linear Progression
function calculateLinearProgression(
  startDate: Date,
  endDate: Date,
  budgetBac: number,
  timePoints: Date[]
): TimePeriod[] {
  const totalDays = differenceInDays(endDate, startDate);
  return timePoints.map(date => {
    const daysElapsed = differenceInDays(date, startDate);
    const percentComplete = Math.min(Math.max(daysElapsed / totalDays, 0), 1);
    return {
      date,
      cumulativePercent: percentComplete,
      cumulativeBudget: budgetBac * percentComplete,
      periodBudget: calculatePeriodBudget(...)
    };
  });
}

// Gaussian Progression (approximation using normal CDF)
function calculateGaussianProgression(
  startDate: Date,
  endDate: Date,
  budgetBac: number,
  timePoints: Date[]
): TimePeriod[] {
  // Use normal distribution curve with peak at midpoint
  // Implement using error function approximation
}

// Logarithmic Progression
function calculateLogarithmicProgression(
  startDate: Date,
  endDate: Date,
  budgetBac: number,
  timePoints: Date[]
): TimePeriod[] {
  // Logarithmic curve: slow start, accelerating completion
  // Use log curve scaled to duration
}
```

**Note:** Progression formulas must match future PV calculation engine (E4-001) requirements. Need to coordinate with Sprint 4 planning.

---

## Phase Breakdown

### Phase 0: Backend API Endpoint for Cost Elements with Schedules (TDD - Backend First)

**Objective:** Create API endpoint to efficiently fetch cost elements with their schedules for filtering

**Files to Create:**
1. `backend/app/api/routes/budget_timeline.py` - New router for budget timeline endpoints

**Files to Modify:**
1. `backend/app/api/__init__.py` - Register new router

**Test Files:**
1. `backend/tests/api/routes/test_budget_timeline.py` - New test file

**Commits (Target: <100 lines, <5 files per commit):**

**Commit 0.1:** Add failing test for cost elements with schedules endpoint
- Test: `test_get_cost_elements_with_schedules_by_project()`
- Test: `test_get_cost_elements_with_schedules_by_wbe()`
- Test: `test_get_cost_elements_with_schedules_by_type()`
- Test: `test_get_cost_elements_with_schedules_combined_filters()`
- Test: `test_get_cost_elements_with_schedules_filtered()`
- Test: `test_get_cost_elements_with_schedules_missing_schedule()`

**Commit 0.2:** Implement cost elements with schedules endpoint
- Endpoint: `GET /api/v1/projects/{project_id}/cost-elements-with-schedules`
- Query parameter: `wbe_ids[]` (optional, filter by WBE IDs)
- Query parameter: `cost_element_ids[]` (optional, filter by cost element IDs)
- Query parameter: `cost_element_type_ids[]` (optional, filter by cost element type IDs)
- Returns: Array of cost elements with nested schedule data
- Response schema: `CostElementWithSchedulePublic`
- Applies filters with AND logic (all specified filters must match)

**Commit 0.3:** Add response schema model
- Create `CostElementWithSchedulePublic` schema
- Includes cost element fields + schedule fields (or null if missing)
- Export from models

**Commit 0.4:** Add edge case tests and error handling
- Test: Project not found (404)
- Test: Empty project (no cost elements)
- Test: Cost elements without schedules (null schedule)
- Test: Invalid project ID format
- Test: No cost elements match type filter
- Test: Combined filters with no matches

**Estimated Time:** 3-4 hours
**Test Target:** 8-10 tests passing

---

### Phase 1: Progression Calculation Utilities (TDD - Backend/Frontend Utilities)

**Objective:** Implement calculation functions for each progression type with comprehensive tests

**Files to Create:**
1. `frontend/src/utils/progressionCalculations.ts` - Progression calculation utilities

**Test Files:**
1. `frontend/src/utils/__tests__/progressionCalculations.test.ts` - Unit tests

**Commits (Target: <100 lines, <5 files per commit):**

**Commit 1.1:** Add failing test for linear progression calculation
- Test: `test_linearProgression_evenDistribution()`
- Test: `test_linearProgression_atStartDate()`
- Test: `test_linearProgression_atEndDate()`
- Test: `test_linearProgression_midpoint()`

**Commit 1.2:** Implement linear progression function
- Function: `calculateLinearProgression()`
- Returns: Array of time periods with cumulative budget values
- Handles edge cases (before start, after end, exact dates)

**Commit 1.3:** Add failing test for gaussian progression calculation
- Test: `test_gaussianProgression_peakAtMidpoint()`
- Test: `test_gaussianProgression_slowStart()`
- Test: `test_gaussianProgression_acceleratingEnd()`
- Test: `test_gaussianProgression_totalBudgetReached()`

**Commit 1.4:** Implement gaussian progression function
- Function: `calculateGaussianProgression()`
- Uses normal distribution CDF approximation
- Peak at midpoint, symmetric curve

**Commit 1.5:** Add failing test for logarithmic progression calculation
- Test: `test_logarithmicProgression_slowStart()`
- Test: `test_logarithmicProgression_acceleratingCompletion()`
- Test: `test_logarithmicProgression_totalBudgetReached()`

**Commit 1.6:** Implement logarithmic progression function
- Function: `calculateLogarithmicProgression()`
- Logarithmic curve scaled to schedule duration
- Slow start, accelerating toward end

**Commit 1.7:** Add edge case tests and validation
- Test: Invalid date ranges
- Test: Zero budget
- Test: Single day duration
- Test: Invalid progression types

**Estimated Time:** 4-6 hours
**Test Target:** 15-20 tests passing

---

### Phase 2: Time Series Data Generation

**Objective:** Create utility to generate time point arrays for chart visualization

**Files to Create/Modify:**
1. `frontend/src/utils/timeSeriesGenerator.ts` - Time series generation

**Test Files:**
1. `frontend/src/utils/__tests__/timeSeriesGenerator.test.ts` - Unit tests

**Commits:**

**Commit 2.1:** Add failing test for time series generation
- Test: `test_generateTimeSeries_daily()`
- Test: `test_generateTimeSeries_weekly()`
- Test: `test_generateTimeSeries_monthly()`
- Test: `test_generateTimeSeries_includesStartAndEnd()`

**Commit 2.2:** Implement time series generation
- Function: `generateTimeSeries(startDate, endDate, granularity)`
- Granularities: 'daily', 'weekly', 'monthly'
- Returns: Array of Date objects

**Commit 2.3:** Add edge case tests
- Test: Single day range
- Test: Very short ranges (< 7 days)
- Test: Very long ranges (> 365 days)
- Test: Invalid granularity

**Estimated Time:** 1-2 hours
**Test Target:** 8-10 tests passing

---

### Phase 2.5: Aggregation Utilities

**Objective:** Create utilities to aggregate multiple cost element timelines

**Files to Create:**
1. `frontend/src/utils/timelineAggregation.ts` - Aggregation utilities

**Test Files:**
1. `frontend/src/utils/__tests__/timelineAggregation.test.ts` - Unit tests

**Commits:**

**Commit 2.5.1:** Add failing test for timeline aggregation
- Test: `test_aggregateTimelines_singleElement()`
- Test: `test_aggregateTimelines_multipleElements()`
- Test: `test_aggregateTimelines_overlappingDates()`
- Test: `test_aggregateTimelines_differentProgressionTypes()`

**Commit 2.5.2:** Implement timeline aggregation function
- Function: `aggregateTimelines(timePeriodsByElement[])`
- Merges time points across all elements
- Sums cumulative budgets at each time point
- Handles different date ranges

**Commit 2.5.3:** Add edge case tests
- Test: Empty array
- Test: Single element
- Test: Elements with no overlap
- Test: Elements with identical schedules

**Estimated Time:** 2-3 hours
**Test Target:** 8-10 tests passing

---

### Phase 3: Filter Interface Component

**Objective:** Create filter interface for selecting cost elements and WBEs

**Files to Create:**
1. `frontend/src/components/Projects/BudgetTimelineFilter.tsx` - Filter interface component

**Commits:**

**Commit 3.1:** Create BudgetTimelineFilter component structure
- Component props: `projectId`, `context`, `onFilterChange(callback)`, `initialFilters?`
- Context enum: `"project" | "wbe" | "cost-element" | "standalone"`
- Use TanStack Query to fetch WBEs, cost elements, and cost element types
- Basic structure with context-aware filter visibility
- Pre-populate filters from `initialFilters` prop

**Commit 3.2:** Implement project and WBE selectors
- Project dropdown (if multiple projects context)
- WBE multi-select with tags/chips
- Quick filter: "All cost elements in project"
- Display selected WBE count

**Commit 3.3:** Implement cost element type and cost element selectors
- Cost Element Type multi-select dropdown with search
- Filter by type_code/type_name
- Display selected type count
- Cost Element multi-select dropdown with search
- Filter by selected WBEs and types
- Display selected cost element count
- Quick filters: "All in selected WBE(s)", "All of selected types", "Selected cost elements"

**Commit 3.4:** Add selection summary and actions
- Selection summary: "X WBEs, Y types, Z cost elements" (context-aware)
- Apply button: Triggers filter and calculation
- Clear button: Resets all selections
- Visual feedback for selected items
- Show/hide filters based on context (e.g., hide WBE selector on WBE page)

**Commit 3.5:** Add styling and responsive design
- Chakra UI components (Select, Checkbox, Button, Badge)
- Responsive layout for mobile/tablet
- Clear visual hierarchy
- Loading states while fetching data

**Estimated Time:** 4-5 hours
**Test Target:** Component renders, selections work, callbacks fire correctly

---

### Phase 5: Budget Timeline Page/Route

**Objective:** Create dedicated page/route for budget timeline visualization with filter interface

**Files to Create:**
1. `frontend/src/routes/_layout/projects.$id.budget-timeline.tsx` - Budget timeline page route

**Files to Modify:**
1. `frontend/src/routes/_layout/projects.$id.tsx` - Add navigation link to budget timeline

**Commits:**

**Commit 5.1:** Create budget timeline route structure
- New route: `/projects/:projectId/budget-timeline`
- Use TanStack Router patterns
- Fetch project data
- Basic page layout

**Commit 5.2:** Integrate filter interface and timeline
- Add BudgetTimelineFilter component with `context="standalone"`
- Add BudgetTimeline component
- Connect filter selections to timeline
- Fetch cost elements with schedules based on filter

**Commit 5.3:** Add page layout and navigation
- Page title and description
- Link from project detail page
- Breadcrumb navigation
- Loading and error states
- Responsive layout

**Estimated Time:** 3-4 hours
**Test Target:** Page renders, navigation works, filter and timeline integrated

---

### Phase 5.5: Integration into Project, WBE, and Cost Element Pages

**Objective:** Embed BudgetTimelineFilter and BudgetTimeline components in existing pages with context-aware filtering

**Files to Modify:**
1. `frontend/src/routes/_layout/projects.$id.tsx` - Add budget timeline section
2. `frontend/src/routes/_layout/projects.$id.wbes.$wbeId.tsx` - Add budget timeline section
3. `frontend/src/components/Projects/EditCostElement.tsx` - Add budget timeline section (optional)

**Commits:**

**Commit 5.5.1:** Add budget timeline to project detail page
- Add BudgetTimelineFilter with `context="project"`
- Add BudgetTimeline component
- Pre-select all cost elements in project (or user selection)
- Position near budget summary section
- Collapsible section or separate tab

**Commit 5.5.2:** Add budget timeline to WBE detail page
- Add BudgetTimelineFilter with `context="wbe"`
- Pre-select current WBE in `initialFilters`
- Hide WBE selector (already in context)
- Add BudgetTimeline component
- Position near budget summary section

**Commit 5.5.3:** Add budget timeline to cost element edit dialog (optional)
- Add BudgetTimelineFilter with `context="cost-element"`
- Pre-select current cost element in `initialFilters`
- Show single cost element timeline
- Add as additional section/tab in EditCostElement dialog

**Estimated Time:** 3-4 hours
**Test Target:** Components render correctly in each context, filters work appropriately, no layout issues

---

### Phase 6: Integration into Existing Views (Optional - if not embedded)

**Objective:** Add quick access to budget timeline page from project/WBE detail pages (alternative to embedded components)

**Files to Modify:**
1. `frontend/src/routes/_layout/projects.$id.tsx` - Add budget timeline button/link
2. `frontend/src/routes/_layout/projects.$id.wbes.$wbeId.tsx` - Add budget timeline button/link

**Commits:**

**Commit 6.1:** Add budget timeline link to project detail
- Button/link to budget timeline page
- Pre-select project in filter via URL params
- Positioned near budget summary section

**Commit 6.2:** Add budget timeline link to WBE detail
- Button/link to budget timeline page
- Pre-select WBE in filter via URL params
- Positioned near budget summary section

**Estimated Time:** 1-2 hours
**Note:** This phase is optional if Phase 5.5 (embedded components) is implemented

---

### Phase 7: Validation and Edge Cases

**Objective:** Ensure robust handling of edge cases and validation

**Commits:**

**Commit 5.1:** Add validation and error handling
- Validate schedule dates (end >= start)
- Validate budget_bac >= 0
- Handle missing schedule gracefully
- Show appropriate error messages

**Commit 5.2:** Add integration tests
- Test component renders with valid data
- Test component handles missing schedule
- Test component handles invalid dates
- Test component updates when data changes

**Commit 7.1:** Add validation and error handling
- Validate filter selections (at least one cost element selected)
- Validate schedule dates (end >= start) for all elements
- Validate budget_bac >= 0 for all elements
- Handle missing schedules gracefully
- Show appropriate error messages
- Handle empty selections

**Commit 7.2:** Add integration tests
- Test page renders with valid data
- Test filter interface works correctly
- Test timeline displays with multiple elements
- Test aggregated vs multi-line toggle
- Test navigation from project/WBE detail pages

**Commit 7.3:** Performance optimization (if needed)
- Memoize calculation results
- Optimize chart rendering for long time ranges and many elements
- Consider data sampling for very long ranges
- Debounce filter changes

**Estimated Time:** 3-4 hours

---

## Test Strategy

### Unit Tests (Frontend Utilities)

**Progression Calculations:**
- ✅ Linear: Even distribution verification
- ✅ Linear: Start date (0% complete, €0 budget)
- ✅ Linear: End date (100% complete, full budget)
- ✅ Linear: Midpoint (50% complete, 50% budget)
- ✅ Linear: Before start date (0% complete)
- ✅ Linear: After end date (100% complete)
- ✅ Gaussian: Peak at midpoint verification
- ✅ Gaussian: Slow start verification
- ✅ Gaussian: Symmetric curve verification
- ✅ Gaussian: Total budget reached at end
- ✅ Logarithmic: Slow start verification
- ✅ Logarithmic: Accelerating completion verification
- ✅ Logarithmic: Total budget reached at end
- ✅ Edge cases: Zero budget, invalid dates, single day

**Time Series Generation:**
- ✅ Daily granularity
- ✅ Weekly granularity
- ✅ Monthly granularity
- ✅ Includes start and end dates
- ✅ Edge cases: Single day, very short/long ranges

### Component Tests (Manual + Visual)

**BudgetTimelineFilter Component:**
- ✅ Renders with project data
- ✅ Context-aware filter visibility (shows/hides based on context)
- ✅ Project selector works (when context allows)
- ✅ WBE multi-select works (hidden on WBE page context)
- ✅ Cost Element Type multi-select works
- ✅ Cost element multi-select works
- ✅ Quick filters work ("All in project", "All in WBE", "All of selected types", etc.)
- ✅ Selection summary displays correctly (includes type count)
- ✅ Initial filters pre-populate correctly
- ✅ Apply button triggers callback
- ✅ Clear button resets selections
- ✅ Responsive design on mobile/tablet

**BudgetTimeline Component:**
- ✅ Renders with single cost element
- ✅ Renders with multiple cost elements
- ✅ Displays aggregated chart correctly
- ✅ Displays multi-line chart correctly
- ✅ Toggle between aggregated/multi-line works
- ✅ Shows correct progression curves for each element
- ✅ Handles missing schedules (skips or shows message)
- ✅ Handles missing budgets (shows 0 or skips)
- ✅ Updates when filter selections change
- ✅ Responsive design on mobile/tablet
- ✅ Time granularity selector works
- ✅ Chart tooltips display correctly (aggregated and multi-line)
- ✅ Legend displays correctly for multi-line mode

### Integration Tests

**Budget Timeline Page:**
- ✅ Page renders with project data
- ✅ Filter interface works correctly (standalone context)
- ✅ Timeline displays based on filter selections
- ✅ Cost element type filtering works
- ✅ Combined filters work (WBE + type, etc.)
- ✅ Navigation from project detail works
- ✅ Navigation from WBE detail works
- ✅ Pre-selected filters work (from navigation links)
- ✅ Page layout remains intact with different selections

**Component Reusability:**
- ✅ BudgetTimelineFilter works in project page context
- ✅ BudgetTimelineFilter works in WBE page context
- ✅ BudgetTimelineFilter works in cost element page context
- ✅ BudgetTimelineFilter works in standalone page context
- ✅ Filters hide/show appropriately based on context
- ✅ Initial filters pre-populate correctly in each context
- ✅ No duplicate code between different page implementations

---

## Implementation Checklist

### Phase 0: Backend API Endpoint (4 commits)
- [ ] Commit 0.1: Failing test for cost elements with schedules endpoint
- [ ] Commit 0.2: Implement cost elements with schedules endpoint
- [ ] Commit 0.3: Add response schema model
- [ ] Commit 0.4: Edge case tests and error handling

### Phase 1: Progression Calculations (7 commits)
- [ ] Commit 1.1: Failing test for linear progression
- [ ] Commit 1.2: Implement linear progression
- [ ] Commit 1.3: Failing test for gaussian progression
- [ ] Commit 1.4: Implement gaussian progression
- [ ] Commit 1.5: Failing test for logarithmic progression
- [ ] Commit 1.6: Implement logarithmic progression
- [ ] Commit 1.7: Edge case tests and validation

### Phase 2: Time Series Generation (3 commits)
- [ ] Commit 2.1: Failing test for time series generation
- [ ] Commit 2.2: Implement time series generation
- [ ] Commit 2.3: Edge case tests

### Phase 2.5: Aggregation Utilities (3 commits)
- [ ] Commit 2.5.1: Failing test for timeline aggregation
- [ ] Commit 2.5.2: Implement timeline aggregation function
- [ ] Commit 2.5.3: Edge case tests

### Phase 3: Filter Interface Component (5 commits)
- [ ] Commit 3.1: Component structure
- [ ] Commit 3.2: Implement project and WBE selectors
- [ ] Commit 3.3: Implement cost element selector
- [ ] Commit 3.4: Add selection summary and actions
- [ ] Commit 3.5: Add styling and responsive design

### Phase 4: Budget Timeline Component (6 commits)
- [ ] Commit 4.1: Component structure (multi-element support)
- [ ] Commit 4.2: Integrate progression calculations for multiple elements
- [ ] Commit 4.3: Implement aggregated Chart.js line chart
- [ ] Commit 4.4: Add multi-line chart support
- [ ] Commit 4.5: Add chart features and enhancements
- [ ] Commit 4.6: Add chart controls and visual indicators

### Phase 5: Budget Timeline Page/Route (3 commits)
- [ ] Commit 5.1: Create budget timeline route structure
- [ ] Commit 5.2: Integrate filter interface and timeline
- [ ] Commit 5.3: Add page layout and navigation

### Phase 5.5: Integration into Project, WBE, and Cost Element Pages (3 commits)
- [ ] Commit 5.5.1: Add budget timeline to project detail page
- [ ] Commit 5.5.2: Add budget timeline to WBE detail page
- [ ] Commit 5.5.3: Add budget timeline to cost element edit dialog (optional)

### Phase 6: Integration into Existing Views (Optional - if not embedded, 2 commits)
- [ ] Commit 6.1: Add budget timeline link to project detail
- [ ] Commit 6.2: Add budget timeline link to WBE detail

### Phase 7: Validation (3 commits)
- [ ] Commit 7.1: Add validation and error handling
- [ ] Commit 7.2: Add integration tests
- [ ] Commit 7.3: Performance optimization (if needed)

---

## Code Patterns to Follow

### Frontend Patterns
- Use TypeScript with strict typing
- Use date-fns or similar for date calculations (check existing)
- Follow existing component patterns (EditCostElement, BudgetSummary)
- Use Chart.js time scale for date axis
- Format currency: `toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })`
- Use Chakra UI components for layout and styling
- Error handling with try/catch and user-friendly messages

### Calculation Patterns
- Pure functions (no side effects)
- Input validation (dates, budget values)
- Edge case handling (zero values, invalid ranges)
- Memoization for expensive calculations
- Type-safe interfaces for data structures

### Component Structure
```tsx
interface CostElementWithSchedule {
  cost_element_id: string;
  department_name: string;
  budget_bac: number;
  cost_element_type_id: string;
  schedule: {
    start_date: string; // ISO date string
    end_date: string;    // ISO date string
    progression_type: string; // "linear" | "gaussian" | "logarithmic"
  } | null;
}

type FilterContext = "project" | "wbe" | "cost-element" | "standalone";

interface BudgetTimelineFilterProps {
  projectId: string;
  context: FilterContext;
  onFilterChange: (filter: {
    wbeIds?: string[];
    costElementIds?: string[];
    costElementTypeIds?: string[];
  }) => void;
  initialFilters?: {
    wbeIds?: string[];
    costElementIds?: string[];
    costElementTypeIds?: string[];
  };
}

interface BudgetTimelineProps {
  costElements: CostElementWithSchedule[];
  viewMode?: "aggregated" | "multi-line"; // Default: "aggregated"
}

// Usage on Project Page
<BudgetTimelineFilter
  projectId={projectId}
  context="project"
  initialFilters={{}} // Optional: pre-select all in project
  onFilterChange={(filter) => {
    // Fetch cost elements with schedules based on filter
    // Update BudgetTimeline
  }}
/>

// Usage on WBE Page
<BudgetTimelineFilter
  projectId={projectId}
  context="wbe"
  initialFilters={{ wbeIds: [wbeId] }} // Pre-select current WBE
  onFilterChange={(filter) => {
    // Fetch cost elements with schedules based on filter
  }}
/>

// Usage on Cost Element Page
<BudgetTimelineFilter
  projectId={projectId}
  context="cost-element"
  initialFilters={{ costElementIds: [costElementId] }} // Pre-select current element
  onFilterChange={(filter) => {
    // Fetch cost elements with schedules based on filter
  }}
/>

<BudgetTimeline
  costElements={selectedCostElements}
  viewMode="aggregated"
/>
```

---

## Estimated Timeline

- **Phase 0 (Backend API Endpoint):** 3-4 hours
- **Phase 1 (Progression Calculations):** 4-6 hours
- **Phase 2 (Time Series Generation):** 1-2 hours
- **Phase 2.5 (Aggregation Utilities):** 2-3 hours
- **Phase 3 (Filter Interface):** 5-6 hours (increased for context-aware and type filtering)
- **Phase 4 (Budget Timeline Component):** 5-7 hours
- **Phase 5 (Budget Timeline Page/Route):** 3-4 hours
- **Phase 5.5 (Integration into Existing Pages):** 3-4 hours
- **Phase 6 (Integration into Existing Views):** 1-2 hours (optional, if not doing Phase 5.5)
- **Phase 7 (Validation):** 3-4 hours

**Total:** ~30-42 hours (4-5.5 days)

---

## Risk Assessment

**Low Risk:**
- Reuses existing Chart.js library (already in project)
- Calculation logic is deterministic (no backend complexity)
- Follows established component patterns

**Medium Risk:**
- **Progression formula accuracy:** Must match future PV calculation engine
  - **Mitigation:** Coordinate with Sprint 4 (E4-001) planning to ensure formulas match
  - **Mitigation:** Create shared calculation utilities that both frontend and backend can use
- **Performance with long time ranges:** Many data points could slow chart
  - **Mitigation:** Use appropriate granularity (monthly default), consider data sampling
- **Gaussian/Logarithmic formula complexity:** May need research for correct implementation
  - **Mitigation:** Start with simplified versions, refine based on PV calculation requirements

**High Risk:**
- None identified

**Known Dependencies:**
- Requires CostElementSchedule (E2-003) - ✅ Complete
- Requires Chart.js dependencies (react-chartjs-2) - ✅ Already in project (E2-006)
- Requires CostElement.budget_bac field - ✅ Complete

**Future Coordination:**
- **Sprint 4 (E4-001):** Planned Value calculation must use same progression formulas
- Consider extracting progression calculations to shared utility (backend/frontend)

---

## Success Criteria

✅ **Functionality:**
- Filter interface allows selecting cost elements by project, WBE, cost element type, or individual selection
- Filter interface is context-aware and reusable across different pages (project, WBE, cost element, standalone)
- Timeline chart displays budget consumption over schedule period for selected elements
- Supports both aggregated (sum) and multi-line (individual) views
- All three progression types (linear, gaussian, logarithmic) work correctly for each element
- Chart updates when filter selections change
- Combined filters work correctly (e.g., WBE + type, project + type)
- Handles edge cases gracefully (missing schedule, zero budget, invalid dates, empty selections)

✅ **User Experience:**
- Filter interface is intuitive and clear
- Quick filters provide fast access to common selections
- Chart is clear and easy to understand
- Toggle between aggregated and multi-line views works smoothly
- Visual indicators help identify key dates
- Responsive design works on all viewports
- Loading and error states are clear

✅ **Code Quality:**
- Comprehensive test coverage (30+ unit tests)
- Follows TDD principles (failing tests first)
- No code duplication (reuses Chart.js patterns, existing component patterns)
- Type-safe implementation
- Backend API follows existing patterns

✅ **Integration:**
- Dedicated page/route for budget timeline
- Components embedded in project, WBE, and cost element pages with context-aware behavior
- Navigation links from project and WBE detail pages (if not embedded)
- Pre-selected filters work from navigation and page context
- Components are reusable and flexible across different contexts
- Doesn't break existing functionality
- Updates automatically when data changes

---

## Notes

- **Progression Formula Alignment:** Critical to ensure formulas match future PV calculation engine (E4-001). Consider creating shared calculation module.
- **Chart Library:** Already using react-chartjs-2 from E2-006, follow existing patterns.
- **Time Granularity:** Default to monthly for readability, but allow user to change if needed.
- **Future Enhancement:** Could add comparison view showing actual cost vs planned budget consumption (requires E3-001 Cost Registration).

---

**Plan Status:** ✅ Ready for Implementation
**Next Action:** Begin Phase 0, Commit 0.1 (failing test for backend API endpoint first)
**TDD Discipline:** All commits must start with failing tests before implementation

---

## Additional Notes

### Filter Interface Design Patterns

**Multi-Select Pattern:**
- Use Chakra UI Select component with `multiple` prop or custom multi-select
- Alternative: Use Checkbox group with search/filter
- Display selected items as tags/chips for easy removal
- Follow existing DataTable multi-select patterns if available

**Quick Filter Buttons:**
- "All in Project" - Selects all cost elements in project (project context)
- "All in Selected WBE(s)" - Selects all cost elements in selected WBEs (project context)
- "All in this WBE" - Selects all cost elements in current WBE (WBE context)
- "All of Selected Types" - Selects all cost elements matching selected types (any context)
- "Selected Cost Elements" - Uses manually selected cost elements only (any context)

**Context-Aware Behavior:**
- **Project page:** Shows project selector, WBE selector, type selector, cost element selector
- **WBE page:** Hides WBE selector (already in context), shows type selector, cost element selector
- **Cost element page:** Hides WBE selector, shows type selector, cost element selector (pre-selected)
- **Standalone page:** Shows all selectors (full filtering capability)

**Selection Summary:**
- Display as: "3 WBEs selected, 15 cost elements selected"
- Show total budget: "Total budget: €1,234,567.89"
- Update in real-time as selections change

### Aggregation Logic

**Time Point Merging:**
- Collect all unique time points from all selected cost elements
- Sort chronologically
- For each time point, sum cumulative budgets from all elements that have reached that point
- Handle elements with different start/end dates (0 before start, full budget after end)

**Multi-Line Chart:**
- One dataset per cost element
- Color management: Use color palette, assign unique colors
- Legend: Department name + color indicator
- Toggle visibility of individual lines (optional enhancement)

### Performance Considerations

**Large Datasets:**
- If many cost elements selected (>20), consider defaulting to aggregated view
- Warn user if too many elements selected for multi-line view
- Consider data sampling for very long time ranges (>2 years)
- Memoize calculations to avoid recalculation on every render

**API Efficiency:**
- Backend endpoint should return only necessary fields
- Consider pagination if cost elements exceed limit
- Cache project/WBE/cost element lists if used frequently
