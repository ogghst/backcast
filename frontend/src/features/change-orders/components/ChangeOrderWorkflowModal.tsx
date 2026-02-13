import { Modal, Tabs, Spin, Alert, Space, Button } from "antd";
import { useState, useCallback } from "react";
import { ReloadOutlined } from "@ant-design/icons";
import { useChangeOrder } from "../api/useChangeOrders";
import {
  WorkflowStepper,
  ChangeOrderDetailsSection,
  StepDetailsSection,
  WorkflowButtons,
  BranchLockIndicator,
} from "./index";

interface ChangeOrderWorkflowModalProps {
  /** Whether the modal is visible */
  open: boolean;
  /** Callback when modal is closed */
  onCancel: () => void;
  /** Change Order ID (UUID) */
  changeOrderId: string;
}

/**
 * ChangeOrderWorkflowModal - Unified modal for Change Order workflow management.
 *
 * This modal provides a comprehensive view of a Change Order with three sections:
 * 1. Details Tab: CO metadata, branch lock indicator
 * 2. Workflow Tab: Workflow stepper + action buttons
 * 3. Activity Tab: Step details and workflow guidance
 *
 * The modal opens on clicking a Change Order in the list (not a separate page).
 */
export function ChangeOrderWorkflowModal({
  open,
  onCancel,
  changeOrderId,
}: ChangeOrderWorkflowModalProps) {
  const [activeTab, setActiveTab] = useState("workflow");

  // Fetch Change Order data
  const {
    data: changeOrder,
    isLoading,
    error,
    refetch,
  } = useChangeOrder(changeOrderId, {
    enabled: open && !!changeOrderId,
  });

  // Handle refresh action
  const handleRefresh = useCallback(() => {
    refetch();
  }, [refetch]);

  const modalWidth = 700;

  return (
    <Modal
      title={
        <Space>
          <span>Change Order: {changeOrder?.code || "Loading..."}</span>
          {changeOrder?.branch_locked && (
            <BranchLockIndicator locked text="Branch Locked" />
          )}
        </Space>
      }
      open={open}
      onCancel={onCancel}
      width={modalWidth}
      footer={null}
      destroyOnClose
    >
      {isLoading ? (
        <div style={{ textAlign: "center", padding: "40px 0" }}>
          <Spin size="large" />
        </div>
      ) : error ? (
        <Alert
          type="error"
          message="Error loading change order"
          description={error.message}
          showIcon
          action={
            <Button
              icon={<ReloadOutlined />}
              onClick={handleRefresh}
              size="small"
            >
              Retry
            </Button>
          }
        />
      ) : !changeOrder ? (
        <Alert
          type="warning"
          message="Change Order not found"
          description="The requested change order could not be loaded."
        />
      ) : (
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={[
            {
              key: "workflow",
              label: "Workflow",
              children: (
                <div style={{ minHeight: 300 }}>
                  {/* Workflow stepper */}
                  <WorkflowStepper status={changeOrder.status || "Draft"} />

                  {/* Action buttons */}
                  <div style={{ marginBottom: 24 }}>
                    <WorkflowButtons changeOrder={changeOrder} />
                  </div>

                  {/* Current status info */}
                  <StepDetailsSection
                    status={changeOrder.status || "Draft"}
                    availableTransitions={changeOrder.available_transitions || []}
                    branchLocked={changeOrder.branch_locked || false}
                  />
                </div>
              ),
            },
            {
              key: "details",
              label: "Details",
              children: (
                <div style={{ minHeight: 300 }}>
                  <ChangeOrderDetailsSection changeOrder={changeOrder} />
                </div>
              ),
            },
          ]}
        />
      )}
    </Modal>
  );
}
