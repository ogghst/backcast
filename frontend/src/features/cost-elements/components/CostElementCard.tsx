import { Tag } from "antd";
import { useNavigate } from "react-router-dom";
import type { CostElementRead } from "@/api/generated";
import { EntityCard } from "@/components/common/EntityCard";

interface CostElementCardProps {
  costElement: CostElementRead;
  typeNames: Record<string, string>;
}

export const CostElementCard = ({
  costElement,
  typeNames,
}: CostElementCardProps) => {
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
    />
  );
};
