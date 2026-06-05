/**
 * Project Members Page
 *
 * Displays the member management interface for a specific project.
 */

import { useParams } from "react-router-dom";
import { useProject } from "@/features/projects/api/useProjects";
import { ProjectMemberManager } from "@/features/projects/components/ProjectMemberManager";
import { PageWrapper } from "@/components/layout/PageWrapper";

export const ProjectMembers = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const { data: project, isLoading: isProjectLoading } = useProject(projectId || "");

  if (!projectId) {
    return null;
  }

  if (isProjectLoading) {
    return (
      <PageWrapper>
        <div>Loading project information...</div>
      </PageWrapper>
    );
  }

  if (!project) {
    return (
      <PageWrapper>
        <div>Project not found</div>
      </PageWrapper>
    );
  }

  return (
    <PageWrapper>
      <ProjectMemberManager projectId={projectId} projectName={project.name} />
    </PageWrapper>
  );
};
