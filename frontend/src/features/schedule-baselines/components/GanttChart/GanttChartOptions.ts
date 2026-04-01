/**
 * Gantt Chart ECharts Options Builder
 *
 * Builds the ECharts option object for the Gantt chart, including
 * custom renderItem for bars, dataZoom, tooltip, and today marker.
 *
 * @module features/schedule-baselines/components/GanttChart
 */

import type { EChartsOption } from "echarts";
import type { EChartsColorPalette, EChartsTooltipConfig } from "@/features/evm/utils/echartsTheme";
import type { GanttRow } from "./GanttDataTransformer";
import { formatRowLabel } from "./GanttDataTransformer";

/** Color mapping for progression types. */
const PROGRESSION_COLORS: Record<string, string> = {
  LINEAR: "#5b8ff9",
  GAUSSIAN: "#5ad8a6",
  LOGARITHMIC: "#faad14",
};

/**
 * Build ECharts option for the Gantt chart.
 *
 * @param rows - Transformed GanttRow array
 * @param projectStart - Project start date for x-axis range
 * @param projectEnd - Project end date for x-axis range
 * @param colors - Color palette from useEChartsColors()
 * @param tooltipConfig - Tooltip config from useEChartsTheme()
 */
export function buildGanttOptions(
  rows: GanttRow[],
  projectStart: Date | null,
  projectEnd: Date | null,
  colors: EChartsColorPalette,
  tooltipConfig: EChartsTooltipConfig,
  gridLeft: number = 220,
): EChartsOption {
  const yLabels = rows.map((row) => formatRowLabel(row));

  // Build series data: each bar is [yIndex, startTimestamp, endTimestamp, row]
  // Include any row with valid dates (WBE rows with aggregated dates and cost elements)
  const barData: Array<[number, number, number, GanttRow]> = [];
  rows.forEach((row, index) => {
    if (row.startDate && row.endDate) {
      barData.push([index, row.startDate.getTime(), row.endDate.getTime(), row]);
    }
  });

  // Determine x-axis range
  const now = new Date();
  const xMin = projectStart
    ? Math.min(projectStart.getTime(), now.getTime())
    : now.getTime() - 30 * 24 * 3600 * 1000;
  const xMax = projectEnd
    ? Math.max(projectEnd.getTime(), now.getTime())
    : now.getTime() + 365 * 24 * 3600 * 1000;

  return {
    tooltip: {
      ...tooltipConfig,
      trigger: "item",
      formatter: (params: { dataIndex: number; data: [number, number, number, GanttRow] }) => {
        const row = params.data[3];
        const start = row.startDate!;
        const end = row.endDate!;
        const durationDays = Math.ceil(
          (end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24),
        );
        const format = (d: Date) =>
          d.toLocaleDateString("en-US", {
            year: "numeric",
            month: "short",
            day: "numeric",
          });

        // WBE group header tooltip
        if (row.isWbe) {
          return `<div style="font-weight:600;margin-bottom:4px;">${row.name}</div>
<div style="color:${colors.textSecondary};font-size:11px;margin-bottom:4px;">WBE Group</div>
<div style="display:flex;justify-content:space-between;gap:24px;">
  <span>Start</span><span style="font-weight:600;">${format(start)}</span>
</div>
<div style="display:flex;justify-content:space-between;gap:24px;">
  <span>End</span><span style="font-weight:600;">${format(end)}</span>
</div>
<div style="display:flex;justify-content:space-between;gap:24px;">
  <span>Duration</span><span style="font-weight:600;">${durationDays} days</span>
</div>
<div style="display:flex;justify-content:space-between;gap:24px;">
  <span>Items</span><span style="font-weight:600;">${row.childrenCount}</span>
</div>`;
        }

        // Cost element tooltip
        return `<div style="font-weight:600;margin-bottom:4px;">${row.name}</div>
<div style="color:${colors.textSecondary};font-size:11px;margin-bottom:4px;">${row.wbeCode}</div>
<div style="display:flex;justify-content:space-between;gap:24px;">
  <span>Start</span><span style="font-weight:600;">${format(start)}</span>
</div>
<div style="display:flex;justify-content:space-between;gap:24px;">
  <span>End</span><span style="font-weight:600;">${format(end)}</span>
</div>
<div style="display:flex;justify-content:space-between;gap:24px;">
  <span>Duration</span><span style="font-weight:600;">${durationDays} days</span>
</div>
<div style="display:flex;justify-content:space-between;gap:24px;">
  <span>Budget</span><span style="font-weight:600;">${new Intl.NumberFormat("en-US", { style: "currency", currency: "EUR", minimumFractionDigits: 0 }).format(row.budgetAmount)}</span>
</div>
${
  row.progressionType
    ? `<div style="display:flex;justify-content:space-between;gap:24px;">
  <span>Progression</span><span style="font-weight:600;">${row.progressionType}</span>
</div>`
    : ""
}`;
      },
    },
    grid: {
      left: gridLeft,
      right: 40,
      top: 20,
      bottom: 80,
    },
    xAxis: {
      type: "time",
      position: "bottom",
      min: xMin,
      max: xMax,
      axisLabel: {
        color: colors.textSecondary,
        fontSize: 11,
        formatter: (value: number) => {
          const d = new Date(value);
          return d.toLocaleDateString("en-US", {
            month: "short",
            year: "2-digit",
          });
        },
      },
      axisLine: {
        lineStyle: { color: colors.border },
      },
      splitLine: {
        show: true,
        lineStyle: { color: colors.border, type: "dashed", opacity: 0.4 },
      },
    },
    yAxis: {
      type: "category",
      data: yLabels,
      inverse: true,
      axisLabel: {
        color: colors.text,
        fontSize: 11,
        width: gridLeft - 20,
        overflow: "truncate",
      },
      axisLine: {
        lineStyle: { color: colors.border },
      },
      axisTick: { show: false },
      splitLine: { show: false },
    },
    series: [
      {
        type: "custom",
        renderItem: (
          params: { coordSys: { x: number; y: number; width: number; height: number; top: number },
            dataIndex: number },
          api: { value: (dim: number) => number; coord: (data: number[]) => number[],
            size: (data: number[]) => number[] },
        ) => {
          const yIndex = api.value(0);
          const startTime = api.value(1);
          const endTime = api.value(2);
          const row = barData[params.dataIndex][3];

          // Get pixel coordinates
          const startCoord = api.coord([startTime, yIndex]);
          const endCoord = api.coord([endTime, yIndex]);
          const barHeight = api.size([0, 1])[1] * 0.5;

          const barWidth = Math.max(endCoord[0] - startCoord[0], 2);

          // WBE group bar: single rect, taller, no rounded corners
          if (row.isWbe) {
            const wbeBarHeight = barHeight * 1.4;
            const wbeY = startCoord[1] - wbeBarHeight / 2;

            return {
              type: "group",
              children: [
                {
                  type: "rect",
                  shape: {
                    x: startCoord[0],
                    y: wbeY,
                    width: barWidth,
                    height: wbeBarHeight,
                    r: 0,
                  },
                  style: {
                    fill: colors.textSecondary,
                    opacity: 0.3,
                  },
                },
              ],
            };
          }

          // Cost element bar: dual-layer rendering (background + foreground)
          const y = startCoord[1] - barHeight / 2;
          const bgColor = colors.border;
          const fgColor = row.progressionType
            ? PROGRESSION_COLORS[row.progressionType] ?? colors.primary
            : colors.primary;

          return {
            type: "group",
            children: [
              // Background bar
              {
                type: "rect",
                shape: {
                  x: startCoord[0],
                  y: y,
                  width: barWidth,
                  height: barHeight,
                  r: 3,
                },
                style: {
                  fill: bgColor,
                  opacity: 0.25,
                },
              },
              // Foreground bar (progression type color)
              {
                type: "rect",
                shape: {
                  x: startCoord[0],
                  y: y,
                  width: barWidth,
                  height: barHeight,
                  r: 3,
                },
                style: {
                  fill: fgColor,
                  opacity: 0.8,
                },
              },
            ],
          };
        },
        data: barData,
        encode: {
          x: [1, 2],
          y: 0,
        },
        markLine: {
          silent: true,
          symbol: "none",
          label: {
            show: true,
            position: "start",
            formatter: "Today",
            fontSize: 11,
            color: colors.textSecondary,
          },
          lineStyle: {
            type: "dashed" as const,
            color: colors.textSecondary,
            width: 1,
            opacity: 0.6,
          },
          data: [{ xAxis: now.getTime() }],
        },
      },
    ],
    dataZoom: [
      {
        type: "slider",
        xAxisIndex: 0,
        bottom: 10,
        height: 20,
        borderColor: "transparent",
        backgroundColor: "transparent",
        handleSize: "80%",
        showDetail: false,
        brushSelect: true,
      },
      {
        type: "inside",
        xAxisIndex: 0,
        zoomOnMouseWheel: true,
        moveOnMouseMove: true,
      },
    ],
  };
}
