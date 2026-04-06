# Analysis: Phase 3 -- First Widget Batch (7 Widgets)

**Created:** 2026-04-05
**Request:** Create 7 widget definitions in `frontend/src/features/dashboard/definitions/` that wrap existing components into the dashboard widget system. Depends on Phase 1 (types, registry, WidgetShell, context) and Phase 2 (API hooks for save/load).

---

## Clarified Requirements

This phase creates the first batch of widget definitions -- thin wrappers around 7 existing UI components that already function in the Explorer and entity detail pages. Each widget definition follows a standard pattern: Zod config schema, React component consuming `WidgetComponentProps<TConfig>`, context from `useDashboardContext()`, data from existing TanStack Query hooks, and registration via `registerWidget()`.

### Functional Requirements

1. **QuickStatsBarWidget** (4x1) -- wraps `KPIStrip.tsx`, driven by `useEVMMetrics()`, config: entityType + variant
2. **EVMSummaryWidget** (2x2) -- wraps `EVMSummaryView.tsx`, driven by `useEVMMetrics()`, config: entityType
3. **BudgetStatusWidget** (2x2) -- wraps `BudgetOverviewChart.tsx`, driven by `useEVMMetrics()`, config: showSparkline
4. **CostRegistrationsWidget** (3x2) -- wraps `StandardTable` with cost registration data, config: pageSize + showAddButton
5. **WBETreeWidget** (3x3) -- wraps `ProjectTree.tsx` as a context provider, config: showBudget + showScheduleDates
6. **VarianceChartWidget** (2x2) -- wraps `VarianceChart.tsx`, driven by `useEVMMetrics()`, config: entityType
7. **ProgressTrackerWidget** (3x2) -- progress entry data via `useProgressEntries`/`useLatestProgress`, config: showHistory + historyLimit
8. **registerAll.ts** -- imports and invokes all 7 register functions

### Non-Functional Requirements

- Each widget definition must be a self-contained module (one file per widget + registerAll)
- Widgets must handle loading, error, and empty states through WidgetShell
- Context propagation from WBETreeWidget must update other widgets via the dashboard context bus
- No modification to existing wrapped components -- only thin adapter wrappers

### Constraints

- **Hard dependency on Phase 1**: `WidgetComponentProps<T>`, `registerWidget()`, `WidgetShell`, `useDashboardContext()`, and the widget type system do not exist in the codebase yet
- **Hard dependency on Phase 2**: API hooks for dashboard save/load must exist before widgets can be persisted
- No existing widget infrastructure in the codebase (verified: no matches for `WidgetShell`, `registerWidget`, `WidgetComponentProps`, `useDashboardContext`)

---

## Context Discovery

### Product Scope

The widget system iteration research (`claude.md`, `perplexity.md`, `gemini.md`) establishes the composable dashboard vision. Phase 3 is specifically the "Widget Extraction" phase from the migration strategy -- porting existing screen sections into widget definitions.

### Architecture Context

- **Existing pattern**: The Explorer page (`ProjectExplorer.tsx`) demonstrates the composition pattern already -- `ProjectTree` in a left pane feeds selection state to `ProjectDetailCards`, `WBEDetailCards`, `CostElementDetailCards` in the right pane. The widget system generalizes this composition.
- **Data flow**: All wrapped components already consume TanStack Query hooks (`useEVMMetrics`, `useCostRegistrations`, `useProgressEntries`, `useLatestProgress`) and receive data as props. This is a clean adaptation boundary.
- **Context bus**: `ProjectTree` already has an `onSelect` callback that returns `TreeNodeData` with `{ id, type, name }`. The widget version needs to write this to the dashboard context bus instead of (or in addition to) local state.

### Codebase Analysis

**Components verified to exist and their data dependencies:**

