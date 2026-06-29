import { ApartmentOutlined } from "@ant-design/icons";
import { useCallback, useState, type FC } from "react";
import { ProjectTree, type TreeNodeData } from "@/components/hierarchy/ProjectTree";
import { useDashboardContext } from "../context/useDashboardContext";
import { WidgetShell } from "../components/WidgetShell";
import { WBETreeConfigForm } from "../components/config-forms/WBETreeConfigForm";
import { registerWidget, widgetTypeId } from "..";
import type { WidgetComponentProps } from "../types";

interface WBETreeConfig {
  showBudget: boolean;
  showDates: boolean;
}

/** Map TreeNodeData.type to the prefix used by ProjectTree's internal key scheme. */
const keyPrefixByType: Record<TreeNodeData["type"], string> = {
  project: "project",
  wbs_element: "wbs_element",
  control_account: "ca",
  work_package: "wp",
  cost_element: "ce",
};

const WBETreeComponent: FC<WidgetComponentProps<WBETreeConfig>> = ({
  config,
  instanceId,
  isEditing,
  onRemove,
  onConfigure,
  onFullscreen,
  widgetType,
  dashboardName,
}) => {
  const context = useDashboardContext();
  const [treeSelectedKey, setTreeSelectedKey] = useState<string | null>(null);

  const handleSelect = useCallback(
    (node: TreeNodeData) => {
      const prefix = keyPrefixByType[node.type];
      const prefixedKey = `${prefix}-${node.id}`;

      // If clicking the same node, deselect
      if (treeSelectedKey === prefixedKey) {
        setTreeSelectedKey(null);
        context.setWbeId(undefined);
        context.setCostElementId(undefined);
        return;
      }

      setTreeSelectedKey(prefixedKey);

      if (node.type === "cost_element") {
        context.setCostElementId(node.cost_element_id);
      } else if (node.type === "wbs_element") {
        context.setWbeId(node.wbs_element_id);
        context.setCostElementId(undefined);
      } else if (node.type === "work_package") {
        // Work packages are intermediate nodes - clear CE selection
        context.setCostElementId(undefined);
      } else if (node.type === "control_account") {
        // Control accounts are intermediate nodes - clear CE selection
        context.setCostElementId(undefined);
      } else {
        // Project node - clear both
        context.setWbeId(undefined);
        context.setCostElementId(undefined);
      }
    },
    [context, treeSelectedKey],
  );

  return (
    <WidgetShell
      instanceId={instanceId}
      title="WBE Structure"
      icon={<ApartmentOutlined />}
      isEditing={isEditing}
      onRemove={onRemove}
      onConfigure={onConfigure}
      onFullscreen={onFullscreen}
      widgetType={widgetType}
      dashboardName={dashboardName}
    >
      <ProjectTree
        projectId={context.projectId}
        onSelect={handleSelect}
        selectedKey={treeSelectedKey}
        showBudget={config.showBudget}
        showDates={config.showDates}
      />
    </WidgetShell>
  );
};

registerWidget<WBETreeConfig>({
  typeId: widgetTypeId("wbe-tree"),
  displayName: "WBE Structure",
  description: "Interactive work breakdown element tree with budget and date info",
  category: "breakdown",
  icon: <ApartmentOutlined />,
  sizeConstraints: {
    minW: 3,
    minH: 3,
    defaultW: 3,
    defaultH: 3,
  },
  component: WBETreeComponent,
  defaultConfig: {
    showBudget: true,
    showDates: true,
  },
  scope: "project",
  // The widget renders <ProjectTree>, which lazily fetches 6 endpoints on
  // expand (project / wbs / control-account / work-package / cost-element /
  // schedule-baseline), each gated by a distinct read permission. A user
  // needs all 6 to use the widget fully — gate via hasAllPermissions.
  requiredPermission: [
    "project-read",
    "wbs-element-read",
    "control-account-read",
    "work-package-read",
    "cost-element-read",
    "schedule-baseline-read",
  ],
  configFormComponent: WBETreeConfigForm,
});
