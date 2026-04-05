import { useState } from "react";
import {
  Spin,
  Alert,
  Row,
  Col,
  Tag,
  Space,
  Statistic,
  Typography,
  Descriptions,
  theme,
  Collapse,
  Button,
} from "antd";
import {
  EditOutlined,
  FileTextOutlined,
  DollarOutlined,
  WarningOutlined,
  ThunderboltOutlined,
  LineChartOutlined,
} from "@ant-design/icons";
import { ExplorerCard } from "./ExplorerCard";
import { EVMAnalyzerModal } from "@/features/evm/components/EVMAnalyzerModal";
import { useEVMMetrics, useEVMTimeSeries } from "@/features/evm/api/useEVMMetrics";
import { useProject } from "@/features/projects/api/useProjects";
import { getProjectStatusColor } from "@/lib/status";
import { EntityType } from "@/features/evm/types";
import type { EVMTimeSeriesGranularity } from "@/features/evm/types";
import { formatCurrency, formatDate, formatTimestamp, calculateDuration } from "./shared/formatters";
import { KPIStrip, BudgetOverviewChart, VarianceChart, PerformanceRadar } from "./charts";

const { Text } = Typography;

interface ProjectDetailCardsProps {
  projectId: string;
}

export const ProjectDetailCards = ({ projectId }: ProjectDetailCardsProps) => {
  const { token } = theme.useToken();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [granularity, setGranularity] = useState<EVMTimeSeriesGranularity>(
    "week",
  );

  const { data: project, isLoading, error } = useProject(projectId);
  const { data: evmMetrics, isLoading: evmLoading } = useEVMMetrics(
    EntityType.PROJECT,
    projectId,
  );
  const { data: timeSeries, isLoading: timeSeriesLoading } =
    useEVMTimeSeries(EntityType.PROJECT, projectId, granularity);

  if (isLoading) {
    return (
      <div style={{ textAlign: "center", padding: token.paddingXXL }}>
        <Spin size="large" />
      </div>
    );
  }

  if (error || !project) {
    return (
      <Alert
        type="error"
        description={
          error instanceof Error ? error.message : "Failed to load Project"
        }
        showIcon
        style={{ margin: token.paddingLG }}
      />
    );
  }

  const budgetVariance =
    project.budget && project.contract_value
      ? Number(project.contract_value) - Number(project.budget)
      : null;

  const labelStyle: React.CSSProperties = {
    fontSize: token.fontSizeSM,
    display: "block",
    marginBottom: token.paddingXS,
    fontWeight: token.fontWeightMedium,
    color: token.colorTextSecondary,
  };

  const valueStyle: React.CSSProperties = {
    fontSize: token.fontSizeLG,
    fontWeight: token.fontWeightSemiBold,
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
            fontWeight: token.fontWeightSemiBold,
          }}
        >
          {project.name}
        </Text>
        <Space>
          <Tag
            color={getProjectStatusColor(project.status)}
            style={{
              fontSize: token.fontSize,
              padding: `${token.paddingXS}px ${token.paddingSM}px`,
              borderRadius: token.borderRadius,
              fontWeight: token.fontWeightMedium,
              margin: 0,
            }}
          >
            {project.status || "Draft"}
          </Tag>
          <Button type="text" icon={<EditOutlined />} size="small" />
        </Space>
      </div>

      {/* Summary Strip */}
      <div style={{ padding: `0 ${token.paddingLG}px ${token.paddingSM}px` }}>
        <Row gutter={[token.marginMD, token.marginSM]}>
          <Col xs={8}>
            <Statistic
              title="Budget"
              value={Number(project.budget) || 0}
              precision={0}
              prefix="€"
              valueStyle={{ fontSize: token.fontSizeLG, color: token.colorText }}
            />
          </Col>
          <Col xs={8}>
            <Statistic
              title="Variance"
              value={budgetVariance ?? 0}
              precision={0}
              prefix="€"
              valueStyle={{
                fontSize: token.fontSizeLG,
                color:
                  budgetVariance !== null
                    ? budgetVariance >= 0
                      ? token.colorSuccess
                      : token.colorError
                    : token.colorTextSecondary,
              }}
            />
          </Col>
          <Col xs={8}>
            <Statistic
              title="Duration"
              value={calculateDuration(project.start_date, project.end_date) || "-"}
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
              <ExplorerCard title="Budget Overview" icon={<DollarOutlined />}>
                <BudgetOverviewChart metrics={evmMetrics} height={200} />
              </ExplorerCard>
            </Col>
            <Col xs={24} lg={12}>
              <ExplorerCard title="Variance Analysis" icon={<WarningOutlined />}>
                <VarianceChart metrics={evmMetrics} height={160} />
              </ExplorerCard>
            </Col>
          </Row>
        )}

        {/* Performance Radar */}
        {evmMetrics && evmMetrics.bac > 0 && (
          <ExplorerCard
            title="Performance Overview"
            icon={<ThunderboltOutlined />}
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
          >
            <PerformanceRadar metrics={evmMetrics} height={250} />
          </ExplorerCard>
        )}

        {/* Scope & Timeline - condensed */}
        <ExplorerCard title="Details" icon={<FileTextOutlined />}>
          {project.description && (
            <Text
              type="secondary"
              style={{ display: "block", marginBottom: token.paddingMD }}
            >
              {project.description}
            </Text>
          )}
          <Row gutter={[token.marginLG, token.marginMD]}>
            <Col xs={12} sm={8}>
              <Text type="secondary" style={labelStyle}>
                Code
              </Text>
              <Text style={valueStyle}>{project.code}</Text>
            </Col>
            <Col xs={12} sm={8}>
              <Text type="secondary" style={labelStyle}>
                Status
              </Text>
              <Tag
                color={getProjectStatusColor(project.status)}
                style={{
                  fontSize: token.fontSize,
                  padding: `${token.paddingXS}px ${token.paddingSM}px`,
                  borderRadius: token.borderRadius,
                  fontWeight: token.fontWeightMedium,
                  margin: 0,
                }}
              >
                {project.status || "Draft"}
              </Tag>
            </Col>
            {calculateDuration(project.start_date, project.end_date) && (
              <Col xs={12} sm={8}>
                <Text type="secondary" style={labelStyle}>
                  Duration
                </Text>
                <Text style={valueStyle}>
                  {calculateDuration(project.start_date, project.end_date)}
                </Text>
              </Col>
            )}
            <Col xs={12} sm={8}>
              <Text type="secondary" style={labelStyle}>
                Start
              </Text>
              <Text style={valueStyle}>
                {formatDate(project.start_date)}
              </Text>
            </Col>
            <Col xs={12} sm={8}>
              <Text type="secondary" style={labelStyle}>
                End
              </Text>
              <Text style={valueStyle}>
                {formatDate(project.end_date)}
              </Text>
            </Col>
            <Col xs={12} sm={8}>
              <Text type="secondary" style={labelStyle}>
                Budget
              </Text>
              <Text style={valueStyle}>
                {formatCurrency(project.budget)}
              </Text>
            </Col>
          </Row>
        </ExplorerCard>

        {/* System info - collapsed by default */}
        <Collapse ghost>
          <Collapse.Panel header="System Information" key="system">
            <Descriptions column={2} size="small">
              <Descriptions.Item label="ID">{project.id}</Descriptions.Item>
              <Descriptions.Item label="Project ID">
                {project.project_id}
              </Descriptions.Item>
              <Descriptions.Item label="Branch">
                {project.branch}
              </Descriptions.Item>
              <Descriptions.Item label="Created By">
                {project.created_by_name || "-"}
              </Descriptions.Item>
              <Descriptions.Item label="Created At">
                {formatTimestamp(project.created_at)}
              </Descriptions.Item>
              <Descriptions.Item label="Valid Time">
                {formatTimestamp(project.valid_time)}
              </Descriptions.Item>
              <Descriptions.Item label="Transaction Time">
                {formatTimestamp(project.transaction_time)}
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
      />
    </>
  );
};
