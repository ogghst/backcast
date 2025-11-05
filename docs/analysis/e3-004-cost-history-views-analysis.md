# High-Level Analysis: E3-004 Cost History Views (Integrated into Budget Timeline)

**Task:** E3-004 - Cost History Views
**Sprint:** Sprint 3 - Cost Registration and Data Entry
**Status:** Analysis Phase - Updated
**Date:** 2025-01-27
**Last Updated:** 2025-01-27 (Scope Change: Integrated into Budget Timeline)

---

## Objective

Enhance the existing Budget Timeline component to optionally display cost history (Actual Cost) alongside budget (Planned Value) for EVM comparison. This enables users to compare budgeted vs. actual costs over time at project, WBE, and cost element levels, supporting Earned Value Management analysis. The cost history visualization will be integrated directly into the Budget Timeline component with a toggle to show budget, costs, or both.

---

## Requirements Summary

**From PRD (Section 6.3):**
- System must maintain a complete audit trail of all cost registrations with timestamps and user attribution
- Cost registrations should be displayable with filtering and sorting

**From Plan.md (Sprint 3):**
- E3-004: Cost History Views - Display all recorded costs with filtering and sorting
- Sprint 3 deliverable
- Enables cost tracking and review

**From Project Status:**
- E3-001 (Cost Registration Interface) ✅ Complete - Backend API with cost categories endpoint and full CRUD for cost registrations. Frontend: cost element detail page with tabbed layout showing CostRegistrationsTable scoped to a single cost element.
- E3-002 (Cost Aggregation Logic) ✅ Complete - Backend API with 3 aggregation endpoints (cost-element, WBE, project) with optional is_quality_cost filter.
- E2-005 (Time-Phased Budget Planning) ✅ Complete - Budget Timeline component with Chart.js visualization showing Planned Value (PV) over time

**Current State:**
- ✅ Backend API `/cost-registrations/` supports listing all costs with optional `cost_element_id` filter
- ✅ Budget Timeline component exists showing Planned Value (PV) from cost element schedules
- ✅ Cost aggregation endpoints exist for project/WBE/cost element levels
- ❌ No time-phased cost history (Actual Cost accumulation over time)
- ❌ No integration of cost history into Budget Timeline component
- ❌ No EVM comparison visualization (PV vs AC)

**Scope Change (2025-01-27):**
- Cost history view will be **integrated into Budget Timeline component** (not separate)
- Add display mode toggle: "budget" | "costs" | "both"
- Show Actual Cost (AC) as cumulative line over time alongside Planned Value (PV)
- Support EVM theory: PV (budget) vs AC (actual costs) comparison at all levels

---

## 1. CODEBASE PATTERN ANALYSIS

### 1.1 Existing Budget Timeline Component

**Location:** `frontend/src/components/Projects/BudgetTimeline.tsx`

**Current Implementation:**
- ✅ Uses Chart.js `Line` chart with `react-chartjs-2`
- ✅ Time scale on X-axis (daily granularity)
- ✅ Shows Planned Value (PV) from cost element schedules
- ✅ Supports "aggregated" and "multi-line" view modes
- ✅ Uses progression calculations (linear, gaussian, logarithmic)
- ✅ Integrates with BudgetTimelineFilter component
- ✅ Props: `costElements: CostElementWithSchedulePublic[]`, `viewMode?: "aggregated" | "multi-line"`

**Pattern:**
- Time series generation via `generateTimeSeries()` utility
- Progression calculations via `calculateLinearProgression()`, `calculateGaussianProgression()`, `calculateLogarithmicProgression()`
- Timeline aggregation via `aggregateTimelines()` utility
- Chart.js configuration with time scale and tooltips

**Reusable Components:**
- Chart.js `Line` component from `react-chartjs-2`
- Time scale configuration with `chartjs-adapter-date-fns`
- Tooltip callbacks for currency formatting

