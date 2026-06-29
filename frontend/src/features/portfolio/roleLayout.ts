/**
 * Role-curated layout config for the Portfolio Dashboard.
 *
 * Phase 2 of the functional-dashboards initiative: the same PortfolioPage is
 * rearranged per role so a cost-controller lands on cost-distress first while a
 * PMO director lands on schedule risk first. Only the title, lead metric tiles,
 * default table sort, and section ordering are role-driven — the FilterBar, the
 * data sources, and every individual section's behavior are unchanged.
 *
 * Layouts (approved):
 *   default          → CPI/SPI/VAC/TCPI; kpis→coPipeline→table→atRisk
 *   cost-controller  → CPI + Cost Distress; CPI asc; kpis→costDistress→table→coPipeline→atRisk
 *   pmo-director     → SPI + At-Risk; SPI asc; kpis→atRisk→table→coPipeline
 */

import type { PortfolioProjectMetrics } from "@/api/generated/models/PortfolioProjectMetrics";

/** Keys for the metric tiles shown as the prominent lead row. */
export type LeadMetric = "cpi" | "spi" | "vac" | "tcpi";

/** Section keys rendered in `sectionOrder`. */
export type SectionKey =
  | "kpis"
  | "costDistress"
  | "atRisk"
  | "coPipeline"
  | "table";

/** Antd SorterResult order string for the role default table sort. */
export type SortOrder = "ascend" | "descend";

export interface DefaultSort {
  field: keyof PortfolioProjectMetrics;
  order: SortOrder;
}

export interface LayoutConfig {
  /** Page heading. */
  title: string;
  /**
   * Lead metric tiles (KPI tiles). The at-risk / cost-distress counts are
   * derived client-side from the portfolio breakdown and rendered alongside
   * whichever single index the role leads with.
   */
  leadMetrics: LeadMetric[];
  /**
   * When `true`, render the derived count tile next to the lead metric:
   *  - cost-controller → Cost Distress (CPI<0.9) count
   *  - pmo-director    → At-Risk (SPI<0.9) count
   */
  leadDistressCount?: "cost" | "schedule";
  /** Initial table sort; URL-persisted sort always wins over this. */
  defaultSort?: DefaultSort;
  /** Ordered section keys driving render order on the page. */
  sectionOrder: SectionKey[];
  /**
   * Optional column keys to emphasize (render first) in the per-project table.
   * Kept for forward-compat; v1 leaves column order untouched.
   */
  emphasizedColumns?: (keyof PortfolioProjectMetrics)[];
}

export const roleLayout: Record<string, LayoutConfig> = {
  default: {
    title: "Portfolio Dashboard",
    leadMetrics: ["cpi", "spi", "vac", "tcpi"],
    sectionOrder: ["kpis", "coPipeline", "table", "atRisk"],
  },

  "cost-controller": {
    title: "Cost Controlling",
    leadMetrics: ["cpi"],
    leadDistressCount: "cost",
    defaultSort: { field: "cpi", order: "ascend" },
    sectionOrder: ["kpis", "costDistress", "table", "coPipeline", "atRisk"],
    emphasizedColumns: ["cpi"],
  },

  "pmo-director": {
    title: "PMO / Schedule Governance",
    leadMetrics: ["spi"],
    leadDistressCount: "schedule",
    defaultSort: { field: "spi", order: "ascend" },
    sectionOrder: ["kpis", "atRisk", "table", "coPipeline"],
    emphasizedColumns: ["spi"],
  },
};
