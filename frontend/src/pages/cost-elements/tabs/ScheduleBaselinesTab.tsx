import { useState } from "react";
import { Button, Card, Space, Tooltip, Modal, Tag, theme, Empty, Spin } from "antd";
import { PlusOutlined, EditOutlined, DeleteOutlined, HistoryOutlined, CalendarOutlined, ReloadOutlined } from "@ant-design/icons";
import { useQueryClient } from "@tanstack/react-query";
import type { CostElementRead } from "@/api/generated";
import {
  useCostElementScheduleBaseline,
  useCreateCostElementScheduleBaseline,
  useUpdateCostElementScheduleBaseline,
  useDeleteCostElementScheduleBaseline,
} from "@/features/schedule-baselines/api";
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
  const { token } = theme.useToken();
  const queryClient = useQueryClient();

  // State for modals
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [editingBaseline, setEditingBaseline] = useState<ScheduleBaselineRead | null>(null);
  const [showHistory, setShowHistory] = useState(false);

  const { modal } = Modal;

  // Fetch the single schedule baseline for this cost element (1:1 relationship)
  const {
    data: baseline,
    isLoading,
    isError,
    refetch,
  } = useCostElementScheduleBaseline(
    costElement.cost_element_id,
    costElement.branch || "main"
  );

  useCreateCostElementScheduleBaseline({
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["cost_element_schedule_baseline"] });
      refetch();
    },
  });

  useUpdateCostElementScheduleBaseline({
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["cost_element_schedule_baseline"] });
      refetch();
    },
  });

  const { mutate: deleteBaseline, isPending: isDeleting } = useDeleteCostElementScheduleBaseline({
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["cost_element_schedule_baseline"] });
      refetch();
    },
  });

  const handleEdit = () => {
    if (baseline) {
      setEditingBaseline(baseline);
      setIsCreateModalOpen(true);
    }
  };

  const handleDelete = () => {
    if (baseline) {
      modal.confirm({
        title: "Delete Schedule Baseline",
        content: (
          <div>
            <p>
              Are you sure you want to delete schedule baseline <strong>"{baseline.name}"</strong>?
            </p>
            <p style={{ color: token.colorError, marginTop: 8 }}>
              ⚠️ This action cannot be undone. The cost element will have no schedule baseline after deletion.
            </p>
          </div>
        ),
        okText: "Yes, Delete",
        okType: "danger",
        onOk: () => {
          deleteBaseline({
            costElementId: costElement.cost_element_id,
            baselineId: baseline.schedule_baseline_id,
          });
        },
      });
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  };

  const handleCreateNew = () => {
    setEditingBaseline(null);
    setIsCreateModalOpen(true);
  };

  const handleModalClose = () => {
    setIsCreateModalOpen(false);
    setEditingBaseline(null);
  };

  const handleModalSuccess = () => {
    refetch();
    setIsCreateModalOpen(false);
    setEditingBaseline(null);
  };

  // Loading state
  if (isLoading) {
    return (
      <Card title="Schedule Baseline">
        <div style={{ textAlign: "center", padding: "40px" }}>
          <Spin size="large" />
          <p style={{ marginTop: 16, color: token.colorTextSecondary }}>
            Loading schedule baseline...
          </p>
        </div>
      </Card>
    );
  }

  // Error state
  if (isError) {
    return (
      <Card
        title="Schedule Baseline"
        extra={
          <Button icon={<ReloadOutlined />} onClick={() => refetch()}>
            Retry
          </Button>
        }
      >
        <Empty
          description={
            <div>
              <p>Failed to load schedule baseline</p>
              <Button type="primary" onClick={() => refetch()}>
                Try Again
              </Button>
            </div>
          }
          image={Empty.PRESENTED_IMAGE_SIMPLE}
        />
      </Card>
    );
  }

  // No baseline state (404 from API)
  if (!baseline) {
    return (
      <Card title="Schedule Baseline">
        {/* EVM Info */}
        <div
          style={{
            backgroundColor: token.colorFillSecondary,
            padding: "12px",
            borderRadius: "4px",
            marginBottom: 16,
          }}
        >
          <div style={{ fontSize: "12px", color: token.colorTextSecondary, marginBottom: "8px" }}>
            <strong>Planned Value (PV) Calculation:</strong>
          </div>
          <div style={{ fontSize: "12px", color: token.colorTextSecondary }}>
            • <strong>PV:</strong> Planned Value = BAC × Progress
            <br />
            • <strong>BAC:</strong> Budget at Complete (€{Number(costElement.budget_amount).toLocaleString()})
            <br />
            • <strong>Progress:</strong> Determined by progression type (Linear, Gaussian S-Curve, or Logarithmic)
            <br />• <strong>1:1 Relationship:</strong> Each cost element has exactly one schedule baseline
          </div>
        </div>

        <Empty
          description={
            <div>
              <CalendarOutlined style={{ fontSize: "48px", color: token.colorTextTertiary }} />
              <p style={{ color: token.colorTextTertiary, marginTop: 16, fontSize: 16 }}>
                No schedule baseline found for this cost element.
              </p>
              <p style={{ color: token.colorTextSecondary, marginBottom: 16 }}>
                Create a schedule baseline to enable Planned Value (PV) calculations and EVM tracking.
              </p>
              <Button type="primary" icon={<PlusOutlined />} onClick={handleCreateNew}>
                Create Schedule Baseline
              </Button>
            </div>
          }
        />

        {/* Create Modal */}
        <ScheduleBaselineModal
          visible={isCreateModalOpen}
          onClose={handleModalClose}
          onSuccess={handleModalSuccess}
          costElementId={costElement.cost_element_id}
          baseline={editingBaseline || undefined}
        />
      </Card>
    );
  }

  // Display single baseline
  return (
    <div>
      {/* Header */}
      <Card
        title="Schedule Baseline"
        extra={
          <Space>
            <Tooltip title="View History">
              <Button
                type="text"
                icon={<HistoryOutlined />}
                onClick={() => setShowHistory(true)}
              />
            </Tooltip>
            <Tooltip title="Edit Baseline">
              <Button type="text" icon={<EditOutlined />} onClick={handleEdit} />
            </Tooltip>
            <Tooltip title="Delete Baseline">
              <Button
                type="text"
                danger
                icon={<DeleteOutlined />}
                onClick={handleDelete}
                loading={isDeleting}
              />
            </Tooltip>
          </Space>
        }
      >
        {/* EVM Info */}
        <div
          style={{
            backgroundColor: token.colorFillSecondary,
            padding: "12px",
            borderRadius: "4px",
            marginBottom: 16,
          }}
        >
          <div style={{ fontSize: "12px", color: token.colorTextSecondary, marginBottom: "8px" }}>
            <strong>Planned Value (PV) Calculation:</strong>
          </div>
          <div style={{ fontSize: "12px", color: token.colorTextSecondary }}>
            • <strong>PV:</strong> Planned Value = BAC × Progress
            <br />
            • <strong>BAC:</strong> Budget at Complete (€{Number(costElement.budget_amount).toLocaleString()})
            <br />• <strong>Progress:</strong> Determined by progression type (Linear, Gaussian S-Curve, or Logarithmic)
            <br />• <strong>1:1 Relationship:</strong> Each cost element has exactly one schedule baseline
          </div>
        </div>

        {/* Single Baseline Display */}
        <div
          style={{
            padding: "16px",
            backgroundColor: token.colorBgContainer,
            border: `1px solid ${token.colorBorder}`,
            borderRadius: "4px",
          }}
        >
          <div style={{ marginBottom: 12 }}>
            <label style={{ color: token.colorTextSecondary, fontSize: 12, display: "block", marginBottom: 4 }}>
              Name
            </label>
            <span style={{ fontSize: 16, fontWeight: 500 }}>{baseline.name}</span>
          </div>

          <div style={{ marginBottom: 12 }}>
            <label style={{ color: token.colorTextSecondary, fontSize: 12, display: "block", marginBottom: 4 }}>
              Progression Type
            </label>
            <Tag color={PROGRESSION_COLORS[baseline.progression_type]}>
              {PROGRESSION_LABELS[baseline.progression_type] || baseline.progression_type}
            </Tag>
          </div>

          <div style={{ display: "flex", gap: 24 }}>
            <div style={{ flex: 1 }}>
              <label style={{ color: token.colorTextSecondary, fontSize: 12, display: "block", marginBottom: 4 }}>
                Start Date
              </label>
              <span>{formatDate(baseline.start_date)}</span>
            </div>
            <div style={{ flex: 1 }}>
              <label style={{ color: token.colorTextSecondary, fontSize: 12, display: "block", marginBottom: 4 }}>
                End Date
              </label>
              <span>{formatDate(baseline.end_date)}</span>
            </div>
          </div>

          {baseline.description && (
            <div style={{ marginTop: 12 }}>
              <label style={{ color: token.colorTextSecondary, fontSize: 12, display: "block", marginBottom: 4 }}>
                Description
              </label>
              <span style={{ color: token.colorText }}>{baseline.description}</span>
            </div>
          )}

          <div style={{ marginTop: 12 }}>
            <label style={{ color: token.colorTextSecondary, fontSize: 12, display: "block", marginBottom: 4 }}>
              Branch
            </label>
            <Tag color={baseline.branch === "main" ? "blue" : "orange"}>
              {baseline.branch === "main" ? "Main" : baseline.branch}
            </Tag>
          </div>
        </div>
      </Card>

      {/* Create/Edit Modal */}
      <ScheduleBaselineModal
        visible={isCreateModalOpen}
        onClose={handleModalClose}
        onSuccess={handleModalSuccess}
        costElementId={costElement.cost_element_id}
        baseline={editingBaseline || undefined}
      />

      {/* Version History Drawer */}
      <VersionHistoryDrawer
        open={showHistory}
        onClose={() => setShowHistory(false)}
        versions={[
          {
            id: "v1",
            valid_from: baseline.start_date,
            transaction_time: new Date().toISOString(),
            changed_by: "System",
          },
        ]}
        entityName={`Schedule Baseline: ${baseline.name}`}
        isLoading={false}
      />
    </div>
  );
};
