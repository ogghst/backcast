import { useState, useCallback } from "react";
import { useParams } from "react-router-dom";
import { Empty, theme } from "antd";
import { Allotment } from "allotment";
import "allotment/dist/style.css";
import { ProjectTree, type TreeNodeData } from "@/components/hierarchy/ProjectTree";
import { ProjectDetailCards } from "@/components/explorer/ProjectDetailCards";
import { WBEDetailCards } from "@/components/explorer/WBEDetailCards";
import { CostElementDetailCards } from "@/components/explorer/CostElementDetailCards";

interface Selection {
  type: "project" | "wbe" | "cost_element";
  id: string;
  name: string;
}

export const ProjectExplorer = () => {
  const { token } = theme.useToken();
  const { projectId } = useParams<{ projectId: string }>();
  const [selection, setSelection] = useState<Selection | null>(() =>
    projectId ? { type: "project", id: projectId, name: "" } : null
  );

  const handleSelect = useCallback((node: TreeNodeData) => {
    // Use the specific entity ID for better type safety
    const entityId = node.type === "cost_element"
      ? node.cost_element_id
      : node.type === "wbe"
        ? node.wbe_id
        : node.id;
    setSelection({ type: node.type, id: entityId || node.id, name: node.name });
  }, []);

  if (!projectId) return null;

  const selectedKey = selection
    ? selection.type === "cost_element"
      ? `ce-${selection.id}`
      : selection.type === "wbe"
        ? `wbe-${selection.id}`
        : `project-${selection.id}`
    : undefined;

  return (
    <div style={{ height: "calc(100vh - 180px)" }}>
      <Allotment defaultSizes={[320, 1]} minSizes={[250, 400]}>
        <Allotment.Pane minSize={250} preferredSize={320}>
          <div
            style={{
              height: "100%",
              border: `1px solid ${token.colorBorderSecondary}`,
              borderRadius: token.borderRadiusLG,
              padding: token.paddingSM,
              overflowY: "auto",
            }}
          >
            <ProjectTree
              projectId={projectId}
              onSelect={handleSelect}
              selectedKey={selectedKey}
              showBudget
              showDates
            />
          </div>
        </Allotment.Pane>

        <Allotment.Pane minSize={400}>
          <div
            style={{
              height: "100%",
              overflowY: "auto",
              border: `1px solid ${token.colorBorderSecondary}`,
              borderRadius: token.borderRadiusLG,
            }}
          >
            {!selection ? (
              <div style={{ display: "flex", justifyContent: "center", alignItems: "center", height: "100%" }}>
                <Empty description="Select an item from the tree to view details" />
              </div>
            ) : selection.type === "project" ? (
              <ProjectDetailCards projectId={selection.id} />
            ) : selection.type === "wbe" ? (
              <WBEDetailCards wbeId={selection.id} />
            ) : (
              <CostElementDetailCards costElementId={selection.id} />
            )}
          </div>
        </Allotment.Pane>
      </Allotment>
    </div>
  );
};
