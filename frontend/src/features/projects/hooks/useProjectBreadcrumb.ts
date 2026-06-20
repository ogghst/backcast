import { useProject } from "@/features/projects/api/useProjects";
import type { BreadcrumbEntry } from "@/components/common/EntityBreadcrumb";

/**
 * Builds the project-code breadcrumb entry for project subpages.
 *
 * Returns only the project-code crumb (with a link back to the project root);
 * `EntityBreadcrumb` automatically prepends Home › Projects.
 *
 * Reuses `useProject` — TanStack Query deduplicates by key, so adding this to a
 * page that already fetched the project costs nothing after the first load.
 */
export function useProjectBreadcrumb(
  projectId?: string,
): { items: BreadcrumbEntry[]; loading: boolean } {
  const { data: project, isLoading } = useProject(projectId || "");

  const items: BreadcrumbEntry[] = [
    {
      label: project?.code || "Project",
      to: projectId ? `/projects/${projectId}` : undefined,
    },
  ];

  return { items, loading: isLoading };
}
