import { Select, Space } from "antd";
import {
  BranchesOutlined,
  EditOutlined,
  SendOutlined,
  SearchOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  PlayCircleOutlined,
  StopOutlined,
} from "@ant-design/icons";
import type { BranchOption } from "./types";
import React from "react";

interface BranchSelectorProps {
  /** Currently selected branch */
  value: string;
  /** Available branches */
  branches: BranchOption[];
  /** Called when branch selection changes */
  onChange: (branch: string) => void;
  /** Disable selector */
  disabled?: boolean;
  /** Compact mode for header */
  compact?: boolean;
}

// Map status to Ant Design Icon
const STATUS_ICON: Record<string, React.ReactNode> = {
  Draft: <EditOutlined style={{ color: "#faad14" }} />, // Amber
  Submitted: <SendOutlined style={{ color: "#1890ff" }} />, // Blue
  "Under Review": <SearchOutlined style={{ color: "#52c41a" }} />, // Green
  Approved: <CheckCircleOutlined style={{ color: "#52c41a" }} />, // Green
  Rejected: <CloseCircleOutlined style={{ color: "#ff4d4f" }} />, // Red
  Implemented: <PlayCircleOutlined style={{ color: "#722ed1" }} />, // Purple
  Closed: <StopOutlined style={{ color: "#8c8c8c" }} />, // Gray
};

/**
 * Branch selector dropdown for switching between branches.
 *
 * Displays status badges for change order branches (BR-{code} pattern).
 *
 * @example
 * ```tsx
 * <BranchSelector
 *   value="main"
 *   branches={[
 *     { value: 'main', label: 'main', isDefault: true },
 *     { value: 'BR-CO-2026-001', label: 'BR-CO-2026-001', isChangeOrderBranch: true, changeOrderStatus: 'Draft' },
 *   ]}
 *   onChange={handleBranchChange}
 * />
 * ```
 */
export function BranchSelector({
  value,
  branches,
  onChange,
  disabled = false,
  compact = false,
}: BranchSelectorProps) {
  return (
    <Select
      value={value}
      onChange={onChange}
      disabled={disabled}
      style={{ minWidth: compact ? 120 : 180 }}
      size={compact ? "small" : "middle"}
      suffixIcon={<BranchesOutlined />}
      options={branches.map((branch) => ({
        value: branch.value,
        label: (
          <Space size="small">
            {branch.isChangeOrderBranch ? (
              <Space size="small" align="center">
                {STATUS_ICON[branch.changeOrderStatus || "Draft"] || (
                  <EditOutlined style={{ color: "#faad14" }} />
                )}
                <span style={{ fontSize: compact ? 12 : 13 }}>
                  {branch.label}
                </span>
              </Space>
            ) : (
              <span style={{ fontSize: compact ? 12 : 13 }}>
                {branch.label}
              </span>
            )}
            {branch.isDefault && (
              <span style={{ color: "#888", marginLeft: 4, fontSize: 11 }}>
                (default)
              </span>
            )}
          </Space>
        ),
      }))}
    />
  );
}

export default BranchSelector;
