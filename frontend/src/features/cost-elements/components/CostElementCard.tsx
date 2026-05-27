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
  val ? `€${Number(val).toLocaleString()}` : "-";

export const CostElementCard = ({
  costElement,
  typeNames,
}: CostElementCardProps) => {
  const { token } = theme.useToken();
  const navigate = useNavigate();

  const typeName =
    typeNames[costElement.cost_element_type_id] ||
    "-";

  return (
    <EntityCard
      title={typeName}
      subtitle={costElement.description || "EOC"}
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
          <span>{formatCurrency(Number(costElement.amount))}</span>
        </div>
      }
    />
  );
};
