/**
 * ProjectDetail Page Component
 *
 * Displays detailed information about a Project organized in collapsible panels,
 * along with EVM metrics and analysis capabilities.
 *
 * Panels:
 * - Scope: name, code, description, status
 * - Time: start_date, end_date with duration
 * - Costs: budget, contract_value with variance
 * - System Info: id, project_id, branch, timestamps
 * - WBE: placeholder for future work breakdown elements
 *
 * @module features/projects/pages
 */

import { useState, useMemo } from "react";
import {
  Spin,
  Alert,
  Collapse,
  Row,
  Col,
  Tag,
  Typography,
  Empty,
  Descriptions,
  theme,
  Space,
  type CollapseProps,
} from "antd";
import {
  FileTextOutlined,
  ClockCircleOutlined,
  DollarOutlined,
  InfoCircleOutlined,
  ApartmentOutlined,
} from "@ant-design/icons";
import { useParams } from "react-router-dom";
import { EVMSummaryView } from "@/features/evm/components/EVMSummaryView";
import { EVMAnalyzerModal } from "@/features/evm/components/EVMAnalyzerModal";
import { useEVMMetrics, useEVMTimeSeries } from "@/features/evm/api/useEVMMetrics";
import { useProject } from "../api/useProjects";
import { getProjectStatusColor } from "@/lib/status";
import { EntityType } from "@/features/evm/types";
import type { EVMTimeSeriesGranularity } from "@/features/evm/types";

const { Title, Text } = Typography;

/** Currency formatter for EUR values. */
const currencyFormatter = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "EUR",
});

/**
 * Format a numeric value as EUR currency.
 * @param value - The value to format
 * @returns Formatted currency string or "-" if falsy
 */
const formatCurrency = (value: string | number | null | undefined): string => {
  if (!value) return "-";
  return currencyFormatter.format(Number(value));
};

/**
 * Format an ISO date string for display.
 * @param dateString - ISO date string
 * @returns Locale-formatted date string or "-" if falsy
 */
const formatDate = (dateString: string | null | undefined): string => {
  if (!dateString) return "-";
  return new Date(dateString).toLocaleDateString();
};

/**
 * Format an ISO timestamp string for display with time.
 * @param timestamp - ISO timestamp string
 * @returns Locale-formatted datetime string or "-" if falsy
 */
const formatTimestamp = (timestamp: string | null | undefined): string => {
  if (!timestamp) return "-";
  return new Date(timestamp).toLocaleString();
};

/**
 * Calculate the duration in days between two dates.
 * @param start - Start date string
 * @param end - End date string
 * @returns Duration string like "365 days" or null if dates are missing
 */
const calculateDuration = (
  start: string | null | undefined,
  end: string | null | undefined
): string | null => {
  if (!start || !end) return null;
  const days = Math.ceil(
    (new Date(end).getTime() - new Date(start).getTime()) / (1000 * 60 * 60 * 24)
  );
  return `${Math.abs(days)} day${Math.abs(days) !== 1 ? "s" : ""}`;
};

/**
 * Props for ProjectDetail component
 */
interface ProjectDetailProps {
  /** Project ID (from route params if not provided) */
  projectId?: string;
}

/** Panel keys that should be expanded by default. */
const DEFAULT_ACTIVE_PANELS = ["scope", "costs"] as const;

/**
 * ProjectDetail Component
 *
 * Renders a comprehensive detail view for a Project,
 * including collapsible info panels, EVM metrics, and analysis capabilities.
 */
