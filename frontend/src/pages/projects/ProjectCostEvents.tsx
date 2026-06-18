import { useParams } from "react-router-dom";
import { CostEventsTab } from "@/features/cost-events";
import { PageWrapper } from "@/components/layout/PageWrapper";

export const ProjectCostEvents = () => {
  const { projectId } = useParams<{ projectId: string }>();
  if (!projectId) return null;
  return (
    <PageWrapper>
      <CostEventsTab projectId={projectId} />
    </PageWrapper>
  );
};
