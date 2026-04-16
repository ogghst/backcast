import { BarChartOutlined } from "@ant-design/icons";
import { Typography, theme } from "antd";
import type { FC } from "react";
import { EntityType } from "@/features/evm/types";
import { CostHistoryChart } from "@/features/cost-registration/components/CostHistoryChart";
import { useDashboardContext } from "../context/useDashboardContext";
import { WidgetShell } from "../components/WidgetShell";
import { registerWidget, widgetTypeId } from "..";
import type { WidgetComponentProps } from "../types";

const { Text } = Typography;

interface CostHistoryConfig {
  entityType: EntityType;
}

const CostHistoryComponent: FC<WidgetComponentProps<CostHistoryConfig>> = ({
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
  const context = useDashboardContext();

  const entityType = config.entityType;
  const entityId =
    entityType === EntityType.PROJECT
      ? context.projectId
      : entityType === EntityType.WBE
        ? context.wbeId
        : context.costElementId;

  return (
    <WidgetShell
      instanceId={instanceId}
      title="Cost History"
      icon={<BarChartOutlined />}
      isEditing={isEditing}
      isLoading={false}
      error={null}
      onRemove={onRemove}
      onRefresh={() => {}}
      onConfigure={onConfigure}
      onFullscreen={onFullscreen}
      widgetType={widgetType}
      dashboardName={dashboardName}
    >
      {entityId ? (
        <CostHistoryChart
          entityType={entityType === EntityType.PROJECT ? "project" : entityType === EntityType.WBE ? "wbe" : "cost_element"}
          entityId={entityId}
          headless
          height={250}
        />
      ) : (
        <div style={{ textAlign: "center", padding: token.paddingMD }}>
          <Text type="secondary">
            {entityType === EntityType.PROJECT
              ? "No project data available"
              : "Select an entity to view cost history"}
          </Text>
        </div>
      )}
    </WidgetShell>
  );
};

registerWidget<CostHistoryConfig>({
  typeId: widgetTypeId("cost-history"),
  displayName: "Cost History",
  description: "Burn rate and cumulative cost trends over time",
  category: "trend",
  icon: <BarChartOutlined />,
  sizeConstraints: {
    minW: 4,
    minH: 4,
    defaultW: 6,
    defaultH: 5,
  },
  component: CostHistoryComponent,
  defaultConfig: {
    entityType: EntityType.PROJECT,
  },
});
