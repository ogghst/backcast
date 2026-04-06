# Analysis: Phase 1 -- Frontend Widget Infrastructure

**Created:** 2026-04-05
**Request:** Build the foundation layer for a composable widget dashboard system: frontend types, registry, WidgetShell component, context bus, Zustand composition store, DashboardGrid (react-grid-layout), and WidgetPalette.

---

## Clarified Requirements

This phase creates the frontend-only infrastructure that must be in place before any backend dashboard API or individual widget implementations. The deliverable is a working, empty grid with edit-mode toggle, a widget palette for adding placeholders, and the type system / context bus that future widgets will consume.

### Functional Requirements

- Define a complete TypeScript type system for widget definitions, instances, dashboards, and the context bus
- Implement a typed Widget Registry (`Map<WidgetTypeId, WidgetDefinition>`) with register/get/query functions
- Build a WidgetShell component extending the existing ExplorerCard pattern: header with drag handle, collapse toggle, refresh, settings, fullscreen expand; body with ErrorBoundary, loading/error/empty overlays
- Create a Dashboard Context Bus (React context) providing projectId, wbeId, costElementId, branch, viewDate -- integrating with existing TimeMachineContext for branch/viewDate
- Create a Zustand store (with immer) for composition state: isEditing, activeDashboard, isDirty, selectedWidgetId, plus actions for add/remove/update widgets
- Build a DashboardGrid wrapper around react-grid-layout ResponsiveGridLayout with 12-column grid, responsive breakpoints, and debounced layout changes
- Build a WidgetPalette (Ant Design Drawer) showing widgets grouped by category, with click-to-add behavior
- Install react-grid-layout and its type definitions

### Non-Functional Requirements

- All styling via `theme.useToken()` -- no hardcoded colors or spacing
- TypeScript strict mode compliance -- no `any`
- ESLint clean
- 80%+ test coverage on all new modules
- Components must be testable in isolation (no embedded routing or global state coupling)

### Constraints

- This is frontend-only. No backend API changes, no database migrations, no new endpoints
- Must not break or modify existing pages/routes
- Must coexist with the existing `features/dashboard/` directory (home page dashboard)
- Must integrate with, not replace, TimeMachineContext
- react-grid-layout is a new dependency; it must be evaluated for React 18 compatibility and bundle size impact

---

## Context Discovery

### Product Scope

- No formal user story or epic exists in the product backlog or epics document for widget composition dashboards
- The three research documents under `docs/03-project-plan/iterations/2026-04-06-widget-system/` (claude.md, perplexity.md, gemini.md) provide extensive widget taxonomies and architecture recommendations, but none have been approved as requirements
- The functional requirements document (`docs/01-product-scope/functional-requirements.md`) describes fixed page-per-entity navigation; the widget system represents a paradigm shift from that model
- EVM requirements are well-defined and the EVM data layer (hooks, types, API) already exists at `features/evm/`

### Architecture Context

- **Bounded contexts involved:** None directly -- this is a pure frontend infrastructure layer. However, future widgets will consume data from EVM, Projects, WBEs, Cost Elements, Change Orders, and AI bounded contexts
- **Frontend coding standards** (`docs/02-architecture/frontend/coding-standards.md`) mandate: TypeScript strict, TanStack Query for server state, Zustand for global UI state, Ant Design components, `theme.useToken()` for all styling, JSDoc on all public functions
- **Existing patterns to follow:**
  - `useAppStore.ts`: Zustand + immer middleware, minimal interface
  - `ExplorerCard.tsx`: Token-based Card with `variant="borderless"`, header/body styling split
  - `TimeMachineContext.tsx`: React context + custom hook pattern, integration with query invalidation
  - Feature-based directory structure under `src/features/`
  - `queryKeys.ts` factory for all TanStack Query keys

- **Architectural constraints:**
  - Never duplicate server state in Zustand (coding standards rule)
  - Never use `useEffect` for data fetching -- use TanStack Query hooks
  - All components must use `theme.useToken()` for styling
  - `react-error-boundary` is already installed at v6.0.1

### Codebase Analysis

**Frontend:**

- **ExplorerCard** (`components/explorer/ExplorerCard.tsx`): 58-line component using Card `variant="borderless"` with token-based styling. Well-structured. WidgetShell should extend this pattern but needs additional chrome (drag handle, collapse, settings gear, fullscreen button).

