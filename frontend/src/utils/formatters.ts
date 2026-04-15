/**
 * Unified formatting utilities for the Backcast frontend.
 *
 * This module provides consistent, locale-aware formatting for dates, times,
 * currency, and other display values. It consolidates functionality from:
 * - components/explorer/shared/formatters.ts (currency, duration)
 * - utils/localeDate.ts (locale-aware date formatting)
 *
 * ## Usage
 *
 * ### Simple formatting (most use cases)
 * ```ts
 * import { formatDate, formatDateTime, formatCurrency } from '@/utils/formatters';
 *
 * formatDate(date)           // "Jan 15, 2026" (browser locale)
 * formatDateTime(timestamp)  // "Jan 15, 2026, 10:30 AM"
 * formatCurrency(1234.56)    // "€1,234.56"
 * ```
 *
 * ### Hook-based (for performance-sensitive components)
 * ```ts
 * import { useDateFormatter } from '@/utils/formatters';
 *
 * function MyComponent({ date }) {
 *   const formatDate = useDateFormatter();
 *   return <span>{formatDate(date)}</span>;
 * }
 * ```
 *
 * ### Advanced options
 * ```ts
 * formatDate(date, { style: "short" })              // "1/15/26"
 * formatDate(date, { locale: "it-IT", style: "long" }) // "15 gennaio 2026"
 * formatTemporalRange(temporalData)                // "Jan 15, 2026 – Present"
 * ```
 */

import { useMemo } from "react";

// ============================================================================
// Types
// ============================================================================

/** Date format style for locale-aware formatting. */
export type DateFormatStyle = "short" | "medium" | "long" | "full";

/** Options for date formatting. */
export interface FormatDateOptions {
  /** Date format style (default: "medium") */
  style?: DateFormatStyle;
  /** Locale to use (default: browser locale) */
  locale?: string;
  /** Fallback string if date is invalid (default: "Unknown") */
  fallback?: string;
}

// ============================================================================
// Simple Formatters (for most use cases)
// ============================================================================

/**
 * Format a date using browser locale.
 *
 * @param dateValue - Date value (ISO string, Date object, or null)
 * @param options - Formatting options
 * @returns Formatted date string (e.g., "Jan 15, 2026")
 *
 * @example
 * formatDate("2026-01-15T10:00:00+00:00")           // "Jan 15, 2026"
 * formatDate("2026-01-15T10:00:00+00:00", { style: "short" })  // "1/15/26"
 * formatDate(null)                                  // "Unknown"
 */
export function formatDate(
  dateValue: string | Date | null | undefined,
  options: FormatDateOptions = {}
): string {
  const { style = "medium", locale = undefined, fallback = "Unknown" } = options;

  if (!dateValue) {
    return fallback;
  }

  try {
    const date = typeof dateValue === "string" ? new Date(dateValue) : dateValue;
    if (isNaN(date.getTime())) {
      return fallback;
    }
    return date.toLocaleDateString(locale, { dateStyle: style });
  } catch {
    return fallback;
  }
}

/**
 * Format a date and time using browser locale.
 *
 * @param dateValue - Date value from backend
 * @param options - Formatting options
 * @returns Formatted datetime string (e.g., "Jan 15, 2026, 10:30 AM")
 */
export function formatDateTime(
  dateValue: string | Date | null | undefined,
  options: FormatDateOptions = {}
): string {
  const { style = "medium", locale = undefined, fallback = "Unknown" } = options;

  if (!dateValue) {
    return fallback;
  }

  try {
    const date = typeof dateValue === "string" ? new Date(dateValue) : dateValue;
    if (isNaN(date.getTime())) {
      return fallback;
    }
    return date.toLocaleString(locale, {
      dateStyle: style,
      timeStyle: "short",
    });
  } catch {
    return fallback;
  }
}

/**
 * Format a time value using browser locale.
 *
 * @param dateValue - Date value from backend
 * @param options - Formatting options
 * @returns Formatted time string (e.g., "10:30 AM")
 */
