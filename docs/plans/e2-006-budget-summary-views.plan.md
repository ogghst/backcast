# Implementation Plan: E2-006 Budget Summary Views

**Task:** E2-006 - Budget Summary Views
**Sprint:** Sprint 2 - Budget Allocation and Revenue Distribution
**Status:** Planning Complete - Ready for Implementation
**Date:** 2025-01-27

---

## Objective

Display aggregated total budgets and revenues at project and WBE levels for financial overview. Provide summary cards showing budget/revenue status for quick review.

---

## Requirements Summary

**From PRD (Section 6.1 & 13.1):**
- Display aggregated total budgets and revenues at project and WBE levels
- Show total allocated budgets vs available budgets
- Show total revenue allocations vs contract values
- Provide financial overview for quick status assessment
- Available at project and WBE levels with drill-down capabilities

**From Plan.md:**
- Create summary views that display total budgets and revenues at project and WBE levels
- Summarizes budget/revenue status for review

---

## Implementation Approach

**Strategy:** Incremental Enhancement
- Add backend aggregation endpoint first (backend-first approach)
- Create reusable frontend summary component
- Integrate into existing Project and WBE detail pages
- Follow TDD with failing tests first

**Architecture Pattern:**
- Backend: Aggregation endpoint that calculates totals from existing data
- Frontend: Reusable summary component with configurable level (project/WBE)
- Visualization: Use react-chartjs-2 for interactive charts (Doughnut for utilization, Bar for comparisons)
- Integration: Add summary cards and charts above existing tables in detail views

---

## Data Model Analysis

### Fields to Aggregate

**Project Level:**
- `project.contract_value` (revenue limit)
- Sum of `wbe.revenue_allocation` (total allocated revenue)
- Sum of `cost_element.budget_bac` across all WBEs (total budget)
- Sum of `cost_element.revenue_plan` across all WBEs (total planned revenue)

**WBE Level:**
- `wbe.revenue_allocation` (revenue limit)
- Sum of `cost_element.budget_bac` for WBE (total budget)
- Sum of `cost_element.revenue_plan` for WBE (total planned revenue)

### Aggregation Structure

```typescript
interface BudgetSummary {
  level: "project" | "wbe"
  revenue_limit: number        // contract_value or wbe.revenue_allocation
  total_revenue_allocated: number  // sum of wbe.revenue_allocation or cost_element.revenue_plan
  total_budget_bac: number     // sum of cost_element.budget_bac
  total_revenue_plan: number   // sum of cost_element.revenue_plan
  remaining_revenue: number     // revenue_limit - total_revenue_allocated
  revenue_utilization_percent: number  // (total_revenue_allocated / revenue_limit) * 100
}
```

---

## Phase Breakdown

### Phase 1: Backend Aggregation Endpoint (TDD - Backend First)

**Objective:** Create API endpoint that calculates and returns budget/revenue summaries

**Files to Create:**
1. `backend/app/api/routes/budget_summary.py` - New router for budget summary endpoint

**Files to Modify:**
1. `backend/app/api/__init__.py` - Register new router
2. `backend/app/models/__init__.py` - Export new schema if needed

**Test Files:**
1. `backend/tests/api/routes/test_budget_summary.py` - New test file

**Commits (Target: <100 lines, <5 files per commit):**

**Commit 1.1:** Add failing test for project-level budget summary
- Test: `test_get_project_budget_summary()`
- Validates: Returns correct totals, handles project with no WBEs, handles project with WBEs but no cost elements

**Commit 1.2:** Implement project-level summary endpoint
- Endpoint: `GET /api/v1/budget-summary/project/{project_id}`
- Function: `get_project_budget_summary()`
- Query: Sum WBEs and cost elements, calculate totals
- Response schema: `BudgetSummaryPublic`

**Commit 1.3:** Add failing test for WBE-level budget summary
- Test: `test_get_wbe_budget_summary()`
- Validates: Returns correct totals, handles WBE with no cost elements

**Commit 1.4:** Implement WBE-level summary endpoint
- Endpoint: `GET /api/v1/budget-summary/wbe/{wbe_id}`
- Function: `get_wbe_budget_summary()`
- Query: Sum cost elements for WBE, use WBE revenue_allocation as limit
- Reuse same response schema

**Commit 1.5:** Add edge case tests
- Test: `test_get_project_budget_summary_empty_project()`
- Test: `test_get_wbe_budget_summary_empty_wbe()`
- Test: `test_get_budget_summary_not_found()`

**Commit 1.6:** Add error handling
- Handle project/WBE not found (404)
- Handle unauthorized access (403)
- Validation of IDs

**Estimated Time:** 4-6 hours
**Test Target:** 6-8 tests passing

