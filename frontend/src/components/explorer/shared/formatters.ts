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
