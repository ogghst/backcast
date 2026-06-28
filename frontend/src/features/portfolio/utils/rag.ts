/**
 * RAG (Red/Amber/Green) bucketing for portfolio performance indices.
 *
 * Locked decision (functional-analysis.md §13) — IDENTICAL bands for CPI & SPI:
 *   - Green  : index >= 1.0
 *   - Amber  : 0.9 <= index < 1.0   (i.e. [0.9, 1.0))
 *   - Red    : index < 0.9
 *
 * A project's overall RAG = the WORSE band of its CPI band and SPI band
 * (Red > Amber > Green). When both indices are null the project is "Unknown".
 *
 * NOTE: the server does NOT filter or compute RAG; this is a client-side
 * concern (see PortfolioPage filtering + KPI status derivation).
 */

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
