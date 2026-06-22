/**
 * GanttChart Component (page wrapper)
 *
 * Public entry point: `<GanttChart projectId={...}/>`. Fetches Gantt data,
 * drives the viewport via {@link useScheduleViewport}, and renders the page
 * chrome (React y-axis label panel + draggable vertical separator + toolbar)
 * AROUND the presentational {@link ScheduleTimeline}.
 *
 * The label panel renders collapse triangles and click-to-navigate
 * independently of ECharts so it stays fixed when the separator is dragged.
 * The presentational core owns the chart options + live instance.
 *
 * @module features/schedule-baselines/components/GanttChart
 */

import React, {
  useMemo,
  useCallback,
  useRef,
  useEffect,
} from "react";
import { theme } from "antd";
import { useNavigate } from "react-router-dom";
import { useEChartsTheme } from "@/features/evm/utils/echartsTheme";
import { useGanttData } from "../../api/useGanttData";
import { useProjectCurrency } from "@/features/projects/api/useProjectCurrency";
import { ScheduleTimeline } from "./ScheduleTimeline";
import { GanttToolbar } from "./GanttToolbar";
import { useScheduleViewport } from "./useScheduleViewport";
import {
  defaultFullConfig,
  type GanttChartConfig,
} from "./config";
import {
  transformGanttData,
  computeCollapseToLevel,
  type GanttRow,
} from "./GanttDataTransformer";
import type { GanttItem } from "../../api/useGanttData";

/** Resizable task-panel bounds (px). */
const GRID_LEFT_MIN = 300;
const GRID_LEFT_MAX = 600;
/** Height math constants — kept here to lay out the React label panel. */
const MIN_HEIGHT = 200;
const MAX_HEIGHT = 1200;
const FALLBACK_ROW_HEIGHT = 32;

interface GanttChartProps {
  projectId: string;
}

