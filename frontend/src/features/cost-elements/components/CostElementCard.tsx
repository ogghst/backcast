import { Tag, theme } from "antd";
import { DollarOutlined } from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import type { CostElementRead } from "@/api/generated";
import { EntityCard } from "@/components/common/EntityCard";

interface CostElementCardProps {
  costElement: CostElementRead;
  typeNames: Record<string, string>;
}

const formatCurrency = (val: number | null | undefined) =>
  val ? `\u20AC${Number(val).toLocaleString()}` : "-";

export const CostElementCard = ({
  costElement,
  typeNames,
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
    />
  );
};
