import { UnorderedListOutlined } from "@ant-design/icons";
import { Empty, Table, Tag, Typography, theme } from "antd";
import { type FC, useMemo } from "react";
import type { ColumnsType } from "antd/es/table";
import { useDashboardContext } from "../context/useDashboardContext";
import { useChangeOrders } from "@/features/change-orders/api/useChangeOrders";
import type { ChangeOrderPublic } from "@/api/generated";
import { WidgetShell } from "../components/WidgetShell";
import { registerWidget, widgetTypeId } from "..";
import type { WidgetComponentProps } from "../types";

const { Text } = Typography;

// ---------------------------------------------------------------------------
// Config
// ---------------------------------------------------------------------------

interface ChangeOrdersListConfig {
  statusFilter: "all" | "open" | "approved" | "rejected";
  pageSize: number;
}

const STATUS_COLORS: Record<string, string> = {
  Draft: "default",
  "Submitted for Approval": "processing",
  "Under Review": "purple",
  Approved: "success",
  Rejected: "error",
  Implemented: "cyan",
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const IMPACT_ORDER: Record<string, number> = {
  LOW: 0,
  MEDIUM: 1,
  HIGH: 2,
  CRITICAL: 3,
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const ChangeOrdersListComponent: FC<
  WidgetComponentProps<ChangeOrdersListConfig>
> = ({ config, instanceId, isEditing, onRemove, onConfigure }) => {
  const { token } = theme.useToken();
  const context = useDashboardContext();

  const { data, isLoading, error, refetch } = useChangeOrders({
    projectId: context.projectId,
    pagination: { current: 1, pageSize: config.pageSize },
  });

  const filteredItems = useMemo(() => {
    const items = data?.items ?? [];
    if (config.statusFilter === "all") return items;

    return items.filter((co) => {
      const status = co.status ?? "";
      switch (config.statusFilter) {
        case "open":
          return (
            status === "Draft" ||
            status === "Submitted for Approval" ||
            status === "Under Review"
          );
        case "approved":
          return status === "Approved" || status === "Implemented";
        case "rejected":
          return status === "Rejected";
        default:
          return true;
      }
    });
  }, [data?.items, config.statusFilter]);

  const columns = useMemo<ColumnsType<ChangeOrderPublic>>(
    () => [
      {
        title: "Code",
        dataIndex: "code",
        key: "code",
        width: 100,
        render: (val: string) => (
          <Text strong style={{ fontSize: token.fontSizeSM }}>
            {val}
          </Text>
        ),
      },
      {
        title: "Title",
        dataIndex: "title",
        key: "title",
        ellipsis: true,
      },
      {
        title: "Status",
        dataIndex: "status",
        key: "status",
        width: 120,
        render: (val: string | null) => (
          <Tag color={STATUS_COLORS[val ?? ""] ?? "default"}>
            {val ?? "-"}
          </Tag>
        ),
      },
      {
        title: "Impact",
        dataIndex: "impact_level",
        key: "impact_level",
        width: 90,
        render: (val: string | null) => (
          <Text
            style={{
              fontSize: token.fontSizeSM,
              color:
                val === "CRITICAL"
                  ? token.colorError
                  : val === "HIGH"
                    ? token.colorWarning
                    : token.colorTextSecondary,
            }}
          >
            {val ?? "-"}
          </Text>
        ),
        sorter: (a, b) =>
          (IMPACT_ORDER[a.impact_level ?? ""] ?? -1) -
          (IMPACT_ORDER[b.impact_level ?? ""] ?? -1),
      },
    ],
    [token.fontSizeSM, token.colorError, token.colorWarning, token.colorTextSecondary],
  );

  if (!context.projectId) {
    return (
      <WidgetShell
        instanceId={instanceId}
        title="Change Orders"
        icon={<UnorderedListOutlined />}
        isEditing={isEditing}
        isLoading={false}
        error={null}
        onRemove={onRemove}
        onConfigure={onConfigure}
      >
        <Empty description="No project selected" />
      </WidgetShell>
    );
  }

  return (
    <WidgetShell
      instanceId={instanceId}
      title="Change Orders"
      icon={<UnorderedListOutlined />}
      isEditing={isEditing}
      isLoading={isLoading}
      error={error}
      onRemove={onRemove}
      onRefresh={refetch}
      onConfigure={onConfigure}
    >
      <Table<ChangeOrderPublic>
        columns={columns}
        dataSource={filteredItems}
        rowKey="id"
        size="small"
        pagination={{ pageSize: config.pageSize, size: "small" }}
        scroll={{ y: 220 }}
        style={{ fontSize: token.fontSizeSM }}
      />
    </WidgetShell>
  );
};

// ---------------------------------------------------------------------------
// Registration
// ---------------------------------------------------------------------------

registerWidget<ChangeOrdersListConfig>({
  typeId: widgetTypeId("change-orders-list"),
  displayName: "Change Orders",
  description: "List of change orders with status and impact level",
  category: "action",
  icon: <UnorderedListOutlined />,
  sizeConstraints: {
    minW: 4,
    minH: 3,
    defaultW: 4,
    defaultH: 3,
  },
  component: ChangeOrdersListComponent,
  defaultConfig: {
    statusFilter: "all",
    pageSize: 5,
  },
});
