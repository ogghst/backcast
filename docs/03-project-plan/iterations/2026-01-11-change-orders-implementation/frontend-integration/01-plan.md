# Frontend Integration: E06-U03 & E06-U07 - PLAN

**Date Created:** 2026-01-13
**Epic:** E006 (Branching & Change Order Management)
**Iteration:** Frontend Integration - Branch-Aware UI
**Status:** Planning Phase
**Related Docs:** [Phase 2](../phase2/) | [Functional Requirements](../../../../../01-product-scope/functional-requirements.md)

---

## Executive Summary

This iteration implements the frontend components for E06-U03 (Modify Entities in Branch) and E06-U07 (Merged View) to complete the branch management functionality. The backend is complete (Phase 2), and this phase focuses on making branch capabilities visible and usable to end users.

**Key Deliverables:**
1. Branch-aware CRUD for Projects, CostElements (E06-U03)
2. Merged view component integration (E06-U07)
3. Branch selector in header for switching contexts
4. View mode selector (merged/isolated)

**Note:** The frontend already has a solid foundation with `ViewModeSelector`, `BranchSelector`, `useTimeMachineStore`, and the WBE implementation pattern. This iteration will apply these patterns consistently across all branch-enabled entities.

---

## Phase 1: Context Analysis

### Existing Frontend Architecture

**Time Machine Infrastructure:**
- `src/stores/useTimeMachineStore.ts` - Zustand store for branch/mode/as_of state
- `src/contexts/TimeMachineContext.tsx` - React context provider
- `src/components/time-machine/ViewModeSelector.tsx` - Merged/Isolated mode toggle
- `src/components/time-machine/BranchSelector.tsx` - Branch dropdown with status badges

**Reference Implementation (WBE):**
- `src/features/wbes/api/useWBEs.ts` - Shows pattern for branch/mode/as_of query params
- Manual `__request` calls to include query parameters
- Mutations inject control_date and branch from time machine context

**API Client:**
- `src/api/client.ts` - Global Axios instance with JWT interceptor
- Environment-based base URL configuration

### Documentation Review

**Functional Requirements (FR-8.4.12, FR-14.1.2):**
- **FR-8.4.12**: Merged view service displaying entities from main + branch
- **FR-14.1.2**: Branch selection control in application header
- **FR-14.1.1**: Time machine date selector in header

**Branching Requirements:**
- Entities filter by current branch context automatically
- Branch status indicators (Active, Locked, Archived)
- Locked branches prevent modification operations
- Merged view overlays branch changes on main

### Codebase Analysis

**Existing Patterns:**
```typescript
// WBE List Query Pattern (src/features/wbes/api/useWBEs.ts)
const response = await __request(OpenAPI, {
  method: "GET",
  url: "/api/v1/wbes",
  query: {
    project_id: params?.projectId,
    branch: params?.branch || "main",
    mode: mode,  // "merged" | "isolated"
    as_of: asOf || undefined,
  },
});
```

**What's Working:**
- Time machine store with persistence
- Branch selector with status badges
- View mode selector (merged/isolated)
- WBE implementation as reference pattern

**What's Missing:**
- CostElements list query doesn't use branch/mode/as_of params
- Projects list query doesn't use branch/mode/as_of params
- No frontend tests for branch-aware functionality

---

## Phase 2: Problem Definition

### Problem Statement

**E06-U03 (Modify Entities in Branch):**
The backend supports branch, mode, and as_of query parameters for filtering entities by branch context. However, the frontend API hooks for Projects and CostElements don't utilize these parameters, preventing users from viewing and editing entities in change order branches.

**E06-U07 (Merged View):**
The ViewModeSelector component exists and integrates with the time machine store, but the backend's merged view capability (combining main + branch entities) is not fully utilized across all branch-enabled entity types.

### Why Important Now

1. **Phase 2 Backend Complete**: BranchService, ChangeOrderService, and workflow integration are tested and ready
2. **User Value**: Users cannot see or use branch management features without frontend integration
3. **Iteration Completion**: E06-U03 and E06-U07 are marked as deferred in Phase 2 CHECK phase

### Success Criteria (Measurable)

