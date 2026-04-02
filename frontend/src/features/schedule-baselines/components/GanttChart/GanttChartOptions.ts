/**
 * Gantt Chart ECharts Options Builder
 *
 * Builds the ECharts option object for the Gantt chart, including
 * custom renderItem for bars, dataZoom, tooltip, and today marker.
 * Uses dual grids: a time legend header and the main chart area.
 *
 * @module features/schedule-baselines/components/GanttChart
 */

import type { EChartsOption } from "echarts";
import type { EChartsColorPalette, EChartsTooltipConfig } from "@/features/evm/utils/echartsTheme";
import type { GanttRow } from "./GanttDataTransformer";

/** Color mapping for progression types. */
const PROGRESSION_COLORS: Record<string, string> = {
  LINEAR: "#5b8ff9",
  GAUSSIAN: "#5ad8a6",
  LOGARITHMIC: "#faad14",
};

/** Height of the time legend header grid in pixels (month row + week row). */
export const TIME_LEGEND_HEIGHT = 56;

/** Bottom padding for dataZoom slider + x-axis labels + spacing. */
export const CHART_BOTTOM_PADDING = 80;

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
  const yLabels = rows.map((row) => row.name);

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

  // One week in milliseconds -- used as tick interval for weekly markers
  const ONE_WEEK_MS = 7 * 24 * 3600 * 1000;

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
    grid: [
      // Grid 0: month header (xAxis[0] at top, xAxis[2] at bottom)
      // Height is intentionally small — xAxis[2] labels render in the gap
      // between grid 0 bottom and grid 1 top.
      {
        left: gridLeft,
        right: 40,
        top: 0,
        height: 22,
      },
      // Grid 1: main chart area
      {
        left: gridLeft,
        right: 40,
        top: TIME_LEGEND_HEIGHT,
        bottom: CHART_BOTTOM_PADDING,
      },
    ],
    xAxis: [
      // xAxis 0: month row (top of grid 0) — cascading formatter auto-selects monthly ticks
      {
        type: "time",
        position: "top",
        gridIndex: 0,
        min: xMin,
        max: xMax,
        axisLabel: {
          color: colors.text,
          fontSize: 11,
          fontWeight: "bold" as const,
          // Callback formatter: only render text near month boundaries
          // to avoid showing weekly day numbers between month labels.
          formatter: (value: number) => {
            const d = new Date(value);
            if (d.getDate() <= 7) {
              const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
              return `${months[d.getMonth()]} '${String(d.getFullYear()).slice(2)}`;
            }
            return "";
          },
        },
        axisLine: {
          lineStyle: { color: colors.border },
          onZero: false,
        },
        axisTick: {
          show: true,
          alignWithLabel: true,
          lineStyle: { color: colors.border },
        },
        splitLine: { show: false },
      },
      // xAxis 1: main chart axis (bottom of grid 1) — weekly splitLines for grid
      {
        type: "time",
        position: "bottom",
        gridIndex: 1,
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
          lineStyle: { color: colors.border, type: "dashed" as const, opacity: 0.6 },
        },
        interval: ONE_WEEK_MS,
      },
      // xAxis 2: week-date row (bottom of grid 0) — dd/mm per week start
      {
        type: "time",
        position: "bottom",
        gridIndex: 0,
        min: xMin,
        max: xMax,
        axisLabel: {
          color: colors.textSecondary,
          fontSize: 10,
          formatter: (value: number) => {
            const d = new Date(value);
            const dd = String(d.getDate()).padStart(2, "0");
            const mm = String(d.getMonth() + 1).padStart(2, "0");
            return `${dd}/${mm}`;
          },
        },
        axisLine: {
          lineStyle: { color: colors.border },
          onZero: false,
        },
        axisTick: {
          show: true,
          alignWithLabel: true,
          lineStyle: { color: colors.border },
        },
        splitLine: { show: false },
        interval: ONE_WEEK_MS,
      },
    ],
    yAxis: [
      // yAxis 0: hidden value axis for time legend grid (grid 0)
      // Must be type "value" with a range — a category axis with data:[] collapses the grid
      // and prevents xAxis labels from rendering.
      {
        type: "value",
        gridIndex: 0,
        show: false,
        min: 0,
        max: 1,
      },
      // yAxis 1: main chart category axis (grid 1)
      {
        type: "category",
        data: yLabels,
        inverse: true,
        gridIndex: 1,
        axisLabel: {
          width: gridLeft - 20,
          overflow: "truncate",
          formatter: (value: string, index: number) => {
            const row = rows[index];
            if (!row) return value;
            const indent = `{i${row.level}|}`;
            if (row.isWbe) {
              const icon = row.collapsed ? "\u25B6 " : "\u25BC ";
              return `${indent}{icon|${icon}}{wbe|${row.name}}`;
            }
            return `${indent}{ce|${row.name}}`;
          },
          rich: {
            // Indent spacers: each level adds 35px left padding
            ...Object.fromEntries(
              Array.from({ length: 6 }, (_, i) => [
                `i${i}`,
                { padding: [0, 0, 0, i * 35] },
              ]),
            ),
            icon: {
              fontSize: 10,
              fontFamily: "monospace",
              color: colors.textSecondary,
              padding: [0, 4, 0, 0],
            },
            wbe: {
              fontWeight: "bold" as const,
              fontSize: 11,
              color: colors.text,
            },
            ce: {
              fontWeight: "normal" as const,
              fontSize: 11,
              color: colors.textSecondary,
            },
          },
        },
        axisLine: {
          lineStyle: { color: colors.border },
        },
        axisTick: { show: false },
        splitLine: { show: false },
      },
    ],
    series: [
      // Dummy series to force grid 0 (time legend) axis rendering.
      // ECharts skips axis label rendering for grids with no series data.
      // Two dummy series needed: one per xAxis in grid 0 (month row + week row).
      {
        type: "custom",
        xAxisIndex: 0,
        yAxisIndex: 0,
        silent: true,
        renderItem: () => ({ type: "group", children: [] }),
        data: [[xMin + 1, 0.5]],
        encode: { x: 0, y: 1 },
      },
      {
        type: "custom",
        xAxisIndex: 2,
        yAxisIndex: 0,
        silent: true,
        renderItem: () => ({ type: "group", children: [] }),
        data: [[xMin + 1, 0.5]],
        encode: { x: 0, y: 1 },
      },
      {
        type: "custom",
        xAxisIndex: 1,
        yAxisIndex: 1,
        clip: true,
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
        xAxisIndex: [0, 1, 2],
        bottom: 10,
        height: 20,
        borderColor: "transparent",
        backgroundColor: "transparent",
        handleSize: "80%",
        showDetail: false,
        brushSelect: true,
        filterMode: "none",
        startValue: xMin,
        endValue: xMin + 6 * 30 * 24 * 3600 * 1000, // 6 months from project start
      },
      {
        type: "inside",
        xAxisIndex: [0, 1, 2],
        filterMode: "none",
        zoomOnMouseWheel: true,
        moveOnMouseMove: true,
      },
    ],
  };
}
