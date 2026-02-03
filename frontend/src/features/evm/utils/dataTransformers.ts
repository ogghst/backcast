/**
 * Data Transformers for EVM Charts
 *
 * Utility functions to transform EVM API data into formats
 * suitable for ECharts consumption.
 *
 * @module features/evm/utils/dataTransformers
 */

import type { EVMTimeSeriesResponse } from "../types";

/**
 * Transformed series data for ECharts time series charts.
 * Each series contains name and array of [date, value] tuples.
 */
export interface TransformedSeries {
  name: string;
  data: Array<[string, number]>;
  color?: string;
}

/**
 * Transform EVM time-series data for PV/EV/AC progression chart.
 * Converts flat EVMTimeSeriesResponse to series format for ECharts.
 *
 * @param timeSeries - Time series data from API
 * @returns Array of series objects with PV, EV, and AC data
 */
export function transformEVMProgressionData(timeSeries: EVMTimeSeriesResponse): TransformedSeries[] {
  const points = timeSeries.points ?? [];

  return [
    {
      name: "PV",
      color: "#5b8ff9", // Blue
      data: points.map((p) => [p.date, p.pv] as [string, number]),
    },
    {
      name: "EV",
      color: "#5ad8a6", // Green
      data: points.map((p) => [p.date, p.ev] as [string, number]),
    },
    {
      name: "AC",
      color: "#5d7092", // Gray
      data: points.map((p) => [p.date, p.ac] as [string, number]),
    },
  ];
}

/**
 * Transform EVM time-series data for CPI vs SPI Performance Indices chart.
 *
 * Context: Uses backend-calculated CPI and SPI values for consistency.
 * Values above 1.0 indicate good performance.
 *
 * @param timeSeries - Time series data from API
 * @returns Array of series objects with CPI and SPI data
 */
export function transformPerformanceIndicesData(
  timeSeries: EVMTimeSeriesResponse
): TransformedSeries[] {
  const points = timeSeries.points ?? [];

  // Filter out points where CPI or SPI are null
  const validPoints = points.filter(
    (p) => p.cpi !== null && p.spi !== null
  );

  return [
    {
      name: "CPI",
      color: "#5b8ff9", // Blue
      data: validPoints.map((p) => [p.date, p.cpi!] as [string, number]),
    },
    {
      name: "SPI",
      color: "#5ad8a6", // Green
      data: validPoints.map((p) => [p.date, p.spi!] as [string, number]),
    },
  ];
}

/**
 * Transform EVM time-series data for Forecast vs Actual comparison chart.
 *
 * @param timeSeries - Time series data from API
 * @returns Array of series objects with Forecast and Actual data
 */
export function transformCostComparisonData(timeSeries: EVMTimeSeriesResponse): TransformedSeries[] {
  const points = timeSeries.points ?? [];

  return [
    {
      name: "Forecast",
      color: "#faad14", // Orange
      data: points.map((p) => [p.date, p.forecast] as [string, number]),
    },
    {
      name: "Actual",
      color: "#ff4d4f", // Red
      data: points.map((p) => [p.date, p.actual] as [string, number]),
    },
  ];
}

/**
 * Transform all EVM time-series data for a complete chart set.
 * Returns both chart types' data in a single object.
 *
 * @param timeSeries - Time series data from API
 * @returns Object with both progression and performance indices data
 */
export function transformAllTimeSeriesData(timeSeries: EVMTimeSeriesResponse): {
  evmProgression: TransformedSeries[];
  performanceIndices: TransformedSeries[];
} {
  return {
    evmProgression: transformEVMProgressionData(timeSeries),
    performanceIndices: transformPerformanceIndicesData(timeSeries),
  };
}

/**
 * Filter data points to show only those within a specific date range.
 * Useful for zoom/slice operations.
 *
 * @param data - Array of [date, value] tuples
 * @param startDate - Start date (ISO string or Date)
 * @param endDate - End date (ISO string or Date)
 * @returns Filtered data array
 */
export function filterDataByDateRange(
  data: Array<[string, number]>,
  startDate: string | Date,
  endDate: string | Date,
): Array<[string, number]> {
  const start = new Date(startDate);
  const end = new Date(endDate);

  return data.filter(([dateStr]) => {
    const date = new Date(dateStr);
    return date >= start && date <= end;
  });
}

/**
 * Get the visible date range from a subset of data points.
 * Useful for DataZoom integration.
 *
 * @param series - Array of series objects
 * @returns Object with start and end dates, or null if no data
 */
export function getDateRangeFromSeries(series: TransformedSeries[]): {
  startDate: string;
  endDate: string;
} | null {
  if (series.length === 0 || series[0].data.length === 0) {
    return null;
  }

  const allDates = series.flatMap((s) => s.data.map(([date]) => new Date(date).getTime()));
  const min = Math.min(...allDates);
  const max = Math.max(...allDates);

  return {
    startDate: new Date(min).toISOString(),
    endDate: new Date(max).toISOString(),
  };
}

/**
 * Calculate data statistics for a series.
 * Useful for tooltips and summary displays.
 *
 * @param data - Array of [date, value] tuples
 * @returns Object with min, max, avg, and latest values
 */
export function calculateSeriesStats(data: Array<[string, number]>): {
  min: number;
  max: number;
  avg: number;
  latest: number;
  latestDate: string;
} | null {
  if (data.length === 0) return null;

  const values = data.map(([, v]) => v);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const sum = values.reduce((a, b) => a + b, 0);
  const avg = sum / values.length;

  // Last data point
  const [latestDate, latest] = data[data.length - 1];

  return { min, max, avg, latest, latestDate };
}

/**
 * Normalize null/undefined values in time-series data.
 * Replaces nulls with the previous non-null value (forward fill).
 *
 * @param data - Array of [date, value] tuples
 * @returns Cleaned data array with forward-filled values
 */
export function forwardFillNulls(data: Array<[string, number | null]>): Array<[string, number]> {
  const result: Array<[string, number]> = [];
  let lastValid: number | null = null;

  for (const [date, value] of data) {
    if (value !== null && value !== undefined) {
      lastValid = value;
      result.push([date, value]);
    } else if (lastValid !== null) {
      result.push([date, lastValid]);
    } else {
      // No valid value yet, use 0
      result.push([date, 0]);
    }
  }

  return result;
}

/**
 * Aggregate time-series data to a coarser granularity.
 * Useful when backend returns finer data than needed.
 *
 * @param data - Array of [date, value] tuples
 * @param targetGranularity - Target granularity: 'week' or 'month'
 * @returns Aggregated data array
 */
export function aggregateToGranularity(
  data: Array<[string, number]>,
  targetGranularity: "week" | "month",
): Array<[string, number]> {
  if (data.length === 0) return [];

  const aggregationMap = new Map<string, number[]>();

  for (const [dateStr, value] of data) {
    const date = new Date(dateStr);
    let key: string;

    if (targetGranularity === "week") {
      // Get the Monday of the week
      const d = new Date(date);
      const day = d.getDay();
      const diff = d.getDate() - day + (day === 0 ? -6 : 1);
      d.setDate(diff);
      key = d.toISOString().split("T")[0];
    } else {
      // First day of the month
      key = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-01`;
    }

    if (!aggregationMap.has(key)) {
      aggregationMap.set(key, []);
    }
    aggregationMap.get(key)!.push(value);
  }

  // Calculate sum for each period
  return Array.from(aggregationMap.entries())
    .map(([date, values]) => [date, values.reduce((a, b) => a + b, 0)] as [string, number])
    .sort((a, b) => a[0].localeCompare(b[0]));
}
