import { Card, Badge, Button, Space, Alert, Tag } from "antd";
import {
  CheckCircleOutlined,
  ClockCircleOutlined,
  CloseCircleOutlined,
  SyncOutlined,
  MergeCellsOutlined,
} from "@ant-design/icons";
import type { ChangeOrderPublic } from "@/api/generated";
import { useWorkflowActions, isActionAvailable, WORKFLOW_ACTIONS } from "../hooks/useWorkflowActions";
import { CollapsibleCard } from "@/components/common/CollapsibleCard";

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
 *
 * Hidden in create mode (when changeOrder is null).
 */
export function ChangeOrderWorkflowSection({
  changeOrder,
  onActionSuccess,
  useCollapsibleCard = false,
}: ChangeOrderWorkflowSectionProps): JSX.Element | null {
  // Hide in create mode
  if (!changeOrder) {
    return null;
  }

  const { change_order_id, status, branch_locked, available_transitions } = changeOrder;

  // Workflow actions
  const { submit, approve, reject, merge, isLoading } = useWorkflowActions(
    change_order_id,
    { onSuccess: onActionSuccess }
  );

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
      <Space direction="vertical" style={{ width: "100%" }} size="large">
        <div>
          <div style={{ marginBottom: 8, color: "#8c8c8c" }}>Current Status</div>
          <Badge
            color={STATUS_COLORS[status] || "default"}
            text={
              <Tag
                icon={STATUS_ICONS[status]}
                color={STATUS_COLORS[status] || "default"}
                style={{ fontSize: 14, padding: "4px 12px" }}
              >
                {status}
              </Tag>
            }
          />
        </div>

        {/* Available transitions */}
        {available_transitions && available_transitions.length > 0 && (
          <div>
            <div style={{ marginBottom: 8, color: "#8c8c8c" }}>Available Transitions</div>
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
          </Space>
        </div>
      </Space>
    </>
  );

  // Use CollapsibleCard if requested, otherwise use regular Card
  if (useCollapsibleCard) {
    return (
      <CollapsibleCard
        id="workflow"
        title={<Space>Workflow Status</Space>}
        style={{ marginBottom: 16 }}
      >
        {content}
      </CollapsibleCard>
    );
  }

  return (
    <Card
      id="workflow"
      title={<Space>Workflow Status</Space>}
      style={{ marginBottom: 16 }}
    >
      {content}
    </Card>
  );
}
