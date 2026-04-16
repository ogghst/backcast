import { theme } from "antd";
import type React from "react";
import type { EVMMetricsResponse, MetricKey } from "@/features/evm/types";
import { getMetricStatus } from "@/features/evm/types";
import { formatCompactCurrency } from "@/utils/formatters";

interface CompactKPIStripProps {
  metrics: EVMMetricsResponse;
}

interface MetricCellConfig {
  key: string;
  label: string;
  metricKey: MetricKey;
  getValue: (m: EVMMetricsResponse) => number | null;
  formatValue: (v: number | null) => string;
}

const METRIC_CELLS: MetricCellConfig[] = [
  {
    key: "cpi",
    label: "CPI",
    metricKey: "cpi",
    getValue: (m) => m.cpi,
    formatValue: (v) => (v !== null ? v.toFixed(2) : "--"),
  },
  {
    key: "spi",
    label: "SPI",
    metricKey: "spi",
    getValue: (m) => m.spi,
    formatValue: (v) => (v !== null ? v.toFixed(2) : "--"),
  },
  {
    key: "progress",
    label: "Progress",
    metricKey: "progress_percentage",
    getValue: (m) => m.progress_percentage,
    formatValue: (v) => (v !== null ? `${Math.round(v)}%` : "--"),
  },
  {
    key: "cv",
    label: "CV",
    metricKey: "cv",
    getValue: (m) => m.cv,
    formatValue: (v) => formatCompactCurrency(v),
  },
  {
    key: "vac",
    label: "VAC",
    metricKey: "vac",
    getValue: (m) => m.vac,
    formatValue: (v) => formatCompactCurrency(v),
  },
];

function getStatusColor(
  status: "good" | "warning" | "bad",
  token: ReturnType<typeof theme.useToken>["token"],
): string {
  switch (status) {
    case "good":
      return token.colorSuccess;
    case "warning":
      return token.colorWarning;
    case "bad":
      return token.colorError;
  }
}

const MetricCell: React.FC<{
  config: MetricCellConfig;
  metrics: EVMMetricsResponse;
  token: ReturnType<typeof theme.useToken>["token"];
}> = ({ config, metrics, token }) => {
  const value = config.getValue(metrics);
  const status = getMetricStatus(config.metricKey, value);
  const color = getStatusColor(status, token);

  return (
    <div
      role="status"
      aria-label={`${config.label}: ${config.formatValue(value)}, ${status}`}
      style={{
        flex: 1,
        minWidth: 0,
        textAlign: "center",
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          gap: token.marginXS,
        }}
      >
        <span
          aria-hidden="true"
          style={{
            width: 8,
            height: 8,
            borderRadius: "50%",
            background: color,
            flexShrink: 0,
          }}
        />
        <span
          style={{
            fontSize: token.fontSizeLG,
            fontWeight: token.fontWeightSemiBold,
            color,
            lineHeight: 1.2,
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
          }}
        >
          {config.formatValue(value)}
        </span>
      </div>
      <div
        style={{
          fontSize: token.fontSizeXS,
          color: token.colorTextTertiary,
          marginTop: 2,
          lineHeight: 1,
        }}
      >
        {config.label}
      </div>
    </div>
  );
};

export const CompactKPIStrip: React.FC<CompactKPIStripProps> = ({
  metrics,
}) => {
  const { token } = theme.useToken();

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        width: "100%",
        height: "100%",
        padding: `${token.paddingXS}px ${token.paddingSM}px`,
      }}
    >
      {METRIC_CELLS.map((config) => (
        <MetricCell
          key={config.key}
          config={config}
          metrics={metrics}
          token={token}
        />
      ))}
    </div>
  );
};
