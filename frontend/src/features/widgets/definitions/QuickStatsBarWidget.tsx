import { DashboardOutlined } from "@ant-design/icons";
import { Typography, theme } from "antd";
import type { FC } from "react";
import { EntityType } from "@/features/evm/types";
import { CompactKPIStrip } from "./shared/CompactKPIStrip";
import { WidgetShell } from "../components/WidgetShell";
import { useWidgetEVMData } from "./shared/useWidgetEVMData";
import { registerWidget, widgetTypeId } from "..";
import type { WidgetComponentProps } from "../types";

const { Text } = Typography;

interface QuickStatsBarConfig {
  entityType: EntityType;
  /** @deprecated No longer used; kept for backward-compatible persisted configs. */
  variant?: "full" | "compact";
}

const QuickStatsBarComponent: FC<WidgetComponentProps<QuickStatsBarConfig>> = ({
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
  const { metrics, isLoading, error, entityId, refetch } = useWidgetEVMData(
    config.entityType,
  );

  return (
    <WidgetShell
      instanceId={instanceId}
      title="Quick Stats"
      icon={<DashboardOutlined />}
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
      {metrics ? (
        <CompactKPIStrip metrics={metrics} />
      ) : (
        !isLoading &&
        !error &&
        !entityId && (
          <div
            style={{
              textAlign: "center",
              padding: token.paddingMD,
            }}
          >
            <Text type="secondary">Select an entity to view KPIs</Text>
          </div>
        )
      )}
    </WidgetShell>
  );
};

registerWidget<QuickStatsBarConfig>({
  typeId: widgetTypeId("quick-stats-bar"),
  displayName: "Quick Stats Bar",
  description: "Compact KPI strip showing CPI, SPI, progress, CV, and VAC",
  category: "summary",
  icon: <DashboardOutlined />,
  sizeConstraints: {
    minW: 4,
    minH: 1,
    defaultW: 4,
    defaultH: 1,
  },
  component: QuickStatsBarComponent,
  defaultConfig: {
    entityType: EntityType.PROJECT,
    variant: "full",
  },
});
