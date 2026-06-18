/**
 * Agent Executions Hooks
 *
 * TanStack Query hooks for the background agent execution REST API:
 *   - GET  /api/v1/ai/chat/executions            -> paginated history
 *   - GET  /api/v1/ai/chat/executions/running-count
 *   - POST /api/v1/ai/chat/executions/{id}/stop
 *
 * Cache keys live under queryKeys.ai.chat.executions.*. The list auto-refetches
 * every 5s while mounted so newly started/finished executions appear without a
 * manual refetch (TanStack stops polling once the query is inactive).
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import axios from "axios";
import { toast } from "sonner";
import { queryKeys } from "@/api/queryKeys";

const API_BASE = "/api/v1/ai/chat";

export interface AgentExecutionContext {
  type: string | null;
  name: string | null;
  project_id: string | null;
  branch_id: string | null;
}

export interface AgentExecutionHistoryItem {
  id: string;
  name: string | null;
  status: string;
  execution_mode: string;
  run_in_background: boolean;
  started_at: string; // ISO datetime
  completed_at: string | null; // ISO datetime
  session_id: string;
  context: AgentExecutionContext;
  assistant_name: string | null;
  total_tokens: number;
  tool_calls_count: number;
}

export interface AgentExecutionListResponse {
  items: AgentExecutionHistoryItem[];
  total: number;
  has_more: boolean;
}

export interface RunningExecutionsCountResponse {
  count: number;
}

const listExecutions = async (
  status?: string,
  limit = 25,
  offset = 0,
): Promise<AgentExecutionListResponse> => {
  const params: Record<string, number | string> = { limit, offset };
  if (status && status !== "all") {
    params.status = status;
  }
  const response = await axios.get<AgentExecutionListResponse>(
    `${API_BASE}/executions`,
    { params },
  );
  return response.data;
};

const fetchRunningCount = async (): Promise<number> => {
  const response = await axios.get<RunningExecutionsCountResponse>(
    `${API_BASE}/executions/running-count`,
  );
  return response.data.count;
};

const stopExecution = async (executionId: string): Promise<void> => {
  await axios.post(`${API_BASE}/executions/${executionId}/stop`);
};

interface UseAgentExecutionsOptions {
  status?: string;
  limit?: number;
  offset?: number;
}

/**
 * Paginated list of agent executions. Polls every 5s while mounted so newly
 * started/finished rows appear without a manual refetch.
 */
export function useAgentExecutions({
  status,
  limit = 25,
  offset = 0,
}: UseAgentExecutionsOptions = {}) {
  return useQuery<AgentExecutionListResponse>({
    queryKey: queryKeys.ai.chat.executions.list(status),
    queryFn: () => listExecutions(status, limit, offset),
    // Poll unconditionally while mounted so newly started/finished executions
    // appear without a manual refetch. Aligns freshness with the menu badge
    // (useRunningExecutionsCount). TanStack stops polling once inactive.
    refetchInterval: 5000,
  });
}

/**
 * Count of currently-running executions. Polls every 5s — used for the menu badge.
 */
export function useRunningExecutionsCount() {
  return useQuery<number>({
    queryKey: queryKeys.ai.chat.executions.runningCount(),
    queryFn: fetchRunningCount,
    refetchInterval: 5000,
  });
}

/**
 * Stop a running execution. Invalidates the executions list and chat sessions on
 * success so the UI reflects the new terminal state. Reusable from both the
 * Agents History page and the in-chat Stop button.
 */
export function useStopExecution(
  options?: {
    onSuccess?: () => void;
    onError?: (error: Error) => void;
  },
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (executionId: string) => stopExecution(executionId),
    onSuccess: (...args) => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.ai.chat.executions.all,
      });
      queryClient.invalidateQueries({
        queryKey: queryKeys.ai.chat.sessions(),
      });
      options?.onSuccess?.();
      void args;
    },
    onError: (error: Error) => {
      toast.error(`Failed to stop agent: ${error.message}`);
      options?.onError?.(error);
    },
  });
}
