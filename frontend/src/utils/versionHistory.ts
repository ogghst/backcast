/**
 * Shared utilities for version history mapping across entity tabs.
 *
 * This module provides functions to transform API history responses into
 * the format expected by VersionHistoryDrawer, eliminating code duplication
 * across CostRegistrationsTab, ProgressEntriesTab, and other entity tabs.
 */

import type { TemporalRange } from "@/components/common/VersionHistory";

/**
 * History item type from API responses.
 *
 * API responses vary in structure:
 * - Some have valid_from as a direct string
 * - Some have valid_time as a string or { lower: string }
 * - Some have transaction_time as a string or { lower: string }
 */
type ApiHistoryItem = {
  valid_from?: string;
  valid_time?: string | TemporalRange | { lower: string; start?: string };
  transaction_time?: string | TemporalRange | { lower: string; start?: string };
  created_by_name?: string;
  [key: string]: unknown; // Allow additional entity-specific fields
};

/**
 * Map API history versions to VersionHistoryDrawer format.
 *
 * Handles variations in API response structures:
 * - String vs object temporal fields
 * - Different field names (valid_from vs valid_time)
 * - Missing or null values
 *
 * @param versions - Array of history versions from API
 * @returns Array of mapped versions for VersionHistoryDrawer
 *
 * @example
 * const versions = mapHistoryVersions(apiHistory);
 * // Returns: [{ id: "v1", valid_from: "...", transaction_time: "...", ... }]
 */
export function mapHistoryVersions(
  versions: unknown[] | undefined
): Array<{
  id: string;
  valid_from: string;
  transaction_time: string;
  valid_to: string | null;
  changed_by: string;
}> {
  if (!versions || versions.length === 0) {
    return [];
  }

  return versions.map((version, idx, arr) => {
    const v = version as ApiHistoryItem;

    return {
      id: `v${arr.length - idx}`,
      valid_from: extractValidFrom(v),
      transaction_time: extractTransactionTime(v),
      valid_to: null,
      changed_by: v.created_by_name || "System",
    };
  });
}

/**
 * Extract valid_from from history item variations.
 */
function extractValidFrom(item: ApiHistoryItem): string {
  // Direct valid_from field
  if (item.valid_from) {
    return item.valid_from;
  }

  // valid_time field (string or object)
  if (item.valid_time) {
    if (typeof item.valid_time === "string") {
      return item.valid_time;
    }
    if (typeof item.valid_time === "object" && "lower" in item.valid_time) {
      return item.valid_time.lower || "";
    }
  }

  return "";
}

/**
 * Extract transaction_time from history item variations.
 */
function extractTransactionTime(item: ApiHistoryItem): string {
  if (!item.transaction_time) {
    return "";
  }

  if (typeof item.transaction_time === "string") {
    return item.transaction_time;
  }

  if (typeof item.transaction_time === "object" && "lower" in item.transaction_time) {
    return item.transaction_time.lower || "";
  }

  return "";
}