| Component | File | Data Hook | Props Interface |
|---|---|---|---|
| KPIStrip | `components/explorer/charts/KPIStrip.tsx` | `useEVMMetrics()` | `metrics: EVMMetricsResponse, variant: "full"\|"compact"` |
| EVMSummaryView | `features/evm/components/EVMSummaryView.tsx` | `useEVMMetrics()` | `metrics: EVMMetricsResponse, onAdvanced?: () => void` |
| BudgetOverviewChart | `components/explorer/charts/BudgetOverviewChart.tsx` | `useEVMMetrics()` | `metrics: EVMMetricsResponse, height?: number` |
| ProjectTree | `components/hierarchy/ProjectTree.tsx` | `useWBEs()` + `useProject()` | `projectId: string, onSelect?, showBudget?, showDates?` |
| VarianceChart | `components/explorer/charts/VarianceChart.tsx` | `useEVMMetrics()` | `metrics: EVMMetricsResponse, height?: number` |
| StandardTable | `components/common/StandardTable.tsx` | (generic) | `tableParams, onChange, toolbar?, searchable?` |

**Hooks verified to exist:**

| Hook | File | Key Params |
|---|---|---|
| `useEVMMetrics` | `features/evm/api/useEVMMetrics.ts` | `(entityType: EntityType, entityId: string, params?)` |
| `useBudgetStatus` | `features/cost-registration/api/useCostRegistrations.ts` | `(costElementId: string)` |
| `useCostRegistrations` | `features/cost-registration/api/useCostRegistrations.ts` | `(params?: { cost_element_id, pagination, filters, ... })` |
| `useProgressEntries` | `features/progress-entries/api/useProgressEntries.ts` | `(params?: { cost_element_id, page, perPage, ... })` |
| `useLatestProgress` | `features/progress-entries/api/useProgressEntries.ts` | `(costElementId: string, asOf?: string)` |
| `useProgressHistory` | `features/progress-entries/api/useProgressEntries.ts` | `(costElementId: string, page, perPage)` |

**Key observations:**

1. Five of seven widgets (QuickStatsBar, EVMSummary, BudgetStatus, VarianceChart, ProgressTracker) share the same data acquisition pattern: resolve entity scope from context, call `useEVMMetrics(entityType, entityId)`, pass result to wrapped component. This is a strong signal for a shared helper.

2. `CostRegistrationsWidget` is the only table-based widget. It requires a different integration pattern since `StandardTable` manages its own pagination, search, and sort state internally. This widget needs to bridge between widget config (pageSize, showAddButton) and StandardTable's imperative state.

3. `WBETreeWidget` is architecturally different from all others: it is a **context provider** rather than a consumer. It writes to the context bus on node selection, while the other six widgets read from it. This dual role must be explicitly modeled.

4. `EVMSummaryView` has an `onAdvanced` callback that currently opens the EVM Analyzer modal. In widget context, this behavior needs to be either preserved (modal still works) or adapted (widget-level expand replaces it).

5. `ProjectTree` currently fetches data via `useWBEs` and `useProject`, with child node loading through manual `queryClient.fetchQuery` calls. It uses `useTimeMachineParams()` for branch/time-travel support. All widget wrappers must similarly respect the time machine context.

6. The existing `ExplorerCard` component provides consistent card styling (borderless, header with icon/title/extra). When components are wrapped in `WidgetShell`, the inner `ExplorerCard` may create visual redundancy (card-within-card). This must be addressed per widget.

---

## Solution Options

### Option 1: Thin Adapter Pattern (Minimal Wrapping)

**Architecture & Design:**

Each widget definition creates the thinnest possible adapter between the widget system contract and the existing component. The adapter reads context, fetches data, and passes props directly. No intermediate abstractions or shared utilities beyond what Phase 1 provides.

**Structure per widget:**
1. Zod schema for config (2-5 fields each)
2. Component function that calls `useDashboardContext()` for entity scoping
3. Component calls the appropriate existing TanStack Query hook
4. Component renders the wrapped component with data props
5. Module-level `registerWidget()` call

**Key design decisions:**
- `WBETreeWidget.onSelect` writes `{ wbeId, costElementId }` to the dashboard context bus
- `EVMSummaryView.onAdvanced` is wired to `WidgetShell` expand/fullscreen action
- Components that use `ExplorerCard` internally (KPIStrip) are wrapped as-is; the `WidgetShell` provides the outer frame, and `ExplorerCard` becomes the inner content
- `CostRegistrationsWidget` owns its own `tableParams` state, bridging StandardTable's controlled pattern

