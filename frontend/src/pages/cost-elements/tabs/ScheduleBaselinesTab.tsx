import { useState } from "react";
import { Button, Table, Card, Space, Tooltip, Modal, Tag } from "antd";
import { PlusOutlined, EditOutlined, DeleteOutlined, HistoryOutlined, CalendarOutlined } from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import { useQueryClient } from "@tanstack/react-query";
import type { CostElementRead } from "@/api/generated";
import {
  useScheduleBaselines,
  useDeleteScheduleBaseline,
  useScheduleBaselineHistory,
} from "@/features/schedule-baselines/api/useScheduleBaselines";
import { ScheduleBaselineModal } from "@/features/schedule-baselines/components/ScheduleBaselineModal";
import { VersionHistoryDrawer } from "@/components/common/VersionHistory";
import type { ScheduleBaselineRead } from "@/features/schedule-baselines/api/useScheduleBaselines";

interface ScheduleBaselinesTabProps {
  costElement: CostElementRead;
}

// Progression type tag colors
const PROGRESSION_COLORS: Record<string, string> = {
  LINEAR: "blue",
  GAUSSIAN: "green",
  LOGARITHMIC: "orange",
};

// Progression type labels
const PROGRESSION_LABELS: Record<string, string> = {
  LINEAR: "Linear",
  GAUSSIAN: "Gaussian (S-Curve)",
  LOGARITHMIC: "Logarithmic",
};

