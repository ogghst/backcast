/**
 * ProjectChat Page
 *
 * Project-specific AI chat interface.
 * Scopes the AI chat session to a specific project context,
 * allowing the LLM to focus on project data.
 */

import { useEffect } from "react";
import { useParams } from "react-router-dom";
import { ChatInterface } from "@/features/ai/chat/components/ChatInterface";
import { useTimeMachineStore } from "@/stores/useTimeMachineStore";
import { useProject } from "@/features/projects/api/useProjects";

/**
 * Project-specific chat page component.
 *
 * This component:
 * 1. Extracts the projectId from route params
 * 2. Fetches the project data to get the stable root_id
 * 3. Sets the Time Machine context to scope temporal queries to this project
 * 4. Passes the stable project_id to ChatInterface for project-scoped AI chat
 *
 * @example
 * ```tsx
 * // Route: /projects/:projectId/chat
 * <ProjectChat />
 * ```
 */
export const ProjectChat = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const setCurrentProject = useTimeMachineStore((state) => state.setCurrentProject);
  const { data: project } = useProject(projectId!);

  // Set Time Machine context to this project on mount
  useEffect(() => {
    if (projectId) {
      setCurrentProject(projectId);
    }
  }, [projectId, setCurrentProject]);

  // Pass the stable root_id from project data to ChatInterface
  return <ChatInterface projectId={project?.project_id} />;
};
