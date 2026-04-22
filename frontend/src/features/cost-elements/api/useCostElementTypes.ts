import { useQuery } from "@tanstack/react-query";
import { CostElementTypesService, type CostElementTypeRead } from "@/api/generated";
import { queryKeys } from "@/api/queryKeys";
import type { PaginatedResponse } from "@/types/api";

export const useCostElementTypes = () => {
  return useQuery({
    queryKey: queryKeys.costElementTypes.list,
    queryFn: async () => {
      const res = await CostElementTypesService.getCostElementTypes(1, 1000);
      const items: CostElementTypeRead[] = Array.isArray(res) ? res : (res as PaginatedResponse<CostElementTypeRead>).items || [];
      return items;
    },
    staleTime: 5 * 60 * 1000,
  });
};
