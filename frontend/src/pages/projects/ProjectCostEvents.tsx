import { useParams } from "react-router-dom";
import { CostEventsTab } from "@/features/cost-events";
import { ProjectPage } from "@/features/projects/components/ProjectPage";

export const ProjectCostEvents = () => {
  const { projectId } = useParams<{ projectId: string }>();
  if (!projectId) return null;
  return (
    <ProjectPage title="Cost Events">
      <CostEventsTab projectId={projectId} />
    </ProjectPage>
  );
};
