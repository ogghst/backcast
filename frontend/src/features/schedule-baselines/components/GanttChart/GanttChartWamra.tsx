/**
 * GanttChartWamra Component
 *
 * Renders a Gantt chart using @wamra/gantt-task-react for side-by-side
 * comparison with the existing ECharts implementation. Read-only mode
 * with project hierarchy grouping and progression-type coloring.
 *
 * The task list pane is dynamically sized to 30% of the container width
 * using a ResizeObserver, since the library's column widths only accept
 * pixel values.
 *
 * Theme compliance note: The library uses `barLabelColor` for BOTH bar
 * text labels AND the calendar/timeline header text (via inline SVG
 * `fill`). CSS overrides are applied for colors the library hardcodes
 * in its stylesheet (borders, calendar header fill, separator lines).
 *
 * @module features/schedule-baselines/components/GanttChart
 */

import { useEffect, useMemo, useRef, useState } from "react";
import { Segmented, Spin, theme, Typography } from "antd";
import { Gantt, ViewMode } from "@wamra/gantt-task-react";
import type {
  Column,
  ColumnProps,
  Task,
  TaskListHeaderProps,
  TaskListTableProps,
} from "@wamra/gantt-task-react";
import "@wamra/gantt-task-react/dist/style.css";

import { useGanttData } from "../../api/useGanttData";
import { adaptGanttItems } from "./GanttTaskAdapter";

/** Fraction of the container width allocated to the task list pane. */
const TASK_LIST_WIDTH_RATIO = 0.3;

/** Minimum task list width in pixels (prevents collapse on narrow viewports). */
const MIN_TASK_LIST_WIDTH = 150;

interface GanttChartWamraProps {
  projectId: string;
  height?: number | string;
}

/** View mode options for the segmented control. */
const VIEW_OPTIONS = [
  { label: "Day", value: ViewMode.Day },
  { label: "Week", value: ViewMode.Week },
  { label: "Month", value: ViewMode.Month },
];

/**
 * Builds a <style> tag that overrides hardcoded colors in the library's
 * CSS with theme-aware tokens. The library's style.css hardcodes values
 * like `fill: #333`, `stroke: #e6e4e4`, and `border: #e6e4e4` that
 * the `colors` prop cannot control.
 */
function buildThemeOverrides(t: Record<string, string>) {
  return `
    /* Calendar (timeline) header area */
    [class*="_calendarMain_"] {
      border-top-color: ${t.colorBorder} !important;
      border-bottom-color: ${t.colorBorder} !important;
    }
    [class*="_calendarBottomText_"] {
      fill: ${t.colorText} !important;
    }
    [class*="_calendarTopText_"] {
      fill: ${t.colorTextSecondary} !important;
    }
    [class*="_calendarTopTick_"] {
      stroke: ${t.colorBorderSecondary} !important;
    }
    [class*="_calendarHeader_"] {
      fill: ${t.colorBgContainer} !important;
      stroke: ${t.colorBorderSecondary} !important;
    }

    /* Task list header (left pane) */
    [class*="_ganttTable_Header_"] {
      border-bottom-color: ${t.colorBorder} !important;
      border-top-color: ${t.colorBorder} !important;
      background-color: ${t.colorBgContainer} !important;
    }
    [class*="_ganttTable_HeaderSeparator_"] {
      border-right-color: ${t.colorBorderSecondary} !important;
    }

    /* Task list container border */
    [class*="_ganttTableRoot_"] {
      border-left-color: ${t.colorBorder} !important;
    }

    /* Column resizer handle */
    [class*="_taskListResizer_"]::before {
      background-color: ${t.colorBorderSecondary} !important;
    }

    /* Tooltip */
    [class*="_tooltipDefaultContainer_"] {
      background: ${t.colorBgElevated} !important;
    }
    [class*="_tooltipDefaultContainerParagraph_"] {
      color: ${t.colorTextSecondary} !important;
    }

    /* Context menu options */
    [class*="_menuOption_"] {
      background-color: ${t.colorBgElevated} !important;
    }
    [class*="_menuOption_"]:hover {
      background-color: ${t.colorBgTextHover} !important;
    }

    /* Bar handles (drag grips) */
    [class*="_barHandle_"] {
      fill: ${t.colorBorder} !important;
    }
    [class*="_barHandle_"]:hover {
      fill: ${t.colorTextTertiary} !important;
    }

    /* Bar relation handles */
    [class*="_barRelationHandle_"] {
      fill: ${t.colorBorder} !important;
      stroke: ${t.colorTextTertiary} !important;
    }
    [class*="_barRelationHandle_"]:hover {
      fill: ${t.colorTextTertiary} !important;
    }

    /* Relation lines */
    [class*="_relationLine_"] {
      stroke: ${t.colorBorder} !important;
    }

    /* Resizer hover */
    [class*="_resizer_"]:hover {
      background-color: ${t.colorBorderSecondary} !important;
    }

    /* Project (WBE) bars: scale group to 10px height, top-aligned in row.
     * transform-box: fill-box makes transforms relative to the element's own
     * bounding box (works for ALL rows, not just the first).
     * scaleY(10/28) scales the 28px bar to 10px from top.
     * translateY(-11px) shifts up by centering offset (50-28)/2 = 11px.
     * Triangles land ~5px below bar top, contained within bar. */
    g[data-testid^="task-project"] {
      transform-box: fill-box;
      transform-origin: left top;
      transform: translateY(-11px) scaleY(0.357);
    }
  `;
}

