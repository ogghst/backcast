import { useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Card } from "antd";
import { ProjectTree, type TreeNodeData } from "@/components/hierarchy/ProjectTree";

export const ProjectStructure = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();

  const handleSelect = useCallback(
    (node: TreeNodeData) => {
      if (node.type === "project" && projectId) {
        navigate(`/projects/${projectId}/overview`);
      } else if (node.type === "wbe" && projectId) {
        navigate(`/projects/${projectId}/wbes/${node.id}`);
      } else if (node.type === "cost_element") {
        navigate(`/cost-elements/${node.id}`);
      }
    },
    [navigate, projectId]
  );

  if (!projectId) return null;

  return (
    <Card title="Project Structure">
      <ProjectTree projectId={projectId} onSelect={handleSelect} />
    </Card>
  );
};
