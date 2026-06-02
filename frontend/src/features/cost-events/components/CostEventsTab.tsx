import { useMemo, useState } from "react";
import {
  Table,
  Button,
  Space,
  Tag,
  Popconfirm,
  Tooltip,
  Select,
} from "antd";
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  HistoryOutlined,
  LinkOutlined,
  CalendarOutlined,
  SwapOutlined,
} from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import { usePermission } from "@/hooks/usePermission";
import { useThemeTokens } from "@/hooks/useThemeTokens";
import { useEntityHistory } from "@/hooks/useEntityHistory";
import { VersionHistoryDrawer } from "@/components/common/VersionHistory";
import { mapHistoryVersions } from "@/utils/versionHistory";
import { formatCurrency } from "@/utils/formatters";
import { useProjectCurrency } from "@/features/projects/api/useProjectCurrency";
import { OpenAPI } from "@/api/generated/core/OpenAPI";
import { request as __request } from "@/api/generated/core/request";
import type { CostEventRead, CostEventCreate, CostEventUpdate } from "@/api/generated";
import {
  useCostEvents,
  useCreateCostEvent,
  useUpdateCostEvent,
  useDeleteCostEvent,
  useCostEventTypes,
} from "../api/useCostEvents";
import { CostEventModal } from "./CostEventModal";
import { CostEventSummaryCard } from "./CostEventSummaryCard";
import { CostEventBreakdownDrawer } from "./CostEventBreakdownDrawer";

const STATUS_COLORS: Record<string, string> = {
  open: "blue",
  closed: "default",
};

interface CostEventsTabProps {
  projectId: string;
}

