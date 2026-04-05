This is excellent material to work with. Let me analyze all 11 screens systematically before defining the widget architecture.

From the screenshots, I can identify the following distinct UI surfaces in **Backcast**: Project Details, WBE tree structure, Project Schedule (Gantt), Explorer (split-panel tree + detail), Change Orders list, Cost Element detail (with sub-tabs: Overview/EVM, Forecasts, Schedule Baselines, Cost Registrations, Progress), and AI Chat. These map cleanly to a composable widget system.

Here is the full requirement analysis.

---

## Backcast — Composable Widget System: Requirement Analysis

### 1. Strategic Rationale

The current application follows a **fixed page-per-entity** paradigm: each entity (project, WBE, cost element) occupies its own dedicated route with a fixed tab layout. This is appropriate for simple data entry but it forces the user to navigate across multiple pages to answer cross-cutting questions — for example, comparing EVM metrics across WBEs, or reviewing cost registrations alongside a Gantt chart.

The migration to a **composable widget grid** — as implemented in Jira Dashboards, Notion, and Linear's custom views — allows each user or team to assemble the information density they need, in the layout that matches their workflow. For a project manager, that might be a full-screen EVM summary. For a cost controller, a side-by-side of budget status and cost registrations. The system remains the same; the composition changes.

---

### 2. Widget Catalogue

Widgets are derived from current screens cross-referenced with PMI's Earned Value Management and project performance reporting standards (PMBOK 7th edition, Practice Standard for EVM).

#### 2.1 Project-Level Widgets

**Project Header Card**
Displays project identity fields: code, name, status badge, start/end dates, duration. Serves as the anchor widget on any project dashboard. Compact variant (single row, suitable for top-of-page placement) and full variant. Maps to the current Project Details Overview section.

**Budget Status Widget**
Shows Budget (BAC), Actual Cost (AC), Remaining, and Used % with a progress bar and status label (Healthy / At Risk / Critical). Driven by the PMI cost performance baseline. Supports sparkline trend on the used % over time.

**EVM Summary Widget**
The core PMI performance reporting surface. Displays the four quadrants: Schedule Metrics (SPI, SV) and Cost Metrics (BAC, AC, CV, CPI). Each metric tile shows value, color-coded status (green/amber/red per configurable thresholds), and a tooltip with the PMI definition. An "Advanced" expansion opens a time-phased EVM chart (S-curve: PV vs EV vs AC) rendered in ECharts. This widget is the most information-dense in the system and must support both compact (4-tile summary) and expanded (full S-curve) modes.

**Cost Element Details Widget**
Editable detail form for a single cost element: code, name, description, budget, type, WBE assignment, branch, validity. Includes an inline Update action. Currently surfaced as the lower section of the cost element Overview tab.

#### 2.2 Work Breakdown Structure Widgets

**WBE Tree Widget**
A collapsible, searchable tree of the full WBE hierarchy (L1 → L2 → L3). Each node shows code, name, budget allocation, and branch. Clicking a node sets the active context for other widgets on the same dashboard (context propagation, see §4). Supports drag-to-reorder nodes within the same level. This maps to the current Structure tab and the left panel of the Explorer.

**WBE Summary Card**
A compact card summarising a single WBE: code, level badge, budget, parent, branch, and child WBE count. Used when the WBE tree widget is not present, or as a header above cost element grids.

**Cost Elements Grid Widget**
A filterable, sortable card grid of cost elements belonging to a WBE or project scope. Each card shows: type badge (Labor / Material / Equipment / Subcontract / Travel), code, budget, branch. Supports type-filter chips and sort controls. Maps to the "Cost Elements – L1 WBE 1" section in the WBE Details page.

#### 2.3 Scheduling Widgets

**Project Schedule (Gantt) Widget**
A full Gantt chart rendered in ECharts (custom bar series on a time axis). Rows correspond to WBEs and their cost elements. Supports zoom (day / week / month), today-line, baseline overlay, and row-level collapse. This is the most complex widget in terms of rendering and is the only one that should default to a full-width layout slot. Incorporates the PMI schedule baseline concept: baseline bars rendered as a lighter underlay behind actual bars.

**Schedule Baseline Widget**
A detail widget for a single cost element's schedule baseline: name, progression type (Linear / Gaussian S-Curve / Logarithmic), start date, end date, branch. Displays the PV calculation logic (PV = BAC × Progress) as a reference panel. Maps to the current Schedule Baselines tab.

#### 2.4 Financial Widgets

**Cost Registrations Widget**
A table of actual cost entries for a cost element or WBE scope: amount, quantity, unit, date, description. Shows total at the top. Supports search, sort, and pagination. Includes an "+ Add Cost" action. Maps to the Cost Registrations tab.

