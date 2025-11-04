# Implementation Plan: E3-002 Cost Aggregation Logic

**Task:** E3-002 - Cost Aggregation Logic
**Sprint:** Sprint 3 - Cost Registration and Data Entry
**Status:** Planning Complete - Ready for Implementation
**Date:** 2025-11-04

---

## Objective

Roll up individual cost transactions to cost element, WBE, and project levels to calculate Actual Cost (AC) for EVM calculations. Expose aggregated costs in the frontend with computed fields for cost analysis.

---

## Requirements Summary

**From PRD (Section 6.2 & 12.2):**
- Cost registrations update Actual Cost (AC) for the associated cost element and WBE
- AC represents the realized cost incurred for work performed
- AC is calculated from all registered costs including quality event costs
- AC feeds directly into EVM calculations

**From User Decisions:**
- ✅ Cost aggregation exposed in frontend right now (Sprint 3)
- ✅ Expose just total cost with optional filter (is_quality_cost parameter)
- ✅ No date filtering, defer to later
- ✅ Include computed fields (cost_percentage_of_budget)

**From Plan.md (Sprint 3):**
- Implement cost aggregation logic that rolls up individual cost transactions to cost element, WBE, and project levels
- Accumulate actual cost data required for future performance analysis

---

## Implementation Approach

**Strategy:** Incremental Enhancement (Backend-First TDD)
- Add backend aggregation endpoints first (following budget_summary pattern)
- Create reusable frontend summary component
- Integrate into existing CostElement, WBE, and Project detail pages
- Follow TDD with failing tests first

**Architecture Pattern:**
- Backend: Aggregation endpoints that calculate totals from CostRegistration records
- Frontend: Reusable CostSummary component with configurable level (cost-element/WBE/project)
- Visualization: Summary cards showing total cost, computed fields, and cost breakdown
- Integration: Add summary cards above existing tables in detail views

---

## Data Model Analysis

### Fields to Aggregate

**Cost Element Level:**
- Sum of `cost_registration.amount` for cost_element_id
- Optional filter: `is_quality_cost` (true/false/null for all)
- Reference: `cost_element.budget_bac` for computed fields

**WBE Level:**
- Sum of all cost registrations for all cost elements in WBE
- Optional filter: `is_quality_cost` (true/false/null for all)
- Reference: Sum of `cost_element.budget_bac` for computed fields

**Project Level:**
- Sum of all cost registrations for all cost elements in all WBEs in project
- Optional filter: `is_quality_cost` (true/false/null for all)
- Reference: Sum of all `cost_element.budget_bac` for computed fields

### Aggregation Structure

```typescript
interface CostSummary {
  level: "cost-element" | "wbe" | "project"
  total_cost: number              // Sum of cost_registration.amount
  cost_element_id?: string        // For cost-element level
  wbe_id?: string                 // For WBE level
  project_id?: string             // For project level
  budget_bac?: number              // Reference budget for computed fields
  cost_percentage_of_budget?: number  // (total_cost / budget_bac) * 100
  cost_registration_count?: number    // Number of cost registrations aggregated
}
```

### Query Parameters

- `is_quality_cost?: boolean` - Optional filter for quality costs only
  - `true`: Only quality costs (is_quality_cost = true)
  - `false`: Only regular costs (is_quality_cost = false)
  - `null` or omitted: All costs

---

## Phase Breakdown

### Phase 1: Backend Model Schema (TDD - Backend First)

**Objective:** Create response schemas for cost summary data

**Files to Create:**
1. `backend/app/models/cost_summary.py` - Schema definitions

**Commits:**

**Commit 1.1:** Create CostSummaryBase schema
- Fields: `level`, `total_cost`, `cost_element_id?`, `wbe_id?`, `project_id?`, `budget_bac?`
- Computed fields: `cost_percentage_of_budget`, `cost_registration_count`
- Use Decimal for monetary values (DECIMAL(15,2))
- Use Pydantic computed_field for calculated values

**Commit 1.2:** Create CostSummaryPublic schema
- Extends CostSummaryBase
- Add metadata: `calculated_at` timestamp (optional, for future use)

**Estimated Time:** 1 hour
**Test Target:** Schema validation tests

---