/**
 * Custom column cell that renders the task name with hierarchy indicators.
 * Uses theme tokens for full light/dark mode compatibility.
 */
const TaskNameCell: React.FC<ColumnProps> = ({ data }) => {
  const { token } = theme.useToken();
  const {
    task,
    depth,
    hasChildren,
    isClosed,
    onExpanderClick,
    distances: { nestedTaskNameOffset, expandIconWidth },
  } = data;

  if (task.type === "empty") return null;

  const isProject = task.type === "project";

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        paddingLeft: nestedTaskNameOffset * depth,
        height: "100%",
        width: "100%",
        color: isProject ? token.colorText : token.colorTextSecondary,
        fontWeight: isProject
          ? token.fontWeightSemiBold
          : token.fontWeightNormal,
        fontSize: "inherit",
        fontFamily: "inherit",
        overflow: "hidden",
        whiteSpace: "nowrap",
        textOverflow: "ellipsis",
      }}
    >
      {hasChildren && (
        <span
          onClick={(e) => {
            e.stopPropagation();
            if (task.type !== "empty") {
              onExpanderClick(task as Task);
            }
          }}
          style={{
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            width: expandIconWidth,
            cursor: "pointer",
            fontSize: token.fontSizeXS,
            color: token.colorTextTertiary,
            flexShrink: 0,
          }}
        >
          {isClosed ? "\u25B6" : "\u25BC"}
        </span>
      )}
      <span style={{ overflow: "hidden", textOverflow: "ellipsis" }}>
        {task.name}
      </span>
    </div>
  );
};

/**
 * Custom tooltip content showing task details with antd Typography.
 */
const TooltipContent: React.FC<{
  task: Task;
  fontSize: string;
  fontFamily: string;
}> = ({ task }) => {
  const { token } = theme.useToken();
  const durationDays = Math.ceil(
    (task.end.getTime() - task.start.getTime()) / (1000 * 60 * 60 * 24),
  );

  return (
    <div
      style={{
        padding: token.paddingSM,
        minWidth: 180,
        backgroundColor: token.colorBgElevated,
        borderRadius: token.borderRadius,
      }}
    >
      <Typography.Text strong style={{ display: "block", marginBottom: 4 }}>
        {task.name}
      </Typography.Text>
      <Typography.Text type="secondary" style={{ display: "block" }}>
        {task.start.toLocaleDateString()} - {task.end.toLocaleDateString()}
      </Typography.Text>
      <Typography.Text type="secondary" style={{ display: "block" }}>
        Duration: {durationDays} day{durationDays !== 1 ? "s" : ""}
      </Typography.Text>
      {task.type === "project" && (
        <Typography.Text type="secondary" style={{ display: "block" }}>
          Group: WBE
        </Typography.Text>
      )}
    </div>
  );
};

/**
 * Custom task list header showing column title.
 * Uses theme tokens for light/dark compatibility.
 */
const TaskListHeader: React.FC<TaskListHeaderProps> = ({
  headerHeight,
  fontFamily,
  fontSize,
}) => {
  const { token } = theme.useToken();
  return (
    <div
      style={{
        height: headerHeight,
        fontFamily,
        fontSize,
        display: "flex",
        alignItems: "center",
        paddingLeft: token.paddingSM,
        borderBottom: `1px solid ${token.colorBorderSecondary}`,
        fontWeight: token.fontWeightSemiBold,
        color: token.colorTextSecondary,
        backgroundColor: token.colorBgContainer,
      }}
    >
      Task
    </div>
  );
};

/**
 * Custom task list table that renders task names with proper hierarchy.
 * Uses theme tokens for light/dark compatibility.
 */
