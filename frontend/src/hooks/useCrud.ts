import {
  useQuery,
  useMutation,
  useQueryClient,
  UseQueryOptions,
  UseMutationOptions,
} from "@tanstack/react-query";
import { toast } from "sonner";

/**
 * @fileoverview Generic CRUD Hook Factory
 *
 * **WHEN TO USE THIS GENERIC HOOK:**
 *
 * ✅ **USE FOR:** Simple, non-versioned entities (departments, cost element types, users)
 *    - Entities WITHOUT Time Machine context (no branch/asOf/mode parameters)
 *    - Entities WITHOUT versioning requirements (no history tracking)
 *    - Standard CRUD operations only (create, read, update, delete)
 *
 * ❌ **DO NOT USE FOR:** Versioned entities (projects, WBEs, cost elements, forecasts)
 *    - These should use `useVersionedCrud` from `@/hooks/useVersionedCrud.ts`
 *    - Versioned entities require Time Machine context and special cache keys
 *    - Always prefer domain-specific hooks from `@/features/{domain}/api/`
 *
 * **QUERY KEY PATTERN:**
 *
 * This generic hook creates query keys like: `[resourceName, "list", filters]`
 * This is acceptable for simple entities but does NOT integrate with the centralized
 * `queryKeys` factory at `@/api/queryKeys.ts`.
 *
 * For new code, prefer using the queryKeys factory directly:
 *
 * @example
 * ```typescript
 * // ❌ AVOID: Generic useCrud for versioned entities
 * const { useList, useCreate } = createResourceHooks(
 *   "projects",  // Wrong! Projects are versioned
 *   ProjectService
 * );
 *
 * // ✅ CORRECT: Use domain-specific hooks with factory keys
 * import { useProjects, useCreateProject } from "@/features/projects/api/useProjects";
 * // These hooks use queryKeys.projects.list() with Time Machine context
 *
 * // ✅ ACCEPTABLE: Generic useCrud for simple entities
 * const { useList, useCreate } = createResourceHooks(
 *   "departments",  // OK! Departments are not versioned
 *   DepartmentService
 * );
 * ```
 */

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
export interface LegacyApiMethods<T, TCreate, TUpdate, TList = T[]> {
  getUsers?: (filters?: any) => Promise<TList>;
  getUser?: (id: string) => Promise<T>;
  createUser?: (data: TCreate) => Promise<T>;
  updateUser?: (id: string, data: TUpdate) => Promise<T>;
  deleteUser?: (id: string) => Promise<void>;
}

/**
 * API methods using semantic names (new direct pattern).
 * This interface allows direct usage of service methods without adapters.
 */
export interface NamedApiMethods<T, TCreate, TUpdate, TList = T[]> {
  list?: (filters?: any) => Promise<TList>;
  detail?: (id: string) => Promise<T>;
  create?: (data: TCreate) => Promise<T>;
  update?: (id: string, data: TUpdate) => Promise<T>;
  delete?: (id: string) => Promise<void>;
}

export type ApiMethods<T, TCreate, TUpdate, TList = T[]> =
  | LegacyApiMethods<T, TCreate, TUpdate, TList>
  | NamedApiMethods<T, TCreate, TUpdate, TList>;

/**
 * Creates a set of React Query hooks for CRUD operations on a resource.
 *
 * ...
 */
export const createResourceHooks = <T, TCreate, TUpdate, TList = T[]>(
  queryKey: string,
  api: ApiMethods<T, TCreate, TUpdate, TList>,
  options?: CrudOptions
) => {
  // Normalize invalidation arrays
  const getInvalidationKeys = (type: "create" | "update" | "delete") => {
    const keys = options?.invalidation?.[type] || [];
    return [queryKey, ...keys];
  };

  // Detect which API pattern is being used
  const isLegacy = "getUsers" in api || "getUser" in api;

  const useList = (
    filters?: unknown,
    queryOptions?: Omit<UseQueryOptions<TList, Error>, "queryKey">
  ) => {
    return useQuery({
      queryKey: [queryKey, "list", filters],
      queryFn: () => {
        const listFn = isLegacy
          ? (api as LegacyApiMethods<T, TCreate, TUpdate, TList>).getUsers
          : (api as NamedApiMethods<T, TCreate, TUpdate, TList>).list;
        if (!listFn) throw new Error("list method not implemented");
        return listFn(filters);
      },
      ...queryOptions,
    });
  };

  const useDetail = (
    id: string,
    queryOptions?: Omit<UseQueryOptions<T, Error>, "queryKey">
  ) => {
    return useQuery({
      queryKey: [queryKey, "detail", id],
      queryFn: () => {
        const detailFn = isLegacy
          ? (api as LegacyApiMethods<T, TCreate, TUpdate, TList>).getUser
          : (api as NamedApiMethods<T, TCreate, TUpdate, TList>).detail;
        if (!detailFn) throw new Error("detail method not implemented");
        return detailFn(id);
      },
      enabled: !!id,
      ...queryOptions,
    });
  };

  const useCreate = (
    mutationOptions?: Omit<UseMutationOptions<T, Error, TCreate>, "mutationFn">
  ) => {
    const queryClient = useQueryClient();
    return useMutation({
      mutationFn: (data: TCreate) => {
        const createFn = isLegacy
          ? (api as LegacyApiMethods<T, TCreate, TUpdate, TList>).createUser
          : (api as NamedApiMethods<T, TCreate, TUpdate, TList>).create;
        if (!createFn) throw new Error("create method not implemented");
        return createFn(data);
      },
      onSuccess: (...args) => {
        const keys = getInvalidationKeys("create");
        keys.forEach((key) =>
          queryClient.invalidateQueries({ queryKey: [key] })
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
    >
  ) => {
    const queryClient = useQueryClient();
    return useMutation({
      mutationFn: ({ id, data }: { id: string; data: TUpdate }) => {
        const updateFn = isLegacy
          ? (api as LegacyApiMethods<T, TCreate, TUpdate, TList>).updateUser
          : (api as NamedApiMethods<T, TCreate, TUpdate, TList>).update;
        if (!updateFn) throw new Error("update method not implemented");
        return updateFn(id, data);
      },
      onSuccess: (...args) => {
        const keys = getInvalidationKeys("update");
        keys.forEach((key) =>
          queryClient.invalidateQueries({ queryKey: [key] })
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
    >
  ) => {
    const queryClient = useQueryClient();
    return useMutation({
      mutationFn: (id: string) => {
        const deleteFn = isLegacy
          ? (api as LegacyApiMethods<T, TCreate, TUpdate, TList>).deleteUser
          : (api as NamedApiMethods<T, TCreate, TUpdate, TList>).delete;
        if (!deleteFn) throw new Error("delete method not implemented");
        return deleteFn(id);
      },
      onSuccess: (...args) => {
        const keys = getInvalidationKeys("delete");
        keys.forEach((key) =>
          queryClient.invalidateQueries({ queryKey: [key] })
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