export function formatTime(
  dateValue: string | Date | null | undefined,
  options: FormatDateOptions = {}
): string {
  const { locale = undefined, fallback = "Unknown" } = options;

  if (!dateValue) {
    return fallback;
  }

  try {
    const date = typeof dateValue === "string" ? new Date(dateValue) : dateValue;
    if (isNaN(date.getTime())) {
      return fallback;
    }
    return date.toLocaleTimeString(locale, {
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return fallback;
  }
}

/**
 * Format a temporal range from backend formatted response.
 *
 * Backend temporal responses include:
 * - lower: ISO timestamp
 * - upper: ISO timestamp or null (if unbounded)
 * - lower_formatted: Pre-formatted display string
 * - upper_formatted: "Present" or formatted upper date
 * - is_currently_valid: Boolean
 *
 * @param temporalData - Temporal range data from backend API
 * @param options - Formatting options
 * @returns Formatted range string (e.g., "Jan 15, 2026 – Present")
 *
 * @example
 * formatTemporalRange({
 *   lower: "2026-01-15T10:00:00+00:00",
 *   upper: null,
 *   is_currently_valid: true
 * }) // "Jan 15, 2026 – Present"
 */
export function formatTemporalRange(
  temporalData: {
    lower?: string | null;
    upper?: string | null;
    lower_formatted?: string;
    upper_formatted?: string;
    is_currently_valid?: boolean;
  } | null | undefined,
  options: FormatDateOptions = {}
): string {
  if (!temporalData) {
    return options.fallback || "Unknown";
  }

  const { style = "medium", locale = undefined } = options;

  const lowerFormatted = temporalData.lower
    ? formatDate(temporalData.lower, { style, locale, fallback: "Unknown" })
    : "Unknown";

  const upperFormatted = temporalData.is_currently_valid || !temporalData.upper
    ? "Present"
    : formatDate(temporalData.upper, { style, locale, fallback: "Unknown" });

  return `${lowerFormatted} – ${upperFormatted}`;
}

// ============================================================================
// Hook-based Formatters (for performance-sensitive components)
// ============================================================================

/**
 * Hook for memoized date formatting.
 *
 * Use this in components that render dates frequently to avoid
 * re-formatting on every render.
 *
 * @param options - Formatting options (stable reference)
 * @returns Memoized date formatter function
 *
 * @example
 * function MyComponent({ date }) {
 *   const formatDate = useDateFormatter();
 *   return <span>{formatDate(date)}</span>;
 * }
 */
export function useDateFormatter(options: FormatDateOptions = {}) {
  const { style = "medium", locale = undefined, fallback = "Unknown" } = options;

  return useMemo(
    () => (dateValue: string | Date | null | undefined) =>
      formatDate(dateValue, { style, locale, fallback }),
    [style, locale, fallback]
  );
}

/**
 * Hook for memoized datetime formatting.
 *
 * @param options - Formatting options (stable reference)
 * @returns Memoized datetime formatter function
 */
export function useDateTimeFormatter(options: FormatDateOptions = {}) {
  const { style = "medium", locale = undefined, fallback = "Unknown" } = options;

  return useMemo(
    () => (dateValue: string | Date | null | undefined) =>
      formatDateTime(dateValue, { style, locale, fallback }),
    [style, locale, fallback]
  );
}

// ============================================================================
// Currency & Number Formatters
// ============================================================================

/** Currency formatter instance (EUR). */
const currencyFormatter = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "EUR",
});

/**
 * Format a value as EUR currency.
 *
 * @param value - Numeric value to format
 * @returns Formatted currency string (e.g., "€1,234.56")
 *
 * @example
 * formatCurrency(1234.56)  // "€1,234.56"
 * formatCurrency(null)     // "-"
 */
export function formatCurrency(value: string | number | null | undefined): string {
  if (!value) return "-";
  return currencyFormatter.format(Number(value));
}

/**
 * Format a value as compact currency (K/M suffixes).
 *
 * @param value - Numeric value to format
 * @returns Formatted compact currency string (e.g., "€1.2M", "€345K")
 */
export function formatCompactCurrency(
  value: string | number | null | undefined
): string {
  if (value === null || value === undefined) return "--";
  const num = Number(value);
  if (isNaN(num)) return "--";

  const sign = num < 0 ? "-" : "";
  const abs = Math.abs(num);

  if (abs >= 1_000_000) return `${sign}€${(abs / 1_000_000).toFixed(1)}M`;
  if (abs >= 1_000) return `${sign}€${(abs / 1_000).toFixed(1)}K`;
  return `${sign}€${abs.toFixed(0)}`;
}

// ============================================================================
// Duration & Helper Formatters
// ============================================================================

/**
 * Calculate the duration between two dates in days.
 *
 * @param start - Start date string
 * @param end - End date string
 * @returns Duration string (e.g., "30 days") or null if either date is missing
 */
export function calculateDuration(
  start: string | null | undefined,
  end: string | null | undefined
): string | null {
  if (!start || !end) return null;

  const days = Math.ceil(
    (new Date(end).getTime() - new Date(start).getTime()) / (1000 * 60 * 60 * 24)
  );
  return `${Math.abs(days)} day${Math.abs(days) !== 1 ? "s" : ""}`;
}

/**
 * Get the user's browser locale.
 *
 * @returns Browser locale string (e.g., "en-US", "it-IT")
 */
export function getBrowserLocale(): string {
  return navigator.language || "en-US";
}
