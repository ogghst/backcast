import { BarChartOutlined } from "@ant-design/icons";
import { Typography, theme } from "antd";
import type { FC } from "react";
import { useDashboardContext } from "../context/useDashboardContext";
import { useChangeOrderStats } from "@/features/change-orders/api/useChangeOrderStats";
import { StatusDistributionChart } from "@/features/change-orders/components/StatusDistributionChart";
import { CostTrendChart } from "@/features/change-orders/components/CostTrendChart";
import { WidgetShell } from "../components/WidgetShell";
import { registerWidget, widgetTypeId } from "..";
import type { WidgetComponentProps } from "../types";

const { Text } = Typography;

interface ChangeOrderAnalyticsConfig {
  chartType: "distribution" | "costTrend";
}

const ChangeOrderAnalyticsComponent: FC<
  WidgetComponentProps<ChangeOrderAnalyticsConfig>
> = ({ config, instanceId, isEditing, onRemove, onConfigure, onFullscreen, widgetType, dashboardName }) => {
  const { token } = theme.useToken();
  const { projectId } = useDashboardContext();

  const { data, isLoading, error, refetch } = useChangeOrderStats({
    projectId,
  });

  const isEmpty = !isLoading && !error && !data;

  return (
    <WidgetShell
      instanceId={instanceId}
      title="Change Order Analytics"
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
      {data ? (
        config.chartType === "costTrend" ? (
          <CostTrendChart data={data.cost_trend} />
        ) : (
          <StatusDistributionChart data={data.by_status} />
        )
      ) : (
        isEmpty && (
          <div
            style={{
              textAlign: "center",
              padding: token.paddingMD,
            }}
          >
            <Text type="secondary">No project selected</Text>
          </div>
        )
      )}
    </WidgetShell>
  );
};

registerWidget<ChangeOrderAnalyticsConfig>({
  typeId: widgetTypeId("change-order-analytics"),
  displayName: "Change Order Analytics",
  description: "Change order status distribution or cost trend chart",
  category: "diagnostic",
  icon: <BarChartOutlined />,
  sizeConstraints: {
    minW: 4,
    minH: 3,
    defaultW: 4,
    defaultH: 3,
  },
  component: ChangeOrderAnalyticsComponent,
  defaultConfig: {
    chartType: "distribution",
  },
});
