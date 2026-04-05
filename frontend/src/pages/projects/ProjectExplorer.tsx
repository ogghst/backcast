import { useState, useCallback } from "react";
import { useParams } from "react-router-dom";
import { Spin, Empty, theme } from "antd";
import { Allotment } from "allotment";
import "allotment/dist/style.css";
import { ProjectTree, type TreeNodeData } from "@/components/hierarchy/ProjectTree";
import { ProjectDetail } from "@/features/projects/pages/ProjectDetail";
import { WBEDetail } from "@/features/wbes/pages/WBEDetail";
import { CostElementDetail } from "@/pages/cost-elements/tabs/CostElementDetail";
import { useCostElement } from "@/features/cost-elements/api/useCostElements";

interface Selection {
  type: "project" | "wbe" | "cost_element";
  id: string;
  name: string;
}

const CostElementPanel = ({ costElementId }: { costElementId: string }) => {
  const { data: costElement, isLoading } = useCostElement(costElementId);

  if (isLoading) {
    return (
      <div style={{ display: "flex", justifyContent: "center", padding: 40 }}>
        <Spin size="large" />
      </div>
    );
  }

  if (!costElement) {
    return <Empty description="Cost element not found" />;
  }

  return <CostElementDetail costElement={costElement} />;
};

export const ProjectExplorer = () => {
  const { token } = theme.useToken();
  const { projectId } = useParams<{ projectId: string }>();
  const [selection, setSelection] = useState<Selection | null>(() =>
    projectId ? { type: "project", id: projectId, name: "" } : null
  );

  const handleSelect = useCallback((node: TreeNodeData) => {
    setSelection({ type: node.type, id: node.id, name: node.name });
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
              showBudget={false}
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
              <ProjectDetail projectId={selection.id} />
            ) : selection.type === "wbe" ? (
              <WBEDetail wbeId={selection.id} />
            ) : (
              <CostElementPanel costElementId={selection.id} />
            )}
          </div>
        </Allotment.Pane>
      </Allotment>
    </div>
  );
};
