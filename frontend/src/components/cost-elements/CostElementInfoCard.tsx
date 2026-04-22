import { Descriptions, Typography, Tag, theme } from "antd";
import type { CostElementRead } from "@/api/generated";
import { EntityInfoCard } from "@/components/common/EntityInfoCard";
import { entityInfoDescriptionsProps } from "@/components/common/entityInfoDescriptionsProps";
import { formatTemporalRange } from "@/utils/formatters";

interface CostElementInfoCardProps {
  costElement: CostElementRead;
  loading?: boolean;
}

export const CostElementInfoCard = ({
  costElement,
}: CostElementInfoCardProps) => {
  const { token } = theme.useToken();

  return (
    <EntityInfoCard
      title="Cost Element Information"
      id="cost-element-info-card"
    >
      <Descriptions {...entityInfoDescriptionsProps(token)}>
        <Descriptions.Item label="Type">
          <Tag
            color="purple"
            style={{
              padding: `${token.paddingXS}px ${token.paddingSM}px`,
              borderRadius: token.borderRadiusSM,
            }}
          >
            {costElement.cost_element_type_code ||
              costElement.cost_element_type_name ||
              "-"}
          </Tag>
        </Descriptions.Item>

        <Descriptions.Item label="WBE">
          {costElement.wbe_name || "-"}
        </Descriptions.Item>

        <Descriptions.Item label="Cost Element ID">
          <Typography.Text code copyable style={{ fontSize: token.fontSizeXS }}>
            {costElement.cost_element_id}
          </Typography.Text>
        </Descriptions.Item>

        <Descriptions.Item label="Branch">
          <Tag
            color={costElement.branch === "main" ? "blue" : "orange"}
            style={{
              padding: `${token.paddingXS}px ${token.paddingSM}px`,
              borderRadius: token.borderRadiusSM,
            }}
          >
            {costElement.branch}
          </Tag>
        </Descriptions.Item>

        <Descriptions.Item label="Created By">
          {costElement.created_by || "System"}
        </Descriptions.Item>

        <Descriptions.Item label="Valid Time">
          {costElement.valid_time_formatted
            ? formatTemporalRange(costElement.valid_time_formatted)
            : "-"}
        </Descriptions.Item>
      </Descriptions>
    </EntityInfoCard>
  );
};
