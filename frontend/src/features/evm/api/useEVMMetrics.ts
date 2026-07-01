/**
 * Custom EVM (Earned Value Management) Hooks
 *
 * Provides TanStack Query hooks for fetching EVM metrics, time-series data,
 * and batch metrics for multiple entities.
 *
 * Features:
 * - useEVMMetrics: Fetch metrics for a single entity
 * - useEVMTimeSeries: Fetch time-series data with granularity
 * - useEVMMetricsBatch: Fetch aggregated metrics for multiple entities
 *
 * All hooks integrate with TimeMachineContext for time-travel queries.
 */

import { useQuery, type UseQueryOptions } from "@tanstack/react-query";
import { useTimeMachineParams } from "@/contexts/TimeMachineContext";
import { OpenAPI } from "@/api/generated/core/OpenAPI";
import { request as __request } from "@/api/generated/core/request";
import { queryKeys } from "@/api/queryKeys";
import type {
  EVMMetricsResponse,
  EVMTimeSeriesResponse,
  EVMTimeSeriesGranularity,
  EntityType,
} from "../types";

/**
 * Parameters for EVM metrics queries
 */
interface EVMQueryParams {
  /** Branch to query (default: from TimeMachine context) */
  branch?: string;
  /** Control date for time-travel queries (ISO 8601 string) */
  controlDate?: string;
}

/**
 * Extended parameters for useEVMMetrics
 */
interface UseEVMMetricsParams extends EVMQueryParams {
  /** TanStack Query options */
  queryOptions?: Omit<
    UseQueryOptions<EVMMetricsResponse>,
    "queryKey" | "queryFn"
  >;
}

/**
 * Transform API response to ensure numeric fields are numbers (not strings).
 *
 * The backend may return numeric values as strings due to Decimal serialization.
 * This transformer ensures all numeric fields are actual numbers.
 */
function transformEVMMetricsResponse(data: unknown): EVMMetricsResponse {
  const response = data as EVMMetricsResponse;

  // Convert numeric fields that may come as strings from Python Decimal serialization
  const numericFields: (keyof EVMMetricsResponse)[] = [
    "bac",
    "pv",
    "ac",
    "ev",
    "cv",
    "sv",
    "cpi",
    "spi",
    "eac",
    "vac",
    "etc",
  ];

  const transformed = { ...response };

  for (const field of numericFields) {
    const value = transformed[field];
    if (value !== null && typeof value === "string") {
      // Convert string to number
      (transformed as Record<string, unknown>)[field] = parseFloat(value);
    }
  }

  return transformed;
}

/**
 * Fetch EVM metrics for a single entity.
 *
 * @param entityType - Type of entity (cost_element | work_package | control_account | wbs_element | project)
 * @param entityId - ID of the entity to fetch metrics for
 * @param params - Optional query parameters
 * @returns TanStack Query result with EVM metrics
 *
 * @example
 * ```tsx
 * const { data, isLoading, error } = useEVMMetrics("cost_element", costElementId);
 * ```
 */
export function useEVMMetrics(
  entityType: EntityType,
  entityId: string,
  params?: UseEVMMetricsParams,
) {
  const { mode: tmMode, branch: tmBranch, asOf } = useTimeMachineParams();

  const branch = params?.branch || tmBranch || "main";
  const controlDate = params?.controlDate || asOf;

  return useQuery<EVMMetricsResponse>({
    queryKey: queryKeys.evm.metrics(entityType, entityId, {
      branch,
      controlDate,
      mode: tmMode,
    }),
    queryFn: async () => {
      // All entity types (incl. cost_element) use the generic EVM metrics route.
      // The backend resolves a cost_element to its owning Work Package server-side.
      const data = await __request(OpenAPI, {
        method: "GET",
        url: "/api/v1/evm/{entity_type}/{entity_id}/metrics",
        path: {
          entity_type: entityType,
          entity_id: entityId,
        },
        query: {
          control_date: controlDate || undefined,
          branch,
          branch_mode: tmMode,
        },
      });

      return transformEVMMetricsResponse(data);
    },
    enabled: !!entityId && entityId.length > 0,
    ...params?.queryOptions,
  });
}

