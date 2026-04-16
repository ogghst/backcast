/**
 * ProjectDetailPanels Component
 *
 * Displays detailed information about a Project organized in collapsible panels.
 *
 * Panels:
 * - Scope: name, code, description, status
 * - Time: start_date, end_date with duration
 * - Costs: budget, contract_value with variance
 * - System Info: id, project_id, branch, timestamps
 * - WBE: placeholder for future work breakdown elements
 *
 * @module components/projects
 */

import { useMemo } from "react";
import {
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
import { ProjectRead } from "@/api/generated";
import { getProjectStatusColor } from "@/lib/status";
import { formatDate, formatDateTime, formatTemporalRange, calculateDuration as formatDuration } from "@/utils/formatters";

const { Text } = Typography;

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
 * Props for ProjectDetailPanels component
 */
interface ProjectDetailPanelsProps {
  /** Project data to display */
  project: ProjectRead;
}

/** Panel keys that should be expanded by default. */
const DEFAULT_ACTIVE_PANELS = ["scope", "costs"] as const;

/**
 * ProjectDetailPanels Component
 *
 * Renders a comprehensive collapsible panel view for a Project.
 * Extracted from ProjectDetail for reuse across the application.
 */
export const ProjectDetailPanels: React.FC<ProjectDetailPanelsProps> = ({ project }) => {
  const { token } = theme.useToken();

  /**
   * Build collapse panel items from project data.
   * Memoized to prevent unnecessary recalculations.
   */
  const collapseItems: CollapseProps["items"] = useMemo(() => {
    // Calculate budget variance for the Costs panel
    const budgetVariance =
      project.budget && project.contract_value
        ? Number(project.contract_value) - Number(project.budget)
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
            {project.description && (
              <Text
                type="secondary"
                style={{
                  display: "block",
                  marginBottom: token.paddingMD,
                  fontSize: token.fontSize,
                }}
              >
                {project.description}
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
                    {project.code}
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
                  {formatDate(project.start_date)}
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
                  {formatDate(project.end_date)}
                </Text>
              </div>
            </Col>
            {formatDuration(project.start_date, project.end_date) && (
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
                    {formatDuration(project.start_date, project.end_date)}
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
                  {formatCurrency(project.budget)}
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
                  {formatCurrency(project.contract_value)}
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
            <Descriptions.Item label="ID">{project.id}</Descriptions.Item>
            <Descriptions.Item label="Project ID">{project.project_id}</Descriptions.Item>
            <Descriptions.Item label="Branch">{project.branch}</Descriptions.Item>
            <Descriptions.Item label="Created By">
              {project.created_by_name || "-"}
            </Descriptions.Item>
            <Descriptions.Item label="Created At">
              {formatDateTime(project.created_at)}
            </Descriptions.Item>
            <Descriptions.Item label="Valid Time">
              {project.valid_time_formatted?.lower_formatted || formatTemporalRange(project.valid_time)}
            </Descriptions.Item>
            <Descriptions.Item label="Transaction Time">
              {project.transaction_time_formatted?.lower_formatted || formatTemporalRange(project.transaction_time)}
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
  }, [project, token]);

  return (
    <Collapse
      defaultActiveKey={[...DEFAULT_ACTIVE_PANELS]}
      items={collapseItems}
      bordered
      style={{
        backgroundColor: "transparent",
      }}
    />
  );
};

export default ProjectDetailPanels;
