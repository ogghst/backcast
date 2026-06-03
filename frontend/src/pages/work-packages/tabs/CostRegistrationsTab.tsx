import { App, Button, Space, Input, Tag, Grid, Badge, Typography, Alert, theme, Empty, Spin } from "antd";
import {
  DeleteOutlined,
  EditOutlined,
  PlusOutlined,
  HistoryOutlined,
  SearchOutlined,
  PaperClipOutlined,
} from "@ant-design/icons";
import { useState } from "react";
import type { ColumnType } from "antd/es/table";
import type { FilterValue } from "antd/es/table/interface";
import { formatDate } from "@/utils/formatters";
import {
  CostRegistrationsService,
  type CostRegistrationRead,
  type CostRegistrationCreate,
} from "@/api/generated";
import { Can } from "@/components/auth/Can";
import type { WorkPackageRead } from "@/api/generated";
import {
  useCostRegistrations,
  useCreateCostRegistration,
  useUpdateCostRegistration,
  useDeleteCostRegistration,
} from "@/features/cost-registration/api/useCostRegistrations";
import { CostRegistrationModal } from "@/features/cost-registration/components/CostRegistrationModal";
import { StandardTable } from "@/components/common/StandardTable";
import { useTableParams } from "@/hooks/useTableParams";
import { VersionHistoryDrawer } from "@/components/common/VersionHistory";
import { useEntityHistory } from "@/hooks/useEntityHistory";
import { mapHistoryVersions } from "@/utils/versionHistory";
import { useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "@/api/queryKeys";
import { useTimeMachineParams } from "@/contexts/TimeMachineContext";

import { useParams } from "react-router-dom";
import { useProjectCurrency } from "@/features/projects/api/useProjectCurrency";
import { getCurrencySymbol } from "@/utils/formatters";
import { ViewModeToggle } from "@/components/common/ViewModeToggle";
import { useViewMode } from "@/hooks/useViewMode";
import { CostRegistrationCard } from "@/features/cost-registration/components/CostRegistrationCard";
import { useCostEventTypes } from "@/features/cost-events/api/useCostEvents";
import { WorkPackagesPmiService } from "@/api/generated";
import type { CostElementRead } from "@/api/generated";
import { useQuery } from "@tanstack/react-query";

const { Text } = Typography;

interface CostRegistrationsTabProps {
  workPackage: WorkPackageRead;
}

interface CostRegistrationApiParams {
  work_package_id?: string;
  pagination?: { current?: number; pageSize?: number };
  filters?: Record<string, (string | number | boolean)[] | null>;
  sortField?: string;
  sortOrder?: string;
  search?: string;
  [key: string]: unknown;
}

export const CostRegistrationsTab = ({
  workPackage,
}: CostRegistrationsTabProps) => {
  const { projectId } = useParams<{ projectId: string }>();
  const { tableParams, handleTableChange, handleSearch } = useTableParams<
    CostRegistrationRead,
    Record<string, FilterValue | null>
  >();
  const queryClient = useQueryClient();
  const { asOf } = useTimeMachineParams();
  const screens = Grid.useBreakpoint();
  const { data: packageTypeOptions } = useCostEventTypes();
  const isMobile = !screens.md;
  const { token } = theme.useToken();
  const { viewMode: crViewMode, resolvedMode: crResolvedMode, cycleViewMode: crCycleViewMode } = useViewMode("cost-registrations", isMobile);
  const useCard = crResolvedMode === "card";

  const currency = useProjectCurrency(undefined);
  const currencySymbol = getCurrencySymbol(currency);

  // Fetch cost elements for this work package
  const { data: costElements = [], isLoading: costElementsLoading } = useQuery<
    CostElementRead[]
  >({
    queryKey: queryKeys.costElements.list(workPackage.work_package_id),
    queryFn: async () => {
      const res = await WorkPackagesPmiService.getWorkPackageCostElements(
        workPackage.work_package_id,
      );
      return (res as CostElementRead[]) || [];
    },
    enabled: !!workPackage.work_package_id,
  });

  // Build query params - use work_package_id for aggregated view across all EOCs
  const queryParams: CostRegistrationApiParams = {
    work_package_id: workPackage.work_package_id,
    pagination: tableParams.pagination,
    sortField: tableParams.sortField,
    sortOrder: tableParams.sortOrder,
    search: tableParams.search,
  };

  const { data, isLoading, refetch } = useCostRegistrations(queryParams);
  const costRegistrations = data?.items || [];
  const total = data?.total || 0;

  const [modalOpen, setModalOpen] = useState(false);
  const [selectedRegistration, setSelectedRegistration] =
    useState<CostRegistrationRead | null>(null);
  const [historyOpen, setHistoryOpen] = useState(false);

  // History hook
  const { data: historyVersions, isLoading: historyLoading } = useEntityHistory(
    {
      resource: "cost_registrations",
      entityId: selectedRegistration?.cost_registration_id,
      fetchFn: (id) => CostRegistrationsService.getCostRegistrationHistory(id),
      enabled: historyOpen,
    },
  );

  const { mutateAsync: createCostRegistration } = useCreateCostRegistration({
    onSuccess: () => {
      refetch();
      queryClient.invalidateQueries({
        queryKey: queryKeys.costRegistrations.budgetStatus(
          workPackage.work_package_id,
          { asOf },
        ),
      });
      setModalOpen(false);
    },
  });

  const { mutateAsync: updateCostRegistration } = useUpdateCostRegistration({
    onSuccess: () => {
      refetch();
      queryClient.invalidateQueries({
        queryKey: queryKeys.costRegistrations.budgetStatus(
          workPackage.work_package_id,
          { asOf },
        ),
      });
      setModalOpen(false);
    },
  });

  const { mutate: deleteCostRegistration } = useDeleteCostRegistration({
    onSuccess: () => {
      refetch();
      queryClient.invalidateQueries({
        queryKey: queryKeys.costRegistrations.budgetStatus(
          workPackage.work_package_id,
          { asOf },
        ),
      });
    },
  });

  const { modal } = App.useApp();

  const handleDelete = (registration: CostRegistrationRead) => {
    modal.confirm({
      title: "Are you sure you want to delete this Cost Registration?",
      content:
        "This will soft delete the cost registration. It will be preserved in history.",
      okText: "Yes, Delete",
      okType: "danger",
      onOk: () =>
        deleteCostRegistration({
          id: registration.cost_registration_id,
          costElementId: registration.cost_element_id,
        }),
    });
  };

  const handleAddCost = () => {
    if (costElements.length === 0) return;
    setSelectedRegistration(null);
    setModalOpen(true);
  };

  const getColumnSearchProps = (
    dataIndex: keyof CostRegistrationRead,
  ): ColumnType<CostRegistrationRead> => ({
    filterDropdown: ({
      setSelectedKeys,
      selectedKeys,
      confirm,
      clearFilters,
    }) => (
      <div style={{ padding: 8 }}>
        <Input
          placeholder={`Search ${dataIndex}`}
          value={selectedKeys[0]}
          onChange={(e) =>
            setSelectedKeys(e.target.value ? [e.target.value] : [])
          }
          onPressEnter={() => confirm()}
          style={{ width: 188, marginBottom: 8, display: "block" }}
        />
        <Space>
          <Button
            type="primary"
            onClick={() => confirm()}
            icon={<SearchOutlined />}
            size="small"
            style={{ width: 90 }}
          >
            Search
          </Button>
          <Button
            onClick={() => clearFilters && clearFilters()}
            size="small"
            style={{ width: 90 }}
          >
            Reset
          </Button>
        </Space>
      </div>
    ),
    filterIcon: (filtered: boolean) => (
      <SearchOutlined style={{ color: filtered ? "#1890ff" : undefined }} />
    ),
    onFilter: (value, record) => {
      const fieldVal = record[dataIndex];
      return fieldVal
        ? fieldVal
            .toString()
            .toLowerCase()
            .includes((value as string).toLowerCase())
        : false;
    },
  });

  const columns: ColumnType<CostRegistrationRead>[] = [
    {
      title: "Amount",
      dataIndex: "amount",
      key: "amount",
      align: "right",
      sorter: true,
      width: 120,
      render: (amount) => (
        <span>
          {currencySymbol}
          {Number(amount).toLocaleString(undefined, {
            minimumFractionDigits: 2,
          })}
        </span>
      ),
    },
    {
      title: "Quantity",
      dataIndex: "quantity",
      key: "quantity",
      align: "right",
      responsive: ["sm"],
      render: (quantity) =>
        quantity ? Number(quantity).toLocaleString() : "-",
    },
    {
      title: "Unit",
      dataIndex: "unit_of_measure",
      key: "unit_of_measure",
      responsive: ["md"],
      render: (unit) => unit || "-",
    },
    {
      title: "Date",
      dataIndex: "registration_date",
      key: "registration_date",
      sorter: true,
      width: 140,
      render: (date) => formatDate(date, { style: "short", fallback: "-" }),
    },
    {
      title: "Description",
      dataIndex: "description",
      key: "description",
      ellipsis: true,
      ...getColumnSearchProps("description"),
      render: (description) => description || "-",
    },
    {
      title: "Cost Element",
      dataIndex: "cost_element_type_name",
      key: "cost_element_type_name",
      responsive: ["md"],
      render: (
        name: string | null,
        record: CostRegistrationRead,
      ) => {
        if (!name) return "-";
        const typeLabel =
          packageTypeOptions?.find(
            (o) => o.value === record.cost_event_type,
          )?.label || record.cost_event_type;
        return (
          <Space size={4}>
            <span>{name}</span>
            {record.cost_event_type && (
              <Tag>{typeLabel}</Tag>
            )}
          </Space>
        );
      },
    },
    {
      title: "Invoice",
      dataIndex: "invoice_number",
      key: "invoice_number",
      responsive: ["lg"],
      ...getColumnSearchProps("invoice_number"),
      render: (invoice) => invoice || "-",
    },
    {
      title: "Vendor",
      dataIndex: "vendor_reference",
      key: "vendor_reference",
      responsive: ["lg"],
      ...getColumnSearchProps("vendor_reference"),
      render: (vendor) => vendor || "-",
    },
    {
      title: "Files",
      dataIndex: "attachment_count",
      key: "attachment_count",
      width: 70,
      align: "center",
      responsive: ["sm"],
      render: (count: number) =>
        count > 0 ? (
          <Badge count={count} size="small" color="blue">
            <PaperClipOutlined style={{ fontSize: 16 }} />
          </Badge>
        ) : (
          <Text type="secondary">-</Text>
        ),
    },
    {
      title: "Actions",
      key: "actions",
      width: isMobile ? 80 : 150,
      fixed: "right",
      render: (_, record) => (
        <Space>
          <Can permission="cost-registration-read">
            <Button
              icon={<HistoryOutlined />}
              onClick={() => {
                setSelectedRegistration(record);
                setHistoryOpen(true);
              }}
              title="View History"
            />
          </Can>
          <Can permission="cost-registration-update">
            <Button
              icon={<EditOutlined />}
              onClick={() => {
                setSelectedRegistration(record);
                setModalOpen(true);
              }}
              title="Edit"
            />
          </Can>
          <Can permission="cost-registration-delete">
            <Button
              danger
              icon={<DeleteOutlined />}
              onClick={() => handleDelete(record)}
              title="Delete"
            />
          </Can>
        </Space>
      ),
    },
  ];

  // Calculate total costs
  const totalCosts = costRegistrations.reduce(
    (sum, registration) => sum + Number(registration.amount),
    0,
  );

  return (
    <div>
      {costElements.length === 0 && !costElementsLoading && (
        <Alert
          message="No Cost Elements"
          description="Create cost elements first in the Work Package overview before adding cost registrations."
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
        />
      )}

      {/* Toolbar - shared between card and table views */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: token.marginMD }}>
        <Space>
          <div style={{ fontSize: "16px", fontWeight: "bold" }}>
            Cost Registrations
          </div>
          <Tag color="blue">
            Total: {currencySymbol}
            {totalCosts.toLocaleString(undefined, { minimumFractionDigits: 2 })}
          </Tag>
        </Space>
        <Space>
          <ViewModeToggle viewMode={crViewMode} onCycleViewMode={crCycleViewMode} />
          {costElements.length > 0 && (
            <Can permission="cost-registration-create">
              <Button type="primary" icon={<PlusOutlined />} onClick={handleAddCost}>
                Add Cost
              </Button>
            </Can>
          )}
        </Space>
      </div>

      {/* Card view */}
      {useCard ? (
        isLoading ? (
          <div style={{ display: "flex", justifyContent: "center", padding: token.paddingXL }}><Spin /></div>
        ) : costRegistrations.length === 0 ? (
          <Empty description="No cost registrations" />
        ) : (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: token.marginMD }}>
            {costRegistrations.map((cr) => (
              <CostRegistrationCard
                key={cr.id || cr.cost_registration_id}
                registration={cr}
                currencySymbol={currencySymbol}
              />
            ))}
          </div>
        )
      ) : (
        /* Table view */
        <StandardTable<CostRegistrationRead>
          tableParams={{
            ...tableParams,
            pagination: { ...tableParams.pagination, total },
          }}
          onChange={handleTableChange}
          loading={isLoading}
          dataSource={costRegistrations}
          columns={columns}
          rowKey="id"
          searchable={true}
          searchPlaceholder="Search cost registrations..."
          onSearch={handleSearch}
          scroll={{ x: isMobile ? "max-content" : undefined }}
          size={isMobile ? "small" : "middle"}
        />
      )}

      {/* Cost element picker modal -- shown when multiple cost elements exist */}
      {/* Create/Edit modal */}
      <CostRegistrationModal
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={async (values) => {
          if (selectedRegistration) {
            await updateCostRegistration({
              id: selectedRegistration.cost_registration_id,
              data: values,
              costElementId: selectedRegistration.cost_element_id,
            });
          } else {
            await createCostRegistration(values as CostRegistrationCreate);
          }
        }}
        confirmLoading={isLoading}
        initialValues={selectedRegistration}
        costElementId={selectedRegistration?.cost_element_id}
        workPackageId={workPackage.work_package_id}
        projectId={projectId || ""}
      />

      <VersionHistoryDrawer
        open={historyOpen}
        onClose={() => setHistoryOpen(false)}
        versions={mapHistoryVersions(historyVersions)}
        entityName={`Cost Registration: ${
          selectedRegistration?.description ||
          `${currencySymbol}${selectedRegistration?.amount}`
        }`}
        isLoading={historyLoading}
      />
    </div>
  );
};
