/**
 * Schedule dependency hooks
 *
 * CRUD hooks for dependency links between schedule baselines.
 * Invalidates both dependency and Gantt caches on mutation
 * so dependency arrows stay in sync.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { request as __request } from "@/api/generated/core/request";
import { OpenAPI } from "@/api/generated/core/OpenAPI";
import { queryKeys } from "@/api/queryKeys";

/** Dependency link between two schedule baselines. */
export interface ScheduleDependencyRead {
  id: string;
  schedule_dependency_id: string;
  predecessor_id: string;
  successor_id: string;
  dependency_type: string;
  lag_days: number;
  branch: string;
  project_id: string;
  created_at: string;
  updated_at: string;
}

export interface ScheduleDependencyCreate {
  predecessor_id: string;
  successor_id: string;
  dependency_type?: string;
  lag_days?: number;
  project_id: string;
  branch?: string;
}

export interface ScheduleDependencyUpdate {
  dependency_type?: string;
  lag_days?: number;
}

/** A schedule baseline option for dependency UI dropdowns. */
export interface ScheduleOption {
  schedule_baseline_id: string;
  name: string;
  code: string;
  start_date?: string | null;
  end_date?: string | null;
}

/** Format a schedule option as a display label: "CODE - Name" or "Name". */
export function formatScheduleLabel(s: { code?: string; name: string }): string {
  return s.code ? `${s.code} - ${s.name}` : s.name;
}

/**
 * Fetch schedule dependencies for a project.
 *
 * @param projectId - The project ID to fetch dependencies for
 * @param branch - Optional branch name for branch isolation
 */
export const useScheduleDependencies = (
  projectId: string,
  branch?: string,
) => {
  return useQuery<ScheduleDependencyRead[]>({
    queryKey: queryKeys.scheduleDependencies.list(projectId, branch),
    queryFn: async () => {
      const res = await __request(OpenAPI, {
        method: "GET",
        url: "/api/v1/schedule-dependencies",
        query: {
          project_id: projectId,
          branch,
        },
      });
      return res as ScheduleDependencyRead[];
    },
    enabled: !!projectId,
  });
};

/**
 * Create a new schedule dependency.
 *
 * Invalidates dependency and Gantt caches on success.
 */
export const useCreateScheduleDependency = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: ScheduleDependencyCreate) => {
      const res = await __request(OpenAPI, {
        method: "POST",
        url: "/api/v1/schedule-dependencies",
        body: data,
      });
      return res as ScheduleDependencyRead;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.scheduleDependencies.all,
      });
      queryClient.invalidateQueries({ queryKey: queryKeys.gantt.all });
    },
  });
};

/**
 * Update an existing schedule dependency.
 *
 * Invalidates dependency and Gantt caches on success.
 */
export const useUpdateScheduleDependency = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      schedule_dependency_id,
      ...data
    }: ScheduleDependencyUpdate & { schedule_dependency_id: string }) => {
      const res = await __request(OpenAPI, {
        method: "PUT",
        url: "/api/v1/schedule-dependencies/{schedule_dependency_id}",
        path: { schedule_dependency_id },
        body: data,
      });
      return res as ScheduleDependencyRead;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.scheduleDependencies.all,
      });
      queryClient.invalidateQueries({ queryKey: queryKeys.gantt.all });
    },
  });
};

/**
 * Delete a schedule dependency.
 *
 * Invalidates dependency and Gantt caches on success.
 */
export const useDeleteScheduleDependency = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (schedule_dependency_id: string) => {
      await __request(OpenAPI, {
        method: "DELETE",
        url: "/api/v1/schedule-dependencies/{schedule_dependency_id}",
        path: { schedule_dependency_id },
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.scheduleDependencies.all,
      });
      queryClient.invalidateQueries({ queryKey: queryKeys.gantt.all });
    },
  });
};
