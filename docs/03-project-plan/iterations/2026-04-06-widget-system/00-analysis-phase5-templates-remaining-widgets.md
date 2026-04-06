# Analysis: Phase 5 -- Templates + Remaining Widgets

**Created:** 2026-04-05
**Request:** Add template system (3 built-in templates) and complete the widget catalogue (9 remaining widget definitions) for the composable dashboard system. Depends on Phases 1-4 being complete.

---

## Clarified Requirements

This phase delivers two distinct but related work streams: (A) three pre-built dashboard templates seeded into the database, and (B) nine additional widget definitions that wrap existing feature components into the widget framework.

### Assumptions

1. Phases 1-4 of the widget system are complete. This means `WidgetShell`, the widget registry, `react-grid-layout` grid integration, the dashboard context bus, the dashboard save/load API, and the first batch of widgets (BudgetStatus, EVMSummary, WBETree, CostRegistrations, CostElementGrid, QuickStatsBar, VarianceAnalysis, ProgressTracker) all exist and are functional.
2. The backend `dashboard_layout_service.py` exists with CRUD operations for dashboard layouts.
3. The `WidgetDefinition<TConfig, TQuery, TData>` interface and the widget registry pattern are established.
4. Templates are `Dashboard` objects with `isTemplate: true` and predefined widget instances.

### Functional Requirements

**Part A: Template System**
- FR-5.1: Three built-in templates (PM Overview, EVM Analyst, Cost Controller) are seeded into the database on application startup or migration.
- FR-5.2: Each template is a Dashboard record with `isTemplate: true`, containing pre-configured widget instances with fixed grid positions.
- FR-5.3: Templates can be applied to a project to create a user's personal dashboard instance.
- FR-5.4: Template seeding is idempotent (upsert behavior, no duplicates on repeated application starts).

**Part B: Remaining Widget Definitions**
- FR-5.5: EVMTrendChartWidget (4x3) wrapping `EVMTimeSeriesChart` with granularity and entityType configuration.
- FR-5.6: EVMEfficiencyGaugesWidget (4x2) wrapping dual `EVMGauge` components (CPI + SPI) with threshold configuration.
- FR-5.7: MiniGanttWidget (6x3) wrapping Gantt chart components with zoom and baseline overlay configuration.
- FR-5.8: ForecastWidget (3x2) wrapping forecast display with showVAC/showETC configuration.
- FR-5.9: ChangeOrdersListWidget (4x3) wrapping change order table with status filter and pagination.
- FR-5.10: ChangeOrderAnalyticsWidget (4x3) wrapping SCurve/charts with chart type configuration.
- FR-5.11: AIChatWidget (4x4) wrapping the ChatInterface with persona and session persistence.
- FR-5.12: ProjectHeaderWidget (4x1) wrapping ProjectSummaryCard with date/status display toggles.
- FR-5.13: HealthSummaryWidget (4x2) -- new aggregated SPI/CPI/SV display with color-coded status and configurable thresholds.

### Non-Functional Requirements

- NFR-5.1: Each widget must implement the standard widget contract (loading skeleton, error state with retry, empty state, context binding).
- NFR-5.2: Template seeding must not block application startup (async or migration-based).
- NFR-5.3: Widget wrappers must not duplicate data-fetching logic; they must delegate to existing hooks.
- NFR-5.4: AIChatWidget must handle the WebSocket lifecycle correctly within the widget lifecycle (connect on mount, disconnect on unmount or when widget is removed from grid).
- NFR-5.5: MiniGanttWidget must perform acceptably within a constrained grid cell (potentially reduced data density vs full-page Gantt).

### Constraints

- Templates depend on the widget catalogue being complete (widgets referenced in templates must have valid type IDs in the registry).
- AIChatWidget is architecturally complex: it embeds a full WebSocket session inside a widget, which introduces lifecycle and memory concerns.
- HealthSummaryWidget is the only widget in this batch that has no existing component to wrap -- it requires new UI implementation.
- MiniGanttWidget wrapping the full ECharts Gantt into a small grid cell may require a simplified rendering mode.

---

## Context Discovery

### Product Scope

- The widget system vision is documented in three AI research files at `docs/03-project-plan/iterations/2026-04-06-widget-system/` (claude.md, perplexity.md, gemini.md).
- Templates serve as onboarding mechanisms ("Start with a Template") and role-based defaults (PM, EVM Analyst, Cost Controller) aligned with PMI reporting standards.
- The widget taxonomy follows PMI categories: Summary, Trend, Diagnostic, Breakdown, Forecast, Action, Narrative, Utility.

### Architecture Context