/**
 * Parameters for time-series queries
 */
interface EVMTimeSeriesParams extends EVMQueryParams {
  /** Time granularity (day, week, month) */
  granularity: EVMTimeSeriesGranularity;
  /** TanStack Query options */
  queryOptions?: Omit<
    UseQueryOptions<EVMTimeSeriesResponse>,
    "queryKey" | "queryFn"
  >;
}

/**
 * Fetch time-series EVM data for an entity.
 *
 * @param entityType - Type of entity (cost_element | work_package | control_account | wbs_element | project)
 * @param entityId - ID of the entity to fetch time-series for
 * @param granularity - Time granularity for data points
 * @param params - Optional query parameters
 * @returns TanStack Query result with time-series data
 *
 * @example
 * ```tsx
 * const { data, isLoading, error } = useEVMTimeSeries(
 *   "cost_element",
 *   costElementId,
 *   "week"
 * );
 * ```
 */
export function useEVMTimeSeries(
  entityType: EntityType,
  entityId: string,
  granularity: EVMTimeSeriesGranularity,
  params?: EVMTimeSeriesParams,
) {
  const { mode: tmMode, branch: tmBranch, asOf } = useTimeMachineParams();

  const branch = params?.branch || tmBranch || "main";
  const controlDate = params?.controlDate || asOf;

  return useQuery<EVMTimeSeriesResponse>({
    queryKey: queryKeys.evm.timeSeries(entityType, entityId, {
      branch,
      controlDate,
      granularity,
      mode: tmMode,
    }),
    queryFn: async () => {
      return await __request(OpenAPI, {
        method: "GET",
        url: "/api/v1/evm/{entity_type}/{entity_id}/timeseries",
        path: {
          entity_type: entityType,
          entity_id: entityId,
        },
        query: {
          granularity,
          control_date: controlDate || undefined,
          branch,
          branch_mode: tmMode,
        },
      });
    },
    enabled: !!entityId && entityId.length > 0 && !!granularity,
    ...params?.queryOptions,
  });
}

/**
 * Parameters for batch metrics queries
 */
interface EVMMetricsBatchParams extends EVMQueryParams {
  /** TanStack Query options */
  queryOptions?: Omit<
    UseQueryOptions<EVMMetricsResponse>,
    "queryKey" | "queryFn"
  >;
}

/**
 * Fetch aggregated EVM metrics for multiple entities.
 *
 * @param entityType - Type of entities (cost_element | work_package | control_account | wbs_element | project)
 * @param entityIds - Array of entity IDs to fetch metrics for
 * @param params - Optional query parameters
 * @returns TanStack Query result with batch metrics
 *
 * @example
 * ```tsx
 * const { data, isLoading, error } = useEVMMetricsBatch(
 *   "cost_element",
 *   [id1, id2, id3]
 * );
 * ```
 */
export function useEVMMetricsBatch(
  entityType: EntityType,
  entityIds: string[] | undefined,
  params?: EVMMetricsBatchParams,
) {
  const { mode: tmMode, branch: tmBranch, asOf } = useTimeMachineParams();

  const branch = params?.branch || tmBranch || "main";
  const controlDate = params?.controlDate || asOf;

  return useQuery<EVMMetricsResponse>({
    queryKey: queryKeys.evm.batch(entityType, entityIds || [], {
      branch,
      controlDate,
      mode: tmMode,
    }),
    queryFn: async () => {
      // POST /evm/batch — all params in the body; backend returns a single
      // aggregated EVMMetricsResponse (re-derives CPI/SPI/TCPI from summed
      // EV/AC/PV).
      const data = await __request(OpenAPI, {
        method: "POST",
        url: "/api/v1/evm/batch",
        body: {
          entity_type: entityType,
          entity_ids: entityIds || [],
          control_date: controlDate || undefined,
          branch,
          branch_mode: tmMode,
        },
      });
      return transformEVMMetricsResponse(data);
    },
    enabled: !!entityIds && entityIds.length > 0,
    ...params?.queryOptions,
  });
}
