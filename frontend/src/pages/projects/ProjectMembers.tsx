/**
 * Project Members Page
 *
 * Displays the member management interface for a specific project.
 */

import { useParams } from "react-router-dom";
import { useProject } from "@/features/projects/api/useProjects";
import { ProjectMemberManager } from "@/features/projects/components/ProjectMemberManager";
import { ProjectPage } from "@/features/projects/components/ProjectPage";

export const ProjectMembers = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const { data: project, isLoading: isProjectLoading } = useProject(projectId || "");

  if (!projectId) {
    return null;
  }

  if (isProjectLoading) {
    return (
      <ProjectPage title="Members">
        <div>Loading project information...</div>
      </ProjectPage>
    );
  }

  if (!project) {
    return (
      <ProjectPage title="Members">
        <div>Project not found</div>
      </ProjectPage>
    );
  }

  return (
    <ProjectPage title="Members">
      <ProjectMemberManager projectId={projectId} projectName={project.name} />
    </ProjectPage>
  );
};