**Limitations:**
- ❌ Only shows Planned Value (PV) - no Actual Cost (AC)
- ❌ No display mode toggle (budget vs costs vs both)
- ❌ No cost data integration

### 1.2 Existing Cost Aggregation Backend API

**Location:** `backend/app/api/routes/cost_summary.py`

**Current Implementation:**
- ✅ `GET /cost-summary/project/{project_id}` - Project-level aggregation
- ✅ `GET /cost-summary/wbe/{wbe_id}` - WBE-level aggregation
- ✅ `GET /cost-summary/cost-element/{cost_element_id}` - Cost element-level aggregation
- ✅ Optional `is_quality_cost` filter parameter
- ✅ Returns `CostSummaryPublic` with `total_cost`, `budget_bac`, `cost_percentage_of_budget`

**Pattern:**
- Aggregates total costs from CostRegistration records
- Calculates sums at different hierarchical levels
- Returns single aggregated value (not time-series)

**Limitations:**
- ❌ Returns only total aggregate (not time-phased)
- ❌ No date-based aggregation for time-series visualization
- ❌ No cumulative cost calculation by date

### 1.3 Cost Registration Backend API

**Location:** `backend/app/api/routes/cost_registrations.py`

**Current Implementation:**
- ✅ `GET /cost-registrations/` endpoint with optional `cost_element_id` filter
- ✅ Supports pagination
- ✅ Returns `CostRegistrationsPublic` with list of cost registrations
- ✅ Each registration has: `registration_date`, `amount`, `cost_category`, etc.

**Pattern:**
- Uses SQLModel `select()` queries
- Returns list of individual cost registrations
- Supports filtering by cost element

**Limitations:**
- ❌ No time-series aggregation (needs cumulative costs by date)
- ❌ No filtering by project_id or wbe_id (only cost_element_id)

### 1.3 Project-Scoped Endpoint Pattern

**Location:** `backend/app/api/routes/budget_summary.py`, `backend/app/api/routes/baseline_logs.py`

**Pattern:**
- Project-scoped endpoints: `/projects/{project_id}/resource/`
- WBE-scoped endpoints: `/wbes/{wbe_id}/resource/` (if applicable)
- Validation: Check project/WBE exists before processing
- Returns aggregated or filtered data scoped to parent resource

**Example:**
```python
@router.get("/projects/{project_id}/budget-summary/")
def get_project_budget_summary(
    session: SessionDep,
    _current_user: CurrentUser,
    project_id: uuid.UUID,
) -> Any:
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    # ... aggregation logic
```

### 1.4 Tabbed Layout Pattern

**Location:** `frontend/src/routes/_layout/projects.$id.tsx`

**Pattern:**
- Uses Chakra UI `Tabs.Root` with `Tabs.List`, `Tabs.Trigger`, `Tabs.Content`
- URL-synchronized tabs via `Route.useSearch()` with `tab` parameter
- Tab navigation via `navigate()` with search params
- Existing tabs: "info", "wbes", "summary", "cost-summary", "timeline", "baselines"

**Reusable Pattern:**
- Tab state management via URL search params
- Consistent tab structure across detail pages
- WBE detail page follows same pattern

---

## 2. INTEGRATION TOUCHPOINT MAPPING

### 2.1 Backend Files to Create

**File:** `backend/app/api/routes/cost_timeline.py` (NEW)
- **Purpose:** Time-phased cost aggregation endpoint for timeline visualization
- **Endpoints:**
  - `GET /projects/{project_id}/cost-timeline/` - Time-series cost data for project
  - Query parameters: `wbe_ids?`, `cost_element_ids?`, `start_date?`, `end_date?`
- **Response:** Time-series data with cumulative costs by date
- **Pattern:** Similar to `/cost-elements-with-schedules` endpoint structure

**File:** `backend/app/models/cost_timeline.py` (NEW)
- **Purpose:** Response schemas for time-phased cost data
- **Schemas:**
  - `CostTimelinePointPublic` - Single point: `date`, `cumulative_cost`, `period_cost`
  - `CostTimelinePublic` - List of points: `data: list[CostTimelinePointPublic]`, `total_cost`

