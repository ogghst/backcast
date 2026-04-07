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
 * Maps widget config entity types to the lowercase API format.
 * Handles both uppercase enum keys strings (e.g., "PROJECT", "WBE", "COST_ELEMENT")
 * and lowercase values (e.g., "project", "wbe", "cost_element").
 * Returns undefined for unknown entity types.
 */
function normalizeEntityType(raw: string | undefined): EntityType | undefined {
  if (!raw) return undefined;
  const str = String(raw);
  switch (str) {
    case "PROJECT":
    case "project":
      return EntityType.PROJECT;
    case "WBE":
    case "wbe":
      return EntityType.WBE;
    case "COST_ELEMENT":
    case "cost_element":
      return EntityType.COST_ELEMENT;
    default:
      console.warn(`Unknown entity type: ${raw}`);
      return undefined;
  }
}

/**
 * Resolves entity scope from dashboard context and fetches EVM metrics.
 *
 * Maps EntityType to the correct ID from context:
 * - PROJECT -> projectId
 * - WBE -> wbeId
 * - COST_ELEMENT -> costElementId
 *
 * Uses string-based comparison to handle both enum references and plain strings
 * from deserialized backend JSON config.
 *
 * When the needed ID is undefined, returns a disabled query.
 */
export function useWidgetEVMData(entityType: EntityType): WidgetEVMDataResult {
  const context = useDashboardContext();

  // Normalize to string for robust comparison against both enum and raw string values
  const entityTypeStr = String(entityType);

  const entityId =
    entityTypeStr === EntityType.PROJECT || entityTypeStr === "project"
      ? context.projectId
      : entityTypeStr === EntityType.WBE || entityTypeStr === "wbe"
        ? context.wbeId
        : context.costElementId;

  const normalizedType = normalizeEntityType(entityType);
  const result = useEVMMetrics(normalizedType ?? EntityType.PROJECT, entityId ?? "");

  return {
    metrics: result.data,
    isLoading: result.isLoading,
    error: result.error,
    entityId,
    refetch: result.refetch,
  };
}
