/**
 * Agent Schedules API Hooks
 *
 * TanStack Query hooks for agent schedule CRUD + toggle/trigger operations:
 *   - GET    /api/v1/ai/agent-schedules            -> list (owner-scoped)
 *   - POST   /api/v1/ai/agent-schedules            -> create
 *   - GET    /api/v1/ai/agent-schedules/{id}       -> detail
 *   - PUT    /api/v1/ai/agent-schedules/{id}       -> update
 *   - DELETE /api/v1/ai/agent-schedules/{id}       -> delete (204)
 *   - POST   /api/v1/ai/agent-schedules/{id}/toggle  -> flip is_active
 *   - POST   /api/v1/ai/agent-schedules/{id}/trigger -> "Run now"
 *
 * Cache keys live under queryKeys.ai.agentSchedules.*. List + detail keys
 * are invalidated on every mutation so the table reflects the latest
 * next_run_at / last_run_at computed by the backend.
 */

import axios from "axios";
import {
  useMutation,
  useQueryClient,
  useQuery as useTanstackQuery,
  type UseMutationOptions,
  type UseQueryOptions,
} from "@tanstack/react-query";
import { toast } from "sonner";
import { queryKeys } from "@/api/queryKeys";
import type {
  AgentScheduleCreate,
  AgentScheduleRead,
  AgentScheduleTriggerResponse,
  AgentScheduleUpdate,
} from "@/api/generated";

const API_BASE = "/api/v1/ai/agent-schedules";

export interface AgentScheduleListFilters {
  isActive?: boolean;
  assistantConfigId?: string;
  ownerUserId?: string;
}

const agentScheduleApi = {
  list: async (filters?: AgentScheduleListFilters): Promise<AgentScheduleRead[]> => {
    const params: Record<string, string> = {};
    if (filters?.isActive !== undefined) params.is_active = String(filters.isActive);
    if (filters?.assistantConfigId) params.assistant_config_id = filters.assistantConfigId;
    if (filters?.ownerUserId) params.owner_user_id = filters.ownerUserId;
    const response = await axios.get<AgentScheduleRead[]>(API_BASE, { params });
    return response.data;
  },

  detail: async (id: string): Promise<AgentScheduleRead> => {
    const response = await axios.get<AgentScheduleRead>(`${API_BASE}/${id}`);
    return response.data;
  },

  create: async (data: AgentScheduleCreate): Promise<AgentScheduleRead> => {
    const response = await axios.post<AgentScheduleRead>(API_BASE, data);
    return response.data;
  },

  update: async (id: string, data: AgentScheduleUpdate): Promise<AgentScheduleRead> => {
    const response = await axios.put<AgentScheduleRead>(`${API_BASE}/${id}`, data);
    return response.data;
  },

  delete: async (id: string): Promise<void> => {
    await axios.delete(`${API_BASE}/${id}`);
  },

  toggle: async (id: string): Promise<AgentScheduleRead> => {
    const response = await axios.post<AgentScheduleRead>(`${API_BASE}/${id}/toggle`);
    return response.data;
  },

  trigger: async (id: string): Promise<AgentScheduleTriggerResponse> => {
    const response = await axios.post<AgentScheduleTriggerResponse>(`${API_BASE}/${id}/trigger`);
    return response.data;
  },
};

/**
 * List agent schedules (owner-scoped by the backend). Pass filters to narrow
 * by active state, assistant, or owner.
 */
export const useAgentSchedules = (
  filters?: AgentScheduleListFilters,
  options?: Omit<UseQueryOptions<AgentScheduleRead[], Error>, "queryKey" | "queryFn">
) => {
  return useTanstackQuery<AgentScheduleRead[], Error>({
    queryKey: queryKeys.ai.agentSchedules.list(filters),
    queryFn: () => agentScheduleApi.list(filters),
    ...options,
  });
};

/**
 * Fetch a single agent schedule by ID.
 */
export const useAgentSchedule = (
  id: string,
  options?: Omit<UseQueryOptions<AgentScheduleRead, Error>, "queryKey" | "queryFn">
) => {
  return useTanstackQuery<AgentScheduleRead, Error>({
    queryKey: queryKeys.ai.agentSchedules.detail(id),
    queryFn: () => agentScheduleApi.detail(id),
    enabled: !!id,
    ...options,
  });
};

