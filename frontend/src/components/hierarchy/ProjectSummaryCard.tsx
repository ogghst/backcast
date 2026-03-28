import { ProjectRead } from "@/api/generated";
import { ProjectHeaderCard } from "@/components/projects/ProjectHeaderCard";
import { ProjectInfoCard } from "@/components/projects/ProjectInfoCard";

interface ProjectSummaryCardProps {
  project: ProjectRead;
  loading?: boolean;
}

/**
 * ProjectSummaryCard - Project summary with header and info cards.
 *
 * Displays project name, key metrics, and additional details in a
 * compact two-card layout.
 */
export const ProjectSummaryCard = ({
  project,
  loading,
}: ProjectSummaryCardProps) => {
  return (
    <>
      <ProjectHeaderCard project={project} loading={loading} />
      <ProjectInfoCard project={project} loading={loading} />
    </>
  );
};