export const ScheduleBaselinesTab = ({ costElement }: ScheduleBaselinesTabProps) => {
  const queryClient = useQueryClient();

  // State for modals
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [editingBaseline, setEditingBaseline] = useState<ScheduleBaselineRead | null>(null);
  const [showHistory, setShowHistory] = useState(false);
  const [selectedBaseline, setSelectedBaseline] = useState<ScheduleBaselineRead | null>(null);

  const { modal } = Modal;

  // Fetch schedule baselines for this cost element
  const { data: baselinesData, isLoading, refetch } = useScheduleBaselines({
    cost_element_id: costElement.cost_element_id,
    pagination: { current: 1, pageSize: 100 },
  });

  const baselines = baselinesData?.items || [];

  const { mutate: deleteScheduleBaseline } = useDeleteScheduleBaseline({
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["schedule_baselines"] });
    },
  });

  const { data: history, isLoading: historyLoading } = useScheduleBaselineHistory(
    selectedBaseline?.schedule_baseline_id || "",
    !!selectedBaseline?.schedule_baseline_id && showHistory
  );

  const handleEdit = (baseline: ScheduleBaselineRead) => {
    setEditingBaseline(baseline);
    setIsCreateModalOpen(true);
  };

  const handleDelete = (baseline: ScheduleBaselineRead) => {
    modal.confirm({
      title: "Delete Schedule Baseline",
      content: `Are you sure you want to delete schedule baseline "${baseline.name}"? This action cannot be undone.`,
      okText: "Yes, Delete",
      okType: "danger",
      onOk: () => deleteScheduleBaseline({ id: baseline.schedule_baseline_id }),
    });
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  };

  const columns: ColumnsType<ScheduleBaselineRead> = [
    {
      title: "Name",
      dataIndex: "name",
      key: "name",
      render: (name: string) => <span style={{ fontWeight: 500 }}>{name}</span>,
    },
    {
      title: "Progression Type",
      dataIndex: "progression_type",
      key: "progression_type",
      width: 180,
      render: (type: string) => (
        <Tag color={PROGRESSION_COLORS[type]}>
          {PROGRESSION_LABELS[type] || type}
        </Tag>
      ),
    },
    {
      title: "Start Date",
      dataIndex: "start_date",
      key: "start_date",
      width: 140,
      render: (date: string) => formatDate(date),
    },
    {
      title: "End Date",
      dataIndex: "end_date",
      key: "end_date",
      width: 140,
      render: (date: string) => formatDate(date),
    },
    {
      title: "Branch",
      dataIndex: "branch",
      key: "branch",
      width: 100,
      render: (branch: string) => {
        const isMain = branch === "main";
        return (
          <Tag color={isMain ? "blue" : "orange"}>
            {isMain ? "Main" : branch}
          </Tag>
        );
      },
    },
    {
      title: "Actions",
      key: "actions",
      width: 150,
      render: (_, record: ScheduleBaselineRead) => (
        <Space>
          <Tooltip title="Edit Baseline">
            <Button
              type="text"
              icon={<EditOutlined />}
              onClick={() => handleEdit(record)}
            />
          </Tooltip>
          <Tooltip title="View History">
            <Button
              type="text"
              icon={<HistoryOutlined />}
              onClick={() => {
                setSelectedBaseline(record);
                setShowHistory(true);
              }}
            />
          </Tooltip>
          <Tooltip title="Delete Baseline">
            <Button
              type="text"
              danger
              icon={<DeleteOutlined />}
              onClick={() => handleDelete(record)}
            />
          </Tooltip>
        </Space>
      ),
    },
  ];

  return (
    <div>
      {/* Header */}
      <Card
        title="Schedule Baselines"
        extra={
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => {
              setEditingBaseline(null);
              setIsCreateModalOpen(true);
            }}
          >
            Create Schedule Baseline
          </Button>
        }
      >
        {/* EVM Info */}
        <div
          style={{
            backgroundColor: "#f0f0f0",
            padding: "12px",
            borderRadius: "4px",
            marginBottom: 16,
          }}
        >
          <div style={{ fontSize: "12px", color: "#666", marginBottom: "8px" }}>
            <strong>Planned Value (PV) Calculation:</strong>
          </div>
          <div style={{ fontSize: "12px", color: "#666" }}>
            • <strong>PV:</strong> Planned Value = BAC × Progress
            <br />
            • <strong>BAC:</strong> Budget at Complete (€{Number(costElement.budget_amount).toLocaleString()})
            <br />
            • <strong>Progress:</strong> Determined by progression type (Linear, Gaussian S-Curve, or Logarithmic)
            <br />
            • <strong>Progression Types:</strong> Linear (uniform), Gaussian (slow start/fast middle/tapering end), Logarithmic (front-loaded)
          </div>
        </div>

        {/* Schedule Baselines Table */}
        <Table
          columns={columns}
          dataSource={baselines}
          rowKey="schedule_baseline_id"
          loading={isLoading}
          pagination={false}
          locale={{
            emptyText: (
              <div style={{ padding: "24px", textAlign: "center" }}>
                <CalendarOutlined style={{ fontSize: "32px", color: "#ccc" }} />
                <p style={{ color: "#999", marginTop: "16px" }}>
                  No schedule baselines found for this cost element.
                </p>
                <Button
                  type="link"
                  onClick={() => {
                    setEditingBaseline(null);
                    setIsCreateModalOpen(true);
                  }}
                >
                  Create the first schedule baseline
                </Button>
              </div>
            ),
          }}
        />
      </Card>

      {/* Create/Edit Modal */}
      <ScheduleBaselineModal
        visible={isCreateModalOpen}
        onClose={() => {
          setIsCreateModalOpen(false);
          setEditingBaseline(null);
        }}
        onSuccess={() => {
          refetch();
          setIsCreateModalOpen(false);
          setEditingBaseline(null);
        }}
        costElementId={costElement.cost_element_id}
        baseline={editingBaseline || undefined}
      />

      {/* Version History Drawer */}
      <VersionHistoryDrawer
        open={showHistory}
        onClose={() => {
          setShowHistory(false);
          setSelectedBaseline(null);
        }}
        versions={(history || []).map((v, idx, arr) => {
          const item = v as ScheduleBaselineRead & {
            valid_time?: string[] | string;
            transaction_time?: string[] | string;
            created_by_name?: string;
          };
          return {
            ...item,
            id: `v${arr.length - idx}`,
            valid_from: Array.isArray(item.valid_time)
              ? item.valid_time[0]
              : (item.valid_time as string) || new Date().toISOString(),
            transaction_time: Array.isArray(item.transaction_time)
              ? item.transaction_time[0]
              : (item.transaction_time as string) || new Date().toISOString(),
            changed_by: item.created_by_name || "System",
          };
        })}
        entityName={`Schedule Baseline: ${selectedBaseline?.name || ""}`}
        isLoading={historyLoading}
      />
    </div>
  );
};