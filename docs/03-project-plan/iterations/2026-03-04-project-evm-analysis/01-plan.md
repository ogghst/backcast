# PLAN Phase: Project-Level EVM Analysis Page

**Plan Date:** 2026-03-04
**Based On:** Analysis Document `00-analysis.md`
**Status:** Ready for Implementation

---

## Phase 1: Scope & Success Criteria

### 1.1 Approved Approach Summary

**Selected Option:** Create frontend project-level EVM analysis page following WBE EVM tab pattern

**Architecture:**
- Standalone page component (`ProjectEVMAnalysis.tsx`)
- Reuses existing EVM components (EVMSummaryView, EVMTimeSeriesChart, EVMAnalyzerModal)
- Integrates with existing hooks (useEVMMetrics, useEVMTimeSeries)
- Adds navigation tab and routing

**Key Decisions:**
1. Create separate page component (not embedded in ProjectOverview)
2. Use EntityType.PROJECT for all EVM queries
3. Follow WBEDetailPage EVM tab pattern exactly
4. Maintain consistency with existing navigation structure

### 1.2 Success Criteria (Measurable)

**Functional Criteria:**

- [ ] Users can navigate to "EVM Analysis" tab from project pages
  - **VERIFIED BY:** Unit test (ProjectLayout.test.tsx)

- [ ] EVM metrics display at project level (aggregated from WBEs)
  - **VERIFIED BY:** Unit test verifying EVMSummaryView receives data from useEVMMetrics

- [ ] Historical trends chart works with granularity selection (day/week/month)
  - **VERIFIED BY:** Unit test verifying granularity state management and EVMTimeSeriesChart updates

- [ ] Advanced analysis modal opens with detailed gauges
  - **VERIFIED BY:** Unit test verifying modal state and EVMAnalyzerModal rendering

- [ ] TimeMachine context integration works (branch/time-travel queries)
  - **VERIFIED BY:** Unit test verifying hook calls include TimeMachine parameters

**Technical Criteria:**

- [ ] Performance: Initial render < 500ms
  - **VERIFIED BY:** Manual testing with React DevTools Profiler

- [ ] Type Safety: TypeScript strict mode with zero errors
  - **VERIFIED BY:** `npm run typecheck` (CI pipeline)

- [ ] Code Quality: ESLint clean
  - **VERIFIED BY:** `npm run lint` (CI pipeline)

- [ ] Test Coverage: ≥80% on new code
  - **VERIFIED BY:** `npm test -- --coverage` (CI pipeline)

**TDD Criteria:**

- [ ] All tests written BEFORE implementation code
- [ ] Each test failed first (documented in DO phase log)
- [ ] Test coverage ≥80% on new files
- [ ] Tests follow Arrange-Act-Assert pattern
- [ ] Tests use accessible selectors (getByRole, getByText)

### 1.3 Scope Boundaries

**In Scope:**

- Create ProjectEVMAnalysis.tsx page component
- Create ProjectEVMAnalysis.test.tsx with unit tests
- Modify ProjectLayout.tsx to add EVM Analysis tab
- Modify routes/index.tsx to add route configuration
- Update ProjectLayout.test.tsx to verify new navigation item
- Ensure EntityType.PROJECT is supported by existing EVM hooks

**Out of Scope:**

- Backend API modifications (already supports EntityType.PROJECT)
- Creating new EVM components (reusing existing ones)
- Modifying EVMSummaryView, EVMTimeSeriesChart, or EVMAnalyzerModal
- Integration tests beyond navigation
- E2E tests
- Performance optimization beyond baseline requirements
- Error boundary implementation (using existing patterns)

---

## Phase 2: Work Decomposition

### 2.1 Task Breakdown

