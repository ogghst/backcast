/**
 * CostHistoryChart Component
 *
 * Displays cost history trends at cost element, WBE, or project level.
 * Two charts: Burn Rate (bar) and Cumulative Cost Trend (line/S-curve).
 */

import { useMemo, useState } from "react";
import { Card, Radio, Space, Typography } from "antd";
import type { EChartsOption } from "echarts";
import { EChartsBaseChart } from "@/features/evm/components/charts/EChartsBaseChart";
import { useEChartsTheme } from "@/features/evm/utils/echartsTheme";
import {
  createCurrencyFormatter,
  createDateFormatter,
} from "@/features/evm/utils/echartsConfig";
import {
  useAggregatedCosts,
  useCumulativeCosts,
} from "@/features/cost-registration/api/useCostRegistrations";

const { Title } = Typography;

type CostGranularity = "daily" | "weekly" | "monthly";
type CostEntityType = "cost_element" | "wbe" | "project";

interface AggregatedCostPoint {
  period_start: string;
  total_amount: number;
}

interface CumulativeCostPoint {
  registration_date: string;
  amount: number;
  cumulative_amount: number;
}

export interface CostHistoryChartProps {
  entityType: CostEntityType;
  entityId: string;
  budgetAmount?: number;
  height?: number;
  headless?: boolean;
  delayRender?: boolean;
}

const SIX_MONTHS_AGO = new Date(
  new Date().setMonth(new Date().getMonth() - 6),
).toISOString();

const GRANULARITY_MAP: Record<CostGranularity, "day" | "week" | "month"> = {
  daily: "day",
  weekly: "week",
  monthly: "month",
};

/** Shared dataZoom configuration for cost charts. */
const DATA_ZOOM: EChartsOption["dataZoom"] = [
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
];

/** Shared grid configuration for cost charts. */
const CHART_GRID = {
  left: "3%",
  right: "3%",
  bottom: "15%",
  top: "8%",
  containLabel: true,
};

/**
 * Build a tooltip formatter for cost charts.
 * Renders a colored dot + label + formatted amount.
 */
const buildCostTooltipFormatter =
  (
    label: string,
    dateFormatter: (v: string) => string,
    currencyFormatter: (v: number) => string,
  ) =>
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  (params: any) => {
    if (!Array.isArray(params) || params.length === 0) return "";
    const p = params[0];
    const dateLabel = dateFormatter(
      Array.isArray(p.value) ? p.value[0] : p.axisValue,
    );
    const amount = Array.isArray(p.value) ? p.value[1] : p.value;
    return `<div style="font-weight: 600; margin-bottom: 4px;">${dateLabel}</div>
      <div style="display: flex; justify-content: space-between; gap: 16px;">
        <span style="display: flex; align-items: center;">
          <span style="display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: ${p.color}; margin-right: 6px;"></span>
          ${label}
        </span>
        <span style="font-weight: 600;">${currencyFormatter(amount)}</span>
      </div>`;
  };

