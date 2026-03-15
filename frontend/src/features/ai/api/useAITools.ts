import axios from "axios";
import {
  useQuery as useTanstackQuery,
  type UseQueryOptions,
} from "@tanstack/react-query";
import { queryKeys } from "@/api/queryKeys";
import type { AIToolPublic } from "../types";

const API_BASE = "/api/v1/ai/config";

const toolApi = {
  list: async (): Promise<AIToolPublic[]> => {
    const response = await axios.get<AIToolPublic[]>(`${API_BASE}/tools`);
    return response.data;
  },
};

/**
 * Hook to fetch all documented AI tools from the backend registry
 */
export const useAITools = (
  options?: Omit<UseQueryOptions<AIToolPublic[], Error>, "queryKey" | "queryFn">
) => {
  return useTanstackQuery<AIToolPublic[], Error>({
    queryKey: queryKeys.ai.tools.lists(),
    queryFn: () => toolApi.list(),
    ...options,
  });
};
