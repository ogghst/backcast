/**
 * Shared portfolio-widget metrics + RAG banding + cost-distress helpers.
 *
 * Extracted (Phase 3 of the global-dashboard-widgets initiative) from the
 * legacy portfolio page / roleLayout / rag.ts so it SURVIVES the Phase-10
 * portfolio retirement (which deletes the portfolio tree) and the Phase-4
 * portfolio widgets can import these helpers from a stable, co-located home.
 *
 * This module is the canonical source. The legacy files (until deleted in
 * Phase 10) re-export from here; do NOT import rag/cpiCostDistress/MetricMetadata
 * blocks from anywhere else.
 *
 * Source design: docs/03-project-plan/iterations/2026-06-29-global-dashboard-widgets/
 *   global-dashboard-widgets-design.md §7 Phase 3 + gap G12.
 */

import { MetricCategory, type MetricMetadata } from "@/features/evm/types";
import type { PortfolioProjectMetrics } from "@/api/generated/models/PortfolioProjectMetrics";

// ── KPI metadata (portfolio-level — not coupled to a project) ───────────────
// CPI/SPI/VAC `key` values ARE valid keyof EVMMetricsResponse, so the literals
// satisfy MetricMetadata directly. TCPI is NOT in the hand-written EVM type
// (only the generated one carries it); its `key` needs the documented double
// cast. The field is only used for a11y IDs in MetricCard.

const CPI_METADATA: MetricMetadata = {
  key: "cpi",
  name: "Portfolio CPI",
  description:
    "Cost Performance Index (EV / AC) rolled up across the portfolio. < 1.0 = over budget.",
  category: MetricCategory.PERFORMANCE,
  targetRanges: { min: 0, max: 2, good: 1.0 },
  higherIsBetter: true,
  format: "number",
};

const SPI_METADATA: MetricMetadata = {
  key: "spi",
  name: "Portfolio SPI",
  description:
    "Schedule Performance Index (EV / PV) rolled up across the portfolio. < 1.0 = behind schedule.",
  category: MetricCategory.SCHEDULE,
  targetRanges: { min: 0, max: 2, good: 1.0 },
  higherIsBetter: true,
  format: "number",
};

const VAC_METADATA: MetricMetadata = {
  key: "vac",
  name: "Portfolio VAC",
  description:
    "Variance at Completion (BAC − EAC) in portfolio base currency. Negative = over budget at completion.",
  category: MetricCategory.FORECAST,
  targetRanges: { min: -Infinity, max: Infinity, good: 0 },
  higherIsBetter: true,
  format: "currency",
};

const TCPI_METADATA = {
  key: "tcpi",
  name: "Portfolio TCPI",
  description:
    "To-Complete Performance Index (BAC / EAC). >= 1.0 = on track for the EAC budget; < 1.0 = remaining work must be done more cheaply.",
  category: MetricCategory.PERFORMANCE,
  targetRanges: { min: 0, max: 2, good: 1.0 },
  higherIsBetter: true,
  format: "number",
} as unknown as MetricMetadata;

export { CPI_METADATA, SPI_METADATA, VAC_METADATA, TCPI_METADATA };

// ── RAG (Red/Amber/Green) banding ──────────────────────────────────────────
//
// Locked decision (functional-analysis.md §13) — IDENTICAL bands for CPI & SPI:
//   - Green  : index >= 1.0
//   - Amber  : 0.9 <= index < 1.0   (i.e. [0.9, 1.0))
//   - Red    : index < 0.9
//
// A project's overall RAG = the WORSE band of its CPI band and SPI band
// (Red > Amber > Green). When both indices are null the project is "Unknown".
//
// NOTE: the server does NOT filter or compute RAG; this is a client-side
// concern (see PortfolioPage filtering + KPI status derivation).

export type RagBand = "Green" | "Amber" | "Red" | "Unknown";

/**
 * Lower bound of the Red band. A performance index strictly below this value
 * is "Red"; at-or-above but below 1.0 is "Amber".
 *
 * Shared so the at-risk (SPI<0.9) and cost-distress (CPI<0.9) derivations do
 * not re-hardcode the threshold.
 */
export const RED_BAND_THRESHOLD = 0.9;

/** Order severity for picking the worse of two bands (higher = worse). */
const BAND_SEVERITY: Record<Exclude<RagBand, "Unknown">, number> = {
  Green: 0,
  Amber: 1,
  Red: 2,
};

/**
 * Bucket a single performance index (CPI or SPI) into a RAG band.
 * Returns "Unknown" when the index is null/undefined.
 */
export function indexBand(index: number | null | undefined): RagBand {
  if (index === null || index === undefined || Number.isNaN(index)) {
    return "Unknown";
  }
  if (index >= 1.0) return "Green";
  if (index >= RED_BAND_THRESHOLD) return "Amber";
  return "Red";
}

/**
 * Derive the project's overall RAG band from its CPI and SPI.
 *
 * The worse (most severe) of the two present bands wins. If only one index is
 * present, that band is used. If both are null, the band is "Unknown".
 */
export function ragBand(cpi: number | null, spi: number | null): RagBand {
  const cpiBand = indexBand(cpi);
  const spiBand = indexBand(spi);

  if (cpiBand === "Unknown" && spiBand === "Unknown") return "Unknown";
  if (cpiBand === "Unknown") return spiBand;
  if (spiBand === "Unknown") return cpiBand;

  return BAND_SEVERITY[cpiBand] >= BAND_SEVERITY[spiBand] ? cpiBand : spiBand;
}

/**
 * Map a RAG band onto the MetricCard `status` union.
 *
 * Green → good, Amber → warning, Red → bad. Unknown (insufficient data)
 * maps to warning so it is visually distinct from a healthy tile without
 * being flagged as a failure.
 */
export function ragToStatus(band: RagBand): "good" | "warning" | "bad" {
  switch (band) {
    case "Green":
      return "good";
    case "Amber":
      return "warning";
    case "Red":
      return "bad";
    case "Unknown":
      return "warning";
  }
}

// ── Cost-distress selector ─────────────────────────────────────────────────

/**
 * Projects in cost distress: CPI present and strictly below the Red-band
 * threshold (mirrors the SPI<0.9 at-risk derivation). Ranked CPI ascending so
 * the worst performers surface first.
 */
export function cpiCostDistress(
  projects: PortfolioProjectMetrics[],
): PortfolioProjectMetrics[] {
  return projects
    .filter((p) => p.cpi != null && p.cpi < RED_BAND_THRESHOLD)
    .sort((a, b) => (a.cpi ?? Infinity) - (b.cpi ?? Infinity));
}
