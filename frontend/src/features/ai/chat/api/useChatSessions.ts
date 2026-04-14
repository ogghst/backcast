/**
 * Chat Session API Hooks
 *
 * Provides TanStack Query hooks for AI chat session operations.
 * Uses the centralized query keys factory for cache management.
 */

import {
  useMutation,
  useQueryClient,
  type UseMutationOptions,
  useQuery as useTanstackQuery,
  type UseQueryOptions,
} from "@tanstack/react-query";
import { toast } from "sonner";
import axios from "axios";
import { queryKeys } from "@/api/queryKeys";
import type {
  AIConversationSessionPublic,
  AIConversationMessagePublic,
  AIConversationSessionPaginated,
} from "../../types";

// API base URL - axios is configured with auth interceptors in client.ts
const API_BASE = "/api/v1/ai/chat";

const sessionsApi = {
  list: async (contextType?: string): Promise<AIConversationSessionPublic[]> => {
    const params = contextType ? { context_type: contextType } : {};
    const response = await axios.get<AIConversationSessionPublic[]>(
      `${API_BASE}/sessions`,
      { params }
    );
    return response.data;
  },

  listPaginated: async (
    skip: number = 0,
    limit: number = 10
  ): Promise<AIConversationSessionPaginated> => {
    const response = await axios.get<AIConversationSessionPaginated>(
      `${API_BASE}/sessions/paginated`,
      { params: { skip, limit } }
    );
    return response.data;
  },

  getMessages: async (
    sessionId: string
  ): Promise<AIConversationMessagePublic[]> => {
    const response = await axios.get<AIConversationMessagePublic[]>(
      `${API_BASE}/sessions/${sessionId}/messages`
    );
    return response.data;
  },

  delete: async (sessionId: string): Promise<void> => {
    await axios.delete(`${API_BASE}/sessions/${sessionId}`);
  },
};

/**
 * Hook to fetch all chat sessions for the current user
 * @param options - Query options with optional contextType filter
 */
export const useChatSessions = (
  options?: Omit<
    UseQueryOptions<AIConversationSessionPublic[], Error>,
    "queryKey" | "queryFn"
  > & { contextType?: string }
) => {
  const { contextType, ...restOptions } = options || {};
  return useTanstackQuery<AIConversationSessionPublic[], Error>({
    queryKey: queryKeys.ai.chat.sessions(),
    queryFn: () => sessionsApi.list(contextType),
    ...restOptions,
  });
};

/**
 * Hook to fetch messages for a specific session
 * @param sessionId - The session ID to fetch messages for
 */
export const useChatMessages = (
  sessionId: string | undefined,
  options?: Omit<
    UseQueryOptions<AIConversationMessagePublic[], Error>,
    "queryKey" | "queryFn"
  >
) => {
  return useTanstackQuery<AIConversationMessagePublic[], Error>({
    queryKey: sessionId ? queryKeys.ai.chat.messages(sessionId) : ["ai", "chat", "messages", "empty"],
    queryFn: () => sessionsApi.getMessages(sessionId!),
    enabled: !!sessionId,
    ...options,
  });
};

/**
 * Hook to delete a chat session
 */
export const useDeleteSession = (
  options?: Omit<UseMutationOptions<void, Error, string>, "mutationFn">
) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (sessionId: string) => sessionsApi.delete(sessionId),
    onSuccess: (...args) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.ai.chat.sessions() });
      toast.success("Chat deleted successfully");
      options?.onSuccess?.(...args);
    },
    onError: (error, ...args) => {
      toast.error(`Error deleting chat: ${error.message}`);
      options?.onError?.(error, ...args);
    },
    ...options,
  });
};