- **Bounded contexts involved:** Dashboard (new), EVM (existing), Schedule Baselines (existing), Forecasts (existing), Change Orders (existing), AI Chat (existing), Projects (existing).
- **Existing patterns to follow:**
  - Widget definition pattern from Phases 1-4: `WidgetDefinition<TConfig, TQuery, TData>` with `useData`, `render`, `configSchema`, `defaultSize`, `minSize`.
  - TanStack Query hooks for data fetching (`useEVMMetrics`, `useEVMTimeSeries`, `useForecasts`, `useChangeOrders`).
  - TimeMachineContext integration for time-travel and branch parameters.
  - WidgetShell for chrome (header, loading, error, expand).
- **Architectural constraints:** Single-server deployment; in-memory event bus for AI chat; WebSocket connections are per-client.

### Codebase Analysis

**Backend:**

- `backend/app/services/dashboard_service.py` -- existing dashboard service (recent activity, project spotlight). No `dashboard_layout_service.py` exists yet; this is expected to be created in Phase 2.
- No `seed_templates()` function exists; this is new work for Phase 5.
- EVM metrics endpoints exist: `/api/v1/evm/{entity_type}/{entity_id}/metrics` and `/api/v1/evm/{entity_type}/{entity_id}/timeseries`.
- Forecast, change order, schedule baseline, and progress entry endpoints all exist.

**Frontend:**

- **EVM components to wrap:**
  - `frontend/src/features/evm/components/EVMTimeSeriesChart.tsx` -- full time-series chart with granularity control.
  - `frontend/src/features/evm/components/EVMGauge.tsx` -- individual gauge for CPI or SPI.
  - `frontend/src/features/evm/components/EVMSummaryView.tsx` -- metric summary cards.
  - Data hooks: `useEVMMetrics()`, `useEVMTimeSeries()` in `features/evm/api/useEVMMetrics.ts`.

- **Gantt components to wrap:**
  - `frontend/src/features/schedule-baselines/components/GanttChart/GanttChart.tsx` -- full ECharts Gantt.
  - Data hooks: `useGanttData.ts`, `useScheduleBaselines.ts`.

- **Forecast components to wrap:**
  - `frontend/src/features/forecasts/components/ForecastComparisonCard.tsx`, `ForecastHistoryView.tsx`.
  - Data hooks: `useForecasts`, `useForecast` in `features/forecasts/api/useForecasts.ts`.

- **Change order components to wrap:**
  - `frontend/src/features/change-orders/components/ChangeOrderList.tsx`, `ChangeOrderAnalytics.tsx`, `SCurveChart.tsx`, `StatusDistributionChart.tsx`, `CostTrendChart.tsx`.
  - Data hooks: `useChangeOrders.ts`, `useChangeOrderStats.ts`.

- **AI chat components to wrap:**
  - `frontend/src/features/ai/chat/components/ChatInterface.tsx` -- full chat with session sidebar, message list, input, streaming.
  - Data hooks: `useStreamingChat.ts`, `useChatSessions.ts`, `useChatSessionsPaginated.ts`.
  - WebSocket-based streaming with agent activity panel.

- **Project header to wrap:**
  - `frontend/src/components/hierarchy/ProjectSummaryCard.tsx`.
  - Data hooks: `useProject()` from `features/projects/api/useProjects.ts`.

- **Explorer charts (potentially reusable):**
  - `frontend/src/components/explorer/charts/` -- BudgetOverviewChart, VarianceChart, PerformanceRadar, KPIStrip, BudgetUtilizationGauge. These could inform the HealthSummaryWidget implementation.

---

## Solution Options

### Option 1: Sequential Implementation -- Templates First, Then Widget Wrappers

**Architecture & Design:**

Build all nine widget definitions first, verify each one independently, then build the template system that references them. The template seeder runs as an Alembic data migration. Each widget wrapper is a thin adapter: it takes the widget's `TConfig`, maps it to the wrapped component's props, and delegates all data fetching to existing hooks.

**UX Design:**

Templates appear as preset options when creating a new dashboard. Users select "Start from Template" and pick one of the three built-in templates. The system clones the template's layout into a personal dashboard. Widgets within templates render identically to their standalone counterparts.

**Implementation:**

1. Implement HealthSummaryWidget first (the only truly new component).
2. Implement widget wrappers in dependency order: ProjectHeaderWidget (simplest), EVMTrendChartWidget, EVMEfficiencyGaugesWidget, ForecastWidget, ChangeOrdersListWidget, ChangeOrderAnalyticsWidget, MiniGanttWidget (complex ECharts sizing), AIChatWidget (complex lifecycle).
3. Create template TypeScript definitions in `frontend/src/features/dashboard/templates/`.
4. Create backend `seed_templates()` in `dashboard_layout_service.py` as an idempotent upsert.
5. Create Alembic data migration to seed templates.
6. Wire template selection into the dashboard creation flow.