export const CostEventsTab = ({ projectId }: CostEventsTabProps) => {
  const { spacing, colors, borderRadius, typography } = useThemeTokens();
  const { can } = usePermission();
  const currency = useProjectCurrency(projectId);
  const { data: costEventTypeOptions } = useCostEventTypes();

  // Build dynamic color lookup from API data
  const typeColors = useMemo(() => {
    const colorMap: Record<string, string> = {};
    (costEventTypeOptions || []).forEach((ct) => {
      colorMap[ct.value] = ct.color;
    });
    return colorMap;
  }, [costEventTypeOptions]);

  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(10);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingEvent, setEditingEvent] =
    useState<CostEventRead | null>(null);
  const [historyDrawerOpen, setHistoryDrawerOpen] = useState(false);
  const [historyEventId, setHistoryEventId] = useState<string | null>(null);
  const [breakdownDrawerOpen, setBreakdownDrawerOpen] = useState(false);
  const [breakdownEvent, setBreakdownEvent] =
    useState<CostEventRead | null>(null);
  const [typeFilter, setTypeFilter] = useState<string | null>(null);

  // Query cost events
  const { data: eventsData, isLoading } = useCostEvents({
    project_id: projectId,
    cost_event_type_id: typeFilter ?? undefined,
    page,
    perPage,
  });

  const events = eventsData?.items || [];
  const total = eventsData?.total || 0;

  // Mutations
  const createMutation = useCreateCostEvent();
  const updateMutation = useUpdateCostEvent();
  const deleteMutation = useDeleteCostEvent();

  // History query
  const { data: historyData, isLoading: historyLoading } = useEntityHistory({
    resource: "cost-events",
    entityId: historyEventId,
    fetchFn: async (id) => {
      return __request(OpenAPI, {
        method: "GET",
        url: "/api/v1/cost-events/{cost_event_id}/history",
        path: { cost_event_id: id },
        errors: { 422: "Validation Error" },
      }) as Promise<CostEventRead[]>;
    },
    enabled: historyDrawerOpen && !!historyEventId,
  });

  const handleCreate = () => {
    setEditingEvent(null);
    setModalOpen(true);
  };

  const handleEdit = (ev: CostEventRead) => {
    setEditingEvent(ev);
    setModalOpen(true);
  };

  const handleDelete = async (ev: CostEventRead) => {
    await deleteMutation.mutateAsync({
      id: ev.cost_event_id,
      projectId,
    });
  };

  const handleToggleStatus = async (ev: CostEventRead) => {
    const newStatus = ev.status === "open" ? "closed" : "open";
    await updateMutation.mutateAsync({
      id: ev.cost_event_id,
      data: { status: newStatus },
    });
  };

  const handleModalOk = async (
    values: CostEventCreate | CostEventUpdate,
  ) => {
    if (editingEvent) {
      await updateMutation.mutateAsync({
        id: editingEvent.cost_event_id,
        data: values as CostEventUpdate,
      });
    } else {
      await createMutation.mutateAsync(values as CostEventCreate);
    }
    setModalOpen(false);
    setEditingEvent(null);
  };

  const handleViewHistory = (ev: CostEventRead) => {
    setHistoryEventId(ev.cost_event_id);
    setHistoryDrawerOpen(true);
  };

  const handleViewBreakdowns = (ev: CostEventRead) => {
    setBreakdownEvent(ev);
    setBreakdownDrawerOpen(true);
  };

  const columns: ColumnsType<CostEventRead> = [
    {
      title: "Name",
      dataIndex: "name",
      key: "name",
      width: 200,
      ellipsis: true,
      render: (name: string, record) => (
        <Tooltip title={name}>
          <span style={{ fontWeight: typography.weights.medium }}>
            {name}
          </span>
          {record.external_event_id &&
            record.external_event_id !== record.name && (
              <span
                style={{
                  color: colors.textTertiary,
                  fontSize: typography.sizes.xs,
                  marginLeft: spacing.xs,
                }}
              >
                ({record.external_event_id})
              </span>
            )}
        </Tooltip>
      ),
    },
    {
      title: "Type",
      dataIndex: "cost_event_type_id",
      key: "cost_event_type_id",
      width: 140,
      render: (_: string, record: CostEventRead) => (
        <Tag color={typeColors[record.cost_event_type_id] || "default"}>
          {record.cost_event_type_name || record.cost_event_type_code || "Unknown"}
        </Tag>
      ),
    },
    {
      title: "Status",
      dataIndex: "status",
      key: "status",
      width: 90,
      render: (status: string) => (
        <Tag color={STATUS_COLORS[status] || "default"}>
          {status ? status.charAt(0).toUpperCase() + status.slice(1) : "-"}
        </Tag>
      ),
    },
    {
      title: "Date",
      dataIndex: "event_date_formatted",
      key: "event_date",
      width: 130,
      render: (dateFormatted: { formatted: string }) => {
        const val = dateFormatted?.formatted;
        return val && val !== "Unknown" ? val : "-";
      },
    },
    {
      title: "COQ Category",
      dataIndex: "coq_category",
      key: "coq_category",
      width: 140,
      render: (category: string | null) => {
        if (!category) return <span style={{ color: colors.textTertiary }}>-</span>;
        return (
          <Tag
            color={
              category === "conformance" ? colors.success : colors.error
            }
            style={{ textTransform: "capitalize" }}
          >
            {category}
          </Tag>
        );
      },
    },
    {
      title: "Est. Impact",
      dataIndex: "estimated_impact",
      key: "estimated_impact",
      width: 140,
      align: "right",
      render: (cost: string) => (
        <span
          style={{
            fontWeight: typography.weights.medium,
            color: colors.text,
          }}
        >
          {formatCurrency(Number(cost || 0), currency)}
        </span>
      ),
      sorter: (a, b) =>
        Number(a.estimated_impact || 0) - Number(b.estimated_impact || 0),
    },
    {
      title: "Schedule",
      dataIndex: "schedule_impact_days",
      key: "schedule_impact_days",
      width: 110,
      render: (days: number | null) => {
        if (!days || days === 0) {
          return <span style={{ color: colors.textTertiary }}>-</span>;
        }
        return (
          <span style={{ color: colors.error }}>
            <CalendarOutlined style={{ marginRight: spacing.xs }} />
            {days}d
          </span>
        );
      },
    },
    {
      title: "Actual",
      key: "actual_cost",
      width: 130,
      align: "right",
      render: (_, record) => {
        const planned = Number(record.estimated_impact || 0);
        const actual = record.actual_cost ? Number(record.actual_cost) : null;
        if (actual === null || actual === undefined) {
          return <span style={{ color: colors.textTertiary }}>-</span>;
        }
        const overBudget = actual > planned;
        return (
          <Tooltip
            title={`Planned: ${formatCurrency(planned, currency)} | Actual: ${formatCurrency(actual, currency)}`}
          >
            <span
              style={{
                fontWeight: typography.weights.medium,
                color: overBudget ? colors.error : colors.text,
              }}
            >
              {formatCurrency(actual, currency)}
            </span>
          </Tooltip>
        );
      },
    },
    {
      title: "",
      key: "allocations",
      width: 70,
      render: (_, record) => (
        <Tooltip title="View allocations">
          <LinkOutlined
            onClick={() => handleViewBreakdowns(record)}
            style={{ color: colors.primary, cursor: "pointer" }}
          />
        </Tooltip>
      ),
    },
    {
      title: "Actions",
      key: "actions",
      width: 140,
      fixed: "right",
      render: (_, record) => (
        <Space size="small">
          {can("work-package-update") && (
            <Tooltip title={record.status === "open" ? "Close" : "Reopen"}>
              <Button
                type="text"
                icon={<SwapOutlined />}
                onClick={() => handleToggleStatus(record)}
                style={{ color: colors.textSecondary }}
              />
            </Tooltip>
          )}
          {can("work-package-update") && (
            <Button
              type="text"
              icon={<EditOutlined />}
              onClick={() => handleEdit(record)}
              style={{ color: colors.primary }}
            />
          )}
          <Button
            type="text"
            icon={<HistoryOutlined />}
            onClick={() => handleViewHistory(record)}
            style={{ color: colors.info }}
          />
          {can("work-package-delete") && (
            <Popconfirm
              title="Delete Cost Event"
              description="Are you sure you want to delete this cost event?"
              onConfirm={() => handleDelete(record)}
              okText="Delete"
              okButtonProps={{ danger: true }}
              cancelText="Cancel"
            >
              <Button type="text" icon={<DeleteOutlined />} danger />
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ];

  return (
    <div>
      {/* Summary Card */}
      {(typeFilter === null ||
        costEventTypeOptions?.find((ct) => ct.value === typeFilter)?.is_quality) && <CostEventSummaryCard projectId={projectId} />}

      {/* Action Bar */}
      <div
        style={{
          marginBottom: spacing.md,
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <h2 style={{ margin: 0, fontSize: typography.sizes.lg }}>
          Cost Events
        </h2>
        {can("work-package-create") && (
          <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
            Add Event
          </Button>
        )}
      </div>

      {/* Type Filter */}
      <div style={{ marginBottom: spacing.md }}>
        <Select
          placeholder="Filter by type"
          value={typeFilter ?? undefined}
          onChange={(value) => {
            setTypeFilter(value ?? null);
            setPage(1);
          }}
          options={(costEventTypeOptions || []).map((opt) => ({
            label: opt.label,
            value: opt.value,
          }))}
          allowClear
          style={{ minWidth: 200 }}
        />
      </div>

      {/* Table */}
      <Table
        columns={columns}
        dataSource={events}
        rowKey="cost_event_id"
        loading={isLoading}
        pagination={{
          current: page,
          pageSize: perPage,
          total,
          showSizeChanger: true,
          showTotal: (t) => `Total ${t} events`,
          onChange: (newPage, newPerPage) => {
            setPage(newPage);
            setPerPage(newPerPage || 10);
          },
        }}
        scroll={{ x: 1200 }}
        style={{
          borderRadius: borderRadius.lg,
        }}
      />

      {/* Create/Edit Modal */}
      <CostEventModal
        open={modalOpen}
        onCancel={() => {
          setModalOpen(false);
          setEditingEvent(null);
        }}
        onOk={handleModalOk}
        confirmLoading={
          createMutation.isPending || updateMutation.isPending
        }
        initialValues={editingEvent}
        projectId={projectId}
        currency={currency}
      />

      {/* History Drawer */}
      <VersionHistoryDrawer
        open={historyDrawerOpen}
        onClose={() => {
          setHistoryDrawerOpen(false);
          setHistoryEventId(null);
        }}
        versions={mapHistoryVersions(historyData)}
        entityName="Cost Event"
        isLoading={historyLoading}
      />

      {/* Breakdown Drawer */}
      <CostEventBreakdownDrawer
        open={breakdownDrawerOpen}
        onClose={() => {
          setBreakdownDrawerOpen(false);
          setBreakdownEvent(null);
        }}
        costEventId={breakdownEvent?.cost_event_id || null}
        name={breakdownEvent?.name}
        totalCost={Number(breakdownEvent?.estimated_impact || 0)}
        currency={currency}
      />
    </div>
  );
};
