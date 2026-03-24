/**
 * ApprovalDialog Component
 *
 * Modal dialog for requesting user approval for critical AI tool execution.
 * Displays tool information, arguments, and risk level.
 * Provides Approve/Reject/Cancel buttons for user decision.
 *
 * Theme-aware: Uses Ant Design theme tokens for dark mode support.
 */

import { Modal, Alert, Typography, Tag, Space, Descriptions, Button, theme } from "antd";
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
  // Access theme tokens for dark mode support
  const { token } = theme.useToken();

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
          <ExclamationCircleOutlined style={{ color: token.colorWarning }} />
          <span>Approve Tool Execution</span>
        </Space>
      }
      open={open}
      onCancel={handleCancel}
      width={600}
      destroyOnClose
      footer={
        <Space style={{ width: "100%", justifyContent: "flex-end" }}>
          <Button danger onClick={handleReject}>
            Reject
          </Button>
          <Button onClick={handleCancel}>
            Cancel
          </Button>
          <Button type="primary" onClick={handleApprove}>
            Approve
          </Button>
        </Space>
      }
    >
      <Alert
        message="Critical Tool Requires Approval"
        description="This tool has been marked as critical and requires your explicit approval before execution."
        type="warning"
        showIcon
        style={{ marginBottom: token.marginLG }}
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
                background: token.colorFillAlter,
                padding: token.paddingSM,
                borderRadius: token.borderRadiusSM,
                fontSize: token.fontSizeSM,
                overflow: "auto",
                maxHeight: 200,
                color: token.colorText,
                border: `1px solid ${token.colorBorderSecondary}`,
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
        style={{ marginTop: token.marginLG }}
      />
    </Modal>
  );
};