- **useAppStore** (`stores/useAppStore.ts`): Minimal zustand+immer store (20 lines) with single boolean state. The composition store will be significantly more complex but should follow the same `create()(immer((set) => ...)))` pattern.

- **TimeMachineContext** (`contexts/TimeMachineContext.tsx`): Provides `asOf`, `branch`, `mode`, `isHistorical`, `invalidateQueries()`. The dashboard context bus should consume this context (not duplicate it) and add entity-level context (projectId, wbeId, costElementId).

- **Dashboard feature collision** (`features/dashboard/`): This directory already exists as the home page dashboard (welcome message, project spotlight, recent activity grid, `DashboardData` types, `useDashboardData` hook). The new widget system cannot use `features/dashboard/types.ts` without conflict. A separate feature directory is required.

- **EVM data hooks** (`features/evm/api/useEVMMetrics.ts`): Already consume `TimeMachineContext` params. Future EVM widgets will work automatically if the context bus correctly delegates branch/viewDate to TimeMachineContext.

- **ProjectExplorer** (`pages/projects/ProjectExplorer.tsx`): Uses `allotment` for split-pane layout (tree + detail cards). The explorer pattern (tree selecting an entity, detail cards rendering) is effectively a manual widget composition. The widget system should eventually subsume this pattern.

- **Dependencies already installed:** react-error-boundary, zustand (v5), immer, zod, @dnd-kit/core, @dnd-kit/sortable, allotment, echarts, echarts-for-react

- **Dependencies NOT installed:** react-grid-layout, @types/react-grid-layout

---

## Solution Options

### Option 1: New `features/widgets/` Feature Directory (Recommended)

Create a dedicated `frontend/src/features/widgets/` feature directory containing all widget infrastructure. This avoids collision with the existing `features/dashboard/` (home page) and establishes a clear naming boundary.

**Architecture & Design:**

- Directory: `src/features/widgets/`
  - `types.ts` -- WidgetTypeId, WidgetCategory, WidgetSizeConstraints, WidgetDefinition, WidgetInstance, Dashboard, DashboardContextValue, WidgetComponentProps
  - `registry.ts` -- typed Map with `registerWidget`, `getWidgetDefinition`, `getWidgetsByCategory`, `getAllWidgetDefinitions`
  - `components/WidgetShell.tsx` -- extends ExplorerCard pattern, adds header chrome and ErrorBoundary
  - `components/DashboardGrid.tsx` -- wraps react-grid-layout ResponsiveGridLayout
  - `components/WidgetPalette.tsx` -- Ant Design Drawer for widget selection
  - `context/DashboardContextBus.tsx` -- React context composing TimeMachineContext + entity selection
  - `context/useDashboardContext.ts` -- hook
- Store: `src/stores/useDashboardCompositionStore.ts` -- follows useAppStore pattern (zustand + immer)
- Install react-grid-layout + @types/react-grid-layout as new dependencies

**UX Design:**

- DashboardGrid renders an empty 12-column grid with a floating "Edit Dashboard" button
- Clicking "Edit Dashboard" toggles `isEditing` in the composition store, which shows the WidgetPalette drawer and drag handles
- WidgetPalette lists placeholder widget types grouped by category, clicking one adds it with default size
- WidgetShell wraps each placed widget with consistent chrome
- All interactions are frontend-only; layout is stored in Zustand (lost on refresh, since no backend API yet)

**Implementation:**

- Create `features/widgets/types.ts` with all type definitions
- Create `features/widgets/registry.ts` with Map-based registry and helper functions
- Create `WidgetShell` extending ExplorerCard (import and wrap, or fork the pattern)
- Create `DashboardContextBus` that reads from TimeMachineContext and adds entity-level state (projectId, wbeId, costElementId) via internal useState or a small Zustand slice
- Create `useDashboardCompositionStore` with isEditing, activeDashboard (layout array), isDirty, selectedWidgetId
- Create `DashboardGrid` wrapping react-grid-layout's ResponsiveGridLayout
- Create `WidgetPalette` as Ant Design Drawer with category-grouped list
- Add tests for registry, store, context bus, and WidgetShell rendering

**Trade-offs:**

| Aspect          | Assessment                                                                              |
| --------------- | --------------------------------------------------------------------------------------- |
| Pros            | Clean separation from existing dashboard; clear naming; follows feature-based pattern   |
| Cons            | New directory alongside dashboard may cause initial confusion about which is "the dashboard" |
| Complexity      | Low-Medium -- well-scoped, no backend dependencies, leverages existing patterns         |
| Maintainability | Good -- isolated feature, no coupling to existing pages                                 |
| Performance     | Good -- react-grid-layout is lightweight; Zustand store is minimal overhead             |

