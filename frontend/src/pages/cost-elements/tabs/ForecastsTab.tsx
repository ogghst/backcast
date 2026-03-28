import { useState } from "react";
import { Button, Card, Table, Space, Tooltip, Modal, Tag, theme, Alert, Grid } from "antd";
import { PlusOutlined, EditOutlined, DeleteOutlined, HistoryOutlined, InfoCircleOutlined } from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import { useQueryClient } from "@tanstack/react-query";
import type { CostElementRead } from "@/api/generated";
import {
  useCostElementForecast,
  useUpdateCostElementForecast,
  useDeleteCostElementForecast,
} from "@/features/cost-elements/api/useCostElements";
import { ForecastModal, ForecastHistoryView } from "@/features/forecasts/components";
import { useTimeMachineParams } from "@/contexts/TimeMachineContext";
import { queryKeys } from "@/api/queryKeys";

interface ForecastsTabProps {
  costElement: CostElementRead;
}

interface ForecastWithComparison {
  forecast_id: string;
  eac_amount: string | number;
  basis_of_estimate: string;
  branch: string;
  created_at: string;
  updated_at: string;
  approved_date?: string;
  approved_by?: string;
  comparison?: {
    bac_amount: string;
    eac_amount: string;
    ac_amount: string;
    vac_amount: string;
    etc_amount: string;
  };
}

export const ForecastsTab = ({ costElement }: ForecastsTabProps) => {
  const { token } = theme.useToken();
  const { branch: tmBranch, asOf } = useTimeMachineParams();
  const queryClient = useQueryClient();
  const currentBranch = tmBranch || costElement.branch || "main";
  const screens = Grid.useBreakpoint();
  const isMobile = !screens.md;

  // State for modals
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [editingForecast, setEditingForecast] = useState<ForecastWithComparison | null>(null);
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [showHistoryView, setShowHistoryView] = useState(false);

  // Fetch the single forecast for this cost element (1:1 relationship)
  const { data: forecastData, isLoading, isError } = useCostElementForecast(
    costElement.cost_element_id,
    currentBranch
  );

  const forecast = forecastData as ForecastWithComparison | null;

  // Mutations
  const updateMutation = useUpdateCostElementForecast({
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.forecasts.byCostElement(costElement.cost_element_id, currentBranch, { asOf })
      });
      setEditingForecast(null);
    },
  });

  const deleteMutation = useDeleteCostElementForecast({
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.forecasts.byCostElement(costElement.cost_element_id, currentBranch, { asOf })
      });
      setDeleteConfirmOpen(false);
    },
  });

  const handleCreate = (values: Record<string, unknown>) => {
    // For 1:1 relationship, we use the update endpoint which creates if doesn't exist
    updateMutation.mutate({
      costElementId: costElement.cost_element_id,
      data: values,
      branch: currentBranch,
    });
    setIsCreateModalOpen(false);
  };

  const handleUpdate = (values: Record<string, unknown>) => {
    if (!editingForecast) return;
    updateMutation.mutate({
      costElementId: costElement.cost_element_id,
      data: values,
      branch: currentBranch,
    });
  };

  const handleDelete = () => {
    deleteMutation.mutate({
      costElementId: costElement.cost_element_id,
      branch: currentBranch,
    });
  };

  // Calculate EVM metrics for display
  const getEVMMetrics = () => {
    if (!forecast) return null;

    const bac = Number(costElement.budget_amount);
    const eac = Number(forecast.eac_amount);
    const vac = bac - eac; // VAC = BAC - EAC

    const vacStatus = vac > 0 ? "success" : vac < 0 ? "error" : "default";
    const vacText = vac > 0 ? "Under Budget" : vac < 0 ? "Over Budget" : "On Budget";

    return { vac, vacStatus, vacText, bac, eac };
  };

  const evmMetrics = getEVMMetrics();

  // Responsive columns - hide less important columns on mobile
  const columns: ColumnsType<ForecastWithComparison> = [
    {
      title: "EAC (Estimate at Complete)",
      dataIndex: "eac_amount",
      key: "eac_amount",
      render: (eac: string | number) => {
        if (!evmMetrics) return null;
        const { vac, vacStatus, vacText } = evmMetrics;
        return (
          <div>
            <div style={{ fontWeight: "bold" }}>
              €{Number(eac).toLocaleString()}
            </div>
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
      responsive: ["md"],
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
      responsive: ["lg"],
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
      responsive: ["lg"],
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
              onClick={() => setDeleteConfirmOpen(true)}
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
        title="Forecast"
        extra={
          !forecast && (
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => setIsCreateModalOpen(true)}
            >
              Create Forecast
            </Button>
          )
        }
      >
        {/* Info Alert about 1:1 Relationship */}
        <Alert
          message="One Forecast Per Cost Element"
          description="Each cost element can have only one forecast. Updating or creating a new forecast will replace any existing forecast for this cost element in the current branch."
          type="info"
          showIcon
          icon={<InfoCircleOutlined />}
          style={{ marginBottom: 16 }}
        />

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
            <strong>EVM Metrics:</strong>
          </div>
          <div style={{ fontSize: "12px", color: token.colorTextSecondary }}>
            • <strong>BAC:</strong> Budget at Complete (€{Number(costElement.budget_amount).toLocaleString()})
            <br />
            • <strong>EAC:</strong> Estimate at Complete (Projected total cost)
            <br />
            • <strong>VAC:</strong> Variance at Complete = BAC - EAC
            <br />
            • <strong>ETC:</strong> Estimate to Complete = EAC - AC
          </div>
        </div>

        {/* Forecast Table or Empty State */}
        {forecast ? (
          <Table
            columns={columns}
            dataSource={[forecast]}
            rowKey="forecast_id"
            loading={isLoading}
            pagination={false}
            scroll={{ x: isMobile ? "max-content" : undefined }}
            size={isMobile ? "small" : "middle"}
          />
        ) : (
          <div style={{ padding: "24px", textAlign: "center" }}>
            {isError ? (
              <p style={{ color: "#ff4d4f" }}>
                Error loading forecast. Please try again.
              </p>
            ) : isLoading ? (
              <p style={{ color: "#999" }}>Loading forecast...</p>
            ) : (
              <>
                <p style={{ color: "#999" }}>
                  No forecast found for this cost element.
                </p>
                <Button
                  type="primary"
                  icon={<PlusOutlined />}
                  onClick={() => setIsCreateModalOpen(true)}
                >
                  Create Forecast
                </Button>
              </>
            )}
          </div>
        )}
      </Card>

      {/* Create Modal */}
      <ForecastModal
        open={isCreateModalOpen}
        onCancel={() => setIsCreateModalOpen(false)}
        onOk={handleCreate}
        confirmLoading={updateMutation.isPending}
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
        open={deleteConfirmOpen}
        onOk={handleDelete}
        onCancel={() => setDeleteConfirmOpen(false)}
        confirmLoading={deleteMutation.isPending}
        okText="Delete"
        okButtonProps={{ danger: true }}
      >
        <p>Are you sure you want to delete this forecast?</p>
        <p style={{ color: "#999", fontSize: "12px" }}>
          The cost element will remain without a forecast. You can create a new forecast later.
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
