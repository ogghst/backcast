import { DashboardOutlined } from "@ant-design/icons";
import { Typography, theme } from "antd";
import type { FC } from "react";
import { EntityType } from "@/features/evm/types";
import { KPIStrip } from "@/components/explorer/charts/KPIStrip";
import { WidgetShell } from "../components/WidgetShell";
import { useWidgetEVMData } from "./shared/useWidgetEVMData";
import { registerWidget, widgetTypeId } from "..";
import type { WidgetComponentProps } from "../types";

const { Text } = Typography;

interface QuickStatsBarConfig {
  entityType: EntityType;
  variant: "full" | "compact";
}

const QuickStatsBarComponent: FC<WidgetComponentProps<QuickStatsBarConfig>> = ({
  config,
  instanceId,
  isEditing,
  onRemove,
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
    >
      {metrics ? (
        <KPIStrip metrics={metrics} variant={config.variant} hideCard />
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
  description: "At-a-glance KPI strip with CPI, SPI, progress, and EAC gauges",
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