const TaskListTable: React.FC<TaskListTableProps> = ({
  tasks,
  fontFamily,
  fontSize,
  distances,
  selectedIdsMirror,
  onClick,
  onExpanderClick,
}) => {
  const { token } = theme.useToken();
  return (
    <div
      style={{
        fontFamily,
        fontSize,
        backgroundColor: token.colorBgContainer,
      }}
    >
      {tasks.map((t) => {
        const task = "type" in t ? t : null;
        if (!task || task.type === "empty") return null;

        const isSelected = t.id in selectedIdsMirror;
        const isProject = task.type === "project";

        return (
          <div
            key={t.id}
            style={{
              height: distances.rowHeight,
              display: "flex",
              alignItems: "center",
              paddingLeft: isProject ? token.paddingXS : token.paddingLG,
              cursor: "pointer",
              backgroundColor: isSelected
                ? `${token.colorPrimary}08`
                : "transparent",
              borderBottom: `1px solid ${token.colorBorderSecondary}`,
              fontWeight: isProject
                ? token.fontWeightSemiBold
                : token.fontWeightNormal,
              fontSize: isProject ? fontSize : undefined,
              color: isProject ? token.colorText : token.colorTextSecondary,
            }}
            onClick={() => onClick(t)}
          >
            {isProject && (
              <span
                onClick={(e) => {
                  e.stopPropagation();
                  if ("hideChildren" in task) {
                    onExpanderClick(task as Task);
                  }
                }}
                style={{
                  marginRight: token.marginXS,
                  cursor: "pointer",
                  fontSize: token.fontSizeXS,
                  color: token.colorTextTertiary,
                }}
              >
                {task.hideChildren ? "\u25B6" : "\u25BC"}
              </span>
            )}
            {t.name}
          </div>
        );
      })}
    </div>
  );
};

/**
 * Hook to measure a container element's width and compute the task list
 * width as a ratio of that measurement. Updates on resize via
 * ResizeObserver.
 */
function useTaskListWidth(ratio: number, minWidth: number) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [taskListWidth, setTaskListWidth] = useState(minWidth);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const update = () => {
      const w = Math.max(Math.round(el.clientWidth * ratio), minWidth);
      setTaskListWidth(w);
    };

    update();

    const observer = new ResizeObserver(update);
    observer.observe(el);
    return () => observer.disconnect();
  }, [ratio, minWidth]);

  return { containerRef, taskListWidth };
}

