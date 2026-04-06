import { DashboardOutlined } from "@ant-design/icons";
import { Typography, theme } from "antd";
import type { FC } from "react";
import { EntityType } from "@/features/evm/types";
import { EVMGauge } from "@/features/evm/components/EVMGauge";
import { WidgetShell } from "../components/WidgetShell";
import { useWidgetEVMData } from "./shared/useWidgetEVMData";
import { registerWidget, widgetTypeId } from "..";
import type { WidgetComponentProps } from "../types";

const { Text } = Typography;

interface EVMEfficiencyGaugesConfig {
  entityType: EntityType;
  goodThreshold: number;
  warningPercent: number;
}

const EVMEfficiencyGaugesComponent: FC<
  WidgetComponentProps<EVMEfficiencyGaugesConfig>
> = ({ config, instanceId, isEditing, onRemove, onConfigure }) => {
  const { token } = theme.useToken();
  const { metrics, isLoading, error, entityId, refetch } = useWidgetEVMData(
    config.entityType,
  );

  return (
    <WidgetShell
      instanceId={instanceId}
      title="Efficiency Gauges"
      icon={<DashboardOutlined />}
      isEditing={isEditing}
      isLoading={isLoading}
      error={error}
      onRemove={onRemove}
      onRefresh={refetch}
      onConfigure={onConfigure}
    >
      {metrics ? (
        <div
          style={{
            display: "flex",
            justifyContent: "space-around",
            alignItems: "center",
            height: "100%",
          }}
        >
          <EVMGauge
            value={metrics.cpi}
            min={0}
            max={2}
            label="CPI"
            size={130}
            goodThreshold={config.goodThreshold}
            warningThresholdPercent={config.warningPercent}
          />
          <EVMGauge
            value={metrics.spi}
            min={0}
            max={2}
            label="SPI"
            size={130}
            goodThreshold={config.goodThreshold}
            warningThresholdPercent={config.warningPercent}
          />
        </div>
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
              Select an entity to view efficiency gauges
            </Text>
          </div>
        )
      )}
    </WidgetShell>
  );
};

registerWidget<EVMEfficiencyGaugesConfig>({
  typeId: widgetTypeId("evm-efficiency-gauges"),
  displayName: "Efficiency Gauges",
  description: "CPI and SPI gauge visualizations with threshold-based coloring",
  category: "diagnostic",
  icon: <DashboardOutlined />,
  sizeConstraints: {
    minW: 4,
    minH: 2,
    defaultW: 4,
    defaultH: 2,
  },
  component: EVMEfficiencyGaugesComponent,
  defaultConfig: {
    entityType: EntityType.PROJECT,
    goodThreshold: 1.0,
    warningPercent: 0.9,
  },
});
