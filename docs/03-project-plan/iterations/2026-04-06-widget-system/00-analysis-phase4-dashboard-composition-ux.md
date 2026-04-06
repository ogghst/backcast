# Analysis: Phase 4 -- Dashboard Composition UX

**Created:** 2026-04-07
**Request:** Implement the user-facing project dashboard page and composition experience, including ProjectDashboard page, DashboardToolbar, WidgetConfigDrawer, route integration, and view/edit mode transitions. Depends on Phases 1-3 (widget infrastructure, backend API, widget definitions).

---

## Clarified Requirements

### Functional Requirements

1. **ProjectDashboard Page** -- A new route page that composes DashboardToolbar, DashboardGrid, and WidgetPalette (conditional on edit mode). Loads the dashboard layout for a given project via a `useDashboardLayout(projectId)` hook, falling back to a default template when no user dashboard exists. Obtains `projectId` from `useParams()`.

2. **DashboardToolbar** -- Displays: View/Edit mode toggle ("Customize" / "Done"), editable dashboard name (inline), template selector dropdown, a save button with dirty-state indicator, and a "Reset to Default" action with confirmation popover.

3. **WidgetConfigDrawer** -- An Ant Design Drawer for editing a selected widget's configuration. Opens on settings gear click or widget selection in edit mode. Form generated from the widget's Zod schema (or a custom form per widget type). Apply/Cancel actions.

4. **Route Integration** -- New route `/projects/:projectId/dashboard` added as a child of the existing `ProjectLayout`. A "Dashboard" tab added to `ProjectLayout`'s `PageNavigation` items. Existing routes remain unchanged.

5. **View Mode (default)** -- Dashboard loads with saved widgets. Widgets are interactive (tooltips, sorting, drill-down). No editing UI visible.

6. **Edit Mode** -- Triggered by "Customize". Grid overlay (subtle dotted guide), WidgetPalette drawer slides in from right, drag handles appear on all widgets. Click to select opens WidgetConfigDrawer. Add widget from palette places at grid bottom with default size. Drag to reorder, resize handles on corners. "Done" saves and returns to view mode. Unsaved changes trigger confirmation dialog on navigation.

### Non-Functional Requirements

- **Performance:** Dashboard grid must render smoothly with up to ~20 widgets without lag.
- **State isolation:** A broken widget must not crash the entire dashboard.
- **Persistence:** Dashboard layouts saved per user per project. Autosave or explicit save.
- **Responsiveness:** 12-column grid on desktop. Graceful degradation on smaller screens.

### Constraints

- **Hard dependency on Phases 1-3:** This phase requires the WidgetShell, WidgetRegistry, react-grid-layout integration (Phase 1), the backend dashboard layout API endpoints (Phase 2), and at least a baseline set of widget definitions (Phase 3) to be complete before meaningful development can begin.
- **Existing navigation pattern:** Must integrate with `ProjectLayout` + `PageNavigation` component pattern. No custom navigation injection.
- **State management convention:** Server state via TanStack Query, UI state via Zustand, forms via Ant Design Form. No deviations.
- **No `react-grid-layout` in `package.json`:** The project currently uses `@dnd-kit` for drag-and-drop, not `react-grid-layout`. The grid engine decision from Phase 1 must be resolved first.

---

## Context Discovery

### Product Scope

- **Vision** (`docs/01-product-scope/vision.md`): Target users include Project Managers (daily), Department Managers, Project Controllers (read-only), and Executives (summary dashboards). The dashboard composition UX primarily serves Project Managers and Executives.
- **Functional Requirements** (`docs/01-product-scope/functional-requirements.md`): The system must support hierarchical tracking (Projects -> WBEs -> Cost Elements), EVM compliance, and change order isolation. The dashboard must reflect these domain concepts accurately.
- No explicit user stories exist for "customizable project dashboard" in the functional requirements document. This is a new capability being introduced through the widget system initiative.

### Architecture Context

- **Bounded Contexts:** The dashboard is a cross-cutting UI concern. It aggregates data from the Projects, WBEs, Cost Elements, EVM, Change Orders, and Schedule bounded contexts. It does not introduce a new bounded context itself -- it is a presentation-layer composition.
- **Frontend Architecture** (`docs/02-architecture/frontend/coding-standards.md`):
  - Server state: TanStack Query with centralized `queryKeys` factory.
  - Global UI state: Zustand (persist middleware for localStorage).
  - Forms: Ant Design Form.
  - Rule: Never duplicate server state in Zustand.
  - All public functions/components must have JSDoc.
