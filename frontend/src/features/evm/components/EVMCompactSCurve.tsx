import { useMemo } from "react";
import { Skeleton, theme } from "antd";
import type { EChartsOption } from "echarts";

import { EChartsBaseChart } from "./charts/EChartsBaseChart";
import { useEChartsTheme } from "../utils/echartsTheme";
import {
  transformEVMProgressionData,
  forwardFillNulls,
} from "../utils/dataTransformers";
import { formatValue } from "../utils/formatters";
import type { EVMTimeSeriesResponse } from "../types";

interface EVMCompactSCurveProps {
  timeSeries?: EVMTimeSeriesResponse;
  loading?: boolean;
  height?: number;
}

export const EVMCompactSCurve: React.FC<EVMCompactSCurveProps> = ({
  timeSeries,
  loading = false,
  height = 220,
}) => {
  const { token } = theme.useToken();
  const { colors, tooltipConfig } = useEChartsTheme();

  const option = useMemo<EChartsOption>(() => {
    if (!timeSeries) return {};

    const series = transformEVMProgressionData(timeSeries);
    const pvData = forwardFillNulls(series[0].data);
    const evData = forwardFillNulls(series[1].data);
    const acData = forwardFillNulls(series[2].data);

    return {
      grid: {
        top: 16,
        right: 16,
        bottom: 32,
        left: 56,
      },
      xAxis: {
        type: "category",
        data: pvData.map(([d]) => d),
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: {
          color: token.colorTextSecondary,
          fontSize: 11,
          rotate: pvData.length > 12 ? 45 : 0,
          formatter: (value: string) => {
            const d = new Date(value);
            return `${d.getDate()}/${d.getMonth() + 1}`;
          },
        },
      },
      yAxis: {
        type: "value",
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: {
          color: token.colorTextSecondary,
          fontSize: 11,
          formatter: (value: number) => formatValue(value, "currency"),
        },
        splitLine: {
          lineStyle: {
            color: token.colorBorderSecondary,
            type: "dashed" as const,
          },
        },
      },
      tooltip: {
        ...tooltipConfig,
        trigger: "axis",
        formatter: (params: unknown) => {
          type TooltipItem = {
            seriesName: string;
            value: number;
            color: string;
            axisValue: string;
            axisValueLabel: string;
          };
          const items = params as TooltipItem[];
          if (!Array.isArray(items) || items.length === 0) return "";
          const date = items[0].axisValueLabel || items[0].axisValue;
          let html = `<div style="margin-bottom:4px;font-weight:600">${date}</div>`;
          for (const item of items) {
            html += `<div style="display:flex;align-items:center;gap:6px">
              <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${item.color}"></span>
              <span>${item.seriesName}: ${formatValue(item.value, "currency")}</span>
            </div>`;
          }
          return html;
        },
      },
      series: [
        {
          name: "PV",
          type: "line",
          data: pvData.map(([, v]) => v),
          lineStyle: { color: colors.pv, type: "dashed" as const, width: 1.5 },
          itemStyle: { color: colors.pv },
          symbol: "none",
          areaStyle: { color: colors.pv, opacity: 0.08 },
          smooth: true,
        },
        {
          name: "EV",
          type: "line",
          data: evData.map(([, v]) => v),
          lineStyle: { color: colors.ev, width: 2 },
          itemStyle: { color: colors.ev },
          symbol: "none",
          areaStyle: { color: colors.ev, opacity: 0.12 },
          smooth: true,
        },
        {
          name: "AC",
          type: "line",
          data: acData.map(([, v]) => v),
          lineStyle: { color: colors.ac, width: 2 },
          itemStyle: { color: colors.ac },
          symbol: "none",
          areaStyle: { color: colors.ac, opacity: 0.12 },
          smooth: true,
        },
      ],
    };
  }, [timeSeries, colors, tooltipConfig, token]);

  if (!timeSeries && !loading) {
    return <Skeleton paragraph={{ rows: 4 }} style={{ height }} active />;
  }

  return (
    <EChartsBaseChart
      option={option}
      loading={loading}
      height={height}
      showWhenEmpty
    />
  );
};
