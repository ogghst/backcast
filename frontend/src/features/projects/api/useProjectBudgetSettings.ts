import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  ProjectBudgetSettingsService,
  type ProjectBudgetSettingsRead,
  type ProjectBudgetSettingsCreate,
} from "@/api/generated";
import { queryKeys } from "@/api/queryKeys";

/**
 * Custom hook to fetch budget settings for a project.
 * Returns the project's budget warning threshold and admin override settings.
 *
 * @param projectId - The project ID to fetch budget settings for
 * @param queryOptions - Optional TanStack Query options
 *
 * @example
 * ```tsx
 * const { data: settings, isLoading, error } = useProjectBudgetSettings(projectId);
 * ```
 */
export const useProjectBudgetSettings = (
  projectId: string | undefined,
  queryOptions?: Omit<
    ReturnType<typeof useQuery<ProjectBudgetSettingsRead, Error>>,
    "queryKey" | "queryFn"
  >,
) => {
  return useQuery<ProjectBudgetSettingsRead>({
    queryKey: queryKeys.projects.detail(projectId || ""),
    queryFn: async () => {
      if (!projectId) throw new Error("Project ID is required");

      try {
        return await ProjectBudgetSettingsService.getProjectBudgetSettings(
          projectId,
        );
      } catch (error: unknown) {
        // Return default settings if none exist (404)
        if (
          error &&
          typeof error === "object" &&
          "status" in error &&
          error.status === 404
        ) {
          return {
            id: "",
            project_budget_settings_id: "",
            project_id: projectId,
            created_by: "",
            warning_threshold_percent: "80.0",
            allow_project_admin_override: true,
          };
        }
        throw error;
      }
    },
    enabled: !!projectId,
    staleTime: 5 * 60 * 1000, // 5 minutes
    ...queryOptions,
  });
};

/**
 * Custom hook to update budget settings for a project.
 * Creates new settings if none exist, or updates existing settings.
 *
 * @param mutationOptions - Optional TanStack Query mutation options
 *
 * @example
 * ```tsx
 * const updateSettings = useUpdateProjectBudgetSettings({
 *   onSuccess: () => {
 *     toast.success('Budget settings updated');
 *   }
 * });
 *
 * updateSettings.mutate({
 *   projectId: 'project-123',
 *   settings: { warning_threshold_percent: 85, allow_project_admin_override: true }
 * });
 * ```
 */
export const useUpdateProjectBudgetSettings = (
  mutationOptions?: Omit<
    ReturnType<
      typeof useMutation<
        ProjectBudgetSettingsRead,
        Error,
        { projectId: string; settings: ProjectBudgetSettingsCreate }
      >
    >,
    "mutationFn"
  >,
) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      projectId,
      settings,
    }: {
      projectId: string;
      settings: ProjectBudgetSettingsCreate;
    }) => {
      return await ProjectBudgetSettingsService.updateProjectBudgetSettings(
        projectId,
        settings,
      );
    },
    onSuccess: (data, variables) => {
      // Invalidate the project budget settings query
      queryClient.invalidateQueries({
        queryKey: queryKeys.projects.detail(variables.projectId),
      });
      toast.success("Budget settings updated successfully");
      mutationOptions?.onSuccess?.(data, variables, undefined);
    },
    onError: (error, variables) => {
      toast.error(
        `Failed to update budget settings: ${
          error instanceof Error ? error.message : "Unknown error"
        }`,
      );
      mutationOptions?.onError?.(error, variables, undefined);
    },
  });
};