Key technical challenge: AIChatWidget must manage WebSocket lifecycle within the widget's mount/unmount cycle. The `ChatInterface` component expects to manage its own session list sidebar; the widget wrapper must suppress the sidebar and provide a simplified view.

**Trade-offs:**

| Aspect          | Assessment                                                                                   |
| --------------- | -------------------------------------------------------------------------------------------- |
| Pros            | Clear dependency ordering; templates always reference valid widget types; testable incrementally |
| Cons            | Longer time before any template is usable; AIChatWidget complexity blocks template completion |
| Complexity      | Medium -- individual widgets are mostly thin wrappers; AIChatWidget and MiniGanttWidget are the outliers |
| Maintainability | Good -- each widget wrapper is isolated; templates are declarative data                      |
| Performance     | Good -- thin wrappers add negligible overhead; template seeding is one-time                  |

---

### Option 2: Parallel Tracks -- Widget Wrappers + Template Skeleton Simultaneously

**Architecture & Design:**

Split into two independent work streams. Track A builds the nine widget wrappers. Track B builds the template infrastructure (backend seeding, frontend template picker UI) with placeholder references. Both tracks merge when all widgets are ready. The template seeder validates that all referenced widget types exist in the registry before inserting.

**UX Design:**

Same as Option 1. The template picker UI can be built with mock widgets initially, then switches to real widgets once Track A delivers.

**Implementation:**

Track A (Widgets):
- Same widget implementation order as Option 1.
- Each widget is independently testable and deployable.

Track B (Templates):
- Define template schema (JSON structure for dashboard + widget instances).
- Build backend `seed_templates()` with registry validation.
- Build frontend template picker UI (gallery of templates with preview thumbnails).
- Use placeholder rendering for widgets not yet implemented.

Key risk: If a widget's actual props/config surface differs significantly from the template's assumed layout, the template may need adjustment after Track A completes.

**Trade-offs:**

| Aspect          | Assessment                                                                                   |
| --------------- | -------------------------------------------------------------------------------------------- |
| Pros            | Faster overall delivery; template infrastructure ready when widgets complete; parallelizable  |
| Cons            | Risk of template-widget mismatch; requires coordination between tracks; more integration testing |
| Complexity      | Medium-High -- two parallel tracks require careful synchronization                           |
| Maintainability | Good -- same isolation as Option 1                                                           |
| Performance     | Good -- no difference from Option 1                                                          |

---

### Option 3: Defer Complex Widgets -- Ship Templates with Available Widgets Only

**Architecture & Design:**

Classify the nine widgets into tiers by complexity. Ship the template system with the simpler widgets (ProjectHeaderWidget, EVMTrendChartWidget, EVMEfficiencyGaugesWidget, ForecastWidget, ChangeOrdersListWidget, HealthSummaryWidget). Defer the three complex widgets (MiniGanttWidget, ChangeOrderAnalyticsWidget, AIChatWidget) to a Phase 5b.

Templates use only the available widgets. The PM Overview and Cost Controller templates ship immediately. The EVM Analyst template ships with the EVM widgets but without the AI Chat placeholder.

**UX Design:**

Templates show a "Coming Soon" placeholder for deferred widgets. Users who need Gantt or AI Chat in their dashboard must wait for Phase 5b. The widget palette shows available widgets with disabled entries for deferred ones.

**Implementation:**

1. Implement 6 simpler widgets in dependency order.
2. Build template system referencing only the 6 available widgets.
3. Build backend seeding and frontend template picker.
4. Phase 5b: Implement MiniGanttWidget, ChangeOrderAnalyticsWidget, AIChatWidget and update templates.

Key benefit: Faster time to value. The template system and most widgets ship quickly while the three complex widgets get dedicated attention in a follow-up.

**Trade-offs:**

| Aspect          | Assessment                                                                                   |
| --------------- | -------------------------------------------------------------------------------------------- |
| Pros            | Fastest initial delivery; complex widgets get dedicated attention; reduced integration risk   |
| Cons            | Incomplete templates; EVM Analyst template is the most impacted; "Coming Soon" friction       |
| Complexity      | Low-Medium -- fewer widgets to integrate simultaneously                                       |
| Maintainability | Fair -- deferred widgets may require template updates later                                   |
| Performance     | Good -- same as other options for shipped widgets                                             |

---

## Comparison Summary

| Criteria           | Option 1: Sequential     | Option 2: Parallel Tracks | Option 3: Defer Complex    |
| ------------------ | ------------------------ | ------------------------- | -------------------------- |
| Development Effort | High (9 widgets + templates as one block) | Medium-High (parallel but coordination overhead) | Low-Medium (6 widgets + templates first) |
| UX Quality         | Complete on delivery     | Complete on delivery      | Partial (3 widgets deferred) |
| Flexibility        | Good                     | Good                      | Best (iterative delivery)  |
| Risk               | Medium (single delivery) | Medium-High (sync risk)   | Low (incremental)          |
| Best For           | Complete feature set in one shot | Faster with good coordination | Fastest value, phased rollout |

