import { ThunderboltOutlined } from "@ant-design/icons";
import { Typography, theme } from "antd";
import type { FC } from "react";
import { EntityType } from "@/features/evm/types";
import { ForecastComparisonCard } from "@/features/forecasts/components/ForecastComparisonCard";
import { WidgetShell } from "../components/WidgetShell";
import { ForecastConfigForm } from "../components/config-forms/ForecastConfigForm";
import { useWidgetEVMData } from "./shared/useWidgetEVMData";
import { useDashboardContext } from "../context/useDashboardContext";
import { registerWidget, widgetTypeId } from "..";
import type { WidgetComponentProps } from "../types";

const { Text } = Typography;

export interface ForecastWidgetConfig {
  showVAC: boolean;
  showETC: boolean;
}

const ForecastWidgetComponent: FC<WidgetComponentProps<ForecastWidgetConfig>> = ({
  config: _config, // eslint-disable-line @typescript-eslint/no-unused-vars
  instanceId,
  isEditing,
  onRemove,
  onConfigure,
}) => {
  const { token } = theme.useToken();
  const { costElementId } = useDashboardContext();
  const { metrics, isLoading, error, refetch } = useWidgetEVMData(
    EntityType.COST_ELEMENT,
  );

  const budgetAmount = metrics?.bac ?? 0;

  return (
    <WidgetShell
      instanceId={instanceId}
      title="Forecast"
      icon={<ThunderboltOutlined />}
      isEditing={isEditing}
      isLoading={isLoading}
      error={error}
      onRemove={onRemove}
      onRefresh={refetch}
      onConfigure={onConfigure}
    >
      {costElementId ? (
        <ForecastComparisonCard
          costElementId={costElementId}
          budgetAmount={budgetAmount}
        />
      ) : (
        !isLoading &&
        !error && (
          <div
            style={{
              textAlign: "center",
              padding: token.paddingMD,
            }}
          >
            <Text type="secondary">
              Select a cost element to view forecast
            </Text>
          </div>
        )
      )}
    </WidgetShell>
  );
};

registerWidget<ForecastWidgetConfig>({
  typeId: widgetTypeId("forecast"),
  displayName: "Forecast",
  description: "EVM forecast comparison with advanced analysis",
  category: "action",
  icon: <ThunderboltOutlined />,
  sizeConstraints: {
    minW: 3,
    minH: 2,
    defaultW: 3,
    defaultH: 2,
  },
  component: ForecastWidgetComponent,
  defaultConfig: {
    showVAC: true,
    showETC: true,
  },
  configFormComponent: ForecastConfigForm,
});
