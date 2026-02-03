/**
 * EVM (Earned Value Management) Types
 *
 * This file contains TypeScript interfaces and types that mirror the backend
 * EVM Pydantic schemas. All types are designed to be fully compatible with the
 * backend API responses.
 *
 * Backend Reference:
 * - backend/app/models/schemas/evm.py
 *
 * @module features/evm/types
 */

/**
 * Entity type for EVM metrics.
 *
 * Defines the granularity level for EVM calculations:
 * - COST_ELEMENT: Individual cost element (leaf node)
 * - WBE: Work Breakdown Element (intermediate node)
 * - PROJECT: Project level (root node)
 *
 * @enum {string}
 */
export enum EntityType {
  COST_ELEMENT = "cost_element",
  WBE = "wbe",
  PROJECT = "project",
}

/**
 * Time granularity for EVM time-series aggregation.
 *
 * Defines the time interval for data point aggregation:
 * - DAY: Daily data points
 * - WEEK: Weekly data points (default)
 * - MONTH: Monthly data points
 *
 * @enum {string}
 */
export enum EVMTimeSeriesGranularity {
  DAY = "day",
  WEEK = "week",
  MONTH = "month",
}

/**
 * Metric category for organizing EVM metrics in the UI.
 *
 * Metrics are grouped by topic for better user experience:
 * - Schedule: Time-based performance metrics (SPI, SV)
 * - Cost: Budget and cost metrics (BAC, AC, CV, CPI)
 * - Variance: Deviation metrics (CV, SV)
 * - Performance: Efficiency indices (CPI, SPI)
 * - Forecast: Projected completion metrics (EAC, VAC, ETC)
 *
 * @enum {string}
 */
export enum MetricCategory {
  SCHEDULE = "Schedule",
  COST = "Cost",
  VARIANCE = "Variance",
  PERFORMANCE = "Performance",
  FORECAST = "Forecast",
}

/**
 * Earned Value Management metrics for any entity type.
 *
 * Provides a flat structure with all EVM metrics explicitly defined.
 * Supports cost_element, wbe, and project entity types.
 *
 * Metrics:
 * - BAC: Budget at Completion (total planned budget)
 * - PV: Planned Value (budgeted cost of work scheduled)
 * - AC: Actual Cost (actual cost incurred)
 * - EV: Earned Value (budgeted cost of work performed)
 * - CV: Cost Variance (EV - AC, negative = over budget)
 * - SV: Schedule Variance (EV - PV, negative = behind schedule)
 * - CPI: Cost Performance Index (EV / AC, < 1.0 = over budget)
 * - SPI: Schedule Performance Index (EV / PV, < 1.0 = behind schedule)
 * - EAC: Estimate at Completion (projected total cost)
 * - VAC: Variance at Completion (BAC - EAC)
 * - ETC: Estimate to Complete (EAC - AC)
 *
 * This schema uses a flat structure with all metrics as individual fields,
 * not a list-based approach, for better type safety and API clarity.
 *
 * @interface EVMMetricsResponse
 */
export interface EVMMetricsResponse {
  /** Entity type (cost_element, wbe, or project) */
  entity_type: EntityType;

  /** Entity ID (cost element, WBE, or project) */
  entity_id: string;

  /** Budget at Completion (total planned budget) */
  bac: number;

  /** Planned Value (budgeted cost of work scheduled) */
  pv: number;

  /** Actual Cost (cost incurred to date) */
  ac: number;

  /** Earned Value (budgeted cost of work performed) */
  ev: number;

  /** Cost Variance (EV - AC, negative = over budget) */
  cv: number;

  /** Schedule Variance (EV - PV, negative = behind schedule) */
  sv: number;

  /**
   * Cost Performance Index (EV / AC, < 1.0 = over budget)
   * @nullable
   */
  cpi: number | null;

  /**
   * Schedule Performance Index (EV / PV, < 1.0 = behind schedule)
   * @nullable
   */
  spi: number | null;

  /**
   * Estimate at Completion (projected total cost at completion)
   * @nullable
   */
  eac: number | null;

  /**
   * Variance at Completion = BAC - EAC (negative = over budget)
   * @nullable
   */
  vac: number | null;

  /**
   * Estimate to Complete = EAC - AC (remaining work cost)
   * @nullable
   */
  etc: number | null;

  /** Control date for time-travel query */
  control_date: string;

  /** Branch name */
  branch: string;
}

