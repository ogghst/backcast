import { useState, useMemo } from "react";
import {
  Spin,
  Alert,
  Row,
  Col,
  Space,
  Statistic,
  Typography,
  Empty,
  Descriptions,
  theme,
  Collapse,
  Button,
} from "antd";
import {
  EditOutlined,
  FileTextOutlined,
  DollarOutlined,
  PieChartOutlined,
  LineChartOutlined,
} from "@ant-design/icons";
import { ExplorerCard } from "./ExplorerCard";
import { EVMAnalyzerModal } from "@/features/evm/components/EVMAnalyzerModal";
import { useEVMMetrics, useEVMTimeSeries } from "@/features/evm/api/useEVMMetrics";
import { useWBSElement } from "@/features/wbs-elements/api/useWBSElements";
import { useCostElements } from "@/features/cost-elements/api/useCostElements";
import { EntityType } from "@/features/evm/types";
import { EVMTimeSeriesGranularity } from "@/features/evm/types";
import { formatTimestamp } from "./shared/formatters";
import { KPIStrip, BudgetOverviewChart, BudgetDistributionChart } from "./charts";
import { useProjectCurrency } from "@/features/projects/api/useProjectCurrency";
import { getCurrencySymbol, formatTemporalRange } from "@/utils/formatters";


const { Text } = Typography;

interface WBSElementDetailCardsProps {
  wbsElementId: string;
}

