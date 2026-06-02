import { Tag, theme } from "antd";
import { BankOutlined } from "@ant-design/icons";
import type { ControlAccountRead } from "@/api/generated";
import { EntityCard } from "@/components/common/EntityCard";

interface ControlAccountCardProps {
  controlAccount: ControlAccountRead;
  onClick?: () => void;
}

export const ControlAccountCard = ({
  controlAccount,
  onClick,
}: ControlAccountCardProps) => {
  const { token } = theme.useToken();

  return (
    <EntityCard
      title={controlAccount.name}
      subtitle={controlAccount.code || controlAccount.control_account_id}
      badge={<Tag color="blue">CA</Tag>}
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
          <BankOutlined />
          <span>
            {controlAccount.wbs_element_name || "-"} /{" "}
            {controlAccount.organizational_unit_name || "-"}
          </span>
        </div>
      }
    />
  );
};