### Phase 2: Backend Aggregation Endpoint - Cost Element Level

**Objective:** Create API endpoint that calculates and returns cost summary for a cost element

**Files to Create:**
1. `backend/app/api/routes/cost_summary.py` - New router for cost summary endpoint

**Files to Modify:**
1. `backend/app/api/__init__.py` - Register new router
2. `backend/app/models/__init__.py` - Export new schema

**Test Files:**
1. `backend/tests/api/routes/test_cost_summary.py` - New test file

**Commits (Target: <100 lines, <5 files per commit):**

**Commit 2.1:** Add failing test for cost-element-level cost summary
- Test: `test_get_cost_element_cost_summary()`
- Validates: Returns correct total_cost, handles cost element with no registrations, handles cost element with multiple registrations
- Test cases: All costs, quality costs only, regular costs only

**Commit 2.2:** Implement cost-element-level summary endpoint
- Endpoint: `GET /api/v1/cost-summary/cost-element/{cost_element_id}`
- Query parameter: `is_quality_cost?: bool` (optional filter)
- Function: `get_cost_element_cost_summary()`
- Query: Sum cost_registration.amount where cost_element_id matches, optionally filter by is_quality_cost
- Get cost_element.budget_bac for computed fields
- Response schema: `CostSummaryPublic`
- Handle 404 if cost element not found

**Commit 2.3:** Add edge case tests for cost-element level
- Test: `test_get_cost_element_cost_summary_empty()` (no registrations)
- Test: `test_get_cost_element_cost_summary_quality_only()` (filter quality costs)
- Test: `test_get_cost_element_cost_summary_not_found()` (404)
- Test: `test_get_cost_element_cost_summary_computed_fields()` (percentage calculation)

**Estimated Time:** 2-3 hours
**Test Target:** 5-6 tests passing

---

### Phase 3: Backend Aggregation Endpoint - WBE Level

**Objective:** Create API endpoint that calculates and returns cost summary for a WBE

**Commits:**

**Commit 3.1:** Add failing test for WBE-level cost summary
- Test: `test_get_wbe_cost_summary()`
- Validates: Returns correct total_cost aggregated across all cost elements in WBE
- Test cases: All costs, quality costs only, regular costs only

**Commit 3.2:** Implement WBE-level summary endpoint
- Endpoint: `GET /api/v1/cost-summary/wbe/{wbe_id}`
- Query parameter: `is_quality_cost?: bool` (optional filter)
- Function: `get_wbe_cost_summary()`
- Query: Get all cost elements for WBE, then sum all cost registrations for those cost elements
- Calculate sum of cost_element.budget_bac for computed fields
- Response schema: `CostSummaryPublic`
- Handle 404 if WBE not found

**Commit 3.3:** Add edge case tests for WBE level
- Test: `test_get_wbe_cost_summary_empty()` (no cost elements or registrations)
- Test: `test_get_wbe_cost_summary_multiple_elements()` (aggregation across multiple cost elements)
- Test: `test_get_wbe_cost_summary_not_found()` (404)

**Estimated Time:** 2-3 hours
**Test Target:** 4-5 tests passing

---

### Phase 4: Backend Aggregation Endpoint - Project Level

**Objective:** Create API endpoint that calculates and returns cost summary for a project

**Commits:**

**Commit 4.1:** Add failing test for project-level cost summary
- Test: `test_get_project_cost_summary()`
- Validates: Returns correct total_cost aggregated across all WBEs and cost elements
- Test cases: All costs, quality costs only, regular costs only

**Commit 4.2:** Implement project-level summary endpoint
- Endpoint: `GET /api/v1/cost-summary/project/{project_id}`
- Query parameter: `is_quality_cost?: bool` (optional filter)
- Function: `get_project_cost_summary()`
- Query: Get all WBEs for project → get all cost elements for those WBEs → sum all cost registrations
- Calculate sum of all cost_element.budget_bac for computed fields
- Response schema: `CostSummaryPublic`
- Handle 404 if project not found

**Commit 4.3:** Add edge case tests for project level
- Test: `test_get_project_cost_summary_empty()` (no WBEs, cost elements, or registrations)
- Test: `test_get_project_cost_summary_multiple_wbes()` (aggregation across multiple WBEs)
- Test: `test_get_project_cost_summary_not_found()` (404)

