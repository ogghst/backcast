/**
 * Work Package Forecast API hooks (1:1 relationship)
 *
 * Uses nested endpoints: /api/v1/work-packages/{id}/forecast
 * Forecast uses PUT (upsert) - creates if missing, updates if exists.
 */

import {
  useMutation,
  useQueryClient,
  type UseMutationOptions,
  useQuery,
  type UseQueryOptions,
} from "@tanstack/react-query";
import { toast } from "sonner";
import { useTimeMachineParams } from "@/contexts/TimeMachineContext";
import { WorkPackagesPmiService } from "@/api/generated";
import { queryKeys } from "@/api/queryKeys";

export interface WorkPackageForecastRead {
  forecast_id: string;
  work_package_id: string;
  eac_amount: number;
  basis_of_estimate: string;
  approved_date?: string | null;
  approved_by?: string | null;
  branch: string;
  created_by: string;
}

export interface WorkPackageForecastUpdate {
  eac_amount: number;
  basis_of_estimate: string;
  branch?: string;
  control_date?: string | null;
}

export const useWorkPackageForecast = (
  workPackageId: string,
  branch: string = "main",
  queryOptions?: Omit<
    UseQueryOptions<WorkPackageForecastRead | null>,
    "queryKey" | "queryFn"
  >,
) => {
  const { asOf } = useTimeMachineParams();

  return useQuery<WorkPackageForecastRead | null>({
    queryKey: queryKeys.forecasts.byWorkPackage(workPackageId, branch, { asOf }),
    queryFn: async () => {
      try {
        const res = await WorkPackagesPmiService.getWorkPackageForecast(
          workPackageId,
          branch,
          asOf || undefined,
        );
        return res as WorkPackageForecastRead;
      } catch (error: unknown) {
        const status = (error as { status?: number })?.status;
        if (status === 404) return null;
        throw error;
      }
    },
    enabled: !!workPackageId,
    ...queryOptions,
  });
};

export const useUpsertWorkPackageForecast = (
  mutationOptions?: Omit<
    UseMutationOptions<
      WorkPackageForecastRead,
      Error,
      { workPackageId: string; data: WorkPackageForecastUpdate }
    >,
    "mutationFn"
  >,
) => {
  const { asOf } = useTimeMachineParams();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      workPackageId,
      data,
    }: {
      workPackageId: string;
      data: WorkPackageForecastUpdate;
    }) => {
      const payload = {
        ...data,
        branch: data.branch || "main",
        control_date: asOf || null,
      };
      const res = await WorkPackagesPmiService.updateWorkPackageForecast(
        workPackageId,
        payload,
      );
      return res as WorkPackageForecastRead;
    },
    onSuccess: (data, variables, ...rest) => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.forecasts.byWorkPackage(variables.workPackageId),
      });
      queryClient.invalidateQueries({ queryKey: queryKeys.workPackages.all });
      toast.success("Forecast saved successfully");
      mutationOptions?.onSuccess?.(data, variables, ...rest);
    },
    onError: (error, ...args) => {
      toast.error(`Error saving forecast: ${error.message}`);
      mutationOptions?.onError?.(error, ...args);
    },
  });
};

export const useDeleteWorkPackageForecast = (
  mutationOptions?: Omit<
    UseMutationOptions<
      void,
      Error,
      { workPackageId: string; branch?: string }
    >,
    "mutationFn"
  >,
) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      workPackageId,
      branch,
    }: {
      workPackageId: string;
      branch?: string;
    }) => {
      await WorkPackagesPmiService.deleteWorkPackageForecast(
        workPackageId,
        branch || "main",
      );
    },
    onSuccess: (data, variables, ...rest) => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.forecasts.byWorkPackage(variables.workPackageId),
      });
      queryClient.invalidateQueries({ queryKey: queryKeys.workPackages.all });
      toast.success("Forecast deleted successfully");
      mutationOptions?.onSuccess?.(data, variables, ...rest);
    },
    onError: (error, ...args) => {
      toast.error(`Error deleting forecast: ${error.message}`);
      mutationOptions?.onError?.(error, ...args);
    },
  });
};
