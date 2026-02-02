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

import { useQuery } from "@tanstack/react-query";
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
    ReturnType<typeof useQuery<EVMMetricsResponse>>["options"],
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
      transformed[field] = parseFloat(
        value,
      ) as EVMMetricsResponse[typeof field];
    }
  }

  return transformed;
}

/**
 * Response from batch EVM metrics query
 */
interface EVMMetricsBatchResponse {
  /** Entity type for all metrics */
  entity_type: EntityType;
  /** Individual entity metrics */
  metrics: Array<Omit<EVMMetricsResponse, "entity_type">>;
  /** Aggregated metrics across all entities */
  aggregated: Omit<
    EVMMetricsResponse,
    | "entity_type"
    | "entity_id"
    | "control_date"
    | "branch"
    | "branch_mode"
    | "warning"
  >;
}

/**
 * Fetch EVM metrics for a single entity.
 *
 * @param entityType - Type of entity (cost_element, wbe, project)
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
    }),
    queryFn: async () => {
      // For cost elements, use the existing endpoint
      // For WBE and project, we'll need to check if those endpoints exist
      // and fall back to the appropriate endpoint or throw an error
      const data =
        entityType === "cost_element"
          ? await __request(OpenAPI, {
              method: "GET",
              url: "/api/v1/cost-elements/{cost_element_id}/evm",
              path: {
                cost_element_id: entityId,
              },
              query: {
                control_date: controlDate || undefined,
                branch,
                branch_mode: tmMode === "merged" ? "merge" : "strict",
              },
            })
          : await __request(OpenAPI, {
              method: "GET",
              url: "/api/v1/evm/{entity_type}/{entity_id}/metrics",
              path: {
                entity_type: entityType,
                entity_id: entityId,
              },
              query: {
                control_date: controlDate || undefined,
                branch,
                branch_mode: tmMode === "merged" ? "merge" : "strict",
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
    ReturnType<typeof useQuery<EVMTimeSeriesResponse>>["options"],
    "queryKey" | "queryFn"
  >;
}

/**
 * Fetch time-series EVM data for an entity.
 *
 * @param entityType - Type of entity (cost_element, wbe, project)
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
    }),
    queryFn: async () => {
      // For cost elements, use the cost-element-specific endpoint
      if (entityType === "cost_element") {
        return await __request(OpenAPI, {
          method: "GET",
          url: "/api/v1/cost-elements/{cost_element_id}/evm-history",
          path: {
            cost_element_id: entityId,
          },
          query: {
            granularity,
            control_date: controlDate || undefined,
            branch,
            branch_mode: tmMode === "merged" ? "merge" : "strict",
          },
        });
      }

      // For WBE and Project entity types, use the generic endpoint
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
          branch_mode: tmMode === "merged" ? "merge" : "strict",
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
    ReturnType<typeof useQuery<EVMMetricsBatchResponse>>["options"],
    "queryKey" | "queryFn"
  >;
}

/**
 * Fetch aggregated EVM metrics for multiple entities.
 *
 * @param entityType - Type of entities (cost_element, wbe, project)
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

  return useQuery<EVMMetricsBatchResponse>({
    queryKey: queryKeys.evm.batch(entityType, entityIds || [], {
      branch,
      controlDate,
    }),
    queryFn: async () => {
      // Use the batch endpoint for all entity types
      return await __request(OpenAPI, {
        method: "POST",
        url: "/api/v1/evm/{entity_type}/batch",
        path: {
          entity_type: entityType,
        },
        query: {
          control_date: controlDate || undefined,
          branch,
          branch_mode: tmMode === "merged" ? "merge" : "strict",
        },
        body: {
          entity_ids: entityIds || [],
        },
      });
    },
    enabled: !!entityIds && entityIds.length > 0,
    ...params?.queryOptions,
  });
}
