import { Card, Row, Col, Statistic, Tag, Tooltip, Space, theme } from "antd";
import { InfoCircleOutlined } from "@ant-design/icons";
import type { ForecastRead } from "@/api/generated";

interface ForecastComparisonCardProps {
  forecast: ForecastRead;
  budgetAmount: number; // BAC
  actualCost?: number; // AC (if available)
}

export const ForecastComparisonCard = ({
  forecast,
  budgetAmount,
  actualCost = 0,
}: ForecastComparisonCardProps) => {
  const { token } = theme.useToken();

  // Calculate EVM metrics locally from forecast data
  // With 1:1 relationship, the forecast has all the data we need
  const bac = budgetAmount;
  const eac = Number(forecast.eac_amount);
  const ac = actualCost;
  const vac = bac - eac; // VAC = BAC - EAC
  const etc = eac - ac; // ETC = EAC - AC

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
      extra={
        <Tag color={forecast.branch === "main" ? "blue" : "orange"}>
          {forecast.branch === "main" ? "Main" : forecast.branch}
        </Tag>
      }
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
              value={bac > 0 ? (bac / eac).toFixed(2) : "0.00"}
              valueStyle={{
                color:
                  bac > eac ? "#52c41a" : bac < eac ? "#ff4d4f" : "#1890ff",
              }}
              suffix={
                <Tag
                  color={bac > eac ? "green" : bac < eac ? "red" : "blue"}
                  style={{ marginLeft: 8, fontSize: "12px" }}
                >
                  {bac > eac
                    ? "Efficient"
                    : bac < eac
                      ? "Inefficient"
                      : "Neutral"}
                </Tag>
              }
            />
          </Col>
        </Row>

      {/* Basis of Estimate */}
      <div
        style={{
          marginTop: 16,
          padding: 12,
          backgroundColor: token.colorFillSecondary,
          borderRadius: 4,
          borderLeft: `3px solid ${token.colorPrimary}`,
        }}
      >
        <div style={{ fontSize: "12px", color: token.colorTextTertiary, marginBottom: 4 }}>
          <strong>Basis of Estimate:</strong>
        </div>
        <div style={{ fontSize: "13px", color: token.colorText }}>
          {forecast.basis_of_estimate}
        </div>
      </div>
    </Card>
  );
};
