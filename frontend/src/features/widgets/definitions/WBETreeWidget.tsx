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
  wbe: "wbe",
  cost_element: "ce",
};

const WBETreeComponent: FC<WidgetComponentProps<WBETreeConfig>> = ({
  config,
  instanceId,
  isEditing,
  onRemove,
  onConfigure,
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
        context.setCostElementId(node.id);
      } else if (node.type === "wbe") {
        context.setWbeId(node.id);
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
  configFormComponent: WBETreeConfigForm,
});
