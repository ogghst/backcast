import { Row, Col, Statistic, Progress, theme, Typography } from "antd";
import { ExplorerCard } from "../ExplorerCard";
import { EChartsGauge } from "@/features/evm/components/charts/EChartsGauge";
import type { EVMMetricsResponse } from "@/features/evm/types";
import { formatCurrency } from "../shared/formatters";

const { Text } = Typography;

interface KPIStripProps {
  metrics: EVMMetricsResponse;
  /** 'full' for project/WBE (4 items), 'compact' for cost element (3 items) */
  variant?: "full" | "compact";
  /** Optional extra content rendered in the card header (e.g. an action button) */
  extra?: React.ReactNode;
}

export const KPIStrip: React.FC<KPIStripProps> = ({
  metrics,
  variant = "full",
  extra,
}) => {
  const { token } = theme.useToken();

  if (variant === "compact") {
    return (
      <ExplorerCard title="KPI Overview">
        <Row gutter={[token.paddingMD, token.paddingMD]} align="middle">
          <Col xs={8} style={{ textAlign: "center" }}>
            <Progress
              type="circle"
              percent={Math.round(metrics.progress_percentage)}
              size={100}
              format={(percent) => `${percent}%`}
              strokeColor={token.colorPrimary}
            />
            <div
              style={{
                marginTop: token.paddingXS,
                fontSize: token.fontSizeSM,
                color: token.colorTextSecondary,
              }}
            >
              Budget Utilization
            </div>
          </Col>
          <Col xs={8} style={{ textAlign: "center" }}>
            <EChartsGauge
              value={metrics.cpi}
              min={0}
              max={2}
              label="CPI"
              goodThreshold={1.0}
              variant="semi-circle"
              size={120}
            />
          </Col>
          <Col xs={8} style={{ textAlign: "center" }}>
            <EChartsGauge
              value={metrics.spi}
              min={0}
              max={2}
              label="SPI"
              goodThreshold={1.0}
              variant="semi-circle"
              size={120}
            />
          </Col>
        </Row>
      </ExplorerCard>
    );
  }

  const eacColor =
    metrics.eac !== null && metrics.eac > metrics.bac
      ? token.colorError
      : token.colorSuccess;

  return (
    <ExplorerCard title="KPI Overview" extra={extra}>
      <Row gutter={[token.paddingMD, token.paddingMD]} align="middle">
        <Col xs={24} sm={12} md={6} style={{ textAlign: "center" }}>
          <EChartsGauge
            value={metrics.cpi}
            min={0}
            max={2}
            label="CPI"
            goodThreshold={1.0}
            variant="semi-circle"
            size={160}
          />
        </Col>
        <Col xs={24} sm={12} md={6} style={{ textAlign: "center" }}>
          <EChartsGauge
            value={metrics.spi}
            min={0}
            max={2}
            label="SPI"
            goodThreshold={1.0}
            variant="semi-circle"
            size={160}
          />
        </Col>
        <Col xs={24} sm={12} md={6} style={{ textAlign: "center" }}>
          <Progress
            type="circle"
            percent={Math.round(metrics.progress_percentage)}
            size={120}
            format={(percent) => `${percent}%`}
            strokeColor={token.colorPrimary}
          />
          <div
            style={{
              marginTop: token.paddingXS,
              fontSize: token.fontSizeSM,
              color: token.colorTextSecondary,
            }}
          >
            Progress
          </div>
        </Col>
        <Col xs={24} sm={12} md={6} style={{ textAlign: "center" }}>
          {metrics.eac !== null ? (
            <div>
              <Statistic
                title="EAC"
                value={metrics.eac}
                formatter={(value) => formatCurrency(value as number)}
                valueStyle={{ color: eacColor, fontSize: token.fontSizeXL }}
              />
              <Text type="secondary" style={{ fontSize: token.fontSizeSM }}>
                BAC: {formatCurrency(metrics.bac)}
              </Text>
            </div>
          ) : (
            <Statistic
              title="BAC"
              value={metrics.bac}
              formatter={(value) => formatCurrency(value as number)}
              valueStyle={{ fontSize: token.fontSizeXL }}
            />
          )}
        </Col>
      </Row>
    </ExplorerCard>
  );
};
