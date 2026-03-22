/**
 * ApprovalDialog Component
 *
 * Modal dialog for requesting user approval for critical AI tool execution.
 * Displays tool information, arguments, and risk level.
 * Provides Approve/Reject/Cancel buttons for user decision.
 */

import { Modal, Alert, Typography, Tag, Space, Descriptions } from "antd";
import type { WSApprovalRequestMessage } from "../chat/types";
import { ExclamationCircleOutlined } from "@ant-design/icons";

const { Text, Paragraph } = Typography;

interface ApprovalDialogProps {
  open: boolean;
  approvalRequest: WSApprovalRequestMessage | null;
  onApprove: () => void;
  onReject: () => void;
  onCancel?: () => void;
}

/**
 * Modal dialog for approving critical tool execution
 *
 * @param open - Whether the modal is visible
 * @param approvalRequest - The approval request details
 * @param onApprove - Callback when user approves
 * @param onReject - Callback when user rejects
 * @param onCancel - Optional callback when user cancels (closes modal)
 *
 * @example
 * ```tsx
 * <ApprovalDialog
 *   open={showApproval}
 *   approvalRequest={approvalRequest}
 *   onApprove={() => handleApproval(true)}
 *   onReject={() => handleApproval(false)}
 *   onCancel={() => setShowApproval(false)}
 * />
 * ```
 */
export const ApprovalDialog = ({
  open,
  approvalRequest,
  onApprove,
  onReject,
  onCancel,
}: ApprovalDialogProps) => {
  if (!approvalRequest) {
    return null;
  }

  const handleApprove = () => {
    onApprove();
  };

  const handleReject = () => {
    onReject();
  };

  const handleCancel = () => {
    onCancel?.();
  };

  // Format tool arguments for display
  const formatArgs = (args: Record<string, unknown>): string => {
    return JSON.stringify(args, null, 2);
  };

  // Format expiration time
  const formatExpiresAt = (isoString: string): string => {
    const date = new Date(isoString);
    return date.toLocaleString();
  };

  return (
    <Modal
      title={
        <Space>
          <ExclamationCircleOutlined style={{ color: "#faad14" }} />
          <span>Approve Tool Execution</span>
        </Space>
      }
      open={open}
      onOk={handleApprove}
      onCancel={handleCancel}
      okText="Approve"
      cancelText="Reject"
      okButtonProps={{ danger: false }}
      cancelButtonProps={{ danger: true }}
      width={600}
      destroyOnClose
      footer={[
        <button key="reject" type="button" onClick={handleReject} style={{ marginRight: 8 }}>
          Reject
        </button>,
        <button key="cancel" type="button" onClick={handleCancel} style={{ marginRight: 8 }}>
          Cancel
        </button>,
        <button key="approve" type="button" onClick={handleApprove}>
          Approve
        </button>,
      ]}
    >
      <Alert
        message="Critical Tool Requires Approval"
        description="This tool has been marked as critical and requires your explicit approval before execution."
        type="warning"
        showIcon
        style={{ marginBottom: 16 }}
      />

      <Descriptions bordered column={1} size="small">
        <Descriptions.Item label="Tool Name">
          <Text code>{approvalRequest.tool_name}</Text>
        </Descriptions.Item>

        <Descriptions.Item label="Risk Level">
          <Tag color="red">{approvalRequest.risk_level.toUpperCase()}</Tag>
        </Descriptions.Item>

        <Descriptions.Item label="Tool Arguments">
          <Paragraph>
            <pre
              style={{
                background: "#f5f5f5",
                padding: 8,
                borderRadius: 4,
                fontSize: 12,
                overflow: "auto",
                maxHeight: 200,
              }}
            >
              {formatArgs(approvalRequest.tool_args)}
            </pre>
          </Paragraph>
        </Descriptions.Item>

        <Descriptions.Item label="Expires At">
          <Text type="secondary">{formatExpiresAt(approvalRequest.expires_at)}</Text>
        </Descriptions.Item>
      </Descriptions>

      <Alert
        message="Approval will allow this tool to execute with the provided arguments."
        type="info"
        showIcon
        style={{ marginTop: 16 }}
      />
    </Modal>
  );
};
