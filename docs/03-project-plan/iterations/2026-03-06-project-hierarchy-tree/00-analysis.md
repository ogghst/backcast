# Analysis: Project Hierarchy Tree Component

**Date:** 2026-03-06
**Status:** ANALYSIS COMPLETE
**Iteration:** Project Structure Hierarchy Visualization

---

## 1. Requirements Summary

### User Request

Create a new project structure component that shows the project WBE and Cost Element hierarchy using an expandable tree (Ant Design Tree). The component shall be visible as a tab in the main project page, and shall show by default all root WBEs with names and budget. Opening a WBE node will show its child WBEs and Cost Elements with budget. Child WBEs can be expandable to show their WBEs and Cost Elements. Clicking on a WBE or Cost Element will open its detail page. The tree content must be consistent with `as_of`, `branch`, and `branch mode` in session status.

### Functional Requirements

1. **New Component**: Project structure tree component using Ant Design Tree
2. **Placement**: Visible as a tab in main project page (alongside Overview, Change Orders, EVM Analysis)
3. **Default View**: Show all root WBEs with names and `budget_allocation`
4. **Expandable Nodes**:
   - Opening a WBE node shows its child WBEs and Cost Elements with budgets
   - Child WBEs are recursively expandable
5. **Navigation**: Clicking on WBE or Cost Element opens their detail page
6. **Context Consistency**: Tree content must respect `as_of`, `branch`, and `branch mode` from session status

### Non-Functional Requirements

