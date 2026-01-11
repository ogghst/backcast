# PLAN Phase: Time Machine Component

**Created:** 2026-01-09  
**Status:** 📋 Planning  
**Iteration:** 2026-01-09-time-machine-component  
**Related Analysis:** [00-ANALYSIS.md](./00-ANALYSIS.md)

---

## Phase 1: Context Analysis

### Documentation Review

| Document         | Key Findings                                                              |
| ---------------- | ------------------------------------------------------------------------- |
| Product Vision   | "Ability to time travel project at a specific date" - core feature        |
| ADR-005          | Bitemporal versioning with `valid_time` ranges, `get_as_of` method exists |
| Coding Standards | TanStack Query for server state, Zustand for client, TypeScript strict    |
| Sprint Backlog   | Current iteration complete, this is the next major feature                |

### Codebase Analysis

**Existing Patterns Identified:**

- `TemporalService.get_as_of()` - Backend time-travel query ready
- `useUserPreferencesStore.ts` - Zustand + localStorage pattern
- `AppLayout.tsx` - Header integration point
- `createResourceHooks` pattern for TanStack Query

**Integration Points:**

- `AppLayout.tsx` header section
- All entity list/detail hooks (need `as_of` parameter)
- Backend route handlers (need `as_of` query parameter)

---

## Phase 2: Problem Definition

### 1. Problem Statement

**What:** Users cannot visualize or navigate to historical states of their projects.

**Why now:** Time travel is a core product differentiator explicitly called out in the product vision. The backend infrastructure (bitemporal versioning) is complete, but no UI exists to leverage it.

**If not addressed:** The EVCS versioning capabilities remain unused, reducing the product's value proposition.

**Business value:** Enables audit compliance, change order analysis, and historical reporting.

### 2. Success Criteria (Measurable)

**Functional Criteria:**

- [ ] Time Machine button visible in header when project is selected
- [ ] Click expands timeline view
- [ ] Slider allows selection of any date within project range
- [ ] Branch selector shows available branches
- [ ] "Now" button resets to current time
- [ ] Selected time persists in localStorage per project
- [ ] All data queries respect selected time via `as_of` parameter
- [ ] Branch creation/merge markers visible on timeline

**Technical Criteria:**

- [ ] TypeScript strict mode compliance (zero `any`)
- [ ] Backend endpoints accept `as_of` query parameter
- [ ] Query invalidation triggers on time/branch change
- [ ] Component renders in <100ms

**Business Criteria:**

- [ ] Users can view project state at any past date
- [ ] Users can switch between branches to compare change orders

### 3. Scope Definition

**In Scope:**

- Time Machine compact header component
- Time Machine expanded timeline panel
- Zustand store with localStorage persistence
- `as_of` parameter on Project, WBE, Cost Element endpoints
- Branch selector dropdown
- Query invalidation on time/branch change
- Branch creation/merge markers

**Out of Scope:**

- WBE/Cost Element level timeline events (project-level only)
- Rich timeline visualization library (using Ant Design Slider)
- Backend branch metadata API (using existing history endpoint)
- Mobile-specific UI optimization
- Keyboard shortcuts for time navigation

---

## Phase 3: Implementation Options

_Note: Options were evaluated in Analysis phase. Option 3 was approved._

| Aspect            | Option 3: Hybrid (Approved)                             |
| ----------------- | ------------------------------------------------------- |
| **Approach**      | Compact header + expandable detail panel                |
| **Patterns**      | Zustand store, Context API for as_of propagation        |
| **Pros**          | Progressive UX, no external libs, existing patterns     |
| **Cons**          | Limited visualization vs dedicated library              |
| **Test Strategy** | Unit tests for store, integration for API, E2E for flow |
| **Risk Level**    | Low                                                     |
| **Complexity**    | Medium                                                  |

### Recommendation: ✅ Approved

Option 3 selected for:

