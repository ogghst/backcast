import {
  useMutation,
  useQueryClient,
  UseMutationOptions,
  useQuery,
  type UseQueryOptions,
} from "@tanstack/react-query";
import { toast } from "sonner";
import { useTimeMachineParams } from "@/contexts/TimeMachineContext";
import {
  ForecastsService,
  type ForecastRead,
  type ForecastCreate,
  type ForecastUpdate,
} from "@/api/generated";
import { OpenAPI } from "@/api/generated/core/OpenAPI";
import { request as __request } from "@/api/generated/core/request";
import type { PaginatedResponse } from "@/types/api";
import { queryKeys } from "@/api/queryKeys";

// Extended types for Branch support
export type CreateWithBranch = ForecastCreate & { branch?: string };
export type UpdateWithBranch = ForecastUpdate & { branch?: string };

/**
 * Forecast API parameters for filtering, pagination, and sorting.
 */
interface ForecastListParams {
  branch?: string;
  pagination?: { current?: number; pageSize?: number };
  cost_element_id?: string;
  queryOptions?: Omit<UseQueryOptions<PaginatedResponse<ForecastRead>>, "queryKey" | "queryFn">;
}

/**
 * Custom useForecasts list hook with Time Machine integration.
 */
export const useForecasts = (params?: ForecastListParams) => {
  const { asOf, mode, branch: tmBranch } = useTimeMachineParams();

  return useQuery<PaginatedResponse<ForecastRead>>({
    queryKey: queryKeys.forecasts.list(params?.cost_element_id, {
      ...params,
      asOf,
      mode,
      branch: tmBranch,
    }),
    queryFn: async () => {
      const {
        branch = tmBranch || "main",
        pagination,
        cost_element_id,
      } = params || {};
      const page = pagination?.current || 1;
      const perPage = pagination?.pageSize || 20;

      // Manual request to support as_of and mode query params
      const res = await __request(OpenAPI, {
        method: "GET",
        url: "/api/v1/forecasts",
        query: {
          page,
          per_page: perPage,
          branch,
          cost_element_id,
          mode: mode,
          as_of: asOf || undefined,
        },
      });

      if (Array.isArray(res)) {
        return {
          items: res,
          total: res.length,
          page: 1,
          per_page: res.length,
        };
      }
      return res as unknown as PaginatedResponse<ForecastRead>;
    },
    ...params?.queryOptions,
  });
};

/**
 * Hook to get a single forecast by ID.
 */
export const useForecast = (forecastId: string, branch?: string) => {
  const { asOf, mode, branch: tmBranch } = useTimeMachineParams();

  return useQuery<ForecastRead>({
    queryKey: queryKeys.forecasts.detail(forecastId, {
      branch: branch || tmBranch,
      asOf,
      mode,
    }),
    queryFn: async () => {
      return ForecastsService.getForecast(
        forecastId,
        branch || tmBranch || "main",
        asOf || undefined
      );
    },
    enabled: !!forecastId,
  });
};

/**
 * Hook to get forecast comparison metrics (EVM calculations).
 * @deprecated Use useCostElementEvmMetrics from useCostElements instead.
 */
export const useForecastComparison = (forecastId: string, branch?: string) => {
  console.warn(
    "useForecastComparison is deprecated. Use useCostElementEvmMetrics from useCostElements instead."
  );
  const { branch: tmBranch } = useTimeMachineParams();

  return useQuery({
    queryKey: queryKeys.forecasts.comparison(forecastId, branch || tmBranch),
    queryFn: async () => {
      return __request(OpenAPI, {
        method: "GET",
        url: "/api/v1/forecasts/{forecast_id}/comparison",
        path: { forecast_id: forecastId },
        query: { branch: branch || tmBranch || "main" },
      });
    },
    enabled: !!forecastId,
  });
};

/**
 * Custom create hook with Time Machine integration.
 * Automatically injects control_date from TimeMachine context.
 */
export const useCreateForecast = (
  mutationOptions?: Omit<
    UseMutationOptions<ForecastRead, Error, CreateWithBranch>,
    "mutationFn"
  >
) => {
  const { asOf } = useTimeMachineParams();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CreateWithBranch) => {
      const { branch, ...rest } = data;
      // Inject control_date
      const payload: ForecastCreate = {
        ...rest,
        control_date: asOf || null,
      };
      return ForecastsService.createForecast(payload, branch || "main");
    },
    onSuccess: (...args) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.forecasts.all });
      toast.success("Forecast created successfully");
      mutationOptions?.onSuccess?.(...args);
    },
    onError: (error, ...args) => {
      toast.error(`Error creating forecast: ${error.message}`);
      mutationOptions?.onError?.(error, ...args);
    },
  });
};

/**
 * Custom update hook with Time Machine integration.
 * Automatically injects control_date from TimeMachine context.
 */
export const useUpdateForecast = (
  mutationOptions?: Omit<
    UseMutationOptions<
      ForecastRead,
      Error,
      { id: string; data: UpdateWithBranch }
    >,
    "mutationFn"
  >
) => {
  const { asOf } = useTimeMachineParams();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateWithBranch }) => {
      const { branch, ...rest } = data;
      // Inject control_date
      const payload: ForecastUpdate = {
        ...rest,
        control_date: asOf || null,
      };
      return ForecastsService.updateForecast(
        id,
        payload,
        branch || "main"
      );
    },
    onSuccess: (...args) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.forecasts.all });
      toast.success("Forecast updated successfully");
      mutationOptions?.onSuccess?.(...args);
    },
    onError: (error, ...args) => {
      toast.error(`Error updating forecast: ${error.message}`);
      mutationOptions?.onError?.(error, ...args);
    },
  });
};

/**
 * Custom delete hook with Time Machine integration.
 * Automatically injects control_date from TimeMachine context as a query parameter.
 */
export const useDeleteForecast = (
  mutationOptions?: Omit<UseMutationOptions<void, Error, string>, "mutationFn">
) => {
  const { asOf } = useTimeMachineParams();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (compositeId: string) => {
      // compositeId format: "uuid:::branch"
      const [id, branch] = compositeId.split(":::");

      // Manual request to support control_date query param
      return __request(OpenAPI, {
        method: "DELETE",
        url: "/api/v1/forecasts/{forecast_id}",
        path: {
          forecast_id: id,
        },
        query: {
          branch: branch || "main",
          control_date: asOf || undefined,
        },
      }) as Promise<void>;
    },
    onSuccess: (...args) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.forecasts.all });
      toast.success("Forecast deleted successfully");
      mutationOptions?.onSuccess?.(...args);
    },
    onError: (error, ...args) => {
      toast.error(`Error deleting forecast: ${error.message}`);
      mutationOptions?.onError?.(error, ...args);
    },
  });
};
