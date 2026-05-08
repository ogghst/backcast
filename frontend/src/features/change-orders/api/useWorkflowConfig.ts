/**
 * TanStack Query hooks for Change Order Workflow Configuration API.
 *
 * Provides hooks for fetching and mutating global and project-level
 * workflow configuration (impact levels, approval rules, SLA rules, weights).
 */
import {
  useQuery,
  useMutation,
  useQueryClient,
  type UseQueryOptions,
  type UseMutationOptions,
} from "@tanstack/react-query";
import { toast } from "sonner";
import { OpenAPI } from "@/api/generated/core/OpenAPI";
import { request as __request } from "@/api/generated/core/request";
import { queryKeys } from "@/api/queryKeys";

// ---------------------------------------------------------------------------
// Types matching backend WorkflowConfigResponse / WorkflowConfigUpdateRequest
// ---------------------------------------------------------------------------

export interface ImpactLevelConfig {
  level_name: string;
  level_order: number;
  threshold_amount: number;
  score_threshold_min: number;
  score_threshold_max: number;
  is_active: boolean;
}

export interface ApprovalRuleConfig {
  impact_level_name: string;
  required_authority_level: string;
  approver_role: string;
}

export interface SLARuleConfig {
  impact_level_name: string;
  business_days: number;
  escalation_trigger_pct: number | null;
}

export interface ImpactWeights {
  budget: number;
  schedule: number;
  revenue: number;
  evm: number;
}

export interface ScoreBoundaries {
  LOW: number;
  MEDIUM: number;
  HIGH: number;
  CRITICAL: number;
}

export interface WorkflowTransitionsConfig {
  transitions: Record<string, string[]>;
  lock_transitions: [string, string][];
  unlock_transitions: [string, string][];
  editable_statuses: string[];
}

export interface CustomFieldDefinition {
  name: string;
  type: "text" | "number" | "date" | "select";
  required: boolean;
  options: string[];
}

export interface WorkflowConfigResponse {
  id: string;
  config_id: string;
  project_id: string | null;
  is_active: boolean;
  version: number;
  created_by: string;
  updated_by: string | null;
  created_at: string;
  updated_at: string;
  impact_levels: ImpactLevelConfig[];
  approval_rules: ApprovalRuleConfig[];
  sla_rules: SLARuleConfig[];
  impact_weights: ImpactWeights;
  score_boundaries: ScoreBoundaries;
  workflow_transitions: WorkflowTransitionsConfig | null;
  custom_fields: CustomFieldDefinition[] | null;
  holiday_country_code: string | null;
}

export interface WorkflowConfigUpdateRequest {
  impact_levels: ImpactLevelConfig[];
  approval_rules: ApprovalRuleConfig[];
  sla_rules: SLARuleConfig[];
  impact_weights: ImpactWeights;
  score_boundaries: ScoreBoundaries;
  workflow_transitions: WorkflowTransitionsConfig | null;
  custom_fields?: CustomFieldDefinition[] | null;
  holiday_country_code?: string | null;
}

// ---------------------------------------------------------------------------
// Response transformer: the backend serialises some numeric fields as strings.
// Parse them back to numbers so the TypeScript types are accurate at runtime.
// ---------------------------------------------------------------------------

function transformConfigResponse(
  raw: WorkflowConfigResponse,
): WorkflowConfigResponse {
  return {
    ...raw,
    impact_weights: {
      budget: parseFloat(String(raw.impact_weights.budget)),
      schedule: parseFloat(String(raw.impact_weights.schedule)),
      revenue: parseFloat(String(raw.impact_weights.revenue)),
      evm: parseFloat(String(raw.impact_weights.evm)),
    },
    score_boundaries: {
      LOW: parseFloat(String(raw.score_boundaries.LOW)),
      MEDIUM: parseFloat(String(raw.score_boundaries.MEDIUM)),
      HIGH: parseFloat(String(raw.score_boundaries.HIGH)),
      CRITICAL: parseFloat(String(raw.score_boundaries.CRITICAL)),
    },
    impact_levels: raw.impact_levels.map((level) => ({
      ...level,
      threshold_amount: parseFloat(String(level.threshold_amount)),
      score_threshold_min: parseFloat(String(level.score_threshold_min)),
      score_threshold_max: parseFloat(String(level.score_threshold_max)),
    })),
  };
}

// ---------------------------------------------------------------------------
// Helper: build request config object
// ---------------------------------------------------------------------------

function getConfig(url: string) {
  return {
    method: "GET" as const,
    url,
  };
}

function putConfig(url: string, body: WorkflowConfigUpdateRequest) {
  return {
    method: "PUT" as const,
    url,
    body,
  };
}

function deleteConfig(url: string) {
  return {
    method: "DELETE" as const,
    url,
  };
}

// ---------------------------------------------------------------------------
// Query hooks
// ---------------------------------------------------------------------------

/**
 * Fetch the global workflow configuration.
 */