- **Performance**: Lazy loading for scalability (don't load entire hierarchy upfront)
- **Maintainability**: Follow existing frontend patterns and conventions
- **Type Safety**: TypeScript strict mode compliance

### Constraints

- Use existing Ant Design Tree component (already in project dependencies)
- Must integrate with existing TimeMachine context
- Must use existing API hooks (`useWBEs`, `useCostElements`)

---

## 2. Context Discovery

### Product Scope

- **Epic**: Project Structure Visualization
- **User Story**: As a project manager, I want to see the hierarchical structure of my project's WBEs and Cost Elements so that I can understand the budget breakdown and navigate to specific items for detailed analysis.

### Architecture Context

**Bounded Contexts Involved:**
- WBE Management (`frontend/src/features/wbes/`)
- Cost Element Management (`frontend/src/features/cost-elements/`)
- Project Management (`frontend/src/pages/projects/`)

**Existing Patterns to Follow:**
- Ant Design Tree component usage (see `HierarchicalDiffView.tsx`)
- TimeMachine context integration (hooks already use `useTimeMachineParams()`)
- React Router navigation pattern
- TanStack Query for data fetching

**Architectural Constraints:**
- Must use existing API layer (no new backend endpoints required)
- Must respect EVCS temporal context (as_of, branch, mode)

### Codebase Analysis

**Frontend - Existing Related Components:**

| File | Purpose | Relevance |
|------|---------|-----------|
| `frontend/src/features/change-orders/components/HierarchicalDiffView.tsx` | Shows Ant Design Tree usage pattern | High - reference for Tree implementation |
| `frontend/src/pages/projects/ProjectLayout.tsx` | Main project page with tab navigation | High - needs modification for new tab |
| `frontend/src/routes/index.tsx` | Route configuration | High - needs new route |
| `frontend/src/contexts/TimeMachineContext.tsx` | Provides temporal context | High - already used by WBE/CE hooks |
| `frontend/src/features/wbes/api/useWBEs.ts` | WBE API hook | High - supports `parentWbeId` for hierarchy |
| `frontend/src/features/cost-elements/api/useCostElements.ts` | Cost Element API hook | High - filters by `wbe_id` |

**API Hooks Available:**

- `useWBEs({ projectId, parentWbeId })` - Already integrated with TimeMachineContext
- `useCostElements({ wbe_id })` - Already integrated with TimeMachineContext

**Type Definitions:**
- `WBERead`: Has `name`, `code`, `budget_allocation`, `parent_wbe_id`, `wbe_id`
- `CostElementRead`: Has `name`, `code`, `budget_amount`, `cost_element_id`, `wbe_id`

**Detail Pages (Navigation Targets):**
- WBE Detail: `/projects/:projectId/wbes/:wbeId` → `WBEDetailPage`
- Cost Element Detail: `/cost-elements/:id` → `CostElementDetailPage`

---

## 3. Solution Options

### Option 1: Lazy-Loading Tree (Recommended)

**Architecture & Design:**
- Fetch root WBEs on component mount
- Load child WBEs and Cost Elements when node expands
- Use Ant Design Tree's `loadData` prop for lazy loading
- Tree nodes maintain their own expanded state

**UX Design:**
- Initial load shows only root WBEs (fast initial render)
- User clicks expand icon to load and show children
- Expandable nodes show a loading indicator during data fetch
- Click anywhere else on the node to navigate to detail page

**Implementation:**
- Use `useWBEs({ projectId, parentWbeId: "null" })` for roots
- Implement `loadChildren` function that:
  - Fetches child WBEs by `parentWbeId`
  - Fetches Cost Elements by `wbe_id`
  - Combines and transforms to tree nodes
- Handle node click with `onSelect` (distinguish expand vs select)

**Trade-offs:**

| Aspect | Assessment |
|--------|------------|
| Pros | - Fast initial load<br>- Scales to deep hierarchies<br>- Only fetches needed data<br>- Follows Ant Design patterns |
| Cons | - More complex state management<br>- Each expand requires API call |
| Complexity | Medium |
| Maintainability | Good (established pattern) |
| Performance | Excellent for large/deep hierarchies |

---

### Option 2: Full Hierarchy Fetch

**Architecture & Design:**
- Fetch entire WBE hierarchy on component mount
- Transform flat WBE list to tree structure in memory
- Fetch all Cost Elements up front

**UX Design:**
- All data available immediately
- Instant expand (no loading indicator)
- Slower initial render for large projects

**Implementation:**
- Fetch all WBEs for project (without parent filter)
- Build tree structure by grouping children under parents
- Fetch Cost Elements for each WBE (or use existing nested data)

**Trade-offs:**

| Aspect | Assessment |
|--------|------------|
| Pros | - Simpler implementation<br>- Instant expand/collapse<br>- All data available at once |
| Cons | - Slow initial load for large projects<br>- Fetches unnecessary data<br>- Doesn't scale well |
| Complexity | Low |
| Maintainability | Good (simpler code) |
| Performance | Poor for large hierarchies |

---

### Option 3: Hybrid with Prefetch

**Architecture & Design:**
- Fetch root WBEs + 1 level of children on mount
- Lazy load deeper levels
- Prefetch data on hover for instant expand

**UX Design:**
- Near-instant expand for first level
- Loading indicator only for deeper levels
- Optimized perceived performance

**Implementation:**
- Fetch roots and their immediate children
- Use `onMouseEnter` to prefetch next level
- Cache loaded children

**Trade-offs:**

| Aspect | Assessment |
|--------|------------|
| Pros | - Good balance of speed and complexity<br>- Optimized perceived performance |
| Cons | - Most complex implementation<br>- May fetch unnecessary data on hover |
| Complexity | High |
| Maintainability | Fair (more complex) |
| Performance | Good for most use cases |

---

## 4. Comparison Summary

| Criteria | Option 1: Lazy-Loading | Option 2: Full Fetch | Option 3: Hybrid |
|----------|----------------------|---------------------|------------------|
| Development Effort | Medium | Low | High |
| UX Quality | Good (fast initial) | Fair (slow initial) | Excellent |
| Flexibility | High | Low | Medium |
| Scalability | Excellent | Poor | Good |
| Best For | Large/deep hierarchies | Small, shallow hierarchies | Medium hierarchies with UX focus |

---

## 5. Recommendation

**I recommend Option 1 (Lazy-Loading Tree) because:**

1. **Scalability**: As projects grow, lazy loading ensures performance doesn't degrade
2. **Follows Best Practices**: Ant Design Tree's `loadData` pattern is designed for this use case
3. **Existing Infrastructure**: Backend API already supports hierarchical queries via `parent_wbe_id`
4. **User Experience**: Fast initial load, acceptable loading indicators on expand
5. **Code Quality**: Reference implementation exists in `HierarchicalDiffView.tsx`

**Alternative consideration:** Choose Option 2 (Full Fetch) only if analysis shows most projects have very small hierarchies (< 20 total nodes) and you prioritize simpler implementation over scalability.

---

## 6. Decision

**Approved:** Option 1 - Lazy-Loading Tree

The lazy-loading approach provides the best balance of performance, scalability, and user experience for the project's expected growth.

---

## 7. Next Steps

1. **PLAN Phase**: Create detailed implementation plan with file-by-file breakdown
2. **DO Phase**: Implement following RED-GREEN-REFACTOR TDD methodology
3. **CHECK Phase**: Verify all tests pass, run quality checks
4. **ACT Phase**: Update documentation, create sprint in project plan

---

## 8. References

- [Architecture: Frontend Contexts](../../02-architecture/frontend/contexts/03-ui-ux.md)
- [Architecture: Frontend Coding Standards](../../02-architecture/frontend/coding-standards.md)
- [Existing: HierarchicalDiffView.tsx](../../../frontend/src/features/change-orders/components/HierarchicalDiffView.tsx)
- [API: useWBEs Hook](../../../frontend/src/features/wbes/api/useWBEs.ts)
- [API: useCostElements Hook](../../../frontend/src/features/cost-elements/api/useCostElements.ts)
