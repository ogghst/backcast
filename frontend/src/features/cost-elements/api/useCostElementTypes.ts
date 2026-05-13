import { useQuery } from "@tanstack/react-query";
import { CostElementTypesService, type CostElementTypeRead } from "@/api/generated";
import { queryKeys } from "@/api/queryKeys";
import type { PaginatedResponse } from "@/types/api";

export const useCostElementTypes = () => {
  return useQuery({
    queryKey: queryKeys.costElementTypes.list,
    queryFn: async () => {
      const res = await CostElementTypesService.getCostElementTypes(1, 1000, undefined, undefined, undefined, undefined, 'asc');
      // Backend always returns PaginatedResponse with items array
      const paginatedRes = res as PaginatedResponse<CostElementTypeRead>;
      return paginatedRes.items || [];
    },
    staleTime: 5 * 60 * 1000,
  });
};
