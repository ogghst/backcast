/**
 * Gantt Chart ECharts Options Builder
 *
 * Builds the ECharts option object for the Gantt chart from a declarative
 * {@link GanttChartConfig} plus the active zoom preset. All layout
 * constants (header height, bottom padding, splitline interval, default
 * framing window, progression colours) are derived from `config` / the
 * preset / the theme palette — nothing layout-critical is hard-coded here.
 *
 * Dual-grid structure (unchanged from the pre-refactor design):
 *   - grid 0: time header (xAxis[0] primary row + xAxis[2] secondary row,
 *             kept alive by two empty custom-series)
 *   - grid 1: main chart (xAxis[1] splitlines + monthly labels)
 *
 * @module features/schedule-baselines/components/GanttChart
 */

import type { EChartsOption } from "echarts";
import type {
  EChartsColorPalette,
  EChartsTooltipConfig,
} from "@/features/evm/utils/echartsTheme";
import type { GanttRow } from "./GanttDataTransformer";
import type { GanttDependencyLink } from "../../api/useGanttData";
import type { GanttChartConfig } from "./config";
import { getZoomPreset } from "./zoomPresets";

/**
 * Internal height of the grid-0 primary-label strip (xAxis[0] top row).
 *
 * The secondary axis (xAxis[2]) renders in the gap between grid 0's bottom
 * and grid 1's top, so this is intentionally smaller than `headerHeight`.
 */
const HEADER_STRIP_HEIGHT = 22;

/**
 * Progression-type → chart-token colour map.
 *
 * Tokenised via the ECharts palette (`pv`/`ev`/`forecast`) which already
 * carry the original hex values — so `zoom:'month'` + default density renders
 * pixel-identically to the pre-refactor implementation.
 */
function progressionColor(
  type: string | null,
  colors: EChartsColorPalette,
): string {
  switch (type) {
    case "LINEAR":
      return colors.pv;
    case "GAUSSIAN":
      return colors.ev;
    case "LOGARITHMIC":
      return colors.forecast;
    default:
      return colors.primary;
  }
}

/**
 * Default bar/row tooltip formatter for a Gantt row.
 *
 * Extracted verbatim from the inline `tooltip.formatter` body so alternate
 * hosts (e.g. the portfolio Gantt widget, which renders project spans instead
 * of cost elements) can supply their own `tooltipFormatter` while reusing the
 * same engine. The default (cost-element / WBE) path is byte-identical to the
 * pre-extraction inline formatter.
 *
 * @param row      - The matched GanttRow (params.data[3])
 * @param currency - ISO currency code for the Budget line
 * @param colors   - Theme palette (carries textSecondary for muted labels)
 */
