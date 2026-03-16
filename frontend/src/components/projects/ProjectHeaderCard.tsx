import React from "react";
import { Card, Tag, Typography, theme, Row, Col } from "antd";
import { ProjectRead } from "@/api/generated";
import { getProjectStatusColor } from "@/lib/status";

const { Text, Title } = Typography;

interface ProjectHeaderCardProps {
  project: ProjectRead;
  loading?: boolean;
}

/**
 * ProjectHeaderCard - Compact card displaying key project information.
 *
 * Shows project name, code, status, and key metrics in a refined layout.
 */
export const ProjectHeaderCard = ({
  project,
  loading,
}: ProjectHeaderCardProps) => {
  const { token } = theme.useToken();

  // Format currency values
  const formatCurrency = (value: number | string | null | undefined) => {
    if (!value) return "-";
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "EUR",
    }).format(Number(value));
  };

  // Format date values
  const formatDate = (dateString: string | null | undefined) => {
    if (!dateString) return "-";
    return new Date(dateString).toLocaleDateString();
  };

  return (
    <Card
      loading={loading}
      style={{
        marginBottom: token.marginLG,
        borderRadius: token.borderRadiusLG,
        border: `1px solid ${token.colorBorder}`,
      }}
      styles={{
        body: {
          padding: token.paddingXL,
        },
      }}
    >
      {/* Row 1: Full Project Name */}
      <div
        style={{
          marginBottom: token.marginLG,
        }}
      >
        <Title
          level={3}
          style={{
            margin: 0,
            fontSize: token.fontSizeXXL,
            fontWeight: token.fontWeightSemiBold,
            color: token.colorText,
          }}
        >
          {project.name}
        </Title>
      </div>

      {/* Row 2: Code, Budget, Contract Value, Date Range, Status */}
      <Row gutter={[token.marginLG, token.marginMD]}>
        <Col xs={12} sm={8} md={4}>
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
        <Col xs={12} sm={8} md={4}>
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
        <Col xs={12} sm={8} md={4}>
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
        <Col xs={12} sm={12} md={6}>
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
              Date Range
            </Text>
            <Text
              style={{
                fontSize: token.fontSizeLG,
                fontWeight: token.fontWeightSemiBold,
                color: token.colorText,
              }}
            >
              {formatDate(project.start_date)} → {formatDate(project.end_date)}
            </Text>
          </div>
        </Col>
        <Col xs={12} sm={12} md={6}>
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
                fontSize: token.fontSizeLG,
                padding: `${token.paddingXS}px ${token.paddingMD}px`,
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
    </Card>
  );
};
