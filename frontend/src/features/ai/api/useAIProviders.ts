/**
 * AI Provider API Hooks
 *
 * Provides TanStack Query hooks for AI Provider CRUD operations.
 * Uses the centralized query keys factory for cache management.
 */

import {
  useMutation,
  useQueryClient,
  UseMutationOptions,
  useQuery as useTanstackQuery,
  type UseQueryOptions,
} from "@tanstack/react-query";
import { toast } from "sonner";
import axios from "axios";
import { queryKeys } from "@/api/queryKeys";
import type {
  AIProviderPublic,
  AIProviderCreate,
  AIProviderUpdate,
} from "../types";

// API base URL - axios is configured with auth interceptors in client.ts
const API_BASE = "/api/v1/ai/config";

const providerApi = {
  list: async (includeInactive?: boolean): Promise<AIProviderPublic[]> => {
    const params = includeInactive ? { include_inactive: "true" } : {};
    const response = await axios.get<AIProviderPublic[]>(`${API_BASE}/providers`, { params });
    return response.data;
  },

  detail: async (id: string): Promise<AIProviderPublic> => {
    const response = await axios.get<AIProviderPublic>(`${API_BASE}/providers/${id}`);
    return response.data;
  },

  create: async (data: AIProviderCreate): Promise<AIProviderPublic> => {
    const response = await axios.post<AIProviderPublic>(`${API_BASE}/providers`, data);
    return response.data;
  },

  update: async (id: string, data: AIProviderUpdate): Promise<AIProviderPublic> => {
    const response = await axios.put<AIProviderPublic>(`${API_BASE}/providers/${id}`, data);
    return response.data;
  },

  delete: async (id: string): Promise<void> => {
    await axios.delete(`${API_BASE}/providers/${id}`);
  },
};

/**
 * Hook to fetch all AI providers
 * @param includeInactive - Whether to include inactive providers
 */
export const useAIProviders = (
  includeInactive?: boolean,
  options?: Omit<UseQueryOptions<AIProviderPublic[], Error>, "queryKey" | "queryFn">
) => {
  return useTanstackQuery<AIProviderPublic[], Error>({
    queryKey: queryKeys.ai.providers.list(includeInactive),
    queryFn: () => providerApi.list(includeInactive),
    ...options,
  });
};

/**
 * Hook to fetch a single AI provider by ID
 * @param id - Provider ID
 */
export const useAIProvider = (
  id: string,
  options?: Omit<UseQueryOptions<AIProviderPublic, Error>, "queryKey" | "queryFn">
) => {
  return useTanstackQuery<AIProviderPublic, Error>({
    queryKey: queryKeys.ai.providers.detail(id),
    queryFn: () => providerApi.detail(id),
    enabled: !!id,
    ...options,
  });
};

/**
 * Hook to create a new AI provider
 */
export const useCreateAIProvider = (
  options?: Omit<UseMutationOptions<AIProviderPublic, Error, AIProviderCreate>, "mutationFn">
) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: AIProviderCreate) => providerApi.create(data),
    onSuccess: (...args) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.ai.providers.all });
      toast.success("AI provider created successfully");
      options?.onSuccess?.(...args);
    },
    onError: (error, ...args) => {
      toast.error(`Error creating AI provider: ${error.message}`);
      options?.onError?.(error, ...args);
    },
    ...options,
  });
};

/**
 * Hook to update an existing AI provider
 */
export const useUpdateAIProvider = (
  options?: Omit<
    UseMutationOptions<AIProviderPublic, Error, { id: string; data: AIProviderUpdate }>,
    "mutationFn"
  >
) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: AIProviderUpdate }) =>
      providerApi.update(id, data),
    onSuccess: (...args) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.ai.providers.all });
      toast.success("AI provider updated successfully");
      options?.onSuccess?.(...args);
    },
    onError: (error, ...args) => {
      toast.error(`Error updating AI provider: ${error.message}`);
      options?.onError?.(error, ...args);
    },
    ...options,
  });
};

/**
 * Hook to delete an AI provider
 */
export const useDeleteAIProvider = (
  options?: Omit<UseMutationOptions<void, Error, string>, "mutationFn">
) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => providerApi.delete(id),
    onSuccess: (...args) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.ai.providers.all });
      toast.success("AI provider deleted successfully");
      options?.onSuccess?.(...args);
    },
    onError: (error, ...args) => {
      toast.error(`Error deleting AI provider: ${error.message}`);
      options?.onError?.(error, ...args);
    },
    ...options,
  });
};