- **Existing Grid/DnD Dependencies:** The project already has `@dnd-kit/core`, `@dnd-kit/sortable`, and `@dnd-kit/utilities` installed. It does NOT have `react-grid-layout`. This is a critical decision point for Phase 1 that directly impacts this phase.

### Codebase Analysis

**Frontend:**

- **Routes** (`frontend/src/routes/index.tsx`): Uses `createBrowserRouter`. Project pages are children of `/projects/:projectId` -> `ProjectLayout`. Currently 8 child routes: index (Overview), structure, explorer, schedule, change-orders, members, evm-analysis, chat. Adding a `dashboard` child route follows the established pattern exactly.

- **ProjectLayout** (`frontend/src/pages/projects/ProjectLayout.tsx`): Renders `PageNavigation` with a static array of `{ key, label, path }` items, followed by `<Outlet />`. Adding a Dashboard entry to this array is a one-line addition. The "Dashboard" label is already used in `HeaderNavigation` for the Home page ("/"), so care must be taken to avoid user confusion. Consider "Project Dashboard" or "Overview Dashboard" as the tab label.

- **HeaderNavigation** (`frontend/src/components/navigation/HeaderNavigation.tsx`): Top-level navigation (Home / Projects / AI Chat). This is NOT the same as project-level `PageNavigation`. The feature request mentions modifying HeaderNavigation, but the actual integration point is `ProjectLayout`'s `PageNavigation`. No change to `HeaderNavigation` is needed.

- **Existing Dashboard Feature** (`frontend/src/features/dashboard/`): A "Home Dashboard" exists with `DashboardHeader`, `ProjectSpotlight`, `ActivityGrid`, `ActivitySection` components, and `useDashboardData` hook. This is the **global** home page dashboard (recent activity, last-edited project). It is NOT the same as the per-project composable dashboard proposed here. These two features must coexist without confusion. The existing `useDashboardData` hook fetches from `/api/v1/dashboard/recent-activity`. The new `useDashboardLayout` hook will fetch from a different endpoint.

- **Query Keys** (`frontend/src/api/queryKeys.ts`): A `dashboard` section exists with `recentActivity` key. New dashboard layout keys will need to be added (e.g., `dashboardLayout`, `dashboardTemplates`). Must not conflict with existing keys.

- **ProjectExplorer** (`frontend/src/pages/projects/ProjectExplorer.tsx`): Uses `Allotment` (split-pane) for a tree + detail view. Uses `useParams()` for `projectId`. Uses `theme.useToken()` for styling. These are the patterns to follow.

- **TimeMachine Integration**: The `useTimeMachineStore` provides per-project `branch`, `asOf`, and `viewMode` state. The project dashboard must respect these context parameters -- widgets should re-render when the user switches branches or travels in time. This is a significant integration concern not explicitly addressed in the feature request.

- **Zustand Pattern**: `useTimeMachineStore` uses `immer` + `persist` middleware. The dashboard edit state (edit mode, selected widget, dirty flag) should follow this pattern if persisted to localStorage, or use a simpler in-memory store if transient.

**Backend:**

- No backend changes are in scope for Phase 4 (API comes from Phase 2). However, the frontend must be designed to consume the API contract defined in Phase 2.

**Widget System Research** (`docs/03-project-plan/iterations/2026-04-06-widget-system/`):

- Three research documents (claude.md, perplexity.md, gemini.md) provide comprehensive widget system design guidance.
- Key insight from research: The grid engine should be `react-grid-layout` for desktop/tablet composition, not `@dnd-kit` (which is for sortable lists, not grid layouts with resize).
- Recommended 12-column grid with breakpoints at 1280/960/640px.
- Recommended widget taxonomy by job (Summary, Trend, Diagnostic, Breakdown, Forecast, Action, Narrative, Utility).
- Composition UX should follow Jira's add-gadget/edit-save model.

---

## Solution Options

### Option 1: Minimal Viable Dashboard (Single-Page Composition)

**Architecture & Design:**

A single `ProjectDashboard.tsx` page component that manages all state internally via a Zustand store (`useDashboardStore`). The page conditionally renders view mode or edit mode based on a boolean flag. The `DashboardToolbar`, `DashboardGrid`, and `WidgetPalette` are sibling components rendered within the page. Widget config is edited via a single `WidgetConfigDrawer` that reads the selected widget's Zod schema from the registry and generates a form dynamically.

State management uses:
- **Zustand** (`useDashboardStore`): edit mode flag, selected widget ID, dirty state, local layout cache (unsaved changes).
- **TanStack Query** (`useDashboardLayout`): fetch/sync layout from backend API.
- **Ant Design Form**: inside WidgetConfigDrawer for per-widget configuration.

