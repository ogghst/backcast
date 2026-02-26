import {
  useMutation,
  useQueryClient,
  UseMutationOptions,
} from "@tanstack/react-query";
import { toast } from "sonner";
import { OpenAPI } from "@/api/generated/core/OpenAPI";
import { request as __request } from "@/api/generated/core/request";
import { queryKeys } from "@/api/queryKeys";

/**
 * Custom hook for archiving an Implemented or Rejected change order.
 * Soft-deletes the branch.
 */
export const useArchiveChangeOrder = (
  mutationOptions?: Omit<UseMutationOptions<void, Error, string>, "mutationFn">,
) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => {
      return __request(OpenAPI, {
        method: "POST",
        url: `/api/v1/change-orders/${id}/archive`,
      }) as Promise<void>;
    },
    onSuccess: (...args) => {
      // Invalidate change orders queries so the archived one disappears from standard lists
      queryClient.invalidateQueries({ queryKey: queryKeys.changeOrders.all });
      queryClient.invalidateQueries({ queryKey: queryKeys.projects.all });

      toast.success("Branch archived successfully");
      mutationOptions?.onSuccess?.(...args);
    },
    onError: (error, ...args) => {
      toast.error(`Error archiving branch: ${error.message}`);
      mutationOptions?.onError?.(error, ...args);
    },
    ...mutationOptions,
  });
};