**Forecast Widget**
Displays the EAC (Estimate at Complete) for a cost element, with basis-of-estimate label and VAC (Variance at Completion). Includes an info panel explaining BAC, EAC, VAC, and ETC per PMI definitions. Maps to the Forecasts tab. One-forecast-per-cost-element constraint is displayed as an info banner.

#### 2.5 Progress Widgets

**Progress Tracker Widget**
Shows the latest progress percentage as a labeled progress bar with timestamp. Below, a paginated history table of progress entries: date, percentage (with mini bar), notes, reported-by user ID. Includes an "+ Add Progress" action and history clock icon for each entry. Maps to the Progress tab.

#### 2.6 Change Order Widgets

**Change Orders List Widget**
A table of change orders for a project: code, title, status badge (Draft / Submitted for Approval / Approved / Rejected), effective date, row actions (edit, history, delete). Includes a "+ New Change Order" button and supports tab switching between List View and Analytics View. Maps to the Change Orders tab.

**Change Order Analytics Widget**
A dashboard-within-a-widget showing change order distribution by status (donut chart, ECharts), cumulative value over time (line chart), and a summary of pending approval value. Feeds the Analytics View of the Change Orders screen.

#### 2.7 AI and Utility Widgets

**AI Chat Widget**
An embedded chat panel with session history sidebar, persona selector (Senior Project Manager, selectable from the header), and a multi-agent response renderer that displays subagent routing badges (e.g. `evm_analyst`, `project_manager`) inline in the conversation. Supports resizing between narrow (sidebar) and wide (main panel) layout modes.

**Quick Stats Bar**
A single-row strip of 4–6 KPI numbers drawn from the active project context: total budget, total AC, overall SPI, overall CPI, open change orders count, overall progress %. Designed to sit at the top of any dashboard as a persistent summary. Inspired by the PMI project performance dashboard concept.

---

### 3. Widget Properties and Capabilities (Universal Contract)

Every widget in the system implements the following universal interface, regardless of its content type.

**Identity and Configuration.** Each widget instance has a stable UUID, a widget type identifier, a human-editable title override, and a JSON configuration blob containing its data scope (e.g., which project, WBE, or cost element it is bound to). Configuration is persisted per dashboard and per user.

**Context Binding.** Widgets declare which context dimensions they consume: `projectId`, `wbeId`, `costElementId`, `branch`, `viewDate`. When a context provider widget (such as the WBE Tree) updates a dimension, all widgets on the same dashboard that declare that dimension as a dependency re-fetch their data automatically. This is the core mechanism replacing page-level routing.

**Size Classes.** Each widget declares its minimum and preferred size class: `1×1` (compact KPI tile), `2×1` (standard card), `2×2` (standard panel), `4×2` (wide panel), `full-width` (Gantt, Schedule). The grid system enforces these constraints during placement.