**UX Design:**

View mode: Widgets render in a read-only grid. No overlay, no drag handles. Widgets are interactive (tooltips, sorting).

Edit mode: Click "Customize" -> grid overlay appears (CSS background with dot pattern), WidgetPalette slides in from right as an Ant Design Drawer, drag/resize handles appear on each widget. Clicking a widget selects it (blue outline) and opens the WidgetConfigDrawer on the right side. Adding from palette places widget at the bottom. "Done" saves and exits edit mode.

Dirty detection: Track layout changes via Zustand `isDirty` flag. Navigation away while dirty triggers `react-router-dom`'s `useBlocker` or a manual `beforeunload` listener.

**Implementation:**

Key files to create:
- `frontend/src/pages/projects/ProjectDashboard.tsx`
- `frontend/src/features/dashboard/composition/DashboardToolbar.tsx`
- `frontend/src/features/dashboard/composition/DashboardGrid.tsx`
- `frontend/src/features/dashboard/composition/WidgetPalette.tsx`
- `frontend/src/features/dashboard/composition/WidgetConfigDrawer.tsx`
- `frontend/src/features/dashboard/composition/stores/useDashboardStore.ts`
- `frontend/src/features/dashboard/composition/hooks/useDashboardLayout.ts`

Key files to modify:
- `frontend/src/routes/index.tsx` -- add dashboard route
- `frontend/src/pages/projects/ProjectLayout.tsx` -- add Dashboard tab
- `frontend/src/api/queryKeys.ts` -- add dashboard layout keys

Technical challenges:
- Zod schema to Ant Design Form dynamic generation requires a utility that traverses the Zod schema and produces form field descriptors.
- `useBlocker` from react-router-dom v6 has unstable API; may need a custom navigation guard.
- react-grid-layout integration must coexist with the existing `@dnd-kit` dependencies (no conflict expected since they serve different purposes).

**Trade-offs:**

| Aspect          | Assessment                                                               |
| --------------- | ------------------------------------------------------------------------ |
| Pros            | Minimal scope, fastest path to a working dashboard page. Clean separation of view/edit modes. Follows existing project patterns exactly. |
| Cons            | Dynamic Zod-to-Form generation may not cover all widget types well. Single Zustand store may grow complex as features are added. |
| Complexity      | Medium                                                                   |
| Maintainability | Good -- each component has a single responsibility, follows project conventions. |
| Performance     | Good -- Zustand for transient state is lightweight. TanStack Query for server state is already proven. |

---

### Option 2: Context-Bus Architecture (Cross-Widget Communication)

**Architecture & Design:**

Extends Option 1 with a **Dashboard Context Bus** -- a React Context at the dashboard root that holds the active `{ projectId, wbeId, costElementId, branch, viewDate }` tuple. Widgets can act as context *providers* (e.g., WBE Tree widget selecting a node) or context *consumers* (e.g., EVM Summary widget re-fetching when wbeId changes). This replaces URL-parameter-driven navigation for intra-dashboard interaction.

The context bus integrates with the existing `useTimeMachineStore` -- branch and asOf changes propagate through the bus to all widgets automatically.

State management uses:
- **React Context** (`DashboardContext`): shared context tuple across widgets.
- **Zustand** (`useDashboardStore`): edit mode, dirty state, layout operations.
- **TanStack Query** (`useDashboardLayout`): server state for layout persistence.
- **Custom hook** (`useWidgetContext`): convenience hook for widgets to subscribe to context changes.

**UX Design:**

Same view/edit mode as Option 1, but with added cross-widget interaction: selecting a WBE in a WBE Tree widget automatically updates all context-consuming widgets on the dashboard. This enables scenarios like "select a cost element in the tree, see its EVM metrics update in the adjacent widget" without page navigation.

**Implementation:**

Additional files beyond Option 1:
- `frontend/src/features/dashboard/composition/context/DashboardContext.tsx`
- `frontend/src/features/dashboard/composition/hooks/useWidgetContext.ts`

Additional complexity:
- Widget definitions must declare which context dimensions they consume and/or provide.
- The `WidgetRegistry` needs metadata for context dependencies.
- Must carefully integrate with `useTimeMachineStore` to avoid circular updates.

**Trade-offs:**

