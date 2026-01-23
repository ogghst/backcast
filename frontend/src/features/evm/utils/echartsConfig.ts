/**
 * ECharts Configuration Builders
 *
 * Utility functions to build ECharts option objects for different chart types.
 * Provides consistent configuration across all EVM charts.
 *
 * @module features/evm/utils/echartsConfig
 */

import type { EChartsOption } from "echarts";
import type { EChartsColorPalette, EChartsAxisConfig, EChartsTooltipConfig, EChartsLegendConfig } from "./echartsTheme";

/**
 * Build gauge chart options for EVM metrics (CPI, SPI).
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
  colors: EChartsColorPalette
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

  // Calculate zone angles
  const totalAngle = variant === "semi-circle" ? 180 : 360;
  const startAngle = variant === "semi-circle" ? 180 : 90;

  // Convert thresholds to percentages (0-100)
  const warningPercent = ((warningThreshold - min) / (max - min)) * 100;
  const goodPercent = ((goodThreshold - min) / (max - min)) * 100;

  return {
    series: [
      {
        type: "gauge",
        startAngle,
        endAngle: startAngle + totalAngle,
        radius: "90%",
        center: ["50%", variant === "semi-circle" ? "70%" : "50%"],
        min,
        max,
        splitNumber: 5,
        axisLine: {
          lineStyle: {
            width: 20,
            color: [
              [Math.max(0, Math.min(100, warningPercent)) / 100, colors.gaugeBad],
              [Math.max(0, Math.min(100, goodPercent)) / 100, colors.gaugeWarning],
              [1, colors.gaugeGood],
            ],
          },
        },
        pointer: {
          icon: variant === "semi-circle"
            ? "path://M12.8,0.7l12,40.1H0.7L12.8,0.7z"
            : "path://M2090.3,887.8l-18.4-294.1c-0.6-9.7-8.9-17.1-18.6-16.6c-9.7,0.6-17.1,8.9-16.6,18.6l14.3,228.7l-159.1-165.3c-6.9-7.2-18.3-7.4-25.5-0.5c-7.2,6.9-7.4,18.3-0.5,25.5l171.2,178c-3.5,6.4-5.5,13.8-5.5,21.7c0,24.2,19.6,43.8,43.8,43.8s43.8-19.6,43.8-43.8c0-11.9-4.8-22.7-12.5-30.6L2090.3,887.8z",
          length: variant === "semi-circle" ? "12%" : "60%",
          itemStyle: {
            color: "auto",
          },
        },
        axisTick: {
          distance: -20,
          length: 5,
          lineStyle: {
            color: colors.text,
            width: 1,
          },
        },
        splitLine: {
          distance: -20,
          length: 10,
          lineStyle: {
            color: colors.text,
            width: 2,
          },
        },
        axisLabel: {
          distance: -35,
          color: colors.text,
          fontSize: 12,
          formatter: (value: number) => value.toFixed(1),
        },
        detail: {
          valueAnimation: true,
          formatter: (value: number) => (value !== null ? value.toFixed(2) : "N/A"),
          fontSize: 24,
          fontWeight: "bold",
          color: colors.text,
          offsetCenter: variant === "semi-circle" ? [0, "30%"] : [0, "80%"],
        },
        title: {
          offsetCenter: variant === "semi-circle" ? [0, "-10%"] : [0, "-50%"],
          fontSize: 14,
          color: colors.textSecondary,
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
  | "cost-comparison"; // Forecast vs Actual

/**
 * Build time series chart options for EVM analysis.
 */
export interface TimeSeriesConfigOptions {
  /** Chart type */
  chartType: TimeSeriesChartType;
  /** Series data - array of objects with name, data points */
  series: Array<{
    name: string;
    data: Array<[string, number]>; // [date, value] tuples
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
  }
): EChartsOption {
  const { colors, axisConfig, tooltipConfig, legendConfig } = theme;

  const {
    // chartType, // Not used in options, kept for interface consistency
    series,
    showZoom = true,
    dualYAxis = false,
    yFormatter = (v) => v.toString(),
    xFormatter = (v) => v,
    // height, // Not used in options, controlled by component
  } = options;

  // Default colors based on series name
  const defaultColors: Record<string, string> = {
    PV: colors.pv,
    EV: colors.ev,
    AC: colors.ac,
    Forecast: colors.forecast,
    Actual: colors.actual,
  };

  return {
    color: series.map((s) => s.color ?? defaultColors[s.name] ?? colors.primary),
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
          result += `<div style="display: flex; justify-content: space-between; gap: 16px;">
            <span style="display: flex; align-items: center;">
              <span style="display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: ${param.color}; margin-right: 6px;"></span>
              ${param.seriesName}
            </span>
            <span style="font-weight: 600;">${yFormatter(param.value)}</span>
          </div>`;
        });
        return result;
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
    yAxis: series.slice(0, dualYAxis ? 2 : 1).map((_s, index) => ({
      type: "value" as const,
      position: dualYAxis && index === 1 ? "right" : "left",
      ...axisConfig,
      axisLabel: {
        ...axisConfig.axisLabel,
        formatter: yFormatter,
      },
      splitLine: {
        ...axisConfig.splitLine,
        show: index === 0,
      },
    })),
    series: series.map((s, index) => ({
      name: s.name,
      type: "line" as const,
      data: s.data,
      smooth: true,
      symbol: "circle" as const,
      symbolSize: 6,
      yAxisIndex: dualYAxis && index >= 2 ? 1 : 0,
      emphasis: {
        focus: "series" as const,
      },
    })),
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
export function createCurrencyFormatter(currency: string = "EUR"): (value: number) => string {
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
export function createDateFormatter(granularity: "day" | "week" | "month"): (value: string) => string {
  return (value: string) => {
    const date = new Date(value);
    if (isNaN(date.getTime())) return value;

    switch (granularity) {
      case "day":
        return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
      case "week":
        return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
      case "month":
        return date.toLocaleDateString("en-US", { month: "short", year: "numeric" });
      default:
        return value;
    }
  };
}
