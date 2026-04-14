import { SettingOutlined } from "@ant-design/icons";
import type { FC } from "react";
import { BudgetSettingsWidget as BudgetSettingsComponent } from "@/features/projects/widgets/BudgetSettingsWidget";
import { WidgetShell } from "../components/WidgetShell";
import { registerWidget, widgetTypeId } from "..";
import type { WidgetComponentProps } from "../types";

interface BudgetSettingsConfig {
  // No additional config needed - projectId comes from context
}

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
  // Get projectId from dashboard context or widget config
  // For now, we'll extract it from the dashboard name or context
  // In a real implementation, this might come from a dashboard context provider

  // TODO: Get projectId from dashboard context
  // For now, we'll need to pass it through the widget config or context
  const projectId = ""; // This would come from dashboard context

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
        <div style={{ padding: "16px", textAlign: "center" }}>
          This widget requires a project context. Please add it to a project-specific dashboard.
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
