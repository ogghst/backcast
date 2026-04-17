import { useState } from "react";
import {
  Table,
  Button,
  Space,
  Tag,
  Popconfirm,
  message,
  Badge,
} from "antd";
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  HistoryOutlined,
} from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import { usePermission } from "@/hooks/usePermission";
import { useThemeTokens } from "@/hooks/useThemeTokens";
import { useEntityHistory } from "@/hooks/useEntityHistory";
import { VersionHistoryDrawer } from "@/components/common/VersionHistory";
import {
  useQualityEvents,
  useCreateQualityEvent,
  useUpdateQualityEvent,
  useDeleteQualityEvent,
} from "../api/useQualityEvents";
import { QualityEventModal } from "./QualityEventModal";
import { QualityEventSummaryCard } from "./QualityEventSummaryCard";
import type { QualityEventRead } from "@/api/generated";
import type { CostElementRead } from "@/api/generated";

interface QualityEventsTabProps {
  costElement: CostElementRead;
}

export const QualityEventsTab = ({ costElement }: QualityEventsTabProps) => {
  const { spacing, colors, borderRadius, typography } = useThemeTokens();
  const { can } = usePermission();

  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(10);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingEvent, setEditingEvent] = useState<QualityEventRead | null>(null);
  const [historyDrawerOpen, setHistoryDrawerOpen] = useState(false);
  const [historyEventId, setHistoryEventId] = useState<string | null>(null);

  // Query quality events
  const { data: qualityEventsData, isLoading } = useQualityEvents({
    cost_element_id: costElement.cost_element_id,
    page,
    perPage,
  });

  const qualityEvents = qualityEventsData?.items || [];
  const total = qualityEventsData?.total || 0;

  // Mutations
  const createMutation = useCreateQualityEvent();
  const updateMutation = useUpdateQualityEvent();
  const deleteMutation = useDeleteQualityEvent();

  // History query
  const { data: historyData, isLoading: historyLoading } = useEntityHistory({
    resource: "quality-events",
    entityId: historyEventId,
    fetchFn: async (id) => {
      const { QualityEventsService } = await import("@/api/generated");
      return QualityEventsService.getQualityEventHistory(id);
    },
    enabled: historyDrawerOpen && !!historyEventId,
  });

  const handleCreate = () => {
    setEditingEvent(null);
    setModalOpen(true);
  };

  const handleEdit = (event: QualityEventRead) => {
    setEditingEvent(event);
    setModalOpen(true);
  };

  const handleDelete = async (event: QualityEventRead) => {
    try {
      await deleteMutation.mutateAsync({
        id: event.quality_event_id,
        costElementId: costElement.cost_element_id,
      });
      message.success("Quality event deleted successfully");
    } catch (error) {
      console.error("Delete error:", error);
    }
  };

  const handleModalOk = async (values: unknown) => {
    try {
      if (editingEvent) {
        await updateMutation.mutateAsync({
          id: editingEvent.quality_event_id,
          data: values as never,
        });
      } else {
        await createMutation.mutateAsync(values as never);
      }
      setModalOpen(false);
      setEditingEvent(null);
    } catch (error) {
      console.error("Save error:", error);
    }
  };

  const handleViewHistory = (event: QualityEventRead) => {
    setHistoryEventId(event.quality_event_id);
    setHistoryDrawerOpen(true);
  };

  const getSeverityColor = (severity?: string | null) => {
    switch (severity) {
      case "critical":
        return "error";
      case "high":
        return "warning";
      case "medium":
        return "processing";
      case "low":
        return "success";
      default:
        return "default";
    }
  };

  const getEventTypeColor = (type?: string | null) => {
    switch (type) {
      case "defect":
        return "error";
      case "rework":
        return "warning";
      case "scrap":
        return "default";
      case "warranty":
        return "processing";
      default:
        return "default";
    }
  };

  const columns: ColumnsType<QualityEventRead> = [
    {
      title: "Date",
      dataIndex: "event_date_formatted",
      key: "event_date",
      width: 150,
      render: (dateFormatted) => dateFormatted?.formatted || "-",
    },
    {
      title: "Event Type",
      dataIndex: "event_type",
      key: "event_type",
      width: 120,
      render: (type) => (
        <Tag color={getEventTypeColor(type)}>
          {type?.toUpperCase() || "OTHER"}
        </Tag>
      ),
    },
    {
      title: "Severity",
      dataIndex: "severity",
      key: "severity",
      width: 100,
      render: (severity) => (
        <Badge
          status={getSeverityColor(severity) as never}
          text={severity?.toUpperCase() || "UNKNOWN"}
        />
      ),
      filters: [
        { text: "Critical", value: "critical" },
        { text: "High", value: "high" },
        { text: "Medium", value: "medium" },
        { text: "Low", value: "low" },
      ],
    },
    {
      title: "Description",
      dataIndex: "description",
      key: "description",
      ellipsis: true,
      render: (text) => (
        <span style={{ fontSize: typography.sizes.sm }}>{text}</span>
      ),
    },
    {
      title: "Cost Impact",
      dataIndex: "cost_impact",
      key: "cost_impact",
      width: 120,
      render: (cost) => (
        <span
          style={{
            fontWeight: typography.weights.medium,
            color: colors.text,
          }}
        >
          €{Number(cost || 0).toFixed(2)}
        </span>
      ),
      sorter: (a, b) =>
        Number(a.cost_impact || 0) - Number(b.cost_impact || 0),
    },
    {
      title: "Actions",
      key: "actions",
      width: 120,
      fixed: "right",
      render: (_, record) => (
        <Space size="small">
          {can("quality-event-write") && (
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
          {can("quality-event-delete") && (
            <Popconfirm
              title="Delete Quality Event"
              description="Are you sure you want to delete this quality event?"
              onConfirm={() => handleDelete(record)}
              okText="Delete"
              okButtonProps={{ danger: true }}
              cancelText="Cancel"
            >
              <Button
                type="text"
                icon={<DeleteOutlined />}
                danger
              />
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ];

  return (
    <div>
      {/* Summary Card */}
      <QualityEventSummaryCard
        qualityEvents={qualityEvents}
        loading={isLoading}
      />

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
          Quality Events
        </h2>
        {can("quality-event-write") && (
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={handleCreate}
          >
            Add Quality Event
          </Button>
        )}
      </div>

      {/* Table */}
      <Table
        columns={columns}
        dataSource={qualityEvents}
        rowKey="quality_event_id"
        loading={isLoading}
        pagination={{
          current: page,
          pageSize: perPage,
          total,
          showSizeChanger: true,
          showTotal: (total) => `Total ${total} events`,
          onChange: (newPage, newPerPage) => {
            setPage(newPage);
            setPerPage(newPerPage || 10);
          },
        }}
        scroll={{ x: 800 }}
        style={{
          borderRadius: borderRadius.lg,
        }}
      />

      {/* Create/Edit Modal */}
      <QualityEventModal
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
        costElementId={costElement.cost_element_id}
      />

      {/* History Drawer */}
      <VersionHistoryDrawer
        open={historyDrawerOpen}
        onClose={() => {
          setHistoryDrawerOpen(false);
          setHistoryEventId(null);
        }}
        title="Quality Event History"
        history={historyData || []}
        loading={historyLoading}
        renderVersion={(version: QualityEventRead) => (
          <div>
            <div
              style={{
                marginBottom: spacing.sm,
                paddingBottom: spacing.sm,
                borderBottom: `1px solid ${colors.border}`,
              }}
            >
              <div style={{ fontWeight: typography.weights.medium, marginBottom: spacing.xs }}>
                {version.event_type?.toUpperCase()} - {version.severity?.toUpperCase()}
              </div>
              <div style={{ fontSize: typography.sizes.sm, color: colors.textSecondary }}>
                {version.event_date_formatted?.formatted}
              </div>
            </div>
            <div>
              <div style={{ marginBottom: spacing.xs }}>
                <strong>Description:</strong>
              </div>
              <div style={{ marginBottom: spacing.sm, fontSize: typography.sizes.sm }}>
                {version.description}
              </div>
              {version.root_cause && (
                <>
                  <div style={{ marginBottom: spacing.xs }}>
                    <strong>Root Cause:</strong>
                  </div>
                  <div style={{ marginBottom: spacing.sm, fontSize: typography.sizes.sm }}>
                    {version.root_cause}
                  </div>
                </>
              )}
              {version.resolution_notes && (
                <>
                  <div style={{ marginBottom: spacing.xs }}>
                    <strong>Resolution:</strong>
                  </div>
                  <div style={{ fontSize: typography.sizes.sm }}>
                    {version.resolution_notes}
                  </div>
                </>
              )}
              <div style={{ marginTop: spacing.sm, fontWeight: typography.weights.medium }}>
                Cost Impact: €{Number(version.cost_impact || 0).toFixed(2)}
              </div>
            </div>
          </div>
        )}
      />
    </div>
  );
};
