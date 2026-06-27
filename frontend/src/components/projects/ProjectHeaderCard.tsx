import React from "react";
import { ProjectRead } from "@/api/generated";
import { getProjectStatusColor } from "@/lib/status";
import { StatusTag } from "@/components/layout";
import { EntityHeaderCard } from "@/components/common/EntityHeaderCard";

interface ProjectHeaderCardProps {
  project: ProjectRead;
  loading?: boolean;
  extraContent?: React.ReactNode;
  actualCosts?: string | number | null;
}

export const ProjectHeaderCard = ({
  project,
  loading,
  extraContent,
  actualCosts,
}: ProjectHeaderCardProps) => {
  // control_date is returned by the API but not yet in the generated type
  const controlDate = (project as Record<string, unknown>)
    .control_date as string | null | undefined;

  return (
    <EntityHeaderCard
      title={`${project.code} — ${project.name}`}
      badge={
        <StatusTag color={getProjectStatusColor(project.status)}>
          {project.status || "draft"}
        </StatusTag>
      }
      description={project.description ?? undefined}
      loading={loading}
      currency={project.currency || "EUR"}
      scheduleStart={project.start_date ?? undefined}
      scheduleEnd={project.end_date ?? undefined}
      controlDate={controlDate ?? undefined}
      budget={project.budget}
      revenue={project.contract_value}
      actualCosts={actualCosts}
      extraContent={extraContent}
    />
  );
};
