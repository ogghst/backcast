import React from "react";
import { Card, Tag, Typography, theme, Row, Col } from "antd";
import { WBERead } from "@/api/generated";

const { Text, Title } = Typography;

interface WBEHeaderCardProps {
  wbe: WBERead;
  loading?: boolean;
}

/**
 * WBEHeaderCard - Compact card displaying key WBE information.
 *
 * Shows WBE name, code, level, budget, and key metrics in a refined layout.
 */
export const WBEHeaderCard = ({
  wbe,
  loading,
}: WBEHeaderCardProps) => {
  const { token } = theme.useToken();

  // Format currency values
  const formatCurrency = (value: string | null | undefined) => {
    if (!value) return "-";
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "EUR",
    }).format(Number(value));
  };

  // Get status color - WBEs don't have a status field like projects, so we use branch color
  const getBranchColor = (branch: string) => {
    if (branch === "main") return "blue";
    if (branch.startsWith("BR-")) return "orange";
    return "default";
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
      {/* Row 1: Full WBE Name */}
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
          {wbe.name}
        </Title>
      </div>

      {/* Row 2: Code, Budget, Level, Parent, Branch */}
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
              {wbe.code}
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
              Budget Allocation
            </Text>
            <Text
              style={{
                fontSize: token.fontSizeLG,
                fontWeight: token.fontWeightSemiBold,
                color: token.colorText,
              }}
            >
              {formatCurrency(wbe.budget_allocation)}
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
              Level
            </Text>
            <Tag
              color="cyan"
              style={{
                fontSize: token.fontSizeLG,
                padding: `${token.paddingXS}px ${token.paddingMD}px`,
                borderRadius: token.borderRadius,
                fontWeight: token.fontWeightMedium,
                margin: 0,
              }}
            >
              L{wbe.level}
            </Tag>
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
              Parent WBE
            </Text>
            <Text
              style={{
                fontSize: token.fontSizeLG,
                fontWeight: token.fontWeightSemiBold,
                color: token.colorText,
              }}
            >
              {wbe.parent_wbe_id ? wbe.parent_name || wbe.parent_wbe_id : "Project Root"}
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
              Branch
            </Text>
            <Tag
              color={getBranchColor(wbe.branch)}
              style={{
                fontSize: token.fontSizeLG,
                padding: `${token.paddingXS}px ${token.paddingMD}px`,
                borderRadius: token.borderRadius,
                fontWeight: token.fontWeightMedium,
                margin: 0,
              }}
            >
              {wbe.branch || "main"}
            </Tag>
          </div>
        </Col>
      </Row>
    </Card>
  );
};
