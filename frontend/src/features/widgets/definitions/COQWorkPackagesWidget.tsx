import { UnorderedListOutlined } from "@ant-design/icons";
import { Empty, Table, Tag, Typography, theme } from "antd";
import { type FC, useMemo } from "react";
import type { ColumnsType } from "antd/es/table";
import { useDashboardContext } from "../context/useDashboardContext";
import {
  useCostEvents,
  COQ_CATEGORY_OPTIONS,
} from "@/features/cost-events/api/useCostEvents";
import type { CostEventRead } from "@/api/generated/models/CostEventRead";
import { formatCurrency } from "@/components/explorer/shared/formatters";
import { WidgetShell } from "../components/WidgetShell";
import { registerWidget, widgetTypeId } from "..";
import type { WidgetComponentProps } from "../types";

const { Text } = Typography;

interface COQWorkPackagesConfig {
  pageSize: number;
}

const CATEGORY_COLORS: Record<string, string> = {
  prevention: "blue",
  appraisal: "cyan",
  internal_failure: "orange",
  external_failure: "red",
};

const CATEGORY_LABELS: Record<string, string> = Object.fromEntries(
  COQ_CATEGORY_OPTIONS.map((o) => [o.value, o.label]),
);

const COQWorkPackagesComponent: FC<
  WidgetComponentProps<COQWorkPackagesConfig>
> = ({ config, instanceId, isEditing, onRemove, onConfigure, onFullscreen, widgetType, dashboardName }) => {
  const { token } = theme.useToken();
  const context = useDashboardContext();

  const { data, isLoading, error, refetch } = useCostEvents({
    project_id: context.projectId,
    quality_only: true,
    page: 1,
    perPage: config.pageSize,
  });

  const items = data?.items ?? [];

  const columns = useMemo<ColumnsType<CostEventRead>>(
    () => [
      {
        title: "Name",
        dataIndex: "name",
        key: "name",
        ellipsis: true,
        render: (val: string) => (
          <Text style={{ fontSize: token.fontSizeSM }}>{val}</Text>
        ),
      },
      {
        title: "Category",
        dataIndex: "coq_category",
        key: "coq_category",
        width: 120,
        render: (val: string | null) => (
          <Tag color={CATEGORY_COLORS[val ?? ""] ?? "default"}>
            {CATEGORY_LABELS[val ?? ""] ?? val ?? "-"}
          </Tag>
        ),
      },
      {
        title: "Planned Cost",
        dataIndex: "cost_impact",
        key: "cost_impact",
        width: 110,
        align: "right",
        render: (val: string) => (
          <Text style={{ fontSize: token.fontSizeSM }}>
            {formatCurrency(val)}
          </Text>
        ),
      },
      {
        title: "Status",
        dataIndex: "status",
        key: "status",
        width: 80,
        render: (val: string) => (
          <Tag color={val === "open" ? "processing" : "default"}>
            {val}
          </Tag>
        ),
      },
    ],
    [token.fontSizeSM],
  );

  if (!context.projectId) {
    return (
      <WidgetShell
        instanceId={instanceId}
        title="COQ Work Packages"
        icon={<UnorderedListOutlined />}
        isEditing={isEditing}
        isLoading={false}
        error={null}
        onRemove={onRemove}
        onConfigure={onConfigure}
        onFullscreen={onFullscreen}
        widgetType={widgetType}
        dashboardName={dashboardName}
      >
        <Empty description="No project selected" />
      </WidgetShell>
    );
  }

  return (
    <WidgetShell
      instanceId={instanceId}
      title="COQ Work Packages"
      icon={<UnorderedListOutlined />}
      isEditing={isEditing}
      isLoading={isLoading}
      error={error}
      onRemove={onRemove}
      onRefresh={refetch}
      onConfigure={onConfigure}
      onFullscreen={onFullscreen}
      widgetType={widgetType}
      dashboardName={dashboardName}
    >
      <Table<CostEventRead>
        columns={columns}
        dataSource={items}
        rowKey="id"
        size="small"
        pagination={{ pageSize: config.pageSize, size: "small" }}
        scroll={{ y: 220 }}
        style={{ fontSize: token.fontSizeSM }}
      />
    </WidgetShell>
  );
};

registerWidget<COQWorkPackagesConfig>({
  typeId: widgetTypeId("coq-work-packages"),
  displayName: "COQ Work Packages",
  description: "List of quality impact work packages with category and cost",
  category: "action",
  icon: <UnorderedListOutlined />,
  sizeConstraints: {
    minW: 4,
    minH: 3,
    defaultW: 6,
    defaultH: 3,
  },
  component: COQWorkPackagesComponent,
  defaultConfig: {
    pageSize: 5,
  },
});
