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
import { antDesignTheme } from "./echartsTheme";

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

/**
 * Build budget overview grouped bar chart options.
 *
 * Compares BAC, Actual Cost, Earned Value, and EAC as a grouped bar chart.
 * If EAC is null, only the first 3 bars are shown.
 *
 * @param options - Budget overview configuration
 * @param colors - Color palette from useEChartsColors()
 * @returns ECharts option object
 */
export interface BudgetOverviewConfigOptions {
  /** EVM metrics for the budget comparison */
  metrics: {
    bac: number;
    ac: number;
    ev: number;
    eac: number | null;
  };
  /** Currency formatter for axis and tooltip (defaults to raw number) */
  currencyFormatter?: (v: number) => string;
}

export function buildBudgetOverviewOptions(
  options: BudgetOverviewConfigOptions,
  colors: EChartsColorPalette,
): EChartsOption {
  const { metrics, currencyFormatter: fmt } = options;
  const formatValue = fmt ?? ((v: number) => v.toString());

  const categories = ["BAC", "Actual Cost", "Earned Value"];
  const values = [metrics.bac, metrics.ac, metrics.ev];
  const barColors = ["#5b8ff9", "#5d7092", "#5ad8a6"];

  if (metrics.eac !== null) {
    categories.push("EAC");
    values.push(metrics.eac);
    barColors.push("#faad14");
  }

  return {
    color: barColors,
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "shadow" },
      formatter: (params: unknown) => {
        if (!Array.isArray(params) || params.length === 0) return "";
        return params
          .map(
            (p: { seriesName: string; value: number; color: string }) =>
              `<div style="display: flex; justify-content: space-between; gap: 16px;">
              <span style="display: flex; align-items: center;">
                <span style="display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: ${p.color}; margin-right: 6px;"></span>
                ${p.seriesName}
              </span>
              <span style="font-weight: 600;">${formatValue(p.value)}</span>
            </div>`,
          )
          .join("");
      },
    },
    legend: {
      bottom: 0,
      textStyle: { color: colors.text, fontSize: 12 },
      itemGap: 16,
      itemWidth: 16,
      itemHeight: 12,
    },
    grid: {
      left: "3%",
      right: "3%",
      bottom: "12%",
      top: "8%",
      containLabel: true,
    },
    xAxis: {
      type: "category",
      data: ["Budget Analysis"],
      axisLabel: { color: colors.textSecondary, fontSize: 12 },
      axisLine: { lineStyle: { color: colors.border } },
      axisTick: { lineStyle: { color: colors.border } },
    },
    yAxis: {
      type: "value",
      axisLabel: {
        color: colors.textSecondary,
        fontSize: 12,
        formatter: (v: number) => formatValue(v),
      },
      splitLine: {
        lineStyle: { color: colors.border, type: "dashed" },
      },
    },
    series: categories.map((name, index) => ({
      name,
      type: "bar" as const,
      barWidth: "40%",
      data: [values[index]],
      itemStyle: {
        color: barColors[index],
        borderRadius: [4, 4, 0, 0],
      },
    })),
  };
}

/**
 * Build variance horizontal bar chart options.
 *
 * Displays Cost Variance (CV) and Schedule Variance (SV) as horizontal bars,
 * colored green for positive values and red for negative values.
 *
 * @param options - Variance bar configuration
 * @param colors - Color palette from useEChartsColors()
 * @returns ECharts option object
 */
export interface VarianceBarConfigOptions {
  /** Variance metrics */
  metrics: {
    cv: number;
    sv: number;
  };
  /** Currency formatter for tooltip (defaults to raw number) */
  currencyFormatter?: (v: number) => string;
}