| # | Task | Files | Dependencies | Success Criteria | Complexity |
|---|------|-------|--------------|------------------|------------|
| 1 | Write tests for ProjectEVMAnalysis component | `frontend/src/pages/projects/ProjectEVMAnalysis.test.tsx` | None | Tests fail (RED phase) | Medium |
| 2 | Implement ProjectEVMAnalysis component | `frontend/src/pages/projects/ProjectEVMAnalysis.tsx` | Task 1 | Tests pass (GREEN phase) | Low |
| 3 | Write tests for ProjectLayout with EVM tab | `frontend/src/pages/projects/ProjectLayout.test.tsx` (modify) | None | Tests fail (RED phase) | Low |
| 4 | Add EVM Analysis tab to ProjectLayout | `frontend/src/pages/projects/ProjectLayout.tsx` (modify) | Task 3 | Tests pass (GREEN phase) | Low |
| 5 | Add route for ProjectEVMAnalysis | `frontend/src/routes/index.tsx` (modify) | Task 2 | Navigation works | Low |
| 6 | Run quality gates and fix issues | All modified files | Tasks 1-5 | All quality gates pass | Low |
| 7 | Refactor for code quality | All modified files | Task 6 | Code review ready | Low |

**Task Ordering Principles Applied:**

1. Tests defined first (TDD RED phase)
2. Frontend components before routing
3. Implementation follows tests (TDD GREEN phase)
4. Quality gates last (REFACTOR phase)

### 2.2 Test-to-Requirement Traceability

| Acceptance Criterion | Test ID | Test File | Expected Behavior |
|---------------------|---------|-----------|-------------------|
| AC1: Navigation to EVM Analysis tab | T-001 | ProjectLayout.test.tsx | Renders "EVM Analysis" tab |
| AC2: EVM metrics display | T-002 | ProjectEVMAnalysis.test.tsx | EVMSummaryView receives metrics data |
| AC3: Historical trends chart | T-003 | ProjectEVMAnalysis.test.tsx | Chart updates on granularity change |
| AC4: Advanced analysis modal | T-004 | ProjectEVMAnalysis.test.tsx | Modal opens on button click |
| AC5: TimeMachine integration | T-005 | ProjectEVMAnalysis.test.tsx | Hooks called with TimeMachine params |
| AC6: Loading state | T-006 | ProjectEVMAnalysis.test.tsx | Shows loading spinner when loading |
| AC7: Error handling | T-007 | ProjectEVMAnalysis.test.tsx | Handles missing projectId gracefully |

---

## Phase 3: Test Specification

### 3.1 Test Hierarchy

```text
├── Unit Tests (frontend/src/pages/projects/)
│   ├── ProjectEVMAnalysis.test.tsx (new)
│   │   ├── Happy path tests
│   │   ├── Component rendering tests
│   │   ├── State management tests
│   │   └── Hook integration tests
│   └── ProjectLayout.test.tsx (modify)
│       └── Navigation item tests
└── Integration Tests
    └── ProjectNavigation.integration.test.tsx (existing, may need update)
```

### 3.2 Test Cases (First 7)

| Test ID | Test Name | Criterion | Type | Expected Result |
|---------|-----------|-----------|------|-----------------|
| T-001 | `test_project_layout_renders_evm_analysis_tab` | AC1 | Unit | "EVM Analysis" tab visible in navigation |
| T-002 | `test_project_evm_analysis_renders_summary_view` | AC2 | Unit | EVMSummaryView component rendered with metrics |
| T-003 | `test_project_evm_analysis_granularity_selection` | AC3 | Unit | Granularity state changes on selection |
| T-004 | `test_project_evm_analysis_opens_modal` | AC4 | Unit | EVMAnalyzerModal visible after button click |
| T-005 | `test_project_evm_analysis_calls_hooks_with_project_type` | AC5 | Unit | useEVMMetrics called with EntityType.PROJECT |
| T-006 | `test_project_evm_analysis_shows_loading_state` | AC6 | Unit | Loading spinner shown when isLoading=true |
| T-007 | `test_project_evm_analysis_handles_missing_project_id` | AC7 | Unit | Renders nothing or shows error when projectId undefined |

### 3.3 Test Infrastructure Needs

