/**
 * Dashboard Layout API Hooks
 *
 * TanStack Query hooks for dashboard layout CRUD operations.
 * Uses the generated OpenAPI client (__request + OpenAPI pattern).
 *
 * Non-versioned entity -- no EVCS, no time-travel params.
 *
 * Backend routes: /api/v1/dashboard-layouts
 */

import {
  useQuery,
  useMutation,
  useQueryClient,
  type UseQueryOptions,
  type UseMutationOptions,
} from "@tanstack/react-query";
import { OpenAPI } from "@/api/generated/core/OpenAPI";
import { request as __request } from "@/api/generated/core/request";
import { queryKeys } from "@/api/queryKeys";
import type {
  DashboardLayoutRead,
  DashboardLayoutCreate,
  DashboardLayoutUpdate,
  CloneTemplateRequest,
} from "@/types/dashboard-layout";

// ---------------------------------------------------------------------------
// API functions
// ---------------------------------------------------------------------------

const API_BASE = "/api/v1/dashboard-layouts";

export const layoutApi = {
  list: (projectId?: string): Promise<DashboardLayoutRead[]> =>
    __request(OpenAPI, {
      method: "GET",
      url: API_BASE,
      query: projectId ? { project_id: projectId } : undefined,
    }),

  templates: (): Promise<DashboardLayoutRead[]> =>
    __request(OpenAPI, {
      method: "GET",
      url: `${API_BASE}/templates`,
    }),

  detail: (id: string): Promise<DashboardLayoutRead> =>
    __request(OpenAPI, {
      method: "GET",
      url: `${API_BASE}/{layout_id}`,
      path: { layout_id: id },
    }),

  create: (data: DashboardLayoutCreate): Promise<DashboardLayoutRead> =>
    __request(OpenAPI, {
      method: "POST",
      url: API_BASE,
      body: data,
    }),

  update: (args: {
    id: string;
    data: DashboardLayoutUpdate;
  }): Promise<DashboardLayoutRead> =>
    __request(OpenAPI, {
      method: "PUT",
      url: `${API_BASE}/{layout_id}`,
      path: { layout_id: args.id },
      body: args.data,
    }),

  delete: (id: string): Promise<void> =>
    __request(OpenAPI, {
      method: "DELETE",
      url: `${API_BASE}/{layout_id}`,
      path: { layout_id: id },
    }),

  updateTemplate: (args: {
    id: string;
    data: DashboardLayoutUpdate;
  }): Promise<DashboardLayoutRead> =>
    __request(OpenAPI, {
      method: "PUT",
      url: `${API_BASE}/templates/{layout_id}`,
      path: { layout_id: args.id },
      body: args.data,
    }),

  clone: (args: {
    id: string;
    data: CloneTemplateRequest;
  }): Promise<DashboardLayoutRead> =>
    __request(OpenAPI, {
      method: "POST",
      url: `${API_BASE}/{layout_id}/clone`,
      path: { layout_id: args.id },
      body: args.data,
    }),
};

// ---------------------------------------------------------------------------
// Query hooks
// ---------------------------------------------------------------------------

/**
 * List dashboard layouts for the current user, optionally filtered by project.
 */
export const useDashboardLayouts = (
  projectId?: string,
  options?: Omit<
    UseQueryOptions<DashboardLayoutRead[], Error>,
    "queryKey" | "queryFn"
  >,
) => {
  return useQuery<DashboardLayoutRead[], Error>({
    queryKey: queryKeys.dashboardLayouts.list(projectId),
    queryFn: () => layoutApi.list(projectId),
    ...options,
  });
};

/**
 * List all template dashboard layouts.
 */
export const useDashboardLayoutTemplates = (
  options?: Omit<
    UseQueryOptions<DashboardLayoutRead[], Error>,
    "queryKey" | "queryFn"
  >,
) => {
  return useQuery<DashboardLayoutRead[], Error>({
    queryKey: queryKeys.dashboardLayouts.templates(),
    queryFn: () => layoutApi.templates(),
    ...options,
  });
};

/**
 * Get a single dashboard layout by ID.
 */
export const useDashboardLayout = (
  id: string,
  options?: Omit<
    UseQueryOptions<DashboardLayoutRead, Error>,
    "queryKey" | "queryFn"
  >,
) => {
  return useQuery<DashboardLayoutRead, Error>({
    queryKey: queryKeys.dashboardLayouts.detail(id),
    queryFn: () => layoutApi.detail(id),
    enabled: !!id,
    ...options,
  });
};

// ---------------------------------------------------------------------------
// Mutation hooks
// ---------------------------------------------------------------------------

/**
 * Create a new dashboard layout.
 */
