# Plan: Project Hierarchy Tree Component

**Created:** 2026-03-06
**Based on:** [00-analysis.md](./00-analysis.md)
**Approved Option:** Option 1 - Lazy-Loading Tree

---

## Scope & Success Criteria

### Approved Approach Summary

- **Selected Option**: Option 1 - Lazy-Loading Tree
- **Architecture**: Lazy-loading tree component using Ant Design Tree with `loadData` pattern
- **Key Decisions**:
  - Fetch root WBEs on component mount
  - Load child WBEs and Cost Elements when node expands
  - Use existing API hooks (`useWBEs`, `useCostElements`) with TimeMachine context
  - Navigate to detail pages on node click (excluding expand toggle)
  - Display budget allocation alongside entity names

### Success Criteria

**Functional Criteria:**

- [ ] Tree displays all root WBEs with name and budget_allocation on initial render VERIFIED BY: Visual inspection test
- [ ] Expanding a WBE node shows its child WBEs and Cost Elements with budgets VERIFIED BY: Integration test
- [ ] Child WBE nodes are recursively expandable VERIFIED BY: Integration test
- [ ] Clicking on a WBE node navigates to WBE detail page VERIFIED BY: Navigation test
- [ ] Clicking on a Cost Element node navigates to Cost Element detail page VERIFIED BY: Navigation test
- [ ] Tree content respects as_of, branch, and branch mode from TimeMachine context VERIFIED BY: Time travel integration test
- [ ] Empty state displays when project has no WBEs VERIFIED BY: Visual inspection test
- [ ] Loading indicator shows during lazy load operations VERIFIED BY: Visual inspection test

**Technical Criteria:**

- [ ] Performance: Initial render < 500ms for projects with up to 100 root WBEs VERIFIED BY: Performance measurement
- [ ] TypeScript strict mode compliance (zero type errors) VERIFIED BY: `npm run type-check`
- [ ] ESLint clean (zero errors) VERIFIED BY: `npm run lint`
- [ ] Test coverage >= 80% for new code VERIFIED BY: `npm run test:coverage`

**Business Criteria:**

- [ ] Users can navigate the project hierarchy to understand budget breakdown VERIFIED BY: User acceptance test

### Scope Boundaries

**In Scope:**

- Create new `ProjectStructure` component in `frontend/src/pages/projects/`
- Add "Structure" tab to project layout
- Add route for `/projects/:projectId/structure`
- Lazy-loading tree with WBE and Cost Element hierarchy
- Navigation to WBE and Cost Element detail pages
- Integration with TimeMachine context (as_of, branch, mode)
- Empty state handling
- Loading state handling
- Unit tests for component logic
- Integration tests for data fetching
- Navigation tests for click handlers

**Out of Scope:**

- Backend API changes (all required endpoints already exist)
- Editing WBEs or Cost Elements from tree view
- Bulk operations on tree nodes
- Tree filtering/searching
- Exporting tree data
- Permission-based node visibility
- Collapsing/expanding all nodes at once
- Persisting tree expansion state

---

## Work Decomposition

### Task Breakdown

| # | Task | Files | Dependencies | Success Criteria | Complexity |
|---|------|-------|--------------|------------------|------------|
| 1 | Create ProjectStructure component with tree UI | `frontend/src/pages/projects/ProjectStructure.tsx` | None | Component renders without errors, TypeScript compiles, basic tree structure visible | Medium |
| 2 | Implement root WBEs fetching with useWBEs hook | `frontend/src/pages/projects/ProjectStructure.tsx` | Task 1 | Root WBEs load and display with names and budget_allocation, respects TimeMachine context | Medium |
| 3 | Implement lazy loading for child nodes (WBEs + Cost Elements) | `frontend/src/pages/projects/ProjectStructure.tsx` | Task 2 | Expanding WBE node loads children, loading indicator shows, child nodes display correctly | High |
| 4 | Implement navigation handlers for WBE and Cost Element clicks | `frontend/src/pages/projects/ProjectStructure.tsx` | Task 3 | Clicking WBE navigates to WBE detail, clicking CE navigates to CE detail, expand click doesn't navigate | Medium |
| 5 | Add empty state and error handling | `frontend/src/pages/projects/ProjectStructure.tsx` | Task 3 | Empty state shows when no WBEs, error state shows on API failure, loading state shows during fetch | Low |
| 6 | Write unit tests for ProjectStructure component | `frontend/src/pages/projects/__tests__/ProjectStructure.test.tsx` | Task 5 | All tests pass, coverage >= 80% for component logic | Medium |
| 7 | Write integration tests for tree data fetching | `frontend/src/pages/projects/__tests__/ProjectStructure.integration.test.tsx` | Task 6 | Tests verify root WBE fetch, child lazy load, TimeMachine context integration | Medium |
| 8 | Write navigation tests for click handlers | `frontend/src/pages/projects/__tests__/ProjectStructure.navigation.test.tsx` | Task 6 | Tests verify WBE detail navigation, CE detail navigation, expand vs select behavior | Low |
| 9 | Add "Structure" tab to ProjectLayout | `frontend/src/pages/projects/ProjectLayout.tsx` | Task 1 | New tab appears in project navigation, tab label is "Structure", tab links to correct path | Low |
| 10 | Add route for /projects/:projectId/structure | `frontend/src/routes/index.tsx` | Task 9 | Route renders ProjectStructure component, route parameter projectId is passed correctly | Low |
| 11 | Run quality gates (lint, type-check, test coverage) | N/A | Task 10 | `npm run lint` passes, `npm run type-check` passes, coverage >= 80% | Low |

