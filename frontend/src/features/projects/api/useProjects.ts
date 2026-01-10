import { createResourceHooks } from "@/hooks/useCrud";
import {
  ProjectsService,
  type ProjectRead,
  type ProjectCreate,
  type ProjectUpdate,
} from "@/api/generated";
import { OpenAPI } from "@/api/generated/core/OpenAPI";
import { request as __request } from "@/api/generated/core/request";
import type { PaginatedResponse } from "@/types/api";
import { useTimeMachineParams } from "@/contexts/TimeMachineContext";
import { useQuery, UseQueryOptions } from "@tanstack/react-query";

/**
 * Parameters for server-side filtering, search, and sorting.
 */
interface ServerSideParams {
  page?: number;
  per_page?: number;
  search?: string;
  filters?: string;
  sort_field?: string;
  sort_order?: "asc" | "desc";
  branch?: string;
}

/**
 * Call the new paginated projects API with server-side filtering.
 */
const getProjectsPaginated = async (
  params?: ServerSideParams
): Promise<PaginatedResponse<ProjectRead>> => {
  return __request(OpenAPI, {
    method: "GET",
    url: "/api/v1/projects",
    query: {
      page: params?.page || 1,
      per_page: params?.per_page || 20,
      branch: params?.branch || "main",
      search: params?.search,
      filters: params?.filters,
      sort_field: params?.sort_field,
      sort_order: params?.sort_order,
    },
  });
};

/**
 * Helper to extract pagination params from filters object.
 */
const getPaginationParams = (params?: any) => {
  const current = params?.pagination?.current || 1;
  const pageSize = params?.pagination?.pageSize || 20;

  // Convert Ant Design table filters to server format
  let filterString: string | undefined;
  if (params?.filters) {
    const filterParts: string[] = [];
    Object.entries(params.filters).forEach(([key, value]) => {
      if (
        value &&
        (Array.isArray(value) ? value.length > 0 : value !== undefined)
      ) {
        const values = Array.isArray(value) ? value : [value];
        filterParts.push(`${key}:${values.join(",")}`);
      }
    });
    filterString = filterParts.length > 0 ? filterParts.join(";") : undefined;
  }

  // Support both AntD sorter object and flat params from useTableParams
  const sortField = params?.sorter?.field || params?.sortField;
  const sortOrderRaw = params?.sorter?.order || params?.sortOrder;
  const sortOrder = sortOrderRaw === "descend" ? "desc" : "asc";

  return {
    page: current,
    per_page: pageSize,
    search: params?.search,
    filters: filterString,
    sort_field: sortField,
    sort_order: sortOrder,
  };
};

// Create base hooks without time-travel support
const baseHooks = createResourceHooks<
  ProjectRead,
  ProjectCreate,
  ProjectUpdate,
  PaginatedResponse<ProjectRead>
>("projects", {
  list: async (params) => {
    const serverParams = getPaginationParams(params);
    const res = await getProjectsPaginated(serverParams);
    return res;
  },
  detail: ProjectsService.getProject,
  create: ProjectsService.createProject,
  update: ProjectsService.updateProject,
  delete: ProjectsService.deleteProject,
});

// Export list, create, update, delete as-is
export const useProjects = baseHooks.useList;
export const useCreateProject = baseHooks.useCreate;
export const useUpdateProject = baseHooks.useUpdate;
export const useDeleteProject = baseHooks.useDelete;

/**
 * Custom useProject hook with time-travel support.
 * Automatically injects as_of parameter from TimeMachine context.
 */
export const useProject = (
  id: string | undefined,
  queryOptions?: Omit<UseQueryOptions<ProjectRead, Error>, "queryKey">
) => {
  const { asOf } = useTimeMachineParams();

  return useQuery({
    queryKey: ["projects", "detail", id, { asOf }],
    queryFn: async () => {
      if (!id) throw new Error("Project ID is required");

      // Call the API with as_of parameter if available
      return __request(OpenAPI, {
        method: "GET",
        url: `/api/v1/projects/${id}`,
        query: asOf ? { as_of: asOf } : undefined,
      });
    },
    enabled: !!id,
    ...queryOptions,
  });
};
