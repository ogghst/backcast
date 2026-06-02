/**
 * CostHistoryChart Component
 *
 * Displays Planned Value vs Earned Value at project or WBE level
 * with weekly resolution.
 */

import { useMemo } from "react";
import { Card, Typography } from "antd";

import { EChartsBaseChart } from "@/features/evm/components/charts/EChartsBaseChart";
import { useEChartsTheme } from "@/features/evm/utils/echartsTheme";
import {
  createCurrencyFormatter,
  createDateFormatter,
} from "@/features/evm/utils/echartsConfig";
import { useEVMTimeSeries } from "@/features/evm/api/useEVMMetrics";
import type { EVMTimeSeriesPoint } from "@/features/evm/types";
import { EntityType, EVMTimeSeriesGranularity } from "@/features/evm/types";
import { useProjectCurrency } from "@/features/projects/api/useProjectCurrency";

const { Title } = Typography;

type CostEntityType = "cost_element" | "wbs_element" | "project" | "work_package";

const ENTITY_TYPE_MAP: Record<CostEntityType, EntityType> = {
  cost_element: EntityType.COST_ELEMENT,
  wbs_element: EntityType.WBS_ELEMENT,
  project: EntityType.PROJECT,
  work_package: EntityType.WORK_PACKAGE,
};

export interface CostHistoryChartProps {
  entityType: CostEntityType;
  entityId: string;
  height?: number;
  headless?: boolean;
  delayRender?: boolean;
  controlDate?: string;
  projectId?: string;
}

/** Grid configuration for the chart. */
const CHART_GRID = {
  left: "3%",
  right: "3%",
  bottom: "14%",
  top: "6%",
  containLabel: true,
};

export const CostHistoryChart = ({
  entityType,
  entityId,
  height = 200,
  headless = false,
  delayRender = false,
  controlDate,
  projectId,
}: CostHistoryChartProps) => {
  const { data: tsData, isLoading, error } = useEVMTimeSeries(
    ENTITY_TYPE_MAP[entityType],
    entityId,
    EVMTimeSeriesGranularity.WEEK,
    { controlDate } as Parameters<typeof useEVMTimeSeries>[3],
  );

  const echartsTheme = useEChartsTheme();
  const currency = useProjectCurrency(projectId);
  const currencyFormatter = useMemo(() => createCurrencyFormatter(currency), [currency]);
  const dateFormatter = useMemo(() => createDateFormatter("week"), []);

  const points = tsData?.points as EVMTimeSeriesPoint[] | undefined;

  const chartOptions = useMemo(() => {
    if (!points || points.length === 0) return null;

    const pvData = points.map((p) => [p.date, p.pv]);
    const evData = points.map((p) => [p.date, p.ev]);
    const acData = points.map((p) => [p.date, p.ac]);

    return {
      color: [echartsTheme.colors.pv, echartsTheme.colors.ev, echartsTheme.colors.ac],
      legend: {
        data: ["PV", "EV", "AC"],
        bottom: 0,
        left: "center",
        itemGap: 16,
        textStyle: { fontSize: 11, color: echartsTheme.colors.textSecondary },
      },
      tooltip: {
        ...echartsTheme.tooltipConfig,
        trigger: "axis" as const,
        formatter: (params: unknown) => {
          const p = params as { color: string; seriesName: string; value: [string, number] }[];
          if (!Array.isArray(p) || p.length === 0) return "";
          const dateLabel = dateFormatter(p[0].value[0]);
          const rows = p
            .map(
              (item) =>
                `<span style="display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: ${item.color}; margin-right: 6px;"></span>${item.seriesName}<span style="float: right; font-weight: 600; margin-left: 16px;">${currencyFormatter(item.value[1])}</span>`,
            )
            .join("<br/>");
          return `<div style="font-weight: 600; margin-bottom: 4px;">${dateLabel}</div>${rows}`;
        },
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
          formatter: (v: number) => {
            if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(v % 1_000_000 === 0 ? 0 : 1)}m`;
            if (v >= 1_000) return `${(v / 1_000).toFixed(v % 1_000 === 0 ? 0 : 1)}k`;
            return String(v);
          },
        },
      },
      series: [
        {
          name: "PV",
          type: "line" as const,
          data: pvData,
          smooth: true,
          symbol: "circle" as const,
          symbolSize: 3,
          lineStyle: { width: 2 },
          itemStyle: { color: echartsTheme.colors.pv },
        },
        {
          name: "EV",
          type: "line" as const,
          data: evData,
          smooth: true,
          symbol: "circle" as const,
          symbolSize: 3,
          lineStyle: { width: 2 },
          itemStyle: { color: echartsTheme.colors.ev },
          areaStyle: {
            color: {
              type: "linear" as const,
              x: 0, y: 0, x2: 0, y2: 1,
              colorStops: [
                { offset: 0, color: echartsTheme.colors.ev + "22" },
                { offset: 1, color: "transparent" },
              ],
            } as const,
          },
        },
        {
          name: "AC",
          type: "line" as const,
          data: acData,
          smooth: true,
          symbol: "circle" as const,
          symbolSize: 3,
          lineStyle: { width: 2 },
          itemStyle: { color: echartsTheme.colors.ac },
        },
      ],
    };
  }, [points, echartsTheme, currencyFormatter, dateFormatter]);

  const chartContent = (
    <div>
      <EChartsBaseChart
        option={chartOptions ?? {}}
        loading={isLoading}
        error={error?.message ?? null}
        height={height}
        emptyDescription="No EVM time-series data available"
        delayRender={delayRender}
      />
    </div>
  );

  if (headless) {
    return chartContent;
  }

  return (
    <Card
      title={<Title level={4} style={{ margin: 0 }}>Cost History</Title>}
      loading={isLoading && !points?.length}
    >
      {chartContent}
    </Card>
  );
};

export default CostHistoryChart;
