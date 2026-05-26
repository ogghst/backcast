/**
 * Work Package API hooks - TanStack Query integration.
 *
 * Work packages track cost and schedule impacts of external events
 * on a project. They are versionable but NOT branchable (costs are global facts).
 * Each package can optionally break down costs to specific WBEs/CostElements.
 */

import {
  useMutation,
  useQueryClient,
  useQuery,
  type UseQueryOptions,
  type UseMutationOptions,
} from "@tanstack/react-query";
import { useTimeMachineParams } from "@/contexts/TimeMachineContext";
import { toast } from "sonner";
import { OpenAPI } from "@/api/generated/core/OpenAPI";
import { request as __request } from "@/api/generated/core/request";
import { PackageTypesService } from "@/api/generated/services/PackageTypesService";
import type { PaginatedResponse } from "@/types/api";
import { queryKeys } from "@/api/queryKeys";

// ---------------------------------------------------------------------------
// Types -- inline until generated client is available
// ---------------------------------------------------------------------------

export interface QualityCostAllocation {
  cost_element_id: string;
  amount: number;
  description?: string;
}

export interface QualityCostAllocationRead {
  cost_registration_id: string;
  cost_element_id: string;
  amount: number;
  description?: string;
  cost_element_name?: string;
  wbe_code?: string;
  wbe_id?: string;
}

export type PackageType = string;

export const COQ_CATEGORY_OPTIONS = [
  { label: "Prevention", value: "prevention" },
  { label: "Appraisal", value: "appraisal" },
  { label: "Internal Failure", value: "internal_failure" },
  { label: "External Failure", value: "external_failure" },
] as const;

export interface PackageTypeOption {
  label: string;
  value: string;
  color: string;
  is_quality: boolean;
}

/**
 * Hook to fetch package types from the API.
 * Returns normalized options suitable for Select/Segmented components.
 */
export const usePackageTypes = () => {
  return useQuery<PackageTypeOption[]>({
    queryKey: queryKeys.packageTypes.list,
    queryFn: async () => {
      const res = await PackageTypesService.getPackageTypes(1, 10000);
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const items = Array.isArray(res) ? res : (res as any)?.items || [];
      return items.map(
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (pt: any) => ({
          label: pt.name,
          value: pt.code,
          color: pt.color || "blue",
          is_quality: pt.is_quality || false,
        }),
      );
    },
    staleTime: 5 * 60 * 1000, // 5 minutes — package types change rarely
  });
};

export interface WorkPackageRead {
  id: string;
  work_package_id: string;
  project_id: string;
  name: string;
  package_type: PackageType;
  description: string | null;
  status: "open" | "closed";
  external_event_id: string | null;
  event_date: string | null;
  event_date_formatted: { iso: string | null; formatted: string };
  coq_category: string | null;
  cost_impact: string;
  actual_cost: number | null;
  schedule_impact_days: number | null;
  created_by: string;
}

export interface WorkPackageCreate {
  work_package_id?: string;
  project_id: string;
  name: string;
  package_type: PackageType;
  description?: string | null;
  status?: "open" | "closed";
  external_event_id?: string | null;
  event_date?: string | null;
  coq_category?: string | null;
  cost_impact: number;
  schedule_impact_days?: number | null;
  control_date?: string | null;
  cost_allocations?: QualityCostAllocation[] | null;
}

export interface WorkPackageUpdate {
  name?: string | null;
  package_type?: PackageType | null;
  project_id?: string | null;
  description?: string | null;
  status?: "open" | "closed" | null;
  external_event_id?: string | null;
  event_date?: string | null;
  coq_category?: string | null;
  cost_impact?: number | null;
  schedule_impact_days?: number | null;
  control_date?: string | null;
  cost_allocations?: QualityCostAllocation[] | null;
}

export interface WorkPackageSummary {
  total_cost: string;
  conformance_cost: string;
  nonconformance_cost: string;
  prevention_cost: string;
  appraisal_cost: string;
  internal_failure_cost: string;
  external_failure_cost: string;
  total_schedule_days: number;
  impact_count: number;
  coq_ratio: string | null;
}

export interface COQMetrics {
  total_coq: number;
  cpq: number;
  cpq_percentage: number;
  cpiq: number | null;
  qpi: number | null;
  qpi_rating: string | null;
  total_ac: number;
  coq_ratio: number | null;
}

