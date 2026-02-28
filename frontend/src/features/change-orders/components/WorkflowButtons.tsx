import { Button, Space, Modal } from "antd";
import { SendOutlined, CheckOutlined, CloseOutlined, MergeOutlined, ExclamationCircleOutlined, DeleteOutlined } from "@ant-design/icons";
import { useState } from "react";
import type { ChangeOrderPublic } from "@/api/generated";
import {
  WorkflowTransitionContent,
  MergeConfirmationContent,
  MergeConflictsList,
} from ".";
import { useWorkflowActions, isActionAvailable, WORKFLOW_ACTIONS } from "../hooks/useWorkflowActions";
import type { MergeConflict } from "../api/useChangeOrders";

interface WorkflowButtonsProps {
  /** Change Order data */
  changeOrder: ChangeOrderPublic;
  /** Optional list of merge conflicts (pre-fetched) */
  mergeConflicts?: MergeConflict[];
  /** Whether to show all available transitions or only primary actions */
  mode?: "all" | "primary";
}

/**
 * WorkflowButtons - Action buttons for available workflow transitions.
 *
 * Dynamically renders buttons based on available_transitions from the backend.
 * - Submit: Draft → Submitted for Approval
 * - Approve: Submitted for Approval → Under Review
 * - Reject: Any → Rejected (with confirmation)
 * - Merge: Approved → Implemented (with confirmation and conflict check)
 * - Archive: Implemented/Rejected → Archived (with confirmation)
 */
export function WorkflowButtons({
  changeOrder,
  mergeConflicts = [],
  mode = "all",
}: WorkflowButtonsProps) {
  const {
    submit,
    approve,
    reject,
    merge,
    archive,
    isLoading,
  } = useWorkflowActions(changeOrder.change_order_id);

  const [confirmModal, setConfirmModal] = useState<{
    type: "reject" | "merge" | "archive";
    visible: boolean;
  }>({ type: "reject", visible: false });

  const [comment, setComment] = useState("");

  const availableTransitions = changeOrder.available_transitions || [];

  // Check which actions are available
  const canSubmit = isActionAvailable("SUBMIT", availableTransitions);
  const canApprove = isActionAvailable("APPROVE", availableTransitions);
  const canReject = true; // Reject is always available as a workflow action
  const canMerge = isActionAvailable("MERGE", availableTransitions);
  const canArchive = isActionAvailable("ARCHIVE", availableTransitions);

  const handleAction = async (action: () => Promise<ChangeOrderPublic>) => {
    try {
      await action();
      setConfirmModal({ ...confirmModal, visible: false });
      setComment("");
    } catch {
      // Error is handled by the mutation
    }
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

  const confirmReject = async () => {
    await handleAction(() => reject(comment));
  };

  const confirmMerge = async () => {
    await handleAction(() => merge({ target_branch: "main", comment }));
  };

  const confirmArchive = async () => {
    await handleAction(() => archive());
  };

  // Determine which buttons to show based on mode
  const showSubmit = mode === "all" ? canSubmit : canSubmit;
  const showApprove = mode === "primary" ? canApprove : false;
  const showReject = mode === "primary" ? canReject : false;
  const showMerge = canMerge;
  const showArchive = canArchive;

  return (
    <>
      <Space wrap>
        {/* Submit button - visible in Draft */}
        {showSubmit && (
          <Button
            type="primary"
            icon={<SendOutlined />}
            onClick={() => submit()}
            loading={isLoading}
          >
            {WORKFLOW_ACTIONS.SUBMIT.label}
          </Button>
        )}

        {/* Approve button - visible for reviewers */}
        {showApprove && (
          <Button
            type="primary"
            icon={<CheckOutlined />}
            onClick={() => approve()}
            loading={isLoading}
          >
            {WORKFLOW_ACTIONS.APPROVE.label}
          </Button>
        )}

        {/* Reject button - visible for reviewers */}
        {showReject && (
          <Button
            danger
            icon={<CloseOutlined />}
            onClick={handleReject}
            disabled={isLoading}
          >
            {WORKFLOW_ACTIONS.REJECT.label}
          </Button>
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

        {/* Archive button - visible for Implemented/Rejected */}
        {showArchive && (
          <Button
            icon={<DeleteOutlined />}
            onClick={handleArchive}
            disabled={isLoading}
          >
            {WORKFLOW_ACTIONS.ARCHIVE.label}
          </Button>
        )}
      </Space>

      {/* Reject confirmation modal */}
      <Modal
        title={<Space><ExclamationCircleOutlined /> Reject Change Order</Space>}
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
        <WorkflowTransitionContent
          comment={comment}
          onCommentChange={setComment}
          placeholder="Explain why this change order is being rejected (optional)"
        />
      </Modal>

      {/* Merge confirmation modal */}
      <Modal
        title={<Space><MergeOutlined /> Merge to Main Branch</Space>}
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
        title={<Space><ExclamationCircleOutlined /> Archive Branch</Space>}
        open={confirmModal.type === "archive" && confirmModal.visible}
        onOk={confirmArchive}
        onCancel={() => {
          setConfirmModal({ ...confirmModal, visible: false });
          setComment("");
        }}
        confirmLoading={isLoading}
        okText="Archive Branch"
        okButtonProps={{ danger: true }}
        width={500}
      >
        <p>
          Archive this change order? The branch will hide it from the active branch list but but data remains accessible via time-travel queries.
        </p>
      </Modal>
    </>
  );
}
