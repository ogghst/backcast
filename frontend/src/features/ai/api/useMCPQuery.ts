/**
 * MCP Server API Hooks
 *
 * TanStack Query hooks for MCP Server CRUD and tool discovery operations.
 */

import {
  useMutation,
  useQueryClient,
  useQuery as useTanstackQuery,
  type UseQueryOptions,
  type UseMutationOptions,
} from "@tanstack/react-query";
import { toast } from "sonner";
import axios from "axios";
import { queryKeys } from "@/api/queryKeys";
import type {
  MCPServerPublic,
  MCPServerCreate,
  MCPServerUpdate,
  MCPToolInfo,
} from "../types";

const API_BASE = "/api/v1/mcp/servers";

const mcpServerApi = {
  list: async (includeInactive?: boolean): Promise<MCPServerPublic[]> => {
    const params = includeInactive ? { include_inactive: "true" } : {};
    const response = await axios.get<MCPServerPublic[]>(API_BASE, { params });
    return response.data;
  },

  create: async (data: MCPServerCreate): Promise<MCPServerPublic> => {
    const response = await axios.post<MCPServerPublic>(API_BASE, data);
    return response.data;
  },

  update: async (id: string, data: MCPServerUpdate): Promise<MCPServerPublic> => {
    const response = await axios.put<MCPServerPublic>(`${API_BASE}/${id}`, data);
    return response.data;
  },

  delete: async (id: string): Promise<void> => {
    await axios.delete(`${API_BASE}/${id}`);
  },

  testConnection: async (id: string): Promise<MCPToolInfo[]> => {
    const response = await axios.post<MCPToolInfo[]>(`${API_BASE}/${id}/test`);
    return response.data;
  },

  getCachedTools: async (id: string): Promise<MCPToolInfo[]> => {
    const response = await axios.get<MCPToolInfo[]>(`${API_BASE}/${id}/tools`);
    return response.data;
  },
};

/**
 * Hook to fetch MCP servers
 */
export const useMCPServers = (
  includeInactive?: boolean,
  options?: Omit<UseQueryOptions<MCPServerPublic[], Error>, "queryKey" | "queryFn">
) => {
  return useTanstackQuery<MCPServerPublic[], Error>({
    queryKey: queryKeys.ai.mcpServers.list(includeInactive),
    queryFn: () => mcpServerApi.list(includeInactive),
    ...options,
  });
};

/**
 * Hook to create an MCP server
 */
export const useCreateMCPServer = (
  options?: Omit<UseMutationOptions<MCPServerPublic, Error, MCPServerCreate>, "mutationFn">
) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: MCPServerCreate) => mcpServerApi.create(data),
    onSuccess: (...args) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.ai.mcpServers.all });
      queryClient.invalidateQueries({ queryKey: queryKeys.ai.tools.lists() });
      toast.success("MCP server created successfully");
      options?.onSuccess?.(...args);
    },
    onError: (error, ...args) => {
      toast.error(`Error creating MCP server: ${error.message}`);
      options?.onError?.(error, ...args);
    },
    ...options,
  });
};

/**
 * Hook to update an MCP server
 */
export const useUpdateMCPServer = (
  options?: Omit<
    UseMutationOptions<MCPServerPublic, Error, { id: string; data: MCPServerUpdate }>,
    "mutationFn"
  >
) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: MCPServerUpdate }) =>
      mcpServerApi.update(id, data),
    onSuccess: (...args) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.ai.mcpServers.all });
      queryClient.invalidateQueries({ queryKey: queryKeys.ai.tools.lists() });
      toast.success("MCP server updated successfully");
      options?.onSuccess?.(...args);
    },
    onError: (error, ...args) => {
      toast.error(`Error updating MCP server: ${error.message}`);
      options?.onError?.(error, ...args);
    },
    ...options,
  });
};

/**
 * Hook to delete an MCP server
 */
export const useDeleteMCPServer = (
  options?: Omit<UseMutationOptions<void, Error, string>, "mutationFn">
) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => mcpServerApi.delete(id),
    onSuccess: (...args) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.ai.mcpServers.all });
      queryClient.invalidateQueries({ queryKey: queryKeys.ai.tools.lists() });
      toast.success("MCP server deleted successfully");
      options?.onSuccess?.(...args);
    },
    onError: (error, ...args) => {
      toast.error(`Error deleting MCP server: ${error.message}`);
      options?.onError?.(error, ...args);
    },
    ...options,
  });
};

/**
 * Hook to test MCP server connection and discover tools
 */
export const useTestMCPServer = (
  options?: Omit<UseMutationOptions<MCPToolInfo[], Error, string>, "mutationFn">
) => {
  return useMutation({
    mutationFn: (id: string) => mcpServerApi.testConnection(id),
    onSuccess: (...args) => {
      toast.success("Connection test successful");
      options?.onSuccess?.(...args);
    },
    onError: (error, ...args) => {
      toast.error(`Connection test failed: ${error.message}`);
      options?.onError?.(error, ...args);
    },
    ...options,
  });
};

/**
 * Hook to get cached tools for an MCP server
 */
export const useMCPServerTools = (
  serverId: string,
  options?: Omit<UseQueryOptions<MCPToolInfo[], Error>, "queryKey" | "queryFn">
) => {
  return useTanstackQuery<MCPToolInfo[], Error>({
    queryKey: queryKeys.ai.mcpServers.tools(serverId),
    queryFn: () => mcpServerApi.getCachedTools(serverId),
    enabled: !!serverId,
    ...options,
  });
};