**Fixtures needed:**
- Mock EVM metrics response (can use existing from EVM tests)
- Mock EVM time series response (can use existing from EVM tests)
- Mock project ID from useParams

**Mocks/stubs:**
- `useEVMMetrics` hook - return mock data
- `useEVMTimeSeries` hook - return mock data
- `useParams` from react-router-dom - return mock projectId
- `useTimeMachineParams` - return default values

**Database state:**
- None required (frontend unit tests with mocks)

---

## Phase 4: Implementation Details

### 4.1 Component Structure

**ProjectEVMAnalysis.tsx:**
```typescript
/**
 * Project-level EVM Analysis page component.
 *
 * Context: Displays aggregated EVM metrics for an entire project,
 * including summary cards, historical trends, and advanced analysis.
 * Integrates with TimeMachine for time-travel queries.
 *
 * @module pages/projects/ProjectEVMAnalysis
 */

// Imports:
// - useParams from react-router-dom
// - useState from react
// - Space, Collapse from antd
// - LineChartOutlined from @ant-design/icons
// - useEVMMetrics, useEVMTimeSeries from features/evm/api
// - EVMSummaryView, EVMTimeSeriesChart, EVMAnalyzerModal from features/evm/components
// - EntityType, EVMTimeSeriesGranularity from features/evm/types
// - theme from antd

// Component structure:
// 1. Extract projectId from useParams
// 2. State: granularity (default: WEEK), isEVMModalOpen (default: false)
// 3. Hooks: useEVMMetrics(EntityType.PROJECT, projectId), useEVMTimeSeries(...)
// 4. Render: Space with EVMSummaryView, Collapse with EVMTimeSeriesChart, EVMAnalyzerModal
```

**Pattern to follow:** WBEDetailPage.tsx lines 231-279 (EVM tab content)

### 4.2 File Modifications

**ProjectLayout.tsx modification:**
```typescript
// Add to items array (line 8-11):
const items = [
  { key: "overview", label: "Overview", path: `/projects/${projectId}` },
  { key: "change-orders", label: "Change Orders", path: `/projects/${projectId}/change-orders` },
  { key: "evm-analysis", label: "EVM Analysis", path: `/projects/${projectId}/evm-analysis` },  // NEW
];
```

**routes/index.tsx modification:**
```typescript
// Add import at top:
import { ProjectEVMAnalysis } from "@/pages/projects/ProjectEVMAnalysis";

// Add to children of "/projects/:projectId" route (line 73-82):
{
  path: "/projects/:projectId",
  element: <ProjectLayout />,
  children: [
    { index: true, element: <ProjectOverview /> },
    { path: "change-orders", element: <ProjectChangeOrdersPage /> },
    { path: "evm-analysis", element: <ProjectEVMAnalysis /> },  // NEW
  ],
}
```

---

## Phase 5: Risk Assessment

| Risk Type | Description | Probability | Impact | Mitigation |
|-----------|-------------|-------------|--------|------------|
| Technical | Backend EVM endpoint doesn't support PROJECT type | Low | High | Verify endpoint exists before starting implementation (checked: supported) |
| Technical | Missing test coverage on edge cases | Medium | Medium | Write comprehensive tests first (TDD approach) |
| Integration | TimeMachine context not passed correctly | Low | Medium | Verify hook calls include TimeMachine params in tests |
| UX | Inconsistent styling with WBE EVM tab | Low | Low | Follow WBEDetailPage pattern exactly |
| Performance | Slow initial render with large projects | Low | Medium | TanStack Query caching handles this automatically |

---

## Phase 6: Prerequisites & Dependencies

### Technical Prerequisites

- [x] Backend API supports EntityType.PROJECT in EVM endpoints
- [x] EVM hooks (useEVMMetrics, useEVMTimeSeries) exist and support PROJECT type
- [x] EVM components (EVMSummaryView, EVMTimeSeriesChart, EVMAnalyzerModal) exist
- [x] Frontend dependencies installed (React, Ant Design, TanStack Query)
- [x] Test infrastructure in place (Vitest, Testing Library)

