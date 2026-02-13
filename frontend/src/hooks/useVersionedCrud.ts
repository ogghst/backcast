/**
 * Version-Aware Hook Factory for TanStack Query
 *
 * Extends the basic useCrud pattern with Time Machine context awareness.
 * Automatically injects { branch, asOf, mode } into all query keys for
 * proper cache isolation when switching branches or time-traveling.
 *
 * @example
 * ```tsx
 * const {
 *   useList: useCostElements,
 *   useDetail: useCostElement,
 *   useCreate: useCreateCostElement,
 *   useUpdate: useUpdateCostElement,
 *   useDelete: useDeleteCostElement,
 * } = createVersionedResourceHooks(
 *   "cost-elements",
 *   queryKeys.costElements,
 *   {
 *     list: CostElementsService.getCostElements,
 *     detail: CostElementsService.getCostElement,
 *     create: CostElementsService.createCostElement,
 *     update: CostElementsService.updateCostElement,
 *     delete: CostElementsService.deleteCostElement,
 *   },
 *   {
 *     invalidation: {
 *       create: [queryKeys.forecasts.all],
 *       update: [queryKeys.forecasts.all],
 *       delete: [queryKeys.forecasts.all],
 *     },
 *   }
 * );
 * ```
 */

import {
  useQuery,
  useMutation,
  useQueryClient,
  UseQueryOptions,
  UseMutationOptions,
  type QueryKey,
} from "@tanstack/react-query";
import { toast } from "sonner";
import { useTimeMachineParams } from "@/contexts/TimeMachineContext";

/**
 * Query key factory methods for a resource
 */
export interface QueryKeyFactoryMethods {
  all: QueryKey;
  lists: () => QueryKey;
  list: (params?: any) => QueryKey;
  details: () => QueryKey;
  detail: (id: string, context?: any) => QueryKey;
}

/**
 * API methods using semantic names (direct service pattern)
 */
export interface VersionedApiMethods<T, TCreate, TUpdate, TList = T[]> {
  list?: (filters?: any) => Promise<TList>;
  detail?: (id: string) => Promise<T>;
  create?: (data: TCreate) => Promise<T>;
  update?: (id: string, data: TUpdate) => Promise<T>;
  delete?: (id: string) => Promise<void>;
}

/**
 * Configuration options for versioned hooks
 */
export interface VersionedHookOptions {
  // Dependent invalidations to trigger on mutations
  invalidation?: {
    create?: QueryKey[];
    update?: QueryKey[];
    delete?: QueryKey[];
  };
  // Enable optimistic updates
  optimisticUpdates?: boolean;
  // Custom toast messages
  toastMessages?: {
    create?: string;
    update?: string;
    delete?: string;
  };
}

/**
 * Creates a set of React Query hooks for CRUD operations on a versioned resource.
 *
 * Automatically injects Time Machine context ({ branch, asOf, mode }) into
 * all query keys for proper cache isolation.
 *
 * @param resourceName - Resource name for query keys
 * @param queryKeyFactory - Query key factory from queryKeys
 * @param apiMethods - API service methods
 * @param options - Configuration for invalidation and optimistic updates
 */
export const createVersionedResourceHooks = <
  T,
  TCreate,
  TUpdate,
  TList = T[]
>(
  resourceName: string,
  queryKeyFactory: QueryKeyFactoryMethods,
  apiMethods: VersionedApiMethods<T, TCreate, TUpdate, TList>,
  options?: VersionedHookOptions
) => {
  // Get Time Machine context
  const getContext = () => {
    const { branch, asOf, mode } = useTimeMachineParams();
    return { branch, asOf, mode };
  };

  // Normalize invalidation arrays
  const getInvalidationKeys = (type: "create" | "update" | "delete") => {
    const keys = options?.invalidation?.[type] || [];
    return [queryKeyFactory.all, ...keys];
  };

  const useList = (
    params?: any,
    queryOptions?: Omit<UseQueryOptions<TList, Error>, "queryKey" | "queryFn">
  ) => {
    const context = getContext();

    return useQuery({
      queryKey: queryKeyFactory.list({
        ...params,
        ...context,
      }),
      queryFn: () => {
        if (!apiMethods.list) {
          throw new Error("list method not implemented");
        }
        return apiMethods.list(params);
      },
      ...queryOptions,
    });
  };

  const useDetail = (
    id: string,
    queryOptions?: Omit<UseQueryOptions<T, Error>, "queryKey" | "queryFn">
  ) => {
    const context = getContext();

    return useQuery({
      queryKey: queryKeyFactory.detail(id, context),
      queryFn: () => {
        if (!apiMethods.detail) {
          throw new Error("detail method not implemented");
        }
        return apiMethods.detail(id);
      },
      enabled: !!id,
      ...queryOptions,
    });
  };

  const useCreate = (
    mutationOptions?: Omit<
      UseMutationOptions<T, Error, TCreate>,
      "mutationFn"
    >
  ) => {
    const queryClient = useQueryClient();
    const context = getContext();

    return useMutation({
      mutationFn: (data: TCreate) => {
        if (!apiMethods.create) {
          throw new Error("create method not implemented");
        }
        return apiMethods.create(data);
      },
      onSuccess: (...args) => {
        const keys = getInvalidationKeys("create");
        keys.forEach((key) => queryClient.invalidateQueries({ queryKey: key }));
        toast.success(options?.toastMessages?.create || "Created successfully");
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
    const context = getContext();

    return useMutation({
      mutationFn: ({ id, data }: { id: string; data: TUpdate }) => {
        if (!apiMethods.update) {
          throw new Error("update method not implemented");
        }
        return apiMethods.update(id, data);
      },
      onSuccess: (...args) => {
        const keys = getInvalidationKeys("update");
        keys.forEach((key) => queryClient.invalidateQueries({ queryKey: key }));
        toast.success(options?.toastMessages?.update || "Updated successfully");
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
    const context = getContext();

    return useMutation({
      mutationFn: (id: string) => {
        if (!apiMethods.delete) {
          throw new Error("delete method not implemented");
        }
        return apiMethods.delete(id);
      },
      onSuccess: (...args) => {
        const keys = getInvalidationKeys("delete");
        keys.forEach((key) => queryClient.invalidateQueries({ queryKey: key }));
        toast.success(options?.toastMessages?.delete || "Deleted successfully");
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
