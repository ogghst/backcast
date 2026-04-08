import { BarChartOutlined } from "@ant-design/icons";
import { Typography, theme, Tooltip } from "antd";
import { useMemo, type FC } from "react";
import { useDashboardContext } from "../context/useDashboardContext";
import { useGanttData } from "@/features/schedule-baselines/api/useGanttData";
import type { GanttItem } from "@/features/schedule-baselines/api/useGanttData";
import { WidgetShell } from "../components/WidgetShell";
import { registerWidget, widgetTypeId } from "..";
import type { WidgetComponentProps } from "../types";

const { Text } = Typography;

interface MiniGanttConfig {
  showWBEOnly: boolean;
  zoomLevel: "months" | "weeks";
}

/** A single row in the timeline, grouped by WBE. */
interface TimelineRow {
  wbeId: string;
  code: string;
  name: string;
  startDate: Date;
  endDate: Date;
}

/**
 * Aggregate GanttItems into one row per WBE.
 * Uses the earliest start_date and latest end_date across all cost elements
 * belonging to the same WBE.
 */
function aggregateToWBERows(items: GanttItem[]): TimelineRow[] {
  const groups = new Map<string, TimelineRow>();

  for (const item of items) {
    if (!item.start_date || !item.end_date) continue;

    const existing = groups.get(item.wbe_id);
    const start = new Date(item.start_date);
    const end = new Date(item.end_date);

    if (!existing) {
      groups.set(item.wbe_id, {
        wbeId: item.wbe_id,
        code: item.wbe_code,
        name: item.wbe_name,
        startDate: start,
        endDate: end,
      });
    } else {
      if (start < existing.startDate) existing.startDate = start;
      if (end > existing.endDate) existing.endDate = end;
    }
  }

  return Array.from(groups.values()).sort(
    (a, b) => a.startDate.getTime() - b.startDate.getTime(),
  );
}

/**
 * Build one row per item (cost element level).
 * Groups items by WBE for visual ordering but keeps individual bars.
 */
function toItemRows(items: GanttItem[]): TimelineRow[] {
  return items
    .filter((item) => item.start_date && item.end_date)
    .map((item) => ({
      wbeId: item.cost_element_id,
      code: item.cost_element_code,
      name: item.cost_element_name,
      startDate: new Date(item.start_date!),
      endDate: new Date(item.end_date!),
    }))
    .sort((a, b) => a.startDate.getTime() - b.startDate.getTime());
}

/** Compute the overall timeline bounds from project dates or item data. */
function getTimelineBounds(
  rows: TimelineRow[],
  projectStart: string | null,
  projectEnd: string | null,
): { startMs: number; endMs: number } | null {
  if (rows.length === 0) return null;

  const projectStartMs = projectStart
    ? new Date(projectStart).getTime()
    : null;
  const projectEndMs = projectEnd ? new Date(projectEnd).getTime() : null;

  let startMs = projectStartMs ?? rows[0].startDate.getTime();
  let endMs = projectEndMs ?? rows[0].endDate.getTime();

  for (const row of rows) {
    if (row.startDate.getTime() < startMs) startMs = row.startDate.getTime();
    if (row.endDate.getTime() > endMs) endMs = row.endDate.getTime();
  }

  return { startMs, endMs };
}

const MiniGanttComponent: FC<WidgetComponentProps<MiniGanttConfig>> = ({
  config,
  instanceId,
  isEditing,
  onRemove,
  onConfigure,
  onFullscreen,
  widgetType,
  dashboardName,
}) => {
  const { token } = theme.useToken();
  const { projectId } = useDashboardContext();
  const { data, isLoading, error, refetch } = useGanttData(projectId);

  const rows = useMemo(() => {
    const items = data?.items ?? [];
    return config.showWBEOnly ? aggregateToWBERows(items) : toItemRows(items);
  }, [data?.items, config.showWBEOnly]);

  const bounds = useMemo(
    () =>
      getTimelineBounds(
        rows,
        data?.project_start ?? null,
        data?.project_end ?? null,
      ),
    [rows, data?.project_start, data?.project_end],
  );

  const barColors = useMemo(
    () => [token.colorPrimary, token.colorInfo],
    [token.colorPrimary, token.colorInfo],
  );

  return (
    <WidgetShell
      instanceId={instanceId}
      title="Mini Gantt"
      icon={<BarChartOutlined />}
      isEditing={isEditing}
      isLoading={isLoading}
      error={error}
      onRemove={onRemove}
      onRefresh={refetch}
      onConfigure={onConfigure}
      onFullscreen={onFullscreen}
      widgetType={widgetType}
      dashboardName={dashboardName}
    >
      {rows.length === 0 ? (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            height: "100%",
          }}
        >
          <Text type="secondary">No schedule data available</Text>
        </div>
      ) : bounds ? (
        <div
          style={{
            overflow: "auto",
            height: "100%",
            padding: token.paddingSM,
          }}
        >
          {rows.map((row, index) => {
            const rangeMs = bounds.endMs - bounds.startMs || 1;
            const leftPercent =
              ((row.startDate.getTime() - bounds.startMs) / rangeMs) * 100;
            const widthPercent =
              ((row.endDate.getTime() - row.startDate.getTime()) / rangeMs) *
              100;
            const barColor = barColors[index % barColors.length];
            const label = `${row.code} - ${row.name}`;
            const dateLabel = `${row.startDate.toLocaleDateString()} - ${row.endDate.toLocaleDateString()}`;

            return (
              <div
                key={row.wbeId}
                style={{
                  display: "flex",
                  alignItems: "center",
                  marginBottom: 4,
                }}
              >
                <Tooltip title={label} placement="left">
                  <div
                    style={{
                      width: 120,
                      flexShrink: 0,
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                      fontSize: token.fontSizeSM,
                      color: token.colorTextSecondary,
                    }}
                  >
                    {row.code}
                  </div>
                </Tooltip>
                <Tooltip title={dateLabel}>
                  <div
                    style={{
                      flex: 1,
                      position: "relative",
                      height: 20,
                      background: token.colorFillQuaternary,
                      borderRadius: token.borderRadiusSM,
                    }}
                  >
                    <div
                      style={{
                        position: "absolute",
                        left: `${leftPercent}%`,
                        width: `${Math.max(widthPercent, 0.5)}%`,
                        height: "100%",
                        background: barColor,
                        borderRadius: token.borderRadiusSM,
                        opacity: 0.7,
                      }}
                    />
                  </div>
                </Tooltip>
              </div>
            );
          })}
        </div>
      ) : null}
    </WidgetShell>
  );
};

registerWidget<MiniGanttConfig>({
  typeId: widgetTypeId("mini-gantt"),
  displayName: "Mini Gantt",
  description: "Simplified WBE timeline overview",
  category: "breakdown",
  icon: <BarChartOutlined />,
  sizeConstraints: {
    minW: 6,
    minH: 3,
    defaultW: 6,
    defaultH: 3,
  },
  component: MiniGanttComponent,
  defaultConfig: {
    showWBEOnly: true,
    zoomLevel: "months",
  },
});
