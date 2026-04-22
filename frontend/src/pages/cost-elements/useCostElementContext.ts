import { useOutletContext } from "react-router-dom";
import type { CostElementRead } from "@/api/generated";

export function useCostElementContext() {
  return useOutletContext<{ costElement: CostElementRead }>();
}