### 2.2 Backend Files to Modify

**File:** `backend/app/api/routes/cost_registrations.py`
- **Action:** Add project/WBE filtering to existing endpoint (optional, for future use)
- **Changes:**
  - Add `project_id` and `wbe_id` query parameters (optional)
  - Filter logic to get cost elements via project/WBE hierarchy

### 2.3 Frontend Files to Modify

**File:** `frontend/src/components/Projects/BudgetTimeline.tsx`
- **Action:** Enhance to support cost history display
- **Changes:**
  - Add `displayMode?: "budget" | "costs" | "both"` prop
  - Add cost data fetching logic (from new cost timeline endpoint)
  - Add Actual Cost (AC) dataset to Chart.js chart
  - Update chart configuration to show PV and/or AC based on displayMode
  - Update legend to show both PV and AC when both visible
  - Update tooltips to show both values when both visible

**File:** `frontend/src/components/Projects/BudgetTimelineFilter.tsx`
- **Action:** Add display mode toggle to filter component
- **Changes:**
  - Add radio buttons or toggle for display mode: "Budget", "Costs", "Both"
  - Pass display mode to parent component via callback or prop

**File:** `frontend/src/routes/_layout/projects.$id.tsx`
- **Action:** Add display mode state and pass to BudgetTimeline
- **Changes:**
  - Add state for display mode (default: "budget" to maintain current behavior)
  - Pass display mode to BudgetTimeline component
  - Connect BudgetTimelineFilter display mode toggle to state

**File:** `frontend/src/routes/_layout/projects.$id.wbes.$wbeId.tsx`
- **Action:** Similar changes as project detail page

**File:** `frontend/src/client/sdk.gen.ts`
- **Action:** Regenerate client after backend API changes
- **Changes:**
  - New `CostTimelineService` with cost timeline endpoint methods
  - New types: `CostTimelinePointPublic`, `CostTimelinePublic`

### 2.5 Configuration Dependencies

**No configuration changes required** - uses existing API patterns and frontend components.

---

## 3. ABSTRACTION INVENTORY

### 3.1 Reusable Backend Patterns

**Validation Pattern:**
- `validate_cost_element_exists()` - Can be extended for project/WBE validation
- `validate_cost_category()` - Already exists

**Query Pattern:**
- Project-scoped filtering pattern from `budget_summary.py`
- Hierarchical query pattern (Project → WBE → CostElement) from `baseline_logs.py`

**Pagination Pattern:**
- Standard `skip`/`limit` with `count` query from existing cost_registrations endpoint

### 3.2 Reusable Frontend Patterns

**DataTable Component:**
- `frontend/src/components/DataTable/DataTable.tsx` - Fully featured with filtering, sorting, pagination
- `frontend/src/components/DataTable/TableFilters.tsx` - Client-side filtering UI
- `frontend/src/components/DataTable/types.ts` - ColumnDefExtended type with filter configuration

**Filter Components:**
- Date range filtering pattern from BudgetTimelineFilter (if exists)
- Multi-select pattern from BudgetTimelineFilter or similar

**Tab Integration:**
- Tab navigation pattern from `projects.$id.tsx`
- URL state management via `Route.useSearch()`

**Query Hooks:**
- `useQuery` from `@tanstack/react-query` for data fetching
- Query key pattern: `["cost-history", { projectId, wbeId, filters }]`

### 3.3 Test Utilities

**Backend:**
- `backend/tests/api/routes/test_cost_registrations.py` - Existing test patterns
- Test fixtures for CostRegistration creation
- Test client patterns with authentication

**Frontend:**
- Manual testing patterns (no automated tests found)
- Component testing patterns would follow existing DataTable component tests (if any)

---

## 4. ALTERNATIVE APPROACHES

