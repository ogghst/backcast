/**
 * Mini Gantt Dashboard Widget
 *
 * Renders the SAME `<ScheduleTimeline>` engine as the full /schedule page,
 * driven by `defaultCompactConfig` — collapses the duplication that existed
 * when this widget hand-rolled its own rollup + bars (hardcoded colours, no
 * today line). The widget keeps its `mini-gantt` typeId and filename so
 * persisted layouts need no migration.
 *
 * Compact-mode specifics:
 *   - The tile has no page chrome, so `ScheduleTimeline` is rendered with
 *     `mode:'compact'`, which makes `buildGanttOptions` render the row labels
 *     inside the chart (no React label panel). See GanttChartOptions.ts.
 *   - Default viewport: collapsed to WBE-rollup (`computeCollapseToLevel(
 *     items, 1)`) so a handful of root WBE summary bars fit a tile. Read-only
 *     — there is no collapse-toggle UI on the tile.
 *   - A click anywhere on the tile navigates to the full /schedule page.
 *
 * @module features/widgets/definitions
 */

import { BarChartOutlined } from "@ant-design/icons";
import { Typography } from "antd";
import { useMemo, type FC } from "react";
import { useNavigate } from "react-router-dom";
import { useEChartsTheme } from "@/features/evm/utils/echartsTheme";
import { useGanttData } from "@/features/schedule-baselines/api/useGanttData";
import { ScheduleTimeline } from "@/features/schedule-baselines/components/GanttChart/ScheduleTimeline";
import { defaultCompactConfig } from "@/features/schedule-baselines/components/GanttChart/config";
import { computeCollapseToLevel } from "@/features/schedule-baselines/components/GanttChart/GanttDataTransformer";
import { useProjectCurrency } from "@/features/projects/api/useProjectCurrency";
import { useDashboardContext } from "../context/useDashboardContext";
import { WidgetShell } from "../components/WidgetShell";
import { registerWidget, widgetTypeId } from "..";
import type { WidgetComponentProps } from "../types";

const { Text } = Typography;

/** Persisted config shape (kept stable for typeId 'mini-gantt'). */
type MiniGanttConfig = Record<string, never>;

/**
 * Mini Gantt widget — compact schedule overview rendered on the shared core.
 *
 * Forwards all WidgetShell lifecycle props (instanceId / isEditing /
 * isLoading / error / onRemove / onRefresh / onConfigure / onFullscreen /
 * widgetType / dashboardName). Clicking the chart navigates to /schedule.
 */
const MiniGanttComponent: FC<WidgetComponentProps<MiniGanttConfig>> = ({
  instanceId,
  isEditing,
  onRemove,
  onConfigure,
  onFullscreen,
  widgetType,
  dashboardName,
}) => {
  const navigate = useNavigate();
  const { projectId } = useDashboardContext();
  const { data, isLoading, error, refetch } = useGanttData(projectId ?? "");
  const { colors, tooltipConfig } = useEChartsTheme();
  const currency = useProjectCurrency(projectId);

  // Read-only WBE-rollup view: only root WBE summary bars show (a few rows fit
  // a tile). This is derived state — there is no collapse-toggle UI on the
  // tile, so we compute the collapsed set directly from the data payload
  // rather than seeding local state via an effect (avoids cascading renders).
  // Depends on `data` (stable TanStack reference) — not the derived `items`
  // array, which would change identity every render while data is loading.
  const collapsedWbeIds = useMemo(
    () => computeCollapseToLevel(data?.items ?? [], 1),
    [data],
  );

  // Compact config (no deps, no dataZoom slider, tight density). The chart
  // owns its own y-axis labels in compact mode.
  const compactConfig = useMemo(() => ({ ...defaultCompactConfig }), []);

  // Stable empty-data response so ScheduleTimeline never gets `undefined`.
  const emptyData = useMemo(
    () => ({
      items: [],
      project_start: null,
      project_end: null,
      dependencies: [],
    }),
    [],
  );

  // Don't navigate when the dashboard is in edit mode (clicks should select /
  // drag the tile, not route away).
  const handleClick = () => {
    if (isEditing) return;
    if (!projectId) return;
    navigate(`/projects/${projectId}/schedule`);
  };

  return (
    <WidgetShell
      instanceId={instanceId}
      title="Schedule"
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
      {projectId ? (
        <div
          onClick={handleClick}
          style={{
            height: "100%",
            width: "100%",
            cursor: isEditing ? "default" : "pointer",
            // No fixed-height overflow:auto scroll wrapper — react-grid-layout
            // tiles must not introduce an inner scroll container around the
            // chart (it breaks resizing). The chart fills the tile via "100%".
          }}
        >
          <ScheduleTimeline
            data={data ?? emptyData}
            currency={currency}
            colors={colors}
            tooltipConfig={tooltipConfig}
            config={compactConfig}
            collapsedWbeIds={collapsedWbeIds}
            height="100%"
            loading={isLoading}
          />
        </div>
      ) : (
        !isLoading &&
        !error && (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              height: "100%",
            }}
          >
            <Text type="secondary">Select a project</Text>
          </div>
        )
      )}
    </WidgetShell>
  );
};

registerWidget<MiniGanttConfig>({
  typeId: widgetTypeId("mini-gantt"),
  displayName: "Schedule",
  description:
    "Compact schedule timeline overview (click to open the full Gantt)",
  category: "breakdown",
  icon: <BarChartOutlined />,
  sizeConstraints: {
    minW: 6,
    minH: 3,
    defaultW: 6,
    defaultH: 4,
  },
  component: MiniGanttComponent,
  defaultConfig: {},
});
