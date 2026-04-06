import { useDashboardContext } from "../../context/useDashboardContext";
import { useEVMMetrics } from "@/features/evm/api/useEVMMetrics";
import { EntityType } from "@/features/evm/types";
import type { EVMMetricsResponse } from "@/features/evm/types";

interface WidgetEVMDataResult {
  metrics: EVMMetricsResponse | undefined;
  isLoading: boolean;
  error: Error | null;
  entityId: string | undefined;
  refetch: () => void;
}

/**
 * Resolves entity scope from dashboard context and fetches EVM metrics.
 *
 * Maps EntityType to the correct ID from context:
 * - PROJECT -> projectId
 * - WBE -> wbeId
 * - COST_ELEMENT -> costElementId
 *
 * When the needed ID is undefined, returns a disabled query.
 */
export function useWidgetEVMData(entityType: EntityType): WidgetEVMDataResult {
  const context = useDashboardContext();

  const entityId =
    entityType === EntityType.PROJECT
      ? context.projectId
      : entityType === EntityType.WBE
        ? context.wbeId
        : context.costElementId;

  const result = useEVMMetrics(entityType, entityId ?? "");

  return {
    metrics: result.data,
    isLoading: result.isLoading,
    error: result.error,
    entityId,
    refetch: result.refetch,
  };
}
