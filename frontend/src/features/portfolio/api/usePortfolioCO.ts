/**
 * Portfolio Change-Order pipeline hook.
 *
 * Wraps `GET /api/v1/change-orders/portfolio-stats` and coerces
 * Decimal-serialized string values (cost exposure, pending/approved value,
 * trend cumulative values) to numbers. Mirrors the EVM hook pattern.
 */

import { useQuery } from "@tanstack/react-query";
import { OpenAPI } from "@/api/generated/core/OpenAPI";
import { request as __request } from "@/api/generated/core/request";
import { queryKeys } from "@/api/queryKeys";
import type { ChangeOrderStatsResponse } from "@/api/generated/models/ChangeOrderStatsResponse";

/** Coerce a single string-or-number value to a number (null passes through). */
function toNumber(value: unknown): number | null | undefined {
  if (value === null || value === undefined) return value as null | undefined;
  if (typeof value === "number") return value;
  if (typeof value === "string") {
    const n = parseFloat(value);
    return Number.isNaN(n) ? null : n;
  }
  return value as number;
}

/**
 * Transform the CO portfolio stats response: ensure the top-level monetary
 * fields are real numbers (not Decimal strings).
 *
 * The per-point `cost_trend[].cumulative_value` is left as the generated
 * `string` type to preserve the `ChangeOrderStatsResponse` contract; callers
 * that need it numeric can `parseFloat` at render time.
 */
export function transformCOStatsNumeric(
  data: ChangeOrderStatsResponse,
): ChangeOrderStatsResponse {
  const transformed: ChangeOrderStatsResponse = { ...data };

  transformed.total_cost_exposure = toNumber(
    transformed.total_cost_exposure,
  ) as ChangeOrderStatsResponse["total_cost_exposure"];
  transformed.pending_value = toNumber(
    transformed.pending_value,
  ) as ChangeOrderStatsResponse["pending_value"];
  transformed.approved_value = toNumber(
    transformed.approved_value,
  ) as ChangeOrderStatsResponse["approved_value"];

  return transformed;
}

/** Parameters for {@link usePortfolioCO}. */
export interface UsePortfolioCOParams {
  /** As-of date for the pipeline snapshot; null/undefined = now. */
  asOf?: string | null;
  /** Branch to query (default "main"). */
  branch?: string;
  /** Aging threshold in days (default 7). */
  agingThresholdDays?: number;
  /** TanStack Query enabled flag. */
  enabled?: boolean;
}

/**
 * Fetch the cross-project change-order pipeline stats.
 *
 * @example
 * ```tsx
 * const { data } = usePortfolioCO({ agingThresholdDays: 7 });
 * ```
 */
export function usePortfolioCO(params: UsePortfolioCOParams = {}) {
  const {
    asOf = null,
    branch = "main",
    agingThresholdDays = 7,
    enabled = true,
  } = params;

  return useQuery<ChangeOrderStatsResponse>({
    queryKey: queryKeys.portfolio.changeOrders({
      asOf,
      branch,
      agingThresholdDays,
    }),
    queryFn: async () => {
      const data = await __request(OpenAPI, {
        method: "GET",
        url: "/api/v1/change-orders/portfolio-stats",
        query: {
          branch,
          as_of: asOf ?? undefined,
          aging_threshold_days: agingThresholdDays,
        },
      });
      return transformCOStatsNumeric(data as ChangeOrderStatsResponse);
    },
    enabled,
  });
}