### Test-to-Requirement Traceability

| Acceptance Criterion | Test ID | Test File | Expected Behavior |
|---------------------|---------|-----------|-------------------|
| Tree displays root WBEs with name and budget | T-001 | `ProjectStructure.test.tsx` | Tree renders with root WBE nodes showing `name` and `budget_allocation` |
| Expanding WBE shows children | T-002 | `ProjectStructure.integration.test.tsx` | Clicking expand icon triggers child fetch, children render under parent |
| Child WBEs recursively expandable | T-003 | `ProjectStructure.integration.test.tsx` | Nested WBEs can expand to multiple levels |
| Click WBE navigates to detail | T-004 | `ProjectStructure.navigation.test.tsx` | Click handler calls `navigate` with `/projects/:projectId/wbes/:wbeId` |
| Click CE navigates to detail | T-005 | `ProjectStructure.navigation.test.tsx` | Click handler calls `navigate` with `/cost-elements/:id` |
| Respects TimeMachine context | T-006 | `ProjectStructure.integration.test.tsx` | API calls include `as_of`, `branch`, `mode` from context |
| Empty state for no WBEs | T-007 | `ProjectStructure.test.tsx` | Empty component renders when WBE list is empty |
| Loading indicator on lazy load | T-008 | `ProjectStructure.test.tsx` | Loading spinner appears during child fetch |
| TypeScript strict mode | T-009 | CI Pipeline | `npm run type-check` returns zero errors |
| ESLint clean | T-010 | CI Pipeline | `npm run lint` returns zero errors |
| Coverage >= 80% | T-011 | CI Pipeline | `npm run test:coverage` reports >= 80% for new files |

---

## Test Specification

### Test Hierarchy

```
Unit Tests (frontend/src/pages/projects/__tests__/ProjectStructure.test.tsx)
    - Component renders without crashing
    - Tree structure initializes with root WBEs
    - Empty state displays correctly
    - Loading state displays during fetch
    - Error state displays on API failure
    - Node titles display name and budget

Integration Tests (frontend/src/pages/projects/__tests__/ProjectStructure.integration.test.tsx)
    - Root WBEs fetch from API with TimeMachine params
    - Expanding node loads child WBEs and Cost Elements
    - Multiple levels of nesting work correctly
    - TimeMachine context changes invalidate and refetch data
    - Pagination handling (if WBE count exceeds page size)

Navigation Tests (frontend/src/pages/projects/__tests__/ProjectStructure.navigation.test.tsx)
    - Clicking WBE node (non-expand area) navigates to WBE detail
    - Clicking Cost Element node navigates to Cost Element detail
    - Clicking expand icon does not trigger navigation
    - Navigation uses correct route parameters
```

### Test Cases (first 5)

| Test ID | Test Name | Criterion | Type | Expected Result |
|---------|-----------|-----------|------|-----------------|
| T-001 | `test_project_structure_renders_root_wbes_with_names_and_budget` | FC-1 | Unit | Tree renders DataNode[] with root WBEs, each title contains name and formatted budget |
| T-002 | `test_project_structure_lazy_loads_children_on_expand` | FC-2 | Integration | `loadData` callback fetches child WBEs by `parentWbeId` and Cost Elements by `wbe_id`, returns combined children array |
| T-003 | `test_project_structure_click_wbe_navigates_to_detail` | FC-4, FC-5 | Integration | `onSelect` handler calls `navigate(\`/projects/\${projectId}/wbes/\${wbeId}\`)` when WBE node selected |
| T-004 | `test_project_structure_click_cost_element_navigates_to_detail` | FC-4, FC-5 | Integration | `onSelect` handler calls `navigate(\`/cost-elements/\${costElementId}\`)` when CE node selected |
| T-005 | `test_project_structure_respects_timemachine_context` | FC-6 | Integration | API queries include `asOf`, `branch`, `mode` from `useTimeMachineParams()` |

### Test Infrastructure Needs

- **Fixtures needed**:
  - Mock `useWBEs` hook from `@/features/wbes/api/useWBEs`
  - Mock `useCostElements` hook from `@/features/cost-elements/api/useCostElements`
  - Mock `useParams` from `react-router-dom` for `projectId`
  - Mock `useNavigate` from `react-router-dom`
  - Mock `useTimeMachineParams` for temporal context

