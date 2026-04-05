Requirement Analysis: Composable Widget System for Backcast PM
1. Vision & Executive Summary
Transition the current fixed-page architecture into a modular, widget-based dashboard system. This allows users (Project Managers, Stakeholders, Analysts) to build personalized "Control Centers" by dragging and dropping metrics, charts, and data grids into a flexible layout.
Design Philosophy: Apple-style UX (high whitespace, soft shadows, subtle transitions, "everything-is-an-object") using Ant Design (UI components) and ECharts (visualization).
2. Core Technical Requirements
2.1 The Grid Engine
 * Library Recommendation: react-grid-layout or dnd-kit.
 * Responsive Grid: 12-column grid system with breakpoints for mobile/tablet/desktop.
 * Persistence: Widget layouts (ID, position x/y, size w/h, and config) must be saved per user/per project in the backend.
2.2 Widget Anatomy (The "Interface")
Every widget must implement a standard interface to ensure consistency:
 * Header: Title, status indicator (e.g., "Live"), and a "More" menu (Edit settings, Refresh, Expand, Remove).
 * Content: The core visualization (EChart, AntD Table, or Stat Card).
 * Footer (Optional): "Last updated" timestamp or a "View Details" link to a deep-page.
 * Loading State: Consistent skeleton screens while data is fetching.
3. Widget Taxonomy (Based on PMI EVM Standards)
Following PMI (Project Management Institute) recommendations, data should be categorized into Diagnostic, Performance, and Forecast metrics.
Category A: Diagnostic Widgets (Status & Health)
| Widget Name | Data Source | Visualization | Description |
|---|---|---|---|
| Budget Status | Budget vs Actuals | AntD Progress Bar | Linear gauge showing % of budget consumed (Ref: Screenshot 1000231783). |
| Project Health Card | SPI / CPI / SV | Colored Badges | High-level "Traffic Light" (Red/Amber/Green) based on thresholds. |
| WBS Explorer | WBS Tree | AntD Tree / List | Compact view of the work breakdown structure (Ref: Screenshot 1000231776). |
Category B: Performance Widgets (EVM)
| Widget Name | Data Source | Visualization | Description |
|---|---|---|---|
| EVM Trend Chart | PV, EV, AC over time | ECharts Line Chart | Historical progression of Earned Value metrics (Ref: Screenshot 1000231781). |
| Efficiency Gauges | SPI & CPI | ECharts Gauge | Circular meters showing if $1 of budget is returning \geq 1 of value. |
| Variance Analysis | CV & SV | ECharts Bar Chart | Side-by-side comparison of Cost and Schedule variances. |
Category C: Operational Widgets (Lists & Action)
| Widget Name | Data Source | Visualization | Description |
|---|---|---|---|
| Recent Cost Entries | Cost Registrations | AntD Table (Mini) | The 5 most recent registrations with "Quick Add" button. |
| Pending Change Orders | Change Order DB | AntD List | Items requiring approval/action (Ref: Screenshot 1000231780). |
| Mini-Gantt | Schedule | ECharts Custom/Gantt | A filtered view of the next 14 days of tasks (Ref: Screenshot 1000231779). |
4. User Experience: The Composition Mode
To achieve a "Rock Solid" UX, we define two distinct states for the dashboard.
4.1 "Read" Mode (Default)
 * Widgets are static and interactive (tooltips, table sorting).
 * Glassmorphism effects on hover.
 * Zero "editing" UI elements visible to reduce cognitive load.
4.2 "Edit" Mode (The Layout Manager)
 * Trigger: A "Personalize" or "Edit Dashboard" button with a smooth animation.
 * Visual Cue: The grid background appears (subtle dots), and widgets "wiggle" slightly (iOS style) or show a border.
 * Widget Library: A side-drawer or bottom-sheet containing the "Add Widget" gallery.
 * Collision Logic: Widgets should push others out of the way gracefully when dragged.
 * Empty State: If a user has no widgets, show a "Start with a Template" screen (e.g., "PM Portfolio Template" vs "Financial Auditor Template").
5. General Widget Properties & Configuration
Each widget should have a "Settings" pane (AntD Drawer) allowing per-widget customization:
 * Data Scope: "Current Project" vs "Selected WBS Element."
 * Timeframe: "Last 30 days," "Project to Date," or "Fiscal Year."
 * Visual Style: e.g., Toggle between a "Line" or "Area" chart for trends.
 * Refresh Interval: How often the widget polls the API.
6. Implementation Roadmap (React Context)
 * Stage 1: Containerization. Wrap existing screens (Cost Registration, EVM Summary) into a WidgetWrapper component.
 * Stage 2: Layout State. Implement a DashboardContext to manage the array of widget configurations.
 * Stage 3: DND Integration. Wrap the WidgetWrapper in a drag-and-drop provider.
 * Stage 4: Preset Templates. Define 3-4 default layouts based on common project roles to reduce "blank canvas" anxiety.
7. Design Tokens (Apple-Style)
 * Border Radius: 12px to 16px for widgets.
 * Shadows: 0 4px 20px rgba(0,0,0,0.05) (very soft).
 * Typography: SF Pro (or Inter) with balanced weights. High contrast for primary metrics, subtle grey for helper text.
 * Colors: Use the AntD "Preset Status Colors" but softened. (e.g., Pastel reds for variance, emerald greens for healthy metrics).
