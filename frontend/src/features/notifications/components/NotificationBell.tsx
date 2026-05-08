/**
 * NotificationBell component
 *
 * Displays a bell icon with an unread count badge. Clicking opens a popover
 * with the latest notifications. Supports marking individual or all
 * notifications as read and navigating to linked resources.
 */
import React, { useState, useCallback } from "react";
import { Badge, Button, List, Popover, Spin, Typography, theme, Empty } from "antd";
import { BellOutlined } from "@ant-design/icons";
import { useNavigate } from "react-router-dom";

import { useThemeTokens } from "@/hooks/useThemeTokens";
import {
  useNotifications,
  useUnreadNotificationCount,
  useMarkNotificationRead,
  useMarkAllNotificationsRead,
  type NotificationResponse,
} from "../api/useNotifications";

const { Text, Paragraph } = Typography;

/** Format an ISO date string as a human-readable relative time. */
function timeAgo(dateStr: string): string {
  const now = Date.now();
  const then = new Date(dateStr).getTime();
  const diffSeconds = Math.max(0, Math.floor((now - then) / 1000));

  if (diffSeconds < 60) return "just now";
  const diffMinutes = Math.floor(diffSeconds / 60);
  if (diffMinutes < 60) return `${diffMinutes}m ago`;
  const diffHours = Math.floor(diffMinutes / 60);
  if (diffHours < 24) return `${diffHours}h ago`;
  const diffDays = Math.floor(diffHours / 24);
  if (diffDays < 30) return `${diffDays}d ago`;
  return new Date(dateStr).toLocaleDateString();
}

/** Maximum rendered notification items. */
const PAGE_SIZE = 10;

export const NotificationBell: React.FC = () => {
  const [open, setOpen] = useState(false);
  const navigate = useNavigate();
  const { token } = theme.useToken();
  const { spacing, typography, colors, borderRadius } = useThemeTokens();

  // Fetch unread count (always active for badge)
  const { data: unreadData } = useUnreadNotificationCount();
  const unreadCount = unreadData?.count ?? 0;

  // Fetch notification list only while popover is open
  const { data: listData, isLoading } = useNotifications(
    { page: 1, pageSize: PAGE_SIZE },
    { enabled: open },
  );
  const notifications = listData?.items ?? [];

  const markRead = useMarkNotificationRead();
  const markAllRead = useMarkAllNotificationsRead();

  const handleNotificationClick = useCallback(
    (notification: NotificationResponse) => {
      // Mark as read if unread
      if (!notification.read_at) {
        markRead.mutate(notification.id);
      }

      // Navigate for linked resources
      if (
        notification.resource_type === "change_order" &&
        notification.resource_id
      ) {
        // The change order routes are project-scoped. We close the popover and
        // navigate -- the destination page will resolve the correct project.
        setOpen(false);
        navigate(`/change-orders/${notification.resource_id}`);
      }
    },
    [markRead, navigate],
  );

  const handleMarkAllRead = useCallback(() => {
    markAllRead.mutate();
  }, [markAllRead]);

  const content = (
    <div
      style={{
        width: 360,
        maxHeight: 480,
        display: "flex",
        flexDirection: "column",
      }}
    >
      {/* Header */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          paddingBottom: spacing.sm,
          borderBottom: `1px solid ${colors.border}`,
          marginBottom: spacing.xs,
        }}
      >
        <Text strong style={{ fontSize: typography.sizes.md }}>
          Notifications
        </Text>
        {unreadCount > 0 && (
          <Button
            type="link"
            size="small"
            onClick={handleMarkAllRead}
            loading={markAllRead.isPending}
            style={{ padding: 0, fontSize: typography.sizes.sm }}
          >
            Mark all as read
          </Button>
        )}
      </div>

      {/* List */}
      {isLoading ? (
        <div
          style={{
            display: "flex",
            justifyContent: "center",
            padding: spacing.xl,
          }}
        >
          <Spin />
        </div>
      ) : notifications.length === 0 ? (
        <Empty
          description="No notifications"
          style={{ padding: `${spacing.lg} 0` }}
        />
      ) : (
        <List
          style={{ overflowY: "auto", maxHeight: 400 }}
          dataSource={notifications}
          renderItem={(item: NotificationResponse) => {
            const isUnread = !item.read_at;
            return (
              <List.Item
                key={item.id}
                onClick={() => handleNotificationClick(item)}
                style={{
                  cursor:
                    item.resource_type === "change_order" &&
                    item.resource_id
                      ? "pointer"
                      : "default",
                  padding: `${spacing.sm} ${spacing.md}`,
                  borderRadius: borderRadius.sm,
                  background: isUnread
                    ? token.colorPrimaryBg
                    : "transparent",
                  transition: "background 0.2s",
                  border: "none",
                }}
              >
                <div
                  style={{
                    width: "100%",
                    display: "flex",
                    flexDirection: "column",
                    gap: spacing.xs,
                  }}
                >
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                    }}
                  >
                    <Text
                      strong={isUnread}
                      style={{
                        fontSize: typography.sizes.md,
                        flex: 1,
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                      }}
                    >
                      {item.title}
                    </Text>
                    {isUnread && (
                      <div
                        style={{
                          width: 8,
                          height: 8,
                          borderRadius: "50%",
                          background: colors.primary,
                          marginLeft: spacing.sm,
                          flexShrink: 0,
                        }}
                      />
                    )}
                  </div>
                  <Paragraph
                    style={{
                      margin: 0,
                      fontSize: typography.sizes.sm,
                      color: colors.textSecondary,
                      lineClamp: 2,
                    }}
                    ellipsis={{ rows: 2 }}
                  >
                    {item.message}
                  </Paragraph>
                  <Text
                    type="secondary"
                    style={{ fontSize: typography.sizes.xs }}
                  >
                    {timeAgo(item.created_at)}
                  </Text>
                </div>
              </List.Item>
            );
          }}
        />
      )}
    </div>
  );

  return (
    <Popover
      content={content}
      trigger="click"
      open={open}
      onOpenChange={setOpen}
      placement="bottomRight"
      styles={{
        content: { padding: `${spacing.sm} ${spacing.md}` },
      }}
    >
      <Badge count={unreadCount} size="small" offset={[-2, 2]}>
        <Button
          type="text"
          icon={<BellOutlined style={{ fontSize: typography.sizes.lg }} />}
          style={{ display: "flex", alignItems: "center", justifyContent: "center" }}
        />
      </Badge>
    </Popover>
  );
};