---

## Recommendation

**I recommend Option 3 with a modification: defer only AIChatWidget to Phase 5b, but ship MiniGanttWidget and ChangeOrderAnalyticsWidget in the initial Phase 5.**

Rationale:

1. **AIChatWidget is the only genuinely high-risk widget.** Embedding a full WebSocket-based chat session (with session sidebar, streaming state, agent activity panel, approval dialogs) inside a grid widget introduces lifecycle management complexity that warrants dedicated attention. The `ChatInterface` component has deep integration with `useStreamingChat`, session management, and the execution mode system -- wrapping it properly requires careful design, not a thin adapter.

2. **MiniGanttWidget and ChangeOrderAnalyticsWidget are medium complexity, not high.** MiniGanttWidget wraps the existing `GanttChart` component but may need a "compact mode" prop to reduce data density. ChangeOrderAnalyticsWidget wraps existing chart components (`SCurveChart`, `StatusDistributionChart`, `CostTrendChart`) that already exist in `features/change-orders/components/`. Both are straightforward adapter patterns.

3. **Templates are more useful with 8 of 9 widgets.** The three templates (PM Overview, EVM Analyst, Cost Controller) can be designed without AIChatWidget. None of the templates list AIChatWidget as a required widget. This means all three templates ship complete.

4. **HealthSummaryWidget is the only new UI component.** It should be implemented first since it has no existing component to wrap. However, the `components/explorer/charts/` directory already contains `BudgetUtilizationGauge`, `PerformanceRadar`, and `KPIStrip` that can inform the design. The aggregated SPI/CPI/SV display is conceptually similar to the Explorer's KPI strip.

**Alternative consideration:** Choose Option 1 if the project timeline allows a single complete delivery with no intermediate "Coming Soon" states. This avoids the overhead of managing two sub-phases and ensures the full widget catalogue is available at once.

---

## Decision Questions

1. **AIChatWidget complexity:** Should we defer AIChatWidget to Phase 5b, or is it acceptable to ship a simplified version (e.g., read-only message view without full session management) in Phase 5?

2. **MiniGanttWidget rendering mode:** The full Gantt chart renders with rich ECharts custom bar series. In a 6x3 grid cell, should we render a simplified timeline (e.g., only WBE-level bars, no cost element drilldown) or attempt to render the full chart with scroll/zoom? This affects both complexity and UX.

3. **Template seeding strategy:** Should templates be seeded via Alembic data migration (runs once, tracked in migration history) or via an application startup hook (runs every time, upsert behavior)? The migration approach is more auditable but less flexible for updates; the startup hook is more flexible but runs on every boot.

4. **HealthSummaryWidget scope:** The request says "aggregated SPI/CPI/SV with color-coded status." Should this be a read-only diagnostic display, or should it include actionable elements (e.g., click to drill down into the EVM Analyzer, click to see contributing cost elements)?

5. **Widget numbering alignment:** The request numbers widgets 8-16, implying widgets 1-7 come from earlier phases. Can you confirm the exact list of widgets delivered in Phases 1-4 so I can verify there are no gaps or overlaps in the catalogue?

---

## References

- Widget system research: `docs/03-project-plan/iterations/2026-04-06-widget-system/claude.md`, `perplexity.md`, `gemini.md`
- Main dashboard design: `docs/03-project-plan/iterations/2026-03-15-main-dashboard-design/00-analysis.md`
- EVM types and hooks: `frontend/src/features/evm/types.ts`, `frontend/src/features/evm/api/useEVMMetrics.ts`
- EVM components: `frontend/src/features/evm/components/EVMTimeSeriesChart.tsx`, `EVMGauge.tsx`, `EVMSummaryView.tsx`
- Gantt components: `frontend/src/features/schedule-baselines/components/GanttChart/GanttChart.tsx`
- Forecast hooks: `frontend/src/features/forecasts/api/useForecasts.ts`
- Change order components: `frontend/src/features/change-orders/components/` (ChangeOrderList, ChangeOrderAnalytics, SCurveChart, StatusDistributionChart)
- AI chat interface: `frontend/src/features/ai/chat/components/ChatInterface.tsx`
- Explorer charts (for HealthSummaryWidget reference): `frontend/src/components/explorer/charts/`
- Project summary card: `frontend/src/components/hierarchy/ProjectSummaryCard.tsx`
- Analysis prompt: `docs/04-pdca-prompts/analysis-prompt.md`
- Analysis template: `docs/04-pdca-prompts/_templates/00-analysis-template.md`
