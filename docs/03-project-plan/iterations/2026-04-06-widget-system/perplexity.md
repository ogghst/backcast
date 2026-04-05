Yes — your current fixed pages can be migrated to a composable widget system, and the screenshots already suggest a strong domain model for it: project overview, WBS, cost elements, EVM, forecasts, progress history, and change orders can become reusable dashboard widgets instead of page-specific layouts. A production-grade migration should separate page composition, widget rendering, widget data contracts, and KPI semantics so users can configure views without breaking reporting consistency or PMI-aligned calculations.  [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/images/19849242/da584ccb-0adb-4227-99f0-21e49c10bca2/1000231787.jpeg)

## Target outcome

The target product should behave like a structured, enterprise dashboard builder rather than a free-form website editor: users choose widgets, place them in a responsive grid, configure scope and filters, save named views, and share role-based dashboards. Jira’s model is relevant here because dashboards are built from configurable gadgets, added in edit mode, then customized per data source and refresh behavior.  [support.atlassian](https://support.atlassian.com/jira-software-cloud/docs/add-and-customize-gadgets/)

For your application, the key difference from Jira should be stronger domain integrity: widgets must stay tied to PMI-style project controls concepts such as PV, EV, AC, BAC, CPI, SPI, EAC, ETC, VAC, trend/forecast, and exception reporting, so users can rearrange presentation without redefining business meaning. PMI emphasizes dashboards should answer current cost and schedule status, forecast completion cost/date, identify emerging problems, and show causes of variance, which maps directly to your widget strategy.  [pmi](https://www.pmi.org/learning/library/tools-projects-digital-dashboard-performance-8045)

## Current screen analysis

Your current screens appear to include these functional areas: project details, WBS details, cost element lists and details, EVM summaries, forecasting, progress history, AI/chat assistance, and change orders. This means the migration should preserve those business capabilities while decoupling them from single-purpose screens and re-expressing them as reusable information modules.  [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/images/19849242/da584ccb-0adb-4227-99f0-21e49c10bca2/1000231787.jpeg)

A practical migration rule is: if a screen section can stand alone with its own title, filters, actions, and data loading, it should likely become a widget; if it is only navigation or context framing, it should remain shell layout. From the screenshots, EVM summary cards, cost breakdown tables, progress history, forecast panels, change order lists, and WBS status blocks are all good widget candidates.  [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/images/19849242/da584ccb-0adb-4227-99f0-21e49c10bca2/1000231787.jpeg)

## Product principles

The UX should feel calm, precise, and intentional, with compact typography, neutral surfaces, one accent color, and strong information hierarchy because dashboard UIs work best when clarity dominates decoration. Production-grade web app guidance also favors sidebar-based navigation, compact scale, visible state, progressive disclosure, and URL-reflective state rather than oversized, theatrical UI.  [support.atlassian](https://support.atlassian.com/jira-software-cloud/docs/add-and-customize-gadgets/)

For an Apple-style feel, translate that into: low visual noise, exact spacing, predictable motion, rich but restrained micro-interactions, excellent empty/loading states, and almost no “configuration anxiety.” The builder must feel safe: users should always know what they are editing, what data a widget uses, and how to undo layout changes.  [goretro](https://www.goretro.ai/post/jira-dashboard)

## Core architecture

Use four layers in the front end:

| Layer | Responsibility |
|---|---|
| App shell | Navigation, permissions, global filters, responsive breakpoints |
| Dashboard/page engine | Grid layout, widget registry, saved layouts, edit/view mode |
| Widget runtime | Rendering, widget chrome, loading/error/empty states, config panels |
| Data/query layer | Widget-specific queries, caching, KPI definitions, refresh, filter propagation |

This separation matters because Jira-style composition works only when widget placement is independent from widget data semantics and both are independent from page routing. Atlassian’s gadget model also reinforces the need for explicit add/edit/configure flows rather than mixing composition with normal consumption.  [support.atlassian](https://support.atlassian.com/jira-software-cloud/docs/add-and-customize-gadgets/)

## Composition model

Define a page as a saved composition of widgets, not as a React route with hardcoded sections. A page should store layout, widget instances, widget configuration, visibility rules, and responsive variants, while the widget definition itself stays in a central registry.  [support.atlassian](https://support.atlassian.com/jira-software-cloud/docs/add-and-customize-gadgets/)

Recommended entities:

- Dashboard: named user or shared page.
- Layout version: immutable snapshot for rollback/audit.
- Widget instance: one placed widget with its own config.
- Widget definition: reusable component type.
- Data source binding: project, WBS node, cost account, portfolio, baseline, period.
- View context: page-level filters inherited by widgets.

## Widget taxonomy

You should define widgets by job, not by current page name. A solid taxonomy for your domain is:

| Family | Purpose | Examples |
|---|---|---|
| Summary | At-a-glance KPIs | Project health, BAC/AC/EV snapshot, milestone status |
| Trend | Time-series visibility | EV/PV/AC trend, CPI/SPI trend, forecast trend |
| Diagnostic | Why performance changed | Variance waterfall, top overruns, root-cause notes |
| Breakdown | Structured drilldown | WBS cost tree, cost element list, change order table |
| Forecast | Predict likely outcome | EAC/ETC/VAC cards, completion date forecast |
| Action | Prompt next step | Risks needing review, pending approvals, open changes |
| Narrative | Human explanation | Executive summary, PM commentary, AI-generated digest |
| Utility | Cross-page controls | Filter bar, baseline selector, date range, saved view picker |

PMI-oriented dashboard reporting is strongest when it combines current status, forecast, and early warning indicators, so the system should encourage a balance of summary, trend, and exception widgets rather than letting users build pages made only of decorative KPI cards.  [pmi](https://www.pmi.org/learning/library/tools-projects-digital-dashboard-performance-8045)

## Recommended widgets

Below is the initial production widget set I would define for v1.

### Executive widgets

- Project status card: name, status, sponsor/manager, phase, baseline date, last update.  [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/images/19849242/b34a36e5-6277-47e1-830e-c7c6eb9e5ec1/1000231776.jpeg)
- Executive KPI strip: BAC, EV, AC, PV, CV, SV, CPI, SPI, EAC, VAC. PMI sources consistently identify these as core EVM measures.  [pmi](https://www.pmi.org/learning/library/earned-value-wbs-performance-measurement-baseline-7465)
- Health summary widget: cost health, schedule health, scope/change health, data freshness, confidence level.  [pmi](https://www.pmi.org/learning/library/tools-projects-digital-dashboard-performance-8045)
- Narrative summary widget: concise autogenerated explanation of key movements and exceptions.  [pmi](https://www.pmi.org/learning/library/tools-projects-digital-dashboard-performance-8045)

### EVM widgets

- EVM summary cards.
- EV/PV/AC trend chart.
- CPI/SPI trend chart.
- Variance widget: CV and SV with thresholds and color states.
- Forecast widget: EAC, ETC, VAC, completion date forecast.
- Performance threshold widget: CPI/SPI against warning bands.
- Baseline comparison widget: current baseline vs prior baseline.

PMI reporting focuses on comparing EV with AC and EV with PV, plus forecast-at-completion logic, so these widgets should be first-class and reusable at project, WBS, or cost account level.  [pmi](https://www.pmi.org/learning/library/tools-projects-digital-dashboard-performance-8045)

### Cost widgets

- Cost element table.  [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/images/19849242/7124c7e1-5131-4443-9784-3401c6968512/1000231782.jpeg)
- Cost breakdown tree by WBS / cost account.  [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/images/19849242/02fea307-7c2e-41cf-9880-8e49d03a00f6/1000231783.jpeg)
- Top cost variances list.
- Burn profile chart by period.
- Commitments vs actuals widget.
- Change order cost impact widget.  [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/images/19849242/cd3f1f81-6109-47de-8958-2b3db6e2a7f9/1000231784.jpeg)
- Cost distribution donut or treemap.

### Schedule/progress widgets

- Progress percent card.
- Planned vs actual progress chart.
- Milestone status widget.
- Critical slippage alerts.
- Progress history table or timeline.  [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/images/19849242/59bf7ce3-bf91-4f09-a0e9-fcd8ca801e1c/1000231786.jpeg)
- Earned schedule extension widget if you support it later. PMI-adjacent sources note earned schedule as a useful extension for schedule realism.  [cappmpl](https://www.cappmpl.com/training/pmi-best-practices/evm)

### Scope/WBS widgets

- WBS tree explorer.  [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/images/19849242/02fea307-7c2e-41cf-9880-8e49d03a00f6/1000231783.jpeg)
- WBS node summary card.
- Child element rollup widget.
- Scope completion heatmap.
- Scope change log.

### Change/risk/action widgets

- Change orders table.  [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/images/19849242/cd3f1f81-6109-47de-8958-2b3db6e2a7f9/1000231784.jpeg)
- Pending approvals widget.
- Risk and issue watchlist.
- Action items due soon.
- Exception queue: widgets can publish exceptions into a shared action list.

### Collaboration widgets

- PM notes.
- Audit/history feed.
- AI assistant panel for contextual explanation and next-step suggestions.  [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/images/19849242/da584ccb-0adb-4227-99f0-21e49c10bca2/1000231787.jpeg)
- Activity feed.

## Widget properties

Every widget instance should support a standard set of properties. This is one of the most important parts of the migration.

### Identity and lifecycle

- `id`
- `type`
- `version`
- `title`
- `description`
- `ownerScope` (system / admin / user / template)
- `createdBy`, `updatedBy`
- `createdAt`, `updatedAt`

### Layout

- `x`, `y`, `w`, `h`
- `minW`, `minH`, `maxW`, `maxH`
- `resizable`, `draggable`
- `breakpointLayouts` for desktop/tablet/mobile
- `collapsed`, `hidden`
- `fullscreenCapable`

### Data binding

- `entityType`: project, portfolio, WBS node, cost element, contract, change order
- `entityId`
- `baselineId`
- `dateRange`
- `timeBucket`: day/week/month
- `filters`
- `groupBy`
- `comparisonMode`
- `refreshPolicy`

### Behavior

- `drilldownTarget`
- `actions`
- `exportFormats`
- `permissions`
- `thresholds`
- `alertRules`
- `supportsGlobalFilters`
- `supportsCrossFiltering`

### Presentation

- `displayVariant`: card, chart, table, list, narrative
- `density`: compact, comfortable
- `showHeader`, `showFooter`
- `showLastUpdated`
- `showDefinition`
- `colorMode`
- `emptyStateMode`

## Mandatory widget capabilities

Every production widget should support these capabilities by contract, not by optional implementation:

- Loading state with skeleton.
- Empty state with guidance.
- Partial data state.
- Error state with retry.
- Stale-data indicator.
- Export action where relevant.
- Inspect/configure action.
- Drilldown action.
- Fullscreen or focus mode for data-heavy widgets.
- Keyboard accessibility.
- Responsive rendering.
- Telemetry events.

This aligns with strong web app practice: visible state, no ambiguous failures, and explicit user control.  [support.atlassian](https://support.atlassian.com/jira-software-cloud/docs/add-and-customize-gadgets/)

## Widget data contract

Use a normalized widget contract in React so all widgets can be hosted by the same runtime.

Suggested shape:

```ts
type WidgetDefinition<TConfig, TQuery, TData> = {
  type: string;
  displayName: string;
  category: WidgetCategory;
  defaultSize: { w: number; h: number };
  minSize: { w: number; h: number };
  capabilities: WidgetCapabilities;
  configSchema: ZodSchema<TConfig>;
  querySchema: ZodSchema<TQuery>;
  useData: (ctx: WidgetDataContext, config: TConfig) => WidgetDataResult<TData>;
  render: React.FC<WidgetRenderProps<TConfig, TData>>;
};
```

That lets you enforce a stable registry, version widgets safely, and keep composition metadata separate from rendering logic. It also gives you a migration path from today’s page components: wrap current sections into widget definitions first, then improve them incrementally.  [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/images/19849242/7124c7e1-5131-4443-9784-3401c6968512/1000231782.jpeg)

## PMI-aligned data recommendations

PMI-oriented dashboarding should prioritize answering a small set of management questions: current status in cost and schedule, forecast completion, emerging issues, causes of variance, and value achieved for money spent. That means your standard dashboard templates should always expose some combination of PV, EV, AC, BAC, CV, SV, CPI, SPI, EAC, ETC, and VAC at the selected control level.  [pmi](https://www.pmi.org/learning/library/tools-projects-digital-dashboard-performance-8045)

Recommended KPI hierarchy:

- Primary KPI cards: EV, AC, PV, CPI, SPI.  [pmi](https://www.pmi.org/learning/library/tools-projects-digital-dashboard-performance-8045)
- Forecast cards: EAC, ETC, VAC, projected finish date.  [pmi](https://www.pmi.org/learning/library/tools-projects-digital-dashboard-performance-8045)
- Diagnostic visuals: EV vs PV vs AC trend, variance contributors, top offending WBS/cost accounts.  [pmi](https://www.pmi.org/learning/library/tools-projects-digital-dashboard-performance-8045)
- Context metrics: percent complete, baseline revision count, approved change impact, data date, confidence/quality status.  [linkedin](https://www.linkedin.com/pulse/balanced-scorecard-projects-performance-dashboard-samman-pmp-evp-gpm)

Important PMI-style data rules:

- Keep formula ownership centralized, never inside widget-local code.  [pmi](https://www.pmi.org/learning/library/earned-value-wbs-performance-measurement-baseline-7465)
- Distinguish current-period values from cumulative values.  [pmi](https://www.pmi.org/learning/library/tools-projects-digital-dashboard-performance-8045)
- Always show “as of” date and baseline source.  [pmi](https://www.pmi.org/learning/library/tools-projects-digital-dashboard-performance-8045)
- Allow drilldown from project to control account/WBS level because EV comparison can be done at both project and detailed levels.  [pmi](https://www.pmi.org/learning/library/tools-projects-digital-dashboard-performance-8045)
- Provide narrative interpretation for non-expert users because PMI notes EVM terminology can initially be intimidating.  [pmi](https://www.pmi.org/learning/library/tools-projects-digital-dashboard-performance-8045)

## Page composition UX

The composition experience should feel like editing a dashboard, not editing a spreadsheet. Jira’s add-gadget/edit-save model is a good baseline: browse widgets, add one, configure it, save, and immediately see the result.  [support.atlassian](https://support.atlassian.com/jira-software-cloud/docs/add-and-customize-gadgets/)

Recommended UX flow:

1. User enters “Edit layout.”
2. Grid shows subtle drop zones and resize handles.
3. Left drawer opens widget library with categories and search.
4. User drags or taps “Add” to place widget.
5. Inline configuration sheet appears immediately.
6. Widget renders preview with real or sample data.
7. User saves draft or publishes layout.
8. System preserves undo stack and autosaves draft.

### Builder modes

Use three explicit modes:

- View mode: no layout affordances, only consume data.
- Personalize mode: user edits their own copy or preferences.
- Admin/template mode: edit shared dashboards and role templates.

That separation avoids the common enterprise problem where every page feels half-editable and unsafe.

## Grid system

Use a responsive CSS grid abstraction with breakpoint-specific layout persistence.

Recommended behavior:
- Desktop: 12 columns.
- Tablet: 8 columns.
- Mobile: 4 columns or one-column stacked priority mode.
- Widgets store separate coordinates per breakpoint.
- Mobile should not merely shrink desktop; it should reorder by priority.

For mobile and tablet, composition should be constrained. Users can still choose which widgets appear, but freeform drag-and-drop on phones should be replaced by reorder, pin, hide, and size presets because fine drag interactions are fragile on small screens. Good mobile dashboard design collapses, stacks, and simplifies rather than shrinking every desktop pattern.  [support.atlassian](https://support.atlassian.com/jira-software-cloud/docs/add-and-customize-gadgets/)

## Responsive rules

For PC, tablet, and mobile, define rules at the platform level rather than per widget ad hoc.

### Desktop

- Full composition experience.
- Drag, resize, multi-column layouts.
- Side inspector panel.
- Rich tables, split panes, more simultaneous context.

### Tablet

- Simplified composition.
- Larger handles, fewer columns, bottom sheet configuration.
- Two-pane interaction only when landscape.

### Mobile

- View-first.
- Stacked widgets ordered by importance.
- Edit through “Manage page” sheet, not live drag grid.
- Tables transform into cards or horizontal scroll with strong hints.
- Primary actions move into bottom sheets or sticky action areas.

## UX quality bar

To get the “rock solid, apple-style” feel, focus on these traits:

- Motion is calm and short, about state continuity, never spectacle.
- Every widget moves with spring-like precision when placed or resized.
- No jitter while data loads.
- Numbers animate subtly when values change.
- Headers stay visually quiet; content does the work.
- Hover is informative on desktop, never required.
- Touch targets are generous on tablet/mobile.
- Selection, focus, and active states are extremely clear.

The product should feel “inevitable,” meaning each control appears exactly where a user expects it, with almost no surprise except delight.

## Widget chrome

All widgets should share a common shell:

- Title
- Optional subtitle/context
- Status chips
- Last updated
- Header actions: inspect, filter, export, expand, more
- Body
- Footer for drilldown or provenance

Keep chrome minimal and consistent so users learn one mental model across all widgets. The screenshot set currently mixes page-level and section-level structures; the new shell should normalize that.  [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/images/19849242/7124c7e1-5131-4443-9784-3401c6968512/1000231782.jpeg)

## Interaction patterns

Recommended interactions:

- Drag to place; snap instantly to grid.
- Resize with live ghost preview, then commit.
- Cross-widget filter broadcast, optional per widget.
- Click KPI card to inspect formula, trend, and contributing items.
- Open configuration in side panel on desktop, bottom sheet on mobile/tablet.
- Support undo after delete/remove.
- Save as personal view, shared team view, or template.

Do not rely on hidden gestures. Jira-style configurability works because actions are explicit and discoverable.  [support.atlassian](https://support.atlassian.com/jira-software-cloud/docs/add-and-customize-gadgets/)

## Permissions and governance

A dashboard builder becomes messy fast without governance. You need:

- System widgets vs custom widgets distinction.
- Role-based widget availability.
- Personal dashboards vs shared dashboards vs locked executive dashboards.
- Template inheritance with local overrides.
- Audit trail for shared layout changes.
- Widget deprecation/version migration policy.

This is especially important in project controls because KPI semantics must remain trustworthy even when layouts are personalized. PMI-style reporting depends on consistent interpretation of baseline and EVM values.  [pmi](https://www.pmi.org/learning/library/tools-projects-digital-dashboard-performance-8045)

## Migration strategy

Do this in phases.

### Phase 1

Create the widget platform without changing business logic:
- Widget registry.
- Widget shell.
- Dashboard layout model.
- Saved page model.
- Wrap existing page sections into widgets.

### Phase 2

Migrate the most reusable areas:
- EVM summary.
- Cost element tables.
- Change orders.
- Progress history.
- WBS summary blocks.

### Phase 3

Introduce composition UX:
- Add widget.
- Configure widget.
- Save personal/shared views.
- Responsive layout persistence.

### Phase 4

Standardize KPI services:
- Central formulas.
- Threshold engine.
- narrative/explanation service.
- export service.

### Phase 5

Optimize for excellence:
- Widget virtualization.
- optimistic layout editing.
- telemetry-driven improvement.
- mobile-first personalization patterns.

## Technical recommendations for React, AntD, ECharts

For your stack:

- Use `react-grid-layout` or a similar mature grid engine for desktop/tablet composition.
- Build a typed `WidgetRegistry`.
- Use AntD tokens selectively; override defaults heavily to reduce “stock AntD” feel.
- Use ECharts only inside chart widgets, never as page structure.
- Centralize theme tokens and spacing system outside widget implementations.
- Use React Query or TanStack Query for widget data orchestration and cache sharing.
- Use Zod for widget config schemas and migration/versioning.

AntD is strong for drawers, forms, popovers, tables, segmented controls, and responsive sheets, but to achieve a refined visual result you should reduce borders, tune radii carefully, use compact density, and standardize header/tool areas so widgets do not look like generic Ant cards.

## Non-functional requirements

Your basis document should include these hard requirements:

- Fast initial render with skeletons.
- Independent widget loading failure isolation.
- No full-page crash from one broken widget.
- Autosave draft layouts.
- Undo/redo for composition actions.
- URL-addressable dashboard state.
- Keyboard accessibility for widget actions.
- Touch-friendly edit flows on tablet/mobile.
- Versioned layouts and widget contracts.
- Exportable KPI visuals and tables.
- Observability on widget load time, query failure, and interaction friction.

## Suggested MVP templates

Ship templates first, then full blank-canvas freedom.

- Executive Project Overview
- Cost Control
- EVM Analysis
- WBS Control Board
- Change Management
- Mobile Field Summary

This mirrors how Jira offers customization but still benefits from recognizable dashboard conventions.  [support.atlassian](https://support.atlassian.com/jira-software-cloud/docs/add-and-customize-gadgets/)

## Acceptance criteria

A migrated system is successful when:

- A user can replace today’s fixed summary page with a saved layout of reusable widgets.  [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/images/19849242/36ef6b1a-9625-4724-a20c-cc48231370b3/1000231778.jpeg)
- The same EVM widget works at project, WBS, and cost-element scope.  [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/images/19849242/7124c7e1-5131-4443-9784-3401c6968512/1000231782.jpeg)
- KPI calculations remain consistent regardless of page layout.  [pmi](https://www.pmi.org/learning/library/tools-projects-digital-dashboard-performance-8045)
- Desktop, tablet, and mobile each get intentional layouts rather than scaled-down desktop.  [support.atlassian](https://support.atlassian.com/jira-software-cloud/docs/add-and-customize-gadgets/)
- Shared executive dashboards can be governed while personal views remain flexible.  [alphaservesp](https://www.alphaservesp.com/blog/jira-gadgets-create-and-customize-gadgets-in-jira-dashboard)
- Editing a page feels safe, reversible, and fast.  [goretro](https://www.goretro.ai/post/jira-dashboard)

## Recommended next deliverables

I’d suggest producing these artifacts next:

- Widget inventory and mapping from current screens.
- Domain KPI dictionary with PMI-aligned formulas and definitions.
- Dashboard/page JSON schema.
- Widget definition TypeScript interface.
- Responsive layout rules and breakpoint behavior.
- UX flows for add, configure, save, share, and mobile manage-page.
- Design system spec for your React + AntD implementation.

If you want, I can turn this into a structured migration specification in Markdown or DOC format with:
1. domain model,
2. widget catalog,
3. JSON schemas,
4. React component architecture,
5. UX flows and acceptance criteria.