**Trade-offs:**

| Aspect          | Assessment |
| --------------- | --- |
| Pros            | Lowest implementation effort; no new abstractions; easy to understand each widget in isolation; no coupling between widget definitions |
| Cons            | Repeated data-fetch patterns across 5 EVM widgets; no shared loading/error handling for EVM-backed widgets; potential card-within-card visual issue unaddressed at pattern level |
| Complexity      | Low |
| Maintainability | Good -- each widget is self-contained; changes to one don't affect others |
| Performance     | Good -- each widget manages its own query independently; TanStack Query deduplicates overlapping requests |

---

### Option 2: Shared EVM Widget Helper + Adapter Pattern

**Architecture & Design:**

Introduces a shared utility (`useWidgetEVMData`) that encapsulates the common pattern across the 5 EVM-backed widgets: resolve entity scope from dashboard context, call `useEVMMetrics`, handle the loading/error/null-data states consistently. Widget definitions still follow the adapter pattern but delegate the shared logic.

**Structure:**
1. `frontend/src/features/dashboard/definitions/shared/useWidgetEVMData.ts` -- shared hook
2. Each EVM widget uses `useWidgetEVMData(config.entityType)` instead of calling `useEVMMetrics` directly
3. Non-EVM widgets (CostRegistrations, WBETree, ProgressTracker) follow Option 1 pattern

**Key design decisions:**
- `useWidgetEVMData(entityType, context)` resolves `entityId` from dashboard context based on `entityType` (project -> projectId, wbe -> wbeId, cost_element -> costElementId)
- Returns `{ metrics, isLoading, error, entityId }` in a uniform shape
- Handles the case where context doesn't have the required entity ID (returns disabled state)
- Each widget still owns its own Zod schema and rendering logic

**Trade-offs:**

| Aspect          | Assessment |
| --------------- | --- |
| Pros            | DRY across 5 widgets; consistent error/loading handling; single place to update EVM data acquisition logic; better alignment with the "centralized formula ownership" PMI principle from research |
| Cons            | Adds one more abstraction layer; must carefully handle entity type resolution (project vs wbe vs cost_element); risk of over-generalizing if widget data patterns diverge |
| Complexity      | Low-Medium |
| Maintainability | Good -- shared EVM logic is centralized; widget-specific logic stays local |
| Performance     | Good -- the shared hook uses `useEVMMetrics` under the hood, which still leverages TanStack Query caching |

---

### Option 3: Widget Definition Factory + Declarative Registry

**Architecture & Design:**

Introduces a `defineWidget()` factory function that provides a declarative API for widget definitions. Instead of each widget manually implementing the register-call-and-component pattern, the factory encapsulates the boilerplate. Widget definitions become declarative configurations with optional overrides.

**Structure:**
1. `defineWidget<TConfig>({ id, displayName, category, size, configSchema, loadData, render })` factory
2. `loadData` function maps `(context, config) => QueryResult` -- describes data needs declaratively
3. `render` function receives `({ config, data, shellProps })` -- pure rendering
4. `registerAll.ts` imports widget definitions and passes them to a registry

**Key design decisions:**
- Factory handles `registerWidget()` call, `WidgetShell` wrapping, loading/error/empty state rendering
- Widgets only declare data needs and rendering logic
- Context resolution is part of the factory's `loadData` pipeline
- Non-standard widgets (WBETree as context provider) use escape hatches

**Trade-offs:**

| Aspect          | Assessment |
| --------------- | --- |
| Pros            | Maximum consistency; minimal boilerplate per widget; declarative style is easier to review; factory can enforce mandatory capabilities (loading states, error handling); aligns with the Perplexity research recommendation for a `WidgetDefinition<TConfig, TQuery, TData>` type |
| Cons            | Highest upfront design investment; factory must anticipate all widget patterns or provide escape hatches; WBETreeWidget's context-provider role doesn't fit the consumer-only factory model well; premature abstraction risk -- only 7 widgets in this batch, may not justify a factory |
| Complexity      | Medium-High |
| Maintainability | Good if factory is well-designed; Poor if factory becomes a leaky abstraction requiring frequent escape hatches |
| Performance     | Good -- factory is a compile-time construct, no runtime overhead |

