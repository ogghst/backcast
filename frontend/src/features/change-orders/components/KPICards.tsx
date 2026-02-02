import { Card, Col, Row, Statistic, Typography, Spin } from "antd";
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
}

/**
 * Formats a decimal string to EUR currency.
 */
const formatCurrency = (value: string | null | undefined): string => {
  if (!value) return "€0.00";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "EUR",
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
 * Single KPI Metric Card component.
 */
const KPIMetricCard = ({
  title,
  metric,
}: {
  title: string;
  metric: KPIMetric;
}) => {
  const { color, icon } = getDeltaDisplay(metric.delta);
  const mainValue = formatCurrency(metric.main_value);
  const changeValue = formatCurrency(metric.change_value);

  return (
    <Card bordered>
      <Statistic
        title={title}
        value={metric.change_value ?? "0"}
        precision={2}
        styles={{ content: { color } }}
        prefix={icon}
        suffix="€"
        formatter={(value) => formatCurrency(String(value))}
      />
      <div style={{ marginTop: 8, fontSize: 12, color: "#8c8c8c" }}>
        <div>
          Main: <strong>{mainValue}</strong>
        </div>
        <div>
          Change: <strong>{changeValue}</strong>
        </div>
        {metric.delta && (
          <div>
            Delta: <strong style={{ color }}>{formatCurrency(metric.delta)}</strong>
          </div>
        )}
        {metric.delta_percent !== null && metric.delta_percent !== undefined && (
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
 * KPICards Component
 *
 * Displays KPI comparison cards for:
 * - Budget at Completion (BAC)
 * - Budget Delta
 * - Gross Margin
 *
 * Each card shows:
 * - Current value (change branch)
 * - Main branch value
 * - Delta (absolute difference)
 * - Delta percent (percentage change)
 */
export const KPICards = ({ kpiScorecard, loading }: KPICardsProps) => {
  return (
    <Spin spinning={loading ?? false}>
      <div>
        <Title level={4}>KPI Comparison</Title>
        <Row gutter={[16, 16]}>
          <Col xs={24} sm={12} lg={8}>
            <KPIMetricCard title="Budget at Completion" metric={kpiScorecard.bac} />
          </Col>
          <Col xs={24} sm={12} lg={8}>
            <KPIMetricCard
              title="Total Budget Allocation"
              metric={kpiScorecard.budget_delta}
            />
          </Col>
          <Col xs={24} sm={12} lg={8}>
            <KPIMetricCard title="Gross Margin" metric={kpiScorecard.gross_margin} />
          </Col>
        </Row>
      </div>
    </Spin>
  );
};