/**
 * Single data point for EVM time-series charts.
 *
 * Represents EVM metrics at a specific point in time for charting.
 * Used in time-series responses for trend visualization.
 *
 * @interface EVMTimeSeriesPoint
 */
export interface EVMTimeSeriesPoint {
  /** Date of the data point (ISO 8601 string) */
  date: string;

  /** Planned Value at this date */
  pv: number;

  /** Earned Value at this date */
  ev: number;

  /** Actual Cost at this date */
  ac: number;

  /** Forecast value at this date */
  forecast: number;

  /** Actual value at this date */
  actual: number;

  /**
   * Cost Performance Index (EV / AC, < 1.0 = over budget)
   * @nullable
   */
  cpi: number | null;

  /**
   * Schedule Performance Index (EV / PV, < 1.0 = behind schedule)
   * @nullable
   */
  spi: number | null;
}

/**
 * EVM time-series data for charts.
 *
 * Contains aggregated EVM metrics over a time range with specified granularity.
 * Used for rendering trend charts and performance curves.
 *
 * Server-side aggregation is performed based on the requested granularity.
 *
 * @interface EVMTimeSeriesResponse
 */
export interface EVMTimeSeriesResponse {
  /** Time granularity (day, week, month) */
  granularity: EVMTimeSeriesGranularity;

  /** List of time-series data points */
  points: EVMTimeSeriesPoint[];

  /** Start date of the time series (ISO 8601 string) */
  start_date: string;

  /** End date of the time series (ISO 8601 string) */
  end_date: string;

  /** Total number of data points */
  total_points: number;
}

/**
 * Target ranges for EVM metrics.
 *
 * Defines favorable and unfavorable ranges for metrics to determine
 * color coding in visualizations (green/yellow/red).
 *
 * @interface MetricTargetRanges
 */
export interface MetricTargetRanges {
  /** Minimum value (unfavorable/bottom of range) */
  min: number;

  /** Maximum value (favorable/top of range) */
  max: number;

  /** Good threshold (values above this are good for most metrics) */
  good?: number;
}

/**
 * Metadata for EVM metrics.
 *
 * Provides static information about each metric for UI display:
 * - Human-readable name
 * - Detailed description
 * - Category for grouping
 * - Target ranges for color coding
 *
 * This type is used to drive the MetricCard component and organize
 * metrics in the EVMSummaryView.
 *
 * @interface MetricMetadata
 */
export interface MetricMetadata {
  /** Unique identifier for the metric (matches EVMMetricsResponse field name) */
  key: keyof EVMMetricsResponse;

  /** Human-readable name for display */
  name: string;

  /** Detailed description of what the metric means */
  description: string;

  /** Category for grouping metrics in UI */
  category: MetricCategory;

  /** Target ranges for determining favorable/unfavorable values */
  targetRanges: MetricTargetRanges;

  /** Whether higher values are better (true) or worse (false) */
  higherIsBetter: boolean;

  /** Format string for displaying values (e.g., "€", "%", "") */
  format: "currency" | "percentage" | "number";
}

/**
 * Metric definitions organized by key.
 *
 * This object provides static metadata for all EVM metrics.
 * Used by components to render metric cards, determine color coding,
 * and show descriptions.
 *
 * The definitions are hardcoded in the frontend (per user decision)
 * and organized by topic for better UX.
 */
