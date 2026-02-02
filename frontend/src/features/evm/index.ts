/**
 * EVM Feature Module
 *
 * Exports all EVM-related types, components, hooks, and utilities.
 *
 * @module features/evm
 */

// Types
export type {
  EVMMetricsResponse,
  EVMTimeSeriesPoint,
  EVMTimeSeriesResponse,
  MetricMetadata,
  MetricTargetRanges,
  MetricKey,
} from "./types";

export {
  EntityType,
  EVMTimeSeriesGranularity,
  MetricCategory,
} from "./types";

export {
  METRIC_DEFINITIONS,
  isMetricKey,
  getMetricMetadata,
  getMetricsByCategory,
  getMetricStatus,
} from "./types";

// API Hooks
export {
  useEVMMetrics,
  useEVMTimeSeries,
  useEVMMetricsBatch,
} from "./api/useEVMMetrics";

// Components
export { EVMGauge } from "./components/EVMGauge";
export type { EVMGaugeProps } from "./components/EVMGauge";

export { EVMTimeSeriesChart } from "./components/EVMTimeSeriesChart";

// ECharts Components
export {
  EChartsBaseChart,
  EChartsGauge,
  EChartsTimeSeries,
} from "./components/charts";
export type {
  EChartsBaseChartProps,
  EChartsGaugeProps,
  EChartsTimeSeriesProps,
} from "./components/charts";

// ECharts Utilities
export {
  useEChartsColors,
  useEChartsTheme,
  antDesignTheme,
  buildAxisConfig,
  buildTooltipConfig,
  buildLegendConfig,
} from "./utils/echartsTheme";
export type {
  EChartsColorPalette,
  EChartsAxisConfig,
  EChartsTooltipConfig,
  EChartsLegendConfig,
} from "./utils/echartsTheme";

export {
  buildGaugeOptions,
  buildTimeSeriesOptions,
  createCurrencyFormatter,
  createDateFormatter,
} from "./utils/echartsConfig";
export type {
  GaugeConfigOptions,
  TimeSeriesConfigOptions,
  TimeSeriesChartType,
} from "./utils/echartsConfig";

export {
  transformEVMProgressionData,
  transformCostComparisonData,
  transformAllTimeSeriesData,
  filterDataByDateRange,
  getDateRangeFromSeries,
  calculateSeriesStats,
  forwardFillNulls,
  aggregateToGranularity,
} from "./utils/dataTransformers";
export type { TransformedSeries } from "./utils/dataTransformers";
