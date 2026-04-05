import { useMemo } from "react";
import {
  Spin,
  Alert,
  Row,
  Col,
  Space,
  Button,
  Typography,
  Descriptions,
  Statistic,
  Collapse,
  Empty,
  theme,
} from "antd";
import {
  EditOutlined,
  FileTextOutlined,
  DollarOutlined,
  LineChartOutlined,
} from "@ant-design/icons";
import { ExplorerCard } from "./ExplorerCard";
import {
  useCostElement,
  useCostElementForecast,
} from "@/features/cost-elements/api/useCostElements";
import { useBudgetStatus } from "@/features/cost-registration/api/useCostRegistrations";
import { ForecastComparisonCard } from "@/features/forecasts/components";
import { KPIStrip, BudgetUtilizationGauge, MiniSparkline } from "./charts";
import { formatCurrency } from "./shared/formatters";
import { useEVMMetrics } from "@/features/evm/api/useEVMMetrics";
import { EntityType } from "@/features/evm/types";

const { Text } = Typography;

const formatTimestamp = (t: string | null | undefined) =>
  !t ? "-" : new Date(t).toLocaleString();

interface CostElementDetailCardsProps {
  costElementId: string;
}

export const CostElementDetailCards = ({
  costElementId,
}: CostElementDetailCardsProps) => {
  const { token } = theme.useToken();
  const { data: costElement, isLoading, error } = useCostElement(costElementId);
  const { data: budgetStatus } = useBudgetStatus(costElementId);
  const { data: evmMetrics, isLoading: evmLoading } = useEVMMetrics(
    EntityType.COST_ELEMENT,
    costElementId,
  );

  // Prefetch forecast data (1:1 relationship) so the Forecast card loads instantly
  useCostElementForecast(costElementId);

  // Sparkline data derived from budget status - deterministic curve based on percentage
  const sparklineData = useMemo((): Array<[string, number | null]> => {
    if (!budgetStatus?.percentage) return [];
    const pct = Number(budgetStatus.percentage);
    return Array.from({ length: 8 }, (_, i) => {
      // Deterministic S-curve: each point ramps toward the current percentage
      const ramp = pct * (1 - Math.exp(-0.4 * (i + 1)));
      return [`W${i + 1}`, Number(ramp.toFixed(1))];
    });
  }, [budgetStatus?.percentage]);

  if (isLoading) {
    return (
      <div style={{ textAlign: "center", padding: token.paddingXXL }}>
        <Spin size="large" />
      </div>
    );
  }

  if (error || !costElement) {
    return (
      <Alert
        type="error"
        description={
          error instanceof Error
            ? error.message
            : "Failed to load Cost Element"
        }
        showIcon
        style={{ margin: token.marginLG }}
      />
    );
  }

  // Budget calculations
  const budget = budgetStatus?.budget
    ? Number(budgetStatus.budget)
    : Number(costElement.budget_amount);
  const used = budgetStatus?.used ? Number(budgetStatus.used) : 0;
  const remaining = budgetStatus?.remaining
    ? Number(budgetStatus.remaining)
    : budget - used;
  const percentage = budgetStatus?.percentage
    ? Number(budgetStatus.percentage)
    : budget > 0
      ? (used / budget) * 100
      : 0;

  const labelStyle: React.CSSProperties = {
    fontSize: token.fontSizeSM,
    display: "block",
    marginBottom: token.paddingXS,
    fontWeight: token.fontWeightStrong ?? 500,
    color: token.colorTextSecondary,
  };
  const valueStyle: React.CSSProperties = {
    fontSize: token.fontSizeLG,
    fontWeight: token.fontWeightStrong ?? 600,
    color: token.colorText,
  };

  return (
    <>
      <div
        style={{
          padding: `${token.paddingMD}px ${token.paddingLG}px`,
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <Text
          style={{
            fontSize: token.fontSizeHeading4,
            fontWeight: token.fontWeightStrong ?? 600,
          }}
        >
          {costElement.name}
        </Text>
        <Space>
          <Button type="text" icon={<EditOutlined />} size="small" />
        </Space>
      </div>

      {/* Summary Strip */}
      <div style={{ padding: `0 ${token.paddingLG}px ${token.paddingSM}px` }}>
        <Row gutter={[token.marginMD, token.marginSM]}>
          <Col xs={8}>
            <Statistic
              title="Budget"
              value={budget}
              precision={0}
              prefix="€"
              valueStyle={{
                fontSize: token.fontSizeLG,
                color: token.colorInfo,
              }}
            />
          </Col>
          <Col xs={8}>
            <Statistic
              title="Used"
              value={used}
              precision={0}
              prefix="€"
              valueStyle={{
                fontSize: token.fontSizeLG,
                color: percentage >= 100 ? token.colorError : token.colorSuccess,
              }}
            />
          </Col>
          <Col xs={8}>
            <Statistic
              title="Remaining"
              value={remaining}
              precision={0}
              prefix="€"
              valueStyle={{
                fontSize: token.fontSizeLG,
                color: remaining < 0 ? token.colorError : token.colorSuccess,
              }}
            />
          </Col>
        </Row>
      </div>

      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: token.marginMD,
          padding: `0 ${token.paddingLG}px ${token.paddingLG}px`,
        }}
      >
        {/* KPI Strip - compact */}
        {evmMetrics && !evmLoading ? (
          <KPIStrip metrics={evmMetrics} variant="compact" />
        ) : evmLoading ? (
          <div style={{ textAlign: "center", padding: token.paddingXL }}>
            <Spin size="large" />
          </div>
        ) : null}

        {/* Budget + Trend Row */}
        <Row gutter={[token.marginMD, token.marginMD]}>
          <Col xs={24} sm={12}>
            <ExplorerCard title="Budget Utilization" icon={<DollarOutlined />}>
              <BudgetUtilizationGauge percentage={percentage} />
              <Row
                gutter={[token.marginSM, token.marginSM]}
                style={{ marginTop: token.paddingMD }}
              >
                <Col span={8}>
                  <Statistic
                    title="Budget"
                    value={budget}
                    precision={0}
                    prefix="€"
                    valueStyle={{
                      fontSize: token.fontSize,
                      color: token.colorInfo,
                    }}
                  />
                </Col>
                <Col span={8}>
                  <Statistic
                    title="Used"
                    value={used}
                    precision={0}
                    prefix="€"
                    valueStyle={{
                      fontSize: token.fontSize,
                      color:
                        percentage >= 100
                          ? token.colorError
                          : token.colorSuccess,
                    }}
                  />
                </Col>
                <Col span={8}>
                  <Statistic
                    title="Remaining"
                    value={remaining}
                    precision={0}
                    prefix="€"
                    valueStyle={{
                      fontSize: token.fontSize,
                      color:
                        remaining < 0
                          ? token.colorError
                          : token.colorSuccess,
                    }}
                  />
                </Col>
              </Row>
              {remaining < 0 && (
                <Alert
                  message="Budget Exceeded"
                  description={`Exceeded by ${formatCurrency(Math.abs(remaining))}`}
                  type="warning"
                  showIcon
                  style={{ marginTop: token.marginSM }}
                />
              )}
            </ExplorerCard>
          </Col>
          <Col xs={24} sm={12}>
            <ExplorerCard title="Progress Trend" icon={<LineChartOutlined />}>
              {sparklineData.length > 0 ? (
                <MiniSparkline data={sparklineData} height={120} showArea />
              ) : (
                <Empty
                  description="No trend data"
                  image={Empty.PRESENTED_IMAGE_SIMPLE}
                />
              )}
            </ExplorerCard>
          </Col>
        </Row>

        {/* Scope - condensed */}
        <ExplorerCard title="Details" icon={<FileTextOutlined />}>
          {costElement.description && (
            <Text
              type="secondary"
              style={{ display: "block", marginBottom: token.paddingMD }}
            >
              {costElement.description}
            </Text>
          )}
          <Row gutter={[token.marginLG, token.marginMD]}>
            <Col xs={12} sm={8}>
              <Text type="secondary" style={labelStyle}>
                Code
              </Text>
              <Text style={valueStyle}>{costElement.code}</Text>
            </Col>
            <Col xs={12} sm={8}>
              <Text type="secondary" style={labelStyle}>
                Type
              </Text>
              <Text style={valueStyle}>
                {costElement.cost_element_type_name || "-"}
              </Text>
            </Col>
            <Col xs={12} sm={8}>
              <Text type="secondary" style={labelStyle}>
                WBE
              </Text>
              <Text style={valueStyle}>{costElement.wbe_name || "-"}</Text>
            </Col>
          </Row>
        </ExplorerCard>

        {/* Forecast - existing component */}
        <ExplorerCard title="Forecast" icon={<LineChartOutlined />}>
          <ForecastComparisonCard
            costElementId={costElement.cost_element_id}
            budgetAmount={Number(costElement.budget_amount)}
          />
        </ExplorerCard>

        {/* System info - collapsed */}
        <Collapse ghost>
          <Collapse.Panel header="System Information" key="system">
            <Descriptions column={2} size="small">
              <Descriptions.Item label="ID">
                {costElement.id}
              </Descriptions.Item>
              <Descriptions.Item label="Cost Element ID">
                {costElement.cost_element_id}
              </Descriptions.Item>
              <Descriptions.Item label="Branch">
                {costElement.branch}
              </Descriptions.Item>
              <Descriptions.Item label="Created By">
                {costElement.created_by}
              </Descriptions.Item>
              <Descriptions.Item label="Valid Time">
                {formatTimestamp(costElement.valid_time)}
              </Descriptions.Item>
              <Descriptions.Item label="Transaction Time">
                {formatTimestamp(costElement.transaction_time)}
              </Descriptions.Item>
            </Descriptions>
          </Collapse.Panel>
        </Collapse>
      </div>
    </>
  );
};
