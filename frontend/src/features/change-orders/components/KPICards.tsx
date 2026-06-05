import { Card, Col, Row, Statistic, Typography, Spin, Divider, theme } from "antd";
import {
  ArrowUpOutlined,
  ArrowDownOutlined,
  MinusOutlined,
} from "@ant-design/icons";
import type { KPIScorecard, KPIMetric } from "@/api/generated";

const { Title } = Typography;

interface KPICardsProps {
  kpiScorecard: KPIScorecard;
  loading?: boolean;
  currency?: string;
}

/**
 * Formats a decimal string to currency.
 */
const formatCurrencyValue = (value: string | null | undefined, currency: string = "EUR"): string => {
  if (!value) return new Intl.NumberFormat("en-US", { style: "currency", currency }).format(0);
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
  }).format(Number(value));
};

/**
 * Formats a percentage value.
 */
const formatPercent = (value: number | null | undefined): string => {
  if (value === null || value === undefined) return "-";
  return `${value.toFixed(2)}%`;
};

/**
 * Formats a number with specified decimal places.
 */
const formatNumber = (
  value: string | null | undefined,
  decimals: number = 2,
): string => {
  if (!value) return "0";
  return Number(value).toFixed(decimals);
};

/**
 * Formats days value with unit.
 */
const formatDays = (value: string | null | undefined): string => {
  if (!value) return "0 days";
  return `${Number(value)} days`;
};

/**
 * Determines the color and icon for a delta value.
 * Positive deltas are red (cost increase), negative are green (cost decrease).
 */
const getDeltaDisplay = (delta: string | undefined) => {
  const deltaNum = delta ? Number(delta) : 0;
  if (deltaNum > 0) {
    return {
      color: "#cf1322", // red
      icon: <ArrowUpOutlined />,
      prefix: "+",
    };
  }
  if (deltaNum < 0) {
    return {
      color: "#3f8600", // green
      icon: <ArrowDownOutlined />,
      prefix: "",
    };
  }
  return {
    color: "#8c8c8c", // gray
    icon: <MinusOutlined />,
    prefix: "",
  };
};

/**
 * Determines color for performance index (CPI, SPI).
 * Green if >= 1.0 (good performance), red if < 1.0 (poor performance).
 */
const getPerformanceIndexColor = (value: string | null | undefined): string => {
  if (!value) return "#8c8c8c";
  return Number(value) >= 1.0 ? "#3f8600" : "#cf1322";
};

/**
 * Determines color for schedule duration.
 * Red if duration increased (unfavorable), green if decreased (favorable).
 */
const getScheduleDurationColor = (delta: string | undefined): string => {
  const deltaNum = delta ? Number(delta) : 0;
  if (deltaNum > 0) return "#cf1322"; // red - schedule extended
  if (deltaNum < 0) return "#3f8600"; // green - schedule shortened
  return "#8c8c8c"; // gray - no change
};

/**
 * Single KPI Metric Card component for currency values.
 */
const KPIMetricCard = ({
  title,
  metric,
  currency,
}: {
  title: string;
  metric: KPIMetric;
  currency: string;
}) => {
  const { token } = theme.useToken();
  const { color, icon } = getDeltaDisplay(metric.delta);
  const mainValue = formatCurrencyValue(metric.main_value, currency);
  const changeValue = formatCurrencyValue(metric.change_value, currency);
  const mergedValue = metric.merged_value
    ? formatCurrencyValue(metric.merged_value, currency)
    : null;

  // Use delta for Statistic component to show the difference
  const rawDisplayValue = metric.delta;

  return (
    <Card variant="outlined">
      <Statistic
        title={title}
        value={rawDisplayValue ?? 0}
        precision={2}
        styles={{ content: { color } }}
        prefix={icon}
        formatter={(value) => formatCurrencyValue(String(value), currency)}
      />
      <div style={{ marginTop: token.marginXS, fontSize: 12, color: token.colorTextSecondary }}>
        <div>
          Main: <strong>{mainValue}</strong>
        </div>
        {mergedValue && (
          <div>
            Merged: <strong>{mergedValue}</strong>
          </div>
        )}
        <div>
          Change: <strong>{changeValue}</strong>
        </div>
        {metric.delta && (
          <div>
            Delta:{" "}
            <strong style={{ color }}>{formatCurrencyValue(metric.delta, currency)}</strong>
          </div>
        )}
        {metric.delta_percent !== null &&
          metric.delta_percent !== undefined && (
            <div>
              Change:{" "}
              <strong style={{ color }}>
                {formatPercent(metric.delta_percent)}
              </strong>
            </div>
          )}
      </div>
    </Card>
  );
};

/**
 * Performance Index Card (CPI, SPI, TCPI).
 * Shows the index value with target indicator.
 */
const PerformanceIndexCard = ({
  title,
  metric,
  target,
}: {
  title: string;
  metric: KPIMetric;
  target: string;
}) => {
  const { token } = theme.useToken();
  const mergedValue = metric.merged_value ?? metric.change_value ?? "0";
  const color = getPerformanceIndexColor(mergedValue);
  const mainValue = formatNumber(metric.main_value);
  const changeValue = formatNumber(metric.change_value);

  return (
    <Card variant="outlined">
      <Statistic
        title={title}
        value={mergedValue}
        precision={2}
        styles={{ content: { color } }}
      />
      <div style={{ marginTop: token.marginXS, fontSize: 12, color: token.colorTextSecondary }}>
        <div>
          Main: <strong>{mainValue}</strong>
        </div>
        {metric.merged_value && (
          <div>
            Merged: <strong>{formatNumber(metric.merged_value)}</strong>
          </div>
        )}
        <div>
          Change: <strong>{changeValue}</strong>
        </div>
        <div>
          Target: <strong>{target}</strong>
        </div>
        {metric.delta && (
          <div>
            Delta:{" "}
            <strong style={{ color }}>{formatNumber(metric.delta, 3)}</strong>
          </div>
        )}
      </div>
    </Card>
  );
};

