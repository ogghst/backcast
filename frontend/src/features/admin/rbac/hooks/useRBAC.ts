/**
 * TanStack Query hooks for RBAC admin endpoints.
 *
 * Uses the global axios instance (apiClient) directly because the RBAC admin
 * API (/api/v1/admin/rbac) is not yet included in the generated OpenAPI client.
 *
 * Query keys follow the centralized factory at @/api/queryKeys.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import type {
  RBACRoleRead,
  RBACRoleCreate,
  RBACRoleUpdate,
  RBACProviderStatus,
} from "@/api/types/rbac";

const BASE_URL = "/api/v1/admin/rbac";

// ---------------------------------------------------------------------------
// Queries
// ---------------------------------------------------------------------------

export function useRBACRoles() {
  return useQuery({
    queryKey: queryKeys.adminRbac.roles.list,
    queryFn: async () => {
      const { data } = await apiClient.get<RBACRoleRead[]>(
        `${BASE_URL}/roles`,
      );
      return data;
    },
  });
}

export function useRBACPermissions() {
  return useQuery({
    queryKey: queryKeys.adminRbac.permissions,
    queryFn: async () => {
      const { data } = await apiClient.get<string[]>(
        `${BASE_URL}/permissions`,
      );
      return data;
    },
  });
}

export function useRBACProviderStatus() {
  return useQuery({
    queryKey: queryKeys.adminRbac.providerStatus,
    queryFn: async () => {
      const { data } = await apiClient.get<RBACProviderStatus>(
        `${BASE_URL}/provider-status`,
      );
      return data;
    },
  });
}

// ---------------------------------------------------------------------------
// Mutations
// ---------------------------------------------------------------------------

export function useCreateRBACRole() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (role: RBACRoleCreate) => {
      const { data } = await apiClient.post<RBACRoleRead>(
        `${BASE_URL}/roles`,
        role,
      );
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.adminRbac.roles.all,
      });
    },
  });
}

export function useUpdateRBACRole() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      ...updates
    }: { id: string } & RBACRoleUpdate) => {
      const { data } = await apiClient.put<RBACRoleRead>(
        `${BASE_URL}/roles/${id}`,
        updates,
      );
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.adminRbac.roles.all,
      });
    },
  });
}

export function useDeleteRBACRole() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await apiClient.delete(`${BASE_URL}/roles/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.adminRbac.roles.all,
      });
    },
  });
}
