import { Button, Space, Modal, Tooltip, Tag } from "antd";
import {
  SendOutlined,
  CheckOutlined,
  CloseOutlined,
  MergeOutlined,
  ExclamationCircleOutlined,
  LockOutlined,
  InboxOutlined,
} from "@ant-design/icons";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import type { ChangeOrderPublic } from "@/api/generated";
import { useAuthStore } from "@/stores/useAuthStore";
import {
  WorkflowTransitionContent,
  MergeConfirmationContent,
  MergeConflictsList,
} from ".";
import {
  useWorkflowActions,
  isActionAvailable,
  WORKFLOW_ACTIONS,
} from "../hooks/useWorkflowActions";
import {
  useSubmitForApproval,
  useApproveChangeOrder,
  useRejectChangeOrder,
} from "../api/useApprovals";
import { useArchiveChangeOrder } from "../api/useArchiveChangeOrder";
import { useCanApprove } from "../api/useCanApprove";
import type { MergeConflict } from "../api/useChangeOrders";

interface WorkflowActionsProps {
  /** Change Order data */
  changeOrder: ChangeOrderPublic;
  /** Optional list of merge conflicts (pre-fetched) */
  mergeConflicts?: MergeConflict[];
  /** Whether to show all available transitions or only primary actions */
  mode?: "all" | "primary";
}

/**
 * WorkflowActions - Action buttons for available workflow transitions with authority checks.
 *
 * Dynamically renders buttons based on available_transitions from the backend and user authority.
 * - Submit: Draft → Submitted for Approval (visible only to creator)
 * - Approve: Submitted for Approval → Under Review (visible only to authorized approvers)
 * - Reject: Any → Rejected (visible only to authorized approvers, with confirmation)
 * - Merge: Approved → Implemented (with confirmation and conflict check)
 *
 * Authority Integration:
 * - Uses useCanApprove hook to check user's approval authority
 * - Shows authority level badge when user can approve
 * - Disables buttons with tooltips when user lacks authority
 * - Confirms approve/reject actions with optional comments
 */
