import { useState, useMemo } from "react";
import { Card, Badge, Button, Space, Alert, Tag } from "antd";
import {
  CheckCircleOutlined,
  ClockCircleOutlined,
  CloseCircleOutlined,
  SyncOutlined,
  MergeCellsOutlined,
  ToolOutlined,
} from "@ant-design/icons";
import type { ChangeOrderPublic } from "@/api/generated";
import {
  useWorkflowActions,
  isActionAvailable,
} from "../hooks/useWorkflowActions";
import { CollapsibleCard } from "@/components/common/CollapsibleCard";
import { ChangeOrderRecoveryDialog } from "./ChangeOrderRecoveryDialog";

interface ChangeOrderWorkflowSectionProps {
  changeOrder: ChangeOrderPublic | null;
  /** Callback when workflow action succeeds */
  onActionSuccess?: () => void;
  /** Whether to use CollapsibleCard wrapper */
  useCollapsibleCard?: boolean;
}

// Status badge colors
const STATUS_COLORS: Record<string, string> = {
  Draft: "default",
  "Submitted for Approval": "blue",
  "Under Review": "cyan",
  Approved: "green",
  Rejected: "red",
  Implemented: "purple",
};

// Status icons
const STATUS_ICONS: Record<string, React.ReactNode> = {
  Draft: <ClockCircleOutlined />,
  "Submitted for Approval": <SyncOutlined spin />,
  "Under Review": <SyncOutlined spin />,
  Approved: <CheckCircleOutlined />,
  Rejected: <CloseCircleOutlined />,
  Implemented: <MergeCellsOutlined />,
};

/**
 * ChangeOrderWorkflowSection - Displays workflow status and available actions.
 *
 * Shows:
 * - Current status with badge
 * - Available transitions
 * - Action buttons (Submit, Approve, Reject, Merge)
 * - Lock state warning
 * - Recovery button for stuck workflows (admin only)
 *
 * Hidden in create mode (when changeOrder is null).
 */
