import { useState } from "react";
import { Button, Table, Card, Space, Tooltip, Modal, Tag } from "antd";
import { PlusOutlined, EditOutlined, DeleteOutlined, HistoryOutlined } from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import { useQueryClient } from "@tanstack/react-query";
import type { CostElementRead, ForecastRead } from "@/api/generated";
import {
  useForecasts,
  useCreateForecast,
  useUpdateForecast,
  useDeleteForecast,
} from "@/features/forecasts/api";
import { ForecastModal, ForecastHistoryView } from "@/features/forecasts/components";
import { useTimeMachineParams } from "@/contexts/TimeMachineContext";

interface ForecastsTabProps {
  costElement: CostElementRead;
}

interface ForecastWithComparison extends ForecastRead {
  comparison?: {
    bac_amount: string;
    eac_amount: string;
    ac_amount: string;
    vac_amount: string;
    etc_amount: string;
  };
}

export const ForecastsTab = ({ costElement }: ForecastsTabProps) => {
  // Extract time machine parameters
  // Note: asOf and mode are available for future time travel features
  const { branch: tmBranch } = useTimeMachineParams();
  const queryClient = useQueryClient();
  const currentBranch = tmBranch || costElement.branch || "main";

  // State for modals
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [editingForecast, setEditingForecast] = useState<ForecastRead | null>(null);
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);
  const [showHistoryView, setShowHistoryView] = useState(false);

  // Fetch forecasts for this cost element
  const { data: forecastsData, isLoading } = useForecasts({
    cost_element_id: costElement.cost_element_id,
    branch: currentBranch,
    pagination: { current: 1, pageSize: 100 },
  });

  // Get comparison data for each forecast
  const forecastsWithComparison: ForecastWithComparison[] =
    forecastsData?.items?.map((forecast: ForecastRead) => ({
      ...forecast,
      comparison: undefined, // Will be fetched on demand
    })) || [];

  // Mutations
  const createMutation = useCreateForecast({
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["forecasts"] });
      setIsCreateModalOpen(false);
    },
  });

  const updateMutation = useUpdateForecast({
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["forecasts"] });
      setEditingForecast(null);
    },
  });

  const deleteMutation = useDeleteForecast({
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["forecasts"] });
      setDeleteConfirmId(null);
    },
  });

  const handleCreate = (values: any) => {
    createMutation.mutate({
      ...values,
      cost_element_id: costElement.cost_element_id,
      branch: currentBranch,
    });
  };

  const handleUpdate = (values: any) => {
    if (!editingForecast) return;
    updateMutation.mutate({
      id: editingForecast.forecast_id,
      data: {
        ...values,
        branch: currentBranch,
      },
    });
  };

  const handleDelete = (forecast: ForecastRead) => {
    const compositeId = `${forecast.forecast_id}:::${forecast.branch}`;
    deleteMutation.mutate(compositeId);
  };

  // Calculate EVM metrics for display
  const getEVMMetrics = (forecast: ForecastRead) => {
    const bac = Number(costElement.budget_amount);
    const eac = Number(forecast.eac_amount);
    const vac = bac - eac; // VAC = BAC - EAC

    const vacStatus = vac > 0 ? "success" : vac < 0 ? "error" : "default";
    const vacText = vac > 0 ? "Under Budget" : vac < 0 ? "Over Budget" : "On Budget";

    return { vac, vacStatus, vacText, bac, eac };
  };

  const columns: ColumnsType<ForecastWithComparison> = [
    {
      title: "EAC (Estimate at Complete)",
      dataIndex: "eac_amount",
      key: "eac_amount",
      render: (eac: string, record: ForecastWithComparison) => {
        const { vac, vacStatus, vacText } = getEVMMetrics(record);
        return (
          <div>
            <div style={{ fontWeight: "bold" }}>€{Number(eac).toLocaleString()}</div>
            <Tag color={vacStatus} style={{ marginTop: 4 }}>
              {vacText} (VAC: €{vac.toLocaleString()})
            </Tag>
          </div>
        );
      },
    },
    {
      title: "Basis of Estimate",
      dataIndex: "basis_of_estimate",
      key: "basis_of_estimate",
      ellipsis: true,
      render: (text: string) => (
        <Tooltip title={text}>
          <span>{text?.substring(0, 50)}{text?.length > 50 ? "..." : ""}</span>
        </Tooltip>
      ),
    },
    {
      title: "Branch",
      dataIndex: "branch",
      key: "branch",
      width: 120,
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
      title: "Created",
      dataIndex: "created_at",
      key: "created_at",
      width: 180,
      render: (date: string) => (date ? new Date(date).toLocaleString() : "-"),
    },
    {
      title: "Actions",
      key: "actions",
      width: 150,
      render: (_, record: ForecastWithComparison) => (
        <Space>
          <Tooltip title="Edit Forecast">
            <Button
              type="text"
              icon={<EditOutlined />}
              onClick={() => setEditingForecast(record)}
            />
          </Tooltip>
          <Tooltip title="View History">
            <Button
              type="text"
              icon={<HistoryOutlined />}
              onClick={() => setShowHistoryView(true)}
            />
          </Tooltip>
          <Tooltip title="Delete Forecast">
            <Button
              type="text"
              danger
              icon={<DeleteOutlined />}
              onClick={() => setDeleteConfirmId(record.forecast_id)}
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
        title="Forecasts"
        extra={
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => setIsCreateModalOpen(true)}
          >
            Create Forecast
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
            <strong>EVM Metrics:</strong>
          </div>
          <div style={{ fontSize: "12px", color: "#666" }}>
            • <strong>BAC:</strong> Budget at Complete (€{Number(costElement.budget_amount).toLocaleString()})
            <br />
            • <strong>EAC:</strong> Estimate at Complete (Projected total cost)
            <br />
            • <strong>VAC:</strong> Variance at Complete = BAC - EAC
            <br />
            • <strong>ETC:</strong> Estimate to Complete = EAC - AC
          </div>
        </div>

        {/* Forecasts Table */}
        <Table
          columns={columns}
          dataSource={forecastsWithComparison}
          rowKey="forecast_id"
          loading={isLoading}
          pagination={false}
          locale={{
            emptyText: (
              <div style={{ padding: "24px", textAlign: "center" }}>
                <p style={{ color: "#999" }}>
                  No forecasts found for this cost element.
                </p>
                <Button
                  type="link"
                  onClick={() => setIsCreateModalOpen(true)}
                >
                  Create the first forecast
                </Button>
              </div>
            ),
          }}
        />
      </Card>

      {/* Create Modal */}
      <ForecastModal
        open={isCreateModalOpen}
        onCancel={() => setIsCreateModalOpen(false)}
        onOk={handleCreate}
        confirmLoading={createMutation.isPending}
        currentBranch={currentBranch}
        costElementId={costElement.cost_element_id}
        costElementName={`${costElement.code} - ${costElement.name}`}
        budgetAmount={Number(costElement.budget_amount)}
      />

      {/* Edit Modal */}
      <ForecastModal
        open={!!editingForecast}
        onCancel={() => setEditingForecast(null)}
        onOk={handleUpdate}
        confirmLoading={updateMutation.isPending}
        initialValues={editingForecast || undefined}
        currentBranch={currentBranch}
        costElementId={costElement.cost_element_id}
        costElementName={`${costElement.code} - ${costElement.name}`}
        budgetAmount={Number(costElement.budget_amount)}
      />

      {/* Delete Confirmation Modal */}
      <Modal
        title="Delete Forecast"
        open={!!deleteConfirmId}
        onOk={() => {
          const forecast = forecastsData?.items?.find(
            (f: ForecastRead) => f.forecast_id === deleteConfirmId
          );
          if (forecast) handleDelete(forecast);
        }}
        onCancel={() => setDeleteConfirmId(null)}
        confirmLoading={deleteMutation.isPending}
        okText="Delete"
        okButtonProps={{ danger: true }}
      >
        <p>Are you sure you want to delete this forecast?</p>
        <p style={{ color: "#999", fontSize: "12px" }}>
          This action can be recovered through time travel if needed.
        </p>
      </Modal>

      {/* Forecast History View */}
      <Modal
        title="Forecast History & Time Travel"
        open={showHistoryView}
        onCancel={() => setShowHistoryView(false)}
        footer={null}
        width={1000}
      >
        <ForecastHistoryView
          costElementId={costElement.cost_element_id}
          currentBranch={currentBranch}
        />
      </Modal>
    </div>
  );
};