- Alignment with existing codebase conventions (Zustand, Ant Design)
- No new dependencies
- Reasonable ~12h effort
- Extensible architecture for future enhancements

---

## Phase 4: Technical Design

### TDD Test Blueprint

```
├── Unit Tests (frontend/src/components/time-machine/__tests__/)
│   ├── useTimeMachineStore.test.ts
│   │   ├── should initialize with null selectedTime (now)
│   │   ├── should persist settings to localStorage
│   │   ├── should restore settings from localStorage
│   │   ├── should update selectedTime for project
│   │   └── should reset to now
│   ├── TimeMachineCompact.test.tsx
│   │   ├── should not render when no project selected
│   │   ├── should display current date when selectedTime is null
│   │   ├── should display selected date when set
│   │   └── should toggle expanded state on click
│   └── BranchSelector.test.tsx
│       ├── should show main branch by default
│       └── should call onChange when branch selected
│
├── Integration Tests (backend/tests/unit/api/)
│   ├── test_projects_as_of.py
│   │   ├── should return current version when as_of not provided
│   │   ├── should return historical version when as_of provided
│   │   └── should return 404 when no version exists at as_of
│   └── test_wbes_as_of.py
│       └── (same pattern as projects)
│
└── E2E Tests (frontend/tests/e2e/)
    └── time_machine.spec.ts
        ├── should open time machine panel
        ├── should select date and see historical data
        ├── should switch branches
        └── should persist selection on page reload
```

### First 5 Test Cases (Simplest → Complex)

1. **Unit: Store initializes correctly**

   ```typescript
   test("should initialize with null selectedTime", () => {
     const { result } = renderHook(() => useTimeMachineStore());
     expect(result.current.selectedTime).toBeNull();
     expect(result.current.selectedBranch).toBe("main");
   });
   ```

2. **Unit: Store persists to localStorage**

   ```typescript
   test("should persist settings to localStorage", () => {
     const { result } = renderHook(() => useTimeMachineStore());
     act(() => result.current.selectTime(new Date("2026-01-15"), "proj-1"));
     expect(localStorage.getItem("time-machine-settings")).toContain(
       "2026-01-15"
     );
   });
   ```

3. **Unit: Compact component renders date**

   ```typescript
   test("should display selected date", () => {
     mockUseTimeMachineStore.mockReturnValue({
       selectedTime: "2026-01-15T00:00:00Z",
     });
     render(<TimeMachineCompact projectId="proj-1" />);
     expect(screen.getByText(/Jan 15, 2026/)).toBeInTheDocument();
   });
   ```

4. **Integration: Backend as_of parameter**

   ```python
   async def test_get_project_with_as_of(client, project_with_history):
       """Should return historical version when as_of provided."""
       response = await client.get(
           f"/api/v1/projects/{project_id}?as_of=2026-01-01T00:00:00Z"
       )
       assert response.status_code == 200
       assert response.json()["name"] == "Old Name"  # Historical value
   ```

5. **E2E: Full time machine flow**
   ```typescript
   test("should select date and see historical data", async ({ page }) => {
     await page.goto("/projects/proj-1");
     await page.getByRole("button", { name: /time machine/i }).click();
     await page.getByRole("slider").fill("2026-01-01");
     await expect(page.getByText("Old Project Name")).toBeVisible();
   });
   ```

### Implementation Strategy

**High-Level Approach:**

1. **Backend First:** Add `as_of` query parameter to existing endpoints
2. **Store:** Create Zustand store with localStorage middleware
3. **Context:** Create React Context for global as_of access
4. **Components:** Build compact → expanded → slider → branch selector
5. **Integration:** Wire hooks to use as_of from context
6. **Testing:** Unit → Integration → E2E

**Key Technologies/Patterns:**

- Zustand with `persist` middleware for localStorage
- React Context for as_of propagation to deep components
- TanStack Query `invalidateQueries` for cache busting
- Ant Design Slider with custom marks for timeline
- Ant Design Select for branch dropdown