export const GanttChartWamra: React.FC<GanttChartWamraProps> = ({
  projectId,
  height = 500,
}) => {
  const { token } = theme.useToken();
  const { data, isLoading, isError } = useGanttData(projectId);
  const [viewMode, setViewMode] = useState<ViewMode>(ViewMode.Week);

  const { containerRef, taskListWidth } = useTaskListWidth(
    TASK_LIST_WIDTH_RATIO,
    MIN_TASK_LIST_WIDTH,
  );

  // Transform flat API data into library Tasks
  const tasks = useMemo(
    () => adaptGanttItems(data?.items ?? []),
    [data],
  );

  // Single column definition: task name with hierarchy, sized to 30% of container.
  const columns: readonly Column[] = useMemo(
    () => [
      {
        id: "TaskName",
        Cell: TaskNameCell,
        width: taskListWidth,
        title: "Task",
      },
    ],
    [taskListWidth],
  );

  // Chart colors derived from theme tokens -- all properties auto-adapt to dark mode.
  // NOTE: barLabelColor is used by the library for BOTH bar text labels AND
  // calendar/timeline header text (SVG fill). It must contrast with both the
  // chart background and the bar backgrounds.
  const chartColors = useMemo(
    () => ({
      // Bar text labels AND calendar/timeline header text
      // The library applies this as SVG `fill` for both bar labels and
      // calendar header date text (TopPartOfCalendar + bottom date rows).
      barLabelColor: token.colorTextSecondary,
      barLabelWhenOutsideColor: token.colorText,

      // Regular task bars
      barBackgroundColor: token.colorInfo,
      barBackgroundSelectedColor: token.colorInfoHover,
      barProgressColor: token.colorInfoActive,
      barProgressSelectedColor: token.colorInfoTextHover,

      // Critical variants (task bars)
      barBackgroundCriticalColor: token.colorErrorBg,
      barBackgroundSelectedCriticalColor: token.colorErrorBorder,
      barProgressCriticalColor: token.colorError,
      barProgressSelectedCriticalColor: token.colorErrorActive,

      // Project-type bars (WBE groups)
      projectBackgroundColor: token.colorPrimary,
      projectBackgroundSelectedColor: token.colorPrimaryHover,
      projectProgressColor: token.colorPrimaryActive,
      projectProgressSelectedColor: token.colorPrimaryTextHover,

      // Project critical variants
      projectBackgroundCriticalColor: token.colorErrorBg,
      projectBackgroundSelectedCriticalColor: token.colorErrorBorder,
      projectProgressCriticalColor: token.colorError,
      projectProgressSelectedCriticalColor: token.colorErrorActive,

      // Group bars
      groupBackgroundColor: token.colorPrimary,
      groupBackgroundSelectedColor: token.colorPrimaryHover,
      groupProgressColor: token.colorPrimaryActive,
      groupProgressSelectedColor: token.colorPrimaryTextHover,

      // Group critical variants
      groupBackgroundCriticalColor: token.colorErrorBg,
      groupBackgroundSelectedCriticalColor: token.colorErrorBorder,
      groupProgressCriticalColor: token.colorError,
      groupProgressSelectedCriticalColor: token.colorErrorActive,

      // Milestone
      milestoneBackgroundColor: token.colorWarning,
      milestoneBackgroundSelectedColor: token.colorWarningHover,

      // Milestone critical variants
      milestoneBackgroundCriticalColor: token.colorError,
      milestoneBackgroundSelectedCriticalColor: token.colorErrorActive,

      // Row backgrounds (alternating)
      evenTaskBackgroundColor: token.colorBgContainer,
      oddTaskBackgroundColor: token.colorBgLayout,

      // Dependency arrows
      arrowColor: token.colorBorder,
      arrowCriticalColor: token.colorError,
      arrowWarningColor: token.colorWarning,

      // Today highlight, selection, drag
      todayColor: `${token.colorPrimary}33`,
      selectedTaskBackgroundColor: `${token.colorPrimary}15`,
      taskDragColor: `${token.colorPrimary}80`,
      holidayBackgroundColor: `${token.colorBgLayout}cc`,

      // Context menu
      contextMenuBoxShadow: token.boxShadowSecondary,
      contextMenuBgColor: token.colorBgElevated,
      contextMenuTextColor: token.colorText,
    }),
    [
      token.colorTextSecondary,
      token.colorText,
      token.colorInfo,
      token.colorInfoHover,
      token.colorInfoActive,
      token.colorInfoTextHover,
      token.colorErrorBg,
      token.colorErrorBorder,
      token.colorError,
      token.colorErrorActive,
      token.colorPrimary,
      token.colorPrimaryHover,
      token.colorPrimaryActive,
      token.colorPrimaryTextHover,
      token.colorWarning,
      token.colorWarningHover,
      token.colorBgContainer,
      token.colorBgLayout,
      token.colorBorder,
      token.boxShadowSecondary,
      token.colorBgElevated,
    ],
  );

  // Theme-aware CSS overrides for hardcoded library styles
  const themeCss = useMemo(
    () =>
      buildThemeOverrides({
        colorBorder: token.colorBorder,
        colorBorderSecondary: token.colorBorderSecondary,
        colorText: token.colorText,
        colorTextSecondary: token.colorTextSecondary,
        colorTextTertiary: token.colorTextTertiary,
        colorBgContainer: token.colorBgContainer,
        colorBgElevated: token.colorBgElevated,
        colorBgTextHover: token.colorBgTextHover,
      }),
    [
      token.colorBorder,
      token.colorBorderSecondary,
      token.colorText,
      token.colorTextSecondary,
      token.colorTextTertiary,
      token.colorBgContainer,
      token.colorBgElevated,
      token.colorBgTextHover,
    ],
  );

  if (isError) {
    return (
      <div style={{ padding: token.paddingMD }}>
        <Typography.Text type="danger">
          Error loading schedule data. Please try again.
        </Typography.Text>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div
        style={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          height,
        }}
      >
        <Spin />
      </div>
    );
  }

  if (tasks.length === 0) {
    return (
      <div
        style={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          height,
          color: token.colorTextSecondary,
        }}
      >
        No schedule data available
      </div>
    );
  }

  return (
    <div ref={containerRef}>
      <div
        style={{
          display: "flex",
          justifyContent: "flex-end",
          marginBottom: token.marginSM,
        }}
      >
        <Segmented
          options={VIEW_OPTIONS}
          value={viewMode}
          onChange={(value) => setViewMode(value as ViewMode)}
        />
      </div>
      <div style={{ height }}>
        <style>{themeCss}</style>
        <Gantt
          tasks={tasks}
          viewMode={viewMode}
          fontFamily={token.fontFamily}
          fontSize={`${token.fontSizeSM}px`}
          TooltipContent={TooltipContent}
          TaskListHeader={TaskListHeader}
          TaskListTable={TaskListTable}
          columns={columns}
          colors={chartColors}
          rowHeight={50}
          taskHeight={28}
          barCornerRadius={token.borderRadius}
          barFill={65}
          headerHeight={50}
          dependencies={false}
        />
      </div>
    </div>
  );
};