**E06-U03:**
- [ ] Projects list query accepts branch parameter
- [ ] CostElements list query accepts branch parameter
- [ ] Both queries accept mode parameter (merged/isolated)
- [ ] Both queries accept as_of parameter for time-travel
- [ ] Frontend components respect locked branch state (prevent edits)

**E06-U07:**
- [ ] ViewModeSelector visible in header
- [ ] BranchSelector visible in header
- [ ] Merged view combines main + branch entities
- [ ] Isolated view shows only current branch entities
- [ ] View mode switch triggers re-query with correct mode parameter

**Quality:**
- [ ] Zero TypeScript errors (strict mode)
- [ ] Zero ESLint warnings
- [ ] All existing tests still pass

### Scope Definition

**In Scope:**
1. Update `src/features/projects/api/useProjects.ts` list query with branch/mode/as_of
2. Update `src/features/cost-elements/api/useCostElements.ts` list query with branch/mode/as_of
3. Verify BranchSelector and ViewModeSelector are properly integrated in AppLayout
4. Add locked branch checks to mutation hooks (prevent edits on locked branches)
5. Manual testing of branch switching and view mode toggling

**Out of Scope:**
- Frontend unit tests (deferred due to complexity of mocking React Query)
- E2E tests with Playwright (deferred to separate testing iteration)
- Change Orders CRUD UI (separate feature)
- Branch lock enforcement at API layer (E06-U06 extension)
- Time machine date picker UI enhancements

---

## Phase 3: Implementation Options

| Aspect | Option A: Minimal Update | Option B: Consistent Pattern | Option C: Full Testing |
|--------|-------------------------|----------------------------|----------------------|
| **Approach** | Update only list queries | Apply WBE pattern consistently + add locked checks | Option B + add frontend tests |
| **Files Modified** | 2 (useProjects.ts, useCostElements.ts) | 4 (+ add locked checks to mutations) | 8 (+ test files) |
| **Branch Selector** | Already exists, verify integration | Same | Same |
| **View Mode Selector** | Already exists, verify integration | Same | Same |
| **Locked Branch Handling** | None | Add checks to prevent mutations | Add checks + tests |
| **Testing** | Manual only | Manual only | Manual + unit tests |
| **Risk Level** | Low | Low | Medium (test complexity) |
| **Complexity** | Simple | Simple | Moderate |
| **Pros** | Quickest completion | Consistent with WBE pattern | Full test coverage |
| **Cons** | No locked branch protection | Additional time for mutation checks | High test maintenance burden |
| **Time Estimate** | 2-3 hours | 3-4 hours | 8-12 hours |

### Recommendation: **Option B - Consistent Pattern**

**Justification:**
1. **Aligns with WBE Pattern**: The WBE implementation is the established reference for branch-aware CRUD
2. **Locked Branch Protection**: Preventing edits on locked branches is a critical UX requirement (FR-8.3)
3. **Low Risk**: Straightforward application of existing patterns
4. **Frontend Tests Deferred**: Unit testing React Query hooks is complex and provides marginal value for this simple parameter passing

**Decision:** Proceed with Option B unless user requests Option C.

---

## Phase 4: Technical Design

### TDD Test Blueprint

**Note:** Frontend unit tests for React Query hooks are deferred due to complexity. Testing will be manual verification of:

1. **Branch Switching**: Select different branches, verify data updates
2. **View Mode Toggle**: Switch merged/isolated, verify entity display changes
3. **Locked Branch**: Try editing on locked branch, verify operation is prevented

### Implementation Strategy

**High-Level Approach:**
1. Apply WBE pattern to Projects and CostElements list queries
2. Add locked branch checks to create/update/delete mutations
3. Verify BranchSelector and ViewModeSelector in AppLayout
4. Manual testing of branch switching workflows

**Key Technologies:**
- React Query (TanStack Query) for server state
- Zustand for time machine state
- Ant Design for UI components
- TypeScript strict mode

**Integration Points:**
- `useTimeMachineParams()` hook from time machine context
- `__request()` manual calls for query parameter support
- `useProjectBranches()` for fetching available branches

**Component Breakdown:**

