import { useProject } from "./useProjects";

/**
 * Returns the ISO 4217 currency code for a project.
 * Falls back to "EUR" if the project is not loaded or has no currency.
 */
export function useProjectCurrency(projectId: string | undefined): string {
  const { data: project } = useProject(projectId, {
    requestHeaders: { "X-Silent-Error": "true" },
  });
  return project?.currency || "EUR";
}