---

### Option 2: Extend Existing `features/dashboard/` with Sub-Directories

Extend the existing `features/dashboard/` directory by adding a `widgets/` sub-directory for the widget infrastructure. The existing home-page dashboard components remain in `components/`, and the widget system lives alongside them.

**Architecture & Design:**

- Directory: `src/features/dashboard/`
  - `types.ts` -- EXISTING (home page types: DashboardData, ActivityItem, etc.), keep as-is or rename to `homeTypes.ts`
  - `widgetTypes.ts` -- new widget type definitions
  - `registry.ts` -- widget registry
  - `components/` -- existing home page components remain (DashboardHeader, ProjectSpotlight, ActivityGrid, etc.)
  - `widgets/` -- new sub-directory for WidgetShell, DashboardGrid, WidgetPalette
  - `context/DashboardContextBus.tsx`
- Store: `src/stores/useDashboardCompositionStore.ts`

**UX Design:**

- Same UX as Option 1. The difference is purely organizational.

**Implementation:**

- Rename or re-export existing `types.ts` to avoid collision with widget types
- Add `widgetTypes.ts` alongside existing types
- Create widget infrastructure within `features/dashboard/widgets/`
- Risk of the `types.ts` file becoming a merge conflict point as both features evolve

**Trade-offs:**

| Aspect          | Assessment                                                                    |
| --------------- | ----------------------------------------------------------------------------- |
| Pros            | Keeps all "dashboard" code in one feature; fewer top-level feature directories |
| Cons            | Two unrelated concepts (home page vs widget composition) cohabitate; type collision risk; violates single-responsibility principle for the feature directory |
| Complexity      | Medium -- requires careful renaming and re-export management                   |
| Maintainability | Fair -- the directory serves two masters; future developers will need to understand the split |
| Performance     | Same as Option 1                                                              |

---

### Option 3: Use @dnd-kit Instead of react-grid-layout

Leverage the already-installed `@dnd-kit/core` + `@dnd-kit/sortable` instead of introducing react-grid-layout. Build a custom grid layout engine on top of CSS Grid + dnd-kit for drag-and-drop.

**Architecture & Design:**

- Same feature directory structure as Option 1
- Replace DashboardGrid implementation: CSS Grid for layout, dnd-kit for drag, manual resize handles
- No new npm dependencies
- Must implement: grid snapping, resize constraints, responsive breakpoints, layout serialization

**UX Design:**

- Same conceptual UX, but the grid behavior will differ from react-grid-layout's battle-tested implementation
- Resize behavior must be built from scratch
- Collision detection and auto-packing must be implemented manually

**Implementation:**

- All deliverables from Option 1, plus:
- Custom grid engine with snap-to-grid behavior
- Custom resize handles and constraint enforcement
- Custom collision detection / auto-packing algorithm
- Significant additional testing for grid edge cases

**Trade-offs:**

| Aspect          | Assessment                                                                    |
| --------------- | ----------------------------------------------------------------------------- |
| Pros            | No new dependency; leverages already-installed dnd-kit; potentially smaller bundle |
| Cons            | Massive implementation scope increase; react-grid-layout solves grid layout, resize, responsive breakpoints, and serialization out of the box; building this from scratch is weeks of work and a permanent maintenance burden |
| Complexity      | High -- custom grid engine is a project unto itself                            |
| Maintainability | Poor -- the custom grid engine becomes an internal library that must be maintained and debugged |
| Performance     | Uncertain -- custom implementation may have edge cases react-grid-layout has already solved |

---

## Comparison Summary

| Criteria           | Option 1: `features/widgets/`    | Option 2: Extend `features/dashboard/` | Option 3: dnd-kit Custom Grid |
| ------------------ | -------------------------------- | -------------------------------------- | ----------------------------- |
| Development Effort | 3-4 days                         | 3-4 days + renaming risk               | 7-10 days                     |
| UX Quality         | Good (react-grid-layout proven)  | Good (same)                            | Uncertain (custom engine)     |
| Flexibility        | Good (isolated, extensible)      | Fair (mixed concerns)                  | Good (full control)           |
| Best For           | Clean separation, new feature    | Keeping "dashboard" unified            | Avoiding new dependencies     |
| Risk Level         | Low                              | Medium (type collision, confusion)     | High (custom grid engine)     |

