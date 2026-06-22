/**
 * Gantt Zoom Presets
 *
 * Adaptive time-axis configuration for each discrete zoom level. A preset
 * fully describes how the dual-grid time header and the main-grid splitlines
 * behave at that zoom level, plus the default framing window used by
 * `scrollToToday` and the slider's initial range.
 *
 * Design notes (ECharts time-axis gotchas baked in here):
 *
 * - `primaryAxis` drives xAxis[0] (top header). `secondaryAxis` drives
 *   xAxis[2] (the dd/mm / day / month row under it). When `headerRows === 1`
 *   the builder can omit the secondary axis + its dummy series.
 * - For `month` the primary formatter is the *cascading* formatter
 *   (only emits the month label near a month boundary). Its `interval` is
 *   weekly — this is what makes the pre-refactor chart render
 *   pixel-identically, so do not "simplify" it to a monthly interval.
 * - `splitlineIntervalMs` feeds xAxis[1].splitLine.interval on the main grid.
 *
 * @module features/schedule-baselines/components/GanttChart
 */

import type { ZoomLevel } from "./config";

/** One day, one week, one month (30-day approximation) in milliseconds. */
export const DAY_MS = 24 * 3600 * 1000;
export const WEEK_MS = 7 * DAY_MS;
export const MONTH_MS = 30 * DAY_MS;

const SHORT_MONTHS = [
  "Jan", "Feb", "Mar", "Apr", "May", "Jun",
  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
];

/** Formatter describing a single time-header axis row. */
export interface HeaderAxisSpec {
  /** Label formatter that takes a unix-ms timestamp. */
  formatter: (value: number) => string;
  /**
   * Axis tick interval in ms. Combined with the formatter this controls tick
   * density. Use `WEEK_MS`/`MONTH_MS`/`DAY_MS` from this module.
   */
  interval: number;
}

/** Full preset for one zoom level. */
export interface ZoomPreset {
  /** Tick interval (ms) for the main grid's x-axis labels (xAxis[1]). */
  tickIntervalMs: number;
  /** Splitline interval (ms) for the main grid (xAxis[1].splitLine). */
  splitlineIntervalMs: number;
  /** Default framing window (ms) for scrollToToday + slider initial range. */
  defaultWindowMs: number;
  /** Top header row (xAxis[0]). */
  primaryAxis: HeaderAxisSpec;
  /** Optional second header row (xAxis[2]). Omitted when `headerRows === 1`. */
  secondaryAxis?: HeaderAxisSpec;
  /** Number of header rows the builder must render (1 or 2). */
  headerRows: 1 | 2;
}

/**
 * Cascading month formatter used by the `month` preset's primary axis.
 *
 * Emits "MMM 'YY" only when the tick falls within the first 7 days of a
 * month, blank otherwise. This is what produces clean monthly labels on a
 * weekly-interval axis and MUST be preserved for the no-op-refactor contract.
 */
function cascadingMonthFormatter(value: number): string {
  const d = new Date(value);
  if (d.getDate() <= 7) {
    return `${SHORT_MONTHS[d.getMonth()]} '${String(d.getFullYear()).slice(2)}`;
  }
  return "";
}

/** Plain month formatter "MMM 'YY" for any tick (used by day/week presets). */
function monthFormatter(value: number): string {
  const d = new Date(value);
  return `${SHORT_MONTHS[d.getMonth()]} '${String(d.getFullYear()).slice(2)}`;
}

/** Quarter formatter "Qn 'YY" (Q1 = Jan-Mar). */
function quarterFormatter(value: number): string {
  const d = new Date(value);
  const q = Math.floor(d.getMonth() / 3) + 1;
  return `Q${q} '${String(d.getFullYear()).slice(2)}`;
}

/** Short month name only (used by the quarter preset's secondary axis). */
function shortMonthFormatter(value: number): string {
  return SHORT_MONTHS[new Date(value).getMonth()];
}

/** Day-of-month with NO leading zero ("1".."31"). */
function dayOfMonthFormatter(value: number): string {
  return String(new Date(value).getDate());
}

/** dd/mm weekly formatter (preserves pre-refactor secondary axis output). */
function ddMmFormatter(value: number): string {
  const d = new Date(value);
  const dd = String(d.getDate()).padStart(2, "0");
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  return `${dd}/${mm}`;
}

/** Preset table — looked up by `getZoomPreset`. */
const ZOOM_PRESETS: Record<ZoomLevel, ZoomPreset> = {
  day: {
    tickIntervalMs: DAY_MS,
    splitlineIntervalMs: DAY_MS,
    defaultWindowMs: 14 * DAY_MS,
    primaryAxis: { formatter: monthFormatter, interval: MONTH_MS },
    secondaryAxis: { formatter: dayOfMonthFormatter, interval: DAY_MS },
    headerRows: 2,
  },
  week: {
    tickIntervalMs: WEEK_MS,
    splitlineIntervalMs: WEEK_MS,
    defaultWindowMs: 9 * WEEK_MS,
    primaryAxis: { formatter: monthFormatter, interval: MONTH_MS },
    secondaryAxis: { formatter: ddMmFormatter, interval: WEEK_MS },
    headerRows: 2,
  },
  month: {
    // NOTE: primary uses the cascading formatter on a WEEKLY interval so the
    // month view renders pixel-identically to the pre-refactor implementation.
    tickIntervalMs: WEEK_MS,
    splitlineIntervalMs: WEEK_MS,
    defaultWindowMs: 6 * MONTH_MS,
    primaryAxis: { formatter: cascadingMonthFormatter, interval: WEEK_MS },
    secondaryAxis: { formatter: ddMmFormatter, interval: WEEK_MS },
    headerRows: 2,
  },
  quarter: {
    tickIntervalMs: MONTH_MS,
    splitlineIntervalMs: MONTH_MS,
    defaultWindowMs: 15 * MONTH_MS,
    primaryAxis: { formatter: quarterFormatter, interval: 3 * MONTH_MS },
    secondaryAxis: { formatter: shortMonthFormatter, interval: MONTH_MS },
    headerRows: 2,
  },
};

/**
 * Get the zoom preset for a given level.
 *
 * @param zoom - Discrete zoom level
 * @returns The fully-resolved preset (intervals, window, header formatters)
 */
export function getZoomPreset(zoom: ZoomLevel): ZoomPreset {
  return ZOOM_PRESETS[zoom];
}