export function useGlobalConfig(
  options?: Omit<
    UseQueryOptions<WorkflowConfigResponse, Error>,
    "queryKey" | "queryFn"
  >,
) {
  return useQuery<WorkflowConfigResponse, Error>({
    queryKey: queryKeys.changeOrderConfig.global,
    queryFn: async () => {
      const raw = await __request(
        OpenAPI,
        getConfig("/api/v1/change-order-config/global"),
      );
      return transformConfigResponse(raw as WorkflowConfigResponse);
    },
    ...options,
  });
}

/**
 * Fetch project-level workflow configuration.
 * Returns 404 when the project uses global defaults.
 */
export function useProjectConfig(
  projectId: string | undefined,
  options?: Omit<
    UseQueryOptions<WorkflowConfigResponse, Error>,
    "queryKey" | "queryFn"
  >,
) {
  return useQuery<WorkflowConfigResponse, Error>({
    queryKey: queryKeys.changeOrderConfig.project(projectId!),
    queryFn: async () => {
      const raw = await __request(
        OpenAPI,
        getConfig(`/api/v1/change-order-config/projects/${projectId}`),
      );
      return transformConfigResponse(raw as WorkflowConfigResponse);
    },
    enabled: !!projectId && (options?.enabled ?? true),
    ...options,
  });
}

// ---------------------------------------------------------------------------
// Mutation hooks
// ---------------------------------------------------------------------------

/**
 * Update the global workflow configuration.
 * Invalidates all config queries on success.
 */
export function useUpdateGlobalConfig(
  mutationOptions?: Omit<
    UseMutationOptions<
      WorkflowConfigResponse,
      Error,
      WorkflowConfigUpdateRequest
    >,
    "mutationFn"
  >,
) {
  const queryClient = useQueryClient();

  return useMutation<
    WorkflowConfigResponse,
    Error,
    WorkflowConfigUpdateRequest
  >({
    mutationFn: (data) =>
      __request(
        OpenAPI,
        putConfig("/api/v1/change-order-config/global", data),
      ),
    onSuccess: async (data, ...args) => {
      await queryClient.invalidateQueries({
        queryKey: queryKeys.changeOrderConfig.all,
      });
      toast.success("Global workflow configuration updated");
      mutationOptions?.onSuccess?.(data, ...args);
    },
    onError: (error: Error & { status?: number }, ...args) => {
      if ((error as unknown as { status: number }).status === 409) {
        toast.error(
          "Configuration was modified by another user. Please refresh and try again.",
        );
      } else {
        toast.error(
          `Error updating global configuration: ${error.message}`,
        );
      }
      mutationOptions?.onError?.(error, ...args);
    },
  });
}

/**
 * Update project-level workflow configuration.
 */
export function useUpdateProjectConfig(
  projectId: string,
  mutationOptions?: Omit<
    UseMutationOptions<
      WorkflowConfigResponse,
      Error,
      WorkflowConfigUpdateRequest
    >,
    "mutationFn"
  >,
) {
  const queryClient = useQueryClient();

  return useMutation<
    WorkflowConfigResponse,
    Error,
    WorkflowConfigUpdateRequest
  >({
    mutationFn: (data) =>
      __request(
        OpenAPI,
        putConfig(
          `/api/v1/change-order-config/projects/${projectId}`,
          data,
        ),
      ),
    onSuccess: async (data, ...args) => {
      await queryClient.invalidateQueries({
        queryKey: queryKeys.changeOrderConfig.all,
      });
      toast.success("Project workflow configuration updated");
      mutationOptions?.onSuccess?.(data, ...args);
    },
    onError: (error: Error, ...args) => {
      if ((error as unknown as { status: number }).status === 409) {
        toast.error(
          "Configuration was modified by another user. Please refresh and try again.",
        );
      } else {
        toast.error(
          `Error updating project configuration: ${error.message}`,
        );
      }
      mutationOptions?.onError?.(error, ...args);
    },
  });
}

/**
 * Reset project-level workflow configuration back to global defaults.
 * Calls DELETE /projects/{projectId}.
 */
export function useResetProjectConfig(
  projectId: string,
  mutationOptions?: Omit<
    UseMutationOptions<void, Error, void>,
    "mutationFn"
  >,
) {
  const queryClient = useQueryClient();

  return useMutation<void, Error, void>({
    mutationFn: () =>
      __request(
        OpenAPI,
        deleteConfig(`/api/v1/change-order-config/projects/${projectId}`),
      ),
    onSuccess: async (...args) => {
      await queryClient.invalidateQueries({
        queryKey: queryKeys.changeOrderConfig.all,
      });
      toast.success("Project configuration reset to global defaults");
      mutationOptions?.onSuccess?.(...args);
    },
    onError: (error: Error, ...args) => {
      toast.error(
        `Error resetting project configuration: ${error.message}`,
      );
      mutationOptions?.onError?.(error, ...args);
    },
  });
}