export function buildVarianceBarOptions(
  options: VarianceBarConfigOptions,
  colors: EChartsColorPalette,
): EChartsOption {
  const { metrics, currencyFormatter: fmt } = options;
  const formatValue = fmt ?? ((v: number) => v.toString());

  const categories = ["Cost Variance (CV)", "Schedule Variance (SV)"];
  const values = [metrics.cv, metrics.sv];

  return {
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "shadow" },
      formatter: (params: unknown) => {
        if (!Array.isArray(params) || params.length === 0) return "";
        const p = params[0] as {
          name: string;
          value: number;
          color: string;
        };
        return `<div style="display: flex; justify-content: space-between; gap: 16px;">
          <span style="display: flex; align-items: center;">
            <span style="display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: ${p.color}; margin-right: 6px;"></span>
            ${p.name}
          </span>
          <span style="font-weight: 600;">${formatValue(p.value)}</span>
        </div>`;
      },
    },
    grid: {
      left: "3%",
      right: "3%",
      bottom: "6%",
      top: "6%",
      containLabel: true,
    },
    xAxis: {
      type: "value",
      axisLabel: {
        color: colors.textSecondary,
        fontSize: 12,
        formatter: (v: number) => formatValue(v),
      },
      splitLine: {
        lineStyle: { color: colors.border, type: "dashed" },
      },
    },
    yAxis: {
      type: "category",
      data: categories,
      axisLabel: { color: colors.textSecondary, fontSize: 12 },
      axisLine: { lineStyle: { color: colors.border } },
      axisTick: { show: false },
    },
    series: [
      {
        type: "bar" as const,
        barWidth: "40%",
        data: values.map((v) => ({
          value: v,
          itemStyle: {
            color: v >= 0 ? colors.success : colors.error,
            borderRadius: v >= 0 ? [0, 4, 4, 0] : [4, 0, 0, 4],
          },
        })),
        markLine: {
          silent: true,
          symbol: "none",
          lineStyle: {
            type: "solid" as const,
            color: colors.textSecondary,
            width: 1,
          },
          label: { show: false },
          data: [{ xAxis: 0 }],
        },
      },
    ],
  };
}

/**
 * Build performance radar chart options.
 *
 * Displays CPI, SPI, and progress percentage on a radar chart with a
 * target reference overlay. All values are normalized to 0-1 scale for
 * consistent radar display while labels show actual scales.
 *
 * @param options - Performance radar configuration
 * @param colors - Color palette from useEChartsColors()
 * @returns ECharts option object
 */
export interface PerformanceRadarConfigOptions {
  /** Performance metrics */
  metrics: {
    cpi: number | null;
    spi: number | null;
    progress_percentage: number;
  };
}

export function buildPerformanceRadarOptions(
  options: PerformanceRadarConfigOptions,
  colors: EChartsColorPalette,
): EChartsOption {
  const { metrics } = options;

  // Normalize values to 0-1 scale: cpi/2, spi/2, progress/100
  const actualValues = [
    metrics.cpi !== null ? metrics.cpi / 2 : 0,
    metrics.spi !== null ? metrics.spi / 2 : 0,
    metrics.progress_percentage / 100,
  ];

  // Target values normalized to same scale
  const targetValues = [1.0 / 2, 1.0 / 2, 50 / 100];

  return {
    tooltip: {
      formatter: (params: unknown) => {
        if (!Array.isArray(params) || params.length === 0) return "";
        return params
          .map((p: { seriesName: string; value: number[] }) => {
            const cpi = metrics.cpi !== null ? metrics.cpi.toFixed(2) : "N/A";
            const spi = metrics.spi !== null ? metrics.spi.toFixed(2) : "N/A";
            const progress = `${metrics.progress_percentage.toFixed(1)}%`;
            if (p.seriesName === "Actual") {
              return `<div style="font-weight: 600; margin-bottom: 4px;">${p.seriesName}</div>
                <div>CPI: ${cpi}</div>
                <div>SPI: ${spi}</div>
                <div>Progress: ${progress}</div>`;
            }
            return `<div style="font-weight: 600; margin-bottom: 4px;">${p.seriesName}</div>
              <div>CPI: 1.00</div>
              <div>SPI: 1.00</div>
              <div>Progress: 50%</div>`;
          })
          .join("<hr style=\"margin: 4px 0; border: none; border-top: 1px solid #ddd;\" />");
      },
    },
    legend: {
      bottom: 0,
      textStyle: { color: colors.text, fontSize: 12 },
      itemGap: 16,
      itemWidth: 16,
      itemHeight: 12,
    },
    radar: {
      shape: "polygon" as const,
      indicator: [
        { name: "CPI", max: 1 },
        { name: "SPI", max: 1 },
        { name: "Progress", max: 1 },
      ],
      axisName: {
        color: colors.textSecondary,
        fontSize: 12,
        formatter: (value: string) => {
          if (value === "CPI" || value === "SPI") return `${value} (max 2)`;
          return `${value} (max 100%)`;
        },
      },
      splitArea: {
        areaStyle: { color: ["transparent"] },
      },
      axisLine: { lineStyle: { color: colors.border } },
      splitLine: { lineStyle: { color: colors.border } },
    },
    series: [
      {
        type: "radar" as const,
        data: [
          {
            value: actualValues,
            name: "Actual",
            areaStyle: { color: colors.primary, opacity: 0.3 },
            lineStyle: { color: colors.primary, width: 2 },
            itemStyle: { color: colors.primary },
          },
          {
            value: targetValues,
            name: "Target",
            lineStyle: { color: colors.success, width: 2, type: "dashed" },
            itemStyle: { color: colors.success },
            areaStyle: { opacity: 0 },
          },
        ],
      },
    ],
  };
}