```
src/features/projects/api/
├── useProjects.ts (MODIFY)
│   ├── useProjects() - Add branch/mode/as_of to list query
│   └── useCreateProject() - Add locked branch check
│   └── useUpdateProject() - Add locked branch check
│   └── useDeleteProject() - Add locked branch check

src/features/cost-elements/api/
├── useCostElements.ts (MODIFY)
│   ├── useCostElements() - Add branch/mode/as_of to list query
│   └── useCreateCostElement() - Add locked branch check
│   └── useUpdateCostElement() - Add locked branch check
│   └── useDeleteCostElement() - Add locked branch check

src/layouts/
├── AppLayout.tsx (VERIFY)
│   ├── BranchSelector integration
│   └── ViewModeSelector integration

src/stores/
├── useTimeMachineStore.ts (NO CHANGES)
│   └── Already has branch/mode/as_of state

src/contexts/
├── TimeMachineContext.tsx (NO CHANGES)
│   └── Already provides useTimeMachineParams()
```

---

## Phase 5: Risk Assessment

| Risk Type | Description | Probability | Impact | Mitigation Strategy |
|-----------|-------------|-------------|--------|---------------------|
| **Technical** | OpenAPI client doesn't support branch/mode/as_of params | Low | Low | Use `__request()` manual call pattern from WBE |
| **Integration** | Breaking change to existing API hooks | Low | Low | Parameters are optional, backward compatible |
| **UX** | Users confused by branch switching | Medium | Medium | Clear branch labels and status badges (already exists) |
| **Schedule** | Time estimate underestimates complexity | Low | Low | Simple pattern application, low risk |

---

## Phase 6: Effort Estimation

### Time Breakdown

- **Development:** 3-4 hours
  - Update Projects API hooks: 1 hour
  - Update CostElements API hooks: 1 hour
  - Add locked branch checks: 1 hour
  - Verify and test integration: 1 hour
- **Testing:** 1 hour (manual testing)
- **Documentation:** 1 hour (CHECK phase doc)
- **Total Estimated Effort:** **5-6 hours** (~1 day)

### Prerequisites

1. **Backend:** Phase 2 must be deployed and accessible
2. **Database:** Branches table must exist with main branches created
3. **API:** `/api/v1/projects` and `/api/v1/cost-elements` endpoints must support branch/mode/as_of query parameters

### Dependencies

- Backend branch filtering implementation (✅ Complete - Phase 2)
- OpenAPI specification regeneration (if needed)
- Time machine store and context (✅ Already exists)

---

## Phase 7: Implementation Checklist

### Step 1: Update Projects API Hook
- [ ] Modify `useProjects()` to use `__request()` with branch/mode/as_of
- [ ] Add `useTimeMachineParams()` hook call
- [ ] Add locked branch check to mutations
- [ ] Test with different branches

### Step 2: Update CostElements API Hook
- [ ] Modify `useCostElements()` to use `__request()` with branch/mode/as_of
- [ ] Add `useTimeMachineParams()` hook call
- [ ] Add locked branch check to mutations
- [ ] Test with different branches

### Step 3: Verify Header Components
- [ ] Confirm BranchSelector in AppLayout
- [ ] Confirm ViewModeSelector in AppLayout
- [ ] Test branch switching updates data
- [ ] Test view mode toggle updates data

### Step 4: Manual Testing
- [ ] Create a change order (creates branch)
- [ ] Switch to branch in BranchSelector
- [ ] Verify entities show for selected branch
- [ ] Toggle view mode merged/isolated
- [ ] Verify merged view combines entities
- [ ] Try editing on locked branch (should fail)

### Step 5: Documentation
- [ ] Create CHECK phase document
- [ ] Update iteration status

---

## Output Files

**Created:**
- `docs/03-project-plan/iterations/2026-01-11-change-orders-implementation/frontend-integration/01-plan.md` (this file)

**To Be Created:**
- `frontend-integration/02-do.md` - DO phase documentation
- `frontend-integration/03-check.md` - CHECK phase quality assessment

---

## References

- [Phase 2 Backend Implementation](../phase2/)
- [Functional Requirements - Branching](../../../../../01-product-scope/functional-requirements.md#84-branching-and-versioning-system)
- [Frontend Structure Analysis](../../../../../02-architecture/frontend-structure.md)
- [WBE Reference Implementation](../../../../../../../frontend/src/features/wbes/api/useWBEs.ts)
