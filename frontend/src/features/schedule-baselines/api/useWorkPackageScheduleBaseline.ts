/**
 * Work Package Schedule Baseline API hooks (1:1 relationship)
 *
 * Uses nested endpoints: /api/v1/work-packages/{id}/schedule-baseline
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
import type { ScheduleBaselineRead } from "@/api/generated";

export const useWorkPackageScheduleBaseline = (
  workPackageId: string,
  branch: string = "main",
  queryOptions?: Omit<
    UseQueryOptions<ScheduleBaselineRead | null>,
    "queryKey" | "queryFn"
  >,
) => {
  const { asOf } = useTimeMachineParams();

  return useQuery<ScheduleBaselineRead | null>({
    queryKey: queryKeys.scheduleBaselines.byWorkPackage(workPackageId, {
      branch,
      asOf,
    }),
    queryFn: async () => {
      try {
        const res =
          await WorkPackagesPmiService.getWorkPackageScheduleBaseline(
            workPackageId,
            branch,
          );
        return res as ScheduleBaselineRead;
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

export const useCreateWorkPackageScheduleBaseline = (
  mutationOptions?: Omit<
    UseMutationOptions<
      ScheduleBaselineRead,
      Error,
      {
        workPackageId: string;
        name: string;
        start_date: string;
        end_date: string;
        progression_type?: "LINEAR" | "GAUSSIAN" | "LOGARITHMIC";
        description?: string;
        branch?: string;
      }
    >,
    "mutationFn"
  >,
) => {
  const { asOf } = useTimeMachineParams();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      workPackageId,
      branch,
      ...data
    }: {
      workPackageId: string;
      name: string;
      start_date: string;
      end_date: string;
      progression_type?: "LINEAR" | "GAUSSIAN" | "LOGARITHMIC";
      description?: string;
      branch?: string;
    }) => {
      const payload = {
        ...data,
        branch: branch || "main",
        control_date: asOf || null,
      };
      const res =
        await WorkPackagesPmiService.createWorkPackageScheduleBaseline(
          workPackageId,
          payload,
        );
      return res as ScheduleBaselineRead;
    },
    onSuccess: (data, variables, ...rest) => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.scheduleBaselines.byWorkPackage(
          variables.workPackageId,
        ),
      });
      queryClient.invalidateQueries({ queryKey: queryKeys.workPackages.all });
      toast.success("Schedule Baseline created successfully");
      mutationOptions?.onSuccess?.(data, variables, ...rest);
    },
    onError: (error, ...args) => {
      toast.error(`Error creating Schedule Baseline: ${error.message}`);
      mutationOptions?.onError?.(error, ...args);
    },
  });
};

export const useUpdateWorkPackageScheduleBaseline = (
  mutationOptions?: Omit<
    UseMutationOptions<
      ScheduleBaselineRead,
      Error,
      {
        workPackageId: string;
        baselineId: string;
        data: {
          name?: string;
          start_date?: string;
          end_date?: string;
          progression_type?: "LINEAR" | "GAUSSIAN" | "LOGARITHMIC";
          description?: string;
        };
        branch?: string;
      }
    >,
    "mutationFn"
  >,
) => {
  const { asOf } = useTimeMachineParams();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      workPackageId,
      baselineId,
      data,
      branch,
    }: {
      workPackageId: string;
      baselineId: string;
      data: {
        name?: string;
        start_date?: string;
        end_date?: string;
        progression_type?: "LINEAR" | "GAUSSIAN" | "LOGARITHMIC";
        description?: string;
      };
      branch?: string;
    }) => {
      const payload = {
        ...data,
        branch: branch || "main",
        control_date: asOf || null,
      };
      const res =
        await WorkPackagesPmiService.updateWorkPackageScheduleBaseline(
          workPackageId,
          baselineId,
          payload,
        );
      return res as ScheduleBaselineRead;
    },
    onSuccess: (data, variables, ...rest) => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.scheduleBaselines.byWorkPackage(
          variables.workPackageId,
        ),
      });
      queryClient.invalidateQueries({ queryKey: queryKeys.workPackages.all });
      toast.success("Schedule Baseline updated successfully");
      mutationOptions?.onSuccess?.(data, variables, ...rest);
    },
    onError: (error, ...args) => {
      toast.error(`Error updating Schedule Baseline: ${error.message}`);
      mutationOptions?.onError?.(error, ...args);
    },
  });
};

export const useDeleteWorkPackageScheduleBaseline = (
  mutationOptions?: Omit<
    UseMutationOptions<
      void,
      Error,
      { workPackageId: string; baselineId: string; branch?: string }
    >,
    "mutationFn"
  >,
) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      workPackageId,
      baselineId,
      branch,
    }: {
      workPackageId: string;
      baselineId: string;
      branch?: string;
    }) => {
      await WorkPackagesPmiService.deleteWorkPackageScheduleBaseline(
        workPackageId,
        baselineId,
        branch || "main",
      );
    },
    onSuccess: (data, variables, ...rest) => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.scheduleBaselines.byWorkPackage(
          variables.workPackageId,
        ),
      });
      queryClient.invalidateQueries({ queryKey: queryKeys.workPackages.all });
      toast.success("Schedule Baseline deleted successfully");
      mutationOptions?.onSuccess?.(data, variables, ...rest);
    },
    onError: (error, ...args) => {
      toast.error(`Error deleting Schedule Baseline: ${error.message}`);
      mutationOptions?.onError?.(error, ...args);
    },
  });
};