**Loading and Error States.** Every widget renders a skeleton screen during data loading (Ant Design Skeleton components with custom shimmer animation matching the widget's layout). Errors render an inline error state with retry action, never breaking the surrounding grid.

**Refresh Control.** Widgets support manual refresh (clock icon in header) and configurable auto-refresh intervals (off / 30s / 1min / 5min). The interval is stored per widget instance in its configuration.

**Expand and Collapse.** Every widget can be collapsed to show only its header bar (saving vertical space) and expanded to full-screen overlay mode (for detailed analysis). The expand action is a standard icon in the widget header.

**Drag and Resize.** In edit mode, widgets are draggable (react-grid-layout recommended as the grid engine) and resizable within their declared size constraints. Resize handles appear on all four edges and corners in edit mode only.

**Export.** Each widget exposes an export action: PNG snapshot (for charts), CSV (for tables), and JSON (for raw data). Implemented via ECharts' built-in `saveAsImage` for chart widgets and a custom CSV serialiser for table widgets.

---

### 4. Context Propagation Model

The composable system requires a lightweight **dashboard context bus** — a React context object at the dashboard root that holds the currently active `{projectId, wbeId, costElementId, branch, viewDate}` tuple. Any widget that acts as a context *provider* (WBE Tree, Cost Elements Grid) updates the bus on user interaction. Any widget that acts as a context *consumer* (EVM Summary, Cost Registrations, Progress Tracker) subscribes to relevant dimensions and re-renders on change.

This replaces URL-parameter-driven navigation for intra-dashboard interaction. Cross-dashboard navigation (e.g., opening a cost element in a dedicated view) remains URL-based.

The branch selector and the "Now / Historical" time selector — currently rendered in the global topbar — become first-class context dimensions on the bus, controllable both from the topbar and from within individual widgets.

---

### 5. Dashboard Composition: User Experience

**Entry Point.** From any project, the user accesses "Dashboards" from the project navigation tab. A project ships with one pre-built default dashboard ("Project Overview") that replicates the current fixed-screen layout. This ensures zero regression on day one.

**Edit Mode.** A persistent "Customize" button in the top-right of any dashboard enters edit mode. In edit mode, the grid overlays a subtle dotted guide pattern, drag handles appear on all widgets, and a widget palette slides in from the right. All other interactive elements (charts, links, forms) are disabled in edit mode to prevent accidental data changes.

**Widget Palette.** The palette presents all available widgets grouped by category (Project, WBE, Schedule, Financial, Progress, Change Orders, AI). Each widget entry shows a thumbnail preview, a short description, and its minimum size requirement. Drag from the palette to the grid to place; the grid snaps to the nearest valid position.

**Templates.** Users can save any dashboard as a template and apply it to other projects. Anthropic-supplied system templates include: "EVM Dashboard" (PMI-aligned: Quick Stats Bar + EVM Summary + Gantt + Cost Registrations), "Change Order Review" (Change Orders List + Change Order Analytics + Budget Status), and "Cost Element Deep Dive" (Cost Element Details + Forecast + Schedule Baseline + Progress Tracker + Cost Registrations).

**Persistence.** Dashboard layouts are saved per user per project in the backend. A "Reset to Default" action restores the system default layout. Shared dashboards (read-only views shared via link) are a V2 capability.

---

### 6. Visual System Requirements (React + Ant Design + ECharts)

**Grid Engine.** `react-grid-layout` for drag-drop-resize, configured with a 12-column grid, 8px row height unit, and 12px gutters. Breakpoints at 1280px (desktop), 960px (tablet), and 640px (mobile, single-column, no editing).

**Widget Shell Component.** A single `<WidgetShell>` React component wraps every widget. It renders the standardised header (title, subtitle, refresh icon, expand icon, drag handle), the loading/error overlays, and the content slot. Widget authors implement only the content; the shell handles all chrome.

**Ant Design Alignment.** Use Ant Design's `Card`, `Table`, `Badge`, `Tag`, `Skeleton`, `Tooltip`, and `Statistic` components as the baseline. Custom theme tokens override the default Ant Design palette to match Backcast's teal/blue primary with neutral grays. All interactive states (hover, focus, active) must respect the Ant Design token system — no ad-hoc color overrides.

**ECharts Configuration Standard.** All charts share a common ECharts base theme object (colors, font family, grid padding, tooltip style, legend position) defined once and injected via the ECharts theme registration API. This ensures visual consistency across the EVM S-curve, Gantt, and Change Order analytics charts.

**Typography.** A refined, geometric sans-serif (e.g., DM Sans or Geist) for UI text, paired with tabular-nums variant for all monetary and percentage values to ensure column alignment. Font loaded via Google Fonts with `font-display: swap`.

**Motion.** Widget mount animation: fade-in with 4px upward translate, 200ms ease-out, staggered by 50ms per widget in reading order. Skeleton shimmer uses a CSS linear-gradient animation. No layout-shift animations during data refresh (data updates in-place, not re-mount).

**Apple-Style UX Principles Applied.** Surfaces feel weightless: minimal borders, generous internal padding, soft shadows (`box-shadow: 0 1px 3px rgba(0,0,0,0.08), 0 4px 12px rgba(0,0,0,0.06)`). Every destructive action (delete widget, reset layout) requires a two-step confirmation popover. Contextual menus replace modal dialogs wherever possible. State transitions are always animated, never instantaneous.

---

### 7. Migration Strategy

**Phase 1 — Widget Infrastructure.** Implement the `WidgetShell`, the context bus, and `react-grid-layout` integration. Build the dashboard save/load API. No existing screen is removed; new dashboard route coexists with existing fixed routes.

**Phase 2 — Widget Extraction.** Port existing screen sections to widgets one by one, starting with the highest-value, lowest-complexity candidates: Budget Status, EVM Summary, Cost Registrations, Progress Tracker. Each ported widget is immediately available in the palette.

**Phase 3 — Advanced Widgets.** Implement Gantt (highest complexity), AI Chat widget, and Change Order Analytics. Build the template system.

**Phase 4 — Deprecation.** Once all existing functionality is covered by widgets and the default dashboard template matches the current fixed-screen experience, the old fixed routes can be marked deprecated and eventually removed in a later release.

---

This analysis provides a complete, PMI-aligned, production-grade foundation for the migration. The next step would be implementing the `WidgetShell` component and the dashboard context bus as the core infrastructure layer. Would you like me to build those first, or start with a specific high-priority widget?