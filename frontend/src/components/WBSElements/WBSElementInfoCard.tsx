import { Descriptions, Typography, Tag } from "antd";
import type { WBSElementRead } from "@/api/generated";
import { EntityInfoCard } from "@/components/common/EntityInfoCard";
import { entityInfoDescriptionsProps } from "@/components/common/entityInfoDescriptionsProps";
import { formatDateTime } from "@/utils/formatters";
import { useExtendedToken } from "@/hooks/useToken";

interface WBSElementInfoCardProps {
  wbsElement: WBSElementRead;
  loading?: boolean;
}

export const WBSElementInfoCard = ({ wbsElement }: WBSElementInfoCardProps) => {
  const { token } = useExtendedToken();

  return (
    <EntityInfoCard title="WBS Element Information" id="wbe-info-card">
      <Descriptions {...entityInfoDescriptionsProps(token)}>
        <Descriptions.Item label="Level">
          <Tag
            color="cyan"
            style={{
              padding: `${token.paddingXS}px ${token.paddingSM}px`,
              borderRadius: token.borderRadiusSM,
            }}
          >
            L{wbsElement.level}
          </Tag>
        </Descriptions.Item>

        <Descriptions.Item label="Parent WBE">
          {wbsElement.parent_wbs_element_id ? wbsElement.parent_name || wbsElement.parent_wbs_element_id : "Project Root"}
        </Descriptions.Item>

        <Descriptions.Item label="WBS Element ID">
          <Typography.Text code copyable style={{ fontSize: token.fontSizeXS }}>
            {wbsElement.wbs_element_id}
          </Typography.Text>
        </Descriptions.Item>

        <Descriptions.Item label="Project ID">
          <Typography.Text code style={{ fontSize: token.fontSizeXS }}>
            {wbsElement.project_id}
          </Typography.Text>
        </Descriptions.Item>

        <Descriptions.Item label="Created">
          {formatDateTime(wbsElement.created_at)}
        </Descriptions.Item>

        <Descriptions.Item label="Created By">
          {wbsElement.created_by_name || "System"}
        </Descriptions.Item>
      </Descriptions>
    </EntityInfoCard>
  );
};
