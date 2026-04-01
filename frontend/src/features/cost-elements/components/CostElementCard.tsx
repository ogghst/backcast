import { Button, Space, Tag, theme } from "antd";
import {
  EditOutlined,
  DeleteOutlined,
  HistoryOutlined,
  EyeOutlined,
  DollarOutlined,
} from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import type { CostElementRead } from "@/api/generated";
import { Can } from "@/components/auth/Can";
import { EntityCard } from "@/components/common/EntityCard";

interface CostElementCardProps {
  costElement: CostElementRead;
  typeNames: Record<string, string>;
  onEdit: (costElement: CostElementRead) => void;
  onDelete: (id: string) => void;
  onViewHistory: (costElement: CostElementRead) => void;
}

const formatCurrency = (val: number | null | undefined) =>
  val ? `\u20AC${Number(val).toLocaleString()}` : "-";

export const CostElementCard = ({
  costElement,
  typeNames,
  onEdit,
  onDelete,
  onViewHistory,
}: CostElementCardProps) => {
  const { token } = theme.useToken();
  const navigate = useNavigate();

  const typeName =
    costElement.cost_element_type_name ||
    typeNames[costElement.cost_element_type_id] ||
    "-";

  return (
    <EntityCard
      title={costElement.name}
      subtitle={costElement.code}
      badge={<Tag>{typeName}</Tag>}
      onClick={() =>
        navigate(`/cost-elements/${costElement.cost_element_id}`)
      }
      metrics={
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: token.marginXS,
            fontSize: token.fontSizeSM,
            color: token.colorTextSecondary,
          }}
        >
          <DollarOutlined />
          <span>{formatCurrency(Number(costElement.budget_amount))}</span>
        </div>
      }
      meta={
        <div
          style={{
            display: "flex",
            gap: token.marginSM,
            flexWrap: "wrap",
          }}
        >
          {costElement.branch && (
            <Tag style={{ fontSize: token.fontSizeSM }}>
              {costElement.branch}
            </Tag>
          )}
        </div>
      }
      actions={
        <Space size="small">
          <Can permission="cost-element-read">
            <Button
              size="small"
              icon={<EyeOutlined />}
              onClick={(e) => {
                e.stopPropagation();
                navigate(`/cost-elements/${costElement.cost_element_id}`);
              }}
              title="View Details"
            />
          </Can>
          <Can permission="cost-element-read">
            <Button
              size="small"
              icon={<HistoryOutlined />}
              onClick={(e) => {
                e.stopPropagation();
                onViewHistory(costElement);
              }}
              title="View History"
            />
          </Can>
          <Can permission="cost-element-update">
            <Button
              size="small"
              icon={<EditOutlined />}
              onClick={(e) => {
                e.stopPropagation();
                onEdit(costElement);
              }}
              title="Edit"
            />
          </Can>
          <Can permission="cost-element-delete">
            <Button
              size="small"
              danger
              icon={<DeleteOutlined />}
              onClick={(e) => {
                e.stopPropagation();
                onDelete(costElement.cost_element_id);
              }}
              title="Delete"
            />
          </Can>
        </Space>
      }
    />
  );
};
