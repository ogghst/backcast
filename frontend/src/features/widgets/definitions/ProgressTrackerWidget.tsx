import { RiseOutlined } from "@ant-design/icons";
import { useMemo, type FC } from "react";
import { useDashboardContext } from "../context/useDashboardContext";
import {
  useProgressEntries,
  useLatestProgress,
} from "@/features/progress-entries/api/useProgressEntries";
import { ProgressSummaryCard } from "@/features/progress-entries/components/ProgressSummaryCard";
import { WidgetShell } from "../components/WidgetShell";
import { ProgressTrackerConfigForm } from "../components/config-forms/ProgressTrackerConfigForm";
import { registerWidget, widgetTypeId } from "..";
import type { WidgetComponentProps } from "../types";

interface ProgressTrackerConfig {
  showHistory: boolean;
  historyLimit: number;
}

const ProgressTrackerComponent: FC<
  WidgetComponentProps<ProgressTrackerConfig>
> = ({ config, instanceId, isEditing, onRemove, onConfigure, onFullscreen, widgetType, dashboardName }) => {
  const context = useDashboardContext();

  const queryParams = useMemo(() => {
    if (context.costElementId) {
      return { cost_element_id: context.costElementId };
    }
    if (context.wbeId) {
      return { wbe_id: context.wbeId };
    }
    return { project_id: context.projectId };
  }, [context.costElementId, context.wbeId, context.projectId]);

  const { data, isLoading, error, refetch } = useProgressEntries({
    ...queryParams,
    perPage: config.showHistory ? config.historyLimit + 1 : 1,
  });

  // Also get the latest progress for the primary entity if it's a cost element
  const latestResult = useLatestProgress(context.costElementId ?? "");

  const entries = data?.items ?? [];
  const latestEntry = latestResult.data ?? entries[0];
  const historyEntries = config.showHistory ? entries.slice(1) : [];

  return (
    <WidgetShell
      instanceId={instanceId}
      title="Progress Tracker"
      icon={<RiseOutlined />}
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
      <ProgressSummaryCard
        latestEntry={latestEntry}
        historyEntries={historyEntries}
        hideCard
      />
    </WidgetShell>
  );
};

registerWidget<ProgressTrackerConfig>({
  typeId: widgetTypeId("progress-tracker"),
  displayName: "Progress Tracker",
  description: "Latest progress entry with optional history timeline",
  category: "action",
  icon: <RiseOutlined />,
  sizeConstraints: {
    minW: 3,
    minH: 2,
    defaultW: 3,
    defaultH: 2,
  },
  component: ProgressTrackerComponent,
  defaultConfig: {
    showHistory: true,
    historyLimit: 5,
  },
  configFormComponent: ProgressTrackerConfigForm,
});