### Approach 1: Integrated Budget Timeline Enhancement (Recommended)

**Description:** Enhance existing Budget Timeline component to optionally display Actual Cost (AC) alongside Planned Value (PV). Create new backend endpoint for time-phased cost aggregation. Add display mode toggle (budget/costs/both) to filter component.

**Implementation:**
- Backend: Create `/cost-timeline/` endpoint that returns cumulative costs by date (time-series)
- Frontend: Enhance BudgetTimeline component to accept cost data and display AC line
- Add display mode toggle to BudgetTimelineFilter component
- Integrate cost data fetching with existing filter logic

**Pros:**
- ✅ Follows EVM best practices (PV, AC, EV on same chart)
- ✅ Reuses existing Chart.js infrastructure
- ✅ Natural user workflow (compare budget vs actual on same timeline)
- ✅ Minimal new components (enhance existing)
- ✅ Directly supports EVM theory and Sprint 4 requirements
- ✅ Backward compatible (default shows budget only)

**Cons:**
- ⚠️ Requires new backend endpoint for time-phased aggregation
- ⚠️ Chart component becomes more complex with multiple datasets

**Alignment with Architecture:**
- ✅ Follows existing time-series pattern from budget timeline
- ✅ Consistent with Chart.js multi-dataset pattern
- ✅ Reuses existing filter and aggregation infrastructure

**Estimated Complexity:** Medium (8-10 hours)
- Backend time-phased cost endpoint: 3-4 hours
- Frontend BudgetTimeline enhancement: 2-3 hours
- Display mode toggle integration: 1-2 hours
- Testing and refinement: 1-2 hours

**Risk Factors:**
- Low risk - incremental enhancement to existing working component
- Chart.js multi-dataset pattern is well-documented

### Approach 2: Separate Cost Timeline Component

**Description:** Create new separate CostTimeline component alongside BudgetTimeline. Keep components separate, add toggle to switch between them or show side-by-side.

**Implementation:**
- Backend: Create `/cost-timeline/` endpoint (same as Approach 1)
- Frontend: Create new CostTimeline component (similar structure to BudgetTimeline)
- Add toggle or tabs to switch between Budget Timeline and Cost Timeline views

**Pros:**
- ✅ Clear separation of concerns
- ✅ Components remain simple and focused
- ✅ Easy to maintain independently

**Cons:**
- ❌ Doesn't enable direct comparison (PV vs AC on same chart)
- ❌ Violates EVM best practices (PV, AC, EV should be on same chart)
- ❌ More components to maintain
- ❌ User must switch between views to compare

**Alignment with Architecture:**
- ⚠️ Follows component separation but violates EVM visualization standards

**Estimated Complexity:** Medium-High (10-12 hours)
- Backend endpoint: 3-4 hours
- New component: 3-4 hours
- Toggle/tab integration: 1-2 hours
- Testing: 2-3 hours

**Risk Factors:**
- Medium risk - doesn't meet EVM visualization requirements
- Not recommended - goes against EVM best practices

### Approach 3: Client-Side Cost Aggregation

**Description:** Fetch all cost registrations client-side and aggregate by date in the frontend. No new backend endpoint needed.

**Implementation:**
- Backend: No changes (use existing `/cost-registrations/` endpoint)
- Frontend: Fetch all cost registrations for filtered cost elements, aggregate by date in JavaScript
- Enhance BudgetTimeline to accept aggregated cost data

**Pros:**
- ✅ No backend changes required
- ✅ Fastest to implement

**Cons:**
- ❌ Performance issues with large datasets (many API calls)
- ❌ All cost registrations loaded into memory
- ❌ Complex client-side aggregation logic
- ❌ Poor user experience with large projects

**Alignment with Architecture:**
- ❌ Doesn't follow server-side aggregation patterns
- ❌ Not scalable for production use

**Estimated Complexity:** Low (4-5 hours)
- Frontend aggregation logic: 2-3 hours
- Component integration: 1-2 hours

