# Dashboard & Widgets — User Guide

**Last updated:** 2026-04-08

A step-by-step introductory guide to the Backcast project dashboard and its widget system. Walks through login, navigation, and every feature available on the dashboard page.

---

## Table of Contents

- [1. Logging In](#1-logging-in)
- [2. Opening a Dashboard](#2-opening-a-dashboard)
- [3. Dashboard Overview](#3-dashboard-overview)
- [4. The Widget Catalog](#4-the-widget-catalog)
- [5. Entering Edit Mode](#5-entering-edit-mode)
- [6. Adding Widgets](#6-adding-widgets)
- [7. Rearranging Widgets](#7-rearranging-widgets)
- [8. Resizing Widgets](#8-resizing-widgets)
- [9. Configuring a Widget](#9-configuring-a-widget)
- [10. Removing a Widget](#10-removing-a-widget)
- [11. Saving and Discarding Changes](#11-saving-and-discarding-changes)
- [12. Cross-Widget Interaction](#12-cross-widget-interaction)
- [13. Time Travel and Branches](#13-time-travel-and-branches)
- [14. Dashboard Templates](#14-dashboard-templates)
- [15. Auto-Save Behavior](#15-auto-save-behavior)
- [16. Navigation Guards](#16-navigation-guards)
- [17. Fullscreen Mode](#17-fullscreen-mode)
- [18. Exporting Widget Data](#18-exporting-widget-data)
- [19. Undo and Redo](#19-undo-and-redo)
- [20. Auto-Refresh](#20-auto-refresh)
- [21. Mobile and Tablet Layout](#21-mobile-and-tablet-layout)
- [22. Troubleshooting](#22-troubleshooting)

---

## 1. Logging In

1. Open your browser and navigate to the Backcast application URL (default: `http://localhost:5173`).
2. You will be automatically redirected to the **Login** page (`/login`).
3. Enter your **email** and **password** in the login form.
4. Click **Log In**.
5. On success, you are redirected to the home page (`/`).

> If you do not have an account, contact your system administrator.

---

## 2. Opening a Dashboard

Each project has its own customizable dashboard. To access it:

1. From the home page or sidebar, navigate to **Projects** (`/projects`).
2. Click on the project you want to view. This opens the project's **Overview** tab.
3. In the project's tab navigation, click **Dashboard**.

The URL pattern is: `/projects/:projectId/dashboard`

> **First time?** If no custom dashboard exists for you on this project, the system loads the default **Project Overview** template — a pre-configured layout with 8 widgets covering project KPIs, budget, variance, and more.

---

## 3. Dashboard Overview

The dashboard page presents your project data as a collection of widgets on a responsive grid. Here is what you see:

```
┌─────────────────────────────────────────────────────────────┐
│ Toolbar: [Dashboard Name ▼]    [Customize] [Settings ⚙]    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────┐    │
│  │ Project      │ │ Quick Stats  │ │ EVM Summary      │    │
│  │ Header       │ │ Bar          │ │                  │    │
│  └──────────────┘ └──────────────┘ └──────────────────┘    │
│                                                             │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────┐    │
│  │ Budget       │ │ Variance     │ │ WBE Tree         │    │
│  │ Status       │ │ Chart        │ │                  │    │
│  └──────────────┘ └──────────────┘ └──────────────────┘    │
│                                                             │
│  ┌──────────────┐ ┌─────────────────────────────────────┐  │
│  │ Health       │ │ Cost Registrations                  │  │
│  │ Summary      │ │                                     │  │
│  └──────────────┘ └─────────────────────────────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Toolbar (top bar):**
- **Dashboard name** — displayed at the left. Click to rename.
- **Template selector** — dropdown to switch between saved layouts or templates.
- **Customize button** — enters edit mode for adding, removing, and rearranging widgets.

---

## 4. The Widget Catalog

Backcast ships with **15 widget types** organized into 5 categories:

| Category | Widgets | Purpose |
|----------|---------|---------|
| **Summary** | Project Header, Quick Stats Bar, EVM Summary, Budget Status, Health Summary | At-a-glance KPIs and single-value metrics |
| **Trend** | EVM Trend Chart, Forecast | Time-series analysis and forward-looking projections |
| **Diagnostic** | Variance Chart, EVM Efficiency Gauges, Change Order Analytics | Variance analysis and root-cause identification |
| **Breakdown** | WBE Tree, Mini Gantt | Hierarchical drilldowns and timeline views |
| **Action** | Cost Registrations, Progress Tracker, Change Orders List | Interactive data tables you can act on |

### What each widget shows

| Widget | Description |
|--------|-------------|
| **Project Header** | Project name, status badge, start/end dates. A compact identity bar. |
| **Quick Stats Bar** | Counts of WBEs, cost elements, cost registrations, and change orders. |
| **EVM Summary** | Core Earned Value metrics: BAC, AC, EV, EAC, CPI, SPI, CV, SV, TCPI, VAC. |
| **Budget Status** | Bar or pie chart comparing Budget at Completion (BAC), Actual Cost (AC), Earned Value (EV), and Estimate at Completion (EAC). |
| **Health Summary** | Color-coded health indicators based on CPI/SPI performance thresholds. |
| **EVM Trend Chart** | Line chart tracking EVM metrics over time — useful for spotting trends. |
| **Forecast** | Projections: Estimate at Completion (EAC), Estimate to Complete (ETC), Variance at Completion (VAC). |
| **Variance Chart** | Cost Variance (CV) and Schedule Variance (SV) visualization. |
| **EVM Efficiency Gauges** | Dual dial gauges for CPI and SPI — quick visual check of project health. |
| **Change Order Analytics** | Distribution charts for change orders by status, type, and impact. |
| **WBE Tree** | Interactive Work Breakdown Element hierarchy. Click a node to scope other widgets. |
| **Mini Gantt** | Compact Gantt timeline of project work packages and milestones. |
| **Cost Registrations** | Table of cost entries with filtering, sorting, and pagination. |
| **Progress Tracker** | Table of progress reporting entries with status indicators. |
| **Change Orders List** | Queue of change orders with status, priority, and quick actions. |

---

## 5. Entering Edit Mode

To add, remove, move, or resize widgets, you must enter **edit mode**:

1. Click the **Customize** button in the toolbar.
2. The dashboard background changes to a dotted grid pattern — this confirms you are in edit mode.
3. Each widget displays an action bar with buttons: **Move**, **Resize**, **Settings**, **Delete**.

> Changes made in edit mode are **not saved** until you click **Done**. You can always discard changes by clicking **Cancel**.

---

## 6. Adding Widgets

1. While in edit mode, click the **+ Add Widget** button (appears in the toolbar area).
2. A **Widget Palette** modal opens, showing all available widgets grouped by category.
3. Browse or scan the categories:
   - **Summary** — KPIs and metrics cards
   - **Trend** — time-series and forecasts
   - **Diagnostic** — variance analysis tools
   - **Breakdown** — hierarchies and timelines
   - **Action** — data tables
4. Click on a widget card to add it to your dashboard.
5. The widget appears on the grid with its default size and an auto-computed position (first available row).
6. Repeat to add more widgets.

---

## 7. Rearranging Widgets

1. In edit mode, click the **Move** button (arrows icon) on the widget you want to reposition.
2. The widget becomes draggable — click and drag it to the desired position on the grid.
3. Other widgets automatically shift to accommodate the new position.
4. Release the widget to drop it.
5. The interaction mode resets after the drop is complete.

> The grid uses a **12-column layout**. Widgets snap to grid cells and cannot overlap.

---

## 8. Resizing Widgets

1. In edit mode, click the **Resize** button (expand icon) on the widget you want to resize.
2. A resize handle appears at the bottom-right corner of the widget.
3. Drag the handle to change the widget's width and height.
4. Release to apply the new size.

> Each widget type has **minimum size constraints** — you cannot shrink a widget below its readable minimum. For example, chart widgets require at least 3 columns wide and 2 rows tall.

---

## 9. Configuring a Widget

Many widgets have configurable options that control what data they display and how.

1. In edit mode, click the **Settings** button (gear icon) on the widget.
   - Alternatively, in view mode, hover over the widget and click the floating gear icon.
2. A **configuration drawer** slides in from the right side of the screen.
3. Adjust the available settings. Common options include:
   - **Entity Scope** — whether the widget shows data at Project, WBE, or Cost Element level.
   - **Chart Type** — switch between bar, pie, or line visualizations.
   - **Display Toggles** — show/hide specific data points or labels.
4. Changes preview in real-time on the widget behind the drawer.
5. Click **Apply** to confirm your changes, or **Cancel** to revert.

> Configuration changes in view mode are saved automatically (after a short debounce). In edit mode, they are saved when you click **Done**.

### Available configuration options per widget

| Widget | Configurable Options |
|--------|---------------------|
| EVM Summary | Entity scope (Project / WBE / Cost Element) |
| Budget Status | Entity scope, Chart type (Bar / Pie) |
| Forecast | Entity scope |
| Variance Chart | Entity scope, Chart type |
| Cost Registrations | Page size, Entity scope |
| Progress Tracker | Page size, Entity scope |
| WBE Tree | Expand depth, Show cost elements |

---

## 10. Removing a Widget

1. In edit mode, click the **Delete** button (trash icon) on the widget.
2. The widget is immediately removed from the grid.
3. If removed by mistake, click **Cancel** to discard all edit-mode changes and restore the previous layout.

---

## 11. Saving and Discarding Changes

When you are satisfied with your layout in edit mode:

- Click **Done** — saves all changes (widget additions, removals, moves, resizes, and config updates) to the backend. The dashboard exits edit mode.
- Click **Cancel** — discards all changes made since entering edit mode and restores the previous layout. The dashboard exits edit mode.

> **Done** triggers a single save operation that persists the entire widget layout to the server.

---

## 12. Cross-Widget Interaction

Widgets on the dashboard are not isolated — they communicate through a **context bus**:

1. Add a **WBE Tree** widget to your dashboard.
2. Click on any node in the tree (a WBE or Cost Element).
3. All other widgets on the dashboard automatically update to show data scoped to the selected entity.

**Example flow:**
- Click a WBE in the WBE Tree
- The EVM Summary widget switches from project-level metrics to that WBE's metrics
- The Budget Status chart updates to show that WBE's budget breakdown
- The Variance Chart re-scopes to that WBE's variances

To reset to project-level view, click the project root node in the WBE Tree.

---

## 13. Time Travel and Branches

The dashboard integrates with the **Time Machine** for versioned data exploration:

- **Branch selector** — switch between the main branch and any change order branch to see how proposed changes affect metrics.
- **As-of date** — pick a historical date to see the project state as it was on that date.

All widgets on the dashboard react to Time Machine changes automatically. For example, selecting a different branch will re-fetch EVM metrics for that branch's scope.

---

## 14. Dashboard Templates

The system ships with **3 predefined templates**:

| Template | Widgets | Best For |
|----------|---------|----------|
| **Project Overview** | 8 widgets (header, KPIs, budget, variance, tree, costs, health) | General project monitoring — the default starting point |
| **EVM Analysis** | 7 widgets (summary, gauges, trend, variance, forecast, health) | Deep Earned Value analysis and performance tracking |
| **Cost Controller** | 6 widgets (budget, costs, change orders, analytics, forecast) | Financial tracking and cost management focus |

**To use a template:**
1. Enter edit mode (click **Customize**).
2. Use the **template selector dropdown** in the toolbar to choose a template.
3. The template's widget layout replaces your current layout.
4. Click **Done** to save, or **Cancel** to revert.

> Templates are read-only starting configurations. When you apply a template, you get your own copy that you can freely customize.

---

## 15. Auto-Save Behavior

The dashboard saves your work automatically in these situations:

| Scenario | Behavior |
|----------|----------|
| Widget config changed in **view mode** | Auto-saves after 500ms debounce |
| Changes confirmed via **Done** button | Saves immediately |
| Page refresh or tab close with unsaved changes | Browser prompts to confirm leaving |

Auto-save is **not** active during edit mode — changes accumulate until you click **Done** or **Cancel**.

---

## 16. Navigation Guards

The dashboard protects against accidental data loss:

- **Tab/section navigation** — if you try to navigate away while in edit mode or with unsaved changes, a confirmation dialog appears: "Discard and Leave" or "Stay and Save".
- **Browser close/refresh** — if you close the tab or refresh the page with unsaved changes, the browser shows a "Leave site?" confirmation.

---

## 17. Fullscreen Mode

Any widget can be expanded to fill the entire browser viewport for a closer look at its data.

1. In **view mode**, hover over the widget's top-right corner to reveal the floating toolbar.
2. Click the **expand** button (fullscreen icon).
3. A fullscreen modal opens with the widget rendered at maximum size.
4. Charts and tables automatically resize to fill the available space.
5. To close, press **Escape** or click the **close** button in the modal header.

> Fullscreen mode preserves your current context — entity selections, branch, and date settings carry over from the dashboard.

---

## 18. Exporting Widget Data

You can export widget data in multiple formats directly from the dashboard.

1. In **view mode**, hover over the widget's top-right corner to reveal the floating toolbar.
2. Click the **download** icon to open the export menu.
3. Choose a format:

| Format | Availability | Description |
|--------|-------------|-------------|
| **PNG** | Chart widgets only | High-resolution screenshot of the chart (2x pixel ratio) |
| **CSV** | Table widgets only | Comma-separated values with proper quoting |
| **JSON** | All widgets | Raw widget data as a JSON file |

4. The file downloads automatically with a filename pattern: `{widgetType}-{dashboardName}-{timestamp}.{ext}`

> **PNG export** captures the chart exactly as displayed. **CSV export** includes column headers and handles special characters correctly.

---

## 19. Undo and Redo

When editing your dashboard layout, you can undo and redo changes using keyboard shortcuts or toolbar buttons.

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+Z` (or `Cmd+Z` on Mac) | **Undo** — revert the last change |
| `Ctrl+Shift+Z` (or `Cmd+Shift+Z` on Mac) | **Redo** — re-apply a reverted change |
| `Ctrl+Y` | **Redo** (alternative shortcut) |

### Toolbar Buttons

In edit mode, the toolbar displays **Undo** and **Redo** icon buttons. They are grayed out when there is nothing to undo or redo.

### What can be undone

- Adding a widget
- Removing a widget
- Moving or resizing a widget
- Changing a widget's configuration

### Undo behavior

- Up to **20 changes** can be undone (older changes are pruned).
- Making a new change after an undo clears the redo history.
- Clicking **Done** or **Cancel** clears both undo and redo history.
- Rapid drag operations are batched into a single undo entry.

---

## 20. Auto-Refresh

Widgets can automatically refresh their data at a configurable interval — useful for dashboards displayed on a monitor or during live project updates.

### Configuring auto-refresh

1. Open the widget's **Settings** drawer (gear icon).
2. Below the widget-specific options, find the **Auto-Refresh** section.
3. Choose an interval:

| Option | Interval |
|--------|----------|
| **Off** (default) | No automatic refresh |
| **30 seconds** | Refresh every 30s |
| **1 minute** | Refresh every 60s |
| **5 minutes** | Refresh every 300s |

4. Click **Apply** to save the setting.

### Stale indicator

When a widget's data is older than its refresh interval, a small **amber pulsing dot** appears next to the widget title in the floating toolbar. This indicates the data will refresh on the next cycle.

### Smart visibility detection

Auto-refresh is **paused** when a widget is scrolled off-screen. It resumes automatically when the widget comes back into view. This prevents unnecessary API calls for widgets you cannot see.

---

## 21. Mobile and Tablet Layout

The dashboard adapts its layout and controls for smaller screens.

### Desktop (1200px and wider)

- Full **12-column grid** with drag-and-drop widget arrangement.
- All editing features available.
- Standard toolbar with all controls.

### Tablet (768px – 1199px)

- **8-column grid** with larger touch targets.
- Drag and resize work with touch gestures.
- Simplified toolbar controls.

### Mobile (below 768px)

- **Single-column stacked layout** — widgets display one after another, no grid.
- Drag and resize are disabled. Instead, use the **Manage Widgets** button.
- Widget toolbars use larger touch-friendly buttons (40px tap targets).

#### Managing widgets on mobile

1. Tap the **Manage Widgets** button in the toolbar.
2. A bottom sheet opens showing all widgets in your dashboard.
3. Available actions:
   - **Drag to reorder** — press and hold the drag handle, then drag up or down.
   - **Hide/Show** — toggle the switch to show or hide a widget without removing it.
   - **Delete** — tap the trash icon to permanently remove a widget.
4. Tap outside the sheet or swipe down to close.

---

## 22. Troubleshooting

| Problem | Solution |
|---------|----------|
| Dashboard is empty / no widgets | You may not have a saved layout. Click **Customize** and add widgets, or select a template from the dropdown. |
| Widget shows "Select an entity" | The widget is scoped to a WBE/Cost Element level but nothing is selected. Add a **WBE Tree** widget and click a node. |
| Widget shows loading forever | Check your network connection. Click the **refresh** icon (hover over widget) to retry. |
| Widget shows an error | Click the **retry** button inside the widget. If the error persists, check that the backend server is running. |
| Changes not saving | Ensure you clicked **Done** to exit edit mode. View-mode config changes auto-save after 500ms. |
| Cannot drag/resize a widget | You must be in **edit mode** and click the **Move** or **Resize** button on the specific widget first. Direct dragging is disabled by default to prevent accidental moves. |
| Layout looks broken after resize | The widget may have been shrunk below its minimum size. Enter edit mode and resize it to a larger area. |
| Fullscreen widget not resizing chart | Close and reopen fullscreen mode. Charts auto-resize on open. |
| Export PNG is blank | Ensure the chart has finished loading before exporting. Wait for data to appear, then export. |
| Undo not working | Undo/redo is only available in **edit mode**. Enter edit mode first, then use Ctrl+Z. |
| Auto-refresh not updating | Auto-refresh pauses when the widget is off-screen. Scroll the widget into view to resume. |
| Mobile layout not changing | Clear browser cache or hard-refresh (Ctrl+Shift+R). The responsive layout detects viewport width on load. |

---

## Quick Reference

| Action | How |
|--------|-----|
| Open dashboard | Project page → **Dashboard** tab |
| Enter edit mode | Click **Customize** |
| Add a widget | Edit mode → **+ Add Widget** → pick from palette |
| Move a widget | Edit mode → click **Move** → drag to position |
| Resize a widget | Edit mode → click **Resize** → drag handle |
| Configure a widget | Click **Settings** gear → adjust in drawer |
| Remove a widget | Edit mode → click **Delete** trash icon |
| Save changes | Click **Done** |
| Discard changes | Click **Cancel** |
| Scope widgets to an entity | Click a node in the **WBE Tree** widget |
| Switch dashboard template | Edit mode → template dropdown in toolbar |
| Refresh widget data | Hover widget → click **refresh** icon |
| Fullscreen a widget | View mode → hover widget → click **expand** icon |
| Export widget data | View mode → hover widget → click **download** icon → choose format |
| Undo a change | Edit mode → `Ctrl+Z` or click undo button |
| Redo a change | Edit mode → `Ctrl+Shift+Z` or click redo button |
| Set auto-refresh | Open widget settings → choose interval → Apply |
| Manage widgets on mobile | Tap **Manage Widgets** → reorder, hide, or delete |
