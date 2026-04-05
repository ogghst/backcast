/**
 * GanttChart Component
 *
 * Main component that fetches Gantt data, transforms it, builds ECharts options,
 * and renders the chart. Y-axis labels are rendered by a React panel independent
 * of ECharts, so they stay fixed when the separator is dragged.
 *
 * @module features/schedule-baselines/components/GanttChart
 */

import React, { useState, useMemo, useCallback, useRef, useEffect } from "react";
import { theme } from "antd";
import { useNavigate } from "react-router-dom";
import { EChartsBaseChart } from "@/features/evm/components/charts/EChartsBaseChart";
import { useEChartsTheme } from "@/features/evm/utils/echartsTheme";
import { useGanttData } from "../../api/useGanttData";
import { transformGanttData, type GanttRow } from "./GanttDataTransformer";
import { buildGanttOptions, TIME_LEGEND_HEIGHT, CHART_BOTTOM_PADDING } from "./GanttChartOptions";

/** Row height in pixels for each Gantt row. */
const ROW_HEIGHT = 32;
/** Minimum chart height in pixels. */
const MIN_HEIGHT = 200;
/** Maximum chart height in pixels. */
const MAX_HEIGHT = 1200;
/** Combined height of time legend header and bottom padding. */
const HEADER_FOOTER = TIME_LEGEND_HEIGHT + CHART_BOTTOM_PADDING;

interface GanttChartProps {
  projectId: string;
}

/** ECharts click event params shape for custom series. */
interface ChartClickParams {
  data?: [number, number, number, GanttRow];
}

export const GanttChart: React.FC<GanttChartProps> = ({
  projectId,
}) => {
  const navigate = useNavigate();
  const { token } = theme.useToken();
  const { data, isLoading, isError } = useGanttData(projectId);
  const { colors, tooltipConfig } = useEChartsTheme();

  // Resizable panel: left grid width
  const GRID_LEFT_MIN = 300;
  const GRID_LEFT_MAX = 600;
  const GRID_LEFT_DEFAULT = 300;
  const [gridLeft, setGridLeft] = useState(GRID_LEFT_DEFAULT);

  // Refs for stale closure prevention in drag handler
  const containerRef = useRef<HTMLDivElement>(null);
  const isDraggingRef = useRef(false);
  const gridLeftRef = useRef(gridLeft);
  useEffect(() => {
    gridLeftRef.current = gridLeft;
  }, [gridLeft]);

  // Collapse state for WBE groups
  const [collapsedWbeIds, setCollapsedWbeIds] = useState<Set<string>>(new Set());

  const toggleWbeCollapse = useCallback((wbeId: string) => {
    setCollapsedWbeIds(prev => {
      const next = new Set(prev);
      if (next.has(wbeId)) {
        next.delete(wbeId);
      } else {
        next.add(wbeId);
      }
      return next;
    });
  }, []);

  // Transform flat API data into display rows
  const rows = useMemo(
    () => transformGanttData(data?.items ?? [], collapsedWbeIds),
    [data, collapsedWbeIds],
  );

  // Dynamic height computation based on visible row count
  const chartHeight = useMemo(() => {
    const visibleRows = rows.length;
    return Math.max(MIN_HEIGHT, Math.min(visibleRows * ROW_HEIGHT + HEADER_FOOTER, MAX_HEIGHT));
  }, [rows.length]);

  // Grid height and per-row height for the React y-axis panel
  const gridHeight = chartHeight - TIME_LEGEND_HEIGHT - CHART_BOTTOM_PADDING;
  const rowHeight = rows.length > 0 ? gridHeight / rows.length : ROW_HEIGHT;

  // Parse project dates
  const projectStart = useMemo(
    () => (data?.project_start ? new Date(data.project_start) : null),
    [data],
  );
  const projectEnd = useMemo(
    () => (data?.project_end ? new Date(data.project_end) : null),
    [data],
  );

  // Build ECharts options (y-axis labels hidden — rendered by React panel)
  const chartOption = useMemo(
    () => buildGanttOptions(rows, projectStart, projectEnd, colors, tooltipConfig, gridLeft),
    [rows, projectStart, projectEnd, colors, tooltipConfig, gridLeft],
  );

  // Handle bar clicks for cost element navigation only (WBE collapse handled by React panel)
  const handleEvents = useMemo(() => ({
    click: (params: ChartClickParams) => {
      if (params.data && params.data[3]) {
        const row = params.data[3];
        if (!row.isWbe && row.costElementId) {
          navigate(`/cost-elements/${row.costElementId}`);
        }
      }
    },
  }), [navigate]);

  // Vertical separator drag handler
  const handleSeparatorMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    isDraggingRef.current = true;

    const handleMouseMove = (ev: MouseEvent) => {
      if (!isDraggingRef.current || !containerRef.current) return;
      const containerRect = containerRef.current.getBoundingClientRect();
      const newLeft = ev.clientX - containerRect.left;
      setGridLeft(Math.max(GRID_LEFT_MIN, Math.min(newLeft, GRID_LEFT_MAX)));
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
  }, []);

  // Memoize separator style
  const separatorStyle = useMemo<React.CSSProperties>(() => ({
    position: "absolute",
    left: gridLeft - 2,
    top: 0,
    bottom: 0,
    width: 4,
    cursor: "col-resize",
    zIndex: 10,
    backgroundColor: "transparent",
  }), [gridLeft]);

  if (isError) {
    return (
      <div style={{ padding: 16 }}>
        <p>Error loading schedule data. Please try again.</p>
      </div>
    );
  }

  return (
    <div ref={containerRef} style={{ position: "relative", width: "100%" }}>
      {/* Y-axis label panel - renders labels independently from ECharts */}
      <div style={{
        position: "absolute",
        left: 0,
        top: TIME_LEGEND_HEIGHT,
        width: gridLeft,
        height: gridHeight,
        background: token.colorBgLayout,
        borderRight: `1px solid ${token.colorBorderSecondary}`,
        overflow: "hidden",
        zIndex: 2,
      }}>
        {rows.map((row, index) => {
          const indent = Math.max(0, row.level - 1) * 35 + 8;
          const isHoverable = row.isWbe;
          return (
            <div
              key={`${row.wbeId}-${row.costElementId ?? 'wbe'}-${index}`}
              onClick={() => {
                if (row.isWbe) toggleWbeCollapse(row.wbeId);
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
              }}
              title={row.name}
            >
              {row.isWbe && (
                <span style={{ fontSize: 10, marginRight: 4, fontFamily: "monospace" }}>
                  {row.collapsed ? "\u25B6" : "\u25BC"}
                </span>
              )}
              {row.name}
            </div>
          );
        })}
      </div>
      {/* Chart area elevated background */}
      <div style={{
        position: "absolute",
        left: gridLeft,
        top: 0,
        right: 0,
        bottom: 0,
        background: token.colorBgElevated,
        boxShadow: `-2px 0 6px rgba(0, 0, 0, 0.06)`,
        zIndex: 0,
        pointerEvents: "none",
      }} />
      <EChartsBaseChart
        option={chartOption}
        height={chartHeight}
        loading={isLoading}
        showWhenEmpty={false}
        emptyDescription="No schedule data available"
        onEvents={handleEvents}
        style={{ width: "100%", position: "relative", zIndex: 1 }}
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
  );
};
