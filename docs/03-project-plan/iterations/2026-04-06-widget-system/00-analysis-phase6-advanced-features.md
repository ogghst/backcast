# Analysis: Phase 6 -- Advanced Features (Widget Polish)

**Created:** 2026-04-05
**Request:** Add quality-of-life polish features on top of the completed widget system (Phases 1-5): Widget Export, Auto-Refresh, Responsive Mobile Layout, Undo/Redo for Composition, Widget Fullscreen Mode, and Motion & Animation.

---

## Clarified Requirements

This phase delivers six distinct polish features for the composable widget dashboard. None are core requirements for the dashboard to function, but all contribute to a production-grade user experience. The features are assumed to layer on top of a completed Phase 1 (Widget Infrastructure + WidgetShell) and Phase 4 (Dashboard Composition UX with edit mode).

### Functional Requirements

**F1. Widget Export**
- PNG export for ECharts chart widgets using the chart instance's `getDataURL()` method
- CSV export for table-based widgets via custom Blob serializer + download trigger
- JSON export for raw widget data
- Export actions surfaced in the widget header "more" dropdown menu

**F2. Auto-Refresh**
- Per-widget configurable refresh interval: Off / 30s / 1min / 5min
- Interval setting stored in widget instance config (`refreshInterval` field)
- Powered by TanStack Query's `refetchInterval` option
- Auto-refresh paused when widget is not visible (IntersectionObserver)
- Visual stale indicator when data age exceeds the configured interval

**F3. Responsive Mobile Layout**
- Desktop (>= 1200px): full 12-column grid with drag and resize
- Tablet (768-1199px): 8-column grid, simplified composition, larger touch handles
- Mobile (< 768px): single-column stacked layout, no drag; reorder via "Manage Widgets" bottom sheet
- Widgets store separate layout coordinates per breakpoint
- Mobile edit mode: bottom sheet with widget list supporting reorder, hide/show, and size presets

**F4. Undo/Redo for Composition**
- Composition store maintains an undo stack of dashboard layout snapshots
- Keyboard shortcuts: Ctrl+Z (undo) and Ctrl+Shift+Z (redo) active in edit mode
- Maximum 20 undo steps before oldest entries are pruned
- Undo stack cleared when the user explicitly saves the dashboard

**F5. Widget Fullscreen Mode**
- Modal overlay rendering the widget at full viewport size for detailed analysis
- Triggered by expand button in widget header
- Close with Escape key or close button
- Uses Ant Design Modal in fullscreen configuration

**F6. Motion & Animation**
- Widget mount: fade-in with 4px upward translate, 200ms ease-out, staggered 50ms per widget
- Skeleton shimmer: CSS linear-gradient animation (already partially implemented in `DashboardSkeleton.tsx`)
- No layout shift during data refresh: in-place DOM updates
- Spring-like motion on drag/resize commit (CSS transition, not JS animation library)

### Non-Functional Requirements

- No additional runtime dependencies (leverage existing libraries: TanStack Query, ECharts API, Ant Design Modal, CSS transitions)
- All features must respect edit mode vs view mode boundaries
- Features must not degrade performance on dashboards with 10+ widgets
- Keyboard accessibility for fullscreen (Escape) and undo/redo (Ctrl+Z/Ctrl+Shift+Z)
- Mobile features must work on touch devices without hover dependency

### Constraints

- `react-grid-layout` is NOT currently in `package.json` -- this phase assumes it will be added in Phase 1 or Phase 4
- The existing `useBreakpoint` hook in `src/components/time-machine/useBreakpoint.ts` provides breakpoint detection aligned with Ant Design's system and should be reused
- The project uses Ant Design tokens via `useThemeTokens()` -- motion values should align with the theme system
- ECharts `getDataURL()` is already used in `EChartsTimeSeries.tsx` as a proven export pattern

---

## Context Discovery

### Product Scope

- The widget system is not explicitly defined in current functional requirements (`docs/01-product-scope/`). It emerged from the architectural analysis captured in the three research documents under this iteration folder (claude.md, perplexity.md, gemini.md).
- The PMI-aligned EVM reporting context demands that export features produce audit-suitable outputs (correct values, timestamps, context labels).
- Dashboard personalization is a user story inferred from the composable widget vision, not yet formalized in the product backlog.

### Architecture Context

