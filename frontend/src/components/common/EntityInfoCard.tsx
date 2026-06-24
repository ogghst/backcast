import React from "react";
import { theme } from "antd";
import { CollapsibleCard } from "@/components/common/CollapsibleCard";

interface EntityInfoCardProps {
  title: string;
  id: string;
  collapsed?: boolean;
  children: React.ReactNode;
  /** Extra content rendered in the card header (e.g. action buttons). */
  extra?: React.ReactNode;
}

/**
 * EntityInfoCard - Shared wrapper for entity detail info cards.
 *
 * Provides consistent CollapsibleCard styling, title formatting,
 * and inner padding across all entity types.
 *
 * @example
 * ```tsx
 * <EntityInfoCard title="WBE Information" id="wbe-info-card" loading={isLoading}>
 *   <Descriptions {...entityInfoDescriptionsProps(token)}>
 *     <Descriptions.Item label="Level">L{wbe.level}</Descriptions.Item>
 *   </Descriptions>
 * </EntityInfoCard>
 * ```
 */
export const EntityInfoCard: React.FC<EntityInfoCardProps> = ({
  title,
  id,
  collapsed = true,
  children,
  extra,
}) => {
  const { token } = theme.useToken();

  return (
    <CollapsibleCard
      title={
        <span
          style={{
            fontSize: token.fontSizeLG,
            fontWeight: token.fontWeightStrong,
            color: token.colorText,
          }}
        >
          {title}
        </span>
      }
      id={id}
      collapsed={collapsed}
      extra={extra}
      style={{
        marginBottom: token.marginLG,
        borderRadius: token.borderRadiusLG,
        border: `1px solid ${token.colorBorder}`,
      }}
    >
      <div style={{ padding: token.paddingLG }}>{children}</div>
    </CollapsibleCard>
  );
};