export interface COQTrendPoint {
  date: string;
  // Planned costs (from work package cost_impact)
  planned_prevention: string;
  planned_appraisal: string;
  planned_internal_failure: string;
  planned_external_failure: string;
  total_planned: string;
  // Actual costs (from cost registrations)
  prevention: string;
  appraisal: string;
  internal_failure: string;
  external_failure: string;
  total_coq: string;
  cpq: string;
}

export interface COQTrendResponse {
  granularity: "week" | "month";
  points: COQTrendPoint[];
  start_date: string;
  end_date: string;
  total_points: number;
}

// ---------------------------------------------------------------------------
// List hook
// ---------------------------------------------------------------------------

interface WorkPackageListParams {
  project_id: string;
  coq_category?: string;
  package_type?: string;
  status?: string;
  page?: number;
  perPage?: number;
  asOf?: string;
  queryOptions?: Omit<
    UseQueryOptions<PaginatedResponse<WorkPackageRead>>,
    "queryKey" | "queryFn"
  >;
}

/**
 * Hook to fetch work packages for a project with pagination.
 */
export const useWorkPackages = (params: WorkPackageListParams) => {
  const { asOf: tmAsOf, branch, mode } = useTimeMachineParams();

  return useQuery<PaginatedResponse<WorkPackageRead>>({
    queryKey: queryKeys.workPackages.list(params.project_id, {
      coq_category: params.coq_category,
      package_type: params.package_type,
      status: params.status,
      page: params.page,
      perPage: params.perPage,
      asOf: params.asOf || tmAsOf,
      branch,
      mode,
    }),
    queryFn: async () => {
      const {
        project_id,
        coq_category,
        package_type,
        status,
        page = 1,
        perPage = 20,
      } = params;

      const result = await __request(OpenAPI, {
        method: "GET",
        url: "/api/v1/work-packages",
        query: {
          project_id,
          page,
          per_page: perPage,
          coq_category: coq_category || undefined,
          package_type: package_type || undefined,
          status: status || undefined,
          as_of: params.asOf || tmAsOf || undefined,
          branch,
          mode,
        },
        errors: { 422: "Validation Error" },
      });

      if (Array.isArray(result)) {
        return {
          items: result,
          total: result.length,
          page: 1,
          per_page: result.length,
        };
      }
      return result as unknown as PaginatedResponse<WorkPackageRead>;
    },
    enabled: !!params.project_id,
    ...params.queryOptions,
  });
};

// ---------------------------------------------------------------------------
// Detail hook
// ---------------------------------------------------------------------------

/**
 * Hook to get a single work package by root ID.
 * Supports time-travel queries via asOf parameter.
 */
export const useWorkPackage = (
  workPackageId: string,
  asOf?: string,
) => {
  const { asOf: tmAsOf } = useTimeMachineParams();

  return useQuery<WorkPackageRead>({
    queryKey: queryKeys.workPackages.detail(workPackageId, {
      asOf: asOf || tmAsOf,
    }),
    queryFn: async () => {
      return await __request(OpenAPI, {
        method: "GET",
        url: "/api/v1/work-packages/{work_package_id}",
        path: { work_package_id: workPackageId },
        query: { as_of: asOf || tmAsOf || undefined },
        errors: { 422: "Validation Error" },
      });
    },
    enabled: !!workPackageId,
  });
};

// ---------------------------------------------------------------------------
// History hook
// ---------------------------------------------------------------------------

/**
 * Hook to get full version history for a work package.
 */
export const useWorkPackageHistory = (workPackageId: string) => {
  return useQuery<WorkPackageRead[]>({
    queryKey: queryKeys.workPackages.history(workPackageId),
    queryFn: async () => {
      return await __request(OpenAPI, {
        method: "GET",
        url: "/api/v1/work-packages/{work_package_id}/history",
        path: { work_package_id: workPackageId },
        errors: { 422: "Validation Error" },
      });
    },
    enabled: !!workPackageId,
  });
};

// ---------------------------------------------------------------------------
// Summary hook
// ---------------------------------------------------------------------------

/**
 * Hook to get aggregated COQ summary for a project.
 */
export const useWorkPackageSummary = (projectId: string) => {
  const { asOf, branch, mode } = useTimeMachineParams();

  return useQuery<WorkPackageSummary>({
    queryKey: queryKeys.workPackages.summary(projectId),
    queryFn: async () => {
      return await __request(OpenAPI, {
        method: "GET",
        url: "/api/v1/work-packages/project/{project_id}/summary",
        path: { project_id: projectId },
        query: {
          as_of: asOf || undefined,
          branch,
          mode,
        },
        errors: { 422: "Validation Error" },
      });
    },
    enabled: !!projectId,
  });
};

