import { useParams } from "react-router-dom";
import { CostEventsTab } from "@/features/cost-events";

export const ProjectCostEvents = () => {
  const { projectId } = useParams<{ projectId: string }>();
  if (!projectId) return null;
  return <CostEventsTab projectId={projectId} />;
};
