/**
 * Shared Formatter Utilities
 *
 * @deprecated This module is deprecated. Use @/utils/formatters instead.
 *
 * The new unified utility provides:
 * - Better locale awareness
 * - Hook-based formatters for performance
 * - Consistent API across all formatting needs
 * - TypeScript types and JSDoc documentation
 *
 * Migration guide:
 * - formatDate() → formatDate() from @/utils/formatters (same signature)
 * - formatTimestamp() → formatDateTime() from @/utils/formatters
 * - formatCurrency() → formatCurrency() from @/utils/formatters (same signature)
 *
 * This file is kept for backward compatibility during migration.
 *
 * @module components/explorer/shared/formatters
 */

/**
 * Get the currency symbol for an ISO 4217 currency code.
 */
function getCurrencySymbol(currency: string = "EUR"): string {
  try {
    const parts = new Intl.NumberFormat("en-US", {
      style: "currency",
      currency,
    }).formatToParts(0);
    return parts.find((p) => p.type === "currency")?.value ?? currency;
  } catch {
    return currency;
  }
}

export const formatCurrency = (
  v: string | number | null | undefined,
  currency: string = "EUR",
) => {
  if (!v) return "-";
  try {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency,
    }).format(Number(v));
  } catch {
    return `${currency}${Number(v)}`;
  }
};

export const formatCompactCurrency = (
  v: string | number | null | undefined,
  currency: string = "EUR",
): string => {
  if (v === null || v === undefined) return "--";
  const num = Number(v);
  if (isNaN(num)) return "--";
  const sign = num < 0 ? "-" : "";
  const abs = Math.abs(num);
  const symbol = getCurrencySymbol(currency);
  if (abs >= 1_000_000) return `${sign}${symbol}${(abs / 1_000_000).toFixed(1)}M`;
  if (abs >= 1_000) return `${sign}${symbol}${(abs / 1_000).toFixed(1)}K`;
  return `${sign}${symbol}${abs.toFixed(0)}`;
};

export const formatDate = (d: string | null | undefined) =>
  !d ? "-" : new Date(d).toLocaleDateString();

export const formatTimestamp = (t: string | null | undefined) =>
  !t ? "-" : new Date(t).toLocaleString();

export const calculateDuration = (
  s: string | null | undefined,
  e: string | null | undefined,
) => {
  if (!s || !e) return null;
  const days = Math.ceil(
    (new Date(e).getTime() - new Date(s).getTime()) / (1000 * 60 * 60 * 24),
  );
  return `${Math.abs(days)} day${Math.abs(days) !== 1 ? "s" : ""}`;
};
