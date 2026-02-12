/**
 * SCurveChart Component
 *
 * Reusable ECharts-based component for displaying time series data with dual-line
 * comparison between Main Branch and Change Order MERGE mode. Supports Budget,
 * Planned Value (PV), Earned Value (EV), and Actual Cost (AC) metrics.
 *
 * Context: Used by MultiSCurveDisplay to show individual EVM metric progressions
 * in the change order impact analysis dashboard.
 *
 * @module features/change-orders/components
 */

import React, { useMemo, useRef } from "react";
import { Card, Typography, Button } from "antd";
import { DownloadOutlined } from "@ant-design/icons";
import type { TimeSeriesData } from "@/api/generated";
import { EChartsBaseChart } from "@/features/evm/components/charts/EChartsBaseChart";
import {
  buildTimeSeriesOptions,
  createCurrencyFormatter,
  createDateFormatter,
} from "@/features/evm/utils/echartsConfig";
import { useEChartsTheme } from "@/features/evm/utils/echartsTheme";
import type { EChartsOption } from "echarts";
import type ReactECharts from "echarts-for-react";

const { Title } = Typography;

/**
 * Supported EVM metrics for S-Curve charts.
 */
export type SCurveMetric = "budget" | "pv" | "ev" | "ac";

/**
 * Props for SCurveChart component.
 */
export interface SCurveChartProps {
  /** Chart title displayed in the card header */
  title: string;
  /** Metric name to determine color scheme and data extraction */
  metricName: SCurveMetric;
  /** Time series data containing main_value and change_value for each week */
  data: TimeSeriesData | undefined;
  /** Optional override color for the change order line */
  color?: string;
  /** Chart height in pixels (default: 300) */
  height?: number;
  /** Loading state */
  loading?: boolean;
  /** Show PNG export button (default: false) */
  showExport?: boolean;
  /** Additional CSS class name */
  className?: string;
}

/**
 * Default colors for each EVM metric.
 */
const METRIC_COLORS: Record<SCurveMetric, string> = {
  budget: "#5b8ff9", // Blue
  pv: "#5b8ff9", // Blue - same as budget
  ev: "#5ad8a6", // Green
  ac: "#5d7092", // Gray/Red
};

/**
 * Metric labels for display.
 */
const METRIC_LABELS: Record<SCurveMetric, string> = {
  budget: "Budget Allocation",
  pv: "Planned Value (PV)",
  ev: "Earned Value (EV)",
  ac: "Actual Cost (AC)",
};

/**
 * Transform TimeSeriesData to ECharts series format.
 *
 * @param data - Time series data from API
 * @returns Array of series objects with name and data points
 */
function transformToEChartsSeries(
  data: TimeSeriesData | undefined,
): Array<{ name: string; data: Array<[string, number]> }> {
  if (!data?.data_points || data.data_points.length === 0) {
    return [];
  }

  const mainData: Array<[string, number]> = [];
  const changeData: Array<[string, number]> = [];

  data.data_points.forEach((point) => {
    // Use week_start directly as ISO string for ECharts
    const dateStr = point.week_start;

    // Add main value if present (not null or undefined)
    if (point.main_value !== null && point.main_value !== undefined) {
      mainData.push([dateStr, Number(point.main_value)]);
    }

    // Add change value if present (not null or undefined)
    if (point.change_value !== null && point.change_value !== undefined) {
      changeData.push([dateStr, Number(point.change_value)]);
    }
  });

  return [
    { name: "Main Branch", data: mainData },
    { name: "Change Order (MERGE)", data: changeData },
  ];
}

/**
 * SCurveChart Component
 *
 * Displays a dual-line S-curve chart comparing Main Branch vs Change Order MERGE
 * for a single EVM metric. Uses ECharts for consistent styling and behavior.
 */
export const SCurveChart = React.forwardRef<
  ReactECharts | null,
  SCurveChartProps
>(
  (
    {
      title,
      metricName,
      data,
      color,
      height = 300,
      loading = false,
      showExport = false,
      className,
    },
    ref,
  ) => {
    const chartRef = useRef<ReactECharts | null>(null);
    const echartsTheme = useEChartsTheme();

    // Get color for this metric (use override if provided)
    const metricColor = color ?? METRIC_COLORS[metricName];

    // Transform data to ECharts series format
    const seriesData = useMemo(
      () => transformToEChartsSeries(data),
      [data],
    );

    // Build chart options
    const chartOption: EChartsOption = useMemo(() => {
      if (seriesData.length === 0) {
        return {};
      }

      return buildTimeSeriesOptions(
        {
          chartType: "evm-progression",
          series: [
            {
              name: "Main Branch",
              data: seriesData[0]?.data ?? [],
              color: echartsTheme.colors.textSecondary, // Gray for baseline
            },
            {
              name: "Change Order (MERGE)",
              data: seriesData[1]?.data ?? [],
              color: metricColor,
            },
          ],
          showZoom: false, // Disabled for smaller charts
          yFormatter: createCurrencyFormatter("EUR"),
          xFormatter: createDateFormatter("week"),
        },
        echartsTheme,
      );
    }, [seriesData, metricColor, echartsTheme]);

    /**
     * Export chart to PNG.
     */
    const handleExport = () => {
      const chart = chartRef.current?.getEchartsInstance();
      if (chart) {
        const url = chart.getDataURL({
          type: "png",
          pixelRatio: 2,
          backgroundColor: "#fff",
        });
        const link = document.createElement("a");
        link.href = url;
        link.download = `${metricName}-s-curve-${new Date().toISOString().split("T")[0]}.png`;
        link.click();
      }
    };

    // Chart card with optional export button
    const cardExtra = showExport ? (
      <Button
        type="text"
        icon={<DownloadOutlined />}
        onClick={handleExport}
        size="small"
      >
        Export
      </Button>
    ) : undefined;

    return (
      <Card
        title={<Title level={5}>{title}</Title>}
        extra={cardExtra}
        loading={loading}
        className={className}
        styles={{ body: { padding: 16 } }}
      >
        <EChartsBaseChart
          ref={(node) => {
            chartRef.current = node;
            // Handle forwarded ref
            if (typeof ref === "function") {
              ref(node);
            } else if (ref) {
              ref.current = node;
            }
          }}
          option={chartOption}
          height={height}
          loading={loading}
          showWhenEmpty={false}
          emptyDescription={`No ${METRIC_LABELS[metricName]} data available`}
        />
      </Card>
    );
  },
);

SCurveChart.displayName = "SCurveChart";

export default SCurveChart;
