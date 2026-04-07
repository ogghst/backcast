/**
 * Shared Formatter Utilities
 *
 * Common formatting functions extracted from explorer detail cards.
 * Shared across ProjectDetailCards, WBEDetailCards, and CostElementDetailCards.
 *
 * @module components/explorer/shared/formatters
 */

const currencyFormatter = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "EUR",
});

export const formatCurrency = (v: string | number | null | undefined) =>
  !v ? "-" : currencyFormatter.format(Number(v));

export const formatCompactCurrency = (
  v: string | number | null | undefined,
): string => {
  if (v === null || v === undefined) return "--";
  const num = Number(v);
  if (isNaN(num)) return "--";
  const sign = num < 0 ? "-" : "";
  const abs = Math.abs(num);
  if (abs >= 1_000_000) return `${sign}€${(abs / 1_000_000).toFixed(1)}M`;
  if (abs >= 1_000) return `${sign}€${(abs / 1_000).toFixed(1)}K`;
  return `${sign}€${abs.toFixed(0)}`;
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