export const GanttChart: React.FC<GanttChartProps> = ({ projectId }) => {
  const navigate = useNavigate();
  const { token } = theme.useToken();
  const { data, isLoading, isError } = useGanttData(projectId);
  const { colors, tooltipConfig } = useEChartsTheme();
  const currency = useProjectCurrency(projectId);

  // Parse project dates (also feed the viewport hook for framing clamps)
  const projectStart = useMemo(
    () => (data?.project_start ? new Date(data.project_start) : null),
    [data],
  );
  const projectEnd = useMemo(
    () => (data?.project_end ? new Date(data.project_end) : null),
    [data],
  );

  const viewport = useScheduleViewport({ projectStart, projectEnd });
  const {
    zoom,
    gridLeft,
    setGridLeft,
    density,
    collapsedWbeIds,
    toggleWbe,
    collapseAll,
    expandAll,
    chartRef,
  } = viewport;

  // Row height derived from the density toggle (comfortable=32, compact=22).
  const rowHeightPx = density === "comfortable" ? 32 : 22;

  // Build the active full-mode config from the live viewport state. A new
  // object identity only when zoom/gridLeft/density change → options recompute.
  const config: GanttChartConfig = useMemo(
    () => ({
      ...defaultFullConfig,
      zoom,
      gridLeft,
      density: {
        ...defaultFullConfig.density,
        rowHeight: rowHeightPx,
      },
    }),
    [zoom, gridLeft, rowHeightPx],
  );

  // Tree controls for the toolbar: distinct WBE ids + max outline level, plus
  // collapse-to-level wired through the pure helper. Depends on `data` (stable
  // from TanStack Query), not a per-render rawItems array.
  const treeControls = useMemo(() => {
    const rawItems = data?.items ?? [];
    const allWbeIds = Array.from(
      new Set(rawItems.map((i: GanttItem) => i.wbs_element_id)),
    );
    const maxLevel = rawItems.reduce(
      (m: number, i: GanttItem) => Math.max(m, i.wbe_level),
      0,
    );
    return {
      allWbeIds,
      maxLevel,
      expandAll,
      collapseAll,
      collapseToLevel: (level: number) =>
        collapseAll(computeCollapseToLevel(rawItems, level)),
    };
  }, [data, expandAll, collapseAll]);

  // Rows are needed by the React label panel (ScheduleTimeline transforms its
  // own copy; both read the same collapsedWbeIds so they stay in sync).
  const rows = useMemo(
    () => transformGanttData(data?.items ?? [], collapsedWbeIds),
    [data, collapsedWbeIds],
  );

  // Height math — mirrors ScheduleTimeline so the label panel aligns exactly.
  const headerFooter =
    config.density.headerHeight + config.density.bottomPadding;
  const chartHeight = useMemo(() => {
    const visibleRows = rows.length;
    const rowH = config.density.rowHeight || FALLBACK_ROW_HEIGHT;
    return Math.max(
      MIN_HEIGHT,
      Math.min(visibleRows * rowH + headerFooter, MAX_HEIGHT),
    );
  }, [rows.length, config.density.rowHeight, headerFooter]);

  const gridHeight = chartHeight - headerFooter;
  const rowHeight =
    rows.length > 0 ? gridHeight / rows.length : config.density.rowHeight;

  // Drag separator handlers (unchanged behaviour, refs prevent stale closures)
  const containerRef = useRef<HTMLDivElement>(null);
  const isDraggingRef = useRef(false);
  const gridLeftRef = useRef(gridLeft);
  useEffect(() => {
    gridLeftRef.current = gridLeft;
  }, [gridLeft]);

  const handleSeparatorMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    isDraggingRef.current = true;

    const handleMouseMove = (ev: MouseEvent) => {
      if (!isDraggingRef.current || !containerRef.current) return;
      const containerRect = containerRef.current.getBoundingClientRect();
      const newLeft = ev.clientX - containerRect.left;
      setGridLeft(
        Math.max(GRID_LEFT_MIN, Math.min(newLeft, GRID_LEFT_MAX)),
      );
    };

    const handleMouseUp = () => {
      isDraggingRef.current = false;
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    };

    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseup", handleMouseUp);
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
  }, [setGridLeft]);

  const separatorStyle = useMemo<React.CSSProperties>(
    () => ({
      position: "absolute",
      left: gridLeft - 2,
      top: 0,
      bottom: 0,
      width: 4,
      cursor: "col-resize",
      zIndex: 10,
      backgroundColor: "transparent",
    }),
    [gridLeft],
  );

  // Cost-element bar click → navigate (WBE collapse handled by the React panel)
  const handleBarClick = useCallback(
    (row: GanttRow) => {
      if (!row.isWbe && row.costElementId) {
        navigate(`/cost-elements/${row.costElementId}`);
      }
    },
    [navigate],
  );

  if (isError) {
    return (
      <div style={{ padding: token.paddingMD }}>
        <p>Error loading schedule data. Please try again.</p>
      </div>
    );
  }

  const labelPanelTop = config.density.headerHeight;

  return (
    <div style={{ width: "100%" }}>
      <div
        style={{
          display: "flex",
          justifyContent: "flex-end",
          marginBottom: token.marginSM,
        }}
      >
        <GanttToolbar viewport={viewport} tree={treeControls} />
      </div>
      <div ref={containerRef} style={{ position: "relative", width: "100%" }}>
        {/* Y-axis label panel - renders labels independently from ECharts */}
        <div
          style={{
            position: "absolute",
            left: 0,
            top: labelPanelTop,
            width: gridLeft,
            height: gridHeight,
            background: token.colorBgLayout,
            borderRight: `1px solid ${token.colorBorderSecondary}`,
            overflow: "hidden",
            zIndex: 2,
          }}
        >
          {rows.map((row, index) => {
            const indent = Math.max(0, row.level - 1) * 35 + 8;
            const isHoverable = row.isWbe;
            return (
              <div
                key={`${row.wbsElementId}-${row.costElementId ?? "wbs_element"}-${index}`}
                onClick={() => {
                  if (row.isWbe) toggleWbe(row.wbsElementId);
                  else if (row.costElementId) navigate(`/cost-elements/${row.costElementId}`);
                }}
                style={{
                  height: rowHeight,
                  lineHeight: `${rowHeight}px`,
                  paddingLeft: indent,
                  paddingRight: 8,
                  boxSizing: "border-box",
                  cursor: isHoverable ? "pointer" : row.costElementId ? "pointer" : "default",
                  fontWeight: row.isWbe ? 600 : 400,
                  fontSize: 11,
                  color: row.isWbe ? token.colorText : token.colorTextSecondary,
                  whiteSpace: "nowrap",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  userSelect: "none",
                } as React.CSSProperties}
                title={row.name}
              >
                {row.isWbe && (
                  <span style={{ fontSize: 10, marginRight: 4, fontFamily: "monospace" }}>
                    {row.collapsed ? "▶" : "▼"}
                  </span>
                )}
                {row.name}
              </div>
            );
          })}
        </div>
        {/* Chart area elevated background */}
        <div
          style={{
            position: "absolute",
            left: gridLeft,
            top: 0,
            right: 0,
            bottom: 0,
            background: token.colorBgElevated,
            boxShadow: `-2px 0 6px rgba(0, 0, 0, 0.06)`,
            zIndex: 0,
            pointerEvents: "none",
          }}
        />
        <ScheduleTimeline
          data={data ?? { items: [], project_start: null, project_end: null, dependencies: [] }}
          currency={currency}
          colors={colors}
          tooltipConfig={tooltipConfig}
          config={config}
          collapsedWbeIds={collapsedWbeIds}
          chartRef={chartRef}
          onBarClick={handleBarClick}
          height={chartHeight}
          loading={isLoading}
        />
        {/* Vertical separator for resizing task panel vs chart area */}
        <div
          style={separatorStyle}
          onMouseDown={handleSeparatorMouseDown}
          onMouseEnter={(e) => {
            if (!isDraggingRef.current) {
              (e.currentTarget as HTMLDivElement).style.backgroundColor =
                "rgba(0, 0, 0, 0.15)";
            }
          }}
          onMouseLeave={(e) => {
            if (!isDraggingRef.current) {
              (e.currentTarget as HTMLDivElement).style.backgroundColor =
                "transparent";
            }
          }}
        />
      </div>
    </div>
  );
};
