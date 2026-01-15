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
import type { Branch } from "@/types/branch";
// Custom params interface
export interface ProjectListParams {
  pagination?: {
    current?: number;
    pageSize?: number;
  };
  filters?: Record<
    string,
    (string | number | boolean | bigint)[] | null | undefined
  >;
  sorter?: {
    field?: string | string[];
    order?: string;
  };
  search?: string;
  sortField?: string;
  sortOrder?: string;
  queryOptions?: any;
}

/**
/**
 * Parameters for server-side filtering, search, and sorting.
 */

/**
 * Helper to extract pagination params from filters object.
 */
const getPaginationParams = (params?: ProjectListParams) => {
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

// Custom useProjects list hook with Time Machine integration
export const useProjects = (params?: ProjectListParams) => {
  const { asOf, mode } = useTimeMachineParams();

  return useQuery<PaginatedResponse<ProjectRead>>({
    queryKey: ["projects", params, { asOf, mode }],
    queryFn: async () => {
      const serverParams = getPaginationParams(params);

      // Manual request to support as_of and mode query params
      return __request(OpenAPI, {
        method: "GET",
        url: "/api/v1/projects",
        query: {
          ...serverParams,
          as_of: asOf || undefined,
          mode: mode,
        },
      }) as Promise<PaginatedResponse<ProjectRead>>;
    },
    ...params?.queryOptions,
  });
};

/**
 * Custom create hook with Time Machine integration.
 * Automatically injects control_date and branch from TimeMachine context.
 */
export const useCreateProject = (
  mutationOptions?: Omit<
    UseMutationOptions<ProjectRead, Error, ProjectCreate>,
    "mutationFn"
  >
) => {
  const { asOf, branch } = useTimeMachineParams();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: ProjectCreate) => {
      const payload = { ...data, control_date: asOf || null, branch };
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
 * Automatically injects control_date and branch from TimeMachine context.
 */
export const useUpdateProject = (
  mutationOptions?: Omit<
    UseMutationOptions<ProjectRead, Error, { id: string; data: ProjectUpdate }>,
    "mutationFn"
  >
) => {
  const { asOf, branch } = useTimeMachineParams();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: ProjectUpdate }) => {
      const payload = { ...data, control_date: asOf || null, branch };
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

/**
 * Custom hook to fetch branches for a project.
 * Returns main branch plus any change order branches (co-{code}).
 */
/**
 * Custom hook to fetch branches for a project.
 * Returns main branch plus any change order branches.
 */
export const useProjectBranches = (
  projectId: string | undefined,
  queryOptions?: Omit<UseQueryOptions<Branch[], Error>, "queryKey">
) => {
  return useQuery<Branch[]>({
    queryKey: ["projects", projectId, "branches"],
    queryFn: async () => {
      if (!projectId) throw new Error("Project ID is required");

      return __request(OpenAPI, {
        method: "GET",
        url: `/api/v1/projects/${projectId}/branches`,
      }) as Promise<Branch[]>;
    },
    enabled: !!projectId,
    ...queryOptions,
  });
};
