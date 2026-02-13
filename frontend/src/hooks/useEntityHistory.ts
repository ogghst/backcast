import { useQuery } from "@tanstack/react-query";

/**
 * @fileoverview Generic Entity History Hook
 *
 * **WHEN TO USE THIS GENERIC HOOK:**
 *
 * ✅ **USE FOR:** Quick UI components (VersionHistoryDrawer, history modals)
 *    - When you need a simple, reusable way to fetch entity version history
 *    - Works with ANY entity that has a history endpoint
 *    - Flexible: pass any fetch function for the specific entity
 *
 * ❌ **DO NOT USE FOR:** Main data fetching in components
 *    - For primary data, use domain-specific hooks from `@/features/{domain}/api/`
 *    - Those hooks use the centralized `queryKeys` factory at `@/api/queryKeys.ts`
 *    - This generic hook creates manual query keys: `[resource, entityId, "history"]`
 *
 * **QUERY KEY PATTERN:**
 *
 * This hook creates generic query keys like: `[resource, entityId, "history"]`
 * These keys do NOT integrate with the centralized queryKeys factory.
 *
 * This is ACCEPTABLE for history views because:
 * 1. History data is UI auxiliary (not primary application state)
 * 2. History keys don't need complex invalidation logic
 * 3. Flexibility to work with any entity is more valuable here
 *
 * For main entity data, ALWAYS prefer factory keys:
 *
 * @example
 * ```typescript
 * // ✅ CORRECT: Domain-specific hook for primary data
 * import { useProjects } from "@/features/projects/api/useProjects";
 * const { data: project } = useProjects();  // Uses queryKeys.projects.detail()
 *
 * // ✅ CORRECT: Generic hook for UI component (history drawer)
 * const { data: history } = useEntityHistory({
 *   resource: "projects",
 *   entityId: project?.project_id,
 *   fetchFn: (id) => ProjectsService.getProjectHistory(id),
 * });
 * ```
 */

interface UseEntityHistoryOptions<T> {
  /** Resource name (e.g., "users", "projects", "departments") */
  resource: string;
  /** Root entity ID to fetch history for */
  entityId: string | null | undefined;
  /** Function to fetch history for the given entity ID */
  fetchFn: (id: string) => Promise<T[]>;
  /** Whether the query should run (default: true when entityId exists) */
  enabled?: boolean;
}

/**
 * Generic hook for fetching version history of any versioned entity.
 *
 * @example
 * ```typescript
 * // For users
 * const { data: history, isLoading } = useEntityHistory({
 *   resource: "users",
 *   entityId: user?.user_id,
 *   fetchFn: UserService.getUserHistory,
 *   enabled: drawerOpen,
 * });
 *
 * // For projects
 * const { data: history, isLoading } = useEntityHistory({
 *   resource: "projects",
 *   entityId: project?.project_id,
 *   fetchFn: ProjectService.getProjectHistory,
 *   enabled: drawerOpen,
 * });
 * ```
 */
export const useEntityHistory = <T>({
  resource,
  entityId,
  fetchFn,
  enabled = true,
}: UseEntityHistoryOptions<T>) => {
  return useQuery({
    queryKey: [resource, entityId, "history"],
    queryFn: async () => {
      if (!entityId) return [];
      return await fetchFn(entityId);
    },
    enabled: enabled && !!entityId,
    staleTime: 30000, // Consider data fresh for 30 seconds
  });
};
