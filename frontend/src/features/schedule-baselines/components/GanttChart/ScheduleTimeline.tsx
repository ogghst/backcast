/**
 * ScheduleTimeline
 *
 * PURE presentational Gantt chart: computes rows + schedule index, builds
 * the ECharts options from a {@link GanttChartConfig}, and renders only
 * `<EChartsBaseChart>`. No label panel, no drag separator, no toolbar, no
 * data fetching.
 *
 * This is the reuse unit. The full page wraps it in page chrome (React
 * y-axis panel + drag separator + toolbar); the future compact dashboard
 * widget will render it directly with `mode:'compact'`.
 *
 * WIDGET REUSE CONTRACT — a compact dashboard widget renders this component
 * with a pre-built config and NO page chrome:
 *   ```
 *   <ScheduleTimeline
 *     data={data}
 *     currency={currency}
 *     colors={colors}
 *     tooltipConfig={tooltipConfig}
 *     config={defaultCompactConfig}  // mode:'compact', showDependencies:false, showDataZoom:false
 *     collapsedWbeIds={collapsedWbeIds}
 *     chartRef={chartRef}            // so the widget can call scrollToToday/fitProject
 *     height={220}
 *   />
 *   ```
 * Reuse levers: `defaultCompactConfig` (tight density, no deps, no slider),
 * `getZoomPreset` (time-axis framing), and `useScheduleViewport` (owns zoom +
 * collapse + the live instance). The widget drives framing itself via the
 * viewport actions since the slider/dataZoom is hidden.
 *
 * The live ECharts instance is exposed via `chartRef` (owned by
 * `useScheduleViewport`) so the toolbar can dispatch framing actions.
 *
 * @module features/schedule-baselines/components/GanttChart
 */

import React, { useMemo, useState } from "react";
import type { ECharts } from "echarts";
import { EChartsBaseChart } from "@/features/evm/components/charts/EChartsBaseChart";
import type {
  EChartsColorPalette,
  EChartsTooltipConfig,
} from "@/features/evm/utils/echartsTheme";
import type { GanttDataResponse } from "../../api/useGanttData";
import {
  transformGanttData,
  buildScheduleBaselineIndex,
  type GanttRow,
} from "./GanttDataTransformer";
import { buildGanttOptions } from "./GanttChartOptions";
import type { GanttChartConfig } from "./config";

/** Default row height used for height math when rows is empty. */
const FALLBACK_ROW_HEIGHT = 32;
/** Minimum rendered chart height in pixels. */
const MIN_HEIGHT = 200;
/** Maximum rendered chart height in pixels. */
const MAX_HEIGHT = 1200;

export interface ScheduleTimelineProps {
  /** Raw Gantt data response (items + dates + dependencies). */
  data: GanttDataResponse;
  /** ISO currency code for tooltips. */
  currency: string;
  /** Tokenised theme palette. */
  colors: EChartsColorPalette;
  /** Tokenised tooltip config. */
  tooltipConfig: EChartsTooltipConfig;
  /** Full chart config (mode/zoom/density/flags). */
  config: GanttChartConfig;
  /** Collapsed WBE ids set. */
  collapsedWbeIds: Set<string>;
  /** Live-instance ref (owned by useScheduleViewport). */
  chartRef?: React.MutableRefObject<ECharts | null>;
  /** Optional bar-click handler (defaults to no-op). */
  onBarClick?: (row: GanttRow) => void;
  /** Optional explicit height; otherwise derived from row count + density. */
  height?: number;
  /** Loading state (shows a Spin in place of the chart). */
  loading?: boolean;
}

/**
 * Presentational Gantt timeline. See module doc.
 */
export const ScheduleTimeline: React.FC<ScheduleTimelineProps> = ({
  data,
  currency,
  colors,
  tooltipConfig,
  config,
  collapsedWbeIds,
  chartRef,
  onBarClick,
  height,
  loading,
}) => {
  const { density } = config;
  const headerFooter = density.headerHeight + density.bottomPadding;

  // Transform flat API data into display rows
  const rows = useMemo(
    () => transformGanttData(data?.items ?? [], collapsedWbeIds),
    [data, collapsedWbeIds],
  );

  // Schedule index for dependency-arrow coordinate resolution
  const scheduleIndex = useMemo(
    () => buildScheduleBaselineIndex(rows),
    [rows],
  );

  const projectStart = useMemo(
    () => (data?.project_start ? new Date(data.project_start) : null),
    [data],
  );
  const projectEnd = useMemo(
    () => (data?.project_end ? new Date(data.project_end) : null),
    [data],
  );

  // Hovered dependency index — tracked via onEvents mouseover/mouseout on the
  // dependency series. Lifts the hovered link to full opacity / thicker stroke
  // (ECharts' under-documented custom-series emphasis API is unreliable).
  const [hoveredDepIndex, setHoveredDepIndex] = useState(-1);

  // Build ECharts options
  const option = useMemo(
    () =>
      buildGanttOptions(
        rows,
        data?.dependencies ?? [],
        scheduleIndex,
        projectStart,
        projectEnd,
        colors,
        tooltipConfig,
        currency,
        config,
        hoveredDepIndex,
      ),
    [
      rows,
      data?.dependencies,
      scheduleIndex,
      projectStart,
      projectEnd,
      colors,
      tooltipConfig,
      currency,
      config,
      hoveredDepIndex,
    ],
  );

  // Height math: row count × density, clamped — matches the full-page layout.
  const computedHeight = useMemo(() => {
    if (height != null) return height;
    const visibleRows = rows.length;
    const rowH = density.rowHeight || FALLBACK_ROW_HEIGHT;
    return Math.max(
      MIN_HEIGHT,
      Math.min(visibleRows * rowH + headerFooter, MAX_HEIGHT),
    );
  }, [height, rows.length, density.rowHeight, headerFooter]);

  // Expose the live instance to the hook so the toolbar can dispatch actions.
  const handleChartReady = useMemo(
    () => (chartRef ? (chart: ECharts) => {
      chartRef.current = chart;
    } : undefined),
    [chartRef],
  );

  // Event handlers — bar click navigates; dep hover lifts the link. The dep
  // series items carry 7-element data arrays (vs 4 for bars).
  const handleEvents = useMemo(
    () => ({
      click: (params: { data?: [number, number, number, GanttRow] | unknown[] }) => {
        if (!onBarClick) return;
        if (!params.data || params.data.length !== 4) return;
        const row = params.data[3] as GanttRow;
        onBarClick(row);
      },
      // Dependency-link hover emphasis.
      mouseover: (params: { data?: unknown[]; dataIndex?: number }) => {
        if (params.data && params.data.length === 7 && params.dataIndex != null) {
          setHoveredDepIndex(params.dataIndex);
        }
      },
      mouseout: () => setHoveredDepIndex(-1),
    }),
    [onBarClick],
  );

  return (
    <EChartsBaseChart
      option={option}
      height={computedHeight}
      loading={loading}
      showWhenEmpty={false}
      emptyDescription="No schedule data available"
      onChartReady={handleChartReady}
      onEvents={handleEvents}
      style={{ width: "100%", position: "relative", zIndex: 1 }}
    />
  );
};
