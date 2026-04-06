import { LineChartOutlined } from "@ant-design/icons";
import { Typography, theme } from "antd";
import type { FC } from "react";
import { EntityType } from "@/features/evm/types";
import { VarianceChart } from "@/components/explorer/charts/VarianceChart";
import { WidgetShell } from "../components/WidgetShell";
import { VarianceChartConfigForm } from "../components/config-forms/VarianceChartConfigForm";
import { useWidgetEVMData } from "./shared/useWidgetEVMData";
import { registerWidget, widgetTypeId } from "..";
import type { WidgetComponentProps } from "../types";

const { Text } = Typography;

interface VarianceChartConfig {
  entityType: EntityType;
  showThresholds?: boolean;
  thresholdPercent?: number;
}

const VarianceChartComponent: FC<WidgetComponentProps<VarianceChartConfig>> = ({
  config,
  instanceId,
  isEditing,
  onRemove,
  onConfigure,
}) => {
  const { token } = theme.useToken();
  const { metrics, isLoading, error, entityId, refetch } = useWidgetEVMData(
    config.entityType,
  );

  return (
    <WidgetShell
      instanceId={instanceId}
      title="Variance Analysis"
      icon={<LineChartOutlined />}
      isEditing={isEditing}
      isLoading={isLoading}
      error={error}
      onRemove={onRemove}
      onRefresh={refetch}
      onConfigure={onConfigure}
    >
      {metrics ? (
        <VarianceChart metrics={metrics} />
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
            <Text type="secondary">
              Select an entity to view variance analysis
            </Text>
          </div>
        )
      )}
    </WidgetShell>
  );
};

registerWidget<VarianceChartConfig>({
  typeId: widgetTypeId("variance-chart"),
  displayName: "Variance Analysis",
  description: "Cost and schedule variance bar chart",
  category: "diagnostic",
  icon: <LineChartOutlined />,
  sizeConstraints: {
    minW: 2,
    minH: 2,
    defaultW: 2,
    defaultH: 2,
  },
  component: VarianceChartComponent,
  defaultConfig: {
    entityType: EntityType.PROJECT,
    showThresholds: false,
    thresholdPercent: 10,
  },
  configFormComponent: VarianceChartConfigForm,
});
