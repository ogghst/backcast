/**
 * Temporal/bitemporal utility functions for handling valid_time and transaction_time ranges.
 *
 * @deprecated This module is deprecated. Use @/utils/localeDate for locale-aware date formatting.
 *
 * The backend now provides pre-formatted temporal data via computed fields:
 * - valid_time_formatted.lower_formatted
 * - transaction_time_formatted.lower_formatted
 *
 * For locale-aware formatting of backend dates, use:
 * - formatLocaleDate() - Format dates using browser locale
 * - formatLocaleDateTime() - Format datetimes using browser locale
 * - formatLocaleTemporalRange() - Format temporal ranges using browser locale
 *
 * This file is kept for backward compatibility during the migration period.
 */

/**
 * Type for temporal range values that can be either a string (PostgreSQL range)
 * or an object with start/lower properties (from some API responses).
 */
export type TemporalRange = string | { start?: string; lower?: string } | null | undefined;

/**
 * Date format style for locale-aware formatting.
 */
export type DateFormatStyle = "short" | "medium" | "long" | "full";

/**
 * Parse a temporal range value (string or object) and return the lower bound as a Date.
 *
 * @param range - Temporal range string (e.g., "[2026-01-15 10:00:00+00,)") or object with start/lower
 * @returns Date object representing the lower bound, or null if parsing fails
 *
 * @example
 * ```ts
 * parseTemporalRangeLowerBound("[2026-01-15 10:00:00+00,)") // => Date("2026-01-15T10:00:00+00:00")
 * parseTemporalRangeLowerBound({ start: "2026-01-15T10:00:00Z" }) // => Date("2026-01-15T10:00:00+00:00")
 * parseTemporalRangeLowerBound(null) // => null
 * ```
 */
export function parseTemporalRangeLowerBound(range: TemporalRange): Date | null {
  if (!range) return null;

  // Handle object format { start: string } or { lower: string }
  if (typeof range === "object") {
    const timestamp = range.start || range.lower;
    if (!timestamp) return null;
    const date = new Date(timestamp);
    return isNaN(date.getTime()) ? null : date;
  }

  // Handle string format (PostgreSQL range)
  return parseRangeLowerBound(range);
}

/**
 * Parse a PostgreSQL range string (e.g., "[2026-01-15 10:00:00+00,)")
 * and return the lower bound (start) timestamp as a Date.
 *
 * Range format: `[lower,upper)` where:
 * - `[` or `]` = inclusive bound
 * - `(` or `)` = exclusive bound
 * - Empty string for unbounded (e.g., ")" means infinity)
 *
 * @param rangeStr - PostgreSQL range string (e.g., "[2026-01-15 10:00:00+00,)")
 * @returns Date object representing the lower bound, or null if parsing fails
 *
 * @example
 * ```ts
 * parseRangeLowerBound("[2026-01-15 10:00:00+00,)") // => Date("2026-01-15T10:00:00+00:00")
 * parseRangeLowerBound(null) // => null
 * ```
 */