export function ChangeOrderWorkflowSection({
  changeOrder,
  onActionSuccess,
  useCollapsibleCard = false,
}: ChangeOrderWorkflowSectionProps): JSX.Element | null {
  // Recovery dialog state
  const [recoveryDialogVisible, setRecoveryDialogVisible] = useState(false);

  // Workflow actions - Hook must be top level
  const { submit, approve, reject, merge, isLoading } = useWorkflowActions(
    changeOrder?.change_order_id || "",
    { onSuccess: onActionSuccess },
  );

  // Extract properties for hooks (before early return)
  const status = changeOrder?.status;
  const branch_locked = changeOrder?.branch_locked;
  const available_transitions = changeOrder?.available_transitions;
  const impact_analysis_status = changeOrder?.impact_analysis_status;
  const impact_level = changeOrder?.impact_level;
  const assigned_approver_id = changeOrder?.assigned_approver_id;

  // Check if change order is stuck and needs recovery (must be before early return)
  const isStuck = useMemo(() => {
    const stuckStatuses = ["Submitted for Approval", "Under Review"];
    return (
      changeOrder &&
      stuckStatuses.includes(status || "") &&
      (!available_transitions ||
        available_transitions.length === 0 ||
        !impact_level ||
        !assigned_approver_id ||
        impact_analysis_status === "in_progress")
    );
  }, [changeOrder, status, available_transitions, impact_level, assigned_approver_id, impact_analysis_status]);

  // Hide in create mode
  if (!changeOrder) {
    return null;
  }

  // Check which actions are available
  const canSubmit = isActionAvailable("SUBMIT", available_transitions);
  const canApprove = isActionAvailable("APPROVE", available_transitions);
  const canReject = isActionAvailable("REJECT", available_transitions);
  const canMerge = isActionAvailable("MERGE", available_transitions);

  // All actions disabled when locked
  const actionsDisabled = branch_locked || isLoading;

  // Content component
  const content = (
    <>
      {/* Lock warning */}
      {branch_locked && (
        <Alert
          message="Branch Locked"
          description="This change order is currently under review. The branch is locked and no modifications are allowed."
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
        />
      )}

      {/* Current status */}
      <Space orientation="vertical" style={{ width: "100%" }} size="large">
        <div>
          <div style={{ marginBottom: 8, color: "#8c8c8c" }}>
            Current Status
          </div>
          <Badge
            color={STATUS_COLORS[status || "Draft"] ?? "default"}
            text={
              <Tag
                icon={STATUS_ICONS[status || "Draft"] ?? undefined}
                color={STATUS_COLORS[status || "Draft"] ?? "default"}
                style={{ fontSize: 14, padding: "4px 12px" }}
              >
                {status || "Draft"}
              </Tag>
            }
          />
        </div>

        {/* Available transitions */}
        {available_transitions && available_transitions.length > 0 && (
          <div>
            <div style={{ marginBottom: 8, color: "#8c8c8c" }}>
              Available Transitions
            </div>
            <Space wrap>
              {available_transitions.map((transition) => (
                <Tag key={transition} color="blue">
                  {transition}
                </Tag>
              ))}
            </Space>
          </div>
        )}

        {/* Action buttons */}
        <div>
          <div style={{ marginBottom: 8, color: "#8c8c8c" }}>Actions</div>
          <Space wrap>
            {canSubmit && (
              <Button
                type="primary"
                icon={<SyncOutlined />}
                onClick={() => submit()}
                disabled={actionsDisabled}
              >
                Submit
              </Button>
            )}
            {canApprove && (
              <Button
                type="primary"
                icon={<CheckCircleOutlined />}
                onClick={() => approve()}
                disabled={actionsDisabled}
                style={{ backgroundColor: "#52c41a", borderColor: "#52c41a" }}
              >
                Approve
              </Button>
            )}
            {canReject && (
              <Button
                danger
                icon={<CloseCircleOutlined />}
                onClick={() => reject()}
                disabled={actionsDisabled}
              >
                Reject
              </Button>
            )}
            {canMerge && (
              <Button
                type="primary"
                icon={<MergeCellsOutlined />}
                onClick={() => merge()}
                disabled={actionsDisabled}
                style={{ backgroundColor: "#722ed1", borderColor: "#722ed1" }}
              >
                Merge to Main
              </Button>
            )}
            {/* Recovery button for stuck workflows (admin only) */}
            {isStuck && (
              <Button
                danger
                icon={<ToolOutlined />}
                onClick={() => setRecoveryDialogVisible(true)}
                disabled={actionsDisabled}
                style={{ backgroundColor: "#faad14", borderColor: "#faad14", color: "#000" }}
              >
                Recover Workflow
              </Button>
            )}
          </Space>
        </div>
      </Space>
    </>
  );

  // Use CollapsibleCard if requested, otherwise use regular Card
  if (useCollapsibleCard) {
    return (
      <>
        <CollapsibleCard
          id="workflow"
          title={<Space>Workflow Status</Space>}
          style={{ marginBottom: 16 }}
        >
          {content}
        </CollapsibleCard>
        {/* Recovery dialog */}
        {isStuck && (
          <ChangeOrderRecoveryDialog
            changeOrder={changeOrder}
            visible={recoveryDialogVisible}
            onClose={() => setRecoveryDialogVisible(false)}
            onSuccess={onActionSuccess}
          />
        )}
      </>
    );
  }

  return (
    <>
      <Card
        id="workflow"
        title={<Space>Workflow Status</Space>}
        style={{ marginBottom: 16 }}
      >
        {content}
      </Card>
      {/* Recovery dialog */}
      {isStuck && (
        <ChangeOrderRecoveryDialog
          changeOrder={changeOrder}
          visible={recoveryDialogVisible}
          onClose={() => setRecoveryDialogVisible(false)}
          onSuccess={onActionSuccess}
        />
      )}
    </>
  );
}
