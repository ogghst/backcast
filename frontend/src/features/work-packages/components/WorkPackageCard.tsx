import { Tag, theme } from "antd";
import { DollarOutlined } from "@ant-design/icons";
import type { WorkPackageRead } from "@/api/generated";
import { EntityCard } from "@/components/common/EntityCard";

const STATUS_COLOR_MAP: Record<string, string> = {
  open: "blue",
  in_progress: "orange",
  closed: "green",
};

const formatCurrency = (val: number | string | null | undefined) =>
  val != null ? `€${Number(val).toLocaleString()}` : "-";

interface WorkPackageCardProps {
  workPackage: WorkPackageRead;
  onClick?: () => void;
}

export const WorkPackageCard = ({
  workPackage,
  onClick,
}: WorkPackageCardProps) => {
  const { token } = theme.useToken();

  const statusColor =
    STATUS_COLOR_MAP[workPackage.status || "open"] || "default";

  return (
    <EntityCard
      title={workPackage.name}
      subtitle={workPackage.code || workPackage.work_package_id}
      badge={
        <Tag color={statusColor}>
          {workPackage.status || "open"}
        </Tag>
      }
      onClick={onClick}
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
          <span>{formatCurrency(workPackage.budget_amount)}</span>
        </div>
      }
    />
  );
};
