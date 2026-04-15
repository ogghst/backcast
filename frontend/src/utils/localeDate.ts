/**
 * Locale-aware date formatting utilities for frontend display.
 *
 * @deprecated This module is deprecated. Use @/utils/formatters instead.
 *
 * The new unified utility (@/utils/formatters) consolidates all date
 * formatting functionality into a single, consistent API:
 *
 * Migration guide:
 * - formatLocaleDate() → formatDate() from @/utils/formatters
 * - formatLocaleDateTime() → formatDateTime() from @/utils/formatters
 * - formatLocaleTime() → formatTime() from @/utils/formatters
 * - formatLocaleTemporalRange() → formatTemporalRange() from @/utils/formatters
 * - getBrowserLocale() → getBrowserLocale() from @/utils/formatters
 *
 * The new utility also provides hook-based formatters for performance:
 * - useDateFormatter() - Memoized date formatting
 * - useDateTimeFormatter() - Memoized datetime formatting
 *
 * This file is kept for backward compatibility during migration.
 *
 * ---
 *
 * Locale-aware date formatting utilities for frontend display.
 *
 * This module provides utilities to format backend-provided dates using
 * the browser's locale settings. The backend now provides pre-formatted
 * dates, but the frontend can optionally reformat them for better UX
 * based on user's browser locale.
 *
 * Backend provides:
 * - ISO timestamps (e.g., "2026-01-15T10:00:00+00:00")
 * - Pre-formatted display strings (e.g., "January 15, 2026")
 *
 * Frontend uses this utility to:
 * - Format using browser locale (e.g., "15 gen 2026" for IT locale)
 * - Provide consistent formatting across components
 * - Support different date styles (short, medium, long)
 */

/**
 * Date format style for locale-aware formatting.
 */
export type DateFormatStyle = "short" | "medium" | "long" | "full";

/**
 * Format options for date display.
 */
export interface FormatDateOptions {
  /** Date format style (default: "medium") */
  style?: DateFormatStyle;
  /** Locale to use (default: browser locale) */
  locale?: string;
  /** Fallback string if date is invalid (default: "Unknown") */
  fallback?: string;
}

/**
 * Format a date string or ISO timestamp using browser locale.
 *
 * This utility formats backend-provided dates for display using the
 * browser's locale settings, providing a better user experience.
 *
 * @param dateValue - Date value from backend (ISO string, Date object, or formatted string)
 * @param options - Formatting options
 * @returns Formatted date string using browser locale
 *
 * @example
 * ```ts
 * // Using backend ISO timestamp
 * formatLocaleDate("2026-01-15T10:00:00+00:00")
 * // → "Jan 15, 2026" (en-US locale)
 * // → "15 gen 2026" (it-IT locale)
 *
 * // Using backend pre-formatted string (fallback to parsing)
 * formatLocaleDate("January 15, 2026")
 * // → "Jan 15, 2026" (en-US locale)
 *
 * // With custom locale
 * formatLocaleDate("2026-01-15T10:00:00+00:00", { locale: "de-DE" })
 * // → "15. Jan. 2026"
 *
 * // With different style
 * formatLocaleDate("2026-01-15T10:00:00+00:00", { style: "long" })
 * // → "January 15, 2026"
 * ```
 */
export function formatLocaleDate(
  dateValue: string | Date | null | undefined,
  options: FormatDateOptions = {}
): string {
  const {
    style = "medium",
    locale = undefined, // Use browser default
    fallback = "Unknown",
  } = options;

  if (!dateValue) {
    return fallback;
  }

  try {
    // Convert to Date object
    const date =
      typeof dateValue === "string"
        ? new Date(dateValue)
        : dateValue;

    // Check if date is valid
    if (isNaN(date.getTime())) {
      return fallback;
    }

    // Format using browser locale
    return date.toLocaleDateString(locale, {
      dateStyle: style,
    });
  } catch {
    return fallback;
  }
}

/**
 * Format a date and time string using browser locale.
 *
 * @param dateValue - Date value from backend
 * @param options - Formatting options
 * @returns Formatted datetime string using browser locale
 *
 * @example
 * ```ts
 * formatLocaleDateTime("2026-01-15T10:30:00+00:00")
 * // → "Jan 15, 2026, 10:30 AM" (en-US)
 *
 * formatLocaleDateTime("2026-01-15T10:30:00+00:00", { locale: "it-IT" })
 * // → "15 gen 2026, 10:30"
 * ```
 */
export function formatLocaleDateTime(
  dateValue: string | Date | null | undefined,
  options: FormatDateOptions = {}
): string {
  const {
    style = "medium",
    locale = undefined,
    fallback = "Unknown",
  } = options;

  if (!dateValue) {
    return fallback;
  }

  try {
    const date =
      typeof dateValue === "string"
        ? new Date(dateValue)
        : dateValue;

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
 * Format a time string using browser locale.
 *
 * @param dateValue - Date value from backend
 * @param options - Formatting options
 * @returns Formatted time string using browser locale
 *
 * @example
 * ```ts
 * formatLocaleTime("2026-01-15T10:30:00+00:00")
 * // → "10:30 AM" (en-US)
 *
 * formatLocaleTime("2026-01-15T10:30:00+00:00", { locale: "it-IT" })
 * // → "10:30"
 * ```
 */
export function formatLocaleTime(
  dateValue: string | Date | null | undefined,
  options: FormatDateOptions = {}
): string {
  const {
    locale = undefined,
    fallback = "Unknown",
  } = options;

  if (!dateValue) {
    return fallback;
  }

  try {
    const date =
      typeof dateValue === "string"
        ? new Date(dateValue)
        : dateValue;

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
 * This utility formats the range using browser locale.
 *
 * @param temporalData - Temporal range data from backend API
 * @param options - Formatting options
 * @returns Formatted range string (e.g., "Jan 15, 2026 – Present")
 *
 * @example
 * ```ts
 * // Unbounded range (currently valid)
 * const temporalData = {
 *   lower: "2026-01-15T10:00:00+00:00",
 *   upper: null,
 *   lower_formatted: "January 15, 2026",
 *   upper_formatted: "Present",
 *   is_currently_valid: true
 * };
 *
 * formatLocaleTemporalRange(temporalData)
 * // → "Jan 15, 2026 – Present" (en-US)
 * // → "15 gen 2026 – Presente" (it-IT)
 *
 * // Bounded range (historical)
 * const historicalData = {
 *   lower: "2026-01-15T10:00:00+00:00",
 *   upper: "2026-02-15T10:00:00+00:00",
 *   lower_formatted: "January 15, 2026",
 *   upper_formatted: "February 15, 2026",
 *   is_currently_valid: false
 * };
 *
 * formatLocaleTemporalRange(historicalData)
 * // → "Jan 15, 2026 – Feb 15, 2026" (en-US)
 * ```
 */
export function formatLocaleTemporalRange(
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

  // Format lower bound using locale
  const lowerFormatted = temporalData.lower
    ? formatLocaleDate(temporalData.lower, { style, locale, fallback: "Unknown" })
    : "Unknown";

  // Format upper bound
  const upperFormatted = (() => {
    if (temporalData.is_currently_valid || !temporalData.upper) {
      // Unbounded or "Present"
      return locale === "it-IT" ? "Presente" : "Present";
    }
    return formatLocaleDate(temporalData.upper, { style, locale, fallback: "Unknown" });
  })();

  return `${lowerFormatted} – ${upperFormatted}`;
}

/**
 * Get the user's browser locale.
 *
 * @returns Browser locale string (e.g., "en-US", "it-IT")
 */
export function getBrowserLocale(): string {
  return navigator.language || "en-US";
}
