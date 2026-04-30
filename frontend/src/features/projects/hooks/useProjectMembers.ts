/**
 * Project Members Hooks
 *
 * TanStack Query hooks for managing project members.
 */

import {
  useQuery,
  useMutation,
  useQueryClient,
  UseQueryOptions,
  UseMutationOptions,
} from "@tanstack/react-query";
import { toast } from "sonner";
import { OpenAPI } from "@/api/generated/core/OpenAPI";
import { request as __request } from "@/api/generated/core/request";
import { queryKeys } from "@/api/queryKeys";
import type {
  ProjectMemberRead,
  ProjectMemberCreate,
  ProjectMemberUpdate,
} from "../types/projectMembers";

/**
 * Helper to format UUID for URL
 */
function formatUUID(uuid: string): string {
  return uuid;
}

/**
 * Fetch project members for a given project
 */
export const useProjectMembers = (
  projectId: string | undefined,
  queryOptions?: Omit<UseQueryOptions<ProjectMemberRead[], Error>, "queryKey">
) => {
  return useQuery<ProjectMemberRead[]>({
    queryKey: queryKeys.projects.list(projectId ? [projectId, "members"] : []),
    queryFn: async () => {
      if (!projectId) throw new Error("Project ID is required");

      return __request(OpenAPI, {
        method: "GET",
        url: `/api/v1/projects/${formatUUID(projectId)}/members`,
      }) as Promise<ProjectMemberRead[]>;
    },
    enabled: !!projectId,
    ...queryOptions,
  });
};

/**
 * Add a member to a project
 */
export const useAddProjectMember = (
  mutationOptions?: Omit<
    UseMutationOptions<ProjectMemberRead, Error, ProjectMemberCreate>,
    "mutationFn"
  >,
) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: ProjectMemberCreate) => {
      return __request(OpenAPI, {
        method: "POST",
        url: `/api/v1/projects/${formatUUID(data.project_id)}/members`,
        body: data,
      }) as Promise<ProjectMemberRead>;
    },
    onSuccess: (data, variables) => {
      // Invalidate the project members list for this project
      queryClient.invalidateQueries({
        queryKey: queryKeys.projects.list([variables.project_id, "members"]),
      });
      toast.success("Member added successfully");
      mutationOptions?.onSuccess?.(data, variables);
    },
    onError: (error, ...args) => {
      toast.error(`Error adding member: ${error.message}`);
      mutationOptions?.onError?.(error, ...args);
    },
  });
};

/**
 * Remove a member from a project
 */
export const useRemoveProjectMember = (
  mutationOptions?: Omit<
    UseMutationOptions<void, Error, { projectId: string; userId: string }>,
    "mutationFn"
  >,
) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ projectId, userId }: { projectId: string; userId: string }) => {
      return __request(OpenAPI, {
        method: "DELETE",
        url: `/api/v1/projects/${formatUUID(projectId)}/members/${formatUUID(userId)}`,
      }) as Promise<void>;
    },
    onSuccess: (_, variables) => {
      // Invalidate the project members list for this project
      queryClient.invalidateQueries({
        queryKey: queryKeys.projects.list([variables.projectId, "members"]),
      });
      toast.success("Member removed successfully");
      mutationOptions?.onSuccess?.(_, variables);
    },
    onError: (error, ...args) => {
      toast.error(`Error removing member: ${error.message}`);
      mutationOptions?.onError?.(error, ...args);
    },
  });
};

/**
 * Update a project member's role
 */
export const useUpdateProjectMember = (
  mutationOptions?: Omit<
    UseMutationOptions<
      ProjectMemberRead,
      Error,
      { projectId: string; userId: string; update: ProjectMemberUpdate }
    >,
    "mutationFn"
  >,
) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      projectId,
      userId,
      update,
    }: {
      projectId: string;
      userId: string;
      update: ProjectMemberUpdate;
    }) => {
      return __request(OpenAPI, {
        method: "PATCH",
        url: `/api/v1/projects/${formatUUID(projectId)}/members/${formatUUID(userId)}`,
        body: update,
      }) as Promise<ProjectMemberRead>;
    },
    onSuccess: (_, variables) => {
      // Invalidate the project members list for this project
      queryClient.invalidateQueries({
        queryKey: queryKeys.projects.list([variables.projectId, "members"]),
      });
      toast.success("Member role updated successfully");
      mutationOptions?.onSuccess?.(_, variables);
    },
    onError: (error, ...args) => {
      toast.error(`Error updating member role: ${error.message}`);
      mutationOptions?.onError?.(error, ...args);
    },
  });
};