**Risk Factors:**
- ⚠️ High risk - performance issues with real-world data volumes
- ⚠️ Not recommended for production use

---

## 5. ARCHITECTURAL IMPACT ASSESSMENT

### 5.1 Architectural Principles

**Follows:**
- ✅ **Separation of Concerns:** Cost history view separated from cost registration CRUD
- ✅ **DRY Principle:** Reuses existing DataTable, filtering, and pagination patterns
- ✅ **RESTful Design:** Resource-based endpoints with hierarchical structure
- ✅ **Progressive Enhancement:** Builds on existing cost registration functionality
- ✅ **Consistency:** Follows established patterns from budget_summary.py and baseline_logs.py

**Potential Violations:**
- ⚠️ **Endpoint Complexity:** If enhancing existing endpoint, may become too complex with many optional parameters (mitigated by Approach 1's backward compatibility)

### 5.2 Maintenance Considerations

**Future Maintenance Burden:**
- **Low:** Follows established patterns, minimal new abstractions
- **Medium:** If using Approach 1, endpoint parameter management requires care
- **Schema Evolution:** CostRegistrationWithContextPublic schema may need updates if CostElement/WBE schemas change

**Testing Challenges:**
- **Backend:** Need comprehensive test coverage for all filter combinations
- **Frontend:** Need to test filter interactions, date range validation, multi-select behavior
- **Integration:** Need to test tab navigation, URL state persistence, filter state management

**Performance Considerations:**
- **Database Queries:** Joins with CostElement and WBE tables may impact performance with large datasets
- **Pagination:** Critical for large cost history datasets
- **Indexing:** May need indexes on `registration_date`, `cost_element_id`, `cost_category` for optimal query performance

### 5.3 Dependencies and Integration Points

**Dependencies:**
- Existing CostRegistration model and API
- CostElement and WBE models for context
- DataTable component and filtering infrastructure
- Tab navigation pattern from project detail page

**Integration Points:**
- Project detail page tab system
- WBE detail page (optional integration)
- Cost element detail page (backward compatible - existing CostRegistrationsTable still works)

**Potential Conflicts:**
- None identified - this is additive functionality

---

## 6. RISKS AND UNKNOWNS

### 6.1 Technical Risks

**Risk 1: Performance with Large Datasets**
- **Impact:** High - Large projects may have thousands of cost registrations
- **Mitigation:** Ensure proper pagination, server-side filtering, and database indexing
- **Acceptance:** Pagination and filtering should handle 1000+ cost registrations efficiently

**Risk 2: Date Range Filter Validation**
- **Impact:** Medium - Invalid date ranges could cause API errors
- **Mitigation:** Backend validation for date range (start_date <= end_date), frontend validation before API call
- **Acceptance:** Date range validation prevents invalid queries

**Risk 3: Response Schema Complexity**
- **Impact:** Low - Adding context fields may complicate response structure
- **Mitigation:** Use clear schema naming (CostRegistrationWithContextPublic), maintain backward compatibility
- **Acceptance:** Schema clearly distinguishes contextual vs. simple cost registration views

### 6.2 Business Risks

**Risk 1: User Confusion with Multiple Cost Views**
- **Impact:** Medium - Users may be confused by cost history vs. cost registrations at cost element level
- **Mitigation:** Clear naming ("Cost History" vs. "Cost Registrations"), help text, consistent UI patterns
- **Acceptance:** User testing to ensure clarity

**Risk 2: Filter Complexity**
- **Impact:** Low - Too many filter options may overwhelm users
- **Mitigation:** Progressive disclosure (collapsible filter section), sensible defaults, clear labels
- **Acceptance:** Filters should be intuitive and not hinder common use cases

### 6.3 Unknowns

**Unknown 1: Expected Data Volume**
- **Question:** How many cost registrations per project on average? Maximum?
- **Impact:** Affects pagination strategy and performance optimization
- **Resolution:** Check with stakeholders or use reasonable defaults (100 per page, max 10,000 per project)

**Unknown 2: Filter Usage Patterns**
- **Question:** Which filters will users use most frequently?
- **Impact:** Affects filter UI design and default visibility
- **Resolution:** Start with common filters (date range, cost category), add others based on feedback

**Unknown 3: Sorting Requirements**
- **Question:** What are the most common sorting needs? (date, amount, cost element, etc.)
- **Impact:** Affects default sort order and available sort columns
- **Resolution:** Default to registration_date descending (most recent first), allow sorting on all columns

---

## 7. RECOMMENDATION

**Recommended Approach:** **Approach 1 - Enhance Existing Endpoint**

**Rationale:**
1. **Reuses existing patterns** - Follows established FastAPI query parameter patterns
2. **Backward compatible** - Existing CostRegistrationsTable continues to work
3. **Single source of truth** - One endpoint for all cost registration queries
4. **Flexible** - Supports filtering at project, WBE, or cost element levels
5. **Moderate complexity** - Manageable implementation effort (6-8 hours)

**Implementation Priority:**
1. **Phase 1:** Backend endpoint enhancement with query parameters and joins
2. **Phase 2:** Schema updates (CostRegistrationWithContextPublic)
3. **Phase 3:** Frontend CostHistoryTable component
4. **Phase 4:** CostHistoryFilter component with date range and multi-select
5. **Phase 5:** Integration into project detail page tab
6. **Phase 6:** Testing and refinement

**Success Criteria:**
- Users can view all cost registrations for a project with filtering and sorting
- Performance is acceptable with 1000+ cost registrations (pagination working)
- Filter UI is intuitive and supports common use cases
- Backward compatibility maintained (existing cost element cost registrations view still works)

---

## 8. VISUALIZATION APPROACH

### EVM Standard Visualization Pattern

Based on EVM best practices and Chart.js capabilities, the enhanced Budget Timeline will display:

**Chart Type:** Multi-dataset line chart with time scale (X-axis: dates, Y-axis: cumulative amounts in €)

**Datasets:**
1. **Planned Value (PV)** - Blue line, from cost element schedules (already implemented)
   - Shows cumulative budget planned over time
   - Based on schedule progression types (linear, gaussian, logarithmic)

2. **Actual Cost (AC)** - Red/orange line, from cost registrations (to be added)
   - Shows cumulative actual costs incurred over time
   - Aggregated from cost registration dates and amounts

3. **Earned Value (EV)** - Green line (future Sprint 4)
   - Will be added when earned value recording is implemented

**Display Modes:**
- **"budget"** - Show only PV (current default behavior)
- **"costs"** - Show only AC
- **"both"** - Show PV and AC together for comparison

**Visual Standards (EVM Industry Practice):**
- PV: Blue (#3182ce) - solid line
- AC: Red/Orange (#f56565 or #ed8936) - solid line with different style
- EV: Green (#48bb78) - dashed line (future)
- Tooltips show all values at hover point
- Legend clearly labels each line

### Chart.js Implementation Pattern

Based on Context7 Chart.js documentation:
- Use `Line` chart with multiple datasets
- Time scale on X-axis (already implemented)
- Each dataset has distinct `borderColor` and `label`
- Tooltips configured to show all datasets at hover point
- Legend displays all visible datasets

---

## 9. NEXT STEPS

1. **Review and Approval:** Get stakeholder feedback on integrated approach
2. **Clarifications:**
   - Confirm EVM visualization standards (colors, line styles)
   - Confirm default display mode preference
   - Confirm date range requirements for cost aggregation
3. **Detailed Planning:** Create detailed TDD implementation plan with phase breakdown
4. **Implementation:** Proceed with Phase 1 (backend time-phased cost aggregation API)

---

**Document Owner:** Development Team
**Review Status:** Updated - Ready for Review
**Next Review:** After stakeholder feedback
**Scope Change:** Integrated into Budget Timeline component per user requirements
