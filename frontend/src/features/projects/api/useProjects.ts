import { createResourceHooks } from "@/hooks/useCrud";
import {
  useQuery,
  useMutation,
  useQueryClient,
  UseQueryOptions,
  UseMutationOptions,
} from "@tanstack/react-query";
import { toast } from "sonner";
import { useTimeMachineParams } from "@/contexts/TimeMachineContext";
import {
  ProjectsService,
  type ProjectRead,
  type ProjectCreate,
  type ProjectUpdate,
} from "@/api/generated";
import { OpenAPI } from "@/api/generated/core/OpenAPI";
import { request as __request } from "@/api/generated/core/request";
import type { PaginatedResponse } from "@/types/api";

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
    sort_order: (sortOrder === "desc" ? "desc" : "asc") as "asc" | "desc",
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

// Custom useProjects list hook with Time Machine integration
export const useProjects = (
  params?: Parameters<typeof baseHooks.useList>[0]
) => {
  const { asOf } = useTimeMachineParams();

  return useQuery({
    queryKey: ["projects", params, { asOf }],
    queryFn: async () => {
      const serverParams = getPaginationParams(params);

      // Manual request to support as_of query param
      return __request(OpenAPI, {
        method: "GET",
        url: "/api/v1/projects",
        query: {
          ...serverParams,
          as_of: asOf || undefined,
        },
      }) as Promise<PaginatedResponse<ProjectRead>>;
    },
    ...params?.queryOptions,
  });
};

/**
 * Custom create hook with Time Machine integration.
 * Automatically injects control_date from TimeMachine context.
 */
export const useCreateProject = (
  mutationOptions?: Omit<
    UseMutationOptions<ProjectRead, Error, ProjectCreate>,
    "mutationFn"
  >
) => {
  const { asOf } = useTimeMachineParams();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: ProjectCreate) => {
      const payload = { ...data, control_date: asOf || null };
      return ProjectsService.createProject(payload);
    },
    onSuccess: (...args) => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      toast.success("Created successfully");
      mutationOptions?.onSuccess?.(...args);
    },
    onError: (error, ...args) => {
      toast.error(`Error creating: ${error.message}`);
      mutationOptions?.onError?.(error, ...args);
    },
    ...mutationOptions,
  });
};

/**
 * Custom update hook with Time Machine integration.
 * Automatically injects control_date from TimeMachine context.
 */
export const useUpdateProject = (
  mutationOptions?: Omit<
    UseMutationOptions<ProjectRead, Error, { id: string; data: ProjectUpdate }>,
    "mutationFn"
  >
) => {
  const { asOf } = useTimeMachineParams();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: ProjectUpdate }) => {
      const payload = { ...data, control_date: asOf || null };
      return ProjectsService.updateProject(id, payload);
    },
    onSuccess: (...args) => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      toast.success("Updated successfully");
      mutationOptions?.onSuccess?.(...args);
    },
    onError: (error, ...args) => {
      toast.error(`Error updating: ${error.message}`);
      mutationOptions?.onError?.(error, ...args);
    },
    ...mutationOptions,
  });
};

/**
 * Custom delete hook with Time Machine integration.
 * Automatically injects control_date from TimeMachine context as a query parameter.
 */
export const useDeleteProject = (
  mutationOptions?: Omit<UseMutationOptions<void, Error, string>, "mutationFn">
) => {
  const { asOf } = useTimeMachineParams();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => {
      return __request(OpenAPI, {
        method: "DELETE",
        url: "/api/v1/projects/{project_id}",
        path: {
          project_id: id,
        },
        query: asOf ? { control_date: asOf } : undefined,
      }) as Promise<void>;
    },
    onSuccess: (...args) => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      toast.success("Deleted successfully");
      mutationOptions?.onSuccess?.(...args);
    },
    onError: (error, ...args) => {
      toast.error(`Error deleting: ${error.message}`);
      mutationOptions?.onError?.(error, ...args);
    },
    ...mutationOptions,
  });
};

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
      }) as Promise<ProjectRead>;
    },
    enabled: !!id,
    ...queryOptions,
  });
};