**Component Breakdown:**

| Component             | Responsibility                | Dependencies                  |
| --------------------- | ----------------------------- | ----------------------------- |
| `useTimeMachineStore` | State management, persistence | Zustand, localStorage         |
| `TimeMachineContext`  | Provide as_of/branch to tree  | React Context                 |
| `TimeMachineCompact`  | Header button/display         | Store, Ant Design             |
| `TimeMachineExpanded` | Timeline panel                | Store, Slider, BranchSelector |
| `TimelineSlider`      | Date range slider with marks  | Ant Design Slider             |
| `BranchSelector`      | Branch dropdown               | Ant Design Select             |
| `QuickJumpButtons`    | 1D, 1W, 1M presets            | Store                         |

---

## Phase 5: Risk Assessment

| Risk Type   | Description                                   | Probability | Impact | Mitigation Strategy                                                   |
| ----------- | --------------------------------------------- | ----------- | ------ | --------------------------------------------------------------------- |
| Technical   | `as_of` queries slow for large histories      | Low         | Medium | Add index on `valid_time`, test with realistic data                   |
| Technical   | Branch list not available from current API    | Medium      | Low    | Extract from history endpoint initially, add dedicated endpoint later |
| Integration | Breaking existing hooks with new parameter    | Medium      | High   | Add as_of as optional parameter, default to current behavior          |
| UX          | Timeline slider too imprecise for exact times | Medium      | Low    | Add date picker for precise input alongside slider                    |
| Schedule    | Underestimating E2E test complexity           | Medium      | Medium | Allocate buffer time, start E2E tests early                           |

---

## Phase 6: Effort Estimation

### Time Breakdown

| Task                                               | Estimated Time |
| -------------------------------------------------- | -------------- |
| **Backend: as_of parameter**                       | 2h             |
| - Add parameter to project/wbe/cost-element routes | 1h             |
| - Add integration tests                            | 1h             |
| **Frontend: Store & Context**                      | 2h             |
| - Zustand store with persistence                   | 1h             |
| - React Context for as_of                          | 0.5h           |
| - Unit tests                                       | 0.5h           |
| **Frontend: Components**                           | 4h             |
| - TimeMachineCompact                               | 1h             |
| - TimeMachineExpanded                              | 1.5h           |
| - TimelineSlider with markers                      | 1h             |
| - BranchSelector                                   | 0.5h           |
| **Frontend: Integration**                          | 2h             |
| - Wire hooks to use as_of                          | 1h             |
| - Query invalidation logic                         | 0.5h           |
| - AppLayout integration                            | 0.5h           |
| **Testing**                                        | 3h             |
| - Unit tests (store, components)                   | 1h             |
| - E2E test for full flow                           | 2h             |
| **Documentation**                                  | 1h             |
| - Update coding standards if needed                | 0.5h           |
| - Component documentation                          | 0.5h           |

**Total Estimated Effort:** 14 hours (~2 working days)

### Prerequisites

- [x] Analysis approved with user decisions
- [ ] Backend dev server running
- [ ] Frontend dev server running
- [ ] E2E test infrastructure working

### Deliverables Checklist

| #   | Deliverable                                | Type                 |
| --- | ------------------------------------------ | -------------------- |
| 1   | `as_of` parameter on `/projects/{id}`      | Backend              |
| 2   | `as_of` parameter on `/wbes/{id}`          | Backend              |
| 3   | `as_of` parameter on `/cost-elements/{id}` | Backend              |
| 4   | `useTimeMachineStore.ts`                   | Frontend Store       |
| 5   | `TimeMachineContext.tsx`                   | Frontend Context     |
| 6   | `TimeMachineCompact.tsx`                   | Frontend Component   |
| 7   | `TimeMachineExpanded.tsx`                  | Frontend Component   |
| 8   | `TimelineSlider.tsx`                       | Frontend Component   |
| 9   | `BranchSelector.tsx`                       | Frontend Component   |
| 10  | `QuickJumpButtons.tsx`                     | Frontend Component   |
| 11  | AppLayout integration                      | Frontend Integration |
| 12  | Unit tests                                 | Tests                |
| 13  | E2E test                                   | Tests                |
| 14  | 02-DO.md                                   | Documentation        |

