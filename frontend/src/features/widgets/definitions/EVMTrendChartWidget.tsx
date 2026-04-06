import { LineChartOutlined } from "@ant-design/icons";
import { Typography, theme } from "antd";
import { useState } from "react";
import type { FC } from "react";
import { EntityType, EVMTimeSeriesGranularity } from "@/features/evm/types";
import { EVMTimeSeriesChart } from "@/features/evm/components/EVMTimeSeriesChart";
import { useEVMTimeSeries } from "@/features/evm/api/useEVMMetrics";
import { useDashboardContext } from "../context/useDashboardContext";
import { WidgetShell } from "../components/WidgetShell";
import { registerWidget, widgetTypeId } from "..";
import type { WidgetComponentProps } from "../types";

const { Text } = Typography;

interface EVMTrendChartConfig {
  entityType: EntityType;
  granularity: EVMTimeSeriesGranularity;
}

const EVMTrendChartComponent: FC<WidgetComponentProps<EVMTrendChartConfig>> = ({
  config,
  instanceId,
  isEditing,
  onRemove,
  onConfigure,
}) => {
  const { token } = theme.useToken();
  const [granularity, setGranularity] = useState(config.granularity);

  const context = useDashboardContext();
  const entityType = config.entityType;
  const entityId =
    entityType === EntityType.PROJECT
      ? context.projectId
      : entityType === EntityType.WBE
        ? context.wbeId
        : context.costElementId;

  const { data, isLoading, error, refetch } = useEVMTimeSeries(
    entityType,
    entityId ?? "",
    granularity,
  );

  const handleGranularityChange = (g: EVMTimeSeriesGranularity) => {
    setGranularity(g);
  };

  return (
    <WidgetShell
      instanceId={instanceId}
      title="EVM Trend Chart"
      icon={<LineChartOutlined />}
      isEditing={isEditing}
      isLoading={isLoading}
      error={error}
      onRemove={onRemove}
      onRefresh={refetch}
      onConfigure={onConfigure}
    >
      {entityId ? (
        <EVMTimeSeriesChart
          timeSeries={data}
          loading={isLoading}
          onGranularityChange={handleGranularityChange}
          currentGranularity={granularity}
          headless={true}
          fillContainer={true}
          height="100%"
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
              Select an entity to view trend data
            </Text>
          </div>
        )
      )}
    </WidgetShell>
  );
};

registerWidget<EVMTrendChartConfig>({
  typeId: widgetTypeId("evm-trend-chart"),
  displayName: "EVM Trend Chart",
  description: "Time-series EVM progression and cost comparison charts",
  category: "trend",
  icon: <LineChartOutlined />,
  sizeConstraints: {
    minW: 4,
    minH: 3,
    defaultW: 4,
    defaultH: 3,
  },
  component: EVMTrendChartComponent,
  defaultConfig: {
    entityType: EntityType.PROJECT,
    granularity: EVMTimeSeriesGranularity.MONTH,
  },
});
