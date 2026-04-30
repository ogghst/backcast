/**
 * ApprovalDialog Component
 *
 * Modal dialog for requesting user approval for critical AI tool execution.
 * Displays tool information, arguments, and risk level.
 * Provides Approve/Reject/Cancel buttons for user decision.
 *
 * Features a live countdown timer with progress bar driven by
 * polling_heartbeat WebSocket messages, urgency color transitions,
 * and auto-dismiss when the approval expires.
 *
 * Theme-aware: Uses Ant Design theme tokens for dark mode support.
 */

import { useMemo } from "react";
import { Modal, Alert, Typography, Tag, Space, Descriptions, Button, theme } from "antd";
import type { WSApprovalRequestMessage } from "../chat/types";
import { ExclamationCircleOutlined } from "@ant-design/icons";

const { Text, Paragraph } = Typography;

interface ApprovalDialogProps {
  open: boolean;
  approvalRequest: WSApprovalRequestMessage | null;
  /** Remaining seconds from the latest heartbeat. null = no data yet. */
  remainingSeconds?: number | null;
  onApprove: () => void;
  onReject: () => void;
  onCancel?: () => void;
}

/**
 * Returns the progress bar color based on remaining time.
 * Uses theme token colors for dark mode compatibility.
 */
function getProgressColor(
  remaining: number,
  colors: { success: string; warning: string; error: string }
): string {
  if (remaining > 7) return colors.success;
  if (remaining > 3) return colors.warning;
  return colors.error;
}

/**
 * Modal dialog for approving critical tool execution
 *
 * @param open - Whether the modal is visible
 * @param approvalRequest - The approval request details
 * @param remainingSeconds - Remaining seconds from heartbeat (null = waiting)
 * @param onApprove - Callback when user approves
 * @param onReject - Callback when user rejects
 * @param onCancel - Optional callback when user cancels (closes modal)
 *
 * @example
 * ```tsx
 * <ApprovalDialog
 *   open={showApproval}
 *   approvalRequest={approvalRequest}
 *   remainingSeconds={7}
 *   onApprove={() => handleApproval(true)}
 *   onReject={() => handleApproval(false)}
 *   onCancel={() => setShowApproval(false)}
 * />
 * ```
 */
export const ApprovalDialog = ({
  open,
  approvalRequest,
  remainingSeconds,
  onApprove,
  onReject,
  onCancel,
}: ApprovalDialogProps) => {
  // Access theme tokens for dark mode support
  const { token } = theme.useToken();

  const isExpired = remainingSeconds !== null && remainingSeconds !== undefined && remainingSeconds <= 0;
  const isCountingDown = remainingSeconds !== null && remainingSeconds !== undefined && remainingSeconds > 0;
  const displaySeconds = remainingSeconds !== null && remainingSeconds !== undefined
    ? Math.ceil(remainingSeconds)
    : null;

  // Progress percentage: use remaining / 10 as a reasonable denominator.
  // The backend heartbeat starts at 10s, so this gives a smooth 100% -> 0% depletion.
  const progressPercent = useMemo(() => {
    if (remainingSeconds == null) return 0;
    return Math.max(0, Math.min(100, (remainingSeconds / 10) * 100));
  }, [remainingSeconds]);

  // Progress bar color derived from theme tokens
  const progressColor = useMemo(() => {
    if (remainingSeconds == null || remainingSeconds <= 0) return token.colorError;
    return getProgressColor(remainingSeconds, {
      success: token.colorSuccess,
      warning: token.colorWarning,
      error: token.colorError,
    });
  }, [remainingSeconds, token.colorSuccess, token.colorWarning, token.colorError]);

  // Subtle urgency background when time is critically low
  const urgencyBg = useMemo(() => {
    if (isCountingDown && remainingSeconds !== null && remainingSeconds < 3) {
      return `rgba(${hexToRgb(token.colorError)}, 0.06)`;
    }
    return undefined;
  }, [isCountingDown, remainingSeconds, token.colorError]);

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
          <ExclamationCircleOutlined
            style={{
              color: isExpired ? token.colorError : token.colorWarning,
            }}
          />
          <span>Approve Tool Execution</span>
          {isCountingDown && displaySeconds !== null && (
            <Text
              type="secondary"
              style={{ fontSize: token.fontSizeSM, fontWeight: token.fontWeightNormal }}
            >
              Auto-expiring in {displaySeconds}s
            </Text>
          )}
          {isExpired && (
            <Text
              type="danger"
              style={{ fontSize: token.fontSizeSM, fontWeight: token.fontWeightNormal }}
            >
              Expired
            </Text>
          )}
        </Space>
      }
      open={open}
      onCancel={handleCancel}
      width={600}
      destroyOnHidden
      closable={!isExpired}
      footer={
        <Space style={{ width: "100%", justifyContent: "flex-end" }}>
          <Button danger onClick={handleReject} disabled={isExpired}>
            Reject
          </Button>
          <Button onClick={handleCancel} disabled={isExpired}>
            Cancel
          </Button>
          <Button type="primary" onClick={handleApprove} disabled={isExpired}>
            Approve
          </Button>
        </Space>
      }
    >
      {/* Countdown progress bar */}
      {remainingSeconds !== null && remainingSeconds !== undefined && (
        <div
          style={{
            height: 3,
            background: token.colorFillSecondary,
            borderRadius: `${token.borderRadiusSM}px ${token.borderRadiusSM}px 0 0`,
            overflow: "hidden",
            marginBottom: token.marginMD,
          }}
        >
          <div
            style={{
              height: "100%",
              width: `${progressPercent}%`,
              background: progressColor,
              transition: "width 0.5s linear, background 0.5s linear",
            }}
          />
        </div>
      )}

      <div
        style={{
          ...(urgencyBg ? { background: urgencyBg, borderRadius: token.borderRadiusSM } : {}),
        }}
      >
        <Alert
          message="Critical Tool Requires Approval"
          description="This tool has been marked as critical and requires your explicit approval before execution."
          type={isExpired ? "error" : "warning"}
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
      </div>
    </Modal>
  );
};

/**
 * Converts a hex color string to an "r, g, b" string for use in rgba().
 * Falls back to "255, 77, 79" (red) for invalid input.
 */
function hexToRgb(hex: string): string {
  const cleaned = hex.replace("#", "");
  if (cleaned.length !== 6) return "255, 77, 79";
  const num = parseInt(cleaned, 16);
  if (isNaN(num)) return "255, 77, 79";
  const r = (num >> 16) & 255;
  const g = (num >> 8) & 255;
  const b = num & 255;
  return `${r}, ${g}, ${b}`;
}
