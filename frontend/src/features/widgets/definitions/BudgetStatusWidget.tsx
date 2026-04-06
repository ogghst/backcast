import { PieChartOutlined } from "@ant-design/icons";
import { Typography, theme } from "antd";
import type { FC } from "react";
import { EntityType } from "@/features/evm/types";
import { BudgetOverviewChart } from "@/components/explorer/charts/BudgetOverviewChart";
import { WidgetShell } from "../components/WidgetShell";
import { BudgetStatusConfigForm, type BudgetStatusChartType } from "../components/config-forms/BudgetStatusConfigForm";
import { useWidgetEVMData } from "./shared/useWidgetEVMData";
import { registerWidget, widgetTypeId } from "..";
import type { WidgetComponentProps } from "../types";

const { Text } = Typography;

interface BudgetStatusConfig {
  entityType: EntityType;
  chartType?: BudgetStatusChartType;
}

const BudgetStatusComponent: FC<WidgetComponentProps<BudgetStatusConfig>> = ({
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
      title="Budget Status"
      icon={<PieChartOutlined />}
      isEditing={isEditing}
      isLoading={isLoading}
      error={error}
      onRemove={onRemove}
      onRefresh={refetch}
      onConfigure={onConfigure}
    >
      {metrics ? (
        <BudgetOverviewChart metrics={metrics} />
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
            <Text type="secondary">Select an entity to view budget status</Text>
          </div>
        )
      )}
    </WidgetShell>
  );
};

registerWidget<BudgetStatusConfig>({
  typeId: widgetTypeId("budget-status"),
  displayName: "Budget Status",
  description: "Budget overview chart showing BAC, AC, EV, and EAC",
  category: "trend",
  icon: <PieChartOutlined />,
  sizeConstraints: {
    minW: 2,
    minH: 2,
    defaultW: 2,
    defaultH: 2,
  },
  component: BudgetStatusComponent,
  defaultConfig: {
    entityType: EntityType.PROJECT,
    chartType: "bar",
  },
  configFormComponent: BudgetStatusConfigForm,
});