export const useCreateDashboardLayout = (
  options?: Omit<
    UseMutationOptions<DashboardLayoutRead, Error, DashboardLayoutCreate>,
    "mutationFn"
  >,
) => {
  const queryClient = useQueryClient();

  return useMutation<DashboardLayoutRead, Error, DashboardLayoutCreate>({
    mutationFn: (data) => layoutApi.create(data),
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.dashboardLayouts.all });
    },
    ...options,
  });
};

/**
 * Update an existing dashboard layout.
 */
export const useUpdateDashboardLayout = (
  options?: Omit<
    UseMutationOptions<
      DashboardLayoutRead,
      Error,
      { id: string; data: DashboardLayoutUpdate }
    >,
    "mutationFn"
  >,
) => {
  const queryClient = useQueryClient();

  return useMutation<
    DashboardLayoutRead,
    Error,
    { id: string; data: DashboardLayoutUpdate }
  >({
    mutationFn: (args) => layoutApi.update(args),
    onSettled: (_data, _error, variables) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.dashboardLayouts.all });
      queryClient.invalidateQueries({
        queryKey: queryKeys.dashboardLayouts.detail(variables.id),
      });
    },
    ...options,
  });
};

/**
 * Update an existing template layout (admin only).
 *
 * Calls the dedicated admin endpoint PUT /templates/{id}.
 */
export const useUpdateDashboardTemplate = (
  options?: Omit<
    UseMutationOptions<
      DashboardLayoutRead,
      Error,
      { id: string; data: DashboardLayoutUpdate }
    >,
    "mutationFn"
  >,
) => {
  const queryClient = useQueryClient();

  return useMutation<
    DashboardLayoutRead,
    Error,
    { id: string; data: DashboardLayoutUpdate }
  >({
    mutationFn: (args) => layoutApi.updateTemplate(args),
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.dashboardLayouts.all });
      queryClient.invalidateQueries({
        queryKey: queryKeys.dashboardLayouts.templates(),
      });
    },
    ...options,
  });
};

/**
 * Delete a dashboard layout.
 *
 * Removes the layout from cache optimistically on mutate.
 */
export const useDeleteDashboardLayout = (
  options?: Omit<
    UseMutationOptions<void, Error, string>,
    "mutationFn"
  >,
) => {
  const queryClient = useQueryClient();

  return useMutation<void, Error, string>({
    mutationFn: (id) => layoutApi.delete(id),
    onMutate: async (id) => {
      // Cancel any outgoing refetches so they don't overwrite our optimistic removal
      await queryClient.cancelQueries({ queryKey: queryKeys.dashboardLayouts.all });

      // Remove the detail entry directly
      queryClient.removeQueries({
        queryKey: queryKeys.dashboardLayouts.detail(id),
      });
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.dashboardLayouts.all });
    },
    ...options,
  });
};

/**
 * Clone a template dashboard layout for the current user.
 */
export const useCloneTemplate = (
  options?: Omit<
    UseMutationOptions<
      DashboardLayoutRead,
      Error,
      { id: string; data: CloneTemplateRequest }
    >,
    "mutationFn"
  >,
) => {
  const queryClient = useQueryClient();

  return useMutation<
    DashboardLayoutRead,
    Error,
    { id: string; data: CloneTemplateRequest }
  >({
    mutationFn: (args) => layoutApi.clone(args),
    onMutate: async (variables) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey: queryKeys.dashboardLayouts.all });

      // Optimistically add cloned layout to list caches
      const templateDetail = queryClient.getQueryData<DashboardLayoutRead>(
        queryKeys.dashboardLayouts.detail(variables.id),
      );

      if (templateDetail) {
        // Create optimistic clone entry (will be replaced by real data on success)
        const optimisticClone: DashboardLayoutRead = {
          ...templateDetail,
          id: crypto.randomUUID(),
          project_id: variables.data.project_id ?? templateDetail.project_id,
          is_template: false,
          is_default: false,
        };

        // Insert into known list caches
        const listKeysToInvalidate = [
          queryKeys.dashboardLayouts.list(variables.data.project_id),
          queryKeys.dashboardLayouts.list(undefined),
        ];

        for (const key of listKeysToInvalidate) {
          const current = queryClient.getQueryData<DashboardLayoutRead[]>(key);
          if (current) {
            queryClient.setQueryData<DashboardLayoutRead[]>(key, [
              ...current,
              optimisticClone,
            ]);
          }
        }
      }
    },
    onSuccess: () => {
      // Invalidate all layout lists and templates to refetch fresh data
      queryClient.invalidateQueries({ queryKey: queryKeys.dashboardLayouts.all });
      queryClient.invalidateQueries({
        queryKey: queryKeys.dashboardLayouts.templates(),
      });
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.dashboardLayouts.all });
    },
    ...options,
  });
};