---

## Comparison Summary

| Criteria           | Option 1: Thin Adapter | Option 2: Shared EVM Helper | Option 3: Widget Factory |
| ------------------ | --- | --- | --- |
| Development Effort | Lowest (~2-3 days) | Low-Medium (~3-4 days) | Medium (~5-6 days) |
| UX Quality         | Good | Good | Good |
| Flexibility        | High (no constraints) | Medium (EVM widgets share pattern) | Medium (must fit factory model) |
| Consistency        | Fair (repeated patterns) | Good (EVM widgets consistent) | Best (factory enforces consistency) |
| Best For           | Rapid prototyping; Phase 3 as proof of concept | Production delivery; balancing speed and quality | Long-term widget ecosystem (20+ widgets) |

---

## Recommendation

**I recommend Option 2 (Shared EVM Widget Helper + Adapter Pattern)** because:

1. **Five of seven widgets share the identical data acquisition pattern** (resolve entity from context -> call `useEVMMetrics` -> pass to component). Extracting this into `useWidgetEVMData` eliminates repetition without over-engineering.

2. **The WBETreeWidget and CostRegistrationsWidget have genuinely different patterns** (context provider vs. table with local state). Option 2 handles this gracefully -- shared helper for EVM widgets, thin adapter for the rest -- while Option 3 would force them into a factory model that doesn't fit.

3. **The 7-widget batch is small enough that a full factory is premature**, but large enough that pure duplication across 5 EVM widgets is wasteful and inconsistent. Option 2 hits the right balance.

4. **The PMI research and Perplexity analysis both emphasize centralized formula/data ownership.** A shared EVM hook is the minimal expression of that principle.

**Alternative consideration:** Choose Option 1 if Phase 3 is treated as a throwaway prototype and the widget definitions will be rewritten when the factory pattern stabilizes. Choose Option 3 if the total planned widget count is 20+ and the team is committed to building the factory abstraction upfront.

---

## Identified Risks and Recommendations

### Risk 1: Phase 1/2 Dependencies Not Yet Implemented

**Severity:** Critical
**Description:** The feature request explicitly depends on Phase 1 (types, registry, WidgetShell, context) and Phase 2 (API hooks). Neither exists in the codebase. Writing widget definitions against interfaces that don't exist creates a high risk of rework if those interfaces change during Phase 1/2 implementation.
**Recommendation:** Phase 3 analysis should proceed to plan, but implementation must wait until Phase 1 and Phase 2 are complete and their contracts are stable. Consider defining the Phase 1 interfaces as part of this analysis so that Phase 3 widget definitions can be written against a known contract.

### Risk 2: Card-Within-Card Visual Redundancy

**Severity:** Medium
**Description:** `KPIStrip`, `EVMSummaryView`, and other components render inside `ExplorerCard`, which provides its own header, border, and padding. When wrapped in `WidgetShell` (which also provides a frame), this creates nested card chrome.
**Recommendation:** Each widget definition must decide whether to: (a) strip the `ExplorerCard` from the wrapped component (requires modifying the existing component or creating a variant), (b) suppress `WidgetShell`'s own frame for this widget, or (c) accept the visual nesting. The cleanest approach is (a) -- have the widget definition render the component content without the ExplorerCard wrapper, passing only the inner content to WidgetShell.

### Risk 3: Context Bus Entity Resolution

**Severity:** Medium
**Description:** Widgets declare which entity they operate on via config (`entityType`). The dashboard context bus provides `{ projectId, wbeId, costElementId, branch, viewDate }`. A widget configured for `entityType: "wbe"` must resolve `wbeId` from context, but what happens when `wbeId` is null because no WBE is selected?
**Recommendation:** Each widget must handle the "no entity selected" state gracefully. For EVM widgets, show an empty state with guidance ("Select a WBE from the tree"). For the WBETreeWidget, it always has `projectId` from context and needs no entity selection.

