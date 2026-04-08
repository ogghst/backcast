import { BarChartOutlined } from "@ant-design/icons";
import { Typography, theme } from "antd";
import type { FC } from "react";
import { EntityType } from "@/features/evm/types";
import { EVMSummaryView } from "@/features/evm/components/EVMSummaryView";
import { WidgetShell } from "../components/WidgetShell";
import { EVMSummaryConfigForm } from "../components/config-forms/EVMSummaryConfigForm";
import { useWidgetEVMData } from "./shared/useWidgetEVMData";
import { registerWidget, widgetTypeId } from "..";
import type { WidgetComponentProps } from "../types";

const { Text } = Typography;

interface EVMSummaryConfig {
  entityType: EntityType;
}

const EVMSummaryComponent: FC<WidgetComponentProps<EVMSummaryConfig>> = ({
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
      title="EVM Summary"
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
      {metrics ? (
        <EVMSummaryView metrics={metrics} onAdvanced={undefined} hideHeader />
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
            <Text type="secondary">Select an entity to view EVM summary</Text>
          </div>
        )
      )}
    </WidgetShell>
  );
};

registerWidget<EVMSummaryConfig>({
  typeId: widgetTypeId("evm-summary"),
  displayName: "EVM Summary",
  description: "Comprehensive EVM metrics organized by category",
  category: "summary",
  icon: <BarChartOutlined />,
  sizeConstraints: {
    minW: 2,
    minH: 2,
    defaultW: 2,
    defaultH: 2,
  },
  component: EVMSummaryComponent,
  defaultConfig: {
    entityType: EntityType.PROJECT,
  },
  configFormComponent: EVMSummaryConfigForm,
});
