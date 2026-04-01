import React from "react";
import { Typography, Tag, Divider, theme, Space, Row, Col } from "antd";
import { WBERead } from "@/api/generated";
import { CollapsibleCard } from "@/components/common/CollapsibleCard";

const { Text, Paragraph, Title } = Typography;

interface WBEInfoCardProps {
  wbe: WBERead;
  loading?: boolean;
}

/**
 * WBEInfoCard - Collapsible card with additional WBE details.
 *
 * Displays description, branch, parent info, and metadata in a clean layout.
 * Defaults to collapsed state for progressive disclosure.
 */
export const WBEInfoCard = ({
  wbe,
  loading,
}: WBEInfoCardProps) => {
  const { token } = theme.useToken();

  // Format timestamps
  const formatDateTime = (dateString: string | null | undefined) => {
    if (!dateString) return "-";
    return new Date(dateString).toLocaleString();
  };

  return (
    <CollapsibleCard
      title={
        <span
          style={{
            fontSize: token.fontSizeLG,
            fontWeight: token.fontWeightSemiBold,
            color: token.colorText,
          }}
        >
          WBE Information
        </span>
      }
      id="wbe-info-card"
      collapsed={true}
      loading={loading}
      style={{
        marginBottom: token.marginLG,
        borderRadius: token.borderRadiusLG,
        border: `1px solid ${token.colorBorder}`,
      }}
    >
      <div style={{ padding: token.paddingLG }}>
        <Space direction="vertical" size={token.marginXL} style={{ width: "100%" }}>
          {/* Section 1: Description */}
          <div>
            <Title
              level={5}
              style={{
                margin: `0 0 ${token.marginMD}px 0`,
                fontSize: token.fontSizeLG,
                fontWeight: token.fontWeightSemiBold,
                color: token.colorText,
              }}
            >
              Description
            </Title>
            {wbe.description ? (
              <Paragraph
                style={{
                  margin: 0,
                  color: token.colorText,
                  fontSize: token.fontSize,
                  lineHeight: token.lineHeight,
                }}
              >
                {wbe.description}
              </Paragraph>
            ) : (
              <Text type="secondary">No description provided</Text>
            )}
          </div>

          <Divider style={{ margin: `${token.marginLG}px 0` }} />

          {/* Section 2: Technical Details */}
          <div>
            <Title
              level={5}
              style={{
                margin: `0 0 ${token.marginMD}px 0`,
                fontSize: token.fontSizeLG,
                fontWeight: token.fontWeightSemiBold,
                color: token.colorText,
              }}
            >
              Technical Details
            </Title>
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
                    WBE ID
                  </Text>
                  <Text
                    style={{
                      fontSize: token.fontSizeLG,
                      fontWeight: token.fontWeightSemiBold,
                      color: token.colorText,
                    }}
                  >
                    {wbe.wbe_id}
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
                    Project ID
                  </Text>
                  <Text
                    style={{
                      fontSize: token.fontSizeLG,
                      fontWeight: token.fontWeightSemiBold,
                      color: token.colorText,
                    }}
                  >
                    {wbe.project_id}
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
                    Parent WBE ID
                  </Text>
                  <Text
                    style={{
                      fontSize: token.fontSizeLG,
                      fontWeight: token.fontWeightSemiBold,
                      color: token.colorText,
                    }}
                  >
                    {wbe.parent_wbe_id || "-"}
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
                    Branch
                  </Text>
                  <Tag
                    color={wbe.branch === "main" ? "blue" : "orange"}
                    style={{
                      padding: `${token.paddingXS}px ${token.paddingSM}px`,
                      borderRadius: token.borderRadiusSM,
                    }}
                  >
                    {wbe.branch || "main"}
                  </Tag>
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
                    Level
                  </Text>
                  <Tag
                    color="cyan"
                    style={{
                      padding: `${token.paddingXS}px ${token.paddingSM}px`,
                      borderRadius: token.borderRadiusSM,
                    }}
                  >
                    L{wbe.level}
                  </Tag>
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
                    Revenue Allocation
                  </Text>
                  <Text
                    style={{
                      fontSize: token.fontSizeLG,
                      fontWeight: token.fontWeightSemiBold,
                      color: token.colorText,
                    }}
                  >
                    {wbe.revenue_allocation
                      ? new Intl.NumberFormat("en-US", {
                          style: "currency",
                          currency: "EUR",
                        }).format(Number(wbe.revenue_allocation))
                      : "-"}
                  </Text>
                </div>
              </Col>
            </Row>
          </div>

          <Divider style={{ margin: `${token.marginLG}px 0` }} />

          {/* Section 3: Audit Information */}
          <div>
            <Title
              level={5}
              style={{
                margin: `0 0 ${token.marginMD}px 0`,
                fontSize: token.fontSizeLG,
                fontWeight: token.fontWeightSemiBold,
                color: token.colorText,
              }}
            >
              Audit Information
            </Title>
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
                    Created
                  </Text>
                  <Text
                    style={{
                      fontSize: token.fontSizeLG,
                      fontWeight: token.fontWeightSemiBold,
                      color: token.colorText,
                    }}
                  >
                    {formatDateTime(wbe.created_at)}
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
                    Created By
                  </Text>
                  <Text
                    style={{
                      fontSize: token.fontSizeLG,
                      fontWeight: token.fontWeightSemiBold,
                      color: token.colorText,
                    }}
                  >
                    {wbe.created_by_name || "System"}
                  </Text>
                </div>
              </Col>
            </Row>
          </div>
        </Space>
      </div>
    </CollapsibleCard>
  );
};