// ---------------------------------------------------------------------------
// Allocations hook
// ---------------------------------------------------------------------------

/**
 * Hook to get cost allocation entries for a work package.
 */
export const useWorkPackageAllocations = (workPackageId: string) => {
  return useQuery<QualityCostAllocationRead[]>({
    queryKey: queryKeys.workPackages.allocations(workPackageId),
    queryFn: async () => {
      return await __request(OpenAPI, {
        method: "GET",
        url: "/api/v1/work-packages/{work_package_id}/allocations",
        path: { work_package_id: workPackageId },
        errors: { 422: "Validation Error" },
      });
    },
    enabled: !!workPackageId,
  });
};

// ---------------------------------------------------------------------------
// COQ Metrics hook
// ---------------------------------------------------------------------------

/**
 * Hook to get COQ metrics (CPQ, CPIq, QPI) for a project.
 */
export const useCOQMetrics = (projectId: string) => {
  return useQuery<COQMetrics>({
    queryKey: queryKeys.workPackages.coqMetrics(projectId),
    queryFn: async () => {
      return await __request(OpenAPI, {
        method: "GET",
        url: "/api/v1/work-packages/project/{project_id}/coq-metrics",
        path: { project_id: projectId },
        errors: { 422: "Validation Error" },
      });
    },
    enabled: !!projectId,
  });
};

// ---------------------------------------------------------------------------
// COQ Trend hook
// ---------------------------------------------------------------------------

/**
 * Hook to get COQ trend data over time for a project.
 */
export const useCOQTrend = (
  projectId: string,
  granularity: "week" | "month" = "month",
) => {
  const { asOf } = useTimeMachineParams();

  return useQuery<COQTrendResponse>({
    queryKey: queryKeys.workPackages.coqTrend(projectId, granularity),
    queryFn: async () => {
      return await __request(OpenAPI, {
        method: "GET",
        url: "/api/v1/work-packages/project/{project_id}/coq-trend",
        path: { project_id: projectId },
        query: {
          granularity,
          as_of: asOf || undefined,
        },
        errors: { 422: "Validation Error" },
      });
    },
    enabled: !!projectId,
  });
};

// ---------------------------------------------------------------------------
// Create mutation
// ---------------------------------------------------------------------------

/**
 * Hook to create a new work package.
 *
 * Automatically invalidates work-packages queries on success.
 */
export const useCreateWorkPackage = (
  mutationOptions?: Omit<
    UseMutationOptions<
      WorkPackageRead,
      Error,
      WorkPackageCreate
    >,
    "mutationFn"
  >,
) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: WorkPackageCreate) => {
      return __request(OpenAPI, {
        method: "POST",
        url: "/api/v1/work-packages",
        body: data,
        mediaType: "application/json",
        errors: { 422: "Validation Error" },
      });
    },
    onSuccess: (...args) => {
      const created = args[0] as WorkPackageRead;
      queryClient.invalidateQueries({
        queryKey: queryKeys.workPackages.all,
      });
      queryClient.invalidateQueries({
        queryKey: queryKeys.workPackages.summary(created.project_id),
      });

      toast.success("Work package created successfully");
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (mutationOptions as any)?.onSuccess?.(...args);
    },
    onError: (...args) => {
      toast.error(`Error creating work package: ${(args[0] as Error).message}`);
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (mutationOptions as any)?.onError?.(...args);
    },
  });
};

// ---------------------------------------------------------------------------
// Update mutation (with optimistic update)
// ---------------------------------------------------------------------------

/**
 * Hook to update an existing work package.
 *
 * Performs optimistic update with rollback on error.
 */
