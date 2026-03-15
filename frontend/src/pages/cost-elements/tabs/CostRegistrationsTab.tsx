import { App, Button, Space, Input, Tag } from "antd";
import {
  DeleteOutlined,
  EditOutlined,
  PlusOutlined,
  HistoryOutlined,
  SearchOutlined,
} from "@ant-design/icons";
import { useState } from "react";
import type { ColumnType } from "antd/es/table";
import type { FilterValue } from "antd/es/table/interface";
import {
  CostRegistrationsService,
  type CostRegistrationRead,
} from "@/api/generated";
import { Can } from "@/components/auth/Can";
import type { CostElementRead } from "@/api/generated";
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
import { useQueryClient } from "@tanstack/react-query";
import dayjs from "dayjs";
import { queryKeys } from "@/api/queryKeys";
import { useTimeMachineParams } from "@/contexts/TimeMachineContext";

interface CostRegistrationsTabProps {
  costElement: CostElementRead;
}

interface CostRegistrationApiParams {
  cost_element_id?: string;
  pagination?: { current?: number; pageSize?: number };
  filters?: Record<string, (string | number | boolean)[] | null>;
  sortField?: string;
  sortOrder?: string;
  search?: string;
  [key: string]: unknown;
}

export const CostRegistrationsTab = ({
  costElement,
}: CostRegistrationsTabProps) => {
  const { tableParams, handleTableChange, handleSearch } = useTableParams<
    CostRegistrationRead,
    Record<string, FilterValue | null>
  >();
  const queryClient = useQueryClient();
  const { asOf } = useTimeMachineParams();

  // Build query params
  const queryParams: CostRegistrationApiParams = {
    cost_element_id: costElement.cost_element_id,
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
          costElement.cost_element_id,
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
          costElement.cost_element_id,
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
          costElement.cost_element_id,
          { asOf },
        ),
      });
    },
  });

  const { modal } = App.useApp();

  const handleDelete = (id: string) => {
    modal.confirm({
      title: "Are you sure you want to delete this Cost Registration?",
      content:
        "This will soft delete the cost registration. It will be preserved in history.",
      okText: "Yes, Delete",
      okType: "danger",
      onOk: () =>
        deleteCostRegistration({
          id,
          costElementId: costElement.cost_element_id,
        }),
    });
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
      render: (amount) => (
        <span>
          €
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
      render: (quantity) =>
        quantity ? Number(quantity).toLocaleString() : "-",
    },
    {
      title: "Unit",
      dataIndex: "unit_of_measure",
      key: "unit_of_measure",
      render: (unit) => unit || "-",
    },
    {
      title: "Registration Date",
      dataIndex: "registration_date",
      key: "registration_date",
      sorter: true,
      render: (date) => (date ? dayjs(date).format("YYYY-MM-DD HH:mm") : "-"),
    },
    {
      title: "Description",
      dataIndex: "description",
      key: "description",
      ...getColumnSearchProps("description"),
      render: (description) => description || "-",
    },
    {
      title: "Invoice",
      dataIndex: "invoice_number",
      key: "invoice_number",
      ...getColumnSearchProps("invoice_number"),
      render: (invoice) => invoice || "-",
    },
    {
      title: "Vendor",
      dataIndex: "vendor_reference",
      key: "vendor_reference",
      ...getColumnSearchProps("vendor_reference"),
      render: (vendor) => vendor || "-",
    },
    {
      title: "Actions",
      key: "actions",
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
              onClick={() => handleDelete(record.cost_registration_id)}
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
        toolbar={
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              width: "100%",
            }}
          >
            <Space>
              <div style={{ fontSize: "16px", fontWeight: "bold" }}>
                Cost Registrations
              </div>
              <Tag color="blue">
                Total: €
                {totalCosts.toLocaleString(undefined, {
                  minimumFractionDigits: 2,
                })}
              </Tag>
            </Space>

            <Can permission="cost-registration-create">
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={() => {
                  setSelectedRegistration(null);
                  setModalOpen(true);
                }}
              >
                Add Cost
              </Button>
            </Can>
          </div>
        }
      />

      <CostRegistrationModal
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={async (values) => {
          if (selectedRegistration) {
            await updateCostRegistration({
              id: selectedRegistration.cost_registration_id,
              data: values,
              costElementId: costElement.cost_element_id,
            });
          } else {
            // Filter out undefined values and ensure required fields are present
            // eslint-disable-next-line @typescript-eslint/no-unused-vars
            const { amount, cost_element_id: _cost_element_id, ...rest } = values;
            const createData: Parameters<typeof createCostRegistration>[0] = {
              cost_element_id: costElement.cost_element_id,
              amount: amount ?? 0,
              ...(rest && typeof rest === "object" ? rest : {}),
            };
            await createCostRegistration(createData);
          }
        }}
        confirmLoading={isLoading}
        initialValues={selectedRegistration}
        costElementId={costElement.cost_element_id}
      />

      <VersionHistoryDrawer
        open={historyOpen}
        onClose={() => setHistoryOpen(false)}
        versions={(historyVersions || []).map((version, idx, arr) => {
          // Helper type for history object variations
          type HistoryItem = {
            valid_from?: string;
            valid_time?: string | { lower: string };
            transaction_time?: string | { lower: string };
            created_by_name?: string;
          };
          const v = version as unknown as HistoryItem;

          return {
            id: `v${arr.length - idx}`,
            valid_from:
              v.valid_from ||
              (typeof v.valid_time === "object" ? v.valid_time?.lower : null) ||
              (typeof v.valid_time === "string"
                ? v.valid_time
                : new Date().toISOString()),
            transaction_time:
              (typeof v.transaction_time === "object"
                ? v.transaction_time?.lower
                : null) ||
              (typeof v.transaction_time === "string"
                ? v.transaction_time
                : new Date().toISOString()),
            changed_by: v.created_by_name || "System",
            changes:
              idx === 0 ? { created: "initial" } : { updated: "changed" },
          };
        })}
        entityName={`Cost Registration: ${
          selectedRegistration?.description ||
          `€${selectedRegistration?.amount}`
        }`}
        isLoading={historyLoading}
      />
    </div>
  );
};