| Aspect          | Assessment                                                               |
| --------------- | ------------------------------------------------------------------------ |
| Pros            | Enables rich cross-widget interaction. Aligns with the research documents' recommendation for a "context propagation model." Provides the foundation for the full vision of composable dashboards. |
| Cons            | Significantly more complex. Context bus is an abstraction that adds mental overhead for widget authors. Risk of over-engineering for Phase 4 if few widgets actually need cross-widget communication initially. Integration with TimeMachine store requires careful design. |
| Complexity      | High                                                                     |
| Maintainability | Fair -- more moving parts, more hooks and context providers to reason about. Requires clear documentation for widget authors. |
| Performance     | Fair to Good -- React Context re-renders all consumers on any change. May need optimization (splitting contexts, memoization) if many widgets subscribe. |

---

### Option 3: Page-Level Dashboard (No Edit Mode, Template Selection Only)

**Architecture & Design:**

A stripped-down version where the project dashboard page renders a pre-configured template with no edit mode. Users select from a list of templates (e.g., "EVM Dashboard," "Project Overview," "Cost Control") but cannot rearrange widgets or change their configuration. The template selector is a dropdown in a simple toolbar. Widget configuration is fixed per template.

This approach defers all composition UX (drag, drop, resize, configure) to a later iteration. Phase 4 focuses only on rendering widgets from a template and integrating the route.

State management uses:
- **TanStack Query** (`useDashboardLayout`): fetch the template layout.
- **No Zustand needed**: no edit state to manage.
- **No WidgetConfigDrawer**: not applicable.
- **No dirty tracking**: not applicable.

**UX Design:**

Simple toolbar at top with template selector dropdown and dashboard name. Widgets render in a fixed grid from the template definition. No edit mode, no drag handles, no palette. Users switch templates via dropdown.

**Implementation:**

Smaller set of files:
- `frontend/src/pages/projects/ProjectDashboard.tsx`
- `frontend/src/features/dashboard/composition/DashboardToolbar.tsx` (simplified -- template selector only)
- `frontend/src/features/dashboard/composition/DashboardGrid.tsx` (read-only rendering)
- `frontend/src/features/dashboard/composition/hooks/useDashboardLayout.ts`

**Trade-offs:**

| Aspect          | Assessment                                                               |
| --------------- | ------------------------------------------------------------------------ |
| Pros            | Lowest complexity, fastest to implement. Delivers value quickly (project-level dashboard with relevant widgets). No drag-and-drop or dynamic form generation needed. Can be extended to full composition later. |
| Cons            | Does not satisfy the core feature request (edit mode, widget palette, configuration drawer). Users cannot customize their dashboards. May feel incomplete compared to the vision described in the research documents. |
| Complexity      | Low                                                                      |
| Maintainability | Good -- simple structure, few components. Easy to extend later.          |
| Performance     | Excellent -- minimal overhead, no edit-mode state management.            |

---

## Comparison Summary

| Criteria           | Option 1: Minimal Viable      | Option 2: Context Bus     | Option 3: Template Only   |
| ------------------ | ----------------------------- | ------------------------- | ------------------------- |
| Development Effort | Medium (~5-8 dev days)        | High (~10-14 dev days)    | Low (~2-3 dev days)       |
| UX Quality         | Good (full edit/view cycle)   | Excellent (cross-widget)  | Basic (template only)     |
| Flexibility        | Good (single-page composition)| Excellent (context propagation) | Poor (fixed templates) |
| Risk               | Medium (Zod-to-Form, useBlocker) | High (context bus complexity, TimeMachine integration) | Low              |
| Alignment with Request | High (covers all deliverables) | High (covers all + adds cross-widget) | Low (defers most deliverables) |
| Best For           | Iterative delivery with full UX | Full vision from day one  | Rapid MVP, defer complexity |

---

## Recommendation

**I recommend Option 1 (Minimal Viable Dashboard) because:** it fully satisfies all deliverables in the feature request (ProjectDashboard page, DashboardToolbar, WidgetConfigDrawer, route integration, view/edit modes) while keeping complexity manageable. It follows existing project conventions (Zustand for UI state, TanStack Query for server state, Ant Design for UI) and introduces no exotic abstractions. The Zod-to-Form generation is the primary technical risk, but it can be addressed incrementally -- starting with simple schemas and adding complexity as needed.

The context bus (Option 2) is valuable but should be introduced in a later iteration once the base composition experience is proven and at least a few widgets demonstrate the need for cross-widget communication. Introducing it now, before any widgets exist that would benefit from it, is premature.

Option 3 is a reasonable fallback if Phases 1-3 are delayed and the team needs to deliver something quickly, but it does not satisfy the core request.

**Alternative consideration:** Choose Option 2 if the team has already invested in the widget registry metadata system (Phase 1) that includes context dependency declarations, making the context bus a natural extension rather than a new abstraction.

---

## Decision Questions

