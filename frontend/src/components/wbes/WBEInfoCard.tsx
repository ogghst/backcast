import { Descriptions, Typography, Tag, theme } from "antd";
import type { WBERead } from "@/api/generated";
import { EntityInfoCard } from "@/components/common/EntityInfoCard";
import { entityInfoDescriptionsProps } from "@/components/common/entityInfoDescriptionsProps";
import { formatDateTime } from "@/utils/formatters";

interface WBEInfoCardProps {
  wbe: WBERead;
  loading?: boolean;
}

export const WBEInfoCard = ({ wbe }: WBEInfoCardProps) => {
  const { token } = theme.useToken();

  return (
    <EntityInfoCard title="WBE Information" id="wbe-info-card">
      <Descriptions {...entityInfoDescriptionsProps(token)}>
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
    </EntityInfoCard>
  );
};