/**
 * Schedule Duration Card.
 * Shows duration in days with color coding for schedule changes.
 */
const ScheduleDurationCard = ({
  title,
  metric,
}: {
  title: string;
  metric: KPIMetric;
}) => {
  const { token } = theme.useToken();
  const color = getScheduleDurationColor(metric.delta);
  const { icon, prefix } = getDeltaDisplay(metric.delta);
  const mainValue = formatDays(metric.main_value);
  const changeValue = formatDays(metric.change_value);
  const mergedValue = metric.merged_value
    ? formatDays(metric.merged_value)
    : null;

  // Use raw values for Statistic component
  const rawDisplayValue = metric.merged_value ?? metric.change_value;

  return (
    <Card variant="outlined">
      <Statistic
        title={title}
        value={rawDisplayValue ?? 0}
        precision={0}
        styles={{ content: { color } }}
        prefix={icon}
        formatter={(value) => formatDays(String(value))}
      />
      <div style={{ marginTop: token.marginXS, fontSize: 12, color: token.colorTextSecondary }}>
        <div>
          Main: <strong>{mainValue}</strong>
        </div>
        {mergedValue && (
          <div>
            Merged: <strong>{mergedValue}</strong>
          </div>
        )}
        <div>
          Change: <strong>{changeValue}</strong>
        </div>
        {metric.delta && (
          <div>
            Delta:{" "}
            <strong style={{ color }}>
              {prefix}
              {formatDays(metric.delta)}
            </strong>
          </div>
        )}
      </div>
    </Card>
  );
};

/**
 * KPICards Component
 *
 * Displays KPI comparison cards organized in sections:
 *
 * Financial Metrics:
 * - Budget at Completion (BAC)
 * - Budget Delta
 * - Revenue Delta
 * - Gross Margin
 * - Actual Costs
 * - Estimate at Completion (EAC)
 * - Variance at Completion (VAC)
 *
 * Schedule Metrics:
 * - Schedule Duration
 *
 * Performance Indices:
 * - Cost Performance Index (CPI)
 * - Schedule Performance Index (SPI)
 * - To-Complete Performance Index (TCPI)
 *
 * Each card shows:
 * - Current value (change branch)
 * - Main branch value
 * - Delta (absolute difference)
 * - Delta percent (percentage change) where applicable
 *
 * Color coding:
 * - Financial: Red = cost increase, Green = cost decrease
 * - VAC: Green = under budget, Red = over budget
 * - Schedule: Red = schedule extended, Green = schedule shortened
 * - Performance Indices: Green = >= 1.0 (good), Red = < 1.0 (poor)
 */
export const KPICards = ({ kpiScorecard, loading, currency = "EUR" }: KPICardsProps) => {
  return (
    <Spin spinning={loading ?? false}>
      <div>
        <Title level={4}>Financial Metrics</Title>
        <Row gutter={[16, 16]}>
          <Col xs={24} sm={12} lg={6}>
            <KPIMetricCard
              title="Budget at Completion"
              metric={kpiScorecard.bac}
              currency={currency}
            />
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <KPIMetricCard
              title="Total Budget Allocation"
              metric={kpiScorecard.budget_delta}
              currency={currency}
            />
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <KPIMetricCard
              title="Revenue Allocation"
              metric={kpiScorecard.revenue_delta}
              currency={currency}
            />
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <KPIMetricCard
              title="Gross Margin"
              metric={kpiScorecard.gross_margin}
              currency={currency}
            />
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <KPIMetricCard
              title="Actual Costs"
              metric={kpiScorecard.actual_costs}
              currency={currency}
            />
          </Col>
          {kpiScorecard.eac && (
            <Col xs={24} sm={12} lg={6}>
              <KPIMetricCard
                title="Estimate at Completion"
                metric={kpiScorecard.eac}
                currency={currency}
              />
            </Col>
          )}
          {kpiScorecard.vac && (
            <Col xs={24} sm={12} lg={6}>
              <KPIMetricCard
                title="Variance at Completion"
                metric={kpiScorecard.vac}
                currency={currency}
              />
            </Col>
          )}
        </Row>

        {(kpiScorecard.schedule_duration ||
          kpiScorecard.cpi ||
          kpiScorecard.spi ||
          kpiScorecard.tcpi) && (
          <>
            <Divider />
            <Title level={4}>Schedule & Performance Metrics</Title>
            <Row gutter={[16, 16]}>
              {kpiScorecard.schedule_duration && (
                <Col xs={24} sm={12} lg={6}>
                  <ScheduleDurationCard
                    title="Schedule Duration"
                    metric={kpiScorecard.schedule_duration}
                  />
                </Col>
              )}
              {kpiScorecard.cpi && (
                <Col xs={24} sm={12} lg={6}>
                  <PerformanceIndexCard
                    title="Cost Performance Index"
                    metric={kpiScorecard.cpi}
                    target="≥1.0"
                  />
                </Col>
              )}
              {kpiScorecard.spi && (
                <Col xs={24} sm={12} lg={6}>
                  <PerformanceIndexCard
                    title="Schedule Performance Index"
                    metric={kpiScorecard.spi}
                    target="≥1.0"
                  />
                </Col>
              )}
              {kpiScorecard.tcpi && (
                <Col xs={24} sm={12} lg={6}>
                  <PerformanceIndexCard
                    title="To-Complete Performance Index"
                    metric={kpiScorecard.tcpi}
                    target="≤1.0"
                  />
                </Col>
              )}
            </Row>
          </>
        )}
      </div>
    </Spin>
  );
};