- **Bounded contexts:** Dashboard/Widget system is a new frontend-dominant bounded context. Backend involvement is limited to persisting layout configs (Phase 2 concern, not this phase).
- **State management:** TanStack Query for server state, Zustand for client state. Widget config and undo stack belong in Zustand. Auto-refresh uses TanStack Query's `refetchInterval`.
- **Existing patterns:**
  - ECharts export via `getDataURL()` already implemented in `frontend/src/features/evm/components/charts/EChartsTimeSeries.tsx`
  - Shimmer skeleton animation already implemented in `frontend/src/features/dashboard/components/DashboardSkeleton.tsx` using CSS keyframe injection
  - Breakpoint detection via `useBreakpoint` hook at `frontend/src/components/time-machine/useBreakpoint.ts`
  - Mobile detection via `MOBILE_BREAKPOINT = 768` in `frontend/src/layouts/AppLayout.tsx`
  - Ant Design Modal used throughout the application
  - Theme tokens via `useThemeTokens()` hook used across all dashboard components

### Codebase Analysis

**Frontend:**

| Existing Asset | Relevance to Phase 6 |
|---|---|
| `EChartsTimeSeries.tsx` | PNG export pattern (`getDataURL` + programmatic download) is the reference implementation for F1 |
| `DashboardSkeleton.tsx` | Shimmer animation pattern with CSS keyframe injection is the basis for F6 |
| `useBreakpoint.ts` | Breakpoint detection hook should be reused for F3 responsive layout |
| `AppLayout.tsx` | Mobile detection pattern (`window.innerWidth < 768`) -- prefer `useBreakpoint` instead |
| `echartsConfig.ts` | Shared ECharts configuration builders -- export should not bypass these |
| Explorer charts (`BudgetOverviewChart`, `VarianceChart`, etc.) | Additional chart widgets that will need export capability |

**Backend:**

- No backend changes required for Phase 6. All features are frontend-only.
- The `refreshInterval` field in widget config will need to be part of the widget config schema defined in Phase 1 and persisted via the Phase 2 backend API.

---

## Solution Options

### Option 1: Phased Delivery with Priority Tiers

Deliver features in two sub-phases based on user impact and implementation risk.

**Tier A (Deliver First):** Widget Fullscreen, Motion & Animation, Widget Export
**Tier B (Deliver Second):** Auto-Refresh, Responsive Mobile Layout, Undo/Redo

**Architecture & Design:**

- Tier A features are self-contained enhancements to the WidgetShell component. Fullscreen is a wrapper concern. Motion is CSS-only. Export is a utility function set.
- Tier B features require cross-cutting integration: Auto-Refresh touches every widget's data hook; Responsive Layout requires the grid engine to be fully wired; Undo/Redo requires the composition store to be designed with snapshot support from the start.

**UX Design:**

- Tier A delivers immediate visual and functional polish that demo stakeholders notice.
- Tier B delivers operational quality (always-fresh data, mobile usability, safe editing) that matters for daily production use.

**Implementation:**

Tier A files:
- Widget fullscreen: modification to `WidgetShell` to wrap content in Ant Design Modal, triggered by expand icon
- Motion: CSS module with `@keyframes widgetMount`, applied via className on WidgetShell mount
- Export: `useWidgetExport` hook with three methods (`exportPNG`, `exportCSV`, `exportJSON`), consuming ECharts ref or table data

Tier B files:
- Auto-refresh: `useWidgetAutoRefresh` hook wrapping TanStack Query's `refetchInterval`, with IntersectionObserver guard
- Responsive: new `ResponsiveGrid.tsx` component wrapping react-grid-layout's `ResponsiveGridLayout`, with breakpoint configs
- Undo/Redo: `useUndoStack` hook in composition Zustand store, storing serialized layout snapshots

**Trade-offs:**

| Aspect          | Assessment |
| --------------- | --- |
| Pros            | High-impact features ship first; lower-risk items get more design time; incremental delivery allows user feedback |
| Cons            | Mobile users wait longer; undo/redo is delayed despite being a composition safety net |
| Complexity      | Low-Medium (each feature is self-contained) |
| Maintainability | Good (each feature is an independent hook or component) |
| Performance     | No cross-feature performance coupling |

---

### Option 2: All Six Features in Parallel with Shared Abstraction Layer