export function defaultGanttTooltip(
  row: GanttRow,
  currency: string,
  colors: EChartsColorPalette,
): string {
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
  <span>Budget</span><span style="font-weight:600;">${new Intl.NumberFormat("en-US", { style: "currency", currency, minimumFractionDigits: 0 }).format(row.budgetAmount)}</span>
</div>
${
  row.progressionType
    ? `<div style="display:flex;justify-content:space-between;gap:24px;">
  <span>Progression</span><span style="font-weight:600;">${row.progressionType}</span>
</div>`
    : ""
}`;
}

/**
 * Build ECharts option for the Gantt chart.
 *
 * @param rows              - Transformed GanttRow array
 * @param dependencies      - Dependency links (rendered as right-angle arrows)
 * @param scheduleIndex     - costElementId → y-index map (dependency resolution)
 * @param projectStart      - Project start date (x-axis min clamp)
 * @param projectEnd        - Project end date (x-axis max clamp)
 * @param colors            - Theme palette (tokenised; carries pv/ev/forecast)
 * @param tooltipConfig     - Tooltip config from useEChartsTheme()
 * @param currency          - ISO currency code for tooltips
 * @param config            - Full chart config (mode/zoom/density/flags)
 * @param hoveredDepIndex   - Dependency data index currently hovered (-1 = none).
 *                            Lifts that link to full opacity / thicker stroke.
 * @param barColorFor       - Optional override for the cost-element bar
 *                            foreground colour. Defaults to
 *                            `(row, c) => progressionColor(row.progressionType, c)`
 *                            (the pre-generalisation behaviour). Alternate
 *                            hosts (portfolio Gantt) supply an RAG-derived colour.
 * @param tooltipFormatter  - Optional override for the bar/row tooltip body.
 *                            Defaults to {@link defaultGanttTooltip} (the exact
 *                            pre-extraction inline body). Alternate hosts pass
 *                            a host-specific formatter.
 */
export function buildGanttOptions(
  rows: GanttRow[],
  dependencies: GanttDependencyLink[],
  scheduleIndex: Map<string, number>,
  projectStart: Date | null,
  projectEnd: Date | null,
  colors: EChartsColorPalette,
  tooltipConfig: EChartsTooltipConfig,
  currency: string,
  config: GanttChartConfig,
  hoveredDepIndex: number = -1,
  barColorFor?: (row: GanttRow, colors: EChartsColorPalette) => string,
  tooltipFormatter?: (
    row: GanttRow,
    currency: string,
    colors: EChartsColorPalette,
  ) => string,
): EChartsOption {
  const preset = getZoomPreset(config.zoom);
  const { density, gridLeft, showDependencies, showDataZoom, showTimeHeader } =
    config;

  const yLabels = rows.map((row) => row.name);

  // Build series data: each bar is [yIndex, startTimestamp, endTimestamp, row]
  const barData: Array<[number, number, number, GanttRow]> = [];
  rows.forEach((row, index) => {
    if (row.startDate && row.endDate) {
      barData.push([
        index,
        row.startDate.getTime(),
        row.endDate.getTime(),
        row,
      ]);
    }
  });

  // Build dependency arrow data:
  // [predYIdx, predStartTs, predEndTs, succYIdx, succStartTs, succEndTs, dep]
  const depData: Array<
    [number, number, number, number, number, number, GanttDependencyLink]
  > = [];
  if (showDependencies) {
    for (const dep of dependencies) {
      const predIdx = scheduleIndex.get(dep.predecessor_id);
      const succIdx = scheduleIndex.get(dep.successor_id);
      if (predIdx !== undefined && succIdx !== undefined) {
        const predRow = rows[predIdx];
        const succRow = rows[succIdx];
        if (
          predRow?.startDate &&
          predRow?.endDate &&
          succRow?.startDate &&
          succRow?.endDate
        ) {
          depData.push([
            predIdx,
            predRow.startDate.getTime(),
            predRow.endDate.getTime(),
            succIdx,
            succRow.startDate.getTime(),
            succRow.endDate.getTime(),
            dep,
          ]);
        }
      }
    }
  }

  // Determine x-axis range (clamped so "Today" is always visible)
  const now = new Date();
  const xMin = projectStart
    ? Math.min(projectStart.getTime(), now.getTime())
    : now.getTime() - 30 * 24 * 3600 * 1000;
  const xMax = projectEnd
    ? Math.max(projectEnd.getTime(), now.getTime())
    : now.getTime() + 365 * 24 * 3600 * 1000;

  const gridRight = 40;

  return {
    tooltip: {
      ...tooltipConfig,
      trigger: "item",
      formatter: (params: unknown) => {
        const p = params as { data: unknown[] };

        // Dependency arrow tooltip (7-element data array)
        if (p.data.length === 7) {
          const dep = p.data[6] as GanttDependencyLink;
          const depTypeLabels: Record<string, string> = {
            FS: "Finish-Start",
            SS: "Start-Start",
            FF: "Finish-Finish",
            SF: "Start-Finish",
          };
          return `<div style="font-weight:600;margin-bottom:4px;">Dependency Link</div>
<div style="display:flex;justify-content:space-between;gap:24px;">
  <span>Type</span><span style="font-weight:600;">${depTypeLabels[dep.dependency_type] ?? dep.dependency_type}</span>
</div>
<div style="display:flex;justify-content:space-between;gap:24px;">
  <span>Lag</span><span style="font-weight:600;">${dep.lag_days} day${dep.lag_days !== 1 ? "s" : ""}</span>
</div>`;
        }

        const row = p.data[3] as GanttRow;
        // Pluggable bar/row tooltip body. Defaults to the verbatim
        // pre-extraction inline formatter; alternate hosts (portfolio Gantt)
        // supply a host-specific formatter via `tooltipFormatter`.
        return (tooltipFormatter ?? defaultGanttTooltip)(row, currency, colors);
      },
    },
    grid: [
      // Grid 0: time header (xAxis[0] primary + xAxis[2] secondary)
      // Only the strip is sized; secondary labels render in the gap below it.
      {
        left: gridLeft,
        right: gridRight,
        top: 0,
        height: HEADER_STRIP_HEIGHT,
        show: showTimeHeader,
        backgroundColor: "transparent",
      },
      // Grid 1: main chart area (transparent so CSS overlays show through)
      {
        left: gridLeft,
        right: gridRight,
        top: density.headerHeight,
        bottom: density.bottomPadding,
        show: true,
        backgroundColor: "transparent",
      },
    ],
    xAxis: [
      // xAxis 0: primary header row (top of grid 0)
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
          formatter: preset.primaryAxis.formatter,
        },
        axisLine: { lineStyle: { color: colors.border }, onZero: false },
        axisTick: {
          show: true,
          alignWithLabel: true,
          lineStyle: { color: colors.border },
        },
        splitLine: { show: false },
        interval: preset.primaryAxis.interval,
      },
      // xAxis 1: main chart axis (bottom of grid 1) — preset-driven splitlines
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
        axisLine: { lineStyle: { color: colors.border } },
        splitLine: {
          show: true,
          lineStyle: {
            color: colors.border,
            type: "dashed" as const,
            opacity: 0.6,
          },
        },
        interval: preset.splitlineIntervalMs,
      },
      // xAxis 2: secondary header row (bottom of grid 0)
      {
        type: "time",
        position: "bottom",
        gridIndex: 0,
        min: xMin,
        max: xMax,
        axisLabel: {
          color: colors.textSecondary,
          fontSize: 10,
          formatter: preset.secondaryAxis?.formatter ?? (() => ""),
        },
        axisLine: { lineStyle: { color: colors.border }, onZero: false },
        axisTick: {
          show: true,
          alignWithLabel: true,
          lineStyle: { color: colors.border },
        },
        splitLine: { show: false },
        interval: preset.secondaryAxis?.interval ?? preset.splitlineIntervalMs,
      },
    ],
    yAxis: [
      // yAxis 0: hidden value axis for grid 0 (must be type "value" with a
      // range — a category axis with data:[] collapses the grid and suppresses
      // its xAxis labels).
      { type: "value", gridIndex: 0, show: false, min: 0, max: 1 },
      // yAxis 1: main chart category axis.
      //
      // In `full` mode labels are HIDDEN here — the page renders its own React
      // label panel beside the chart (so collapse triangles + click handlers
      // stay interactive when the separator is dragged).
      //
      // In `compact` mode there is NO React label panel (the dashboard tile has
      // no page chrome), so the chart must render the row names itself. Each
      // label is indented by its outline `level` (leading spaces) and WBE
      // headers are bolded; width + overflow:'truncate' give a clean ellipsis.
      {
        type: "category",
        data: yLabels,
        inverse: true,
        gridIndex: 1,
        ...(config.mode === "compact"
          ? {
              show: true,
              axisLabel: {
                show: true,
                color: colors.textSecondary,
                fontSize: 11,
                width: gridLeft - 8,
                overflow: "truncate" as const,
                // ECharts passes (value, index); the category-axis data array
                // (`yLabels`) is built 1:1 from `rows`, so the index is a
                // reliable lookup — avoids mis-labeling rows that share a name.
                formatter: (_value: string, index: number) => {
                  const row = rows[index];
                  const name = row ? row.name : _value;
                  if (!row) return name;
                  const indent = " ".repeat(Math.max(0, row.level - 1) * 2);
                  return row.isWbe
                    ? `{wbe|${indent}${name}}`
                    : `${indent}${name}`;
                },
                rich: {
                  wbe: {
                    fontWeight: "bold" as const,
                    color: colors.text,
                  },
                },
              },
              axisLine: { show: false },
              axisTick: { show: false },
              splitLine: { show: false },
            }
          : {
              show: false,
              axisLine: { show: false },
              axisTick: { show: false },
              splitLine: { show: false },
            }),
      },
    ],
    series: [
      // Dummy series #1 — forces grid 0 to render xAxis[0] labels.
      // ECharts skips axis-label rendering for grids whose only series are
      // empty-renderItem custom series unless at least one carries data.
      {
        type: "custom",
        xAxisIndex: 0,
        yAxisIndex: 0,
        silent: true,
        renderItem: () => ({ type: "group", children: [] }),
        data: [[xMin + 1, 0.5]],
        encode: { x: 0, y: 1 },
      },
      // Dummy series #2 — forces grid 0 to render xAxis[2] labels.
      {
        type: "custom",
        xAxisIndex: 2,
        yAxisIndex: 0,
        silent: true,
        renderItem: () => ({ type: "group", children: [] }),
        data: [[xMin + 1, 0.5]],
        encode: { x: 0, y: 1 },
      },
      // Main bar series (cost elements + WBE summary bars)
      {
        type: "custom",
        xAxisIndex: 1,
        yAxisIndex: 1,
        clip: true,
        renderItem: (
          params: {
            coordSys: {
              x: number;
              y: number;
              width: number;
              height: number;
              top: number;
            };
            dataIndex: number;
          },
          api: {
            value: (dim: number) => number;
            coord: (data: number[]) => number[];
            size: (data: number[]) => number[];
          },
        ) => {
          const yIndex = api.value(0);
          const startTime = api.value(1);
          const endTime = api.value(2);
          const row = barData[params.dataIndex][3];

          const startCoord = api.coord([startTime, yIndex]);
          const endCoord = api.coord([endTime, yIndex]);
          const barHeight = api.size([0, 1])[1] * 0.5;
          const barWidth = Math.max(endCoord[0] - startCoord[0], 2);

          // WBE summary / rollup bar (MS Project convention): a tall, rounded
          // token-filled bar spanning the WBE's aggregated start→end with
          // distinctive downward-triangle endcaps at BOTH ends. This reads
          // unmistakably as "parent/rollup" and is visually distinct from the
          // dual-layer leaf cost-element bars below.
          if (row.isWbe) {
            const summaryBarHeight = barHeight * 0.68;
            const summaryY = startCoord[1] - summaryBarHeight / 2;
            const fill = colors.primary;
            // Endcap triangle: width ~ barHeight, height ~ summaryBarHeight/2,
            // apex pointing down past the bar's bottom edge.
            const capW = Math.min(Math.max(barHeight * 0.5, 4), 8);
            const capH = Math.min(Math.max(summaryBarHeight * 0.5, 3), 6);
            const barBottom = summaryY + summaryBarHeight;
            const leftCap: [number, number][] = [
              [startCoord[0], summaryY],
              [startCoord[0] + capW, summaryY],
              [startCoord[0] + capW / 2, barBottom + capH],
            ];
            const rightCap: [number, number][] = [
              [startCoord[0] + barWidth, summaryY],
              [startCoord[0] + barWidth - capW, summaryY],
              [startCoord[0] + barWidth - capW / 2, barBottom + capH],
            ];
            return {
              type: "group",
              children: [
                {
                  type: "rect",
                  shape: {
                    x: startCoord[0],
                    y: summaryY,
                    width: barWidth,
                    height: summaryBarHeight,
                    r: 2,
                  },
                  style: { fill, opacity: 0.6 },
                },
                {
                  type: "polygon",
                  shape: { points: leftCap },
                  style: { fill, opacity: 0.7 },
                },
                {
                  type: "polygon",
                  shape: { points: rightCap },
                  style: { fill, opacity: 0.7 },
                },
              ],
            };
          }

          // Cost element bar: dual-layer (background + progression-coloured foreground)
          const y = startCoord[1] - barHeight / 2;
          const fgColor = (
            barColorFor ??
            ((row, c) => progressionColor(row.progressionType, c))
          )(row, colors);
          return {
            type: "group",
            children: [
              {
                type: "rect",
                shape: {
                  x: startCoord[0],
                  y,
                  width: barWidth,
                  height: barHeight,
                  r: 3,
                },
                style: { fill: colors.border, opacity: 0.25 },
              },
              {
                type: "rect",
                shape: {
                  x: startCoord[0],
                  y,
                  width: barWidth,
                  height: barHeight,
                  r: 3,
                },
                style: { fill: fgColor, opacity: 0.8 },
              },
            ],
          };
        },
        data: barData,
        encode: { x: [1, 2], y: 0 },
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
      // Dependency arrow series: right-angle routing driven by dependency type
      // FS: pred finish → succ start | SS: pred start → succ start
      // FF: pred finish → succ finish | SF: pred start → succ finish
      ...(showDependencies
        ? [
            {
              type: "custom" as const,
              xAxisIndex: 1,
              yAxisIndex: 1,
              clip: true,
              silent: false,
              // Professional dependency links: edge-anchored orthogonal routing
              // with a gap between the bar edge and the connector, an arrowhead
              // oriented along the entry direction, and hover emphasis (lifts
              // opacity + width on mouseenter). Subtle at rest (muted token at
              // ~0.45 opacity, 1.25px), clearly interactive on hover.
              //
              // Edge anchors per type:
              //   FS: pred RIGHT (finish) → succ LEFT (start)
              //   SS: pred LEFT  (start)  → succ LEFT (start)
              //   FF: pred RIGHT (finish) → succ RIGHT (finish)
              //   SF: pred LEFT  (start)  → succ RIGHT (finish)
              renderItem: (
                params: { dataIndex: number },
                api: {
                  value: (dim: number) => number;
                  coord: (data: number[]) => number[];
                  size: (data: number[]) => number[];
                },
              ) => {
                const predY = api.value(0);
                const succY = api.value(3);
                const dep = depData[params.dataIndex][6];

                const usePredStart =
                  dep.dependency_type === "SS" || dep.dependency_type === "SF";
                const useSuccStart =
                  dep.dependency_type === "FS" || dep.dependency_type === "SS";

                const predTs = usePredStart ? api.value(1) : api.value(2);
                const succTs = useSuccStart ? api.value(4) : api.value(5);

                const srcCoord = api.coord([predTs, predY]);
                const tgtCoord = api.coord([succTs, succY]);

                // Edge anchor x: pred start = LEFT, pred finish = RIGHT,
                // succ start = LEFT, succ finish = RIGHT.
                const srcX = srcCoord[0];
                const srcY = srcCoord[1];
                const tgtX = tgtCoord[0];
                const tgtY = tgtCoord[1];
                // Source exits to the RIGHT of a finish edge, LEFT of a start edge.
                const srcExitsRight = !usePredStart; // finish → right
                // Target enters from the LEFT of a start edge, RIGHT of a finish edge.
                const tgtEntersFromRight = !useSuccStart; // finish → right (head points left-in)

                const GAP = 10;
                const sameRow = srcY === tgtY;
                const rowH = api.size([0, 1])[1];

                // Exit / entry points sit a GAP away from the bar edge.
                const exitX = srcExitsRight ? srcX + GAP : srcX - GAP;
                const entryX = tgtEntersFromRight ? tgtX + GAP : tgtX - GAP;

                // Orthogonal elbow. Pick a vertical column for the routing:
                // - cross-row links route through a column near the entry side
                //   so the final horizontal segment is short and the arrowhead
                //   lands cleanly on the target edge.
                // - same-row links dip below the lower bar to avoid overlap.
                let points: Array<[number, number]>;
                if (sameRow) {
                  // Same-row link: dip below the bar to avoid overlapping it.
                  // Exit the source edge → down to dipY → across → up into the
                  // target edge. The arrowhead's final segment is vertical.
                  const dipY = srcY + rowH * 0.55 + 6;
                  points = [
                    [srcX, srcY],
                    [srcExitsRight ? srcX + GAP : srcX - GAP, dipY],
                    [tgtEntersFromRight ? tgtX + GAP : tgtX - GAP, dipY],
                    [tgtX, tgtY],
                  ];
                } else {
                  // Cross-row: exit → (exitX, srcY) → (exitX, tgtY) → (entryX, tgtY) → (tgtX, tgtY)
                  points = [
                    [srcX, srcY],
                    [exitX, srcY],
                    [exitX, tgtY],
                    [entryX, tgtY],
                    [tgtX, tgtY],
                  ];
                }

                // Arrowhead oriented along the FINAL segment's vector so it
                // always points the right way into the target edge.
                const n = points.length;
                const prev = points[n - 2];
                const tip = points[n - 1];
                const dx = tip[0] - prev[0];
                const dy = tip[1] - prev[1];
                const len = Math.hypot(dx, dy) || 1;
                const ux = dx / len;
                const uy = dy / len;
                const headLen = 7;
                const headHalf = 4;
                // Base of the head, perpendicular spread.
                const bx = tip[0] - ux * headLen;
                const by = tip[1] - uy * headLen;
                const px = -uy;
                const py = ux;
                const headPoints: Array<[number, number]> = [
                  [tip[0], tip[1]],
                  [bx + px * headHalf, by + py * headHalf],
                  [bx - px * headHalf, by - py * headHalf],
                ];

                const lineColor = colors.textSecondary;
                // Hover emphasis is driven by the caller-supplied
                // `hoveredDepIndex` (tracked via onEvents mouseover/mouseout in
                // ScheduleTimeline) — ECharts' under-documented custom-series
                // `emphasis` API does not reliably fire (see echarts#9176), so we
                // re-render the hovered link at full intensity ourselves.
                const isHovered = hoveredDepIndex === params.dataIndex;
                const restOpacity = isHovered ? 0.9 : 0.45;
                const hoverOpacity = 0.9;
                const restWidth = isHovered ? 2 : 1.25;
                const hoverWidth = 2;

                return {
                  type: "group",
                  children: [
                    {
                      type: "polyline",
                      shape: { points },
                      style: {
                        stroke: lineColor,
                        lineWidth: restWidth,
                        opacity: restOpacity,
                        fill: "none",
                      },
                      // ECharts custom-series applies `styleEmphasis` on hover
                      // (a nested `emphasis.style` block does NOT reliably fire
                      // for custom-series graphic elements — see echarts#9176).
                      styleEmphasis: {
                        stroke: lineColor,
                        lineWidth: hoverWidth,
                        opacity: hoverOpacity,
                        fill: "none",
                      },
                    },
                    {
                      type: "polygon",
                      shape: { points: headPoints },
                      style: { fill: lineColor, opacity: restOpacity },
                      styleEmphasis: {
                        fill: lineColor,
                        opacity: hoverOpacity,
                      },
                    },
                  ],
                };
              },
              data: depData,
              encode: { x: [1, 2, 4, 5], y: [0, 3] },
            },
          ]
        : []),
    ],
    dataZoom: showDataZoom
      ? [
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
            endValue: xMin + preset.defaultWindowMs,
          },
          {
            type: "inside",
            xAxisIndex: [0, 1, 2],
            filterMode: "none",
            zoomOnMouseWheel: true,
            moveOnMouseMove: true,
          },
        ]
      : [
          // No slider in compact mode — still allow wheel/drag pan inside the chart.
          {
            type: "inside",
            xAxisIndex: [0, 1, 2],
            filterMode: "none",
            zoomOnMouseWheel: true,
            moveOnMouseMove: true,
          },
        ],
  } as EChartsOption;
}
