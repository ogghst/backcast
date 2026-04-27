import {
  App,
  Button,
  Space,
  Input,
  Tooltip,
  Progress,
} from "antd";
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
import type { CostElementRead } from "@/api/generated";
import { formatDate, parseTemporalRangeLower } from "@/utils/formatters";
import type { ProgressEntryRead, ProgressEntryCreate } from "@/api/generated";
import {
  useProgressEntries,
  useCreateProgressEntry,
  useUpdateProgressEntry,
  useDeleteProgressEntry,
} from "../api/useProgressEntries";
import { ProgressEntryModal } from "./ProgressEntryModal";
import { ProgressSummaryCard } from "./ProgressSummaryCard";
import { StandardTable } from "@/components/common/StandardTable";
import { useTableParams } from "@/hooks/useTableParams";
import { Can } from "@/components/auth/Can";
import { useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "@/api/queryKeys";
import { useEntityHistory } from "@/hooks/useEntityHistory";
import { VersionHistoryDrawer } from "@/components/common/VersionHistory";
import { mapHistoryVersions } from "@/utils/versionHistory";
import { ProgressEntriesService } from "@/api/generated";

interface ProgressEntriesTabProps {
  costElement: CostElementRead;
}

interface ProgressEntryApiParams {
  cost_element_id?: string;
  page?: number;
  perPage?: number;
  asOf?: string;
}

/**
 * Progress Entries Tab Component
 *
 * Displays progress entries for a cost element with:
 * - Latest progress summary card
 * - Progress visualization
 * - Paginated history table
 * - CRUD operations
 */
export const ProgressEntriesTab = ({
  costElement,
}: ProgressEntriesTabProps) => {
  const { tableParams, handleTableChange, handleSearch } = useTableParams<
    ProgressEntryRead,
    Record<string, FilterValue | null>
  >();
  const queryClient = useQueryClient();

  // Build query params
  const queryParams: ProgressEntryApiParams = {
    cost_element_id: costElement.cost_element_id,
    page: tableParams.pagination?.current || 1,
    perPage: tableParams.pagination?.pageSize || 10,
  };

  const { data, isLoading, refetch } = useProgressEntries(queryParams);
  const progressEntries = data?.items || [];
  const total = data?.total || 0;

  const [modalOpen, setModalOpen] = useState(false);
  const [selectedEntry, setSelectedEntry] = useState<ProgressEntryRead | null>(
    null,
  );
  const [historyOpen, setHistoryOpen] = useState(false);

  // History hook
  const { data: historyVersions, isLoading: historyLoading } = useEntityHistory(
    {
      resource: "progress_entries",
      entityId: selectedEntry?.progress_entry_id,
      fetchFn: (id) => ProgressEntriesService.getProgressEntryHistory(id),
      enabled: historyOpen,
    },
  );

  const { mutateAsync: createProgressEntry } = useCreateProgressEntry({
    onSuccess: () => {
      refetch();
      queryClient.invalidateQueries({
        queryKey: queryKeys.costElements.evmMetrics(
          costElement.cost_element_id,
        ),
      });
      setModalOpen(false);
    },
  });

  const { mutateAsync: updateProgressEntry } = useUpdateProgressEntry({
    onSuccess: () => {
      refetch();
      queryClient.invalidateQueries({
        queryKey: queryKeys.costElements.evmMetrics(
          costElement.cost_element_id,
        ),
      });
      setModalOpen(false);
    },
  });

  const { mutate: deleteProgressEntry } = useDeleteProgressEntry({
    onSuccess: () => {
      refetch();
      queryClient.invalidateQueries({
        queryKey: queryKeys.costElements.evmMetrics(
          costElement.cost_element_id,
        ),
      });
    },
  });

  const { modal } = App.useApp();

  const handleDelete = (id: string) => {
    modal.confirm({
      title: "Are you sure you want to delete this Progress Entry?",
      content:
        "This will soft delete the progress entry. It will be preserved in history.",
      okText: "Yes, Delete",
      okType: "danger",
      onOk: () => deleteProgressEntry(id),
    });
  };

  const getColumnSearchProps = (
    dataIndex: keyof ProgressEntryRead,
  ): ColumnType<ProgressEntryRead> => ({
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

  const columns: ColumnType<ProgressEntryRead>[] = [
    {
      title: "Progress Date",
      dataIndex: "valid_time",
      key: "valid_time",
      sorter: true,
      render: (validTime: string) => {
        if (!validTime) return "-";
        return formatDate(parseTemporalRangeLower(validTime));
      },
    },
    {
      title: "Progress",
      dataIndex: "progress_percentage",
      key: "progress_percentage",
      sorter: true,
      render: (percentage) => {
        const value = parseFloat(percentage);
        return (
          <Space>
            <span>{value.toFixed(2)}%</span>
            <Progress
              percent={value}
              size="small"
              status={value === 100 ? "success" : "active"}
              style={{ width: 80 }}
            />
          </Space>
        );
      },
    },
    {
      title: "Notes",
      dataIndex: "notes",
      key: "notes",
      ...getColumnSearchProps("notes"),
      render: (notes) => {
        if (!notes) return "-";
        const truncated =
          notes.length > 50 ? notes.slice(0, 50) + "..." : notes;
        return notes.length > 50 ? (
          <Tooltip title={notes}>
            <span>{truncated}</span>
          </Tooltip>
        ) : (
          <span>{notes}</span>
        );
      },
    },
    {
      title: "Reported By",
      dataIndex: "created_by",
      key: "created_by",
      render: (name) => name || "-",
    },
    {
      title: "Actions",
      key: "actions",
      render: (_, record) => (
        <Space>
          <Can permission="progress-entry-read">
            <Button
              icon={<HistoryOutlined />}
              onClick={() => {
                setSelectedEntry(record);
                setHistoryOpen(true);
              }}
              title="View History"
            />
          </Can>
          <Can permission="progress-entry-update">
            <Button
              icon={<EditOutlined />}
              onClick={() => {
                setSelectedEntry(record);
                setModalOpen(true);
              }}
              title="Edit"
            />
          </Can>
          <Can permission="progress-entry-delete">
            <Button
              danger
              icon={<DeleteOutlined />}
              onClick={() => handleDelete(record.progress_entry_id)}
              title="Delete"
            />
          </Can>
        </Space>
      ),
    },
  ];

  // Latest progress (first entry since API returns in descending order)
  const latestProgress = progressEntries[0];

  return (
    <div>
      <Space direction="vertical" style={{ width: "100%" }} size="large">
        {/* Latest Progress Summary - using shared component */}
        <ProgressSummaryCard latestEntry={latestProgress} />

        {/* Progress Entries Table */}
        <StandardTable<ProgressEntryRead>
          tableParams={{
            ...tableParams,
            pagination: { ...tableParams.pagination, total },
          }}
          onChange={handleTableChange}
          loading={isLoading}
          dataSource={progressEntries}
          columns={columns}
          rowKey="progress_entry_id"
          searchable={true}
          searchPlaceholder="Search progress entries..."
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
              <div style={{ fontSize: "16px", fontWeight: "bold" }}>
                Progress History
              </div>

              <Can permission="progress-entry-create">
                <Button
                  type="primary"
                  icon={<PlusOutlined />}
                  onClick={() => {
                    setSelectedEntry(null);
                    setModalOpen(true);
                  }}
                >
                  Add Progress
                </Button>
              </Can>
            </div>
          }
        />
      </Space>

      {/* Create/Edit Modal */}
      <ProgressEntryModal
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={async (values) => {
          if (selectedEntry) {
            await updateProgressEntry({
              id: selectedEntry.progress_entry_id,
              data: values,
            });
          } else {
            await createProgressEntry(values as ProgressEntryCreate);
          }
        }}
        confirmLoading={isLoading}
        initialValues={selectedEntry}
        costElementId={costElement.cost_element_id}
      />

      {/* History Drawer */}
      <VersionHistoryDrawer
        open={historyOpen}
        onClose={() => setHistoryOpen(false)}
        versions={mapHistoryVersions(historyVersions)}
        entityName={`Progress Entry: ${
          selectedEntry?.progress_percentage
            ? `${selectedEntry.progress_percentage}%`
            : "Progress"
        }`}
        isLoading={historyLoading}
      />
    </div>
  );
};
