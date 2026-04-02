/**
 * GanttChart Component
 *
 * Main component that fetches Gantt data, transforms it, builds ECharts options,
 * and renders the chart. Supports click navigation to cost element detail pages.
 *
 * @module features/schedule-baselines/components/GanttChart
 */

import React, { useState, useMemo, useCallback, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import type { ECharts } from "echarts";
import { EChartsBaseChart } from "@/features/evm/components/charts/EChartsBaseChart";
import { useEChartsTheme } from "@/features/evm/utils/echartsTheme";
import { useGanttData } from "../../api/useGanttData";
import { transformGanttData, type GanttRow } from "./GanttDataTransformer";
import { buildGanttOptions, TIME_LEGEND_HEIGHT, CHART_BOTTOM_PADDING } from "./GanttChartOptions";

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
  const { data, isLoading, isError } = useGanttData(projectId);
  const { colors, tooltipConfig } = useEChartsTheme();

  // Resizable panel: left grid width
  const GRID_LEFT_MIN = 120;
  const GRID_LEFT_MAX = 500;
  const GRID_LEFT_DEFAULT = 220;
  const [gridLeft, setGridLeft] = useState(GRID_LEFT_DEFAULT);

  // Refs for stale closure prevention in ZRender / drag handlers
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
  const ROW_HEIGHT = 32;
  const MIN_HEIGHT = 200;
  const MAX_HEIGHT = 1200;
  const HEADER_FOOTER = TIME_LEGEND_HEIGHT + CHART_BOTTOM_PADDING; // time legend + x-axis + padding

  const chartHeight = useMemo(() => {
    const visibleRows = rows.length;
    return Math.max(MIN_HEIGHT, Math.min(visibleRows * ROW_HEIGHT + HEADER_FOOTER, MAX_HEIGHT));
  }, [rows.length]);

  // Refs for stale closure prevention in ZRender handlers
  const chartInstanceRef = useRef<ECharts | null>(null);
  const rowsRef = useRef(rows);
  const toggleRef = useRef(toggleWbeCollapse);

  // Keep refs in sync outside of render (react-hooks/refs compliance)
  useEffect(() => {
    rowsRef.current = rows;
  }, [rows]);
  useEffect(() => {
    toggleRef.current = toggleWbeCollapse;
  }, [toggleWbeCollapse]);

  // Parse project dates
  const projectStart = useMemo(
    () => (data?.project_start ? new Date(data.project_start) : null),
    [data],
  );
  const projectEnd = useMemo(
    () => (data?.project_end ? new Date(data.project_end) : null),
    [data],
  );

  // Dynamic width: ensure full timeline is always rendered (all bars visible)
  const MIN_PX_PER_DAY = 5;
  const outerRef = useRef<HTMLDivElement>(null);
  const [outerWidth, setOuterWidth] = useState(800);

  useEffect(() => {
    const el = outerRef.current;
    if (!el) return;
    const observer = new ResizeObserver(entries => {
      for (const entry of entries) {
        setOuterWidth(entry.contentRect.width);
      }
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  const chartWidth = useMemo(() => {
    if (!projectStart || !projectEnd) return outerWidth;
    const days = (projectEnd.getTime() - projectStart.getTime()) / (1000 * 60 * 60 * 24);
    const minWidth = Math.ceil(days) * MIN_PX_PER_DAY;
    return Math.max(minWidth, outerWidth);
  }, [projectStart, projectEnd, outerWidth]);

  // Build ECharts options
  const chartOption = useMemo(
    () => buildGanttOptions(rows, projectStart, projectEnd, colors, tooltipConfig, gridLeft),
    [rows, projectStart, projectEnd, colors, tooltipConfig, gridLeft],
  );

  // Handle click to navigate to cost element detail or toggle WBE collapse
  const handleEvents = useMemo(() => ({
    click: (params: ChartClickParams) => {
      if (params.data && params.data[3]) {
        const row = params.data[3];
        if (row.isWbe) {
          toggleWbeCollapse(row.wbeId);
        } else if (row.costElementId) {
          navigate(`/cost-elements/${row.costElementId}`);
        }
      }
    },
  }), [navigate, toggleWbeCollapse]);

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

  const handleChartReady = useCallback((chart: ECharts) => {
    chartInstanceRef.current = chart;
    const zr = chart.getZr();

    // Click handler for y-axis label area
    zr.on('click', (params: { offsetX: number; offsetY: number }) => {
      const currentGridLeft = gridLeftRef.current;
      if (params.offsetX >= currentGridLeft) return;

      const gridTop = TIME_LEGEND_HEIGHT; // matches main grid.top
      const gridHeight = chart.getHeight() - gridTop - CHART_BOTTOM_PADDING;
      const relativeY = params.offsetY - gridTop;
      if (relativeY < 0 || relativeY > gridHeight) return;

      const currentRows = rowsRef.current;
      if (currentRows.length === 0) return;

      const rowHeight = gridHeight / currentRows.length;
      const clickedIndex = Math.floor(relativeY / rowHeight);

      if (clickedIndex >= 0 && clickedIndex < currentRows.length) {
        const clickedRow = currentRows[clickedIndex];
        if (clickedRow.isWbe) {
          toggleRef.current(clickedRow.wbeId);
        }
      }
    });

    // Mousemove handler for cursor feedback
    zr.on('mousemove', (params: { offsetX: number; offsetY: number }) => {
      const currentGridLeft = gridLeftRef.current;
      const dom = chart.getDom();
      if (!dom) return;

      if (params.offsetX >= currentGridLeft) {
        dom.style.cursor = '';
        return;
      }

      const gridTop = TIME_LEGEND_HEIGHT;
      const gridHeight = chart.getHeight() - gridTop - CHART_BOTTOM_PADDING;
      const relativeY = params.offsetY - gridTop;
      if (relativeY < 0 || relativeY > gridHeight) {
        dom.style.cursor = '';
        return;
      }

      const currentRows = rowsRef.current;
      if (currentRows.length === 0) {
        dom.style.cursor = '';
        return;
      }

      const rowHeight = gridHeight / currentRows.length;
      const hoverIndex = Math.floor(relativeY / rowHeight);

      if (hoverIndex >= 0 && hoverIndex < currentRows.length && currentRows[hoverIndex].isWbe) {
        dom.style.cursor = 'pointer';
      } else {
        dom.style.cursor = '';
      }
    });
  }, []);

  // Cleanup ZRender event listeners on unmount
  useEffect(() => {
    return () => {
      const chart = chartInstanceRef.current;
      if (chart && !chart.isDisposed()) {
        chart.getZr().off('click');
        chart.getZr().off('mousemove');
      }
    };
  }, []);

  if (isError) {
    return (
      <div style={{ padding: 16 }}>
        <p>Error loading schedule data. Please try again.</p>
      </div>
    );
  }

  return (
    <div ref={outerRef} style={{ overflowX: "auto" }}>
      <div ref={containerRef} style={{ position: "relative", minWidth: chartWidth }}>
        <EChartsBaseChart
          option={chartOption}
          height={chartHeight}
          loading={isLoading}
          showWhenEmpty={false}
          emptyDescription="No schedule data available"
          onChartReady={handleChartReady}
          onEvents={handleEvents}
        />
        {/* Vertical separator for resizing task panel vs chart area */}
        <div
          style={{
            position: "absolute",
            left: gridLeft - 2,
            top: 0,
            bottom: 0,
            width: 4,
            cursor: "col-resize",
            zIndex: 10,
            backgroundColor: "transparent",
          }}
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
