import React from "react";
import { ProjectRead } from "@/api/generated";
import { ProjectHeaderCard } from "@/components/projects/ProjectHeaderCard";
import { ProjectInfoCard } from "@/components/projects/ProjectInfoCard";

interface ProjectSummaryCardProps {
  project: ProjectRead;
  loading?: boolean;
}

/**
 * ProjectSummaryCard - Redesigned project summary with card-based layout.
 *
 * Combines ProjectHeaderCard and ProjectInfoCard for a refined dashboard aesthetic.
 */
export const ProjectSummaryCard = ({
  project,
  loading,
}: ProjectSummaryCardProps) => {
  return (
    <>
      <ProjectHeaderCard
        project={project}
        loading={loading}
      />
      <ProjectInfoCard project={project} loading={loading} />
    </>
  );
};
