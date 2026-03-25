/**
 * Project Members Page
 *
 * Displays the member management interface for a specific project.
 */

import { useParams } from "react-router-dom";
import { useProject } from "@/features/projects/api/useProjects";
import { ProjectMemberManager } from "@/features/projects/components/ProjectMemberManager";
import { useThemeTokens } from "@/hooks/useThemeTokens";

export const ProjectMembers = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const { spacing } = useThemeTokens();
  const { data: project, isLoading: isProjectLoading } = useProject(projectId || "");

  if (!projectId) {
    return null;
  }

  if (isProjectLoading) {
    return (
      <div style={{ padding: spacing.md }}>
        <div>Loading project information...</div>
      </div>
    );
  }

  if (!project) {
    return (
      <div style={{ padding: spacing.md }}>
        <div>Project not found</div>
      </div>
    );
  }

  return (
    <div style={{ padding: spacing.md }}>
      <ProjectMemberManager projectId={projectId} projectName={project.name} />
    </div>
  );
};
