/**
 * Gantt Chart Configuration
 *
 * Single declarative config object that drives the entire Gantt layout,
 * zoom behaviour, and feature flags. This is the reuse lever: the future
 * dashboard widget will render `<ScheduleTimeline config={defaultCompactConfig}/>`
 * while the full page renders with `defaultFullConfig`.
 *
 * Every layout constant consumed by the options builder / presentational
 * core is derived from this config (plus the active zoom preset and theme
 * tokens) — nothing layout-critical is hard-coded inside the builder.
 *
 * @module features/schedule-baselines/components/GanttChart
 */

/**
 * Discrete zoom level presets (Tempo / MS Project model).
 *
 * Each level answers a different question:
 * - `day`     — "is anything happening today / this week?"
 * - `week`    — short-horizon sprint / milestone planning
 * - `month`   — the default project-management view (current behaviour)
 * - `quarter` — executive / portfolio roll-up over a long horizon
 */
export type ZoomLevel = "day" | "week" | "month" | "quarter";

/** Density constants that vary between the full page and compact widget. */
export interface GanttDensity {
  /** Per-row height in pixels. */
  rowHeight: number;
  /** Time-header grid height in pixels (grid 0). */
  headerHeight: number;
  /** Bottom padding for dataZoom + main axis labels + spacing. */
  bottomPadding: number;
}

/**
 * Full configuration for the Gantt chart engine.
 *
 * Passed straight through to `buildGanttOptions` and `<ScheduleTimeline>`.
 */
export interface GanttChartConfig {
  /** Layout mode — `full` for the page, `compact` for the future widget. */
  mode: "full" | "compact";
  /** Active discrete zoom level. */
  zoom: ZoomLevel;
  /** Left grid offset in pixels (task-name panel width). */
  gridLeft: number;
  /** Row / header / bottom-padding densities. */
  density: GanttDensity;
  /** Render dependency arrows. */
  showDependencies: boolean;
  /** Render the slider + inside dataZoom controls. */
  showDataZoom: boolean;
  /** Render the dual-grid time header (grid 0). */
  showTimeHeader: boolean;
}

/**
 * Default config for the full page.
 *
 * At `zoom:'month'` with this density the chart renders pixel-identical to
 * the pre-refactor implementation (no-op refactor contract).
 */
export const defaultFullConfig: GanttChartConfig = {
  mode: "full",
  zoom: "month",
  gridLeft: 300,
  density: {
    rowHeight: 32,
    headerHeight: 56,
    bottomPadding: 80,
  },
  showDependencies: true,
  showDataZoom: true,
  showTimeHeader: true,
};

/**
 * Default config for the compact dashboard widget (future phase).
 *
 * Tighter rows, shorter header, no dependency arrows, no dataZoom slider —
 * the widget drives framing itself via `scrollToToday` / `fitProject`.
 */
export const defaultCompactConfig: GanttChartConfig = {
  mode: "compact",
  zoom: "month",
  gridLeft: 120,
  density: {
    rowHeight: 22,
    headerHeight: 28,
    bottomPadding: 24,
  },
  showDependencies: false,
  showDataZoom: false,
  showTimeHeader: true,
};