Build a unified "Widget Enhancement" abstraction that all six features plug into.

**Architecture & Design:**

- Create a `WidgetEnhancementProvider` React context that wraps the dashboard grid and provides: export registry, refresh scheduler, viewport observer, motion controller, and undo manager.
- Each widget registers with the provider on mount and unregisters on unmount.
- The provider coordinates: pausing refresh for off-screen widgets, staggering mount animations, and managing the undo stack.

**UX Design:**

- Consistent behavior across all widgets because the provider enforces contracts.
- Single source of truth for "is this widget visible?" (IntersectionObserver), "is this widget stale?" (refresh timer), and "what animation state is this widget in?" (motion controller).

**Implementation:**

Key files:
- `WidgetEnhancementProvider.tsx` -- context provider with coordinator logic
- `useWidgetEnhancement.ts` -- hook consumed by each widget instance
- `widgetExport.ts` -- pure utility functions for PNG/CSV/JSON export
- `refreshScheduler.ts` -- interval management with IntersectionObserver integration
- `motionController.ts` -- stagger delay calculator and CSS class manager
- `undoManager.ts` -- snapshot store with redo support

**Trade-offs:**

| Aspect          | Assessment |
| --------------- | --- |
| Pros            | Unified architecture; single integration point; features can cross-reference (e.g., "pause auto-refresh during export") |
| Cons            | Over-engineered for the actual complexity; provider becomes a god-object; harder to test individual features; higher coupling |
| Complexity      | High |
| Maintainability | Fair (provider becomes a maintenance burden; many concerns in one place) |
| Performance     | Good (centralized observers are more efficient than per-widget observers) |

---

### Option 3: Minimal Viable Polish (3 Features Only)

Deliver only the three features that require zero new dependencies and have the highest user-facing impact. Defer the other three to a later iteration.

**Include:** Widget Fullscreen, Widget Export, Motion & Animation
**Defer:** Auto-Refresh, Responsive Mobile Layout, Undo/Redo

**Architecture & Design:**

- Fullscreen: Ant Design Modal wrapper on WidgetShell. No new abstractions.
- Export: Utility functions extracted from the existing `EChartsTimeSeries.tsx` pattern, generalized for any widget type.
- Motion: CSS-only animations added to the existing `DashboardSkeleton.tsx` keyframe injection pattern.

**UX Design:**

- Users get a polished desktop experience immediately.
- Mobile users see the desktop layout scaled down (acceptable for MVP, not for production).
- No auto-refresh means manual page refresh to see updated data.
- No undo means composition changes are permanent (risky, but mitigated by explicit save action in Phase 4).

**Implementation:**

Key files:
- `WidgetShell.tsx` -- add fullscreen modal wrapper and mount animation className
- `useWidgetExport.ts` -- hook with `exportPNG(chartRef)`, `exportCSV(data, filename)`, `exportJSON(data, filename)`
- `widgetMotion.css` -- `@keyframes widgetMount`, `@keyframes shimmer`, stagger delay CSS custom properties

**Trade-offs:**

| Aspect          | Assessment |
| --------------- | --- |
| Pros            | Fastest delivery; zero risk of over-engineering; each feature is independently testable |
| Cons            | Mobile support deferred; no auto-refresh is a functional gap for real-time monitoring dashboards; no undo is a UX regression for the composition editor |
| Complexity      | Low |
| Maintainability | Good |
| Performance     | Good |

---

## Comparison Summary

| Criteria           | Option 1 (Phased Tiers) | Option 2 (Shared Provider) | Option 3 (Minimal 3) |
| ------------------ | --- | --- | --- |
| Development Effort | Medium (6 features, 2 deliveries) | High (6 features, 1 delivery) | Low (3 features, 1 delivery) |
| UX Quality         | High (all features delivered in priority order) | High (all features, uniform behavior) | Medium (desktop-only polish, mobile gap) |
| Flexibility        | Good (tiers can be reprioritized) | Poor (provider is rigid) | Good (deferred features can be redesigned later) |
| Best For           | Iterative delivery with feedback loops | Architecturally maximalist approach | Fastest possible polish for demo or MVP |
| Risk               | Low-Medium | High (provider coupling) | Low |

---

## Recommendation

**I recommend Option 1 (Phased Delivery with Priority Tiers) because:**

