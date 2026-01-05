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

export const createResourceHooks = <T, TCreate, TUpdate>(
  queryKey: string,
  api: {
    getUsers?: (filters?: Record<string, unknown>) => Promise<T[]>;
    getUser?: (id: string) => Promise<T>;
    createUser?: (data: TCreate) => Promise<T>;
    updateUser?: (id: string, data: TUpdate) => Promise<T>;
    deleteUser?: (id: string) => Promise<void>;
  },
  options?: CrudOptions,
) => {
  // Normalize invalidation arrays
  const getInvalidationKeys = (type: "create" | "update" | "delete") => {
    const keys = options?.invalidation?.[type] || [];
    return [queryKey, ...keys];
  };

  const useList = (
    filters?: Record<string, unknown>,
    queryOptions?: Omit<UseQueryOptions<T[], Error>, "queryKey">,
  ) => {
    return useQuery({
      queryKey: [queryKey, "list", filters],
      queryFn: () => {
        if (!api.getUsers) throw new Error("getUsers not implemented");
        return api.getUsers(filters);
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
        if (!api.getUser) throw new Error("getUser not implemented");
        return api.getUser(id);
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
        if (!api.createUser) throw new Error("createUser not implemented");
        return api.createUser(data);
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
        if (!api.updateUser) throw new Error("updateUser not implemented");
        return api.updateUser(id, data);
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
        if (!api.deleteUser) throw new Error("deleteUser not implemented");
        return api.deleteUser(id);
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