**Estimated Time:** 2-3 hours
**Test Target:** 4-5 tests passing

---

### Phase 5: Frontend Client Generation

**Objective:** Generate TypeScript client with new endpoints

**Files to Modify:**
1. Run `scripts/generate-client.sh` to regenerate OpenAPI client

**Commits:**

**Commit 5.1:** Regenerate frontend client
- Run client generation script
- Verify new `CostSummaryService` and types exported
- Verify query parameter types for `is_quality_cost`

**Estimated Time:** 15 minutes

---

### Phase 6: Frontend Summary Component

**Objective:** Create reusable CostSummary component

**Files to Create:**
1. `frontend/src/components/Projects/CostSummary.tsx` - Summary cards component

**Commits:**

**Commit 6.1:** Create CostSummary component structure
- Component props: `level`, `costElementId?`, `wbeId?`, `projectId?`, `isQualityCost?: boolean`
- Use TanStack Query to fetch summary data
- Display loading state (skeleton)
- Handle error states

**Commit 6.2:** Implement summary cards UI
- Card 1: Total Cost (formatted currency)
- Card 2: Budget BAC (if available)
- Card 3: Cost % of Budget (computed field, formatted percentage)
- Card 4: Number of Cost Registrations
- Use Chakra UI Card/Stat components
- Format currency: `toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })`
- Format percentage: `toFixed(1)` + "%"

**Commit 6.3:** Add visual indicators and styling
- Color coding for cost percentage:
  - Green (<50%): Under budget
  - Yellow (50-80%): On track
  - Orange (80-100%): Approaching budget
  - Red (>100%): Over budget
- Visual indicator (Icon) based on cost status
- Responsive layout for cards (Grid: 1fr on mobile, 2fr on tablet, 4fr on desktop)
- Add filter toggle for quality costs (if needed in UI)

**Estimated Time:** 3-4 hours
**Test Target:** Component renders, displays data correctly, handles loading/error states

---

### Phase 7: Integration into Cost Element Detail Page

**Objective:** Add cost summary to cost element detail view

**Files to Modify:**
1. `frontend/src/routes/_layout/projects.$id.wbes.$wbeId.cost-elements.$costElementId.tsx`

**Commits:**

**Commit 7.1:** Add CostSummary component to CostElementDetail
- Import CostSummary component
- Add above CostRegistrationsTable section (in "cost-registrations" tab)
- Or add as new "summary" tab (user preference)
- Pass `level="cost-element"` and `costElementId`
- Add optional quality cost filter toggle

**Commit 7.2:** Adjust layout and styling
- Ensure responsive design
- Add spacing between summary and table
- Match existing tab layout pattern
- Test on mobile/tablet viewports

**Estimated Time:** 1 hour

---

### Phase 8: Integration into WBE Detail Page

**Objective:** Add cost summary to WBE detail view

**Files to Modify:**
1. `frontend/src/routes/_layout/projects.$id.wbes.$wbeId.tsx`

**Commits:**

**Commit 8.1:** Add CostSummary component to WBEDetail
- Import CostSummary component
- Add to "summary" tab (alongside BudgetSummary)
- Or create separate "cost-summary" tab
- Pass `level="wbe"` and `wbeId`
- Display alongside BudgetSummary (budget vs actual costs)

**Commit 8.2:** Adjust layout and styling
- Ensure responsive design
- Match ProjectDetail layout pattern
- Combine with BudgetSummary if in same tab
- Test on mobile/tablet viewports

**Estimated Time:** 1 hour

---

### Phase 9: Integration into Project Detail Page

**Objective:** Add cost summary to project detail view

**Files to Modify:**
1. `frontend/src/routes/_layout/projects.$id.tsx`

**Commits:**

**Commit 9.1:** Add CostSummary component to ProjectDetail
- Import CostSummary component
- Add to "summary" tab (alongside BudgetSummary)
- Pass `level="project"` and `projectId`
- Display alongside BudgetSummary (budget vs actual costs)

**Commit 9.2:** Adjust layout and styling
- Ensure responsive design
- Match existing summary tab pattern
- Combine with BudgetSummary for comprehensive financial overview
- Test on mobile/tablet viewports

