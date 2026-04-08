/**
 * Build a standardized export filename.
 * Format: {widgetType}-{dashboardName}-{ISO-timestamp}.{ext}
 */
export function buildExportFilename(
  widgetType: string,
  dashboardName: string,
  extension: string,
): string {
  const ts = new Date().toISOString().replace(/[:.]/g, "-");
  return `${widgetType}-${dashboardName}-${ts}.${extension}`;
}

/**
 * Export an ECharts instance as PNG using getDataURL().
 * Follows the pattern from EChartsTimeSeries.tsx.
 */
export function exportChartAsPNG(
  chartInstance: {
    getDataURL: (opts: {
      type: string;
      pixelRatio: number;
      backgroundColor: string;
    }) => string;
  },
  filename: string,
): void {
  const url = chartInstance.getDataURL({
    type: "png",
    pixelRatio: 2,
    backgroundColor: "#fff",
  });
  triggerDownload(url, filename);
}

/**
 * Export tabular data as CSV (RFC 4180 compliant).
 */
export function exportTableAsCSV(
  columns: string[],
  rows: string[][],
  filename: string,
): void {
  const csvContent = [
    columns.map(escapeCSV).join(","),
    ...rows.map((row) => row.map(escapeCSV).join(",")),
  ].join("\n");

  const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  triggerDownload(url, filename);
  URL.revokeObjectURL(url);
}

/**
 * Export raw data as formatted JSON.
 */
export function exportJSON(data: unknown, filename: string): void {
  const jsonContent = JSON.stringify(data, null, 2);
  const blob = new Blob([jsonContent], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  triggerDownload(url, filename);
  URL.revokeObjectURL(url);
}

/** Escape a CSV value per RFC 4180 */
function escapeCSV(value: string): string {
  const str = String(value ?? "");
  if (str.includes(",") || str.includes('"') || str.includes("\n")) {
    return `"${str.replace(/"/g, '""')}"`;
  }
  return str;
}

/** Trigger a file download via a temporary anchor element */
function triggerDownload(url: string, filename: string): void {
  const link = document.createElement("a");
  link.download = filename;
  link.href = url;
  link.click();
}
