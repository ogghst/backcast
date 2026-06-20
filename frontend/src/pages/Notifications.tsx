/**
 * Notifications Page
 *
 * Full-page, filterable, paginated list of notifications. Modeled on
 * AgentsHistory.tsx (filter bar + Ant Design Table). Clicking a row navigates
 * to the linked resource by resource_type/resource_id.
 */
import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  App,
  Button,
  Select,
  Switch,
  Table,
  Tag,
  Tooltip,
  Typography,
  Space,
  theme,
} from "antd";
import type { ColumnType } from "antd/es/table";
import {
  CheckCircleOutlined,
  InfoCircleOutlined,
  WarningOutlined,
  ExclamationCircleOutlined,
} from "@ant-design/icons";
import { PageWrapper } from "@/components/layout/PageWrapper";
import { useThemeTokens } from "@/hooks/useThemeTokens";
import {
  useNotifications,
  useMarkAllNotificationsRead,
  useMarkNotificationRead,
  type NotificationResponse,
  type NotificationSeverity,
  type NotificationCategory,
} from "@/features/notifications";
import {
  resolveResourceRoute,
  timeAgo,
  SEVERITY_TAG_COLOR,
} from "@/features/notifications/utils";

const { Title } = Typography;

type CategoryFilter = NotificationCategory | "all";
type SeverityFilter = NotificationSeverity | "all";

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

export const Notifications = () => {
  const { token } = theme.useToken();
  const { spacing } = useThemeTokens();
  const navigate = useNavigate();
  const { message } = App.useApp();

  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [category, setCategory] = useState<CategoryFilter>("all");
  const [severity, setSeverity] = useState<SeverityFilter>("all");
  const [unreadOnly, setUnreadOnly] = useState(false);

  const query = useNotifications({
    page,
    pageSize,
    unreadOnly: unreadOnly || undefined,
    category: category === "all" ? undefined : category,
    severity: severity === "all" ? undefined : severity,
  });

  const markRead = useMarkNotificationRead();
  const markAllRead = useMarkAllNotificationsRead({
    onSuccess: () => message.success("All notifications marked as read"),
  });

  const handleRowClick = (item: NotificationResponse) => {
    if (!item.read_at) {
      markRead.mutate(item.id);
    }
    const route = resolveResourceRoute(item.resource_type, item.resource_id);
    if (route) navigate(route);
  };

  const columns = useMemo<ColumnType<NotificationResponse>[]>(
    () => [
      {
        title: "",
        dataIndex: "severity",
        key: "severity",
        width: 40,
        render: (sev: NotificationSeverity) => <SeverityIcon severity={sev ?? "info"} />,
      },
      {
        title: "Title",
        dataIndex: "title",
        key: "title",
        render: (title: string, record) => (
          <Space direction="vertical" size={0}>
            <Typography.Text strong={!record.read_at}>{title}</Typography.Text>
            <Typography.Text
              type="secondary"
              style={{ fontSize: token.fontSizeSM }}
              ellipsis
            >
              {record.message}
            </Typography.Text>
          </Space>
        ),
      },
      {
        title: "Category",
        dataIndex: "category",
        key: "category",
        width: 140,
        render: (cat: NotificationCategory | null) =>
          cat ? (
            <Tag>{cat.replace(/_/g, " ")}</Tag>
          ) : (
            <Tag>system</Tag>
          ),
      },
      {
        title: "Actor",
        dataIndex: "actor_type",
        key: "actor_type",
        width: 120,
        render: (actorType: string | null) =>
          actorType ? actorType.replace(/_/g, " ") : "—",
        ellipsis: true,
      },
      {
        title: "Severity",
        dataIndex: "severity",
        key: "severityTag",
        width: 110,
        render: (sev: NotificationSeverity | null) => (
          <Tag color={SEVERITY_TAG_COLOR[sev ?? "info"] as never}>
            {(sev ?? "info").replace(/_/g, " ")}
          </Tag>
        ),
      },
      {
        title: "Created",
        dataIndex: "created_at",
        key: "created_at",
        width: 130,
        render: (iso: string) => timeAgo(iso),
      },
      {
        title: "Read",
        dataIndex: "read_at",
        key: "read_at",
        width: 80,
        render: (readAt: string | null) =>
          readAt ? (
            <Tag color="default">read</Tag>
          ) : (
            <Tag color="processing">unread</Tag>
          ),
      },
      {
        title: "Actions",
        key: "actions",
        width: 90,
        render: (_, record) =>
          record.read_at ? null : (
            <Tooltip title="Mark as read">
              <Button
                type="text"
                size="small"
                icon={<CheckCircleOutlined />}
                loading={markRead.isPending}
                onClick={(e) => {
                  e.stopPropagation();
                  markRead.mutate(record.id);
                }}
                aria-label="Mark as read"
              />
            </Tooltip>
          ),
      },
    ],
    [token.fontSizeSM, markRead],
  );

  return (
    <PageWrapper>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          gap: spacing.md,
          marginBottom: spacing.md,
          flexWrap: "wrap",
        }}
      >
        <Title level={2} style={{ margin: 0 }}>
          Notifications
        </Title>
        <Space size={spacing.sm} wrap>
          <Select<CategoryFilter>
            style={{ width: 170 }}
            value={category}
            onChange={(v) => {
              setCategory(v);
              setPage(1);
            }}
            options={[
              { label: "All categories", value: "all" },
              { label: "Change Orders", value: "change_order" },
              { label: "Agents", value: "agent" },
              { label: "Project", value: "project" },
              { label: "Document", value: "document" },
              { label: "Branch", value: "branch" },
              { label: "System", value: "system" },
            ]}
          />
          <Select<SeverityFilter>
            style={{ width: 150 }}
            value={severity}
            onChange={(v) => {
              setSeverity(v);
              setPage(1);
            }}
            options={[
              { label: "All severities", value: "all" },
              { label: "Info", value: "info" },
              { label: "Notice", value: "notice" },
              { label: "Warning", value: "warning" },
              { label: "Urgent", value: "urgent" },
            ]}
          />
          <Space size={spacing.xs}>
            <Switch
              checked={unreadOnly}
              onChange={(checked) => {
                setUnreadOnly(checked);
                setPage(1);
              }}
            />
            <Typography.Text>Unread only</Typography.Text>
          </Space>
          <Button onClick={() => markAllRead.mutate()} loading={markAllRead.isPending}>
            Mark all read
          </Button>
        </Space>
      </div>

      <Table<NotificationResponse>
        rowKey="id"
        columns={columns}
        dataSource={query.data?.items ?? []}
        loading={query.isLoading}
        size="middle"
        locale={{ emptyText: "No notifications" }}
        onRow={(record) => ({
          onClick: () => handleRowClick(record),
          style: { cursor: "pointer" },
        })}
        pagination={{
          current: page,
          pageSize,
          total: query.data?.total ?? 0,
          showSizeChanger: true,
          onChange: (p, ps) => {
            setPage(p);
            setPageSize(ps);
          },
        }}
        style={{
          backgroundColor: token.colorBgContainer,
          borderRadius: token.borderRadiusLG,
        }}
      />
    </PageWrapper>
  );
};

export default Notifications;