---

## Task Breakdown for DO Phase

### Task 1: Backend - Add as_of Parameter (2h)

**Files to modify:**

- `backend/app/api/routes/projects.py`
- `backend/app/api/routes/wbes.py`
- `backend/app/api/routes/cost_elements.py`
- `backend/tests/unit/api/test_projects_as_of.py` (new)

**Changes:**

```python
# Add to route handlers
as_of: datetime | None = Query(
    None,
    description="Time travel: get entity state as of this timestamp"
)

# Modify service call
if as_of:
    entity = await service.get_as_of(entity_id, as_of)
else:
    entity = await service.get_by_root_id(entity_id)
```

### Task 2: Frontend - Zustand Store (1h)

**Files to create:**

- `frontend/src/stores/useTimeMachineStore.ts`
- `frontend/src/stores/__tests__/useTimeMachineStore.test.ts`

**Key implementation:**

```typescript
export const useTimeMachineStore = create<TimeMachineState>()(
  persist(
    immer((set, get) => ({
      isExpanded: false,
      selectedTime: null,
      selectedBranch: "main",
      projectSettings: {},
      // ... actions
    })),
    { name: "time-machine-settings" }
  )
);
```

### Task 3: Frontend - React Context (0.5h)

**Files to create:**

- `frontend/src/contexts/TimeMachineContext.tsx`

**Key implementation:**

```typescript
export const TimeMachineProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const { selectedTime, selectedBranch } = useTimeMachineStore();

  const asOfParam = useMemo(
    () => (selectedTime ? new Date(selectedTime).toISOString() : undefined),
    [selectedTime]
  );

  return (
    <TimeMachineContext.Provider
      value={{ asOf: asOfParam, branch: selectedBranch }}
    >
      {children}
    </TimeMachineContext.Provider>
  );
};
```

### Task 4: Frontend - Components (4h)

**Files to create:**

- `frontend/src/components/time-machine/TimeMachineCompact.tsx`
- `frontend/src/components/time-machine/TimeMachineExpanded.tsx`
- `frontend/src/components/time-machine/TimelineSlider.tsx`
- `frontend/src/components/time-machine/BranchSelector.tsx`
- `frontend/src/components/time-machine/QuickJumpButtons.tsx`
- `frontend/src/components/time-machine/types.ts`
- `frontend/src/components/time-machine/index.ts`

### Task 5: Frontend - Hook Integration (1h)

**Files to modify:**

- `frontend/src/api/services/projects.ts`
- `frontend/src/hooks/useCrud.ts` (add asOf support)

**Pattern:**

```typescript
// In data fetching hooks
const { asOf, branch } = useTimeMachineContext();

const { data } = useQuery({
  queryKey: ["projects", projectId, { asOf, branch }],
  queryFn: () => ProjectsService.getProject(projectId, { asOf, branch }),
});
```

### Task 6: Integration & Testing (3h)

**Files to modify:**

- `frontend/src/layouts/AppLayout.tsx` - Add TimeMachine to header
- `frontend/src/main.tsx` - Add TimeMachineProvider

**Files to create:**

- `frontend/tests/e2e/time_machine.spec.ts`

---

## Approval

- [ ] Plan reviewed and approved
- [ ] Effort estimation accepted
- [ ] Ready to proceed to DO phase

**Approver:** ******\_\_\_******  
**Date:** ******\_\_\_******

---

## Related Documentation

- [Analysis Document](./00-ANALYSIS.md)
- [ADR-005: Bitemporal Versioning](../../02-architecture/decisions/ADR-005-bitemporal-versioning.md)
- [Coding Standards](../../02-architecture/coding-standards.md)
