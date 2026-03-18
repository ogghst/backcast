import React from "react";
import { Descriptions, Typography, Tag, Divider, theme, Space } from "antd";
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
            <Descriptions
              size="middle"
              column={{ xs: 1, sm: 2 }}
              colon={true}
              labelStyle={{
                fontWeight: token.fontWeightMedium,
                color: token.colorTextSecondary,
                fontSize: token.fontSize,
              }}
              contentStyle={{
                color: token.colorText,
                fontSize: token.fontSize,
              }}
            >
              <Descriptions.Item label="WBE ID">
                <Text style={{ color: token.colorText }}>
                  {wbe.wbe_id}
                </Text>
              </Descriptions.Item>

              <Descriptions.Item label="Project ID">
                <Text style={{ color: token.colorText }}>
                  {wbe.project_id}
                </Text>
              </Descriptions.Item>

              <Descriptions.Item label="Parent WBE ID">
                <Text style={{ color: token.colorText }}>
                  {wbe.parent_wbe_id || "-"}
                </Text>
              </Descriptions.Item>

              <Descriptions.Item label="Branch">
                <Tag
                  color={wbe.branch === "main" ? "blue" : "orange"}
                  style={{
                    padding: `${token.paddingXS}px ${token.paddingSM}px`,
                    borderRadius: token.borderRadiusSM,
                  }}
                >
                  {wbe.branch || "main"}
                </Tag>
              </Descriptions.Item>

              <Descriptions.Item label="Level">
                <Tag
                  color="cyan"
                  style={{
                    padding: `${token.paddingXS}px ${token.paddingSM}px`,
                    borderRadius: token.borderRadiusSM,
                  }}
                >
                  L{wbe.level}
                </Tag>
              </Descriptions.Item>

              <Descriptions.Item label="Revenue Allocation">
                <Text style={{ color: token.colorText }}>
                  {wbe.revenue_allocation
                    ? new Intl.NumberFormat("en-US", {
                        style: "currency",
                        currency: "EUR",
                      }).format(Number(wbe.revenue_allocation))
                    : "-"}
                </Text>
              </Descriptions.Item>
            </Descriptions>
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
            <Descriptions
              size="middle"
              column={{ xs: 1, sm: 2 }}
              colon={true}
              labelStyle={{
                fontWeight: token.fontWeightMedium,
                color: token.colorTextSecondary,
                fontSize: token.fontSize,
              }}
              contentStyle={{
                color: token.colorText,
                fontSize: token.fontSize,
              }}
            >
              <Descriptions.Item label="Created">
                <Text style={{ color: token.colorText }}>
                  {formatDateTime(wbe.created_at)}
                </Text>
              </Descriptions.Item>

              <Descriptions.Item label="Created By">
                <Text style={{ color: token.colorText }}>
                  {wbe.created_by_name || "System"}
                </Text>
              </Descriptions.Item>
            </Descriptions>
          </div>
        </Space>
      </div>
    </CollapsibleCard>
  );
};
