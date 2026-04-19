import { SettingOutlined } from "@ant-design/icons";
import { Typography, theme } from "antd";
import type { FC } from "react";
import { BudgetSettingsWidget as BudgetSettingsComponent } from "@/features/projects/widgets/BudgetSettingsWidget";
import { useDashboardContext } from "../context/useDashboardContext";
import { WidgetShell } from "../components/WidgetShell";
import { registerWidget, widgetTypeId } from "..";
import type { WidgetComponentProps } from "../types";

const { Text } = Typography;

type BudgetSettingsConfig = Record<string, never>;

/**
 * Budget Settings Dashboard Widget
 *
 * Provides project budget validation settings configuration:
 * - Warning threshold percentage
 * - Project admin override toggle
 *
 * This widget requires a project context and is typically used on
 * project-specific dashboards.
 */
const BudgetSettingsWidget: FC<WidgetComponentProps<BudgetSettingsConfig>> = ({
  instanceId,
  isEditing,
  onRemove,
  onConfigure,
  onFullscreen,
  widgetType,
  dashboardName,
}) => {
  const { token } = theme.useToken();
  // Get projectId from dashboard context
  const context = useDashboardContext();
  const projectId = context.projectId;

  if (!projectId) {
    return (
      <WidgetShell
        instanceId={instanceId}
        title="Budget Settings"
        icon={<SettingOutlined />}
        isEditing={isEditing}
        onRemove={onRemove}
        onConfigure={onConfigure}
        onFullscreen={onFullscreen}
        widgetType={widgetType}
        dashboardName={dashboardName}
      >
        <div
          style={{
            padding: token.paddingMD,
            textAlign: "center",
          }}
        >
          <Text type="secondary">
            This widget requires a project context. Please add it to a project-specific dashboard.
          </Text>
        </div>
      </WidgetShell>
    );
  }

  return (
    <WidgetShell
      instanceId={instanceId}
      title="Budget Settings"
      icon={<SettingOutlined />}
      isEditing={isEditing}
      onRemove={onRemove}
      onConfigure={onConfigure}
      onFullscreen={onFullscreen}
      widgetType={widgetType}
      dashboardName={dashboardName}
    >
      <BudgetSettingsComponent projectId={projectId} />
    </WidgetShell>
  );
};

registerWidget<BudgetSettingsConfig>({
  typeId: widgetTypeId("budget-settings"),
  displayName: "Budget Settings",
  description: "Configure budget warning thresholds and admin override for a project",
  category: "settings",
  icon: <SettingOutlined />,
  sizeConstraints: {
    minW: 3,
    minH: 3,
    defaultW: 6,
    defaultH: 4,
    maxW: 8,
    maxH: 6,
  },
  component: BudgetSettingsWidget,
  defaultConfig: {},
  requiresProjectContext: true,
});
