import { useParams } from "react-router-dom";
import { WorkPackagesTab } from "@/features/work-package";

export const ProjectWorkPackages = () => {
  const { projectId } = useParams<{ projectId: string }>();
  if (!projectId) return null;
  return <WorkPackagesTab projectId={projectId} />;
};
