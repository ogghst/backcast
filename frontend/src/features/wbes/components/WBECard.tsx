import { Tag, theme } from "antd";
import { DollarOutlined } from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import type { WBERead } from "@/api/generated";
import { EntityCard } from "@/components/common/EntityCard";

interface WBECardProps {
  wbe: WBERead;
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

export const WBECard = ({ wbe }: WBECardProps) => {
  const { token } = theme.useToken();
  const navigate = useNavigate();

  return (
    <EntityCard
      title={wbe.name}
      subtitle={wbe.code}
      badge={<Tag color="cyan">L{wbe.level}</Tag>}
      onClick={() =>
        navigate(`/projects/${wbe.project_id}/wbes/${wbe.wbe_id}`)
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
          <span>{formatCurrency(wbe.budget_allocation)}</span>
        </div>
      }
      meta={
        wbe.branch && wbe.branch !== "main" ? (
          <Tag style={{ fontSize: token.fontSizeSM }}>{wbe.branch}</Tag>
        ) : undefined
      }
    />
  );
};
