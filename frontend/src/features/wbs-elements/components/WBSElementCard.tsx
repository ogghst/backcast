import { Tag, theme } from "antd";
import { DollarOutlined } from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import type { WBSElementRead } from "@/api/generated";
import { EntityCard } from "@/components/common/EntityCard";

interface WBSElementCardProps {
  wbsElement: WBSElementRead;
}

const formatCurrency = (value: string | number | null | undefined) => {
  const num = typeof value === "string" ? parseFloat(value) : value;
  if (!num || isNaN(num)) return "-";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "EUR",
    currencyDisplay: "narrowSymbol",
  }).format(num);
};

export const WBSElementCard = ({ wbsElement }: WBSElementCardProps) => {
  const { token } = theme.useToken();
  const navigate = useNavigate();

  return (
    <EntityCard
      title={wbsElement.name}
      subtitle={wbsElement.code}
      badge={<Tag color="cyan">L{wbsElement.level}</Tag>}
      onClick={() =>
        navigate(`/projects/${wbsElement.project_id}/wbs-elements/${wbsElement.wbs_element_id}`)
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
          <span>{formatCurrency(wbsElement.budget_allocation)}</span>
        </div>
      }
      meta={
        wbsElement.branch && wbsElement.branch !== "main" ? (
          <Tag style={{ fontSize: token.fontSizeSM }}>{wbsElement.branch}</Tag>
        ) : undefined
      }
    />
  );
}
