/**
 * Control Account API hooks - TanStack Query integration.
 *
 * Control Accounts sit at the intersection of WBS Elements and
 * Organizational Units in the responsibility assignment matrix (RAM).
 * They are branchable and versionable.
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
import type {
  ControlAccountRead,
  ControlAccountCreate,
  ControlAccountUpdate,
} from "@/api/generated";
import type { PaginatedResponse } from "@/types/api";
import { queryKeys } from "@/api/queryKeys";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ControlAccountListParams {
  wbs_element_id?: string;
  organizational_unit_id?: string;
  page?: number;
  perPage?: number;
  asOf?: string;
  queryOptions?: Omit<
    UseQueryOptions<PaginatedResponse<ControlAccountRead>>,
    "queryKey" | "queryFn"
  >;
}

// ---------------------------------------------------------------------------
// List hook
// ---------------------------------------------------------------------------

/**
 * Hook to fetch control accounts with optional filtering.
 */
export const useControlAccounts = (params: ControlAccountListParams = {}) => {
  const { asOf: tmAsOf } = useTimeMachineParams();

  return useQuery<PaginatedResponse<ControlAccountRead>>({
    queryKey: queryKeys.controlAccounts.list({
      wbs_element_id: params.wbs_element_id,
      organizational_unit_id: params.organizational_unit_id,
      page: params.page,
      perPage: params.perPage,
      asOf: params.asOf || tmAsOf,
    }),
    queryFn: async () => {
      const {
        wbs_element_id,
        organizational_unit_id,
        page = 1,
        perPage = 20,
      } = params;

      const result = await __request(OpenAPI, {
        method: "GET",
        url: "/api/v1/control-accounts",
        query: {
          page,
          per_page: perPage,
          wbs_element_id: wbs_element_id || undefined,
          organizational_unit_id: organizational_unit_id || undefined,
          as_of: params.asOf || tmAsOf || undefined,
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
      return result as unknown as PaginatedResponse<ControlAccountRead>;
    },
    ...params.queryOptions,
  });
};

// ---------------------------------------------------------------------------
// Detail hook
// ---------------------------------------------------------------------------

export const useControlAccount = (
  controlAccountId: string,
  asOf?: string,
) => {
  const { asOf: tmAsOf } = useTimeMachineParams();

  return useQuery<ControlAccountRead>({
    queryKey: queryKeys.controlAccounts.detail(controlAccountId, {
      asOf: asOf || tmAsOf,
    }),
    queryFn: async () => {
      return await __request(OpenAPI, {
        method: "GET",
        url: "/api/v1/control-accounts/{control_account_id}",
        path: { control_account_id: controlAccountId },
        query: { as_of: asOf || tmAsOf || undefined },
        errors: { 422: "Validation Error" },
      });
    },
    enabled: !!controlAccountId,
  });
};

// ---------------------------------------------------------------------------
// History hook
// ---------------------------------------------------------------------------

export const useControlAccountHistory = (controlAccountId: string) => {
  return useQuery<ControlAccountRead[]>({
    queryKey: queryKeys.controlAccounts.history(controlAccountId),
    queryFn: async () => {
      return await __request(OpenAPI, {
        method: "GET",
        url: "/api/v1/control-accounts/{control_account_id}/history",
        path: { control_account_id: controlAccountId },
        errors: { 422: "Validation Error" },
      });
    },
    enabled: !!controlAccountId,
  });
};

// ---------------------------------------------------------------------------
// Create mutation
// ---------------------------------------------------------------------------

export const useCreateControlAccount = (
  mutationOptions?: Omit<
    UseMutationOptions<ControlAccountRead, Error, ControlAccountCreate>,
    "mutationFn"
  >,
) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: ControlAccountCreate) => {
      return __request(OpenAPI, {
        method: "POST",
        url: "/api/v1/control-accounts",
        body: data,
        mediaType: "application/json",
        errors: { 422: "Validation Error" },
      });
    },
    onSuccess: (...args) => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.controlAccounts.all,
      });
      toast.success("Control account created successfully");
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (mutationOptions as any)?.onSuccess?.(...args);
    },
    onError: (...args) => {
      toast.error(`Error creating control account: ${(args[0] as Error).message}`);
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (mutationOptions as any)?.onError?.(...args);
    },
  });
};

// ---------------------------------------------------------------------------
// Update mutation (with optimistic update)
// ---------------------------------------------------------------------------

export const useUpdateControlAccount = (
  mutationOptions?: Omit<
    UseMutationOptions<
      ControlAccountRead,
      Error,
      { id: string; data: ControlAccountUpdate },
      { previous?: ControlAccountRead }
    >,
    "mutationFn"
  >,
) => {
  const { asOf } = useTimeMachineParams();
  const queryClient = useQueryClient();

  return useMutation<
    ControlAccountRead,
    Error,
    { id: string; data: ControlAccountUpdate },
    { previous?: ControlAccountRead }
  >({
    mutationFn: ({ id, data }) => {
      return __request(OpenAPI, {
        method: "PUT",
        url: "/api/v1/control-accounts/{control_account_id}",
        path: { control_account_id: id },
        body: data,
        mediaType: "application/json",
        errors: { 422: "Validation Error" },
      });
    },
    onMutate: async ({ id, data }) => {
      await queryClient.cancelQueries({
        queryKey: queryKeys.controlAccounts.detail(id, { asOf }),
      });
      await queryClient.cancelQueries({
        queryKey: queryKeys.controlAccounts.lists(),
      });

      const previous = queryClient.getQueryData<ControlAccountRead>(
        queryKeys.controlAccounts.detail(id, { asOf }),
      );

      if (previous) {
        queryClient.setQueryData(
          queryKeys.controlAccounts.detail(id, { asOf }),
          (old: ControlAccountRead) => ({ ...old, ...data }),
        );
      }

      return { previous };
    },
    onSuccess: (...args) => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.controlAccounts.all,
      });
      toast.success("Control account updated successfully");
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (mutationOptions as any)?.onSuccess?.(...args);
    },
    onError: (...args) => {
      const error = args[0] as Error;
      const variables = args[1] as { id: string };
      const context = args[2] as { previous?: ControlAccountRead } | undefined;
      if (context?.previous) {
        queryClient.setQueryData(
          queryKeys.controlAccounts.detail(variables.id, { asOf }),
          context.previous,
        );
      }
      toast.error(`Error updating control account: ${error.message}`);
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (mutationOptions as any)?.onError?.(...args);
    },
  });
};

// ---------------------------------------------------------------------------
// Delete mutation
// ---------------------------------------------------------------------------

export const useDeleteControlAccount = (
  mutationOptions?: Omit<
    UseMutationOptions<void, Error, string>,
    "mutationFn"
  >,
) => {
  const { asOf } = useTimeMachineParams();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => {
      return __request(OpenAPI, {
        method: "DELETE",
        url: "/api/v1/control-accounts/{control_account_id}",
        path: { control_account_id: id },
        query: { control_date: asOf || undefined },
        errors: { 422: "Validation Error" },
      });
    },
    onSuccess: (...args) => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.controlAccounts.all,
      });
      toast.success("Control account deleted successfully");
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (mutationOptions as any)?.onSuccess?.(...args);
    },
    onError: (...args) => {
      toast.error(`Error deleting control account: ${(args[0] as Error).message}`);
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (mutationOptions as any)?.onError?.(...args);
    },
  });
};
