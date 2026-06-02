import { Tag, theme } from "antd";
import { PaperClipOutlined } from "@ant-design/icons";
import type { CostRegistrationRead } from "@/api/generated";
import { EntityCard } from "@/components/common/EntityCard";
import { formatDate } from "@/utils/formatters";

const formatCurrency = (val: number | string | null | undefined, symbol = "€") =>
  val != null
    ? `${symbol}${Number(val).toLocaleString(undefined, { minimumFractionDigits: 2 })}`
    : "-";

interface CostRegistrationCardProps {
  registration: CostRegistrationRead;
  currencySymbol?: string;
  onClick?: () => void;
}

export const CostRegistrationCard = ({
  registration,
  currencySymbol = "€",
  onClick,
}: CostRegistrationCardProps) => {
  const { token } = theme.useToken();

  const elementTypeName = (registration as Record<string, unknown>).cost_element_type_name as string | null | undefined;

  return (
    <EntityCard
      title={formatCurrency(registration.amount, currencySymbol)}
      subtitle={registration.description || elementTypeName || "Cost Registration"}
      badge={elementTypeName ? <Tag>{elementTypeName}</Tag> : undefined}
      onClick={onClick}
      metrics={
        <div style={{ display: "flex", flexDirection: "column", gap: token.marginXS, fontSize: token.fontSizeSM, color: token.colorTextSecondary }}>
          <span>{formatDate(registration.registration_date, { style: "short", fallback: "-" })}</span>
          {registration.vendor_reference && <span>Vendor: {registration.vendor_reference}</span>}
        </div>
      }
      meta={
        (registration.attachment_count ?? 0) > 0 ? (
          <div style={{ display: "flex", alignItems: "center", gap: token.marginXS, fontSize: token.fontSizeSM, color: token.colorTextSecondary }}>
            <PaperClipOutlined />
            <span>{registration.attachment_count} file{registration.attachment_count !== 1 ? "s" : ""}</span>
          </div>
        ) : undefined
      }
    />
  );
};
