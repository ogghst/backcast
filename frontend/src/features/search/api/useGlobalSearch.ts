import { useQuery } from "@tanstack/react-query";
import { OpenAPI } from "@/api/generated/core/OpenAPI";
import { request as __request } from "@/api/generated/core/request";
import { queryKeys } from "@/api/queryKeys";
import {
  useAsOfParam,
  useBranchParam,
  useModeParam,
} from "@/stores/useTimeMachineStore";
import type {
  GlobalSearchResponse,
  GlobalSearchParams,
} from "../types";

/**
 * Hook to perform a global search across all entity types.
 * Uses TanStack Query with temporal context (as_of, branch, mode).
 * Only enabled when the query string has at least 1 character.
 */
export const useGlobalSearch = (params: GlobalSearchParams) => {
  const asOf = useAsOfParam();
  const branch = useBranchParam();
  const mode = useModeParam();

  return useQuery<GlobalSearchResponse>({
    queryKey: queryKeys.search.global(params, asOf, branch, mode),
    queryFn: async () => {
      return __request(OpenAPI, {
        method: "GET",
        url: "/api/v1/search",
        query: {
          q: params.q,
          project_id: params.project_id || undefined,
          wbe_id: params.wbe_id || undefined,
          limit: params.limit ?? 50,
          branch,
          mode,
          as_of: asOf || undefined,
        },
      }) as Promise<GlobalSearchResponse>;
    },
    enabled: params.q.length >= 1,
  });
};
