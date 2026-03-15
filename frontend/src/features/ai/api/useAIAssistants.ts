/**
 * AI Assistant API Hooks
 *
 * Provides TanStack Query hooks for AI Assistant CRUD operations.
 * Uses the centralized query keys factory for cache management.
 */

import axios from "axios";
import {
  useMutation,
  useQueryClient,
  type UseMutationOptions,
  useQuery as useTanstackQuery,
  type UseQueryOptions,
} from "@tanstack/react-query";
import { toast } from "sonner";
import { queryKeys } from "@/api/queryKeys";
import type {
  AIAssistantPublic,
  AIAssistantCreate,
  AIAssistantUpdate,
} from "../types";

// API base URL - axios is configured with auth interceptors in client.ts
const API_BASE = "/api/v1/ai/config";

const assistantApi = {
  list: async (includeInactive?: boolean): Promise<AIAssistantPublic[]> => {
    const params = includeInactive ? { include_inactive: "true" } : {};
    const response = await axios.get<AIAssistantPublic[]>(`${API_BASE}/assistants`, { params });
    return response.data;
  },

  detail: async (id: string): Promise<AIAssistantPublic> => {
    const response = await axios.get<AIAssistantPublic>(`${API_BASE}/assistants/${id}`);
    return response.data;
  },

  create: async (data: AIAssistantCreate): Promise<AIAssistantPublic> => {
    const response = await axios.post<AIAssistantPublic>(`${API_BASE}/assistants`, data);
    return response.data;
  },

  update: async (id: string, data: AIAssistantUpdate): Promise<AIAssistantPublic> => {
    const response = await axios.put<AIAssistantPublic>(`${API_BASE}/assistants/${id}`, data);
    return response.data;
  },

  delete: async (id: string): Promise<void> => {
    await axios.delete(`${API_BASE}/assistants/${id}`);
  },
};

/**
 * Hook to fetch all AI assistants
 * @param includeInactive - Whether to include inactive assistants
 */
export const useAIAssistants = (
  includeInactive?: boolean,
  options?: Omit<UseQueryOptions<AIAssistantPublic[], Error>, "queryKey" | "queryFn">
) => {
  return useTanstackQuery<AIAssistantPublic[], Error>({
    queryKey: queryKeys.ai.assistants.list(includeInactive),
    queryFn: () => assistantApi.list(includeInactive),
    ...options,
  });
};

/**
 * Hook to fetch a single AI assistant by ID
 * @param id - Assistant ID
 */
export const useAIAssistant = (
  id: string,
  options?: Omit<UseQueryOptions<AIAssistantPublic, Error>, "queryKey" | "queryFn">
) => {
  return useTanstackQuery<AIAssistantPublic, Error>({
    queryKey: queryKeys.ai.assistants.detail(id),
    queryFn: () => assistantApi.detail(id),
    enabled: !!id,
    ...options,
  });
};

/**
 * Hook to create a new AI assistant
 */
export const useCreateAIAssistant = (
  options?: Omit<UseMutationOptions<AIAssistantPublic, Error, AIAssistantCreate>, "mutationFn">
) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: AIAssistantCreate) => assistantApi.create(data),
    onSuccess: (...args) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.ai.assistants.all });
      toast.success("AI assistant created successfully");
      options?.onSuccess?.(...args);
    },
    onError: (error, ...args) => {
      toast.error(`Error creating AI assistant: ${error.message}`);
      options?.onError?.(error, ...args);
    },
    ...options,
  });
};

/**
 * Hook to update an existing AI assistant
 */
export const useUpdateAIAssistant = (
  options?: Omit<
    UseMutationOptions<AIAssistantPublic, Error, { id: string; data: AIAssistantUpdate }>,
    "mutationFn"
  >
) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: AIAssistantUpdate }) =>
      assistantApi.update(id, data),
    onSuccess: (...args) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.ai.assistants.all });
      toast.success("AI assistant updated successfully");
      options?.onSuccess?.(...args);
    },
    onError: (error, ...args) => {
      toast.error(`Error updating AI assistant: ${error.message}`);
      options?.onError?.(error, ...args);
    },
    ...options,
  });
};

/**
 * Hook to delete an AI assistant
 */
export const useDeleteAIAssistant = (
  options?: Omit<UseMutationOptions<void, Error, string>, "mutationFn">
) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => assistantApi.delete(id),
    onSuccess: (...args) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.ai.assistants.all });
      toast.success("AI assistant deleted successfully");
      options?.onSuccess?.(...args);
    },
    onError: (error, ...args) => {
      toast.error(`Error deleting AI assistant: ${error.message}`);
      options?.onError?.(error, ...args);
    },
    ...options,
  });
};
