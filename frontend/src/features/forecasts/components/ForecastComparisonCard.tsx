import { Card, Row, Col, Statistic, Tag, Tooltip, Space, theme, Empty } from "antd";
import { InfoCircleOutlined } from "@ant-design/icons";
import { useCostElementEvmMetrics } from "@/features/cost-elements/api/useCostElements";

interface ForecastComparisonCardProps {
  costElementId: string;
  budgetAmount: number; // BAC
}

interface EVMMetricsData {
  bac: number;
  pv: number;
  ac: number;
  ev: number;
  cv: number;
  sv: number;
  cpi: number | null;
  spi: number | null;
  eac: number | null;
  vac: number | null;
  etc: number | null;
}

export const ForecastComparisonCard = ({
  costElementId,
  budgetAmount,
}: ForecastComparisonCardProps) => {
  const { token } = theme.useToken();

  // Fetch EVM metrics from the new endpoint
  const { data: evmMetrics, isLoading: evmLoading } =
    useCostElementEvmMetrics(costElementId);

  const metrics = evmMetrics as EVMMetricsData | undefined;

  if (evmLoading) {
    return (
      <Card
        title={
          <Space>
            <span>EVM Analysis</span>
            <Tooltip title="Earned Value Management metrics based on current forecast">
              <InfoCircleOutlined style={{ color: token.colorTextTertiary }} />
            </Tooltip>
          </Space>
        }
        style={{ marginTop: 16 }}
      >
        <Empty description="Loading EVM metrics..." image={Empty.PRESENTED_IMAGE_SIMPLE} />
      </Card>
    );
  }

  if (!metrics) {
    return (
      <Card
        title={
          <Space>
            <span>EVM Analysis</span>
            <Tooltip title="Earned Value Management metrics based on current forecast">
              <InfoCircleOutlined style={{ color: token.colorTextTertiary }} />
            </Tooltip>
          </Space>
        }
        style={{ marginTop: 16 }}
      >
        <Empty
          description="No forecast created yet. Create a forecast to see EVM analysis."
          image={Empty.PRESENTED_IMAGE_SIMPLE}
        />
      </Card>
    );
  }

  // Use metrics from API with fallback to calculated values
  const bac = metrics.bac ?? budgetAmount;
  const eac = metrics.eac ?? (bac > 0 && metrics.cpi ? bac / (metrics.cpi / 100) : 0);
  const ac = metrics.ac ?? 0;
  const vac = metrics.vac ?? (bac - eac);
  const etc = metrics.etc ?? (eac - ac);
  const cpi = metrics.cpi ?? (bac > 0 && eac > 0 ? (bac / eac) * 100 : null);

  // Determine status colors
  const getVACStatus = () => {
    if (vac > 0) return { color: "#52c41a", text: "Under Budget" }; // green
    if (vac < 0) return { color: "#ff4d4f", text: "Over Budget" }; // red
    return { color: "#1890ff", text: "On Budget" }; // blue
  };

  const vacStatus = getVACStatus();

  return (
    <Card
      title={
        <Space>
          <span>EVM Analysis</span>
          <Tooltip title="Earned Value Management metrics based on current forecast">
            <InfoCircleOutlined style={{ color: token.colorTextTertiary }} />
          </Tooltip>
        </Space>
      }
      style={{ marginTop: 16 }}
    >
      <Row gutter={[16, 16]}>
          {/* BAC - Budget at Complete */}
          <Col xs={12} sm={8}>
            <Statistic
              title={
                <Tooltip title="Budget at Complete - Original budget allocated">
                  <span>BAC</span>
                </Tooltip>
              }
              value={bac}
              precision={2}
              prefix="€"
              valueStyle={{ color: "#1890ff" }}
            />
          </Col>

          {/* EAC - Estimate at Complete */}
          <Col xs={12} sm={8}>
            <Statistic
              title={
                <Tooltip title="Estimate at Complete - Projected total cost">
                  <span>EAC</span>
                </Tooltip>
              }
              value={eac}
              precision={2}
              prefix="€"
              valueStyle={{
                color: eac > bac ? "#ff4d4f" : "#52c41a",
              }}
            />
          </Col>

          {/* AC - Actual Cost */}
          <Col xs={12} sm={8}>
            <Statistic
              title={
                <Tooltip title="Actual Cost - Cost incurred to date">
                  <span>AC</span>
                </Tooltip>
              }
              value={ac}
              precision={2}
              prefix="€"
              valueStyle={{ color: "#722ed1" }}
            />
          </Col>

          {/* VAC - Variance at Complete */}
          <Col xs={12} sm={8}>
            <Statistic
              title={
                <Tooltip title="Variance at Complete = BAC - EAC">
                  <span>VAC</span>
                </Tooltip>
              }
              value={Math.abs(vac)}
              precision={2}
              prefix={vac < 0 ? "-€" : "€"}
              valueStyle={{ color: vacStatus.color }}
              suffix={
                <Tag
                  color={vacStatus.color}
                  style={{ marginLeft: 8, fontSize: "12px" }}
                >
                  {vacStatus.text}
                </Tag>
              }
            />
          </Col>

          {/* ETC - Estimate to Complete */}
          <Col xs={12} sm={8}>
            <Statistic
              title={
                <Tooltip title="Estimate to Complete = EAC - AC (Remaining work)">
                  <span>ETC</span>
                </Tooltip>
              }
              value={etc}
              precision={2}
              prefix="€"
              valueStyle={{ color: "#fa8c16" }}
            />
          </Col>

          {/* Cost Performance Index (CPI) */}
          <Col xs={12} sm={8}>
            <Statistic
              title={
                <Tooltip title="Cost Performance Index = BAC / EAC (>1 is good)">
                  <span>CPI</span>
                </Tooltip>
              }
              value={cpi !== null ? (cpi / 100).toFixed(2) : "0.00"}
              valueStyle={{
                color:
                  cpi && cpi > 100 ? "#52c41a" : cpi && cpi < 100 ? "#ff4d4f" : "#1890ff",
              }}
              suffix={
                cpi !== null ? (
                  <Tag
                    color={cpi > 100 ? "green" : cpi < 100 ? "red" : "blue"}
                    style={{ marginLeft: 8, fontSize: "12px" }}
                  >
                    {cpi > 100
                      ? "Efficient"
                      : cpi < 100
                        ? "Inefficient"
                        : "Neutral"}
                  </Tag>
                ) : null
              }
            />
          </Col>
        </Row>
    </Card>
  );
};