export const WBSElementDetailCards = ({ wbsElementId }: WBSElementDetailCardsProps) => {
  const { token } = theme.useToken();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [granularity, setGranularity] = useState<EVMTimeSeriesGranularity>(EVMTimeSeriesGranularity.WEEK);

  const { data: wbe, isLoading, error } = useWBSElement(wbsElementId);
  const currency = useProjectCurrency(wbe?.project_id);
  const currencySymbol = getCurrencySymbol(currency);
  const { data: evmMetrics, isLoading: evmLoading } = useEVMMetrics(
    EntityType.WBS_ELEMENT,
    wbsElementId,
  );
  const { data: timeSeries, isLoading: timeSeriesLoading } = useEVMTimeSeries(
    EntityType.WBS_ELEMENT,
    wbsElementId,
    granularity,
  );
  const { data: childCostElements } = useCostElements({
    filters: { wbs_element_id: [wbsElementId] },
    pagination: { pageSize: 100 },
    queryOptions: { enabled: !!wbsElementId },
  });

  const donutItems = useMemo(() => {
    if (!childCostElements?.items) return [];
    return childCostElements.items
      .filter((ce) => Number(ce.amount) > 0)
      .map((ce) => ({
        name: ce.cost_element_type_name || ce.cost_element_type_code || ce.cost_element_id,
        value: Number(ce.amount),
      }));
  }, [childCostElements]);

  if (isLoading) {
    return (
      <div style={{ textAlign: "center", padding: token.paddingXL }}>
        <Spin size="large" />
      </div>
    );
  }

  if (error || !wbe) {
    return (
      <Alert
        type="error"
        description={
          error instanceof Error ? error.message : "Failed to load WBE"
        }
        showIcon
        style={{ margin: token.paddingLG }}
      />
    );
  }

  const labelStyle: React.CSSProperties = {
    fontSize: token.fontSizeSM,
    display: "block",
    marginBottom: token.paddingXS,
    fontWeight: 600,
    color: token.colorTextSecondary,
  };

  const valueStyle: React.CSSProperties = {
    fontSize: token.fontSizeLG,
    fontWeight: 600,
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
            fontWeight: 600,
          }}
        >
          {wbe.name}
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
              value={Number(wbe.budget_allocation) || 0}
              precision={0}
              prefix={currencySymbol}
              valueStyle={{ fontSize: token.fontSizeLG }}
            />
          </Col>
          <Col xs={8}>
            <Statistic
              title="Revenue"
              value={Number(wbe.revenue_allocation) || 0}
              precision={0}
              prefix={currencySymbol}
              valueStyle={{ fontSize: token.fontSizeLG }}
            />
          </Col>
          <Col xs={8}>
            <Statistic
              title="Level"
              value={wbe.level}
              valueStyle={{ fontSize: token.fontSizeLG }}
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
        {/* KPI Overview Strip */}
        {evmMetrics && !evmLoading ? (
          <KPIStrip
            metrics={evmMetrics}
            variant="full"
            extra={
              <Button
                type="link"
                size="small"
                icon={<LineChartOutlined />}
                onClick={() => setIsModalOpen(true)}
              >
                Advanced Analysis
              </Button>
            }
          />
        ) : evmLoading ? (
          <div style={{ textAlign: "center", padding: token.paddingXL }}>
            <Spin size="large" />
            <div style={{ marginTop: token.paddingMD }}>
              Loading EVM metrics...
            </div>
          </div>
        ) : null}

        {/* Charts Row */}
        {evmMetrics && evmMetrics.bac > 0 && (
          <Row gutter={[token.marginMD, token.marginMD]}>
            <Col xs={24} lg={12}>
              <ExplorerCard title="Cost Distribution" icon={<PieChartOutlined />}>
                {donutItems.length > 0 ? (
                  <BudgetDistributionChart
                    items={donutItems}
                    totalBudget={Number(wbe.budget_allocation || evmMetrics.bac)}
                    height={220}
                  />
                ) : (
                  <Empty
                    description="No child cost elements"
                    image={Empty.PRESENTED_IMAGE_SIMPLE}
                  />
                )}
              </ExplorerCard>
            </Col>
            <Col xs={24} lg={12}>
              <ExplorerCard title="Budget Overview" icon={<DollarOutlined />}>
                <BudgetOverviewChart metrics={evmMetrics} height={220} />
              </ExplorerCard>
            </Col>
          </Row>
        )}

        {/* Scope - condensed */}
        <ExplorerCard title="Details" icon={<FileTextOutlined />}>
          {wbe.description && (
            <Text
              type="secondary"
              style={{ display: "block", marginBottom: token.paddingMD }}
            >
              {wbe.description}
            </Text>
          )}
          <Row gutter={[token.marginLG, token.marginMD]}>
            <Col xs={12} sm={8}>
              <Text type="secondary" style={labelStyle}>
                Code
              </Text>
              <Text style={valueStyle}>{wbe.code}</Text>
            </Col>
            <Col xs={12} sm={8}>
              <Text type="secondary" style={labelStyle}>
                Level
              </Text>
              <Text style={valueStyle}>{wbe.level}</Text>
            </Col>
            <Col xs={12} sm={8}>
              <Text type="secondary" style={labelStyle}>
                Parent
              </Text>
              <Text style={valueStyle}>{wbe.parent_name || "-"}</Text>
            </Col>
          </Row>
        </ExplorerCard>

        {/* System info - collapsed */}
        <Collapse ghost>
          <Collapse.Panel header="System Information" key="system">
            <Descriptions column={2} size="small">
              <Descriptions.Item label="ID">{wbe.id}</Descriptions.Item>
              <Descriptions.Item label="WBE ID">{wbe.wbs_element_id}</Descriptions.Item>
              <Descriptions.Item label="Project ID">
                {wbe.project_id}
              </Descriptions.Item>
              <Descriptions.Item label="Branch">{wbe.branch}</Descriptions.Item>
              <Descriptions.Item label="Created By">
                {wbe.created_by_name || "-"}
              </Descriptions.Item>
              <Descriptions.Item label="Created At">
                {formatTimestamp(wbe.created_at)}
              </Descriptions.Item>
              <Descriptions.Item label="Valid Time">
                {wbe.valid_time_formatted
                  ? formatTemporalRange(wbe.valid_time_formatted)
                  : "-"}
              </Descriptions.Item>
              <Descriptions.Item label="Transaction Time">
                {wbe.transaction_time_formatted
                  ? formatTemporalRange(wbe.transaction_time_formatted)
                  : "-"}
              </Descriptions.Item>
            </Descriptions>
          </Collapse.Panel>
        </Collapse>
      </div>

      <EVMAnalyzerModal
        open={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        evmMetrics={evmMetrics}
        timeSeries={timeSeries}
        loading={evmLoading || timeSeriesLoading}
        onGranularityChange={(g) => setGranularity(g)}
        currency={currency}
      />
    </>
  );
};