export function parseRangeLowerBound(rangeStr: string | null | undefined): Date | null {
  if (!rangeStr) return null;

  // PostgreSQL range format: "[lower,upper)" or "(lower,upper]"
  // Extract the timestamp between the opening bracket and the comma
  const commaIndex = rangeStr.indexOf(',');

  if (commaIndex === -1) return null;

  let timestamp = rangeStr.slice(1, commaIndex).trim();

  // Remove escaped quotes if present (JSON serialization of PostgreSQL ranges)
  timestamp = timestamp.replace(/\\"/g, '');

  // Check for infinity
  if (timestamp === '-infinity' || timestamp === 'infinity') {
    return null;
  }

  const date = new Date(timestamp);
  return isNaN(date.getTime()) ? null : date;
}

/**
 * Parse a PostgreSQL range string and return the upper bound (end) timestamp as a Date.
 *
 * @param rangeStr - PostgreSQL range string (e.g., "[2026-01-15 10:00:00,)")
 * @returns Date object representing the upper bound, or null if unbounded or parsing fails
 *
 * @example
 * ```ts
 * parseRangeUpperBound("[2026-01-15 10:00:00,2026-02-15 10:00:00+00)") // => Date("2026-02-15T10:00:00+00:00")
 * parseRangeUpperBound("[2026-01-15 10:00:00,)") // => null (unbounded)
 * ```
 */
export function parseRangeUpperBound(rangeStr: string | null | undefined): Date | null {
  if (!rangeStr) return null;

  // PostgreSQL range format: "[lower,upper)" or "(lower,upper]"
  // Extract the timestamp between the comma and the closing bracket
  const commaIndex = rangeStr.indexOf(',');

  if (commaIndex === -1) return null;

  let timestamp = rangeStr.slice(commaIndex + 1, -1).trim();

  // Remove escaped quotes if present (JSON serialization of PostgreSQL ranges)
  timestamp = timestamp.replace(/\\"/g, '');

  // Check for empty (unbounded) or infinity
  if (!timestamp || timestamp === '-infinity' || timestamp === 'infinity') {
    return null; // Unbounded upper bound
  }

  const date = new Date(timestamp);
  return isNaN(date.getTime()) ? null : date;
}

/**
 * Check if a range string has an unbounded upper bound (i.e., is currently valid).
 *
 * @param rangeStr - PostgreSQL range string (e.g., "[2026-01-15 10:00:00,)")
 * @returns true if the upper bound is unbounded (currently valid), false otherwise
 *
 * @example
 * ```ts
 * isRangeUnbounded("[2026-01-15 10:00:00,)") // => true
 * isRangeUnbounded("[2026-01-15 10:00:00,2026-02-15 10:00:00)") // => false
 * ```
 */
export function isRangeUnbounded(rangeStr: string | null | undefined): boolean {
  if (!rangeStr) return false;
  const commaIndex = rangeStr.indexOf(',');

  if (commaIndex === -1) return false;

  let upperBound = rangeStr.slice(commaIndex + 1, -1).trim();

  // Remove escaped quotes if present (JSON serialization of PostgreSQL ranges)
  upperBound = upperBound.replace(/\\"/g, '');

  // Empty or infinity means unbounded
  return !upperBound || upperBound === '-infinity' || upperBound === 'infinity';
}

/**
 * Format a temporal range for display as a locale-aware date string.
 * Handles both valid_time and transaction_time ranges in string or object format.
 * Uses the browser's locale settings for automatic formatting.
 *
 * @param range - Temporal range string or object
 * @param style - Date format style (default: "medium")
 * @returns Formatted date string using browser locale, or "Unknown" if parsing fails
 *
 * @example
 * ```ts
 * formatTemporalDate("[2026-01-15 10:00:00+00,)") // => "Jan 15, 2026" (en-US locale)
 * formatTemporalDate("[2026-01-15 10:00:00+00,)", "short") // => "1/15/26" (en-US locale)
 * formatTemporalDate("[2026-01-15 10:00:00+00,)", "long") // => "January 15, 2026" (en-US locale)
 * formatTemporalDate(null) // => "Unknown"
 * ```
 */
export function formatTemporalDate(
  range: TemporalRange,
  style: DateFormatStyle = "medium"
): string {
  const date = parseTemporalRangeLowerBound(range);
  if (!date) return "Unknown";

  // Use locale-aware formatting with the browser's default locale
  return date.toLocaleDateString(undefined, { dateStyle: style });
}

/**
 * Format a temporal range for display as a locale-aware date string with time.
 * Includes both date and time portions.
 *
 * @param range - Temporal range string or object
 * @param style - Date format style (default: "medium")
 * @returns Formatted datetime string using browser locale, or "Unknown" if parsing fails
 *
 * @example
 * ```ts
 * formatTemporalDateTime("[2026-01-15 10:30:00+00,)") // => "Jan 15, 2026, 10:30 AM" (en-US locale)
 * formatTemporalDateTime("[2026-01-15 10:30:00+00,)", "short") // => "1/15/26, 10:30 AM" (en-US locale)
 * formatTemporalDateTime(null) // => "Unknown"
 * ```
 */
export function formatTemporalDateTime(
  range: TemporalRange,
  style: DateFormatStyle = "medium"
): string {
  const date = parseTemporalRangeLowerBound(range);
  if (!date) return "Unknown";

  // Use locale-aware formatting with date and time
  return date.toLocaleString(undefined, {
    dateStyle: style,
    timeStyle: "short"
  });
}

/**
 * Format a PostgreSQL range string for display as a locale-aware date label.
 * Handles both valid_time and transaction_time ranges.
 *
 * @param rangeStr - PostgreSQL range string (e.g., "[2026-01-15 10:00:00+00,)")
 * @param style - Date format style (default: "medium")
 * @returns Formatted date string using browser locale, or "Unknown" if parsing fails
 *
 * @example
 * ```ts
 * formatRangeDate("[2026-01-15 10:00:00+00,)") // => "Jan 15, 2026" (en-US locale)
 * formatRangeDate("[2026-01-15 10:00:00+00,)", "short") // => "1/15/26" (en-US locale)
 * formatRangeDate(null) // => "Unknown"
 * ```
 */
export function formatRangeDate(
  rangeStr: string | null | undefined,
  style: DateFormatStyle = "medium"
): string {
  return formatTemporalDate(rangeStr, style);
}
