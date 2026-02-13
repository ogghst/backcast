/**
 * Temporal/bitemporal utility functions for handling valid_time and transaction_time ranges.
 */

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

  const timestamp = rangeStr.slice(1, commaIndex).trim();

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

  const timestamp = rangeStr.slice(commaIndex + 1, -1).trim();

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

  const upperBound = rangeStr.slice(commaIndex + 1, -1).trim();

  // Empty or infinity means unbounded
  return !upperBound || upperBound === '-infinity' || upperBound === 'infinity';
}
