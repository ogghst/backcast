/**
 * AI Provider Configuration (API Keys) API Hooks
 *
 * Provides TanStack Query hooks for managing provider configurations.
 * Configs are key-value pairs, often used for API keys.
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
import type { AIProviderConfigPublic, AIProviderConfigCreate } from "../types";

const API_BASE = "/api/v1/ai/config";

const configApi = {
  list: async (providerId: string): Promise<AIProviderConfigPublic[]> => {
    const response = await axios.get<AIProviderConfigPublic[]>(`${API_BASE}/providers/${providerId}/configs`);
    return response.data;
  },

  set: async (
    providerId: string,
    data: AIProviderConfigCreate
  ): Promise<AIProviderConfigPublic> => {
    const response = await axios.post<AIProviderConfigPublic>(`${API_BASE}/providers/${providerId}/configs`, data);
    return response.data;
  },

  delete: async (providerId: string, key: string): Promise<void> => {
    await axios.delete(`${API_BASE}/providers/${providerId}/configs/${key}`);
  },
};

/**
 * Hook to fetch configs for a provider
 * @param providerId - Provider ID
 */
export const useAIProviderConfigs = (
  providerId: string,
  options?: Omit<UseQueryOptions<AIProviderConfigPublic[], Error>, "queryKey" | "queryFn">
) => {
  return useTanstackQuery<AIProviderConfigPublic[], Error>({
    queryKey: queryKeys.ai.providerConfigs.list(providerId),
    queryFn: () => configApi.list(providerId),
    enabled: !!providerId,
    ...options,
  });
};

/**
 * Hook to set a config value for a provider
 */
export const useSetAIProviderConfig = (
  options?: Omit<
    UseMutationOptions<
      AIProviderConfigPublic,
      Error,
      { providerId: string; data: AIProviderConfigCreate }
    >,
    "mutationFn"
  >
) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      providerId,
      data,
    }: {
      providerId: string;
      data: AIProviderConfigCreate;
    }) => configApi.set(providerId, data),
    onSuccess: (data, variables) => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.ai.providerConfigs.list(variables.providerId),
      });
      toast.success("Configuration updated successfully");
      options?.onSuccess?.(data, variables, undefined);
    },
    onError: (error, ...args) => {
      toast.error(`Error updating configuration: ${error.message}`);
      options?.onError?.(error, ...args);
    },
    ...options,
  });
};

/**
 * Hook to delete a config from a provider
 */
export const useDeleteAIProviderConfig = (
  options?: Omit<
    UseMutationOptions<void, Error, { providerId: string; key: string }>,
    "mutationFn"
  >
) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ providerId, key }: { providerId: string; key: string }) =>
      configApi.delete(providerId, key),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.ai.providerConfigs.list(variables.providerId),
      });
      toast.success("Configuration deleted successfully");
      options?.onSuccess?.(_, variables, undefined);
    },
    onError: (error, ...args) => {
      toast.error(`Error deleting configuration: ${error.message}`);
      options?.onError?.(error, ...args);
    },
    ...options,
  });
};
