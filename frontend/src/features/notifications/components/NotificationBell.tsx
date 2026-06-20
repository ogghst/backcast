/**
 * NotificationBell component
 *
 * Displays a bell icon with an unread count badge (WS-fed via the query cache,
 * with REST as initial/fallback). Clicking opens a popover with the latest
 * notifications filtered by category tab. Supports marking individual or all
 * notifications as read and navigating to linked resources.
 */
import React, { useState, useCallback, useMemo } from "react";
import {
  Badge,
  Button,
  Drawer,
  Grid,
  List,
  Popover,
  Spin,
  Typography,
  theme,
  Empty,
  Segmented,
  Tag,
  Tooltip,
} from "antd";
import {
  BellOutlined,
  CheckCircleOutlined,
  InfoCircleOutlined,
  WarningOutlined,
  ExclamationCircleOutlined,
} from "@ant-design/icons";
import { useNavigate } from "react-router-dom";

import { useThemeTokens } from "@/hooks/useThemeTokens";
import {
  useNotifications,
  useUnreadNotificationCount,
  useMarkNotificationRead,
  useMarkAllNotificationsRead,
  type NotificationResponse,
  type NotificationSeverity,
} from "../api/useNotifications";
import {
  timeAgo,
  resolveResourceRoute,
  SEVERITY_TAG_COLOR,
} from "../utils";

const { Text, Paragraph } = Typography;

/** Maximum rendered notification items per popover load. */
const PAGE_SIZE = 20;

type CategoryTab = "all" | "change_order" | "agent" | "system";

const CATEGORY_TAB_OPTIONS: { label: string; value: CategoryTab }[] = [
  { label: "All", value: "all" },
  { label: "Change Orders", value: "change_order" },
  { label: "Agents", value: "agent" },
  { label: "System", value: "system" },
];

/** Severity icon component. */
function SeverityIcon({ severity }: { severity: NotificationSeverity }) {
  switch (severity) {
    case "urgent":
      return <ExclamationCircleOutlined style={{ color: "#ff4d4f" }} />;
    case "warning":
      return <WarningOutlined style={{ color: "#faad14" }} />;
    case "notice":
      return <InfoCircleOutlined style={{ color: "#1677ff" }} />;
    default:
      return <CheckCircleOutlined style={{ color: "#8c8c8c" }} />;
  }
}

export const NotificationBell: React.FC = () => {
  const [open, setOpen] = useState(false);
  const [activeCategory, setActiveCategory] = useState<CategoryTab>("all");
  const navigate = useNavigate();
  const { token } = theme.useToken();
  const { spacing, typography, colors, borderRadius } = useThemeTokens();
  const screens = Grid.useBreakpoint();
  const isMobile = !screens.md; // md breakpoint is 768px

  // Badge count — REST provides the initial value; the WS stream writes
  // authoritative updates straight into this cache entry.
  const { data: unreadData } = useUnreadNotificationCount();
  const unreadCount = unreadData?.count ?? 0;

  // Fetch a larger page only while the popover is open, server-filtered by
  // category when a tab is selected.
  const { data: listData, isLoading } = useNotifications(
    {
      page: 1,
      pageSize: PAGE_SIZE,
      category: activeCategory === "all" ? undefined : activeCategory,
    },
    { enabled: open },
  );
  const notifications = listData?.items ?? [];

  const markRead = useMarkNotificationRead();
  const markAllRead = useMarkAllNotificationsRead();

  const handleNotificationClick = useCallback(
    (notification: NotificationResponse) => {
      if (!notification.read_at) {
        markRead.mutate(notification.id);
      }
      const route = resolveResourceRoute(
        notification.resource_type,
        notification.resource_id,
      );
      if (route) {
        setOpen(false);
        navigate(route);
      }
    },
    [markRead, navigate],
  );

  const handleMarkAllRead = useCallback(() => {
    markAllRead.mutate();
  }, [markAllRead]);

  const handleViewAll = useCallback(() => {
    setOpen(false);
    navigate("/notifications");
  }, [navigate]);

  const footer = useMemo(
    () => (
      <div
        style={{
          display: "flex",
          justifyContent: "center",
          paddingTop: spacing.xs,
          borderTop: `1px solid ${colors.border}`,
        }}
      >
        <Button type="link" size="small" onClick={handleViewAll}>
          View all
        </Button>
      </div>
    ),
    [handleViewAll, spacing.xs, colors.border],
  );

  const content = (
    <div
      style={{
        width: isMobile ? "100%" : 380,
        maxHeight: isMobile ? undefined : 520,
        height: isMobile ? "100%" : undefined,
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
          paddingBottom: spacing.xs,
          borderBottom: `1px solid ${colors.border}`,
          marginBottom: spacing.xs,
        }}
      >
        {!isMobile && (
          <Text strong style={{ fontSize: typography.sizes.md }}>
            Notifications
          </Text>
        )}
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

      {/* Category tabs */}
      <div style={{ paddingBottom: spacing.xs }}>
        <Segmented<CategoryTab>
          size="small"
          block
          value={activeCategory}
          onChange={(val) => setActiveCategory(val)}
          options={CATEGORY_TAB_OPTIONS}
        />
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
          style={{
            overflowY: "auto",
            maxHeight: isMobile ? undefined : 360,
            flex: isMobile ? 1 : undefined,
            minHeight: isMobile ? 0 : undefined,
          }}
          dataSource={notifications}
          renderItem={(item: NotificationResponse) => {
            const isUnread = !item.read_at;
            const route = resolveResourceRoute(
              item.resource_type,
              item.resource_id,
            );
            return (
              <List.Item
                key={item.id}
                onClick={() => handleNotificationClick(item)}
                style={{
                  cursor: route ? "pointer" : "default",
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
                      alignItems: "center",
                      gap: spacing.xs,
                    }}
                  >
                    <SeverityIcon severity={item.severity ?? "info"} />
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
                          marginLeft: spacing.xs,
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
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      gap: spacing.xs,
                    }}
                  >
                    <Tag
                      color={
                        SEVERITY_TAG_COLOR[item.severity ?? "info"] as never
                      }
                      style={{ margin: 0, fontSize: typography.sizes.xs }}
                    >
                      {item.category?.replace(/_/g, " ") ?? "system"}
                    </Tag>
                    <Text
                      type="secondary"
                      style={{ fontSize: typography.sizes.xs }}
                    >
                      {timeAgo(item.created_at)}
                    </Text>
                  </div>
                </div>
              </List.Item>
            );
          }}
        />
      )}
      {footer}
    </div>
  );

  const bell = (
    <Tooltip title="Notifications">
      <Badge count={unreadCount} size="small" offset={[-2, 2]}>
        <Button
          type="text"
          icon={<BellOutlined style={{ fontSize: typography.sizes.lg }} />}
          aria-label="Notifications"
          onClick={isMobile ? () => setOpen(true) : undefined}
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        />
      </Badge>
    </Tooltip>
  );

  if (isMobile) {
    return (
      <>
        {bell}
        <Drawer
          title="Notifications"
          placement="right"
          width="100%"
          open={open}
          onClose={() => setOpen(false)}
          styles={{
            body: {
              padding: `${spacing.sm} ${spacing.md}`,
              display: "flex",
              flexDirection: "column",
            },
          }}
        >
          {content}
        </Drawer>
      </>
    );
  }

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
      {bell}
    </Popover>
  );
};
