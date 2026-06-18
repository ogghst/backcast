import { useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Card } from "antd";
import { ProjectTree, type TreeNodeData } from "@/components/hierarchy/ProjectTree";
import { PageWrapper } from "@/components/layout/PageWrapper";

export const ProjectStructure = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();

  const handleSelect = useCallback(
    (node: TreeNodeData) => {
      if (node.type === "project" && projectId) {
        navigate(`/projects/${projectId}`);
      } else if (node.type === "wbs_element" && projectId) {
        navigate(`/projects/${projectId}/wbs-elements/${node.wbs_element_id}`);
      } else if (node.type === "control_account" && projectId) {
        navigate(`/projects/${projectId}/control-accounts/${node.control_account_id}`);
      } else if (node.type === "work_package" && projectId) {
        navigate(`/projects/${projectId}/work-packages/${node.work_package_id}`);
      } else if (node.type === "cost_element") {
        navigate(`/cost-elements/${node.cost_element_id}`);
      }
    },
    [navigate, projectId]
  );

  if (!projectId) return null;

  return (
    <PageWrapper>
      <Card title="Project Structure">
        <ProjectTree projectId={projectId} onSelect={handleSelect} />
      </Card>
    </PageWrapper>
  );
};