/**
 * Build donut/pie chart options for budget distribution.
 *
 * Displays budget items as a donut chart with optional center label
 * showing total value. Uses the Ant Design theme color palette.
 *
 * @param options - Donut chart configuration
 * @param colors - Color palette from useEChartsColors()
 * @returns ECharts option object
 */
export interface DonutConfigOptions {
  /** Budget items to display as donut segments */
  items: Array<{
    name: string;
    value: number;
  }>;
  /** Label displayed above the center value */
  centerLabel?: string;
  /** Value displayed in the donut center */
  centerValue?: string;
}

export function buildDonutOptions(
  options: DonutConfigOptions,
  colors: EChartsColorPalette,
): EChartsOption {
  const { items, centerLabel, centerValue } = options;

  const sliceColors = antDesignTheme.color;

  const showCenter = centerLabel !== undefined || centerValue !== undefined;

  return {
    tooltip: {
      trigger: "item",
      formatter: (params: unknown) => {
        const p = params as {
          name: string;
          value: number;
          percent: number;
        };
        return `<div style="font-weight: 600; margin-bottom: 4px;">${p.name}</div>
          <div>Value: ${createCurrencyFormatter()(p.value)}</div>
          <div>Share: ${p.percent.toFixed(1)}%</div>`;
      },
    },
    legend: {
      bottom: 0,
      type: "scroll",
      textStyle: { color: colors.text, fontSize: 12 },
      itemGap: 16,
      itemWidth: 16,
      itemHeight: 12,
    },
    series: [
      {
        type: "pie" as const,
        radius: ["45%", "70%"],
        center: ["50%", "48%"],
        avoidLabelOverlap: true,
        itemStyle: {
          borderRadius: 4,
        },
        label: {
          show: false,
        },
        emphasis: {
          label: {
            show: true,
            fontSize: 14,
            fontWeight: "bold" as const,
            color: colors.text,
          },
        },
        labelLine: { show: false },
        data: items.map((item, index) => ({
          name: item.name,
          value: item.value,
          itemStyle: {
            color: sliceColors[index % sliceColors.length],
          },
        })),
        ...(showCenter && {
          label: {
            show: true,
            position: "center" as const,
            formatter: () => "",
          },
        }),
      },
    ],
    ...(showCenter && {
      graphic: [
        {
          type: "text" as const,
          left: "center",
          top: "42%",
          style: {
            text: centerValue ?? "",
            fontSize: 20,
            fontWeight: 600,
            fill: colors.text,
            textAlign: "center" as const,
          },
        },
        {
          type: "text" as const,
          left: "center",
          top: "52%",
          style: {
            text: centerLabel ?? "",
            fontSize: 12,
            fill: colors.textSecondary,
            textAlign: "center" as const,
          },
        },
      ],
    }),
  };
}

/**
 * Build mini sparkline chart options for trend indicators.
 *
 * Ultra-compact line chart with no axes, labels, legend, or tooltip.
 * Designed for embedding in metric cards as a trend indicator.
 *
 * @param options - Sparkline configuration
 * @param colors - Color palette from useEChartsColors()
 * @returns ECharts option object
 */
export interface MiniSparklineConfigOptions {
  /** Data points as [label, value] tuples (null values are connected) */
  data: Array<[string, number | null]>;
  /** Line color (defaults to primary) */
  color?: string;
  /** Show gradient area fill beneath the line */
  showArea?: boolean;
}

export function buildMiniSparklineOptions(
  options: MiniSparklineConfigOptions,
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  _colors: EChartsColorPalette,
): EChartsOption {
  const { data, color = "#5b8ff9", showArea = false } = options;

  return {
    grid: {
      left: 0,
      right: 0,
      top: 0,
      bottom: 0,
    },
    xAxis: {
      type: "category",
      show: false,
      data: data.map((d) => d[0]),
    },
    yAxis: {
      type: "value",
      show: false,
    },
    series: [
      {
        type: "line" as const,
        data: data.map((d) => d[1]),
        smooth: true,
        connectNulls: true,
        symbol: "none",
        lineStyle: {
          color,
          width: 2,
        },
        ...(showArea && {
          areaStyle: {
            color: {
              type: "linear" as const,
              x: 0,
              y: 0,
              x2: 0,
              y2: 1,
              colorStops: [
                { offset: 0, color },
                { offset: 1, color: "transparent" },
              ],
            } as const,
          },
        }),
      },
    ],
    tooltip: { show: false },
    legend: { show: false },
  };
}