---

### Phase 2: Backend Model Schema

**Objective:** Create response schemas for budget summary data

**Files to Create:**
1. `backend/app/models/budget_summary.py` - Schema definitions

**Commits:**

**Commit 2.1:** Create BudgetSummaryBase schema
- Fields: level, revenue_limit, total_revenue_allocated, total_budget_bac, total_revenue_plan
- Calculated fields: remaining_revenue, revenue_utilization_percent
- Use Decimal for monetary values

**Commit 2.2:** Create BudgetSummaryPublic schema
- Extends BudgetSummaryBase
- Add metadata: project_id or wbe_id, calculated_at timestamp

**Estimated Time:** 1 hour
**Test Target:** Schema validation tests

---

### Phase 3: Frontend Client Generation

**Objective:** Generate TypeScript client with new endpoints

**Files to Modify:**
1. Run `scripts/generate-client.sh` to regenerate OpenAPI client

**Commits:**

**Commit 3.1:** Regenerate frontend client
- Run client generation script
- Verify new `BudgetSummaryService` and types exported

**Estimated Time:** 15 minutes

---

### Phase 4: Frontend Summary Component

**Objective:** Create reusable BudgetSummary component

**Files to Create:**
1. `frontend/src/components/Projects/BudgetSummary.tsx` - Summary cards component

**Commits:**

**Commit 4.1:** Create BudgetSummary component structure
- Component props: `level`, `projectId?`, `wbeId?`
- Use TanStack Query to fetch summary data
- Display loading state (skeleton)

**Commit 4.1.1:** Install react-chartjs-2 dependencies
- Install: `chart.js` and `react-chartjs-2`
- Update package.json dependencies

**Commit 4.2:** Implement summary cards UI
- Card 1: Total Revenue Allocated (vs Limit)
- Card 2: Total Budget BAC
- Card 3: Total Revenue Plan
- Card 4: Utilization Percentage
- Use Chakra UI Card/Stat components

**Commit 4.3:** Add react-chartjs-2 charts
- Doughnut chart: Revenue utilization (allocated vs remaining)
- Bar chart: Budget vs Revenue comparison
- Register Chart.js elements (ArcElement, BarElement, CategoryScale, LinearScale, Tooltip, Legend)
- Responsive chart sizing

**Commit 4.4:** Add visual indicators and styling
- Color coding: Green (<80%), Yellow (80-95%), Red (>95%)
- Chart color themes matching status colors
- Format currency values
- Format percentages
- Responsive layout for cards and charts

**Estimated Time:** 3-4 hours
**Test Target:** Component renders, displays data correctly, handles loading/error states

---

### Phase 5: Integration into Project Detail Page

**Objective:** Add budget summary to project detail view

**Files to Modify:**
1. `frontend/src/routes/_layout/projects.$id.tsx`

**Commits:**

**Commit 5.1:** Add BudgetSummary component to ProjectDetail
- Import BudgetSummary component
- Add above WBEsTable section
- Pass `level="project"` and `projectId`

**Commit 5.2:** Adjust layout and styling
- Ensure responsive design
- Add spacing between summary and table
- Test on mobile/tablet viewports

**Estimated Time:** 1 hour

---

### Phase 6: Integration into WBE Detail Page

**Objective:** Add budget summary to WBE detail view

**Files to Modify:**
1. `frontend/src/routes/_layout/projects.$id.wbes.$wbeId.tsx`

**Commits:**

**Commit 6.1:** Add BudgetSummary component to WBEDetail
- Import BudgetSummary component
- Add above CostElementsTable section
- Pass `level="wbe"` and `wbeId`

**Commit 6.2:** Adjust layout and styling
- Ensure responsive design
- Match ProjectDetail layout pattern
- Test on mobile/tablet viewports

**Estimated Time:** 1 hour

---

## Test Strategy

### Backend Tests

**Unit Tests:**
- ✅ Project-level summary calculation with multiple WBEs
- ✅ Project-level summary with no WBEs
- ✅ Project-level summary with WBEs but no cost elements
- ✅ WBE-level summary calculation with multiple cost elements
- ✅ WBE-level summary with no cost elements
- ✅ Edge case: All zero values
- ✅ Edge case: Very large numbers
- ✅ Error: Project not found (404)
- ✅ Error: WBE not found (404)
- ✅ Error: Unauthorized access (403)

**Integration Tests:**
- ✅ Summary updates when WBEs added/removed
- ✅ Summary updates when cost elements added/removed
- ✅ Summary updates when revenue allocations change
- ✅ Summary updates when budgets change

### Frontend Tests (Manual + Visual)