export const METRIC_DEFINITIONS: Readonly<Record<string, MetricMetadata>> = {
  // Schedule Metrics
  spi: {
    key: "spi",
    name: "Schedule Performance Index",
    description:
      "Ratio of earned value to planned value. SPI < 1.0 indicates the project is behind schedule. SPI > 1.0 indicates the project is ahead of schedule.",
    category: MetricCategory.SCHEDULE,
    targetRanges: { min: 0, max: 2, good: 1.0 },
    higherIsBetter: true,
    format: "number",
  },

  sv: {
    key: "sv",
    name: "Schedule Variance",
    description:
      "Difference between earned value and planned value. Negative values indicate the project is behind schedule. Positive values indicate the project is ahead of schedule.",
    category: MetricCategory.SCHEDULE,
    targetRanges: { min: -Infinity, max: Infinity, good: 0 },
    higherIsBetter: true,
    format: "currency",
  },

  // Cost Metrics
  bac: {
    key: "bac",
    name: "Budget at Completion",
    description:
      "Total planned budget for the project or cost element. This is the baseline against which all other cost metrics are measured.",
    category: MetricCategory.COST,
    targetRanges: { min: 0, max: Infinity },
    higherIsBetter: false,
    format: "currency",
  },

  ac: {
    key: "ac",
    name: "Actual Cost",
    description:
      "Total actual cost incurred to date. Includes all cost registrations for work performed.",
    category: MetricCategory.COST,
    targetRanges: { min: 0, max: Infinity },
    higherIsBetter: false,
    format: "currency",
  },

  cv: {
    key: "cv",
    name: "Cost Variance",
    description:
      "Difference between earned value and actual cost. Negative values indicate the project is over budget. Positive values indicate the project is under budget.",
    category: MetricCategory.COST,
    targetRanges: { min: -Infinity, max: Infinity, good: 0 },
    higherIsBetter: true,
    format: "currency",
  },

  // Performance Metrics
  cpi: {
    key: "cpi",
    name: "Cost Performance Index",
    description:
      "Ratio of earned value to actual cost. CPI < 1.0 indicates the project is over budget. CPI > 1.0 indicates the project is under budget.",
    category: MetricCategory.PERFORMANCE,
    targetRanges: { min: 0, max: 2, good: 1.0 },
    higherIsBetter: true,
    format: "number",
  },

  // Forecast Metrics
  eac: {
    key: "eac",
    name: "Estimate at Completion",
    description:
      "Projected total cost at completion based on current performance. Calculated as BAC / CPI or from the forecast entity.",
    category: MetricCategory.FORECAST,
    targetRanges: { min: 0, max: Infinity },
    higherIsBetter: false,
    format: "currency",
  },

  vac: {
    key: "vac",
    name: "Variance at Completion",
    description:
      "Difference between budget at completion and estimate at completion. Negative values indicate the project will be over budget at completion.",
    category: MetricCategory.FORECAST,
    targetRanges: { min: -Infinity, max: Infinity, good: 0 },
    higherIsBetter: true,
    format: "currency",
  },

  etc: {
    key: "etc",
    name: "Estimate to Complete",
    description:
      "Estimated cost to complete the remaining work. Calculated as EAC - AC.",
    category: MetricCategory.FORECAST,
    targetRanges: { min: 0, max: Infinity },
    higherIsBetter: false,
    format: "currency",
  },
} as const;

/**
 * Helper type to extract metric keys from EVMMetricsResponse.
 *
 * This type represents all valid metric keys that can be used
 * to access values from an EVMMetricsResponse object.
 */
export type MetricKey = keyof Pick<
  EVMMetricsResponse,
  | "bac"
  | "pv"
  | "ac"
  | "ev"
  | "cv"
  | "sv"
  | "cpi"
  | "spi"
  | "eac"
  | "vac"
  | "etc"
>;

/**
 * Type guard to check if a key is a valid metric key.
 *
 * @param key - The key to check
 * @returns True if the key is a valid metric key
 */
export function isMetricKey(key: string): key is MetricKey {
  return [
    "bac",
    "pv",
    "ac",
    "ev",
    "cv",
    "sv",
    "cpi",
    "spi",
    "eac",
    "vac",
    "etc",
  ].includes(key);
}

/**
 * Get metric metadata for a given metric key.
 *
 * @param key - The metric key
 * @returns The metric metadata, or undefined if not found
 */
export function getMetricMetadata(key: MetricKey): MetricMetadata | undefined {
  return METRIC_DEFINITIONS[key];
}

/**
 * Get all metrics for a specific category.
 *
 * @param category - The metric category
 * @returns Array of metric metadata for the category
 */
export function getMetricsByCategory(
  category: MetricCategory,
): MetricMetadata[] {
  return Object.values(METRIC_DEFINITIONS).filter(
    (m) => m.category === category,
  );
}

/**
 * Determine if a metric value is favorable based on target ranges.
 *
 * @param key - The metric key
 * @param value - The metric value
 * @returns "good", "warning", or "bad"
 */
export function getMetricStatus(
  key: MetricKey,
  value: number | null,
): "good" | "warning" | "bad" {
  if (value === null) return "warning";

  const metadata = getMetricMetadata(key);
  if (!metadata) return "warning";

  const { targetRanges, higherIsBetter } = metadata;
  const { good } = targetRanges;

  if (good === undefined) return "warning";

  if (higherIsBetter) {
    return value >= good ? "good" : value >= good * 0.9 ? "warning" : "bad";
  } else {
    return value <= good ? "good" : value <= good * 1.1 ? "warning" : "bad";
  }
}
