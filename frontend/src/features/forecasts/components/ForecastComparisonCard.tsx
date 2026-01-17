import { Card, Row, Col, Statistic, Tag, Tooltip, Spin, Space } from "antd";
import { InfoCircleOutlined } from "@ant-design/icons";
import { useForecastComparison } from "@/features/forecasts/api";
import type { ForecastRead } from "@/api/generated";

interface ForecastComparisonCardProps {
  forecast: ForecastRead;
  budgetAmount: number; // BAC
  actualCost?: number; // AC (if available)
}

interface ComparisonData {
  bac_amount: string;
  eac_amount: string;
  ac_amount: string;
  vac_amount: string;
  etc_amount: string;
}

export const ForecastComparisonCard = ({
  forecast,
  budgetAmount,
  actualCost = 0,
}: ForecastComparisonCardProps) => {
  // Fetch comparison data from API
  const { data: comparisonData, isLoading: comparisonLoading } =
    useForecastComparison(forecast.forecast_id, forecast.branch);

  const comparison = comparisonData as ComparisonData | undefined;

  // Calculate locally if API data not available (fallback)
  const bac = comparison?.bac_amount
    ? Number(comparison.bac_amount)
    : budgetAmount;
  const eac = comparison?.eac_amount
    ? Number(comparison.eac_amount)
    : Number(forecast.eac_amount);
  const ac = comparison?.ac_amount ? Number(comparison.ac_amount) : actualCost;
  const vac = comparison?.vac_amount
    ? Number(comparison.vac_amount)
    : bac - eac;
  const etc = comparison?.etc_amount ? Number(comparison.etc_amount) : eac - ac;

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
            <InfoCircleOutlined style={{ color: "#999" }} />
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
      {comparisonLoading ? (
        <div style={{ textAlign: "center", padding: "24px" }}>
          <Spin />
        </div>
      ) : (
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
      )}

      {/* Basis of Estimate */}
      {!comparisonLoading && (
        <div
          style={{
            marginTop: 16,
            padding: 12,
            backgroundColor: "#fafafa",
            borderRadius: 4,
            borderLeft: "3px solid #1890ff",
          }}
        >
          <div style={{ fontSize: "12px", color: "#999", marginBottom: 4 }}>
            <strong>Basis of Estimate:</strong>
          </div>
          <div style={{ fontSize: "13px", color: "#333" }}>
            {forecast.basis_of_estimate}
          </div>
        </div>
      )}
    </Card>
  );
};
