import { Button, Space, Tag, theme, Tooltip } from "antd";
import { CheckCircleOutlined } from "@ant-design/icons";
import { EntityCard } from "@/components/common/EntityCard";
import type { NotificationResponse } from "@/features/notifications";
import { SEVERITY_TAG_COLOR, timeAgo } from "@/features/notifications/utils";

interface NotificationCardProps {
  notification: NotificationResponse;
  onOpen?: (n: NotificationResponse) => void;
  onMarkRead?: (id: string) => void;
}

export const NotificationCard = ({
  notification,
  onOpen,
  onMarkRead,
}: NotificationCardProps) => {
  const { token } = theme.useToken();
  const severity = notification.severity ?? "info";

  return (
    <EntityCard
      title={notification.title}
      subtitle={notification.message}
      badge={
        <Space size={token.marginXS} align="center">
          {!notification.read_at && <Tag color="processing">unread</Tag>}
          <Tag color={SEVERITY_TAG_COLOR[severity] as never}>
            {severity.replace(/_/g, " ")}
          </Tag>
        </Space>
      }
      metrics={
        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            alignItems: "center",
            gap: token.marginXS,
            fontSize: token.fontSizeSM,
            color: token.colorTextSecondary,
          }}
        >
          <Tag style={{ marginInlineEnd: 0 }}>
            {notification.category?.replace(/_/g, " ") ?? "system"}
          </Tag>
          {notification.actor_type && (
            <span>{notification.actor_type.replace(/_/g, " ")}</span>
          )}
          <span>{timeAgo(notification.created_at)}</span>
        </div>
      }
      actions={
        !notification.read_at && onMarkRead ? (
          <Tooltip title="Mark as read">
            <Button
              type="text"
              size="small"
              icon={<CheckCircleOutlined />}
              aria-label="Mark as read"
              onClick={(e) => {
                e.stopPropagation();
                onMarkRead(notification.id);
              }}
            />
          </Tooltip>
        ) : undefined
      }
      onClick={onOpen ? () => onOpen(notification) : undefined}
    />
  );
};
