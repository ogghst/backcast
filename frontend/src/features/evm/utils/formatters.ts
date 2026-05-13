/**
 * Shared value formatters for EVM metrics.
 *
 * @module features/evm/utils/formatters
 */

/**
 * Format a numeric value based on the format type.
 *
 * @param value - The numeric value to format (can be null)
 * @param format - The format type (currency, percentage, or number)
 * @returns Formatted string representation of the value
 */
export const formatValue = (
  value: number | null,
  format: "currency" | "percentage" | "number",
): string => {
  if (value === null || value === undefined) return "N/A";

  switch (format) {
    case "currency":
      return new Intl.NumberFormat("en-IE", {
        style: "currency",
        currency: "EUR",
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      }).format(value);

    case "percentage":
      return new Intl.NumberFormat("en-IE", {
        style: "percent",
        minimumFractionDigits: 0,
        maximumFractionDigits: 0,
      }).format(value);

    case "number":
      return new Intl.NumberFormat("en-IE", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      }).format(value);

    default:
      return String(value);
  }
};