export const ProjectDetail: React.FC<ProjectDetailProps> = ({ projectId: propProjectId }) => {
  const { token } = theme.useToken();
  const { projectId: paramProjectId } = useParams<{ projectId?: string }>();
  const projectId = propProjectId || paramProjectId;

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [granularity, setGranularity] = useState<EVMTimeSeriesGranularity>("week");

  // Fetch Project data
  const { data: projectData, isLoading: projectLoading, error: projectError } = useProject(
    projectId || ""
  );

  // Fetch EVM metrics for this Project
  const { data: evmMetrics, isLoading: evmLoading } = useEVMMetrics(
    EntityType.PROJECT,
    projectId || "",
    {
      enabled: !!projectId,
    }
  );

  // Fetch time-series data for charts
  const { data: timeSeries, isLoading: timeSeriesLoading } = useEVMTimeSeries(
    EntityType.PROJECT,
    projectId || "",
    granularity,
    {
      enabled: !!projectId,
    }
  );

  /**
   * Build collapse panel items from project data.
   * Memoized to prevent unnecessary recalculations.
   */
  const collapseItems: CollapseProps["items"] = useMemo(() => {
    if (!projectData) return [];

    // Calculate budget variance for the Costs panel
    const budgetVariance =
      projectData.budget && projectData.contract_value
        ? Number(projectData.contract_value) - Number(projectData.budget)
        : null;

    return [
      {
        key: "scope",
        label: (
          <Space>
            <FileTextOutlined />
            <span>Scope</span>
          </Space>
        ),
        children: (
          <div>
            {projectData.description && (
              <Text
                type="secondary"
                style={{
                  display: "block",
                  marginBottom: token.paddingMD,
                  fontSize: token.fontSize,
                }}
              >
                {projectData.description}
              </Text>
            )}
            <Row gutter={[token.marginLG, token.marginMD]}>
              <Col xs={12} sm={8}>
                <div>
                  <Text
                    type="secondary"
                    style={{
                      fontSize: token.fontSizeSM,
                      display: "block",
                      marginBottom: token.paddingXS,
                      fontWeight: token.fontWeightMedium,
                    }}
                  >
                    Code
                  </Text>
                  <Text
                    style={{
                      fontSize: token.fontSizeLG,
                      fontWeight: token.fontWeightSemiBold,
                      color: token.colorText,
                    }}
                  >
                    {projectData.code}
                  </Text>
                </div>
              </Col>
              <Col xs={12} sm={8}>
                <div>
                  <Text
                    type="secondary"
                    style={{
                      fontSize: token.fontSizeSM,
                      display: "block",
                      marginBottom: token.paddingXS,
                      fontWeight: token.fontWeightMedium,
                    }}
                  >
                    Status
                  </Text>
                  <Tag
                    color={getProjectStatusColor(projectData.status)}
                    style={{
                      fontSize: token.fontSize,
                      padding: `${token.paddingXS}px ${token.paddingSM}px`,
                      borderRadius: token.borderRadius,
                      fontWeight: token.fontWeightMedium,
                      margin: 0,
                    }}
                  >
                    {projectData.status || "Draft"}
                  </Tag>
                </div>
              </Col>
            </Row>
          </div>
        ),
      },
      {
        key: "time",
        label: (
          <Space>
            <ClockCircleOutlined />
            <span>Time</span>
          </Space>
        ),
        children: (
          <Row gutter={[token.marginLG, token.marginMD]}>
            <Col xs={12} sm={8}>
              <div>
                <Text
                  type="secondary"
                  style={{
                    fontSize: token.fontSizeSM,
                    display: "block",
                    marginBottom: token.paddingXS,
                    fontWeight: token.fontWeightMedium,
                  }}
                >
                  Start Date
                </Text>
                <Text
                  style={{
                    fontSize: token.fontSizeLG,
                    fontWeight: token.fontWeightSemiBold,
                    color: token.colorText,
                  }}
                >
                  {formatDate(projectData.start_date)}
                </Text>
              </div>
            </Col>
            <Col xs={12} sm={8}>
              <div>
                <Text
                  type="secondary"
                  style={{
                    fontSize: token.fontSizeSM,
                    display: "block",
                    marginBottom: token.paddingXS,
                    fontWeight: token.fontWeightMedium,
                  }}
                >
                  End Date
                </Text>
                <Text
                  style={{
                    fontSize: token.fontSizeLG,
                    fontWeight: token.fontWeightSemiBold,
                    color: token.colorText,
                  }}
                >
                  {formatDate(projectData.end_date)}
                </Text>
              </div>
            </Col>
            {calculateDuration(projectData.start_date, projectData.end_date) && (
              <Col xs={12} sm={8}>
                <div>
                  <Text
                    type="secondary"
                    style={{
                      fontSize: token.fontSizeSM,
                      display: "block",
                      marginBottom: token.paddingXS,
                      fontWeight: token.fontWeightMedium,
                    }}
                  >
                    Duration
                  </Text>
                  <Text
                    style={{
                      fontSize: token.fontSizeLG,
                      fontWeight: token.fontWeightSemiBold,
                      color: token.colorText,
                    }}
                  >
                    {calculateDuration(projectData.start_date, projectData.end_date)}
                  </Text>
                </div>
              </Col>
            )}
          </Row>
        ),
      },
      {
        key: "costs",
        label: (
          <Space>
            <DollarOutlined />
            <span>Costs</span>
          </Space>
        ),
        children: (
          <Row gutter={[token.marginLG, token.marginMD]}>
            <Col xs={12} sm={8}>
              <div>
                <Text
                  type="secondary"
                  style={{
                    fontSize: token.fontSizeSM,
                    display: "block",
                    marginBottom: token.paddingXS,
                    fontWeight: token.fontWeightMedium,
                  }}
                >
                  Budget
                </Text>
                <Text
                  style={{
                    fontSize: token.fontSizeLG,
                    fontWeight: token.fontWeightSemiBold,
                    color: token.colorText,
                  }}
                >
                  {formatCurrency(projectData.budget)}
                </Text>
              </div>
            </Col>
            <Col xs={12} sm={8}>
              <div>
                <Text
                  type="secondary"
                  style={{
                    fontSize: token.fontSizeSM,
                    display: "block",
                    marginBottom: token.paddingXS,
                    fontWeight: token.fontWeightMedium,
                  }}
                >
                  Contract Value
                </Text>
                <Text
                  style={{
                    fontSize: token.fontSizeLG,
                    fontWeight: token.fontWeightSemiBold,
                    color: token.colorText,
                  }}
                >
                  {formatCurrency(projectData.contract_value)}
                </Text>
              </div>
            </Col>
            {budgetVariance !== null && (
              <Col xs={12} sm={8}>
                <div>
                  <Text
                    type="secondary"
                    style={{
                      fontSize: token.fontSizeSM,
                      display: "block",
                      marginBottom: token.paddingXS,
                      fontWeight: token.fontWeightMedium,
                    }}
                  >
                    Variance
                  </Text>
                  <Text
                    style={{
                      fontSize: token.fontSizeLG,
                      fontWeight: token.fontWeightSemiBold,
                      color: budgetVariance >= 0 ? token.colorSuccess : token.colorError,
                    }}
                  >
                    {formatCurrency(budgetVariance)}
                  </Text>
                </div>
              </Col>
            )}
          </Row>
        ),
      },
      {
        key: "system",
        label: (
          <Space>
            <InfoCircleOutlined />
            <span>System Info</span>
          </Space>
        ),
        children: (
          <Descriptions column={2} size="small">
            <Descriptions.Item label="ID">{projectData.id}</Descriptions.Item>
            <Descriptions.Item label="Project ID">{projectData.project_id}</Descriptions.Item>
            <Descriptions.Item label="Branch">{projectData.branch}</Descriptions.Item>
            <Descriptions.Item label="Created By">
              {projectData.created_by_name || "-"}
            </Descriptions.Item>
            <Descriptions.Item label="Created At">
              {formatTimestamp(projectData.created_at)}
            </Descriptions.Item>
            <Descriptions.Item label="Valid Time">
              {formatTimestamp(projectData.valid_time)}
            </Descriptions.Item>
            <Descriptions.Item label="Transaction Time">
              {formatTimestamp(projectData.transaction_time)}
            </Descriptions.Item>
          </Descriptions>
        ),
      },
      {
        key: "wbe",
        label: (
          <Space>
            <ApartmentOutlined />
            <span>WBE</span>
          </Space>
        ),
        children: (
          <Empty
            description="Work Breakdown Elements will appear here"
            image={Empty.PRESENTED_IMAGE_SIMPLE}
          />
        ),
      },
    ];
  }, [projectData, token]);

  /**
   * Render loading state
   */
  if (projectLoading) {
    return (
      <div style={{ textAlign: "center", padding: token.paddingXL }}>
        <Spin size="large" />
        <div style={{ marginTop: token.paddingMD }}>Loading Project details...</div>
      </div>
    );
  }

  /**
   * Render error state
   */
  if (projectError || !projectData) {
    return (
      <Alert
        title="Error"
        description={projectError instanceof Error ? projectError.message : "Failed to load Project"}
        type="error"
        showIcon
        style={{ margin: token.paddingLG }}
      />
    );
  }

  /**
   * Handle granularity change
   */
  const handleGranularityChange = (newGranularity: EVMTimeSeriesGranularity) => {
    setGranularity(newGranularity);
  };

  /**
   * Handle opening the EVM Analyzer modal
   */
  const handleAdvancedClick = () => {
    setIsModalOpen(true);
  };

  /**
   * Handle closing the EVM Analyzer modal
   */
  const handleCloseModal = () => {
    setIsModalOpen(false);
  };

  return (
    <div style={{ padding: token.paddingLG }}>
      {/* Project Title */}
      <Title
        level={2}
        style={{
          marginBottom: token.marginLG,
          fontWeight: token.fontWeightSemiBold,
        }}
      >
        {projectData.name}
      </Title>

      {/* Collapsible Info Panels */}
      <Collapse
        defaultActiveKey={[...DEFAULT_ACTIVE_PANELS]}
        items={collapseItems}
        bordered
        style={{
          marginBottom: token.marginLG,
          backgroundColor: "transparent",
        }}
      />

      {/* EVM Summary Section */}
      {evmMetrics && !evmLoading ? (
        <EVMSummaryView
          metrics={evmMetrics}
          onAdvanced={handleAdvancedClick}
        />
      ) : evmLoading ? (
        <div style={{ textAlign: "center", padding: token.paddingXL }}>
          <Spin size="large" />
          <div style={{ marginTop: token.paddingMD }}>Loading EVM metrics...</div>
        </div>
      ) : null}

      {/* EVM Analyzer Modal */}
      <EVMAnalyzerModal
        open={isModalOpen}
        onClose={handleCloseModal}
        evmMetrics={evmMetrics}
        timeSeries={timeSeries}
        loading={evmLoading || timeSeriesLoading}
        onGranularityChange={handleGranularityChange}
      />
    </div>
  );
};

export default ProjectDetail;
