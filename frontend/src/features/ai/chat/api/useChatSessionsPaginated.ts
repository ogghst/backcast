/**
 * Paginated Chat Sessions Hook
 *
 * Provides TanStack Query hook for paginated AI chat session operations.
 * Uses the centralized query keys factory for cache management.
 */

import { useCallback, useState } from "react";
import { useQuery as useTanstackQuery } from "@tanstack/react-query";
import { queryKeys } from "@/api/queryKeys";
import type { AIConversationSessionPaginated } from "../../types";

// Reuse the API function from useChatSessions
import axios from "axios";

const API_BASE = "/api/v1/ai/chat";

const listSessionsPaginated = async (
  skip: number = 0,
  limit: number = 10
): Promise<AIConversationSessionPaginated> => {
  const response = await axios.get<AIConversationSessionPaginated>(
    `${API_BASE}/sessions/paginated`,
    { params: { skip, limit } }
  );
  return response.data;
};

interface UseChatSessionsPaginatedOptions {
  initialSkip?: number;
  limit?: number;
}

export function useChatSessionsPaginated(
  options: UseChatSessionsPaginatedOptions = {}
) {
  const { initialSkip = 0, limit = 10 } = options;
  const [skip, setSkip] = useState(initialSkip);

  const query = useTanstackQuery<AIConversationSessionPaginated>({
    queryKey: queryKeys.ai.chat.sessionsPaginated(skip, limit),
    queryFn: () => listSessionsPaginated(skip, limit),
  });

  const loadMore = useCallback(() => {
    setSkip((prev) => prev + limit);
  }, [limit]);

  const reset = useCallback(() => {
    setSkip(0);
  }, []);

  return {
    ...query,
    loadMore,
    reset,
    hasMore: query.data?.has_more ?? false,
    totalCount: query.data?.total_count ?? 0,
  };
}
