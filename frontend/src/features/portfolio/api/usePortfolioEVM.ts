/**
 * Portfolio EVM (cross-project roll-up) hook.
 *
 * Wraps `GET /api/v1/evm/portfolio` and coerces Decimal-serialized string
 * values to numbers on the summary + each project row (mirrors
 * `transformEVMMetricsResponse` from the EVM feature).
 *
 * Uses the GENERATED types (PortfolioEVMResponse, PortfolioProjectMetrics,
 * EVMMetricsResponse) directly — the portfolio summary carries TCPI which the
 * hand-written `src/features/evm/types.ts` does NOT define.
 */

import { useQuery } from "@tanstack/react-query";
import { OpenAPI } from "@/api/generated/core/OpenAPI";
import { request as __request } from "@/api/generated/core/request";
import { queryKeys } from "@/api/queryKeys";
import type { PortfolioEVMResponse } from "@/api/generated/models/PortfolioEVMResponse";
import type { PortfolioProjectMetrics } from "@/api/generated/models/PortfolioProjectMetrics";
import type { EVMMetricsResponse } from "@/api/generated/models/EVMMetricsResponse";

/** Decimal-serialized numeric fields that may arrive as strings. */
const SUMMARY_NUMERIC_FIELDS: ReadonlyArray<keyof EVMMetricsResponse> = [
  "bac",
  "pv",
  "ac",
  "ev",
  "cv",
  "sv",
  "cpi",
  "spi",
  "eac",
  "vac",
  "etc",
  "tcpi",
];

const PROJECT_NUMERIC_FIELDS: ReadonlyArray<keyof PortfolioProjectMetrics> = [
  "cpi",
  "spi",
  "vac",
  "contract_value",
  "bac",
  "eac",
  "delta_eac",
];

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
 * Transform the portfolio response: ensure every numeric field is a real
 * number (not a Decimal-serialized string) on both the summary and the
 * per-project rows.
 */
export function transformPortfolioNumeric(
  data: PortfolioEVMResponse,
): PortfolioEVMResponse {
  const summary = { ...data.summary };
  for (const field of SUMMARY_NUMERIC_FIELDS) {
    const v = summary[field];
    if (v !== undefined) {
      (summary as Record<string, unknown>)[field as string] = toNumber(v);
    }
  }

  const projects = data.projects.map((row) => {
    const transformed = { ...row };
    for (const field of PROJECT_NUMERIC_FIELDS) {
      const v = transformed[field];
      if (v !== undefined) {
        (transformed as Record<string, unknown>)[field as string] = toNumber(v);
      }
    }
    return transformed;
  });

  // at_risk_projects is a subset of `projects`; transform the same way.
  const atRiskProjects = data.at_risk_projects.map((row) => {
    const transformed = { ...row };
    for (const field of PROJECT_NUMERIC_FIELDS) {
      const v = transformed[field];
      if (v !== undefined) {
        (transformed as Record<string, unknown>)[field as string] = toNumber(v);
      }
    }
    return transformed;
  });

  return { ...data, summary, projects, at_risk_projects: atRiskProjects };
}

/** Parameters for {@link usePortfolioEVM}. */
export interface UsePortfolioEVMParams {
  /** EVM as-of (control) date; null/undefined = today. */
  controlDate?: string | null;
  /** Branch to query (default "main"). */
  branch?: string;
  /** Branch mode "isolated" | "merged" (default "merged"). */
  branchMode?: string;
  /** TanStack Query enabled flag. */
  enabled?: boolean;
}

/**
 * Fetch the rolled-up portfolio EVM response.
 *
 * @example
 * ```tsx
 * const { data, isLoading } = usePortfolioEVM({ branchMode: "merged" });
 * ```
 */
export function usePortfolioEVM(params: UsePortfolioEVMParams = {}) {
  const {
    controlDate = null,
    branch = "main",
    branchMode = "merged",
    enabled = true,
  } = params;

  return useQuery<PortfolioEVMResponse>({
    queryKey: queryKeys.portfolio.evm({ controlDate, branch, branchMode }),
    queryFn: async () => {
      const data = await __request(OpenAPI, {
        method: "GET",
        url: "/api/v1/evm/portfolio",
        query: {
          control_date: controlDate ?? undefined,
          branch,
          branch_mode: branchMode,
        },
      });
      return transformPortfolioNumeric(data as PortfolioEVMResponse);
    },
    enabled,
  });
}
