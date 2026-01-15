import { Tooltip, Space } from "antd";
import { LockOutlined, UnlockOutlined } from "@ant-design/icons";

interface BranchLockIndicatorProps {
  /** Whether the branch is locked */
  locked: boolean;
  /** Optional text to display next to the indicator */
  text?: string;
  /** Position variant */
  position?: "inline" | "standalone";
}

/**
 * BranchLockIndicator - Visual component showing branch lock status.
 *
 * Displays a lock/unlock icon with optional text and tooltip.
 * - Locked (red): Branch cannot be modified (under review/approval)
 * - Unlocked (green): Branch can be modified (draft/rejected)
 */
export function BranchLockIndicator({
  locked,
  text,
  position = "inline",
}: BranchLockIndicatorProps) {
  const icon = locked ? <LockOutlined /> : <UnlockOutlined />;
  const tooltipTitle = locked
    ? "Branch is locked - no modifications allowed"
    : "Branch is unlocked - modifications allowed";

  const content = (
    <Space size="small">
      <span style={{ color: locked ? "#ff4d4f" : "#52c41a" }}>{icon}</span>
      {text && <span>{text}</span>}
    </Space>
  );

  if (position === "standalone") {
    return (
      <div style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
        <Tooltip title={tooltipTitle}>{content}</Tooltip>
      </div>
    );
  }

  return <Tooltip title={tooltipTitle}>{content}</Tooltip>;
}
