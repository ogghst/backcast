import React from "react";
import { Descriptions, Typography, Tag, theme } from "antd";
import { WBERead } from "@/api/generated";
import { CollapsibleCard } from "@/components/common/CollapsibleCard";
import { formatDateTime } from "@/utils/formatters";

interface WBEInfoCardProps {
  wbe: WBERead;
  loading?: boolean;
}

/**
 * WBEInfoCard - Collapsible card with additional WBE details.
 *
 * Displays level, parent info, revenue, technical IDs, and audit info.
 * Defaults to collapsed state for progressive disclosure.
 */
export const WBEInfoCard = ({
  wbe,
  loading,
}: WBEInfoCardProps) => {
  const { token } = theme.useToken();

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

          <Descriptions.Item label="Parent WBE">
            {wbe.parent_wbe_id ? wbe.parent_name || wbe.parent_wbe_id : "Project Root"}
          </Descriptions.Item>

          <Descriptions.Item label="WBE ID">
            <Typography.Text code copyable style={{ fontSize: token.fontSizeXS }}>
              {wbe.wbe_id}
            </Typography.Text>
          </Descriptions.Item>

          <Descriptions.Item label="Project ID">
            <Typography.Text code style={{ fontSize: token.fontSizeXS }}>
              {wbe.project_id}
            </Typography.Text>
          </Descriptions.Item>

          <Descriptions.Item label="Created">
            {formatDateTime(wbe.created_at)}
          </Descriptions.Item>

          <Descriptions.Item label="Created By">
            {wbe.created_by_name || "System"}
          </Descriptions.Item>
        </Descriptions>
      </div>
    </CollapsibleCard>
  );
};