**Estimated Time:** 1 hour

---

## Test Strategy

### Backend Tests

**Unit Tests:**
- ✅ Cost-element-level summary calculation with multiple registrations
- ✅ Cost-element-level summary with no registrations
- ✅ Cost-element-level summary with quality cost filter
- ✅ Cost-element-level summary with regular cost filter
- ✅ Cost-element-level computed fields (cost_percentage_of_budget)
- ✅ WBE-level summary calculation with multiple cost elements
- ✅ WBE-level summary with no cost elements
- ✅ WBE-level summary aggregation accuracy
- ✅ Project-level summary calculation with multiple WBEs
- ✅ Project-level summary with no WBEs
- ✅ Project-level summary aggregation accuracy
- ✅ Edge case: All zero values
- ✅ Edge case: Very large numbers (Decimal precision)
- ✅ Error: Cost element not found (404)
- ✅ Error: WBE not found (404)
- ✅ Error: Project not found (404)
- ✅ Error: Unauthorized access (403)
- ✅ Query parameter validation (is_quality_cost)

**Integration Tests:**
- ✅ Summary updates when cost registrations added
- ✅ Summary updates when cost registrations updated
- ✅ Summary updates when cost registrations deleted
- ✅ Summary updates when cost element budget changes
- ✅ Filter accuracy (quality vs regular costs)

### Frontend Tests (Manual + Visual)

**Component Tests:**
- ✅ Component renders with cost-element data
- ✅ Component renders with WBE data
- ✅ Component renders with project data
- ✅ Loading state displays correctly
- ✅ Error state displays correctly
- ✅ Currency formatting correct
- ✅ Percentage formatting correct
- ✅ Color indicators change based on cost percentage
- ✅ Quality cost filter works correctly
- ✅ Responsive design works on mobile

**Integration Tests:**
- ✅ Summary displays in CostElementDetail page
- ✅ Summary displays in WBEDetail page
- ✅ Summary displays in ProjectDetail page
- ✅ Summary updates when cost registrations change (query invalidation)

---

## Implementation Checklist

### Backend
- [ ] Phase 1: Backend model schema (2 commits)
  - [ ] Commit 1.1: CostSummaryBase schema
  - [ ] Commit 1.2: CostSummaryPublic schema
- [ ] Phase 2: Cost-element-level endpoint (3 commits)
  - [ ] Commit 2.1: Failing test for cost-element summary
  - [ ] Commit 2.2: Implement cost-element endpoint
  - [ ] Commit 2.3: Edge case tests
- [ ] Phase 3: WBE-level endpoint (3 commits)
  - [ ] Commit 3.1: Failing test for WBE summary
  - [ ] Commit 3.2: Implement WBE endpoint
  - [ ] Commit 3.3: Edge case tests
- [ ] Phase 4: Project-level endpoint (3 commits)
  - [ ] Commit 4.1: Failing test for project summary
  - [ ] Commit 4.2: Implement project endpoint
  - [ ] Commit 4.3: Edge case tests
- [ ] Phase 5: Client regeneration (1 commit)
  - [ ] Commit 5.1: Regenerate frontend client

### Frontend
- [ ] Phase 6: Summary component (3 commits)
  - [ ] Commit 6.1: Component structure with query
  - [ ] Commit 6.2: Summary cards UI
  - [ ] Commit 6.3: Visual indicators and formatting
- [ ] Phase 7: Cost-element detail integration (2 commits)
  - [ ] Commit 7.1: Add component to CostElementDetail
  - [ ] Commit 7.2: Layout and styling adjustments
- [ ] Phase 8: WBE detail integration (2 commits)
  - [ ] Commit 8.1: Add component to WBEDetail
  - [ ] Commit 8.2: Layout and styling adjustments
- [ ] Phase 9: Project detail integration (2 commits)
  - [ ] Commit 9.1: Add component to ProjectDetail
  - [ ] Commit 9.2: Layout and styling adjustments

---

## Code Patterns to Follow

