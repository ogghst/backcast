import { Button, Space, Tag, theme } from "antd";
import {
  EditOutlined,
  DeleteOutlined,
  RightOutlined,
  DollarOutlined,
} from "@ant-design/icons";
import type { WBERead } from "@/api/generated";
import { Can } from "@/components/auth/Can";
import { EntityCard } from "@/components/common/EntityCard";

interface WBECardProps {
  wbe: WBERead;
  onEdit: (wbe: WBERead) => void;
  onDelete: (wbe: WBERead) => void;
  onOpen: (wbe: WBERead) => void;
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

export const WBECard = ({ wbe, onEdit, onDelete, onOpen }: WBECardProps) => {
  const { token } = theme.useToken();

  return (
    <EntityCard
      title={wbe.name}
      subtitle={wbe.code}
      badge={<Tag color="cyan">L{wbe.level}</Tag>}
      onClick={() => onOpen(wbe)}
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
      actions={
        <Space size="small">
          <Can permission="wbe-update">
            <Button
              size="small"
              icon={<EditOutlined />}
              onClick={(e) => {
                e.stopPropagation();
                onEdit(wbe);
              }}
              title="Edit WBE"
            />
          </Can>
          <Can permission="wbe-delete">
            <Button
              size="small"
              danger
              icon={<DeleteOutlined />}
              onClick={(e) => {
                e.stopPropagation();
                onDelete(wbe);
              }}
              title="Delete WBE"
            />
          </Can>
          <Button
            size="small"
            type="primary"
            ghost
            icon={<RightOutlined />}
            onClick={(e) => {
              e.stopPropagation();
              onOpen(wbe);
            }}
            title="Open"
          />
        </Space>
      }
    />
  );
};