### Risk 4: CostRegistrationsWidget Data Scope

**Severity:** Medium
**Description:** `useCostRegistrations` requires `cost_element_id` as a mandatory parameter. On a dashboard context, the user may have selected a WBE or project, not a specific cost element. The hook will not fetch data without a cost element ID.
**Recommendation:** The CostRegistrationsWidget should either: (a) only be available when a cost element is in context (configurable constraint), (b) aggregate cost registrations across all cost elements in the selected scope (requires a new or modified backend endpoint), or (c) display the cost registrations for the first cost element in the selected WBE/project. Option (a) is simplest and recommended for this batch.

### Risk 5: ProgressTrackerWidget Data Scope

**Severity:** Medium
**Description:** Same issue as Risk 4 -- progress hooks require `cost_element_id`. Progress entries are per-cost-element, not per-WBE or per-project.
**Recommendation:** Same as Risk 4 -- constrain to cost element scope for this batch.

### Risk 6: Time Machine Context Integration

**Severity:** Low-Medium
**Description:** Existing hooks (`useEVMMetrics`, `useCostRegistrations`, etc.) internally call `useTimeMachineParams()` for branch and time-travel support. When these hooks are used inside widget components, the TimeMachine context must still be available in the React tree. The dashboard page must ensure the TimeMachine provider wraps the widget grid.
**Recommendation:** This is a Phase 1 concern (the dashboard page layout), not a Phase 3 widget concern. But widget definitions should not override or bypass the time machine params.

---

## Decision Questions

1. **Entity scope constraints:** Should the CostRegistrationsWidget and ProgressTrackerWidget be restricted to cost-element-only scope in this batch, or should we implement a WBE/project aggregation view (which requires backend work)?

2. **ExplorerCard handling:** For widgets that wrap components using `ExplorerCard` internally, should we: (a) create new variants of those components that omit the card wrapper, (b) render the component as-is and accept visual nesting, or (c) have WidgetShell detect and suppress its own chrome for nested-card widgets?

3. **WBETreeWidget as context provider:** When the WBETreeWidget updates the context bus with a selected node, should all other widgets on the dashboard re-fetch immediately, or should there be a debounce/delay to avoid cascading API calls when the user navigates rapidly through the tree?

4. **Phase sequencing:** Should Phase 3 planning wait until Phase 1 and Phase 2 analysis and plans are approved and their output contracts are defined, or should we proceed with planning in parallel and accept potential rework?

---

## References

- Widget system iteration research: `docs/03-project-plan/iterations/2026-04-06-widget-system/claude.md`, `perplexity.md`, `gemini.md`
- Explorer composition pattern: `frontend/src/pages/projects/ProjectExplorer.tsx`
- KPIStrip component: `frontend/src/components/explorer/charts/KPIStrip.tsx`
- EVMSummaryView component: `frontend/src/features/evm/components/EVMSummaryView.tsx`
- BudgetOverviewChart component: `frontend/src/components/explorer/charts/BudgetOverviewChart.tsx`
- VarianceChart component: `frontend/src/components/explorer/charts/VarianceChart.tsx`
- ProjectTree component: `frontend/src/components/hierarchy/ProjectTree.tsx`
- StandardTable component: `frontend/src/components/common/StandardTable.tsx`
- EVM hooks: `frontend/src/features/evm/api/useEVMMetrics.ts`
- Cost registration hooks: `frontend/src/features/cost-registration/api/useCostRegistrations.ts`
- Progress entry hooks: `frontend/src/features/progress-entries/api/useProgressEntries.ts`
- EVM types: `frontend/src/features/evm/types.ts`
- ExplorerCard pattern: `frontend/src/components/explorer/ExplorerCard.tsx`
- Analysis prompt: `docs/04-pdca-prompts/analysis-prompt.md`
- Analysis template: `docs/04-pdca-prompts/_templates/00-analysis-template.md`
