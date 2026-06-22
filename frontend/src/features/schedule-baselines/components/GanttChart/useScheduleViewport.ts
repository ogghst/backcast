/**
 * useScheduleViewport
 *
 * Owns the interactive viewport state for the Gantt chart: zoom level,
 * task-panel width, WBE collapse set, and the live ECharts instance ref.
 * Exposes imperative framing actions (`scrollToToday`, `fitProject`) that
 * dispatch `dataZoom` actions on the live instance.
 *
 * This hook is deliberately presentation-agnostic — it does not render
 * anything. The full page and the future compact widget both consume it.
 *
 * Framing API: pass `{ projectStart, projectEnd }` into the hook so the
 * actions are self-contained (the toolbar calls `scrollToToday()` with no
 * args) and can clamp to the project range.
 *
 * @module features/schedule-baselines/components/GanttChart
 */

import { useCallback, useMemo, useRef, useState } from "react";
import type { ECharts } from "echarts";
import type { ZoomLevel } from "./config";
import { getZoomPreset } from "./zoomPresets";

/** Inputs needed to clamp framing actions to the project range. */
export interface UseScheduleViewportArgs {
  /** Project start date (x-axis min). Null while data is loading. */
  projectStart: Date | null;
  /** Project end date (x-axis max). Null while data is loading. */
  projectEnd: Date | null;
}

/** Discrete zoom levels exposed to the toolbar. */
export const ZOOM_LEVELS: ZoomLevel[] = ["day", "week", "month", "quarter"];

/**
 * Row density presets. `comfortable` is the full-page default; `compact`
 * tightens row height for denser scanning. The GanttChart wrapper maps this
 * to `config.density.rowHeight`.
 */
export type GanttDensity = "comfortable" | "compact";

/** Density → row-height (px) mapping consumed by the GanttChart wrapper. */
export const DENSITY_ROW_HEIGHT: Record<GanttDensity, number> = {
  comfortable: 32,
  compact: 22,
};

/**
 * Viewport state + actions for the Gantt chart.
 *
 * @param args - projectStart / projectEnd for framing clamps
 */
export function useScheduleViewport({
  projectStart,
  projectEnd,
}: UseScheduleViewportArgs) {
  const [zoom, setZoom] = useState<ZoomLevel>("month");
  const [gridLeft, setGridLeft] = useState<number>(300);
  const [density, setDensity] = useState<GanttDensity>("comfortable");
  const [collapsedWbeIds, setCollapsedWbeIds] = useState<Set<string>>(
    new Set(),
  );

  // Live ECharts instance — owned here so ScheduleTimeline can borrow it via
  // the `chartRef` prop and the toolbar can dispatch actions through it.
  const chartRef = useRef<ECharts | null>(null);

  /** Toggle a single WBE group's collapse state. */
  const toggleWbe = useCallback((id: string) => {
    setCollapsedWbeIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }, []);

  /** Collapse every WBE group whose id is in the provided set. */
  const collapseAll = useCallback((allWbeIds: Iterable<string>) => {
    setCollapsedWbeIds(new Set(allWbeIds));
  }, []);

  /** Expand every WBE group. */
  const expandAll = useCallback(() => {
    setCollapsedWbeIds(new Set());
  }, []);

  /**
   * Frame the viewport around "Today": `[now − window/2, now + window/2]`,
   * clamped to the project range. Window = current zoom preset's default.
   *
   * No-op if the instance is gone or project dates are unknown.
   */
  const scrollToToday = useCallback(() => {
    const chart = chartRef.current;
    if (!chart || chart.isDisposed()) return;

    const now = Date.now();
    const window = getZoomPreset(zoom).defaultWindowMs;
    const half = window / 2;

    const min = projectStart ? projectStart.getTime() : now - half;
    const max = projectEnd ? projectEnd.getTime() : now + half;

    const start = Math.max(now - half, min);
    const end = Math.min(now + half, max);

    chart.dispatchAction({
      type: "dataZoom",
      xAxisIndex: [0, 1, 2],
      startValue: start,
      endValue: end,
    });
  }, [zoom, projectStart, projectEnd]);

  /**
   * Frame the full project range `[projectStart, projectEnd]`.
   *
   * No-op if the instance is gone or project dates are unknown.
   */
  const fitProject = useCallback(() => {
    const chart = chartRef.current;
    if (!chart || chart.isDisposed()) return;
    if (!projectStart || !projectEnd) return;

    chart.dispatchAction({
      type: "dataZoom",
      xAxisIndex: [0, 1, 2],
      startValue: projectStart.getTime(),
      endValue: projectEnd.getTime(),
    });
  }, [projectStart, projectEnd]);

  return useMemo(
    () => ({
      zoom,
      setZoom,
      gridLeft,
      setGridLeft,
      density,
      setDensity,
      collapsedWbeIds,
      toggleWbe,
      collapseAll,
      expandAll,
      scrollToToday,
      fitProject,
      chartRef,
    }),
    [
      zoom,
      gridLeft,
      density,
      collapsedWbeIds,
      toggleWbe,
      collapseAll,
      expandAll,
      scrollToToday,
      fitProject,
    ],
  );
}

/** Return type of {@link useScheduleViewport}. */
export type ScheduleViewport = ReturnType<typeof useScheduleViewport>;