export const useUpdateWorkPackage = (
  mutationOptions?: Omit<
    UseMutationOptions<
      WorkPackageRead,
      Error,
      { id: string; data: WorkPackageUpdate },
      { previousPackage?: WorkPackageRead }
    >,
    "mutationFn"
  >,
) => {
  const { asOf } = useTimeMachineParams();
  const queryClient = useQueryClient();

  return useMutation<
    WorkPackageRead,
    Error,
    { id: string; data: WorkPackageUpdate },
    { previousPackage?: WorkPackageRead }
  >({
    mutationFn: ({ id, data }) => {
      return __request(OpenAPI, {
        method: "PUT",
        url: "/api/v1/work-packages/{work_package_id}",
        path: { work_package_id: id },
        body: data,
        mediaType: "application/json",
        errors: { 422: "Validation Error" },
      });
    },
    onMutate: async ({ id, data }) => {
      await queryClient.cancelQueries({
        queryKey: queryKeys.workPackages.detail(id, { asOf }),
      });
      await queryClient.cancelQueries({
        queryKey: queryKeys.workPackages.lists(),
      });

      // Snapshot previous value
      const previousPackage = queryClient.getQueryData<WorkPackageRead>(
        queryKeys.workPackages.detail(id, { asOf }),
      );

      // Optimistically update detail cache
      if (previousPackage) {
        queryClient.setQueryData(
          queryKeys.workPackages.detail(id, { asOf }),
          (old: WorkPackageRead) => ({ ...old, ...data }),
        );
      }

      return { previousPackage };
    },
    onSuccess: (...args) => {
      const updated = args[0] as WorkPackageRead;
      queryClient.invalidateQueries({
        queryKey: queryKeys.workPackages.all,
      });
      queryClient.invalidateQueries({
        queryKey: queryKeys.workPackages.summary(updated.project_id),
      });

      toast.success("Work package updated successfully");
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (mutationOptions as any)?.onSuccess?.(...args);
    },
    onError: (...args) => {
      const error = args[0] as Error;
      const variables = args[1] as { id: string };
      const context = args[2] as { previousPackage?: WorkPackageRead } | undefined;
      // Rollback optimistic update
      if (context?.previousPackage) {
        queryClient.setQueryData(
          queryKeys.workPackages.detail(variables.id, { asOf }),
          context.previousPackage,
        );
      }
      toast.error(`Error updating work package: ${error.message}`);
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (mutationOptions as any)?.onError?.(...args);
    },
  });
};

// ---------------------------------------------------------------------------
// Delete mutation
// ---------------------------------------------------------------------------

/**
 * Hook to soft-delete a work package.
 */
export const useDeleteWorkPackage = (
  mutationOptions?: Omit<
    UseMutationOptions<
      void,
      Error,
      { id: string; projectId: string }
    >,
    "mutationFn"
  >,
) => {
  const { asOf } = useTimeMachineParams();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id }: { id: string; projectId: string }) => {
      return __request(OpenAPI, {
        method: "DELETE",
        url: "/api/v1/work-packages/{work_package_id}",
        path: { work_package_id: id },
        query: { control_date: asOf || undefined },
        errors: { 422: "Validation Error" },
      });
    },
    onSuccess: (...args) => {
      const variables = args[1] as { projectId: string };

      queryClient.invalidateQueries({
        queryKey: queryKeys.workPackages.all,
      });
      queryClient.invalidateQueries({
        queryKey: queryKeys.workPackages.summary(variables.projectId),
      });

      toast.success("Work package deleted successfully");
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (mutationOptions as any)?.onSuccess?.(...args);
    },
    onError: (...args) => {
      toast.error(`Error deleting work package: ${(args[0] as Error).message}`);
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (mutationOptions as any)?.onError?.(...args);
    },
  });
};

// ---------------------------------------------------------------------------
// Upsert allocations mutation
// ---------------------------------------------------------------------------

/**
 * Hook to replace all cost allocation entries for a work package.
 */
export const useUpsertAllocations = (
  workPackageId: string,
  mutationOptions?: Omit<
    UseMutationOptions<
      QualityCostAllocationRead[],
      Error,
      QualityCostAllocation[]
    >,
    "mutationFn"
  >,
) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (allocations: QualityCostAllocation[]) => {
      return __request(OpenAPI, {
        method: "PUT",
        url: "/api/v1/work-packages/{work_package_id}/allocations",
        path: { work_package_id: workPackageId },
        body: allocations,
        mediaType: "application/json",
        errors: { 422: "Validation Error" },
      });
    },
    onSuccess: (...args) => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.workPackages.allocations(workPackageId),
      });
      queryClient.invalidateQueries({
        queryKey: queryKeys.workPackages.all,
      });

      toast.success("Allocations updated successfully");
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (mutationOptions as any)?.onSuccess?.(...args);
    },
    onError: (...args) => {
      toast.error(`Error updating allocations: ${(args[0] as Error).message}`);
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (mutationOptions as any)?.onError?.(...args);
    },
  });
};
