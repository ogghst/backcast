/**
 * TanStack Query hooks for Role Assignment CRUD endpoints.
 *
 * Uses the global axios instance (apiClient) directly because the
 * role-assignments API (/api/v1/role-assignments) is not yet included
 * in the generated OpenAPI client.
 *
 * Query keys follow the centralized factory at @/api/queryKeys.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import type {
  UserRoleAssignmentRead,
  UserRoleAssignmentCreate,
  UserRoleAssignmentUpdate,
} from "@/api/types/roleAssignment";

const BASE_URL = "/api/v1/role-assignments";

// ---------------------------------------------------------------------------
// Queries
// ---------------------------------------------------------------------------

export function useRoleAssignments(params?: {
  userId?: string;
  scopeType?: string;
  scopeId?: string;
  roleId?: string;
}) {
  return useQuery({
    queryKey: queryKeys.roleAssignments.list(params),
    queryFn: async () => {
      const { data } = await apiClient.get<UserRoleAssignmentRead[]>(
        `${BASE_URL}/`,
        { params },
      );
      return data;
    },
  });
}

// ---------------------------------------------------------------------------
// Mutations
// ---------------------------------------------------------------------------

export function useCreateRoleAssignment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (assignment: UserRoleAssignmentCreate) => {
      const { data } = await apiClient.post<UserRoleAssignmentRead>(
        `${BASE_URL}/`,
        assignment,
      );
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.roleAssignments.lists(),
      });
    },
  });
}

export function useUpdateRoleAssignment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      ...updates
    }: { id: string } & UserRoleAssignmentUpdate) => {
      const { data } = await apiClient.put<UserRoleAssignmentRead>(
        `${BASE_URL}/${id}`,
        updates,
      );
      return data;
    },
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.roleAssignments.detail(variables.id),
      });
      queryClient.invalidateQueries({
        queryKey: queryKeys.roleAssignments.lists(),
      });
    },
  });
}

export function useDeleteRoleAssignment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await apiClient.delete(`${BASE_URL}/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.roleAssignments.lists(),
      });
    },
  });
}
