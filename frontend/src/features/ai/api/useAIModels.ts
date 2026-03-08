/**
 * AI Model API Hooks
 *
 * Provides TanStack Query hooks for AI Model operations.
 * Models are scoped to a provider.
 */

import axios from "axios";
import {
  useMutation,
  useQueryClient,
  UseMutationOptions,
  useQuery as useTanstackQuery,
  type UseQueryOptions,
} from "@tanstack/react-query";
import { toast } from "sonner";
import { queryKeys } from "@/api/queryKeys";
import type { AIModelPublic, AIModelCreate } from "../types";

const API_BASE = "/api/v1/ai/config";

const modelApi = {
  listAll: async (includeInactive?: boolean): Promise<AIModelPublic[]> => {
    const params = includeInactive ? { include_inactive: "true" } : {};
    const response = await axios.get<AIModelPublic[]>(`${API_BASE}/models`, { params });
    return response.data;
  },

  list: async (providerId: string, includeInactive?: boolean): Promise<AIModelPublic[]> => {
    const params = includeInactive ? { include_inactive: "true" } : {};
    const response = await axios.get<AIModelPublic[]>(`${API_BASE}/providers/${providerId}/models`, { params });
    return response.data;
  },

  create: async (providerId: string, data: AIModelCreate): Promise<AIModelPublic> => {
    const response = await axios.post<AIModelPublic>(`${API_BASE}/providers/${providerId}/models`, data);
    return response.data;
  },

  update: async (providerId: string, modelId: string, data: Partial<AIModelCreate>): Promise<AIModelPublic> => {
    const response = await axios.put<AIModelPublic>(`${API_BASE}/providers/${providerId}/models/${modelId}`, data);
    return response.data;
  },

  delete: async (providerId: string, modelId: string): Promise<void> => {
    await axios.delete(`${API_BASE}/providers/${providerId}/models/${modelId}`);
  },
};

/**
 * Hook to fetch all AI models across all providers
 * @param includeInactive - Whether to include inactive models
 */
export const useAllAIModels = (
  includeInactive?: boolean,
  options?: Omit<UseQueryOptions<AIModelPublic[], Error>, "queryKey" | "queryFn">
) => {
  return useTanstackQuery<AIModelPublic[], Error>({
    queryKey: queryKeys.ai.models.list("all", includeInactive),
    queryFn: () => modelApi.listAll(includeInactive),
    ...options,
  });
};

/**
 * Hook to fetch models for a provider
 * @param providerId - Provider ID
 * @param includeInactive - Whether to include inactive models
 */
export const useAIModels = (
  providerId: string,
  includeInactive?: boolean,
  options?: Omit<UseQueryOptions<AIModelPublic[], Error>, "queryKey" | "queryFn">
) => {
  return useTanstackQuery<AIModelPublic[], Error>({
    queryKey: queryKeys.ai.models.list(providerId, includeInactive),
    queryFn: () => modelApi.list(providerId, includeInactive),
    enabled: !!providerId,
    ...options,
  });
};

/**
 * Hook to create a new model for a provider
 */
export const useCreateAIModel = (
  options?: Omit<
    UseMutationOptions<AIModelPublic, Error, { providerId: string; data: AIModelCreate }>,
    "mutationFn"
  >
) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ providerId, data }: { providerId: string; data: AIModelCreate }) =>
      modelApi.create(providerId, data),
    onSuccess: (data, variables) => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.ai.models.list(variables.providerId),
      });
      toast.success("AI model created successfully");
      options?.onSuccess?.(data, variables, undefined);
    },
    onError: (error, ...args) => {
      toast.error(`Error creating AI model: ${error.message}`);
      options?.onError?.(error, ...args);
    },
    ...options,
  });
};

/**
 * Hook to update a model
 */
export const useUpdateAIModel = (
  options?: Omit<
    UseMutationOptions<
      AIModelPublic,
      Error,
      { providerId: string; modelId: string; data: Partial<AIModelCreate> }
    >,
    "mutationFn"
  >
) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ providerId, modelId, data }) =>
      modelApi.update(providerId, modelId, data),
    onSuccess: (data, variables) => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.ai.models.list(variables.providerId),
      });
      toast.success("AI model updated successfully");
      options?.onSuccess?.(data, variables, undefined);
    },
    onError: (error, ...args) => {
      toast.error(`Error updating AI model: ${error.message}`);
      options?.onError?.(error, ...args);
    },
    ...options,
  });
};

/**
 * Hook to delete a model
 */
export const useDeleteAIModel = (
  options?: Omit<
    UseMutationOptions<void, Error, { providerId: string; modelId: string }>,
    "mutationFn"
  >
) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ providerId, modelId }: { providerId: string; modelId: string }) =>
      modelApi.delete(providerId, modelId),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.ai.models.list(variables.providerId),
      });
      toast.success("AI model deleted successfully");
      options?.onSuccess?.(_, variables, undefined);
    },
    onError: (error, ...args) => {
      toast.error(`Error deleting AI model: ${error.message}`);
      options?.onError?.(error, ...args);
    },
    ...options,
  });
};