---

## Recommendation

**I recommend Option 1** because it provides clean separation between the existing home page dashboard and the new widget composition system. The `features/widgets/` directory clearly communicates that this is a distinct subsystem. It avoids the type collision risk in the existing `features/dashboard/types.ts`, follows the project's feature-based directory convention, and introduces no organizational debt.

Option 2 is viable but mixes two unrelated concerns (home page activity feed vs composable widget grid) into one feature directory, which will confuse future contributors. Option 3 is not viable for Phase 1 due to the prohibitive scope of building a custom grid engine when react-grid-layout exists and is well-maintained.

**Key adjustments to the original request that I recommend:**

### 1. Directory: Use `features/widgets/` Instead of `features/dashboard/`

The existing `features/dashboard/` directory serves a different purpose (home page with recent activity, project spotlight). The widget system is a distinct subsystem. Using `features/widgets/` avoids type collisions and naming confusion.

### 2. DashboardContextBus: Consume TimeMachineContext, Do Not Duplicate It

The request says "integrates with existing TimeMachineContext for branch/viewDate." The implementation should call `useTimeMachine()` inside the DashboardContextBus provider to obtain branch and viewDate, then compose those values with the entity-level context (projectId, wbeId, costElementId). This avoids duplicating time machine state and ensures widgets automatically inherit time-travel behavior.

### 3. WidgetDefinition: Keep Simple for Phase 1, Document Anticipated Evolution

The current type design puts the React component reference directly in `WidgetDefinition<TConfig>`. This works for Phase 1 where widgets are placeholders. The Perplexity research suggested a richer pattern with `useData` hooks (`WidgetDefinition<TConfig, TQuery, TData>`). For Phase 1, keep the simpler form. Document the anticipated evolution in JSDoc so later phases can extend the type without breaking changes.

### 4. react-grid-layout React 18 Compatibility

react-grid-layout has known compatibility warnings with React 18 strict mode (double-mount effects). Verify during implementation that StrictMode does not cause issues. The standard workaround (suppressing `useLayoutEffect` warnings or using a wrapper component) is well-documented. This is a known, low-risk issue.

### 5. Layout Persistence Scope: Zustand-Only for Phase 1

Phase 1 stores layout only in Zustand (in-memory). Document explicitly that layouts are lost on page refresh. This is acceptable for infrastructure validation but must be flagged as a known limitation. Phase 2 (Backend Dashboard Layout API) will add persistence.

---

## Decision Questions

1. **Directory naming**: Do you agree with `features/widgets/` instead of `features/dashboard/` to avoid collision with the existing home page dashboard? Or do you prefer a different name (e.g., `features/widget-system/`, `features/dashboards/` plural)?

2. **react-grid-layout vs dnd-kit**: Do you accept the recommendation to use react-grid-layout as a new dependency, given that dnd-kit is already installed but would require building a custom grid engine from scratch?

3. **Scope boundary for Phase 1**: The request specifies 8 deliverables. Should any be deferred to a later phase? Specifically, WidgetPalette (the drawer with categorized widget list) could be simplified to a basic "Add Widget" dropdown in Phase 1, with the full categorized drawer coming in Phase 3 (Dashboard Composition UX).

4. **Default dashboard route**: Should Phase 1 include a new route (e.g., `/projects/:projectId/widgets`) to host the DashboardGrid, or should it only create the components without a hosting page? Adding a route would make the infrastructure immediately visible and testable but touches the router configuration.

---

## References

- [Frontend Coding Standards](../../02-architecture/frontend/coding-standards.md)
- [ExplorerCard component](../../../frontend/src/components/explorer/ExplorerCard.tsx)
- [useAppStore pattern](../../../frontend/src/stores/useAppStore.ts)
- [TimeMachineContext](../../../frontend/src/contexts/TimeMachineContext.tsx)
- [Existing dashboard feature](../../../frontend/src/features/dashboard/types.ts)
- [Theme configuration](../../../frontend/src/config/theme.ts)
- [EVM data hooks](../../../frontend/src/features/evm/api/useEVMMetrics.ts)
- [ProjectExplorer page](../../../frontend/src/pages/projects/ProjectExplorer.tsx)
- [Widget research: Claude analysis](./claude.md)
- [Widget research: Perplexity analysis](./perplexity.md)
- [Widget research: Gemini analysis](./gemini.md)