### Documentation Prerequisites

- [x] Analysis phase approved (`00-analysis.md`)
- [x] Frontend coding standards reviewed (`docs/02-architecture/frontend/coding-standards.md`)
- [x] WBEDetailPage EVM tab pattern understood
- [x] EVM types and components documented

### Dependencies

**Internal Dependencies:**
- `@/features/evm/components/EVMSummaryView`
- `@/features/evm/components/EVMTimeSeriesChart`
- `@/features/evm/components/EVMAnalyzerModal`
- `@/features/evm/api/useEVMMetrics`
- `@/features/evm/api/useEVMTimeSeries`
- `@/features/evm/types` (EntityType, EVMTimeSeriesGranularity)

**External Dependencies:**
- react-router-dom (useParams)
- antd (Space, Collapse, theme)
- @ant-design/icons (LineChartOutlined)

---

## Phase 7: Task Dependency Graph

```yaml
tasks:
  - id: FE-001
    name: "Write tests for ProjectEVMAnalysis component"
    agent: pdca-frontend-do-executor
    dependencies: []
    files:
      - frontend/src/pages/projects/ProjectEVMAnalysis.test.tsx
    kind: test
    phase: RED

  - id: FE-002
    name: "Write tests for ProjectLayout EVM tab"
    agent: pdca-frontend-do-executor
    dependencies: []
    files:
      - frontend/src/pages/projects/ProjectLayout.test.tsx
    kind: test
    phase: RED

  - id: FE-003
    name: "Implement ProjectEVMAnalysis component"
    agent: pdca-frontend-do-executor
    dependencies: [FE-001]
    files:
      - frontend/src/pages/projects/ProjectEVMAnalysis.tsx
    phase: GREEN

  - id: FE-004
    name: "Add EVM Analysis tab to ProjectLayout"
    agent: pdca-frontend-do-executor
    dependencies: [FE-002]
    files:
      - frontend/src/pages/projects/ProjectLayout.tsx
    phase: GREEN

  - id: FE-005
    name: "Add route for ProjectEVMAnalysis"
    agent: pdca-frontend-do-executor
    dependencies: [FE-003]
    files:
      - frontend/src/routes/index.tsx
    phase: GREEN

  - id: FE-006
    name: "Run quality gates and refactor"
    agent: pdca-frontend-do-executor
    dependencies: [FE-003, FE-004, FE-005]
    files:
      - All modified files
    phase: REFACTOR
```

**Execution Order:**
1. **Parallel:** FE-001, FE-002 (both are test tasks, can run simultaneously)
2. **Sequential:** FE-003 (depends on FE-001), FE-004 (depends on FE-002), FE-005 (depends on FE-003)
3. **Final:** FE-006 (depends on all implementation tasks)

---

## Phase 8: Quality Gates Checklist

Before advancing to CHECK phase, verify:

### Code Quality
- [ ] `npm run lint` passes with zero errors
- [ ] `npm run typecheck` passes with zero errors
- [ ] No console.log statements in production code
- [ ] All functions have JSDoc comments
- [ ] All imports use `@/` path aliases

### Test Quality
- [ ] All tests pass (`npm test`)
- [ ] Test coverage ≥80% on new files
- [ ] Tests use accessible selectors (getByRole, getByText)
- [ ] Tests follow Arrange-Act-Assert pattern
- [ ] No skipped tests

### Functionality
- [ ] Can navigate to EVM Analysis tab
- [ ] EVM metrics display correctly
- [ ] Historical trends chart renders
- [ ] Granularity selection works
- [ ] Advanced analysis modal opens
- [ ] Loading states display
- [ ] Error states handled

### Documentation
- [ ] Component has JSDoc with context
- [ ] Complex logic has inline comments
- [ ] Test names are descriptive

---

## Output

**Status:** ✅ Complete - Ready for DO Phase

**Next Phase:** DO - Delegate to `pdca-frontend-do-executor` with task dependency graph
