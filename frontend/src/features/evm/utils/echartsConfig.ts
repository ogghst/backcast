/**
 * ECharts Configuration Builders
 *
 * Utility functions to build ECharts option objects for different chart types.
 * Provides consistent configuration across all EVM charts.
 *
 * @module features/evm/utils/echartsConfig
 */

import type { EChartsOption } from "echarts";
import type {
  EChartsColorPalette,
  EChartsAxisConfig,
  EChartsTooltipConfig,
  EChartsLegendConfig,
} from "./echartsTheme";

/**
 * Build gauge chart options for EVM metrics (CPI, SPI).
 *
 * Simplified gauge following ECharts basic pattern with minimal styling.
 *
 * @param options - Gauge configuration
 * @param colors - Color palette from useEChartsColors()
 * @returns ECharts option object
 */
export interface GaugeConfigOptions {
  /** Current value to display */
  value: number | null;
  /** Minimum value for the gauge range */
  min: number;
  /** Maximum value for the gauge range */
  max: number;
  /** Label for the gauge */
  label: string;
  /** Good threshold value (defaults to 1.0) */
  goodThreshold?: number;
  /** Warning threshold percentage (default 0.9 = 90% of good) */
  warningThresholdPercent?: number;
  /** Chart variant: semi-circle or full-circle */
  variant?: "semi-circle" | "full-circle";
  /** Size of the gauge in pixels */
  size?: number;
}

export function buildGaugeOptions(
  options: GaugeConfigOptions,
  colors: EChartsColorPalette,
): EChartsOption {
  const {
    value,
    min,
    max,
    label,
    goodThreshold = 1.0,
    warningThresholdPercent = 0.9,
    variant = "semi-circle",
  } = options;

  const warningThreshold = goodThreshold * warningThresholdPercent;

  // Convert thresholds to percentages (0-1 range for ECharts)
  const warningPercent = Math.max(
    0,
    Math.min(1, (warningThreshold - min) / (max - min)),
  );
  const goodPercent = Math.max(
    0,
    Math.min(1, (goodThreshold - min) / (max - min)),
  );

  // Standard ECharts gauge angles
  // Semi-circle: 225 to -45 (standard gauge orientation)
  // Full-circle: 90 to -270 (complete circle)
  const isSemiCircle = variant === "semi-circle";
  const startAngle = 225;
  const endAngle = isSemiCircle ? -45 : -270;

  return {
    tooltip: {
      formatter: "{a} <br/>{b} : {c}",
    },
    series: [
      {
        name: label,
        type: "gauge",
        startAngle,
        endAngle,
        min,
        max,
        // Axis line with color zones
        axisLine: {
          lineStyle: {
            width: 20,
            color: [
              [warningPercent, colors.gaugeBad],
              [goodPercent, colors.gaugeWarning],
              [1, colors.gaugeGood],
            ],
          },
        },
        // Simple pointer
        pointer: {
          width: 3,
          length: isSemiCircle ? "60%" : "70%",
        },
        // Minor ticks
        axisTick: {
          distance: -20,
          length: 5,
        },
        // Major split lines
        splitLine: {
          distance: -20,
          length: 12,
        },
        // Axis labels - hidden to reduce visual clutter
        axisLabel: {
          show: false,
        },
        // Detail value display (positioned below the gauge)
        detail: {
          valueAnimation: true,
          formatter: (value: number) =>
            value !== null ? value.toFixed(2) : "N/A",
          fontSize: 22,
          fontWeight: 500,
          offsetCenter: isSemiCircle ? [0, "40%"] : [0, "70%"],
        },
        // Title label
        title: {
          show: true,
          offsetCenter: isSemiCircle ? [0, "80%"] : [0, "-50%"],
          fontSize: 14,
        },
        data: [
          {
            value: value ?? min,
            name: label,
          },
        ],
      },
    ],
  };
}

/**
 * Chart types for time series.
 */
export type TimeSeriesChartType =
  | "evm-progression" // PV, EV, AC on one chart
  | "performance-indices"; // CPI vs SPI

/**
 * Build time series chart options for EVM analysis.
 */
export interface TimeSeriesConfigOptions {
  /** Chart type */
  chartType: TimeSeriesChartType;
  /** Series data - array of objects with name, data points */
  series: Array<{
    name: string;
    data: Array<[string, number | null]>; // [date, value] tuples
    color?: string;
  }>;
  /** Show DataZoom slider */
  showZoom?: boolean;
  /** Use dual Y-axis */
  dualYAxis?: boolean;
  /** Y-axis formatter (e.g., currency) */
  yFormatter?: (value: number) => string;
  /** X-axis formatter (e.g., date) */
  xFormatter?: (value: string) => string;
  /** Chart height in pixels */
  height?: number;
}