### Backend Patterns
- Use SQLModel `select()` with Python `sum()` for aggregations (mirror budget_summary pattern)
- Follow existing router pattern (APIRouter, tags, response models)
- Use dependency injection (`SessionDep`, `CurrentUser`)
- Error handling with `HTTPException` (404, 403)
- Decimal precision for monetary values (DECIMAL(15,2))
- Query parameter: `is_quality_cost: bool | None = Query(default=None)`
- Filter pattern: `if is_quality_cost is not None: statement = statement.where(...)`

### Frontend Patterns
- Use TanStack Query for data fetching
- Use Chakra UI components (Card, Stat, Text, Flex, Grid, Badge)
- Format currency: `toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })`
- Format percentage: `toFixed(1)` + "%"
- Loading states with SkeletonText
- Error states with error messages
- Query key pattern: `["cost-summary", level, id, { isQualityCost }]`

### Component Structure
```tsx
<CostSummary level="cost-element" costElementId={costElementId} />
// or
<CostSummary level="wbe" wbeId={wbeId} />
// or
<CostSummary level="project" projectId={projectId} />
// with optional filter
<CostSummary level="project" projectId={projectId} isQualityCost={true} />
```

---

## Estimated Timeline

- **Phase 1 (Model Schema):** 1 hour
- **Phase 2 (Cost-Element Endpoint):** 2-3 hours
- **Phase 3 (WBE Endpoint):** 2-3 hours
- **Phase 4 (Project Endpoint):** 2-3 hours
- **Phase 5 (Client Generation):** 15 minutes
- **Phase 6 (Frontend Component):** 3-4 hours
- **Phase 7 (Cost-Element Integration):** 1 hour
- **Phase 8 (WBE Integration):** 1 hour
- **Phase 9 (Project Integration):** 1 hour

**Total:** ~13-17 hours (2-2.5 days)

---

## Risk Assessment

**Low Risk:**
- Simple aggregation queries (sum operations, mirroring budget_summary)
- Reusable component pattern (following BudgetSummary pattern)
- No complex business logic
- Established patterns from E2-006

**Medium Risk:**
- Performance with large datasets (many cost registrations)
  - Mitigation: Aggregation done server-side, consider caching later if needed
- UI layout on mobile devices
  - Mitigation: Use responsive Chakra UI Grid/Flex components
- Decimal precision in calculations
  - Mitigation: Use Decimal type throughout, test edge cases

**Known Dependencies:**
- ✅ Requires existing CostRegistration model (E3-001 - Complete)
- ✅ Requires existing Project, WBE, CostElement models (✅ Complete)
- ✅ Requires existing API route patterns (✅ Complete)
- ✅ Requires Chakra UI components (✅ Available)

---

## Success Criteria

✅ **Backend:**
- Aggregation endpoints return correct totals at all three levels
- Handles edge cases (empty cost elements/WBEs/projects)
- Proper error handling (404, 403)
- Query parameter filtering works correctly (is_quality_cost)
- Computed fields calculated accurately
- 15+ tests passing

✅ **Frontend:**
- Summary component displays all required metrics
- Visual indicators work correctly (color coding for cost percentage)
- Responsive design works on all viewports
- Integrated into CostElementDetail, WBEDetail, and ProjectDetail pages
- Updates automatically when cost registrations change
- Quality cost filter works (if implemented in UI)

✅ **User Experience:**
- Users can see cost overview at a glance at all levels
- Cost information is clear and easy to understand
- Visual indicators help identify cost overruns
- No performance degradation
- Consistent with existing BudgetSummary pattern

---

## Notes

- **Reusability:** CostSummary component designed to work at all three levels (cost-element/WBE/project)
- **Future Enhancements:**
  - Date range filtering (deferred as per user decision)
  - Time-phased cost aggregation (costs per month/quarter)
  - Caching for frequently accessed aggregations
  - Export functionality for cost reports
  - Trend indicators (cost trends over time)
- **Performance:** Consider database aggregation (SQL SUM) if Python-side aggregation becomes slow with very large datasets
- **Accessibility:** Ensure color indicators have text labels for color-blind users
- **Integration:** CostSummary can be displayed alongside BudgetSummary in summary tabs for comprehensive financial overview (budget vs actual)

---

**Plan Status:** ✅ Ready for Implementation
**Next Action:** Begin Phase 1, Commit 1.1 (model schema first, then tests)
