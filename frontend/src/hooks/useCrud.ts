import {
  useQuery,
  useMutation,
  useQueryClient,
  UseQueryOptions,
  UseMutationOptions,
} from "@tanstack/react-query";
import { toast } from "sonner";

export interface CrudOptions {
  invalidation?: {
    create?: string[];
    update?: string[];
    delete?: string[];
  };
}

/**
 * API methods using generic names (legacy adapter pattern).
 * This interface allows the old adapter pattern to continue working.
 */
export interface LegacyApiMethods<T, TCreate, TUpdate> {
  getUsers?: (filters?: Record<string, unknown>) => Promise<T[]>;
  getUser?: (id: string) => Promise<T>;
  createUser?: (data: TCreate) => Promise<T>;
  updateUser?: (id: string, data: TUpdate) => Promise<T>;
  deleteUser?: (id: string) => Promise<void>;
}

/**
 * API methods using semantic names (new direct pattern).
 * This interface allows direct usage of service methods without adapters.
 */
export interface NamedApiMethods<T, TCreate, TUpdate> {
  list?: (filters?: Record<string, unknown>) => Promise<T[]>;
  detail?: (id: string) => Promise<T>;
  create?: (data: TCreate) => Promise<T>;
  update?: (id: string, data: TUpdate) => Promise<T>;
  delete?: (id: string) => Promise<void>;
}

export type ApiMethods<T, TCreate, TUpdate> =
  | LegacyApiMethods<T, TCreate, TUpdate>
  | NamedApiMethods<T, TCreate, TUpdate>;

/**
 * Creates a set of React Query hooks for CRUD operations on a resource.
 *
 * Supports two patterns:
 *
 * 1. Legacy adapter pattern (backward compatible):
 *    ```ts
 *    const adapter = {
 *      getUsers: (params) => ProjectsService.getProjects(...),
 *      getUser: (id) => ProjectsService.getProject(id),
 *      createUser: (data) => ProjectsService.createProject(data),
 *      updateUser: (id, data) => ProjectsService.updateProject(id, data),
 *      deleteUser: (id) => ProjectsService.deleteProject(id),
 *    };
 *    const { useList } = createResourceHooks("projects", adapter);
 *    ```
 *
 * 2. New direct pattern (recommended):
 *    ```ts
 *    const { useList } = createResourceHooks("projects", {
 *      list: ProjectsService.getProjects,
 *      detail: ProjectsService.getProject,
 *      create: ProjectsService.createProject,
 *      update: ProjectsService.updateProject,
 *      delete: ProjectsService.deleteProject,
 *    });
 *    ```
 */
export const createResourceHooks = <T, TCreate, TUpdate>(
  queryKey: string,
  api: ApiMethods<T, TCreate, TUpdate>,
  options?: CrudOptions,
) => {
  // Normalize invalidation arrays
  const getInvalidationKeys = (type: "create" | "update" | "delete") => {
    const keys = options?.invalidation?.[type] || [];
    return [queryKey, ...keys];
  };

  // Detect which API pattern is being used
  const isLegacy = "getUsers" in api || "getUser" in api;

  const useList = (
    filters?: Record<string, unknown>,
    queryOptions?: Omit<UseQueryOptions<T[], Error>, "queryKey">,
  ) => {
    return useQuery({
      queryKey: [queryKey, "list", filters],
      queryFn: () => {
        const listFn = isLegacy
          ? (api as LegacyApiMethods<T, TCreate, TUpdate>).getUsers
          : (api as NamedApiMethods<T, TCreate, TUpdate>).list;
        if (!listFn) throw new Error("list method not implemented");
        return listFn(filters);
      },
      ...queryOptions,
    });
  };

  const useDetail = (
    id: string,
    queryOptions?: Omit<UseQueryOptions<T, Error>, "queryKey">,
  ) => {
    return useQuery({
      queryKey: [queryKey, "detail", id],
      queryFn: () => {
        const detailFn = isLegacy
          ? (api as LegacyApiMethods<T, TCreate, TUpdate>).getUser
          : (api as NamedApiMethods<T, TCreate, TUpdate>).detail;
        if (!detailFn) throw new Error("detail method not implemented");
        return detailFn(id);
      },
      enabled: !!id,
      ...queryOptions,
    });
  };

  const useCreate = (
    mutationOptions?: Omit<UseMutationOptions<T, Error, TCreate>, "mutationFn">,
  ) => {
    const queryClient = useQueryClient();
    return useMutation({
      mutationFn: (data: TCreate) => {
        const createFn = isLegacy
          ? (api as LegacyApiMethods<T, TCreate, TUpdate>).createUser
          : (api as NamedApiMethods<T, TCreate, TUpdate>).create;
        if (!createFn) throw new Error("create method not implemented");
        return createFn(data);
      },
      onSuccess: (...args) => {
        const keys = getInvalidationKeys("create");
        keys.forEach((key) =>
          queryClient.invalidateQueries({ queryKey: [key] }),
        );
        toast.success(`Created successfully`);
        mutationOptions?.onSuccess?.(...args);
      },
      onError: (error, ...args) => {
        toast.error(`Error creating: ${error.message}`);
        mutationOptions?.onError?.(error, ...args);
      },
      ...mutationOptions,
    });
  };

  const useUpdate = (
    mutationOptions?: Omit<
      UseMutationOptions<T, Error, { id: string; data: TUpdate }>,
      "mutationFn"
    >,
  ) => {
    const queryClient = useQueryClient();
    return useMutation({
      mutationFn: ({ id, data }: { id: string; data: TUpdate }) => {
        const updateFn = isLegacy
          ? (api as LegacyApiMethods<T, TCreate, TUpdate>).updateUser
          : (api as NamedApiMethods<T, TCreate, TUpdate>).update;
        if (!updateFn) throw new Error("update method not implemented");
        return updateFn(id, data);
      },
      onSuccess: (...args) => {
        const keys = getInvalidationKeys("update");
        keys.forEach((key) =>
          queryClient.invalidateQueries({ queryKey: [key] }),
        );
        toast.success(`Updated successfully`);
        mutationOptions?.onSuccess?.(...args);
      },
      onError: (error, ...args) => {
        toast.error(`Error updating: ${error.message}`);
        mutationOptions?.onError?.(error, ...args);
      },
      ...mutationOptions,
    });
  };

  const useDelete = (
    mutationOptions?: Omit<
      UseMutationOptions<void, Error, string>,
      "mutationFn"
    >,
  ) => {
    const queryClient = useQueryClient();
    return useMutation({
      mutationFn: (id: string) => {
        const deleteFn = isLegacy
          ? (api as LegacyApiMethods<T, TCreate, TUpdate>).deleteUser
          : (api as NamedApiMethods<T, TCreate, TUpdate>).delete;
        if (!deleteFn) throw new Error("delete method not implemented");
        return deleteFn(id);
      },
      onSuccess: (...args) => {
        const keys = getInvalidationKeys("delete");
        keys.forEach((key) =>
          queryClient.invalidateQueries({ queryKey: [key] }),
        );
        toast.success(`Deleted successfully`);
        mutationOptions?.onSuccess?.(...args);
      },
      onError: (error, ...args) => {
        toast.error(`Error deleting: ${error.message}`);
        mutationOptions?.onError?.(error, ...args);
      },
      ...mutationOptions,
    });
  };

  return {
    useList,
    useDetail,
    useCreate,
    useUpdate,
    useDelete,
  };
};