export function buildTimeSeriesOptions(
  options: TimeSeriesConfigOptions,
  theme: {
    colors: EChartsColorPalette;
    axisConfig: EChartsAxisConfig;
    tooltipConfig: EChartsTooltipConfig;
    legendConfig: EChartsLegendConfig;
  },
): EChartsOption {
  const { colors, axisConfig, tooltipConfig, legendConfig } = theme;

  const {
    chartType,
    series,
    showZoom = true,
    dualYAxis = false,
    yFormatter = (v) => v.toString(),
    xFormatter = (v) => v,
    // height, // Not used in options, controlled by component
  } = options;

  // Check if this is a performance indices chart
  const isPerformanceIndices = chartType === "performance-indices";

  // Default colors based on series name
  const defaultColors: Record<string, string> = {
    PV: colors.pv,
    EV: colors.ev,
    AC: colors.ac,
    CPI: "#5b8ff9", // Blue
    SPI: "#5ad8a6", // Green
    Forecast: colors.forecast,
    Actual: colors.actual,
  };

  // Y-axis configuration for performance indices (0-2 range, centered on 1.0)
  const yAxisConfig = series.slice(0, dualYAxis ? 2 : 1).map((_s, index) => ({
    type: "value" as const,
    position: dualYAxis && index === 1 ? "right" : "left",
    ...axisConfig,
    min: isPerformanceIndices ? 0 : undefined,
    max: isPerformanceIndices ? 2 : undefined,
    axisLabel: {
      ...axisConfig.axisLabel,
      formatter: yFormatter,
    },
    splitLine: {
      ...axisConfig.splitLine,
      show: index === 0,
    },
  }));

  // Series configuration with markLine for performance indices
  const seriesConfig = series.map((s, index) => {
    const baseConfig = {
      name: s.name,
      type: "line" as const,
      data: s.data,
      smooth: true,
      connectNulls: true,
      symbol: "circle" as const,
      symbolSize: 6,
      yAxisIndex: dualYAxis && index >= 2 ? 1 : 0,
      emphasis: {
        focus: "series" as const,
      },
    };

    // Add markLine at y=1.0 for performance indices
    if (isPerformanceIndices && index === 0) {
      return {
        ...baseConfig,
        markLine: {
          silent: true,
          symbol: "none",
          label: {
            show: true,
            position: "end" as const,
            formatter: "Target (1.0)",
            fontSize: 11,
            color: colors.success,
          },
          lineStyle: {
            type: "solid" as const,
            color: colors.success,
            width: 2,
          },
          data: [{ yAxis: 1.0 }],
        },
      };
    }

    return baseConfig;
  });

  return {
    color: series.map(
      (s) => s.color ?? defaultColors[s.name] ?? colors.primary,
    ),
    tooltip: {
      ...tooltipConfig,
      trigger: "axis" as const,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      formatter: (params: any) => {
        if (!Array.isArray(params)) return "";
        const date = params[0]?.axisValue;
        let result = `<div style="margin-bottom: 4px; font-weight: 600;">${xFormatter(date)}</div>`;
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        params.forEach((param: any) => {
          const rawValue = Array.isArray(param.value)
            ? param.value[1]
            : param.value;

          // Skip null values in tooltip
          if (rawValue === null || rawValue === undefined) {
            return;
          }

          // Format performance indices with 2 decimal places
          const value = isPerformanceIndices
            ? typeof rawValue === "number"
              ? rawValue.toFixed(2)
              : rawValue
            : yFormatter(rawValue);

          result += `<div style="display: flex; justify-content: space-between; gap: 16px;">
            <span style="display: flex; align-items: center;">
              <span style="display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: ${param.color}; margin-right: 6px;"></span>
              ${param.seriesName}
            </span>
            <span style="font-weight: 600;">${value}</span>
          </div>`;
        });
        return result ===
          `<div style="margin-bottom: 4px; font-weight: 600;">${xFormatter(date)}</div>`
          ? ""
          : result;
      },
    },
    legend: {
      ...legendConfig,
      top: 0,
    },
    grid: {
      left: "3%",
      right: dualYAxis ? "4%" : "3%",
      bottom: showZoom ? "15%" : "8%",
      top: "15%",
      containLabel: true,
    },
    xAxis: {
      type: "category" as const,
      boundaryGap: false,
      ...axisConfig,
      axisLabel: {
        ...axisConfig.axisLabel,
        formatter: xFormatter,
      },
    },
    yAxis: yAxisConfig,
    series: seriesConfig,
    dataZoom: showZoom
      ? [
          {
            type: "slider" as const,
            bottom: "2%",
            height: 20,
            borderColor: "transparent",
            backgroundColor: "transparent",
            handleSize: "80%",
            showDetail: false,
            brushSelect: true,
          },
          {
            type: "inside" as const,
            zoomOnMouseWheel: true,
            moveOnMouseMove: true,
          },
        ]
      : undefined,
  };
}

/**
 * Get currency formatter for tooltips.
 */
export function createCurrencyFormatter(
  currency: string = "EUR",
): (value: number) => string {
  return (value: number) => {
    if (value === null || value === undefined) return "N/A";
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency,
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  };
}

/**
 * Get date formatter for x-axis based on granularity.
 */
export function createDateFormatter(
  granularity: "day" | "week" | "month",
): (value: string) => string {
  return (value: string) => {
    const date = new Date(value);
    if (isNaN(date.getTime())) return value;

    switch (granularity) {
      case "day":
        return date.toLocaleDateString("en-US", {
          month: "short",
          day: "numeric",
        });
      case "week":
        return date.toLocaleDateString("en-US", {
          month: "short",
          day: "numeric",
        });
      case "month":
        return date.toLocaleDateString("en-US", {
          month: "short",
          year: "numeric",
        });
      default:
        return value;
    }
  };
}