/** Invalidate list + detail caches so the table reflects mutations. */
/** Extract a human message from an axios error response (409 conflict, 422 validation, etc). */
function describeError(error: Error): string {
  const err = error as Error & { response?: { status?: number; data?: { detail?: unknown } } };
  // 409 overlap: a run for this schedule is already active — actionable guidance.
  if (err.response?.status === 409) {
    return "An agent run is already active for this schedule. Wait for it to complete or stop it from Agents History.";
  }
  const detail = err.response?.data?.detail;
  if (Array.isArray(detail)) {
    // FastAPI 422 validation error: list of { msg }.
    return detail.map((d) => (d as { msg?: string }).msg).filter(Boolean).join("; ");
  }
  if (typeof detail === "string") return detail;
  return error.message;
}

/**
 * Create an agent schedule. On 422 the server-side cron/timezone validation
 * errors are surfaced in the toast.
 */
export const useCreateAgentSchedule = (
  options?: Omit<UseMutationOptions<AgentScheduleRead, Error, AgentScheduleCreate>, "mutationFn">
) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: AgentScheduleCreate) => agentScheduleApi.create(data),
    onSuccess: (...args) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.ai.agentSchedules.all });
      toast.success("Schedule created successfully");
      options?.onSuccess?.(...args);
    },
    onError: (error, ...args) => {
      toast.error(`Error creating schedule: ${describeError(error)}`);
      options?.onError?.(error, ...args);
    },
  });
};

/**
 * Update an agent schedule (re-validates cron server-side, recomputes next_run_at).
 */
export const useUpdateAgentSchedule = (
  options?: Omit<
    UseMutationOptions<AgentScheduleRead, Error, { id: string; data: AgentScheduleUpdate }>,
    "mutationFn"
  >
) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: AgentScheduleUpdate }) =>
      agentScheduleApi.update(id, data),
    onSuccess: (...args) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.ai.agentSchedules.all });
      toast.success("Schedule updated successfully");
      options?.onSuccess?.(...args);
    },
    onError: (error, ...args) => {
      toast.error(`Error updating schedule: ${describeError(error)}`);
      options?.onError?.(error, ...args);
    },
  });
};

/**
 * Delete an agent schedule (history/sessions are preserved by the backend).
 */
export const useDeleteAgentSchedule = (
  options?: Omit<UseMutationOptions<void, Error, string>, "mutationFn">
) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => agentScheduleApi.delete(id),
    onSuccess: (...args) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.ai.agentSchedules.all });
      toast.success("Schedule deleted successfully");
      options?.onSuccess?.(...args);
    },
    onError: (error, ...args) => {
      toast.error(`Error deleting schedule: ${describeError(error)}`);
      options?.onError?.(error, ...args);
    },
  });
};

/**
 * Flip a schedule's is_active flag (backend recomputes next_run_at).
 */
export const useToggleAgentSchedule = (
  options?: Omit<UseMutationOptions<AgentScheduleRead, Error, string>, "mutationFn">
) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => agentScheduleApi.toggle(id),
    onSuccess: (...args) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.ai.agentSchedules.all });
      options?.onSuccess?.(...args);
    },
    onError: (error, ...args) => {
      toast.error(`Error toggling schedule: ${describeError(error)}`);
      options?.onError?.(error, ...args);
    },
  });
};

/**
 * "Run now" — fires an immediate execution. Returns 409 if a run is already
 * active for the schedule (the overlap guard).
 */
export const useTriggerAgentSchedule = (
  options?: Omit<UseMutationOptions<AgentScheduleTriggerResponse, Error, string>, "mutationFn">
) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => agentScheduleApi.trigger(id),
    onSuccess: (...args) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.ai.agentSchedules.all });
      queryClient.invalidateQueries({ queryKey: queryKeys.ai.chat.executions.all });
      options?.onSuccess?.(...args);
    },
    onError: (error, ...args) => {
      toast.error(`Error triggering schedule: ${describeError(error)}`);
      options?.onError?.(error, ...args);
    },
  });
};