1. It delivers all six features without over-engineering. Each feature is a standalone hook or component, following the project's established pattern of custom hooks (`useBreakpoint`, `useThemeTokens`, `useDashboardData`).

2. Tier A (Fullscreen, Motion, Export) can be built immediately after Phase 4 lands, with zero dependency on the grid engine's final API. These features operate at the WidgetShell level.

3. Tier B (Auto-Refresh, Responsive, Undo/Redo) naturally depends on the composition store and grid engine being stable. Building them second ensures the store API is finalized before the undo stack is integrated.

4. The existing codebase already proves the patterns: `EChartsTimeSeries.tsx` demonstrates PNG export, `DashboardSkeleton.tsx` demonstrates CSS animation, `useBreakpoint.ts` demonstrates responsive detection. Option 1 reuses these proven patterns rather than inventing a new abstraction layer.

**Alternative consideration:** Choose Option 3 if the team needs to demo the widget system at a stakeholder review before the composition store and grid engine are finalized. The three included features (Fullscreen, Export, Motion) are the most visually impressive and require no grid-level integration.

---

## Decision Questions

1. **Auto-Refresh default:** Should widgets default to "off" or to a specific interval (e.g., 1 minute)? For an EVM dashboard where data changes infrequently (weekly cost registrations), aggressive polling may be wasteful.

2. **Responsive layout persistence:** Should the mobile reordering in the "Manage Widgets" sheet persist to the backend as a separate mobile layout, or should it be derived automatically from the desktop layout by collapsing to a priority-ordered stack?

3. **Undo granularity:** Should the undo stack capture every individual widget move/resize as a separate step, or batch multiple rapid changes (e.g., dragging a widget through several grid positions) into a single undo entry?

4. **Export filename convention:** What naming convention should exported files follow? The existing pattern in `EChartsTimeSeries.tsx` uses `evm-chart-{type}-{index}-{timestamp}.png`. Should widget exports follow `{widgetType}-{dashboardName}-{timestamp}.{ext}`?

5. **Animation performance budget:** For dashboards with 15+ widgets, the staggered mount animation (50ms per widget) could take 750ms before the last widget appears. Is this acceptable, or should the stagger cap at a maximum total delay (e.g., 400ms with stagger reducing proportionally)?

---

## Feature Priority Assessment

Ranking the six features by urgency and architectural dependency:

| Priority | Feature | Rationale |
| --- | --- | --- |
| 1 (Highest) | Widget Fullscreen | Essential for data-heavy widgets (Gantt, EVM S-curve); trivial to implement; no dependencies |
| 2 | Widget Export | PMI audit trail requirement; existing pattern to follow; no dependencies |
| 3 | Motion & Animation | Pure CSS; proven pattern in DashboardSkeleton; high visual impact |
| 4 | Auto-Refresh | Operational quality for monitoring; requires TanStack Query integration per widget |
| 5 | Responsive Mobile Layout | Depends on grid engine; requires react-grid-layout responsive breakpoints; high implementation effort |
| 6 | Undo/Redo | Depends on composition store API; highest complexity relative to user impact |

### Features Worth Promoting to Earlier Phases

**Widget Fullscreen** should be promoted to Phase 1 (Widget Infrastructure). It is a pure WidgetShell concern with no dependency on the grid engine, composition store, or backend API. Building it early ensures every widget built in Phases 2-3 has fullscreen from day one.

**Widget Export (PNG only)** could also be promoted to Phase 1 for chart widgets, since the pattern is already proven in `EChartsTimeSeries.tsx`. CSV and JSON export can remain in Phase 6.

---

## References

- Existing PNG export pattern: `frontend/src/features/evm/components/charts/EChartsTimeSeries.tsx` (lines 175-196)
- Skeleton shimmer animation: `frontend/src/features/dashboard/components/DashboardSkeleton.tsx`
- Breakpoint detection hook: `frontend/src/components/time-machine/useBreakpoint.ts`
- ECharts configuration builders: `frontend/src/features/evm/utils/echartsConfig.ts`
- Dashboard feature types: `frontend/src/features/dashboard/types.ts`
- Widget system research: `docs/03-project-plan/iterations/2026-04-06-widget-system/claude.md`
- Frontend coding standards: `docs/02-architecture/frontend/coding-standards.md`