- **Mocks/stubs**:
  - TanStack Query for async data fetching
  - Ant Design Tree component interaction

- **Test data**:
  - Sample WBE hierarchy (root -> child -> grandchild)
  - Sample Cost Elements for WBEs
  - Empty WBE list for empty state tests

---

## Risk Assessment

| Risk Type | Description | Probability | Impact | Mitigation |
|-----------|-------------|-------------|--------|------------|
| Technical | Ant Design Tree `loadData` pattern incompatible with TanStack Query async loading | Low | Medium | Use TanStack Query's `isLoading` state to control Tree's `loading` prop; handle query errors gracefully |
| Technical | Distinguishing between expand click and node select click in Tree component | Medium | Low | Use Tree's `onSelect` for navigation clicks, `onExpand` for expand actions; verify event.target doesn't conflict |
| Integration | TimeMachine context changes don't trigger tree refresh | Low | Medium | Ensure query keys include `{ asOf, branch, mode }` from TimeMachine params; verify query invalidation works |
| Integration | Large WBE hierarchies (> 1000 nodes) cause performance issues | Low | Low | Lazy loading inherently limits loaded nodes; if issues arise, add virtualization in future iteration |
| UX | Users confused about clicking to expand vs clicking to navigate | Medium | Low | Add clear visual distinction (expand icon vs clickable title); add tooltip on first visit if needed |

---

## Task Dependency Graph

```yaml
# Task Dependency Graph
tasks:
  - id: FE-001
    name: "Create ProjectStructure component with tree UI"
    agent: pdca-frontend-do-executor
    dependencies: []

  - id: FE-002
    name: "Implement root WBEs fetching with useWBEs hook"
    agent: pdca-frontend-do-executor
    dependencies: [FE-001]

  - id: FE-003
    name: "Implement lazy loading for child nodes (WBEs + Cost Elements)"
    agent: pdca-frontend-do-executor
    dependencies: [FE-002]

  - id: FE-004
    name: "Implement navigation handlers for WBE and Cost Element clicks"
    agent: pdca-frontend-do-executor
    dependencies: [FE-003]

  - id: FE-005
    name: "Add empty state and error handling"
    agent: pdca-frontend-do-executor
    dependencies: [FE-003]

  - id: FE-006
    name: "Write unit tests for ProjectStructure component"
    agent: pdca-frontend-do-executor
    dependencies: [FE-005]

  - id: FE-007
    name: "Write integration tests for tree data fetching"
    agent: pdca-frontend-do-executor
    dependencies: [FE-006]

  - id: FE-008
    name: "Write navigation tests for click handlers"
    agent: pdca-frontend-do-executor
    dependencies: [FE-006]

  - id: FE-009
    name: "Add 'Structure' tab to ProjectLayout"
    agent: pdca-frontend-do-executor
    dependencies: [FE-001]

  - id: FE-010
    name: "Add route for /projects/:projectId/structure"
    agent: pdca-frontend-do-executor
    dependencies: [FE-009]

  - id: FE-011
    name: "Run quality gates (lint, type-check, test coverage)"
    agent: pdca-frontend-do-executor
    dependencies: [FE-010]
```

---

## Documentation References

### Required Reading

- Coding Standards: `/home/nicola/dev/backcast_evs/docs/02-architecture/frontend/coding-standards.md`
- Frontend Contexts: `/home/nicola/dev/backcast_evs/docs/02-architecture/frontend/contexts/03-ui-ux.md`
- Product Scope - Glossary: `/home/nicola/dev/backcast_evs/docs/01-product-scope/glossary.md`

### Code References

- Ant Design Tree pattern: `/home/nicola/dev/backcast_evs/frontend/src/features/change-orders/components/HierarchicalDiffView.tsx`
- WBE API hook: `/home/nicola/dev/backcast_evs/frontend/src/features/wbes/api/useWBEs.ts`
- Cost Element API hook: `/home/nicola/dev/backcast_evs/frontend/src/features/cost-elements/api/useCostElements.ts`
- TimeMachine context: `/home/nicola/dev/backcast_evs/frontend/src/contexts/TimeMachineContext.tsx`
- Project layout: `/home/nicola/dev/backcast_evs/frontend/src/pages/projects/ProjectLayout.tsx`
- Routes configuration: `/home/nicola/dev/backcast_evs/frontend/src/routes/index.tsx`

---

## Prerequisites

### Technical

- [x] Analysis phase approved
- [ ] Node dependencies installed (`cd frontend && npm install`)
- [ ] Development server running (`npm run dev`)
- [ ] PostgreSQL database running (for backend API)

### Documentation

- [x] Analysis phase approved (`00-analysis.md` reviewed)
- [ ] Frontend coding standards reviewed
- [ ] TimeMachine context documentation understood