1. **Dashboard tab naming:** The Home page already has a "Dashboard" label in `HeaderNavigation`. Should the project-level tab use a different name (e.g., "Project Dashboard," "Control Center," "Overview Dashboard") to avoid user confusion, or is "Dashboard" sufficient given the different navigation contexts (global vs. project-scoped)?

2. **Zod-to-Form strategy:** Should the WidgetConfigDrawer use a generic Zod-to-Form generator (higher upfront cost, reusable for all widgets), or should each widget type provide its own custom config form component (lower upfront cost, more boilerplate per widget)?

3. **Unsaved changes behavior:** When a user has unsaved layout changes and navigates away (clicks another tab, uses browser back), should the system: (a) block navigation with a confirmation dialog, (b) auto-save as a draft, or (c) silently discard with undo capability? The feature request says "confirmation dialog," but auto-save draft is a more modern UX pattern.

4. **TimeMachine integration scope:** Should widgets on the project dashboard automatically respond to TimeMachine state changes (branch switches, time travel) in Phase 4, or should this be deferred to a later phase? This affects the scope of the `useDashboardLayout` hook and every widget's data-fetching logic.

5. **Phase dependency validation:** Has Phase 1 (widget infrastructure including the grid engine decision) been completed or is it in progress? The choice between `react-grid-layout` and `@dnd-kit`-based custom grid directly impacts this phase's implementation approach.

---

## Risks and Missing Considerations

### Identified Risks

1. **Phase dependency bottleneck:** This phase cannot begin meaningful development until Phases 1-3 deliver the WidgetShell, WidgetRegistry, backend API, and at least one widget definition. If those phases slip, this phase is blocked.

2. **Naming collision with existing "Dashboard":** The global Home page uses "Dashboard" terminology (`features/dashboard/`, `useDashboardData`, `DashboardHeader`). The new per-project dashboard feature must either share this feature folder (confusing) or create a separate feature folder (e.g., `features/project-dashboard/` or `features/dashboard/composition/`). The feature request proposes files under `features/dashboard/`, which would mix with the existing global dashboard components.

3. **Grid engine decision unresolved:** `react-grid-layout` is recommended by the research documents and is the standard for dashboard grid layouts with drag-and-resize. But it is not currently in `package.json`. The project has `@dnd-kit` instead, which is designed for sortable lists, not grid layouts. Phase 1 must resolve this. If `react-grid-layout` is chosen, this phase follows naturally. If `@dnd-kit` is forced, custom grid logic will be significantly more complex.

4. **WidgetConfigDrawer form generation:** Dynamically generating Ant Design forms from Zod schemas is non-trivial. Edge cases include conditional fields, nested objects, array types, and custom validation messages. This is the highest technical risk within this phase's scope.

5. **Mobile responsiveness:** The feature request does not address mobile behavior. The research documents recommend a stacked single-column layout on mobile with no editing. This should be specified before implementation.

### Missing Considerations

1. **Error boundary per widget:** The feature request mentions that "widgets are interactive" in view mode but does not address error isolation. A single broken widget should not crash the entire dashboard. Error boundaries (the project already has `react-error-boundary` in dependencies) should wrap each widget instance.

2. **Empty state:** When a user has no widgets on their dashboard (fresh project, no default template), what does the page show? The feature request says "loads default template" but does not specify what the default template contains or what happens if the default template is somehow empty.

3. **Loading state:** The dashboard page needs a loading skeleton while the layout is being fetched. This is not mentioned in the feature request.

4. **Concurrent editing:** If two browser tabs are open with the same dashboard, edits in one tab may overwrite changes in the other. This is likely acceptable for Phase 4 (single-user assumption) but should be documented.

5. **Permission gating:** Should all users be able to enter edit mode, or should there be a permission check? The feature request does not mention RBAC integration. The existing `usePermission` hook and `can()` function should be considered for the "Customize" button.

---

## References

- Widget system research: `docs/03-project-plan/iterations/2026-04-06-widget-system/claude.md`, `perplexity.md`, `gemini.md`
- Frontend coding standards: `docs/02-architecture/frontend/coding-standards.md`
- Routes: `frontend/src/routes/index.tsx`
- ProjectLayout: `frontend/src/pages/projects/ProjectLayout.tsx`
- Existing dashboard feature: `frontend/src/features/dashboard/`
- Query keys: `frontend/src/api/queryKeys.ts`
- TimeMachine store: `frontend/src/stores/useTimeMachineStore.ts`
- Explorer pattern (recent split-pane): `frontend/src/pages/projects/ProjectExplorer.tsx`
- Product vision: `docs/01-product-scope/vision.md`
- Functional requirements: `docs/01-product-scope/functional-requirements.md`