**Component Tests:**
- ✅ Component renders with project data
- ✅ Component renders with WBE data
- ✅ Loading state displays correctly
- ✅ Error state displays correctly
- ✅ Currency formatting correct
- ✅ Percentage formatting correct
- ✅ Color indicators change based on utilization
- ✅ Responsive design works on mobile

**Integration Tests:**
- ✅ Summary displays in ProjectDetail page
- ✅ Summary displays in WBEDetail page
- ✅ Summary updates when data changes (query invalidation)

---

## Implementation Checklist

### Backend
- [ ] Phase 1: Backend aggregation endpoint (6 commits)
  - [ ] Commit 1.1: Failing test for project-level summary
  - [ ] Commit 1.2: Implement project-level endpoint
  - [ ] Commit 1.3: Failing test for WBE-level summary
  - [ ] Commit 1.4: Implement WBE-level endpoint
  - [ ] Commit 1.5: Edge case tests
  - [ ] Commit 1.6: Error handling
- [ ] Phase 2: Backend model schema (2 commits)
  - [ ] Commit 2.1: BudgetSummaryBase schema
  - [ ] Commit 2.2: BudgetSummaryPublic schema
- [ ] Phase 3: Client regeneration (1 commit)
  - [ ] Commit 3.1: Regenerate frontend client

### Frontend
- [ ] Phase 4: Summary component (3 commits)
  - [ ] Commit 4.1: Component structure with query
  - [ ] Commit 4.2: Summary cards UI
  - [ ] Commit 4.3: Visual indicators and formatting
- [ ] Phase 5: Project detail integration (2 commits)
  - [ ] Commit 5.1: Add component to ProjectDetail
  - [ ] Commit 5.2: Layout and styling adjustments
- [ ] Phase 6: WBE detail integration (2 commits)
  - [ ] Commit 6.1: Add component to WBEDetail
  - [ ] Commit 6.2: Layout and styling adjustments

---

## Code Patterns to Follow

### Backend Patterns
- Use SQLModel `select()` with `func.sum()` for aggregations
- Follow existing router pattern (APIRouter, tags, response models)
- Use dependency injection (`SessionDep`, `CurrentUser`)
- Error handling with `HTTPException`
- Decimal precision for monetary values

### Frontend Patterns
- Use TanStack Query for data fetching
- Use Chakra UI components (Card, Stat, Text, Flex, Grid)
- Format currency: `toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })`
- Format percentage: `toFixed(1)` + "%"
- Loading states with SkeletonText
- Error states with error messages

### Component Structure
```tsx
<BudgetSummary level="project" projectId={projectId} />
// or
<BudgetSummary level="wbe" wbeId={wbeId} />
```

---

## Estimated Timeline

- **Phase 1 (Backend Endpoint):** 4-6 hours
- **Phase 2 (Model Schema):** 1 hour
- **Phase 3 (Client Generation):** 15 minutes
- **Phase 4 (Frontend Component):** 3-4 hours
- **Phase 5 (Project Integration):** 1 hour
- **Phase 6 (WBE Integration):** 1 hour

**Total:** ~10-13 hours (1.5-2 days)

---

## Risk Assessment

**Low Risk:**
- Simple aggregation queries (sum operations)
- Reusable component pattern
- No complex business logic

**Medium Risk:**
- Performance with large datasets (many WBEs/cost elements)
  - Mitigation: Aggregation done server-side, consider caching later
- UI layout on mobile devices
  - Mitigation: Use responsive Chakra UI Grid/Flex components

**Known Dependencies:**
- Requires existing Project, WBE, CostElement models (✅ Complete)
- Requires existing API route patterns (✅ Complete)
- Requires Chakra UI components (✅ Available)

---

## Success Criteria

✅ **Backend:**
- Aggregation endpoint returns correct totals
- Handles edge cases (empty projects/WBEs)
- Proper error handling (404, 403)
- 10+ tests passing

✅ **Frontend:**
- Summary component displays all required metrics
- Visual indicators work correctly
- Responsive design works on all viewports
- Integrated into ProjectDetail and WBEDetail pages
- Updates automatically when data changes

✅ **User Experience:**
- Users can see budget/revenue overview at a glance
- Summary information is clear and easy to understand
- Visual indicators help identify over-allocation issues
- No performance degradation

---

## Notes

- **Reusability:** BudgetSummary component designed to work at both project and WBE levels
- **Future Enhancements:** Could add drill-down links, export functionality, or trend indicators
- **Performance:** Consider caching summary calculations if performance becomes an issue
- **Accessibility:** Ensure color indicators have text labels for color-blind users

---

**Plan Status:** ✅ Ready for Implementation
**Next Action:** Begin Phase 1, Commit 1.1 (failing test first)
