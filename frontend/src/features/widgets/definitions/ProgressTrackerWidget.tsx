import { RiseOutlined } from "@ant-design/icons";
import { Progress, Typography, List, theme, Empty } from "antd";
import { useMemo, type FC } from "react";
import { useDashboardContext } from "../context/useDashboardContext";
import {
  useProgressEntries,
  useLatestProgress,
} from "@/features/progress-entries/api/useProgressEntries";
import { WidgetShell } from "../components/WidgetShell";
import { registerWidget, widgetTypeId } from "..";
import type { WidgetComponentProps } from "../types";

const { Text } = Typography;

interface ProgressTrackerConfig {
  showHistory: boolean;
  historyLimit: number;
}

const formatDate = (dateStr: string | null | undefined): string => {
  if (!dateStr) return "-";
  return new Date(dateStr).toLocaleDateString("en-IE", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
};

const ProgressTrackerComponent: FC<
  WidgetComponentProps<ProgressTrackerConfig>
> = ({ config, instanceId, isEditing, onRemove }) => {
  const { token } = theme.useToken();
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
    perPage: config.showHistory ? config.historyLimit : 1,
  });

  // Also get the latest progress for the primary entity if it's a cost element
  const latestResult = useLatestProgress(context.costElementId ?? "");

  const entries = data?.items ?? [];
  const latestEntry = latestResult.data ?? entries[0];
  const historyEntries = config.showHistory ? entries.slice(1) : [];

  const progressPercent = latestEntry
    ? Math.round(parseFloat(latestEntry.progress_percentage))
    : 0;

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
    >
      {entries.length === 0 && !isLoading && !error ? (
        <Empty description="No progress entries found" />
      ) : (
        <div>
          {latestEntry && (
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: token.paddingMD,
                marginBottom: config.showHistory && historyEntries.length > 0
                  ? token.paddingMD
                  : 0,
              }}
            >
              <Progress
                type="circle"
                percent={progressPercent}
                size={80}
                format={(percent) => `${percent}%`}
                strokeColor={token.colorPrimary}
              />
              <div>
                <Text strong style={{ fontSize: token.fontSizeLG }}>
                  {progressPercent}% Complete
                </Text>
                <br />
                <Text type="secondary" style={{ fontSize: token.fontSizeSM }}>
                  As of {formatDate(latestEntry.valid_time)}
                </Text>
                {latestEntry.notes && (
                  <>
                    <br />
                    <Text
                      type="secondary"
                      style={{ fontSize: token.fontSizeXS }}
                    >
                      {latestEntry.notes}
                    </Text>
                  </>
                )}
              </div>
            </div>
          )}

          {config.showHistory && historyEntries.length > 0 && (
            <List
              size="small"
              dataSource={historyEntries}
              renderItem={(entry) => {
                const pct = Math.round(parseFloat(entry.progress_percentage));
                return (
                  <List.Item style={{ padding: `${token.paddingXS}px 0` }}>
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        width: "100%",
                      }}
                    >
                      <Text type="secondary" style={{ fontSize: token.fontSizeSM }}>
                        {formatDate(entry.valid_time)}
                      </Text>
                      <Text style={{ fontSize: token.fontSizeSM }}>{pct}%</Text>
                    </div>
                  </List.Item>
                );
              }}
            />
          )}
        </div>
      )}
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
});
