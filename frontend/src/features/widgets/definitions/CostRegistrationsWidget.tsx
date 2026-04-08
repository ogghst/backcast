import { UnorderedListOutlined } from "@ant-design/icons";
import { Tag, Typography } from "antd";
import type { ColumnsType } from "antd/es/table";
import type { SorterResult } from "antd/es/table/interface";
import type { FilterValue, TablePaginationConfig } from "antd/es/table/interface";
import { useState, useCallback, useMemo, type FC } from "react";
import { useDashboardContext } from "../context/useDashboardContext";
import { useCostRegistrations } from "@/features/cost-registration/api/useCostRegistrations";
import type { CostRegistrationRead } from "@/api/generated";
import { StandardTable, type TableParams } from "@/components/common/StandardTable";
import { WidgetShell } from "../components/WidgetShell";
import { CostRegistrationsConfigForm } from "../components/config-forms/CostRegistrationsConfigForm";
import { registerWidget, widgetTypeId } from "..";
import type { WidgetComponentProps } from "../types";

const { Text } = Typography;

interface CostRegistrationsConfig {
  pageSize: number;
  showAddButton: boolean;
}

const formatCurrency = (value: string | number): string => {
  const num = typeof value === "string" ? parseFloat(value) : value;
  return new Intl.NumberFormat("en-IE", {
    style: "currency",
    currency: "EUR",
  }).format(num);
};

const formatDate = (dateStr: string | null | undefined): string => {
  if (!dateStr) return "-";
  return new Date(dateStr).toLocaleDateString("en-IE", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
};

const columns: ColumnsType<CostRegistrationRead> = [
  {
    title: "Date",
    dataIndex: "registration_date",
    key: "registration_date",
    width: 120,
    render: (val: string | null) => formatDate(val),
  },
  {
    title: "Description",
    dataIndex: "description",
    key: "description",
    ellipsis: true,
    render: (val: string | null) => val || <Text type="secondary">-</Text>,
  },
  {
    title: "Amount",
    dataIndex: "amount",
    key: "amount",
    width: 130,
    align: "right",
    render: (val: string) => (
      <Tag color="blue" style={{ minWidth: 80, textAlign: "center" }}>
        {formatCurrency(val)}
      </Tag>
    ),
  },
  {
    title: "Cost Element",
    dataIndex: "cost_element_id",
    key: "cost_element_id",
    width: 120,
    ellipsis: true,
    render: (val: string) => (
      <Text type="secondary" style={{ fontSize: 12 }}>
        {val.slice(0, 8)}...
      </Text>
    ),
  },
];

const CostRegistrationsComponent: FC<
  WidgetComponentProps<CostRegistrationsConfig>
> = ({ config, instanceId, isEditing, onRemove, onConfigure, onFullscreen, widgetType, dashboardName }) => {
  const context = useDashboardContext();

  const [tableParams, setTableParams] = useState<TableParams>({
    pagination: {
      current: 1,
      pageSize: config.pageSize,
    },
  });

  const queryParams = useMemo(() => {
    if (context.costElementId) {
      return { cost_element_id: context.costElementId };
    }
    if (context.wbeId) {
      return { wbe_id: context.wbeId };
    }
    return { project_id: context.projectId };
  }, [context.costElementId, context.wbeId, context.projectId]);

  const { data, isLoading, error, refetch } = useCostRegistrations({
    ...queryParams,
    pagination: {
      current: tableParams.pagination?.current,
      pageSize: tableParams.pagination?.pageSize,
    },
  });

  const handleTableChange = useCallback(
    (
      pagination: TablePaginationConfig,
      filters: Record<string, FilterValue | null>,
      sorter: SorterResult<CostRegistrationRead> | SorterResult<CostRegistrationRead>[],
    ) => {
      const sortResult = Array.isArray(sorter) ? sorter[0] : sorter;
      setTableParams({
        pagination,
        filters,
        sortField: sortResult.field as string | undefined,
        sortOrder: sortResult.order,
      });
    },
    [],
  );

  return (
    <WidgetShell
      instanceId={instanceId}
      title="Cost Registrations"
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
      <StandardTable<CostRegistrationRead>
        columns={columns}
        dataSource={data?.items ?? []}
        rowKey="id"
        tableParams={tableParams}
        onChange={handleTableChange}
        size="small"
        scroll={{ y: 300 }}
      />
    </WidgetShell>
  );
};

registerWidget<CostRegistrationsConfig>({
  typeId: widgetTypeId("cost-registrations"),
  displayName: "Cost Registrations",
  description: "List of recent cost registrations with pagination",
  category: "action",
  icon: <UnorderedListOutlined />,
  sizeConstraints: {
    minW: 3,
    minH: 2,
    defaultW: 3,
    defaultH: 2,
  },
  component: CostRegistrationsComponent,
  defaultConfig: {
    pageSize: 10,
    showAddButton: false,
  },
  configFormComponent: CostRegistrationsConfigForm,
});