export function WorkflowActions({
  changeOrder,
  mergeConflicts = [],
  mode = "all",
}: WorkflowActionsProps) {
  const user = useAuthStore((state) => state.user);
  const {
    canApprove,
    authorityLevel,
    isLoading: checkingAuthority,
    reason,
  } = useCanApprove(changeOrder);

  // Legacy workflow actions (for merge, non-approval transitions)
  const { merge, isLoading: isLoadingLegacy } = useWorkflowActions(
    changeOrder.change_order_id,
  );

  // New approval mutations
  const submitMutation = useSubmitForApproval();
  const approveMutation = useApproveChangeOrder();
  const rejectMutation = useRejectChangeOrder();
  const archiveMutation = useArchiveChangeOrder();
  const navigate = useNavigate();

  const [confirmModal, setConfirmModal] = useState<{
    type: "submit" | "approve" | "reject" | "merge" | "archive";
    visible: boolean;
  }>({ type: "submit", visible: false });

  const [comment, setComment] = useState("");

  const availableTransitions = changeOrder.available_transitions || [];

  // Check which actions are available
  const canSubmit = isActionAvailable("SUBMIT", availableTransitions);
  const canMerge = isActionAvailable("MERGE", availableTransitions);

  // Check if user created this change order
  const isCreator = user && user.user_id === changeOrder.created_by;

  // Determine if approve/reject should be shown
  // Show when status is Submitted for Approval or Under Review, and user has authority
  const canShowApproveReject =
    (changeOrder.status === "Submitted for Approval" ||
      changeOrder.status === "Under Review") &&
    canApprove;

  // Determine if submit should be shown
  // Only show when status is Draft and user is the creator
  const canShowSubmit =
    changeOrder.status === "Draft" && isCreator && canSubmit;

  const isLoading =
    submitMutation.isPending ||
    approveMutation.isPending ||
    rejectMutation.isPending ||
    archiveMutation.isPending ||
    isLoadingLegacy ||
    checkingAuthority;

  const handleAction = async (action: () => Promise<ChangeOrderPublic>) => {
    try {
      await action();
      setConfirmModal({ ...confirmModal, visible: false });
      setComment("");
    } catch {
      // Error is handled by the mutation
    }
  };

  const handleSubmit = () => {
    setConfirmModal({ type: "submit", visible: true });
  };

  const handleApprove = () => {
    setConfirmModal({ type: "approve", visible: true });
  };

  const handleReject = () => {
    setConfirmModal({ type: "reject", visible: true });
  };

  const handleMerge = () => {
    // Check for conflicts if available
    if (mergeConflicts.length > 0) {
      setConfirmModal({ type: "merge", visible: true });
    } else {
      // No conflicts, proceed with merge confirmation
      setConfirmModal({ type: "merge", visible: true });
    }
  };

  const handleArchive = () => {
    setConfirmModal({ type: "archive", visible: true });
  };

  const confirmSubmit = async () => {
    await handleAction(() =>
      submitMutation.mutateAsync({ id: changeOrder.change_order_id, comment }),
    );
  };

  const confirmApprove = async () => {
    await handleAction(() =>
      approveMutation.mutateAsync({
        id: changeOrder.change_order_id,
        approval: { comments: comment || undefined },
      }),
    );
  };

  const confirmReject = async () => {
    await handleAction(() =>
      rejectMutation.mutateAsync({
        id: changeOrder.change_order_id,
        approval: { comments: comment || undefined },
      }),
    );
  };

  const confirmMerge = async () => {
    await handleAction(() => merge({ target_branch: "main", comment }));
  };

  const confirmArchive = async () => {
    await handleAction(async () => {
      await archiveMutation.mutateAsync(changeOrder.change_order_id);
      navigate("/change-orders");
      // Return a dummy object to satisfy handleAction definition
      return {} as ChangeOrderPublic;
    });
  };

  // Determine which buttons to show based on mode
  const showSubmit = mode === "all" ? canShowSubmit : canShowSubmit;
  const showMerge = canMerge;
  const showArchive =
    changeOrder.status === "Implemented" || changeOrder.status === "Rejected";

  return (
    <>
      <Space wrap>
        {/* Submit button - visible in Draft, only for creator */}
        {showSubmit && (
          <Button
            type="primary"
            icon={<SendOutlined />}
            onClick={handleSubmit}
            loading={isLoading}
          >
            Submit for Approval
          </Button>
        )}

        {/* Approve button - visible for authorized approvers */}
        {canShowApproveReject && mode !== "primary" && (
          <Tooltip
            title={
              authorityLevel
                ? `Your authority level: ${authorityLevel}`
                : undefined
            }
          >
            <Button
              type="primary"
              icon={<CheckOutlined />}
              onClick={handleApprove}
              loading={isLoading}
            >
              Approve{" "}
              {authorityLevel && <Tag color="blue">{authorityLevel}</Tag>}
            </Button>
          </Tooltip>
        )}

        {/* Reject button - visible for authorized approvers */}
        {canShowApproveReject && mode !== "primary" && (
          <Tooltip
            title={
              authorityLevel
                ? `Your authority level: ${authorityLevel}`
                : undefined
            }
          >
            <Button
              danger
              icon={<CloseOutlined />}
              onClick={handleReject}
              loading={isLoading}
            >
              Reject
            </Button>
          </Tooltip>
        )}

        {/* Disabled approve button (for users without authority) */}
        {mode !== "primary" &&
          (changeOrder.status === "Submitted for Approval" ||
            changeOrder.status === "Under Review") &&
          !canApprove &&
          !checkingAuthority && (
            <Tooltip
              title={
                reason || "You are not authorized to approve this change order"
              }
            >
              <Button icon={<LockOutlined />} disabled>
                Approve
              </Button>
            </Tooltip>
          )}

        {/* Merge button - visible when Approved */}
        {showMerge && (
          <Button
            type="primary"
            icon={<MergeOutlined />}
            onClick={handleMerge}
            disabled={isLoading || mergeConflicts.length > 0}
          >
            {WORKFLOW_ACTIONS.MERGE.label}
          </Button>
        )}

        {/* Archive button - visually disabled if not Implemented/Rejected */}
        {mode === "all" && (
          <Tooltip
            title={
              !showArchive
                ? "Only 'Implemented' or 'Rejected' change order branches can be archived"
                : undefined
            }
          >
            <Button
              icon={<InboxOutlined />}
              onClick={handleArchive}
              disabled={!showArchive || isLoading}
            >
              Archive Branch
            </Button>
          </Tooltip>
        )}
      </Space>

      {/* Submit confirmation modal */}
      <Modal
        title={
          <Space>
            <SendOutlined /> Submit for Approval
          </Space>
        }
        open={confirmModal.type === "submit" && confirmModal.visible}
        onOk={confirmSubmit}
        onCancel={() => {
          setConfirmModal({ ...confirmModal, visible: false });
          setComment("");
        }}
        confirmLoading={isLoading}
        okText="Submit"
        width={500}
      >
        <p>
          This will calculate the financial impact, assign an appropriate
          approver based on impact level, and lock the branch for review.
        </p>
        <WorkflowTransitionContent
          comment={comment}
          onCommentChange={setComment}
          placeholder="Add a comment for the approver (optional)"
        />
      </Modal>

      {/* Approve confirmation modal */}
      <Modal
        title={
          <Space>
            <CheckOutlined /> Approve Change Order
          </Space>
        }
        open={confirmModal.type === "approve" && confirmModal.visible}
        onOk={confirmApprove}
        onCancel={() => {
          setConfirmModal({ ...confirmModal, visible: false });
          setComment("");
        }}
        confirmLoading={isLoading}
        okText="Approve"
        width={500}
      >
        <p>Are you sure you want to approve this change order?</p>
        <WorkflowTransitionContent
          comment={comment}
          onCommentChange={setComment}
          placeholder="Add a comment for the audit trail (optional)"
        />
      </Modal>

      {/* Reject confirmation modal */}
      <Modal
        title={
          <Space>
            <ExclamationCircleOutlined /> Reject Change Order
          </Space>
        }
        open={confirmModal.type === "reject" && confirmModal.visible}
        onOk={confirmReject}
        onCancel={() => {
          setConfirmModal({ ...confirmModal, visible: false });
          setComment("");
        }}
        confirmLoading={isLoading}
        okText="Reject"
        okButtonProps={{ danger: true }}
        width={500}
      >
        <p>
          Are you sure you want to reject this change order? The branch will be
          unlocked.
        </p>
        <WorkflowTransitionContent
          comment={comment}
          onCommentChange={setComment}
          placeholder="Explain why this change order is being rejected (optional)"
        />
      </Modal>

      {/* Merge confirmation modal */}
      <Modal
        title={
          <Space>
            <MergeOutlined /> Merge to Main Branch
          </Space>
        }
        open={confirmModal.type === "merge" && confirmModal.visible}
        onOk={confirmMerge}
        onCancel={() => {
          setConfirmModal({ ...confirmModal, visible: false });
          setComment("");
        }}
        confirmLoading={isLoading}
        okText="Merge"
        width={600}
      >
        {mergeConflicts.length > 0 ? (
          <MergeConflictsList conflicts={mergeConflicts} />
        ) : (
          <>
            <MergeConfirmationContent
              sourceBranch={`BR-${changeOrder.code}`}
              targetBranch="main"
              targetStatus="Implemented"
            />
            <WorkflowTransitionContent
              comment={comment}
              onCommentChange={setComment}
              placeholder="Add a comment for this merge (optional)"
            />
          </>
        )}
      </Modal>

      {/* Archive confirmation modal */}
      <Modal
        title={
          <Space>
            <InboxOutlined /> Archive Branch
          </Space>
        }
        open={confirmModal.type === "archive" && confirmModal.visible}
        onOk={confirmArchive}
        onCancel={() => {
          setConfirmModal({ ...confirmModal, visible: false });
        }}
        confirmLoading={isLoading}
        okText="Archive"
        okButtonProps={{ danger: true }}
        width={500}
      >
        <p>
          Are you sure you want to archive this Change Order branch? This will
          hide the branch from active views but retain it in historical records.
        </p>
      </Modal>
    </>
  );
}