export const CostHistoryChart = ({
  entityType,
  entityId,
  budgetAmount,
  height = 300,
  headless = false,
  delayRender = false,
}: CostHistoryChartProps) => {
  const [granularity, setGranularity] = useState<CostGranularity>("weekly");

  const { data: aggregatedData, isLoading: aggregatedLoading, error: aggregatedError } =
    useAggregatedCosts(entityType, entityId, granularity, SIX_MONTHS_AGO);

  const { data: cumulativeData, isLoading: cumulativeLoading, error: cumulativeError } =
    useCumulativeCosts(entityType, entityId, SIX_MONTHS_AGO);

  const echartsTheme = useEChartsTheme();
  const currencyFormatter = useMemo(() => createCurrencyFormatter("EUR"), []);
  const dateFormatter = useMemo(
    () => createDateFormatter(GRANULARITY_MAP[granularity]),
    [granularity],
  );

  const isLoading = aggregatedLoading || cumulativeLoading;

  // Burn Rate bar chart
  const burnRateOptions = useMemo<EChartsOption | null>(() => {
    const data = aggregatedData as AggregatedCostPoint[] | undefined;
    if (!data || data.length === 0) return null;

    return {
      color: [echartsTheme.colors.primary],
      tooltip: {
        ...echartsTheme.tooltipConfig,
        trigger: "axis" as const,
        axisPointer: { type: "shadow" as const },
        formatter: buildCostTooltipFormatter("Burn Rate", dateFormatter, currencyFormatter),
      },
      grid: CHART_GRID,
      xAxis: {
        type: "time" as const,
        ...echartsTheme.axisConfig,
        axisLabel: { ...echartsTheme.axisConfig.axisLabel, formatter: dateFormatter },
      },
      yAxis: {
        type: "value" as const,
        ...echartsTheme.axisConfig,
        axisLabel: {
          ...echartsTheme.axisConfig.axisLabel,
          formatter: (v: number) => currencyFormatter(v),
        },
      },
      series: [
        {
          name: "Burn Rate",
          type: "bar" as const,
          data: data.map((d) => [d.period_start, d.total_amount]),
          itemStyle: { color: echartsTheme.colors.primary, borderRadius: [4, 4, 0, 0] },
          emphasis: { focus: "series" as const },
        },
      ],
      dataZoom: DATA_ZOOM,
    };
  }, [aggregatedData, echartsTheme, currencyFormatter, dateFormatter]);

  // Cumulative Cost line chart
  const cumulativeOptions = useMemo<EChartsOption | null>(() => {
    const data = cumulativeData as CumulativeCostPoint[] | undefined;
    if (!data || data.length === 0) return null;

    return {
      color: [echartsTheme.colors.ac],
      tooltip: {
        ...echartsTheme.tooltipConfig,
        trigger: "axis" as const,
        formatter: buildCostTooltipFormatter("Cumulative", dateFormatter, currencyFormatter),
      },
      grid: CHART_GRID,
      xAxis: {
        type: "time" as const,
        ...echartsTheme.axisConfig,
        axisLabel: { ...echartsTheme.axisConfig.axisLabel, formatter: dateFormatter },
      },
      yAxis: {
        type: "value" as const,
        ...echartsTheme.axisConfig,
        axisLabel: {
          ...echartsTheme.axisConfig.axisLabel,
          formatter: (v: number) => currencyFormatter(v),
        },
      },
      series: [
        {
          name: "Cumulative Cost",
          type: "line" as const,
          data: data.map((d) => [d.registration_date, d.cumulative_amount]),
          smooth: true,
          symbol: "circle" as const,
          symbolSize: 4,
          lineStyle: { color: echartsTheme.colors.ac, width: 2 },
          itemStyle: { color: echartsTheme.colors.ac },
          areaStyle: {
            color: {
              type: "linear" as const,
              x: 0, y: 0, x2: 0, y2: 1,
              colorStops: [
                { offset: 0, color: echartsTheme.colors.ac + "33" },
                { offset: 1, color: "transparent" },
              ],
            } as const,
          },
          ...(budgetAmount !== undefined && {
            markLine: {
              silent: true,
              symbol: "none",
              label: {
                show: true,
                position: "end" as const,
                formatter: `Budget: ${currencyFormatter(budgetAmount)}`,
                fontSize: 11,
                color: echartsTheme.colors.error,
              },
              lineStyle: {
                type: "dashed" as const,
                color: echartsTheme.colors.error,
                width: 2,
              },
              data: [{ yAxis: budgetAmount }],
            },
          }),
        },
      ],
      dataZoom: DATA_ZOOM,
    };
  }, [cumulativeData, echartsTheme, currencyFormatter, dateFormatter, budgetAmount]);

  const hasAggregatedData =
    !!aggregatedData && (aggregatedData as AggregatedCostPoint[]).length > 0;
  const hasCumulativeData =
    !!cumulativeData && (cumulativeData as CumulativeCostPoint[]).length > 0;

  const chartContent = (
    <Space direction="vertical" size="middle" style={{ width: "100%" }}>
      <div style={{ display: "flex", justifyContent: "flex-end" }}>
        <Radio.Group
          value={granularity}
          onChange={(e) => setGranularity(e.target.value as CostGranularity)}
          size="small"
        >
          <Radio.Button value="daily">Daily</Radio.Button>
          <Radio.Button value="weekly">Weekly</Radio.Button>
          <Radio.Button value="monthly">Monthly</Radio.Button>
        </Radio.Group>
      </div>

      <div>
        <Title level={5} style={{ marginBottom: 8 }}>Burn Rate (Costs per Period)</Title>
        <EChartsBaseChart
          option={burnRateOptions ?? {}}
          loading={aggregatedLoading}
          error={aggregatedError?.message ?? null}
          height={height}
          emptyDescription={
            burnRateOptions
              ? "No cost data for the selected period"
              : "No aggregated cost data available"
          }
          delayRender={delayRender}
        />
      </div>

      <div>
        <Title level={5} style={{ marginBottom: 8 }}>Cumulative Cost Trend</Title>
        <EChartsBaseChart
          option={cumulativeOptions ?? {}}
          loading={cumulativeLoading}
          error={cumulativeError?.message ?? null}
          height={height}
          emptyDescription="No cumulative cost data available"
          delayRender={delayRender}
        />
      </div>
    </Space>
  );

  if (headless) {
    return chartContent;
  }

  return (
    <Card
      title={<Title level={4} style={{ margin: 0 }}>Cost History</Title>}
      loading={isLoading && !hasAggregatedData && !hasCumulativeData}
    >
      {chartContent}
    </Card>
  );
};

export default CostHistoryChart;
